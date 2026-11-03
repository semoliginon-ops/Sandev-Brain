"""Bounded, session-local dialogue history for SANDEV Brain.

Dialogue turns preserve conversational continuity but are not trusted facts.
They are intentionally separate from the provenance-checked MemoryLedger.
"""
from __future__ import annotations
from typing import Any

class DialogueHistoryError(ValueError):
    """Raised for invalid dialogue-history input."""

class DialogueHistory:
    def __init__(self, *, max_turns: int = 12, max_chars_per_message: int = 2000):
        for name, value in (("max_turns", max_turns), ("max_chars_per_message", max_chars_per_message)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise DialogueHistoryError(f"{name} must be a positive integer")
        self.max_turns = max_turns
        self.max_chars_per_message = max_chars_per_message
        self._turns: list[dict[str, Any]] = []

    def add(self, speaker: str, text: str, *, turn: int) -> dict[str, Any]:
        if speaker not in {"player", "npc"}:
            raise DialogueHistoryError("speaker must be player or npc")
        if not isinstance(text, str) or not text.strip():
            raise DialogueHistoryError("dialogue text must be a non-empty string")
        if len(text) > self.max_chars_per_message:
            raise DialogueHistoryError("dialogue text exceeds the configured character limit")
        if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
            raise DialogueHistoryError("turn must be a non-negative integer")
        if self._turns and turn < self._turns[-1]["turn"]:
            raise DialogueHistoryError("turn numbers must be non-decreasing")
        item = {"speaker": speaker, "text": text, "turn": turn, "trust": "unverified_dialogue"}
        self._turns.append(item)
        self._turns = self._turns[-self.max_turns:]
        return dict(item)

    def recent(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        if limit is None:
            limit = self.max_turns
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise DialogueHistoryError("limit must be a non-negative integer")
        return [dict(item) for item in self._turns[-limit:]] if limit else []

    def clear(self) -> None:
        self._turns.clear()

    def __len__(self) -> int:
        return len(self._turns)
