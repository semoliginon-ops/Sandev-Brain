"""Small deterministic sentence composer from validated semantic frames.

This creates new combinations from bounded phrase components. It is not a general
language model, does not parse arbitrary text, and never treats raw player text as
trusted slot content.
"""
from __future__ import annotations

from typing import Any, Mapping


class CompositionError(ValueError):
    """Raised when a semantic frame contains unsupported or unsafe fields."""


_SPEECH = {
    "greeting": {
        "warm": ["Senang melihatmu", "Aku lega kamu datang", "Hai, senang kamu kembali"],
        "neutral": ["Halo", "Hai", "Akhirnya kita bertemu lagi"],
        "dry": ["Oh, kamu datang", "Kukira kamu lupa jalan", "Ada apa kali ini"],
    },
    "concern": {
        "warm": ["Aku mengkhawatirkanmu", "Kondisimu membuatku cemas", "Aku ingin memastikan kamu baik-baik saja"],
        "neutral": ["Kondisimu perlu diperhatikan", "Kita harus berhati-hati", "Situasinya belum aman"],
        "dry": ["Kau terlihat berantakan", "Jangan tumbang sekarang", "Kita belum selesai"],
    },
    "gratitude": {
        "warm": ["Terima kasih sudah membantuku", "Aku sungguh menghargai bantuanmu", "Kebaikanmu tidak kulupakan"],
        "neutral": ["Bantuanmu sangat berarti", "Kerja bagus", "Aku mencatat bantuanmu"],
        "dry": ["Lumayan, kau berguna juga", "Kali ini kau bisa diandalkan", "Baiklah, terima kasih"],
    },
    "encourage": {
        "warm": ["Aku percaya padamu", "Kamu tidak harus menghadapi ini sendirian", "Kita bisa melewatinya bersama"],
        "neutral": ["Tetap fokus", "Masih ada kesempatan", "Kita lanjutkan langkah berikutnya"],
        "dry": ["Jangan menyerah sekarang", "Buktikan kalau kau mampu", "Tarik napas, lalu bergerak"],
    },
}

_TOPICS = {
    "danger": ["Ancaman di sekitar kita belum hilang", "Tempat ini masih berbahaya"],
    "health": ["Kita perlu memulihkan kondisimu", "Jangan abaikan lukamu"],
    "quest": ["Tujuan kita masih menunggu", "Perjalanan ini belum selesai"],
    "general": ["Kita hadapi apa pun yang datang", "Aku akan tetap memperhatikan keadaan"],
}

_RELATION_ENDINGS = {
    "close": ["Aku akan tetap di sisimu", "Kau bisa mengandalkanku"],
    "neutral": ["Mari kita lanjutkan bersama", "Kita lihat apa langkah berikutnya"],
    "strained": ["Jangan buat aku menyesal mempercayaimu", "Kita perlu saling membuktikan diri"],
}

_PERSONALITY_TONE = {"warm", "neutral", "dry"}
_RELATIONSHIPS = {"close", "neutral", "strained"}
_TOPICS_ALLOWED = set(_TOPICS)


def _choice(items: list[str], seed: str) -> str:
    # Stable across runs and platforms; no global random state.
    index = sum((i + 1) * ord(ch) for i, ch in enumerate(seed)) % len(items)
    return items[index]


def compose_dialogue(frame: Mapping[str, Any], *, max_chars: int = 280) -> dict[str, Any]:
    """Compose a short line from a validated, game-produced semantic frame."""
    if not isinstance(frame, Mapping):
        raise CompositionError("frame must be an object")
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise CompositionError("max_chars must be a positive integer")
    speech_act = frame.get("speech_act")
    tone = frame.get("tone", "neutral")
    topic = frame.get("topic", "general")
    relationship = frame.get("relationship", "neutral")
    if speech_act not in _SPEECH:
        raise CompositionError("unsupported speech_act")
    if tone not in _PERSONALITY_TONE:
        raise CompositionError("unsupported tone")
    if topic not in _TOPICS_ALLOWED:
        raise CompositionError("unsupported topic")
    if relationship not in _RELATIONSHIPS:
        raise CompositionError("unsupported relationship")
    seed = "|".join(str(frame.get(k, "")) for k in ("speaker_id", "turn", "speech_act", "topic"))
    opening = _choice(_SPEECH[speech_act][tone], seed + "|opening")
    context_line = _choice(_TOPICS[topic], seed + "|topic")
    ending = _choice(_RELATION_ENDINGS[relationship], seed + "|ending")
    # Three independently selected semantic pieces create a compositional line.
    text = f"{opening}. {context_line}. {ending}."
    if len(text) > max_chars:
        text = f"{opening}. {ending}."
    if len(text) > max_chars:
        raise CompositionError("max_chars is too small for a safe complete response")
    return {
        "status": "composed",
        "text": text,
        "source": "compositional_phrase_grammar",
        "frame": {
            "speech_act": speech_act, "tone": tone, "topic": topic,
            "relationship": relationship,
        },
        "is_open_ended_generation": False,
    }
