"""Map validated intent and trusted companion profile data to safe dialogue frames.

This adapter does not parse raw text. It only accepts a matched intent result and
uses explicit, bounded mappings; unsupported intents abstain.
"""
from __future__ import annotations

from typing import Any, Mapping


class SemanticFrameError(ValueError):
    """Raised for malformed validated interpretation or profile metadata."""


_INTENT_TO_FRAME = {
    "greeting": ("greeting", "general"),
    "thanks": ("gratitude", "general"),
    "danger": ("concern", "danger"),
    "heal_request": ("concern", "health"),
    "comfort": ("encourage", "general"),
    "help_request": ("encourage", "quest"),
}


def build_semantic_frame(
    interpretation: Mapping[str, Any],
    *,
    speaker_id: str,
    turn: int,
    personality: str = "neutral",
    relationship_score: int = 0,
) -> dict[str, Any]:
    """Create a composer frame only from a confidently matched intent.

    Action intents are deliberately unsupported here: they belong to the engine
    action path, not conversational sentence composition.
    """
    if not isinstance(interpretation, Mapping):
        raise SemanticFrameError("interpretation must be an object")
    if not isinstance(speaker_id, str) or not speaker_id.strip():
        raise SemanticFrameError("speaker_id must be a non-empty string")
    if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
        raise SemanticFrameError("turn must be a non-negative integer")
    if personality not in {"warm", "neutral", "dry"}:
        raise SemanticFrameError("unsupported personality tone")
    if (isinstance(relationship_score, bool) or not isinstance(relationship_score, int)
            or not -100 <= relationship_score <= 100):
        raise SemanticFrameError("relationship_score must be an integer from -100 to 100")

    if interpretation.get("status") != "matched":
        return {"status": "no_frame", "reason": "intent_not_confidently_matched"}
    intent = interpretation.get("intent")
    mapped = _INTENT_TO_FRAME.get(intent)
    if mapped is None:
        return {"status": "no_frame", "reason": "intent_has_no_dialogue_frame"}
    speech_act, topic = mapped
    relationship = (
        "close" if relationship_score >= 25
        else "strained" if relationship_score <= -25
        else "neutral"
    )
    return {
        "status": "frame_ready",
        "frame": {
            "speaker_id": speaker_id,
            "turn": turn,
            "speech_act": speech_act,
            "tone": personality,
            "topic": topic,
            "relationship": relationship,
        },
        "source": "validated_intent_and_trusted_profile",
        "raw_player_text_used_as_slot": False,
    }
