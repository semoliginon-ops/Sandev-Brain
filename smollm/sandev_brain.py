"""SANDEV Brain runtime prototype for SmolLM2-360M-Instruct."""
from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"
SYSTEM_PROMPT = """Kamu adalah SANDEV Brain untuk simulasi kehidupan SANDEV.
Berbicaralah secara alami dalam bahasa Indonesia dan pertahankan kepribadian karakter.
Gunakan state dan memori yang diberikan. Bedakan fakta tersimpan dari dugaan.
Pertimbangkan kebutuhan, tujuan, hubungan, lokasi, dan konsekuensi sebelum memilih aksi.
Jangan mengklaim aksi berhasil; game engine yang mengonfirmasi hasilnya.
Keluarkan tepat satu objek JSON: {"say":"dialog","action":{"type":"aksi_valid_atau_null","target":"target_atau_kosong"},"memory_update":{"event":"kejadian penting atau kosong","importance":0}}.
Pilih action.type hanya dari VALID ACTIONS. Jangan mengarang aksi, lokasi, atau karakter.
Jika tidak ada aksi cocok, gunakan {"type":null,"target":""}.
memory_update adalah usulan; engine wajib memverifikasi kejadian sebelum menyimpannya."""

def _extract_json(raw: str) -> dict[str, Any]:
    fence = chr(96) * 3
    text = re.sub(r"^\\s*" + re.escape(fence) + r"(?:json)?\\s*", "", raw.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\\s*" + re.escape(fence) + r"\\s*$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start: raise ValueError("Model output contains no JSON object")
    obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict): raise ValueError("Model output must be a JSON object")
    return obj

def validate_response(raw: str, valid_actions: list[str]) -> dict[str, Any]:
    obj = _extract_json(raw)
    say = obj.get("say", "")
    if not isinstance(say, str): raise ValueError("'say' must be a string")
    action = obj.get("action")
    if action is not None:
        if not isinstance(action, dict): raise ValueError("'action' must be an object or null")
        kind = action.get("type")
        if kind is None or not isinstance(kind, str) or kind not in valid_actions: action = None
        else:
            target = action.get("target", "")
            action = {"type": kind, "target": target if isinstance(target, str) else ""}
    memory = obj.get("memory_update", {})
    if not isinstance(memory, dict): memory = {}
    event, importance = memory.get("event", ""), memory.get("importance", 0)
    memory = {"event": event if isinstance(event, str) else "",
              "importance": max(0, min(3, importance)) if isinstance(importance, int) else 0}
    return {"say": say, "action": action, "memory_update": memory}

class MemoryStore:
    """Game-owned persistent facts; storage, not a second AI model."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = loaded if isinstance(loaded, list) else []
        except (OSError, json.JSONDecodeError): self.items = []

    def add_confirmed_event(self, event: str, *, importance: int = 1, turn: int | None = None):
        event = event.strip()
        if not event: return
        item = {"event": event, "importance": max(0, min(3, int(importance)))}
        if turn is not None: item["turn"] = int(turn)
        self.items.append(item)
        self.items = self.items[-200:]
        self.path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")

    def relevant(self, limit: int = 8) -> list[dict[str, Any]]:
        return sorted(self.items, key=lambda item: (int(item.get("importance", 0)), int(item.get("turn", 0))),
                      reverse=True)[:max(0, limit)]

class SandevBrain:
    def __init__(self, model_id: str | None = None, *, device: str | None = None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.model_id = model_id or os.environ.get("SANDEV_SMOLLM_MODEL", DEFAULT_MODEL)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        kwargs: dict[str, Any] = {"torch_dtype": "auto", "low_cpu_mem_usage": True}
        if device: kwargs["device_map"] = device
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)
        self.model.eval()
        self.torch = torch

    def respond(self, *, character: dict[str, Any], player_message: str, valid_actions: list[str],
                recent_events: list[dict[str, Any]] | None = None, max_new_tokens: int = 96) -> dict[str, Any]:
        context = {"character": character, "recent_events": recent_events or [],
                   "player_message": player_message, "valid_actions": valid_actions}
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "KONTEKS SANDEV LIFE:\\n" + json.dumps(context, ensure_ascii=False)}]
        inputs = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        device = next(self.model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                         pad_token_id=self.tokenizer.eos_token_id, use_cache=True)
        prompt_len = inputs["input_ids"].shape[1]
        raw = self.tokenizer.decode(output[0, prompt_len:], skip_special_tokens=True)
        return validate_response(raw, valid_actions)
