"""Trusted fact lookup for entity-focused follow-up questions.

Facts are supplied by the host game and must carry an approved provenance.
Conversation text and model guesses are never treated as authoritative facts.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

TRUSTED_FACT_SOURCES = {"engine_confirmed", "player_approved"}


class FactLookupError(ValueError):
    """Raised when the fact catalog has an invalid structure."""


def retrieve_entity_fact(
    reference_id: str | None,
    aspect: str | None,
    fact_catalog: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Retrieve one unambiguous trusted fact for an entity and question aspect."""
    if reference_id is not None and (not isinstance(reference_id, str) or not reference_id.strip()):
        raise FactLookupError("reference_id must be a non-empty string or None")
    if aspect is not None and (not isinstance(aspect, str) or not aspect.strip()):
        raise FactLookupError("aspect must be a non-empty string or None")
    if isinstance(fact_catalog, (str, bytes)) or not isinstance(fact_catalog, Sequence):
        raise FactLookupError("fact_catalog must be a sequence")

    if reference_id is None or aspect is None:
        return {"status": "not_attempted", "fact": None, "reason": "missing_reference_or_aspect"}

    matches: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in fact_catalog:
        if not isinstance(item, Mapping):
            raise FactLookupError("each fact catalog entry must be an object")
        if item.get("source") not in TRUSTED_FACT_SOURCES:
            continue
        fact_id = item.get("id")
        entity_id = item.get("entity_id")
        fact_aspect = item.get("aspect")
        if not isinstance(fact_id, str) or not fact_id.strip():
            raise FactLookupError("trusted facts need a non-empty id")
        if fact_id in seen_ids:
            raise FactLookupError("trusted fact ids must be unique")
        seen_ids.add(fact_id)
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise FactLookupError("trusted facts need a non-empty entity_id")
        if not isinstance(fact_aspect, str) or not fact_aspect.strip():
            raise FactLookupError("trusted facts need a non-empty aspect")
        if "value" not in item or item.get("value") is None:
            raise FactLookupError("trusted facts need a non-null value")
        if entity_id == reference_id and fact_aspect == aspect:
            matches.append({
                "id": fact_id,
                "entity_id": entity_id,
                "aspect": fact_aspect,
                "value": item["value"],
                "source": item["source"],
            })

    if not matches:
        return {"status": "not_found", "fact": None, "reason": "no_trusted_fact_for_entity_and_aspect"}
    if len(matches) > 1:
        return {"status": "ambiguous", "fact": None, "candidates": [item["id"] for item in matches],
                "reason": "multiple_trusted_facts_for_entity_and_aspect"}
    return {"status": "found", "fact": matches[0], "reason": "unique_trusted_entity_fact"}
