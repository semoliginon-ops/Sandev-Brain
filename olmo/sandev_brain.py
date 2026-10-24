"""Runtime wrapper for the SANDEV-adapted OLMo model.

The model proposes both natural-language dialogue and a game action.
The host game must execute only actions present in its current allow-list.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

DEFAULT_MODEL = "allenai/Olmo-3-7B-Instruct"

SYSTEM_PROMPT = """You are SANDEV Brain, the language intelligence of SANDEV Life.
Speak naturally in Indonesian unless the player uses another language.
Maintain the supplied character identity, memories, emotions, goals, and world state.
Reason about the situation before responding. Never claim an action succeeded; the game engine reports outcomes.
Return exactly one JSON object, without Markdown, with this schema:
{"say":"natural character dialogue","action":{"type":"one valid action or null","target":"optional target or empty string"},"memory_update":"short important event or empty string"}
Only choose an action listed in VALID ACTIONS. If no action is appropriate, use {"type":null,"target":""}.
Do not invent game objects, locations, characters, or action types."""


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object even if the model accidentally wraps it in code fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("OLMo output did not contain a JSON object")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("OLMo output must be a JSON object")
    return value


def validate_response(raw: str, valid_actions: list[str]) -> dict[str, Any]:
    """Validate model output at the game boundary; never silently execute unknown actions."""
    result = _extract_json(raw)
    say = result.get("say", "")
    action = result.get("action")
    memory_update = result.get("memory_update", "")
    if not isinstance(say, str):
        raise ValueError("'say' must be a string")
    if not isinstance(memory_update, str):
        memory_update = ""
    if action is not None:
        if not isinstance(action, dict):
            raise ValueError("'action' must be an object or null")
        action_type = action.get("type")
        if action_type is not None and action_type not in valid_actions:
            # Reject the action instead of executing a hallucinated command.
            action = None
        elif action_type is None:
            action = None
        else:
            target = action.get("target", "")
            action = {"type": action_type, "target": target if isinstance(target, str) else ""}
    return {"say": say, "action": action, "memory_update": memory_update}


class SandevBrain:
    def __init__(self, model_id: str | None = None, *, device_map: str = "auto"):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_id = model_id or os.environ.get("SANDEV_OLMO_MODEL", DEFAULT_MODEL)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            device_map=device_map,
            torch_dtype="auto",
        )
        self.model.eval()

    def respond(
        self,
        *,
        character: dict[str, Any],
        player_message: str,
        valid_actions: list[str],
        recent_memory: list[dict[str, Any]] | None = None,
        max_new_tokens: int = 256,
    ) -> dict[str, Any]:
        world_context = {
            "character": character,
            "recent_memory": recent_memory or [],
            "player_message": player_message,
            "valid_actions": valid_actions,
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "SANDEV LIFE CONTEXT:\n" + json.dumps(world_context, ensure_ascii=False)},
        ]
        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        ).to(self.model.device)
        import torch

        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.6,
                top_p=0.95,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = output[0, inputs["input_ids"].shape[1] :]
        raw = self.tokenizer.decode(generated, skip_special_tokens=True)
        return validate_response(raw, valid_actions)
