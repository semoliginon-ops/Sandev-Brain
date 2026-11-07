"""Validated semantic-frame contract for SANDEV Brain dialogue.

This module does not parse raw text or claim general language understanding.
It converts a conservative interpretation envelope into a stable semantic
representation for downstream dialogue/reasoning components. Uncertain,
unsafe, or unsupported interpretations abstain.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


class SemanticFrameError(ValueError):
    """Raised for malformed interpretation or trusted profile metadata."""


_INTENT_TO_FRAME = {
    "greeting": ("greeting", "general"),
    "thanks": ("gratitude", "general"),
    "danger": ("concern", "danger"),
    "heal_request": ("concern", "health"),
    "comfort": ("encourage", "general"),
    "help_request": ("encourage", "quest"),
}

_SPEECH_ACTS = {"command", "question", "statement", "mention", "cancellation", "unclear"}
_TEMPORAL_SCOPES = {"immediate", "past_or_recounted", "future_intended", "unspecified"}
_NEGATION_STATES = {"detected", "not_detected", "uncertain"}
_TARGET_STATES = {"unresolved", "resolved", "not_applicable"}


def build_semantic_frame(
    interpretation: Mapping[str, Any],
    *,
    speaker_id: str,
    turn: int,
    personality: str = "neutral",
    relationship_score: int = 0,
) -> dict[str, Any]:
    """Convert a validated interpretation into a bounded semantic frame.

    Supports the legacy {status, intent} input and the richer interpret_message
    envelope. For rich envelopes, only clear, non-negated, non-question,
    non-cancellation interpretations can become dialogue frames. This is a
    representation/validation layer, not a raw-language parser or generator.
    """
    if not isinstance(interpretation, Mapping):
        raise SemanticFrameError("interpretation must be an object")
    if not isinstance(speaker_id, str) or not speaker_id.strip():
        raise SemanticFrameError("speaker_id must be a non-empty string")
    if isinstance(turn, bool) or not isinstance(turn, int) or turn < 0:
        raise SemanticFrameError("turn must be a non-negative integer")
    if not isinstance(personality, str) or personality not in {"warm", "neutral", "dry"}:
        raise SemanticFrameError("unsupported personality tone")
    if (isinstance(relationship_score, bool) or not isinstance(relationship_score, int)
            or not -100 <= relationship_score <= 100):
        raise SemanticFrameError("relationship_score must be an integer from -100 to 100")

    rich_envelope = "schema_version" in interpretation
    if rich_envelope and interpretation.get("schema_version") != "1.0":
        raise SemanticFrameError("unsupported interpretation schema_version")

    status = interpretation.get("intent_status", interpretation.get("status"))
    intent = interpretation.get("intent")
    if status != "matched":
        return {"status": "no_frame", "reason": "intent_not_confidently_matched"}
    if not isinstance(intent, str) or not intent.strip():
        raise SemanticFrameError("matched interpretation needs a non-empty intent")

    if rich_envelope:
        speech_act = interpretation.get("speech_act")
        temporal_scope = interpretation.get("temporal_scope")
        negation = interpretation.get("negation")
        target_grounding = interpretation.get("target_grounding")
        needs_clarification = interpretation.get("needs_clarification")
        execution_allowed = interpretation.get("execution_allowed")
        confidence = interpretation.get("confidence")
        game_id = interpretation.get("game_id", "unspecified")

        if speech_act not in _SPEECH_ACTS:
            raise SemanticFrameError("unsupported speech_act")
        if temporal_scope not in _TEMPORAL_SCOPES:
            raise SemanticFrameError("unsupported temporal_scope")
        if negation not in _NEGATION_STATES:
            raise SemanticFrameError("unsupported negation state")
        if target_grounding not in _TARGET_STATES:
            raise SemanticFrameError("unsupported target_grounding")
        if not isinstance(needs_clarification, bool):
            raise SemanticFrameError("needs_clarification must be a boolean")
        if execution_allowed is not False:
            raise SemanticFrameError("semantic dialogue frames must never authorize execution")
        if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not math.isfinite(float(confidence)) or not 0 <= confidence <= 1):
            raise SemanticFrameError("confidence must be a finite number from 0 to 1")
        if not isinstance(game_id, str):
            raise SemanticFrameError("game_id must be a string")

        if (needs_clarification or speech_act in {"question", "command", "mention", "cancellation", "unclear"}
                or temporal_scope in {"past_or_recounted", "future_intended"}
                or negation != "not_detected"):
            return {
                "status": "no_frame",
                "reason": "interpretation_requires_clarification_or_is_not_a_clear_dialogue_act",
            }
    else:
        # Legacy callers have only a matched intent label; preserve their
        # existing behavior while making the weaker evidence explicit.
        speech_act = "statement"
        temporal_scope = "unspecified"
        negation = "not_detected"
        target_grounding = "not_applicable"
        confidence = None
        game_id = "unspecified"

    mapped = _INTENT_TO_FRAME.get(intent)
    if mapped is None:
        return {"status": "no_frame", "reason": "intent_has_no_dialogue_frame"}
    frame_speech_act, topic = mapped
    relationship = (
        "close" if relationship_score >= 25
        else "strained" if relationship_score <= -25
        else "neutral"
    )
    frame = {
        "speaker_id": speaker_id,
        "turn": turn,
        "intent": intent,
        "speech_act": frame_speech_act,
        "source_speech_act": speech_act,
        "temporal_scope": temporal_scope,
        "negation": negation,
        "target_grounding": target_grounding,
        "tone": personality,
        "topic": topic,
        "relationship": relationship,
        "game_id": game_id,
    }
    if confidence is not None:
        frame["confidence"] = float(confidence)

    return {
        "status": "frame_ready",
        "frame": frame,
        "source": "validated_interpretation_and_trusted_profile" if rich_envelope
                  else "validated_intent_and_trusted_profile_legacy",
        "raw_player_text_used_as_slot": False,
        "execution_allowed": False,
    }
