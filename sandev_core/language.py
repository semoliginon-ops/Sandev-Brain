"""Contextual response selection baseline for SANDEV Brain.

This is a transparent, model-independent response selector, not open-ended language
generation. It ranks authored response patterns against explicit intent/context tags.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence


class LanguageInputError(ValueError):
    """Raised when response-selection input is malformed."""


def _string_set(value: Any, field: str) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str) or not isinstance(value, (list, tuple, set)):
        raise LanguageInputError(f"{field} must be a list of strings")
    if any(not isinstance(item, str) for item in value):
        raise LanguageInputError(f"{field} must contain only strings")
    return {item.strip() for item in value if item.strip()}


def select_response(
    context: Mapping[str, Any],
    patterns: Sequence[Mapping[str, Any]],
    *,
    intent: str,
    max_chars: int = 280,
) -> dict[str, Any]:
    """Select a curated line using explicit intent and current context tags.

    A caller must supply an intent from its own validated interpretation layer.
    This function deliberately does not infer intent from raw player text.
    """
    if not isinstance(context, Mapping):
        raise LanguageInputError("context must be an object")
    if not isinstance(intent, str) or not intent.strip():
        raise LanguageInputError("intent must be a non-empty validated label")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise LanguageInputError("max_chars must be a positive integer")

    if context.get("context_version") != "1.0":
        raise LanguageInputError("unsupported context version")
    message_status = context.get("player_message_status")
    if message_status != "raw_uninterpreted_input":
        raise LanguageInputError("context must explicitly mark raw player input as uninterpreted")

    state = context.get("state", {})
    if not isinstance(state, Mapping):
        raise LanguageInputError("context.state must be an object")
    game_id = context.get("game_id", "unspecified")
    if not isinstance(game_id, str):
        raise LanguageInputError("context.game_id must be a string")

    needs: set[str] = set()
    for key, value in state.items():
        if isinstance(key, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
            if 0 <= value <= 100 and value >= 70:
                needs.add(key)
    event_tags: set[str] = set()
    for event in context.get("recent_events", []):
        if isinstance(event, Mapping) and event.get("source") in {"engine_confirmed", "player_approved"}:
            event_tags |= _string_set(event.get("tags", []), "event.tags")
    memory_tags: set[str] = set()
    for memory in context.get("memories", []):
        if isinstance(memory, Mapping) and memory.get("source") in {"engine_confirmed", "player_approved"}:
            memory_tags |= _string_set(memory.get("tags", []), "memory.tags")

    scored: list[tuple[float, str, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    for pattern in patterns:
        if not isinstance(pattern, Mapping):
            raise LanguageInputError("each response pattern must be an object")
        pattern_id = pattern.get("id")
        text = pattern.get("text")
        pattern_intent = pattern.get("intent")
        if not isinstance(pattern_id, str) or not pattern_id.strip():
            raise LanguageInputError("each pattern needs a non-empty id")
        if pattern_id in seen_ids:
            raise LanguageInputError(f"duplicate pattern id: {pattern_id}")
        seen_ids.add(pattern_id)
        if not isinstance(text, str) or not text.strip() or len(text) > max_chars:
            continue
        if not isinstance(pattern_intent, str) or pattern_intent != intent:
            continue
        games = _string_set(pattern.get("games", []), "pattern.games")
        if games and game_id not in games:
            continue
        required = _string_set(pattern.get("required_tags", []), "pattern.required_tags")
        available = event_tags | memory_tags
        if not required.issubset(available):
            continue
        if not _string_set(pattern.get("forbidden_needs", []), "pattern.forbidden_needs").isdisjoint(needs):
            continue
        response_tags = _string_set(pattern.get("tags", []), "pattern.tags")
        overlap = len(response_tags & (event_tags | memory_tags))
        priority = pattern.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, (int, float)):
            raise LanguageInputError("pattern.priority must be numeric")
        scored.append((float(priority) + overlap * 0.01, pattern_id, {
            "id": pattern_id, "text": text, "intent": intent, "game_id": game_id,
            "source": "curated_pattern", "selection_reason": "intent_and_context_match",
        }))

    if not scored:
        return {
            "status": "no_matching_response",
            "text": None,
            "intent": intent,
            "game_id": game_id,
            "source": None,
        }
    # Stable tie-break prevents arbitrary changes between identical contexts.
    return sorted(scored, key=lambda item: (-item[0], item[1]))[0][2]
