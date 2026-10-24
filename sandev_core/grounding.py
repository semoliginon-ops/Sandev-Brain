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


def resolve_context_reference(
    message: str,
    entities: Sequence[Mapping[str, Any]],
    *,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a small set of references only from explicit engine context.

    Supported:
    - "dia/dirinya" when context.focus_entity_id names one current entity.
    - "musuh di belakangnya" when focus_entity_id exists and exactly one
      entity is explicitly marked is_hostile=True with relations_to[focus_id]
      equal to "behind".

    The engine must provide focus_entity_id and relation metadata. This helper
    does not infer spatial relationships from coordinates or guess a focus.
    """
    normalized = normalize_text(message)
    if not isinstance(entities, (list, tuple)):
        raise GroundingInputError("entities must be a list")
    if context is not None and not isinstance(context, Mapping):
        raise GroundingInputError("context must be an object")
    if context is None:
        context = {}

    pronoun_reference = bool(re.search(r"\b(dia|dirinya|nya)\b", normalized))
    behind_enemy_reference = bool(
        re.search(r"\bmusuh di belakangnya\b", normalized)
        or re.search(r"\bmusuh belakangnya\b", normalized)
    )
    if not pronoun_reference and not behind_enemy_reference:
        return {
            "status": "unresolved",
            "entity_id": None,
            "entity_name": None,
            "matched_alias": None,
            "candidates": [],
            "reason": "no_supported_context_reference",
        }

    focus_id = context.get("focus_entity_id")
    by_id = {
        item.get("id"): item
        for item in entities
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }
    if not isinstance(focus_id, str) or focus_id not in by_id:
        return {
            "status": "unresolved",
            "entity_id": None,
            "entity_name": None,
            "matched_alias": None,
            "candidates": [],
            "reason": "focus_entity_not_grounded_in_current_context",
        }

    if behind_enemy_reference:
        candidates = []
        for item in entities:
            if not isinstance(item, Mapping) or item.get("is_hostile") is not True:
                continue
            relations = item.get("relations_to", {})
            if isinstance(relations, Mapping) and relations.get(focus_id) == "behind":
                if isinstance(item.get("id"), str) and isinstance(item.get("name"), str):
                    candidates.append({"entity_id": item["id"], "entity_name": item["name"]})
        unique = {item["entity_id"]: item for item in candidates}
        candidates = sorted(unique.values(), key=lambda item: (item["entity_id"], item["entity_name"]))
        if len(candidates) == 1:
            selected = candidates[0]
            return {
                "status": "grounded",
                "entity_id": selected["entity_id"],
                "entity_name": selected["entity_name"],
                "matched_alias": "musuh di belakangnya",
                "candidates": candidates,
                "reason": "unique_engine_relation_to_focus_entity",
            }
        return {
            "status": "ambiguous" if candidates else "unresolved",
            "entity_id": None,
            "entity_name": None,
            "matched_alias": None,
            "candidates": candidates,
            "reason": "multiple_hostiles_behind_focus" if candidates else "no_engine_marked_hostile_behind_focus",
        }

    selected = by_id[focus_id]
    if not isinstance(selected.get("name"), str) or not selected["name"].strip():
        raise GroundingInputError("focus entity must have a non-empty name")
    return {
        "status": "grounded",
        "entity_id": focus_id,
        "entity_name": selected["name"],
        "matched_alias": "dia",
        "candidates": [{"entity_id": focus_id, "entity_name": selected["name"]}],
        "reason": "explicit_focus_entity_from_current_context",
    }
