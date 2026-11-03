"""Portable, trust-scoped social interaction proposals between NPCs.

The host game supplies nearby NPC IDs and verified pair relationship facts.
This module proposes one allow-listed interaction; it never changes
relationships, executes actions, or assumes an NPC is present without evidence.
"""
from __future__ import annotations

from typing import Any, Mapping


class NPCSocialError(ValueError):
    """Raised when social interaction input is malformed."""


TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
SOCIAL_ACTIONS = {
    "greet", "converse", "offer_help", "avoid", "de_escalate", "invite_group",
}
PERSONALITIES = {"neutral", "friendly", "shy", "cold", "humorous", "angry"}
MAX_NEARBY = 64
MAX_RELATIONSHIPS = 256


def _identity(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NPCSocialError(f"{label} must be a non-empty string")
    if len(value.strip()) > 100:
        raise NPCSocialError(f"{label} must be at most 100 characters")
    return value.strip()


def propose_social_interaction(
    context: Mapping[str, Any],
    *,
    personality: str = "neutral",
    allowed_actions: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """Propose one interaction with a currently nearby NPC.

    Relationship entries require an unordered pair of IDs, score (-100..100),
    and trusted source. Only entries involving the actor and a listed nearby
    NPC can influence a proposal. The game must confirm outcomes and update
    its own relationship ledger after an interaction actually occurs.
    """
    if not isinstance(context, Mapping):
        raise NPCSocialError("context must be an object")
    actor_id = _identity(context.get("npc_id"), "npc_id")
    if personality not in PERSONALITIES:
        raise NPCSocialError("unsupported NPC personality")
    if not isinstance(allowed_actions, (list, tuple)) or isinstance(allowed_actions, (str, bytes)):
        raise NPCSocialError("allowed_actions must be a list or tuple")
    if any(not isinstance(item, str) or not item.strip() for item in allowed_actions):
        raise NPCSocialError("allowed_actions must contain non-empty action IDs")

    nearby = context.get("nearby_npc_ids", [])
    if not isinstance(nearby, (list, tuple)) or isinstance(nearby, (str, bytes)):
        raise NPCSocialError("nearby_npc_ids must be a list")
    if len(nearby) > MAX_NEARBY:
        raise NPCSocialError(f"nearby_npc_ids cannot exceed {MAX_NEARBY} entries")
    nearby_ids = [_identity(item, "nearby_npc_ids item") for item in nearby]
    if actor_id in nearby_ids:
        raise NPCSocialError("npc_id cannot appear in nearby_npc_ids")
    if len(set(nearby_ids)) != len(nearby_ids):
        raise NPCSocialError("nearby_npc_ids cannot contain duplicates")

    relationships = context.get("relationships", [])
    if not isinstance(relationships, list):
        raise NPCSocialError("relationships must be a list")
    if len(relationships) > MAX_RELATIONSHIPS:
        raise NPCSocialError(f"relationships cannot exceed {MAX_RELATIONSHIPS} entries")

    # Explicit state cues are game facts, never inferred from dialogue.
    state = context.get("state", {})
    if not isinstance(state, Mapping):
        raise NPCSocialError("state must be an object")
    wants_socialize = state.get("wants_socialize", False)
    conflict_active = state.get("conflict_active", False)
    target_needs_help = state.get("target_needs_help", False)
    for key, value in (("wants_socialize", wants_socialize),
                       ("conflict_active", conflict_active),
                       ("target_needs_help", target_needs_help)):
        if not isinstance(value, bool):
            raise NPCSocialError(f"state.{key} must be a boolean")

    candidates: list[tuple[int, str, str, str]] = []
    for record in relationships:
        if not isinstance(record, Mapping) or record.get("source") not in TRUSTED_SOURCES:
            continue
        left = _identity(record.get("npc_a_id"), "relationship.npc_a_id")
        right = _identity(record.get("npc_b_id"), "relationship.npc_b_id")
        if left == right:
            raise NPCSocialError("relationship pair must contain two different NPCs")
        if actor_id not in (left, right):
            continue
        target_id = right if left == actor_id else left
        if target_id not in nearby_ids:
            continue
        score = record.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or not -100 <= score <= 100:
            raise NPCSocialError("trusted relationship score must be an integer from -100 to 100")

        weights: dict[str, int] = {}
        reasons: dict[str, str] = {}
        if wants_socialize:
            weights.update({"greet": 18, "converse": 14})
            reasons.update({"greet": "game_state_wants_socialize",
                            "converse": "game_state_wants_socialize"})
        if score >= 60:
            weights["greet"] = weights.get("greet", 0) + 12
            weights["converse"] = weights.get("converse", 0) + 12
            weights["offer_help"] = weights.get("offer_help", 0) + 8
            weights["invite_group"] = weights.get("invite_group", 0) + 8
            reasons.update({key: "trusted_relationship" for key in
                            ("greet", "converse", "offer_help", "invite_group")})
        elif score >= 20:
            weights["greet"] = weights.get("greet", 0) + 8
            weights["converse"] = weights.get("converse", 0) + 6
            reasons.update({"greet": "friendly_relationship",
                            "converse": "friendly_relationship"})
        elif score <= -60:
            weights["avoid"] = weights.get("avoid", 0) + 24
            weights["de_escalate"] = weights.get("de_escalate", 0) + 18
            reasons.update({"avoid": "hostile_relationship",
                            "de_escalate": "hostile_relationship"})
        elif score <= -20:
            weights["avoid"] = weights.get("avoid", 0) + 14
            weights["de_escalate"] = weights.get("de_escalate", 0) + 8
            reasons.update({"avoid": "unfriendly_relationship",
                            "de_escalate": "unfriendly_relationship"})
        if conflict_active:
            weights["de_escalate"] = weights.get("de_escalate", 0) + 20
            reasons["de_escalate"] = "game_state_conflict_active"
        if target_needs_help and score >= 0:
            weights["offer_help"] = weights.get("offer_help", 0) + 20
            reasons["offer_help"] = "game_state_target_needs_help"

        personality_weights = {
            "friendly": {"greet": 5, "converse": 5},
            "humorous": {"greet": 3, "converse": 4},
            "shy": {"avoid": 5},
            "cold": {"converse": -3},
            "angry": {"avoid": 4, "de_escalate": 3},
            "neutral": {},
        }
        for action, points in personality_weights[personality].items():
            weights[action] = weights.get(action, 0) + points
            reasons.setdefault(action, f"personality_{personality}")

        for action, points in weights.items():
            if action in SOCIAL_ACTIONS and action in allowed_actions and points > 0:
                candidates.append((points, action, target_id, reasons[action]))

    if not candidates:
        return {
            "status": "abstained", "proposal": None,
            "reason": "no_eligible_trusted_social_interaction",
            "execution": "not_performed", "authority": "game_engine_required",
        }

    # Highest score wins; stable target and action IDs break ties reproducibly.
    points, action, target_id, reason = sorted(
        candidates, key=lambda item: (-item[0], item[2], item[1])
    )[0]
    return {
        "status": "proposed",
        "proposal": {
            "action_id": action, "target_npc_id": target_id,
            "score": points, "reason_tag": reason,
        },
        "execution": "not_performed",
        "authority": "game_engine_required",
    }
