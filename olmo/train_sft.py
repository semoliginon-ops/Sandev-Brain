"""Supervised fine-tuning of OLMo 3 7B Instruct for SANDEV Life.

The script intentionally trains the OLMo checkpoint itself via a LoRA adapter.
It does not call an external hosted inference API.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

DEFAULT_MODEL = "allenai/Olmo-3-7B-Instruct"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="olmo/data/train.jsonl")
    parser.add_argument("--output", default="outputs/sandev-olmo-adapter")
    parser.add_argument("--model", default=os.environ.get("SANDEV_OLMO_MODEL", DEFAULT_MODEL))
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accumulation", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)
    if not data_path.is_file():
        raise FileNotFoundError(f"Training JSONL not found: {data_path}")

    dataset = load_dataset("json", data_files=str(data_path), split="train")
    if len(dataset) < 2:
        raise ValueError("Provide at least two conversational examples before training.")
    if "messages" not in dataset.column_names:
        raise ValueError("Each JSONL row must contain a 'messages' conversational array.")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    use_cuda = torch.cuda.is_available()
    use_bf16 = use_cuda and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if use_bf16 else (torch.float16 if use_cuda else torch.float32)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    # OLMo's attention and MLP projections are adapted; base weights remain frozen.
    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    output = Path(args.output)
    training_args = SFTConfig(
        output_dir=str(output),
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accumulation,
        max_seq_length=args.max_length,
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
        gradient_checkpointing=True,
        bf16=use_bf16,
        fp16=use_cuda and not use_bf16,
        optim="adamw_torch",
        dataset_num_proc=1,
        packing=False,
    )
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=lora,
    )
    trainer.train()
    trainer.save_model(str(output))
    tokenizer.save_pretrained(str(output))
    print(f"SANDEV OLMo adapter saved to: {output.resolve()}")


if __name__ == "__main__":
    main()
