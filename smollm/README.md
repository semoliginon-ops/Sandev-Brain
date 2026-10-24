# SANDEV Brain — SmolLM2-360M adaptation

Selected base: HuggingFaceTB/SmolLM2-360M-Instruct. This is one adapted language model for Indonesian conversation, character context, memory use, reasoning, and game-action proposals.

Official model card: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
Official model/training repository: https://github.com/huggingface/smollm
The official model card states Apache-2.0. Check all data and artifact licenses before redistribution.

Important limitation: SmolLM2 primarily understands and generates English according to its model card. Indonesian fluency must be taught and evaluated, not assumed.

## Training

Do not train on the Samsung A05. Use a suitable temporary GPU training environment, then evaluate the adapter and a tested quantized export on the phone. This does not require game-time cloud inference.

Install a compatible PyTorch build, then install smollm/requirements.txt. Run: python smollm/train_sft.py --data smollm/data/train.jsonl --output outputs/sandev-smollm2-adapter

The LoRA adapter is not standalone; it requires the same base model unless merged and converted through a tested export pipeline.

## Mobile target: Samsung A05, RAM 6 GB

A 360M model is a plausible on-device candidate. Original BF16 weights are roughly 0.7 GB before runtime and context memory; quantization can reduce storage. Actual peak RAM, speed, heat, and stability on the Samsung A05 are not yet verified. Start with context around 1,024 tokens and at most 96 generated tokens. The Python Transformers runtime is a prototype, not an Android APK.

## Evaluation gates

1. Indonesian relevance, fluency, and character consistency.
2. Correct use of supplied context and remembered facts without inventing events.
3. Reasonable decisions from needs, goals, and constraints.
4. Valid action rate and successful engine execution rate.
5. Actual A05 model download size, installed size, peak RAM, cold start, tokens per second, and crash/timeout rate.

The game engine must verify outcomes and only persist confirmed events. Passing parser tests does not prove model quality or mobile readiness.
