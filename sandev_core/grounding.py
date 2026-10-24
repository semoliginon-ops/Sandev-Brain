"""Ground player-mentioned entities against names supplied by the game engine.

This module resolves references only; it does not infer an action or execute one.
Entity IDs and display names must come from the current trusted game snapshot.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from intent import normalize_text


class GroundingInputError(ValueError):
    """Raised when entity grounding inputs are malformed."""


def ground_entities(
    message: str,
    entities: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve exact entity-name mentions to current engine-provided entities.

    The longest matching alias wins when it uniquely identifies an entity.
    Mentions that tie across distinct entities are marked ambiguous. No entity
    is guessed from genre, action intent, or unrelated world state.
    """
    normalized_message = normalize_text(message)
    if not isinstance(entities, (list, tuple)):
        raise GroundingInputError("entities must be a list")
    if len(entities) > 500:
        raise GroundingInputError("entities exceeds the 500-item limit")

    seen_ids: set[str] = set()
    matches: list[dict[str, Any]] = []
    for index, raw in enumerate(entities):
        if not isinstance(raw, Mapping):
            raise GroundingInputError(f"entities[{index}] must be an object")
        entity_id = raw.get("id")
        name = raw.get("name")
        aliases = raw.get("aliases", [])
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise GroundingInputError(f"entities[{index}].id must be a non-empty string")
        if entity_id in seen_ids:
            raise GroundingInputError(f"duplicate entity id: {entity_id}")
        seen_ids.add(entity_id)
        if not isinstance(name, str) or not name.strip():
            raise GroundingInputError(f"entities[{index}].name must be a non-empty string")
        if not isinstance(aliases, (list, tuple)) or any(
            not isinstance(alias, str) or not alias.strip() for alias in aliases
        ):
            raise GroundingInputError(f"entities[{index}].aliases must be a list of non-empty strings")

        entity_matches = []
        for alias in (name, *aliases):
            normalized_alias = normalize_text(alias)
            if not normalized_alias:
                continue
            match = re.search(
                r"(?<!\w)" + re.escape(normalized_alias) + r"(?!\w)",
                normalized_message,
            )
            if match:
                entity_matches.append({
                    "entity_id": entity_id,
                    "entity_name": name,
                    "matched_alias": normalized_alias,
                    "start": match.start(),
                    "end": match.end(),
                    "length": len(normalized_alias),
                })
        if entity_matches:
            entity_matches.sort(key=lambda item: (-item["length"], item["start"], item["matched_alias"]))
            matches.append(entity_matches[0])

    if not matches:
        return {
            "status": "unresolved",
            "entity_id": None,
            "entity_name": None,
            "matched_alias": None,
            "candidates": [],
            "reason": "no_current_entity_name_match",
        }

    longest = max(item["length"] for item in matches)
    best = [item for item in matches if item["length"] == longest]
    distinct = {item["entity_id"] for item in best}
    if len(distinct) != 1:
        candidates = sorted(
            ({"entity_id": item["entity_id"], "entity_name": item["entity_name"]}
             for item in best),
            key=lambda item: (item["entity_id"], item["entity_name"]),
        )
        return {
            "status": "ambiguous",
            "entity_id": None,
            "entity_name": None,
            "matched_alias": None,
            "candidates": candidates,
            "reason": "multiple_entities_match_equally",
        }

    selected = sorted(best, key=lambda item: (item["start"], item["entity_id"]))[0]
    return {
        "status": "grounded",
        "entity_id": selected["entity_id"],
        "entity_name": selected["entity_name"],
        "matched_alias": selected["matched_alias"],
        "candidates": [{"entity_id": selected["entity_id"], "entity_name": selected["entity_name"]}],
        "reason": "matched_current_engine_entity_name",
    }
