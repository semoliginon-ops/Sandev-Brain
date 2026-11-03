"""Deterministic, NPC-scoped emotional state from trusted game events.

Emotions are presentation/context signals only. They never mutate authoritative
game state, and raw dialogue or model guesses cannot directly change them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
BASELINE = {
    "joy": 50,
    "fear": 0,
    "anger": 0,
    "sadness": 0,
    "trust": 50,
    "suspicion": 0,
}
# Fixed game-authored deltas. Values are intentionally small enough to allow
# emotional change over multiple events rather than one arbitrary jump.
EMOTION_DELTAS = {
    "helped_npc": {"joy": 8, "fear": -3, "trust": 8, "suspicion": -4},
    "saved_npc": {"joy": 12, "fear": -12, "trust": 12, "suspicion": -8},
    "gift_given": {"joy": 6, "trust": 3, "suspicion": -2},
    "kept_promise": {"joy": 5, "trust": 10, "suspicion": -8},
    "kind_dialogue": {"joy": 3, "trust": 2, "anger": -2},
    "harmed_npc": {"fear": 15, "anger": 12, "sadness": 5, "trust": -12, "suspicion": 8},
    "betrayed_npc": {"anger": 18, "sadness": 12, "trust": -18, "suspicion": 18},
    "broke_promise": {"anger": 10, "sadness": 6, "trust": -12, "suspicion": 12},
    "stole_from_npc": {"anger": 8, "trust": -8, "suspicion": 15},
    "insulted_npc": {"anger": 12, "sadness": 4, "trust": -5},
}


class NPCEmotionError(ValueError):
    """Raised when emotional state input is invalid."""


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
        raise NPCEmotionError(f"{name} must be a non-empty string of at most 100 characters")
    return value.strip()


def _mood(values: dict[str, int]) -> str:
    # Strong negative emotions take precedence over positive relationship signals.
    if values["fear"] >= 60:
        return "afraid"
    if values["anger"] >= 60:
        return "angry"
    if values["sadness"] >= 60:
        return "sad"
    if values["suspicion"] >= 60:
        return "suspicious"
    if values["joy"] >= 65 and values["trust"] >= 55:
        return "happy"
    if values["trust"] >= 75:
        return "trusting"
    return "calm"


class NPCEmotionLedger:
    """Persistent emotional state isolated to each (npc_id, player_id) pair."""

    def __init__(self, path: str | Path, *, decay_interval: int = 20):
        if isinstance(decay_interval, bool) or not isinstance(decay_interval, int) or decay_interval < 1:
            raise NPCEmotionError("decay_interval must be a positive integer")
        self.path = Path(path)
        self.decay_interval = decay_interval
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.states = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            self.states = {}

    @staticmethod
    def _key(npc_id: str, player_id: str) -> str:
        return json.dumps([_identity(npc_id, "npc_id"),
                           _identity(player_id, "player_id")], ensure_ascii=False)

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.states, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    @staticmethod
    def _clean_state(raw: Any) -> dict[str, int]:
        values = dict(BASELINE)
        if isinstance(raw, dict):
            for name in BASELINE:
                value = raw.get(name, BASELINE[name])
                if isinstance(value, int) and not isinstance(value, bool):
                    values[name] = max(0, min(100, value))
        return values

    def apply_event(
        self, npc_id: str, player_id: str, event_type: str, *,
        source: str, turn: int,
    ) -> dict[str, Any]:
        npc_id = _identity(npc_id, "npc_id")
        player_id = _identity(player_id, "player_id")
        if source not in TRUSTED_SOURCES:
            raise NPCEmotionError("source must be engine_confirmed or player_approved")
        if event_type not in EMOTION_DELTAS:
            raise NPCEmotionError("unknown emotional event type")
        if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
            raise NPCEmotionError("turn must be a non-negative integer")

        key = self._key(npc_id, player_id)
        record = self.states.get(key, {})
        values = self._clean_state(record.get("values", {}))
        previous_turn = record.get("turn", turn)
        if isinstance(previous_turn, bool) or not isinstance(previous_turn, int) or previous_turn < 0:
            previous_turn = turn
        self._decay(values, max(0, turn - previous_turn))
        for name, delta in EMOTION_DELTAS[event_type].items():
            values[name] = max(0, min(100, values[name] + delta))
        self.states[key] = {"values": values, "turn": max(turn, previous_turn)}
        self._save()
        return self.snapshot(npc_id, player_id, current_turn=turn)

    def _decay(self, values: dict[str, int], age: int) -> None:
        steps = age // self.decay_interval
        if steps <= 0:
            return
        for name, baseline in BASELINE.items():
            if values[name] > baseline:
                values[name] = max(baseline, values[name] - steps)
            elif values[name] < baseline:
                values[name] = min(baseline, values[name] + steps)

    def snapshot(
        self, npc_id: str, player_id: str, *,
        current_turn: int | None = None,
    ) -> dict[str, Any]:
        npc_id = _identity(npc_id, "npc_id")
        player_id = _identity(player_id, "player_id")
        if current_turn is not None and (
            isinstance(current_turn, bool) or not isinstance(current_turn, int) or current_turn < 0
        ):
            raise NPCEmotionError("current_turn must be a non-negative integer")
        record = self.states.get(self._key(npc_id, player_id), {})
        values = self._clean_state(record.get("values", {}))
        last_turn = record.get("turn", 0)
        if isinstance(last_turn, bool) or not isinstance(last_turn, int) or last_turn < 0:
            last_turn = 0
        if current_turn is not None:
            self._decay(values, max(0, current_turn - last_turn))
        return {
            "npc_id": npc_id,
            "player_id": player_id,
            "values": values,
            "mood": _mood(values),
            "updated_turn": last_turn,
        }
