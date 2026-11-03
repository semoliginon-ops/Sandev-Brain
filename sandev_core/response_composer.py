"""Deterministic composition of a reply from one trusted game fact.

This is a small response-composition layer, not open-ended language generation.
It never turns dialogue history or model guesses into facts.
"""
from __future__ import annotations

from typing import Any, Mapping

TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
DEFAULT_TEMPLATES = {
    "family": "Yang kutahu, {fact}",
    "location": "Setahuku, {fact}",
    "motive": "Alasannya, {fact}",
    "identity": "Yang bisa kupastikan, {fact}",
    "general_details": "Yang kutahu, {fact}",
}


class ResponseComposerError(ValueError):
    """Raised when response-composition input is malformed."""


def compose_fact_response(
    reference_id: str | None,
    aspect: str | None,
    fact_lookup: Mapping[str, Any],
    *,
    templates: Mapping[str, str] | None = None,
    max_chars: int = 280,
) -> dict[str, Any]:
    """Compose a concise authored-template reply from one trusted retrieved fact.

    The fact must match the resolved entity and aspect exactly. Unsupported,
    missing, ambiguous, or untrusted data produces an explicit abstention.
    """
    if reference_id is not None and (not isinstance(reference_id, str) or not reference_id.strip()):
        raise ResponseComposerError("reference_id must be a non-empty string or None")
    if aspect is not None and (not isinstance(aspect, str) or not aspect.strip()):
        raise ResponseComposerError("aspect must be a non-empty string or None")
    if not isinstance(fact_lookup, Mapping):
        raise ResponseComposerError("fact_lookup must be an object")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise ResponseComposerError("max_chars must be a positive integer")
    if templates is not None and not isinstance(templates, Mapping):
        raise ResponseComposerError("templates must be an object")

    if reference_id is None or aspect not in DEFAULT_TEMPLATES:
        return {"status": "abstained", "text": None, "reason": "missing_reference_or_unsupported_aspect"}
    if fact_lookup.get("status") != "found":
        return {"status": "abstained", "text": None, "reason": "fact_not_uniquely_found"}

    fact = fact_lookup.get("fact")
    if not isinstance(fact, Mapping):
        raise ResponseComposerError("found fact_lookup must contain a fact object")
    if fact.get("entity_id") != reference_id or fact.get("aspect") != aspect:
        return {"status": "abstained", "text": None, "reason": "fact_does_not_match_reference"}
    if fact.get("source") not in TRUSTED_SOURCES:
        return {"status": "abstained", "text": None, "reason": "fact_source_not_trusted"}
    value = fact.get("value")
    if not isinstance(value, str) or not value.strip():
        return {"status": "abstained", "text": None, "reason": "fact_value_not_plain_text"}
    if len(value) > max_chars:
        return {"status": "abstained", "text": None, "reason": "fact_value_too_long"}

    template = DEFAULT_TEMPLATES[aspect]
    if templates is not None and aspect in templates:
        template = templates[aspect]
    if not isinstance(template, str) or template.count("{fact}") != 1:
        raise ResponseComposerError("response template must contain exactly one {fact} placeholder")
    text = template.replace("{fact}", value.strip())
    if len(text) > max_chars:
        return {"status": "abstained", "text": None, "reason": "composed_response_too_long"}

    return {
        "status": "composed",
        "text": text,
        "reason": "trusted_fact_inserted_into_authored_template",
        "fact_id": fact.get("id"),
        "reference_id": reference_id,
        "aspect": aspect,
        "source": "trusted_fact_template",
    }
