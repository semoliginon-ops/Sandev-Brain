"""Companion memory, relationship, and authored personality response layer.

This is deterministic integration glue. It selects authored lines; it does not
generate open-ended dialogue or infer facts from untrusted player messages.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from context import build_context
from intent import classify_intent
from language import select_response
from memory import MemoryLedger


class CompanionError(ValueError):
    """Raised for invalid companion profile or interaction data."""


class CompanionRuntime:
    def __init__(
        self,
        memory_path: str | Path,
        *,
        companion_id: str,
        personality: str,
        personality_tags: Sequence[str] = (),
    ) -> None:
        if not isinstance(companion_id, str) or not companion_id.strip():
            raise CompanionError("companion_id must be a non-empty string")
        if not isinstance(personality, str) or not personality.strip():
            raise CompanionError("personality must be a non-empty string")
        if isinstance(personality_tags, str) or any(not isinstance(tag, str) for tag in personality_tags):
            raise CompanionError("personality_tags must be a sequence of strings")
        self.companion_id = companion_id
        self.personality = personality.strip()
        self.personality_tags = sorted({tag.strip() for tag in personality_tags if tag.strip()})
        self.memory = MemoryLedger(memory_path)

    def _relationship_score(self) -> int:
        for item in self.memory.retrieve(tags=["relationship"], limit=50):
            if item.get("kind") == "fact" and item.get("key") == "relationship_score":
                value = item.get("value")
                if isinstance(value, int) and not isinstance(value, bool):
                    return max(-100, min(100, value))
        return 0

    def record_confirmed_interaction(
        self, event: str, *, source: str, turn: int, relationship_delta: int = 0,
        tags: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Record an engine-confirmed interaction and bounded relationship change."""
        if source != "engine_confirmed":
            raise CompanionError("relationship changes require engine_confirmed source")
        if isinstance(relationship_delta, bool) or not isinstance(relationship_delta, int):
            raise CompanionError("relationship_delta must be an integer")
        if not -5 <= relationship_delta <= 5:
            raise CompanionError("relationship_delta must be between -5 and 5")
        item = self.memory.record_event(
            event, source=source, turn=turn, tags=[*tags, "relationship"], importance=2
        )
        score = max(-100, min(100, self._relationship_score() + relationship_delta))
        self.memory.remember_fact(
            "relationship_score", score, source="engine_confirmed",
            turn=turn, tags=["relationship"],
        )
        return {"event": item, "relationship_score": score}

    def remember_player_approved_fact(
        self, key: str, value: Any, *, source: str, turn: int,
        tags: Sequence[str] = (),
    ) -> dict[str, Any]:
        if source != "player_approved":
            raise CompanionError("personal facts require explicit player approval")
        return self.memory.remember_fact(
            key, value, source=source, turn=turn, tags=tags
        )

    def respond(
        self,
        snapshot: Mapping[str, Any],
        player_message: str,
        response_patterns: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        context = build_context(
            snapshot, actor_id=self.companion_id, player_message=player_message,
            memory_ledger=self.memory, memory_tags=["relationship"],
        )
        interpretation = classify_intent(
            player_message, context={"game_id": context.get("game_id", "unspecified")}
        )
        if interpretation.get("status") != "matched":
            return {
                "status": "no_response",
                "text": None,
                "interpretation": interpretation,
                "reason": "intent_not_confidently_matched",
                "companion": self.companion_id,
            }

        compatible = []
        for pattern in response_patterns:
            if not isinstance(pattern, Mapping):
                raise CompanionError("each response pattern must be an object")
            required_personality = pattern.get("personality")
            if required_personality is not None and required_personality != self.personality:
                continue
            compatible.append(pattern)
        response = select_response(
            context, compatible, intent=interpretation["intent"]
        )
        if response.get("status") == "no_matching_response":
            return {
                "status": "no_response", "text": None,
                "interpretation": interpretation, "response": response,
                "reason": "no_personality_and_memory_match",
                "companion": self.companion_id,
            }
        return {
            "status": "response_selected",
            "text": response["text"],
            "interpretation": interpretation,
            "response": response,
            "companion": self.companion_id,
            "personality": self.personality,
            "relationship_score": self._relationship_score(),
            "memory_count": len(self.memory.export()),
            "reason": "authored_personality_line_selected_with_verified_memory",
        }
