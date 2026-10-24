# SANDEV Brain — Direct OLMo Adaptation

This directory adapts **allenai/Olmo-3-7B-Instruct** into a SANDEV Life language-and-action model. It is not a hybrid with another model and does not replace OLMo with hand-written NPC rules.

## What is implemented here

- Supervised fine-tuning (SFT) on SANDEV Life conversations and structured game-action examples.
- A SANDEV system prompt that supplies character state and valid game actions to the adapted OLMo model.
- JSON action output with strict allow-list validation before the game engine executes anything.
- A small evaluation set to check Indonesian dialogue, context use, and valid action selection.

The training pipeline starts from the official OLMo 3 7B Instruct checkpoint. It trains an adapter using LoRA so the learned SANDEV behavior is stored as a small adapter artifact instead of copying all base weights into every checkpoint. The adapter still requires the OLMo base checkpoint at inference time; it is not a standalone model.

## Model source

- Model: https://huggingface.co/allenai/Olmo-3-7B-Instruct
- Official training code: https://github.com/allenai/OLMo-core
- Model card lists Apache-2.0 and Transformers >= 4.57.0 support. Recheck the exact upstream license and responsible-use terms before distribution.

## Dataset format

Each JSONL row is a conversational example:

```json
{"messages":[{"role":"system","content":"You are SANDEV Brain..."},{"role":"user","content":"...game state and player message..."},{"role":"assistant","content":"{\"say\":\"...\",\"action\":{\"type\":\"socialize\"}}"}]}
```

Training data should include varied Indonesian conversations, character identity and memory, emotions, planning, game-world knowledge, and tool/action examples. Do not train only on templated responses; evaluate on held-out situations.

## Training

Use a Python 3.10+ environment with a compatible CUDA GPU and enough VRAM. OLMo 3 7B is a large model; this is not expected to train on a normal CPU GitHub Actions runner.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r olmo/requirements.txt
python olmo/train_sft.py --data olmo/data/train.jsonl --output outputs/sandev-olmo-adapter
```

Set `SANDEV_OLMO_MODEL` to a local model directory or another exact compatible OLMo checkpoint if needed. By default, the script uses the official model ID and downloads weights to the training machine's cache.

## Inference contract

Input: character state, recent memory, player message, and the current list of valid actions.

Output JSON:
```json
{
  "say": "Natural dialogue in Indonesian",
  "action": {"type": "socialize", "target": "Joni"},
  "memory_update": "Short relevant event or empty string"
}
```

The runtime rejects malformed JSON and actions not present in the current world's allow-list. This validation is an execution boundary, not a second decision-making brain: OLMo generates the dialogue and proposed action.

## Important limits

- This is an adaptation pipeline and runtime interface, not proof that the adapted model is already trained.
- The initial examples are a tiny smoke-test seed, not enough to teach broad SANDEV behavior.
- Training and inference require model weights. GitHub stores source code and small datasets here, not the multi-gigabyte base checkpoint.
- We must run training and held-out evaluations before claiming quality or equivalence to another model.
