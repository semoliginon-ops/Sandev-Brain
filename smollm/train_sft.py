"""LoRA SFT for SANDEV Brain using SmolLM2-360M-Instruct."""
from __future__ import annotations
import argparse, inspect, os
from pathlib import Path
import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="smollm/data/train.jsonl")
    p.add_argument("--output", default="outputs/sandev-smollm2-adapter")
    p.add_argument("--model", default=os.environ.get("SANDEV_SMOLLM_MODEL", DEFAULT_MODEL))
    p.add_argument("--epochs", type=float, default=3.0)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--max-length", type=int, default=1024)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--grad-accumulation", type=int, default=8)
    return p.parse_args()

def main():
    args = parse_args()
    data_path = Path(args.data)
    if not data_path.is_file(): raise FileNotFoundError(f"Training data not found: {data_path}")
    dataset = load_dataset("json", data_files=str(data_path), split="train")
    if len(dataset) < 2 or "messages" not in dataset.column_names:
        raise ValueError("Dataset needs at least two rows with a messages array.")
    if any(not isinstance(row["messages"], list) or len(row["messages"]) < 2 for row in dataset):
        raise ValueError("Every row must contain at least two conversational messages.")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token
    use_cuda = torch.cuda.is_available()
    use_bf16 = use_cuda and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if use_bf16 else (torch.float16 if use_cuda else torch.float32)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype, low_cpu_mem_usage=True)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()
    linear_names = {name.rsplit(".", 1)[-1] for name, module in model.named_modules() if isinstance(module, torch.nn.Linear)}
    preferred = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    targets = [name for name in preferred if name in linear_names]
    if not targets: raise RuntimeError(f"No expected LoRA projection names found: {sorted(linear_names)[:40]}")
    lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM", target_modules=targets)
    cfg = dict(output_dir=args.output, num_train_epochs=args.epochs, learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size, gradient_accumulation_steps=args.grad_accumulation,
        logging_steps=5, save_strategy="epoch", save_total_limit=2, report_to="none",
        gradient_checkpointing=True, bf16=use_bf16, fp16=use_cuda and not use_bf16,
        optim="adamw_torch", dataset_num_proc=1, packing=False, seed=42)
    params = inspect.signature(SFTConfig).parameters
    cfg["max_length" if "max_length" in params else "max_seq_length"] = args.max_length
    training_args = SFTConfig(**cfg)
    kwargs = dict(model=model, args=training_args, train_dataset=dataset, peft_config=lora)
    trainer_params = inspect.signature(SFTTrainer).parameters
    kwargs["processing_class" if "processing_class" in trainer_params else "tokenizer"] = tokenizer
    trainer = SFTTrainer(**kwargs)
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"Adapter saved to: {Path(args.output).resolve()}")

if __name__ == "__main__": main()
