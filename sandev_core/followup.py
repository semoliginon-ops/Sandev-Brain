"""Conservative reference resolution for conversational follow-ups.

Only engine-confirmed or player-approved catalog entries can be resolved.
Dialogue is used solely as a pointer to a catalog entry, never as evidence that
the referenced entity's attributes or claims are true.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping, Sequence

TRUSTED_REFERENCE_SOURCES = {"engine_confirmed", "player_approved"}
FOLLOW_UP_CUES = (
    "dia siapa", "siapa dia", "mereka siapa", "orang itu", "yang tadi",
    "ceritakan lebih banyak", "cerita lebih lanjut", "bagaimana dengan",
    "kenapa dia", "mengapa dia", "apa maksudnya", "dia itu",
    "keluarganya", "tinggal di mana", "di mana dia", "berasal dari mana",
    "apa pekerjaannya", "siapa keluarganya",
)
FOLLOW_UP_REQUEST_PREFIXES = (
    "dia siapa", "siapa dia", "mereka siapa", "orang itu siapa", "yang tadi",
    "ceritakan lebih banyak", "cerita lebih lanjut", "bagaimana dengan",
    "kenapa dia", "mengapa dia", "apa maksudnya", "tinggal di mana",
    "di mana dia", "berasal dari mana", "apa pekerjaannya",
    "siapa keluarganya", "ceritakan tentang", "jelaskan tentang",
    "tolong ceritakan", "bisa ceritakan", "coba jelaskan",
)


def _contains_phrase(text: str, phrase: str, *, possessive: bool = False) -> bool:
    """Match a whole word/phrase, optionally allowing common Indonesian possessives."""
    escaped = re.escape(phrase)
    if " " in phrase:
        escaped = escaped.replace(r"\ ", r"\s+")
    suffix = r"(?:nya|ku|mu)?" if possessive and " " not in phrase else ""
    return re.search(r"(?<!\w)" + escaped + suffix + r"(?!\w)", text) is not None


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w\s-]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _is_follow_up_request(message: str) -> bool:
    """Avoid treating ordinary statements about an entity as questions."""
    if "?" in message:
        return True
    text = _normalize(message)
    return any(text == cue or text.startswith(cue + " ") for cue in FOLLOW_UP_REQUEST_PREFIXES)


def _classify_aspect(message: str) -> str | None:
    """Return a supported question aspect without inferring its answer."""
    if not _is_follow_up_request(message):
        return None
    text = _normalize(message)
    groups = (
        ("family", ("keluarga", "ayah", "ibu", "saudara", "adik", "kakak", "anak", "istri", "suami")),
        ("location", ("tinggal di mana", "di mana dia", "berasal dari mana", "tempat tinggal", "rumah", "desa")),
        ("motive", ("kenapa", "mengapa", "alasan", "motif", "melakukan itu")),
        ("identity", ("dia siapa", "siapa dia", "identitas", "asal usul")),
    )
    for aspect, terms in groups:
        if any(_contains_phrase(text, term, possessive=True) for term in terms):
            return aspect
    if any(_contains_phrase(text, cue) for cue in FOLLOW_UP_CUES):
        return "general_details"
    return None


class FollowUpInputError(ValueError):
    """Raised when follow-up resolution input is malformed."""


def resolve_follow_up(
    message: str,
    conversation_history: Sequence[Mapping[str, Any]],
    reference_catalog: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve a follow-up to the most recently mentioned trusted catalog entry.

    This deliberately small Indonesian heuristic abstains when no unique
    catalog-backed referent exists. It does not infer facts or authorize actions.
    """
    if not isinstance(message, str):
        raise FollowUpInputError("message must be a string")
    if isinstance(conversation_history, (str, bytes)) or not isinstance(conversation_history, Sequence):
        raise FollowUpInputError("conversation_history must be a sequence")
    if isinstance(reference_catalog, (str, bytes)) or not isinstance(reference_catalog, Sequence):
        raise FollowUpInputError("reference_catalog must be a sequence")

    aspect = _classify_aspect(message)
    is_follow_up = aspect is not None
    if not is_follow_up:
        return {"status": "not_follow_up", "reference_id": None, "candidates": [],
                "aspect": None, "reason": "no_supported_follow_up_cue"}

    entries: list[tuple[str, list[str]]] = []
    seen_ids: set[str] = set()
    for item in reference_catalog:
        if not isinstance(item, Mapping):
            raise FollowUpInputError("each reference catalog entry must be an object")
        if item.get("source") not in TRUSTED_REFERENCE_SOURCES:
            continue
        ref_id, name = item.get("id"), item.get("name")
        aliases = item.get("aliases", [])
        if not isinstance(ref_id, str) or not ref_id.strip() or not isinstance(name, str) or not name.strip():
            raise FollowUpInputError("trusted references need non-empty id and name")
        if ref_id in seen_ids:
            raise FollowUpInputError("reference ids must be unique")
        if not isinstance(aliases, (list, tuple)) or any(not isinstance(x, str) for x in aliases):
            raise FollowUpInputError("reference aliases must be a list of strings")
        seen_ids.add(ref_id)
        terms = [_normalize(name)] + [_normalize(x) for x in aliases if x.strip()]
        entries.append((ref_id, [term for term in terms if term]))

    latest_by_id: dict[str, int] = {}
    for index, turn in enumerate(conversation_history):
        if not isinstance(turn, Mapping):
            raise FollowUpInputError("each conversation turn must be an object")
        text = turn.get("text")
        if not isinstance(text, str):
            raise FollowUpInputError("conversation turn text must be a string")
        normalized_turn = _normalize(text)
        for ref_id, terms in entries:
            if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized_turn) for term in terms):
                latest_by_id[ref_id] = index

    if not latest_by_id:
        return {"status": "unresolved", "reference_id": None, "candidates": [],
                "aspect": aspect, "reason": "no_trusted_catalog_reference_in_recent_dialogue"}
    latest_index = max(latest_by_id.values())
    candidates = sorted(ref_id for ref_id, index in latest_by_id.items() if index == latest_index)
    if len(candidates) != 1:
        return {"status": "ambiguous", "reference_id": None, "candidates": candidates,
                "aspect": aspect, "reason": "multiple_references_mentioned_in_latest_relevant_turn"}
    return {"status": "resolved", "reference_id": candidates[0], "candidates": candidates,
            "reason": "unique_recent_trusted_catalog_reference", "aspect": aspect,
            "reference_source": "trusted_catalog"}
