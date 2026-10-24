"""Model-independent, verified memory ledger for SANDEV Brain.

Only game-engine-confirmed events or explicitly player-approved facts can enter
this ledger. Suggestions from a teacher/model are intentionally not accepted.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}


class MemoryLedger:
    def __init__(self, path: str | Path, *, max_items: int = 500):
        self.path = Path(path)
        self.max_items = max(1, int(max_items))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.items: list[dict[str, Any]] = loaded if isinstance(loaded, list) else []
        except (OSError, json.JSONDecodeError):
            self.items = []

    def _save(self) -> None:
        self.items = self.items[-self.max_items:]
        self.path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_event(
        self, event: str, *, source: str, turn: int, tags: Iterable[str] = (),
        importance: int = 1,
    ) -> dict[str, Any]:
        if source not in TRUSTED_SOURCES:
            raise ValueError("memory source must be engine_confirmed or player_approved")
        event = event.strip()
        if not event:
            raise ValueError("event cannot be empty")
        item = {
            "kind": "event",
            "event": event,
            "source": source,
            "turn": max(0, int(turn)),
            "tags": sorted({tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()}),
            "importance": max(0, min(3, int(importance))),
        }
        self.items.append(item)
        self._save()
        return item.copy()

    def remember_fact(
        self, key: str, value: Any, *, source: str, turn: int,
        tags: Iterable[str] = (),
    ) -> dict[str, Any]:
        if source not in TRUSTED_SOURCES:
            raise ValueError("memory source must be engine_confirmed or player_approved")
        key = key.strip()
        if not key:
            raise ValueError("fact key cannot be empty")
        # New verified value supersedes an older fact with the same key.
        self.items = [item for item in self.items
                      if not (item.get("kind") == "fact" and item.get("key") == key)]
        item = {
            "kind": "fact",
            "key": key,
            "value": value,
            "source": source,
            "turn": max(0, int(turn)),
            "tags": sorted({tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()}),
            "importance": 3,
        }
        self.items.append(item)
        self._save()
        return item.copy()

    def retrieve(self, *, tags: Iterable[str] = (), limit: int = 8) -> list[dict[str, Any]]:
        requested = {tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()}
        candidates = []
        for item in self.items:
            item_tags = set(item.get("tags", []))
            overlap = len(requested & item_tags)
            # If tags are provided, prioritize matching memories; still allow
            # durable facts with no tags to be found as a fallback.
            if requested and overlap == 0 and item_tags:
                continue
            candidates.append((overlap, int(item.get("importance", 0)), int(item.get("turn", 0)), item))
        candidates.sort(key=lambda row: (-row[0], -row[1], -row[2]))
        return [dict(row[3]) for row in candidates[:max(0, int(limit))]]

    def export(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self.items]
