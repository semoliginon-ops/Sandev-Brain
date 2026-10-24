# SmolLM2 research tools for SANDEV Brain

This folder contains research tools using `HuggingFaceTB/SmolLM2-360M-Instruct` as a **teacher/reference during development**. It does not define the shipped SANDEV Brain runtime.

Official model card: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
Official upstream project: https://github.com/huggingface/smollm
The upstream model card lists Apache-2.0. Check each dataset and output artifact's license separately.

## Correct product boundary

The final game must **not load the SmolLM model, its weights, or a different local LLM**. It must not require a cloud LLM during gameplay either. The point of this research is to extract useful behavior into a reusable game system: curated dialogue behavior, structured context and memory, goal/need evaluation, planning, action scoring, and game-engine adapters. A small learned component may be considered only if it can run as an ordinary packaged game component without loading an LLM; first establish whether deterministic/compiled components can meet the quality target.

## Files

- `data/train.jsonl`: small Indonesian behavior seed set.
- `data/eval.jsonl`: separate starter evaluation examples.
- `train_sft.py`: experimental LoRA training of the teacher model. This is research-only and is not the final game build.
- `sandev_brain.py`: research inference harness and prototype for structured outputs, action validation, and persistent event memory. Do not embed this Python Transformers runtime in the game.
- `test_runtime.py`: tests JSON parsing, action allow-list, and memory persistence without loading model weights.

## Research workflow

1. Expand the dataset with diverse Indonesian multi-turn scenarios, character traits, goals, needs, relationships, and world-state constraints.
2. Use the teacher model in the development environment to propose candidate conversations/decisions; review and label examples. Never accept generated claims as game facts automatically.
3. Evaluate examples against held-out scenarios and human-defined rubrics.
4. Convert validated behaviors into the independent SANDEV Brain modules and generic game-action interface.
5. Run the same scenario suite against the independent system, with the teacher as a comparison baseline only.
6. Verify the shipped game works with no LLM weights, model download, or network inference.

## Honest status

The current dataset is only a seed set. Training has not been run and no trained adapter is included. A LoRA adapter alone would still require the base model, so it is not the product we are building. The product is the reusable, model-independent game intelligence system.
