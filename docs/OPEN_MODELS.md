# Open Model Research Notes

This document tracks open model projects worth studying for SANDEV Brain. It is a research index, not a claim that these models can be copied into the game without cost or constraints.

## Projects to inspect

### OLMo
Repository: https://github.com/allenai/OLMo

Study the model code, training pipeline, released checkpoints, tokenizer, evaluation setup, and the license for the exact version/component used.

### OLMoE
Repository: https://github.com/allenai/OLMoE

Study the mixture-of-experts design and its inference/training trade-offs. Do not assume it will be suitable for low-memory mobile deployment without measurement.

### Qwen2.5-0.5B-Instruct
Model page: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

A small instruct model can serve as a comparison point for command understanding and dialogue quality. Verify the model license, runtime requirements, tokenizer, and distribution terms before integration.

## Important distinction

- **Source code** describes how a model or system works.
- **Weights/checkpoints** contain learned parameters.
- **Tokenizer and configuration** are needed to interpret input/output correctly.
- **Training data and training process** affect the capabilities of a trained model.
- **Runtime and hardware** determine whether inference is practical on target devices.

A source repository alone does not reproduce the trained model's intelligence.

## SANDEV Brain research direction

Prioritize a hybrid, simulation-focused brain:
1. Structured character state and persistent memory.
2. Needs, mood, relationships, personality, and goals.
3. A planner that converts goals into valid game actions.
4. Dialogue and intent parsing with graceful fallbacks.
5. Optional compact language model experiments only if packaging, latency, and memory tests justify them.

Before adopting any third-party component, inspect the license for the exact code, model weights, tokenizer, and datasets separately.
