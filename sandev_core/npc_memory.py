"""NPC-scoped verified memories and relationship progression.

Each record is isolated to one (npc_id, player_id) pair. Raw dialogue and
model-generated guesses are never accepted as persistent memories or events.
This module stores game-authored event labels, not inferred narrative claims.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
RELATIONSHIP_DELTAS = {
    "helped_npc": 8,
    "saved_npc": 15,
    "gift_given": 4,
    "kept_promise": 10,
    "kind_dialogue": 2,
    "harmed_npc": -15,
    "betrayed_npc": -20,
    "broke_promise": -12,
    "stole_from_npc": -10,
    "insulted_npc": -4,
}


class NPCMemoryError(ValueError):
    """Raised when NPC memory input is invalid."""


def _identity(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NPCMemoryError(f"{name} must be a non-empty string")
    value = value.strip()
    if len(value) > 100:
        raise NPCMemoryError(f"{name} must be at most 100 characters")
    return value


class NPCMemoryLedger:
    """Bounded persistent memory, strictly scoped to an NPC and player pair."""

    def __init__(self, path: str | Path, *, max_items: int = 500):
        self.path = Path(path)
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise NPCMemoryError("max_items must be a positive integer")
        self.max_items = max_items
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = loaded if isinstance(loaded, list) else []
        except (OSError, json.JSONDecodeError):
            self.items = []

    def _save(self) -> None:
        self.items = self.items[-self.max_items:]
        self.path.write_text(
            json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record_event(
        self, npc_id: str, player_id: str, event: str, *,
        source: str, turn: int, importance: int = 1,
        tags: Iterable[str] = (),
    ) -> dict[str, Any]:
        npc_id = _identity(npc_id, "npc_id")
        player_id = _identity(player_id, "player_id")
        if source not in TRUSTED_SOURCES:
            raise NPCMemoryError("source must be engine_confirmed or player_approved")
        if not isinstance(event, str) or not event.strip():
            raise NPCMemoryError("event must be a non-empty string")
        if len(event.strip()) > 500:
            raise NPCMemoryError("event must be at most 500 characters")
        if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
            raise NPCMemoryError("turn must be a non-negative integer")
        if isinstance(importance, bool) or not isinstance(importance, int):
            raise NPCMemoryError("importance must be an integer")
        safe_tags = sorted({
            tag.strip() for tag in tags
            if isinstance(tag, str) and tag.strip()
        })
        item = {
            "kind": "event", "npc_id": npc_id, "player_id": player_id,
            "event": event.strip(), "source": source, "turn": turn,
            "importance": max(0, min(3, importance)), "tags": safe_tags,
        }
        self.items.append(item)
        self._save()
        return dict(item)

    def remember_fact(
        self, npc_id: str, player_id: str, key: str, value: Any, *,
        source: str, turn: int, tags: Iterable[str] = (),
    ) -> dict[str, Any]:
        npc_id = _identity(npc_id, "npc_id")
        player_id = _identity(player_id, "player_id")
        if source not in TRUSTED_SOURCES:
            raise NPCMemoryError("source must be engine_confirmed or player_approved")
        if not isinstance(key, str) or not key.strip():
            raise NPCMemoryError("key must be a non-empty string")
        if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
            raise NPCMemoryError("turn must be a non-negative integer")
        try:
            safe_value = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError, OverflowError) as exc:
            raise NPCMemoryError("value must be finite JSON-compatible data") from exc
        self.items = [
            item for item in self.items
            if not (
                item.get("kind") == "fact"
                and item.get("npc_id") == npc_id
                and item.get("player_id") == player_id
                and item.get("key") == key.strip()
            )
        ]
        item = {
            "kind": "fact", "npc_id": npc_id, "player_id": player_id,
            "key": key.strip(), "value": safe_value, "source": source,
            "turn": turn, "importance": 3,
            "tags": sorted({tag.strip() for tag in tags
                            if isinstance(tag, str) and tag.strip()}),
        }
        self.items.append(item)
        self._save()
        return dict(item)

    def retrieve(
        self, npc_id: str, player_id: str, *,
        tags: Iterable[str] = (), limit: int = 8,
    ) -> list[dict[str, Any]]:
        npc_id = _identity(npc_id, "npc_id")
        player_id = _identity(player_id, "player_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise NPCMemoryError("limit must be a non-negative integer")
        requested = {tag.strip() for tag in tags
                     if isinstance(tag, str) and tag.strip()}
        candidates = []
        for item in self.items:
            if item.get("npc_id") != npc_id or item.get("player_id") != player_id:
                continue
            if item.get("source") not in TRUSTED_SOURCES:
                continue
            item_tags = set(item.get("tags", []))
            overlap = len(requested & item_tags)
            if requested and overlap == 0 and item_tags:
                continue
            candidates.append((overlap, int(item.get("importance", 0)),
                               int(item.get("turn", 0)), item))
        candidates.sort(key=lambda row: (-row[0], -row[1], -row[2]))
        return [dict(row[3]) for row in candidates[:limit]]


class RelationshipLedger:
    """Deterministic relationship scores from a fixed set of trusted game events."""

    def __init__(self, path: str | Path, *, max_score: int = 100):
        if isinstance(max_score, bool) or not isinstance(max_score, int) or max_score < 1:
            raise NPCMemoryError("max_score must be a positive integer")
        self.path = Path(path)
        self.max_score = max_score
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.scores = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            self.scores = {}

    @staticmethod
    def _key(npc_id: str, player_id: str) -> str:
        return json.dumps([_identity(npc_id, "npc_id"),
                           _identity(player_id, "player_id")], ensure_ascii=False)

    def apply_event(
        self, npc_id: str, player_id: str, event_type: str, *,
        source: str,
    ) -> dict[str, Any]:
        if source not in TRUSTED_SOURCES:
            raise NPCMemoryError("relationship source must be engine_confirmed or player_approved")
        if event_type not in RELATIONSHIP_DELTAS:
            raise NPCMemoryError("unknown relationship event type")
        key = self._key(npc_id, player_id)
        old_score = self.scores.get(key, 0)
        if isinstance(old_score, bool) or not isinstance(old_score, int):
            old_score = 0
        new_score = max(-self.max_score, min(self.max_score,
                                             old_score + RELATIONSHIP_DELTAS[event_type]))
        self.scores[key] = new_score
        self.path.write_text(
            json.dumps(self.scores, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return self.snapshot(npc_id, player_id)

    def snapshot(self, npc_id: str, player_id: str) -> dict[str, Any]:
        score = self.scores.get(self._key(npc_id, player_id), 0)
        if isinstance(score, bool) or not isinstance(score, int):
            score = 0
        score = max(-self.max_score, min(self.max_score, score))
        if score <= -60:
            label = "hostile"
        elif score <= -20:
            label = "unfriendly"
        elif score < 20:
            label = "neutral"
        elif score < 60:
            label = "friendly"
        else:
            label = "trusted"
        return {"npc_id": _identity(npc_id, "npc_id"),
                "player_id": _identity(player_id, "player_id"),
                "score": score, "label": label}
