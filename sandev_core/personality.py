"""Deterministic, authored NPC voice profiles.

Profiles adjust presentation only. They never alter facts, intent, trust, or game state.
"""
from __future__ import annotations

from typing import Any

PERSONALITY_PROFILES = {
    "neutral": {"prefix": "", "suffix": ""},
    "friendly": {"prefix": "Dengan senang hati, ", "suffix": ""},
    "shy": {"prefix": "E-eh, ", "suffix": ""},
    "cold": {"prefix": "Dengar. ", "suffix": ""},
    "humorous": {"prefix": "Hehe, ", "suffix": " Lumayan, kan?"},
    "angry": {"prefix": "Hmph. ", "suffix": ""},
}


class PersonalityError(ValueError):
    """Raised when an NPC personality profile or response is invalid."""


def apply_personality_style(
    text: str,
    personality: str = "neutral",
    *,
    max_chars: int = 280,
) -> dict[str, Any]:
    """Apply one known authored voice profile without changing the response meaning."""
    if not isinstance(text, str) or not text.strip():
        raise PersonalityError("text must be a non-empty string")
    if not isinstance(personality, str) or personality not in PERSONALITY_PROFILES:
        raise PersonalityError("unsupported NPC personality")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise PersonalityError("max_chars must be a positive integer")

    profile = PERSONALITY_PROFILES[personality]
    styled = f'{profile["prefix"]}{text.strip()}{profile["suffix"]}'
    if len(styled) > max_chars:
        return {"status": "abstained", "text": None, "reason": "styled_response_too_long"}
    return {
        "status": "styled",
        "text": styled,
        "personality": personality,
        "source": "authored_personality_profile",
    }


EMOTION_CUES = {
    "afraid": "*suaranya bergetar* ",
    "angry": "*menjawab dengan nada marah* ",
    "sad": "*menunduk sedih* ",
    "suspicious": "*menatap dengan curiga* ",
    "happy": "*tersenyum hangat* ",
    "trusting": "*berbicara dengan akrab* ",
}


def apply_emotion_style(
    text: str,
    emotional_state: dict[str, Any] | None = None,
    *,
    max_chars: int = 280,
) -> dict[str, Any]:
    """Add a small authored delivery cue from a validated emotional snapshot.

    Emotional cues affect presentation only; they do not rewrite dialogue content.
    """
    if not isinstance(text, str) or not text.strip():
        raise PersonalityError("text must be a non-empty string")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise PersonalityError("max_chars must be a positive integer")
    if emotional_state is None:
        return {"status": "styled", "text": text.strip(), "mood": None,
                "source": "no_emotional_state"}
    if not isinstance(emotional_state, dict):
        raise PersonalityError("emotional_state must be an object or None")
    values = emotional_state.get("values")
    required = {"joy", "fear", "anger", "sadness", "trust", "suspicion"}
    if not isinstance(values, dict) or set(values) != required:
        raise PersonalityError("emotional_state.values must contain all six emotion values")
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise PersonalityError(f"emotional value {name} must be an integer from 0 to 100")

    # Re-derive mood from numeric values rather than trusting a supplied mood label.
    if values["fear"] >= 60:
        mood = "afraid"
    elif values["anger"] >= 60:
        mood = "angry"
    elif values["sadness"] >= 60:
        mood = "sad"
    elif values["suspicion"] >= 60:
        mood = "suspicious"
    elif values["joy"] >= 65 and values["trust"] >= 55:
        mood = "happy"
    elif values["trust"] >= 75:
        mood = "trusting"
    else:
        mood = "calm"

    cue = EMOTION_CUES.get(mood, "")
    styled = f"{cue}{text.strip()}"
    if len(styled) > max_chars:
        return {"status": "abstained", "text": None,
                "reason": "emotional_response_too_long", "mood": mood}
    return {"status": "styled", "text": styled, "mood": mood,
            "source": "authored_emotion_delivery_cue"}
