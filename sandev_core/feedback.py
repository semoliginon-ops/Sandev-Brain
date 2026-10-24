"""Outcome feedback from game-engine-confirmed action results.

The ledger is deliberately conservative: only confirmed engine outcomes are
accepted. Scores are advisory nudges, never world-state changes or guarantees.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from brain import ActionCandidate


class OutcomeLedger:
    def __init__(self, path: str | Path, *, max_items: int = 1000):
        self.path = Path(path)
        self.max_items = max(1, int(max_items))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = loaded if isinstance(loaded, list) else []
        except (OSError, json.JSONDecodeError):
            self.items = []

    @staticmethod
    def _tags(tags: Iterable[str]) -> list[str]:
        return sorted({tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()})

    def record_outcome(
        self, action_kind: str, *, success: bool, source: str, turn: int,
        context_tags: Iterable[str] = (),
    ) -> dict:
        if source != "engine_confirmed":
            raise ValueError("action outcome must be confirmed by the game engine")
        if not isinstance(action_kind, str) or not action_kind.strip():
            raise ValueError("action_kind cannot be empty")
        if not isinstance(success, bool):
            raise ValueError("success must be a boolean confirmed by the engine")
        item = {
            "action_kind": action_kind.strip(),
            "success": success,
            "source": source,
            "turn": max(0, int(turn)),
            "context_tags": self._tags(context_tags),
        }
        self.items.append(item)
        self.items = self.items[-self.max_items:]
        self.path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")
        return dict(item)

    def adjustment_for(self, action_kind: str, *, context_tags: Iterable[str] = (),
                       max_adjustment: float = 10.0, min_samples: int = 5) -> float:
        """Return a bounded, smoothed score nudge for an exact context.

        Beta(1,1) smoothing avoids treating one success or failure as certainty.
        The nudge fades linearly until min_samples matching observations exist.
        """
        tags = self._tags(context_tags)
        matching = [item for item in self.items
                    if item.get("action_kind") == action_kind
                    and item.get("context_tags", []) == tags
                    and item.get("source") == "engine_confirmed"
                    and isinstance(item.get("success"), bool)]
        count = len(matching)
        if count == 0:
            return 0.0
        successes = sum(1 for item in matching if item["success"])
        rate = (successes + 1.0) / (count + 2.0)
        confidence = min(1.0, count / max(1, int(min_samples)))
        return max(-abs(max_adjustment), min(abs(max_adjustment),
                   (rate - 0.5) * 2.0 * abs(max_adjustment) * confidence))

    def adjustments_for(self, candidates: Sequence[ActionCandidate], *,
                        context_tags: Iterable[str] = (), max_adjustment: float = 10.0,
                        min_samples: int = 5) -> dict[str, float]:
        tags = self._tags(context_tags)
        return {
            candidate.action_id: self.adjustment_for(
                candidate.kind, context_tags=tags,
                max_adjustment=max_adjustment, min_samples=min_samples,
            )
            for candidate in candidates
        }
