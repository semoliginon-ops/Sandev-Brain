"""Bounded context assembly for future SANDEV Brain language and decision modules.

This module packages authoritative game state and provenance-checked context. It
does not interpret player language, generate dialogue, execute actions, or call a model.
"""
from __future__ import annotations

import json
import math
from typing import Any, Iterable, Mapping

TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
DEFAULT_MAX_MESSAGE_CHARS = 2000
DEFAULT_MAX_STATE_BYTES = 24_000
DEFAULT_MAX_CONTEXT_BYTES = 48_000


class ContextInputError(ValueError):
    """Raised when context input is malformed or exceeds its configured budget."""


def _json_copy(value: Any, name: str) -> Any:
    """Return a JSON-safe deep copy, rejecting non-finite numbers and custom objects."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        return json.loads(encoded)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContextInputError(f"{name} must contain only finite JSON-compatible values") from exc


def _tags(values: Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        raise ContextInputError("memory_tags must be a list of strings")
    try:
        result = sorted({item.strip() for item in values if isinstance(item, str) and item.strip()})
    except TypeError as exc:
        raise ContextInputError("memory_tags must be an iterable of strings") from exc
    return result


def build_context(
    snapshot: Mapping[str, Any],
    *,
    actor_id: str,
    player_message: str = "",
    memory_ledger: Any = None,
    memory_tags: Iterable[str] = (),
    recent_events: Iterable[Mapping[str, Any]] = (),
    max_memories: int = 8,
    max_recent_events: int = 8,
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS,
    max_state_bytes: int = DEFAULT_MAX_STATE_BYTES,
    max_context_bytes: int = DEFAULT_MAX_CONTEXT_BYTES,
) -> dict[str, Any]:
    """Build a bounded context packet from current game input and trusted history.

    The raw player message is preserved verbatim (within the explicit character
    limit); it is not treated as a verified fact. Only events/facts with a
    recognized provenance are included from memory. Current state remains the
    host engine's responsibility and is not inferred from memory.
    """
    if not isinstance(snapshot, Mapping):
        raise ContextInputError("snapshot must be an object")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise ContextInputError("actor_id must be a non-empty string")
    if not isinstance(player_message, str):
        raise ContextInputError("player_message must be a string")
    if max_message_chars < 0 or len(player_message) > max_message_chars:
        raise ContextInputError("player_message exceeds the configured character limit")
    for name, value in (("max_memories", max_memories), ("max_recent_events", max_recent_events),
                        ("max_state_bytes", max_state_bytes), ("max_context_bytes", max_context_bytes)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ContextInputError(f"{name} must be a non-negative integer")

    state = _json_copy(snapshot.get("state", {}), "state")
    if not isinstance(state, dict):
        raise ContextInputError("snapshot.state must be an object")
    state_size = len(json.dumps(state, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    if state_size > max_state_bytes:
        raise ContextInputError("snapshot.state exceeds the configured byte limit")

    goals = _json_copy(snapshot.get("goals", []), "goals")
    if not isinstance(goals, list):
        raise ContextInputError("snapshot.goals must be a list")

    events: list[dict[str, Any]] = []
    if isinstance(recent_events, (str, bytes)):
        raise ContextInputError("recent_events must be an iterable of event objects")
    try:
        for item in recent_events:
            if len(events) >= max_recent_events:
                break
            if not isinstance(item, Mapping):
                raise ContextInputError("each recent event must be an object")
            source = item.get("source")
            event = item.get("event")
            if source not in TRUSTED_SOURCES or not isinstance(event, str) or not event.strip():
                continue
            safe_item = _json_copy(dict(item), "recent event")
            events.append(safe_item)
    except TypeError as exc:
        raise ContextInputError("recent_events must be iterable") from exc

    memories: list[dict[str, Any]] = []
    tags = _tags(memory_tags)
    if memory_ledger is not None:
        retrieve = getattr(memory_ledger, "retrieve", None)
        if not callable(retrieve):
            raise ContextInputError("memory_ledger must provide retrieve(tags=..., limit=...)")
        for item in retrieve(tags=tags, limit=max_memories):
            if not isinstance(item, Mapping) or item.get("source") not in TRUSTED_SOURCES:
                continue
            memories.append(_json_copy(dict(item), "memory item"))

    packet = {
        "context_version": "1.0",
        "game_id": snapshot.get("game_id", "unspecified"),
        "actor_id": actor_id,
        "state_version": snapshot.get("state_version"),
        "state": state,
        "goals": goals,
        "player_message": player_message,
        "player_message_status": "raw_uninterpreted_input",
        "recent_events": events,
        "memories": memories,
        "memory_tags_used": tags,
    }
    packet = _json_copy(packet, "context packet")
    packet_size = len(json.dumps(packet, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    if packet_size > max_context_bytes:
        raise ContextInputError("assembled context exceeds the configured byte limit")
    return packet
