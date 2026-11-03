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
