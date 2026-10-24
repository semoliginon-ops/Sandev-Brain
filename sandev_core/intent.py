"""Transparent Indonesian intent baseline for SANDEV Brain.

This deterministic phrase matcher is an auditable starting point, not a general
language model. It never executes game actions and returns unknown when the
input is ambiguous, negated, or unsupported.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping, Sequence


class IntentInputError(ValueError):
    """Raised when intent-classification input is malformed."""


DEFAULT_PATTERNS: tuple[dict[str, Any], ...] = (
    {"intent": "greeting", "phrases": ("halo", "hai", "hei", "selamat pagi", "selamat siang", "selamat malam", "apa kabar", "pagi kawan", "senang ketemu kamu lagi", "pagi bro", "halo kawan", "hai kita ketemu lagi"), "weight": 1.0},
    {"intent": "thanks", "phrases": ("terima kasih", "makasih", "thanks", "aku berterima kasih", "bantuanmu berarti banget", "bantuanmu sangat berarti", "aku menghargai bantuanmu", "makasih banyak ya", "aku sangat menghargai pertolonganmu", "terima kasih banyak atas dukungannya"), "weight": 1.0},
    {"intent": "farewell", "phrases": ("sampai jumpa", "dadah", "aku pergi dulu", "selamat tinggal", "bye", "aku cabut dulu", "sampai nanti", "aku pamit dulu", "sampai ketemu di lain waktu", "aku harus pergi sekarang"), "weight": 1.0},
    {"intent": "help_request", "phrases": ("tolong bantu", "aku butuh bantuan", "bantu aku", "bisa bantu aku", "aku perlu bantuan", "aku perlu bantuanmu", "help me", "bantu beresin ini", "aku kewalahan", "aku perlu pertolongan", "bisa tolongin aku", "tolong bantu selesaikan urusan ini"), "weight": 1.0},
    {"intent": "danger", "phrases": ("aku diserang", "kita diserang", "ada musuh di belakang", "awas", "bahaya", "aku dalam bahaya", "musuh mendekat", "selamatkan aku", "mengepung kita", "mengepun kita", "lawan mendekat", "ada lawan mendekat", "kita dikepung", "mereka ada di dekat kita", "situasinya gawat", "kita terancam", "musuh sudah mengejar kita"), "weight": 1.0},
    {"intent": "heal_request", "phrases": ("sembuhkan aku", "aku butuh heal", "heal aku", "pulihkan hp", "aku butuh potion", "obati aku", "darahku tinggal sedikit", "hp ku rendah", "hp-ku rendah", "aku sekarat", "kondisiku kritis", "perlu pemulihan", "isi lagi tenaga", "pulihkan tenagaku", "tenagaku habis", "darahku menipis", "pulihkan kesehatanku", "obat untuk memulihkan diri", "sisa darahku sedikit sekali"), "weight": 1.0},
    {"intent": "tactical_attack", "phrases": ("serang musuh", "serang target", "tembak musuh", "hajar mereka", "fokus serang", "maju menyerang", "habisi bos", "arahkan tembakan", "hantam dia", "hantam mereka", "bidik lawan", "tembak lawan", "jadikan dia target", "fokus pada lawan itu", "hajar musuh yang di depan"), "weight": 1.0},
    {"intent": "tactical_defend", "phrases": ("lindungi aku", "jaga aku", "bertahan", "mundur dulu", "cari perlindungan", "tutup sisi kiri", "tutup sisi kanan", "jangan menyerang", "ambil posisi bertahan", "berlindung di balik", "ambil jarak", "tahan posisi", "tetap di belakangku", "cari tempat berlindung", "berlindung dulu", "tolong lindungi bagian belakang", "tetap di tempat aman", "jaga bagian belakang"), "weight": 1.0},
    {"intent": "comfort", "phrases": ("aku takut", "aku sedih", "aku kesepian", "aku sedang tidak baik", "temani aku", "aku butuh teman", "aku cemas", "temenin aku", "jangan tinggalin aku", "aku lagi down", "aku gelisah", "aku butuh ditemani", "aku lagi murung", "aku merasa cemas sendirian", "jangan pergi dulu"), "weight": 1.0},
    {"intent": "banter", "phrases": ("ayo bercanda", "ceritakan lelucon", "buat aku tertawa", "lucu dong", "gombalin aku", "humor receh", "sesuatu yang kocak", "bikin suasana cair", "lempar candaan", "hibur aku dengan lelucon", "bikin aku ngakak", "lontarkan candaan yang lucu"), "weight": 1.0},
)

_NEGATIONS = {"tidak", "jangan", "bukan", "belum", "tak", "enggan"}


def normalize_text(text: str) -> str:
    """Normalize case, punctuation and common casual Indonesian spellings."""
    if not isinstance(text, str):
        raise IntentInputError("message must be a string")
    value = unicodedata.normalize("NFKC", text).casefold().strip()
    value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\b(nggak|enggak|gak|ga)\b", "tidak", value)
    return value


def _is_negated(normalized_message: str, start: int) -> bool:
    """Conservatively detect a negation immediately before a matched phrase."""
    prefix = normalized_message[:start].split()
    return bool(prefix and prefix[-1] in _NEGATIONS) or (
        len(prefix) >= 2 and prefix[-2] in _NEGATIONS
    )


_COMPOSITIONAL_CUES: dict[str, tuple[tuple[str, ...], ...]] = {
    'greeting': (('halo', 'hai', 'salam', 'selamat datang', 'apa kabar'), ('pagi', 'siang', 'malam', 'bertemu', 'berjumpa', 'kawan', 'teman')),
    'thanks': (('terima kasih', 'berterima kasih', 'menghargai', 'berutang budi'), ('bantuan', 'pertolongan', 'berarti', 'kebaikan', 'dukungan')),
    'farewell': (('pamit', 'undur diri', 'pergi', 'berpisah', 'sampai jumpa', 'sampai berjumpa'), ('dulu', 'nanti', 'besok', 'kembali', 'kesempatan lain', 'melanjutkan perjalanan')),
    'help_request': (('bantu', 'bantuan', 'tolong', 'pertolongan', 'kesulitan', 'kesusahan'), ('selesaikan', 'mengurus', 'mengatasi', 'sendirian', 'membantuku', 'persoalan', 'tugas')),
    'danger': (('bahaya', 'ancaman', 'terancam', 'celaka', 'tidak aman', 'gawat', 'dikejar'), ('musuh', 'pengejar', 'mengejar', 'mendekat', 'di belakang', 'diserang', 'rombongan')),
    'heal_request': (('pulihkan', 'sembuhkan', 'obati', 'mengobati', 'penyembuh', 'perawatan', 'pemulihan'), ('luka', 'darah', 'tenaga', 'kesehatan', 'ramuan', 'daya hidup', 'habis')),
    'tactical_attack': (('serang', 'serbu', 'bidik', 'tembak', 'hantam', 'lumpuhkan', 'lepaskan tembakan'), ('musuh', 'lawan', 'sasaran', 'target', 'penyerang', 'gerombolan', 'pemimpin')),
    'tactical_defend': (('bertahan', 'berlindung', 'bersembunyi', 'mundur', 'amankan posisi', 'pertahanan', 'perlindungan'), ('aman', 'risiko', 'tembok', 'utara', 'sisi', 'posisi', 'keluar')),
    'comfort': (('sedih', 'sepi', 'kesepian', 'hampa', 'khawatir', 'cemas', 'berat menjalani', 'kehilangan semangat'), ('temani', 'teman bicara', 'mendengarkan', 'sendirian', 'ditemani', 'ceritaku', 'hari ini')),
    'banter': (('lelucon', 'humor', 'jenaka', 'konyol', 'candaan', 'lucu', 'tertawa', 'ketawa'), ('bikin', 'kasih', 'buat', 'suasana', 'bahan', 'dong', 'ringan')),
}

def _compositional_intent(normalized: str) -> str | None:
    """Require evidence from two separate cue families; otherwise abstain."""
    tokens = set(normalized.split())
    candidates: list[str] = []
    for intent, groups in _COMPOSITIONAL_CUES.items():
        matched_groups = sum(1 for group in groups if any((cue in normalized if ' ' in cue else cue in tokens) for cue in group))
        if matched_groups >= 2:
            candidates.append(intent)
    return candidates[0] if len(candidates) == 1 else None


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
    Scores are rule-match strengths, not calibrated probabilities. Negated
    matches are ignored conservatively; full linguistic scope is not inferred.
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
            match = re.search(r"(?<!\w)" + re.escape(normalized_phrase) + r"(?!\w)", normalized)
            if match and not _is_negated(normalized, match.start()):
                previous = scores.get(intent)
                candidate = (float(weight), normalized_phrase)
                if previous is None or candidate[0] > previous[0] or (candidate[0] == previous[0] and len(candidate[1]) > len(previous[1])):
                    scores[intent] = candidate

    ranked = sorted(
        ((score, intent, phrase) for intent, (score, phrase) in scores.items()),
        key=lambda item: (-item[0], item[1]),
    )
    if not ranked:
        # Conservative compositional fallback: two cue families, no negation.
        has_negation = any(word in _NEGATIONS for word in normalized.split())
        inferred = None if has_negation else _compositional_intent(normalized)
        if inferred and not ("?" in message and "atau" in normalized.split() and inferred in {"tactical_attack", "tactical_defend"}):
            return {"status": "matched", "intent": inferred, "confidence": 0.80,
                    "matched_phrase": None, "normalized_message": normalized,
                    "game_id": game_id, "reason": "compositional_two_cue_families"}
        return {"status": "unknown", "intent": "unknown", "confidence": 0.0,
                "matched_phrase": None, "normalized_message": normalized, "game_id": game_id,
                "reason": "no_supported_phrase_match_or_negated"}

    # A choice question mentioning an action is not itself an instruction.
    # Fail closed rather than treating one option as a command.
    if "?" in message and re.search(r"\batau\b", normalized) and any(
        intent in scores for intent in ("tactical_attack", "tactical_defend")
    ):
        return {"status": "ambiguous", "intent": "unknown", "confidence": 0.0,
                "matched_phrase": None, "normalized_message": normalized, "game_id": game_id,
                "reason": "action_choice_question_requires_clarification"}

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
