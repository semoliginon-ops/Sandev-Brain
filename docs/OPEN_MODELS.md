# Direct OLMo Adaptation for SANDEV Brain

## Chosen upstream model

- Model: [allenai/Olmo-3-7B-Instruct](https://huggingface.co/allenai/Olmo-3-7B-Instruct)
- Official code for pretraining and SFT: [allenai/OLMo-core](https://github.com/allenai/OLMo-core)
- Transformers support: upstream model card states Transformers 4.57.0 or newer.
- License stated by model card: Apache-2.0; also review AI2 Responsible Use Guidelines and licenses of any additional data.

The older `allenai/OLMo` repository says it is out of date for recent releases. New development is in OLMo-core.

## SANDEV adaptation path

This project is adapting OLMo directly, not selecting another base model and not using a hybrid architecture.

1. Start from the official OLMo 3 7B Instruct checkpoint.
2. Fine-tune SANDEV behavior with conversational examples using a LoRA adapter.
3. Train the model to produce natural dialogue and a structured action proposal in one response.
4. Validate the generated action against the game engine's current allow-list before execution.
5. Expand Indonesian training data for memory recall, personality, emotion, long-term goals, planning, game knowledge, and player dialogue.
6. Evaluate on held-out scenarios and record invalid-action rate, context recall, dialogue quality, latency, and memory use.

## Current code

- `olmo/train_sft.py`: supervised fine-tuning entry point.
- `olmo/sandev_brain.py`: OLMo runtime wrapper and output validator.
- `olmo/data/train.jsonl`: tiny seed set for pipeline smoke testing only.
- `olmo/eval.jsonl`: initial held-out evaluation cases.
- `olmo/test_runtime.py`: tests output parsing and action validation without loading model weights.

## Important limits

The adapter has not been trained yet. A small seed dataset cannot teach the full target behavior. OLMo 3 7B's published model files are about 14.6 GB, and training needs substantially more memory than inference; a normal CPU GitHub Actions runner is not a suitable trainer. The repository stores implementation code and examples, not the upstream model weights.

A LoRA adapter is not a standalone language model: it modifies OLMo's learned behavior and must be loaded with its matching base checkpoint. Do not claim parity with another model until evaluation supports it.

## Upstream references

- https://huggingface.co/allenai/Olmo-3-7B-Instruct
- https://github.com/allenai/OLMo-core
- https://docs.allenai.org/models/olmo/index.html
