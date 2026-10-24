"""Transparent Indonesian intent baseline for SANDEV Brain.

This deterministic phrase matcher is an auditable starting point, not a general
language model. It never executes game actions and returns unknown when the
input is ambiguous or unsupported.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping, Sequence


class IntentInputError(ValueError):
    """Raised when intent-classification input is malformed."""


DEFAULT_PATTERNS: tuple[dict[str, Any], ...] = (
    {"intent": "greeting", "phrases": ("halo", "hai", "hei", "selamat pagi", "selamat siang", "selamat malam", "apa kabar"), "weight": 1.0},
    {"intent": "thanks", "phrases": ("terima kasih", "makasih", "thanks", "aku berterima kasih"), "weight": 1.0},
    {"intent": "farewell", "phrases": ("sampai jumpa", "dadah", "aku pergi dulu", "selamat tinggal", "bye"), "weight": 1.0},
    {"intent": "help_request", "phrases": ("tolong bantu", "aku butuh bantuan", "bantu aku", "bisa bantu aku", "aku perlu bantuan", "help me"), "weight": 1.0},
    {"intent": "danger", "phrases": ("aku diserang", "kita diserang", "ada musuh di belakang", "awas", "bahaya", "aku dalam bahaya", "musuh mendekat", "selamatkan aku"), "weight": 1.0},
    {"intent": "heal_request", "phrases": ("sembuhkan aku", "aku butuh heal", "heal aku", "pulihkan hp", "aku butuh potion", "obati aku", "darahku tinggal sedikit", "hp ku rendah", "hp-ku rendah", "aku sekarat"), "weight": 1.0},
    {"intent": "tactical_attack", "phrases": ("serang musuh", "serang target", "tembak musuh", "hajar mereka", "fokus serang", "maju menyerang", "habisi bos"), "weight": 1.0},
    {"intent": "tactical_defend", "phrases": ("lindungi aku", "jaga aku", "bertahan", "mundur dulu", "cari perlindungan", "tutup sisi kiri", "tutup sisi kanan", "jangan menyerang", "ambil posisi bertahan"), "weight": 1.0},
    {"intent": "comfort", "phrases": ("aku takut", "aku sedih", "aku kesepian", "aku sedang tidak baik", "temani aku", "aku butuh teman", "aku cemas"), "weight": 1.0},
    {"intent": "banter", "phrases": ("ayo bercanda", "ceritakan lelucon", "buat aku tertawa", "lucu dong", "gombalin aku"), "weight": 1.0},
)


def normalize_text(text: str) -> str:
    """Normalize case, punctuation and common casual Indonesian spellings."""
    if not isinstance(text, str):
        raise IntentInputError("message must be a string")
    value = unicodedata.normalize("NFKC", text).casefold().strip()
    value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\b(nggak|enggak|gak|ga)\b", "tidak", value)
    return value


def classify_intent(
    message: str,
    *,
    context: Mapping[str, Any] | None = None,
    patterns: Sequence[Mapping[str, Any]] = DEFAULT_PATTERNS,
    min_confidence: float = 0.75,
    ambiguity_margin: float = 0.20,
) -> dict[str, Any]:
    """Classify a short player message into a curated intent label.

    Context is optional and supplies game_id as metadata only. The first version
    deliberately does not use game state to guess what the player means.
    Scores are rule-match strengths, not calibrated probabilities.
    """
    normalized = normalize_text(message)
    if not isinstance(min_confidence, (int, float)) or isinstance(min_confidence, bool) or not 0 <= min_confidence <= 1:
        raise IntentInputError("min_confidence must be between 0 and 1")
    if not isinstance(ambiguity_margin, (int, float)) or isinstance(ambiguity_margin, bool) or not 0 <= ambiguity_margin <= 1:
        raise IntentInputError("ambiguity_margin must be between 0 and 1")
    if context is not None and not isinstance(context, Mapping):
        raise IntentInputError("context must be an object")

    game_id = context.get("game_id", "unspecified") if context is not None else "unspecified"
    if not isinstance(game_id, str):
        raise IntentInputError("context.game_id must be a string")

    scores: dict[str, tuple[float, str]] = {}
    seen: set[tuple[str, str]] = set()
    for pattern in patterns:
        if not isinstance(pattern, Mapping):
            raise IntentInputError("each intent pattern must be an object")
        intent = pattern.get("intent")
        phrases = pattern.get("phrases")
        weight = pattern.get("weight", 1.0)
        if not isinstance(intent, str) or not intent.strip():
            raise IntentInputError("each pattern needs a non-empty intent")
        if not isinstance(phrases, (list, tuple)) or not phrases or any(not isinstance(p, str) or not p.strip() for p in phrases):
            raise IntentInputError("pattern phrases must be a non-empty list of strings")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 < weight <= 1:
            raise IntentInputError("pattern weight must be greater than 0 and at most 1")
        for phrase in phrases:
            normalized_phrase = normalize_text(phrase)
            pair = (intent, normalized_phrase)
            if pair in seen:
                raise IntentInputError(f"duplicate intent phrase: {intent}/{normalized_phrase}")
            seen.add(pair)
            if normalized_phrase and re.search(r"(?<!\w)" + re.escape(normalized_phrase) + r"(?!\w)", normalized):
                previous = scores.get(intent)
                candidate = (float(weight), normalized_phrase)
                if previous is None or candidate[0] > previous[0] or (candidate[0] == previous[0] and len(candidate[1]) > len(previous[1])):
                    scores[intent] = candidate

    ranked = sorted(
        ((score, intent, phrase) for intent, (score, phrase) in scores.items()),
        key=lambda item: (-item[0], item[1]),
    )
    if not ranked:
        return {"status": "unknown", "intent": "unknown", "confidence": 0.0,
                "matched_phrase": None, "normalized_message": normalized, "game_id": game_id,
                "reason": "no_supported_phrase_match"}

    best_score, best_intent, best_phrase = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_score < min_confidence:
        status, intent, reason = "unknown", "unknown", "below_minimum_match_strength"
    elif best_score - second_score < ambiguity_margin:
        status, intent, reason = "ambiguous", "unknown", "competing_intents"
    else:
        status, intent, reason = "matched", best_intent, "curated_phrase_match"

    return {"status": status, "intent": intent, "confidence": best_score if status == "matched" else 0.0,
            "matched_phrase": best_phrase, "normalized_message": normalized, "game_id": game_id,
            "reason": reason}
