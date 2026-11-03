"""Deterministic NPC behavior proposals from trusted game context.

This module ranks a small authored action catalog. It never executes actions,
mutates game state, or treats raw dialogue/model guesses as authoritative.
The game adapter must provide an explicit action allowlist and validate/execute
any accepted proposal itself.
"""
from __future__ import annotations

from typing import Any, Mapping


class NPCBehaviorError(ValueError):
    """Raised when behavior proposal input is malformed."""


ACTION_CATALOG = {
    "approach_player", "keep_distance", "offer_help", "guard_player",
    "request_help", "continue_task", "idle", "flee", "de_escalate",
}
PERSONALITIES = {"neutral", "friendly", "shy", "cold", "humorous", "angry"}
TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
EMOTION_KEYS = {"joy", "fear", "anger", "sadness", "trust", "suspicion"}
MEMORY_CUES = {
    "betrayal": {"keep_distance": 12, "de_escalate": 5, "flee": 5},
    "broken_promise": {"keep_distance": 8, "de_escalate": 4},
    "saved": {"approach_player": 5, "guard_player": 8, "offer_help": 5},
    "helped": {"approach_player": 3, "offer_help": 4},
}


def _bool_signal(state: Mapping[str, Any], key: str) -> bool:
    value = state.get(key, False)
    if not isinstance(value, bool):
        raise NPCBehaviorError(f"state.{key} must be a boolean")
    return value


def _scope_matches(record: Mapping[str, Any], npc_id: str, player_id: str) -> bool:
    return record.get("npc_id") == npc_id and record.get("player_id") == player_id


def _mood(emotion: Mapping[str, Any] | None) -> str:
    if emotion is None:
        return "calm"
    values = emotion.get("values")
    if not isinstance(values, Mapping) or set(values) != EMOTION_KEYS:
        raise NPCBehaviorError("emotional state must contain all six emotion values")
    for key, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise NPCBehaviorError(f"emotion {key} must be an integer from 0 to 100")
    if values["fear"] >= 60:
        return "afraid"
    if values["anger"] >= 60:
        return "angry"
    if values["sadness"] >= 60:
        return "sad"
    if values["suspicion"] >= 60:
        return "suspicious"
    if values["joy"] >= 65 and values["trust"] >= 55:
        return "happy"
    if values["trust"] >= 75:
        return "trusting"
    return "calm"


def _relationship_score(relationship: Mapping[str, Any] | None) -> int:
    if relationship is None:
        return 0
    score = relationship.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not -100 <= score <= 100:
        raise NPCBehaviorError("relationship.score must be an integer from -100 to 100")
    return score


def propose_behavior(
    context: Mapping[str, Any],
    *,
    personality: str = "neutral",
    allowed_actions: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """Propose one allowlisted action using explicit adapter-authored signals.

    Expected state signals are booleans: under_threat, player_needs_help,
    npc_has_task, escape_route_available, player_is_injured. Unknown action IDs
    are ignored. The returned proposal is advisory and is never executable by
    this module.
    """
    if not isinstance(context, Mapping):
        raise NPCBehaviorError("context must be an object")
    if not isinstance(personality, str) or personality not in PERSONALITIES:
        raise NPCBehaviorError("unsupported NPC personality")
    if not isinstance(allowed_actions, (list, tuple)) or isinstance(allowed_actions, (str, bytes)):
        raise NPCBehaviorError("allowed_actions must be a list or tuple")
    if any(not isinstance(item, str) or not item.strip() for item in allowed_actions):
        raise NPCBehaviorError("allowed_actions must contain non-empty action IDs")

    state = context.get("state", {})
    if not isinstance(state, Mapping):
        raise NPCBehaviorError("context.state must be an object")
    signals = {
        key: _bool_signal(state, key)
        for key in ("under_threat", "player_needs_help", "npc_has_task",
                    "escape_route_available", "player_is_injured")
    }

    relationship = context.get("npc_relationship")
    emotion = context.get("npc_emotion")
    for name, record in (("npc_relationship", relationship), ("npc_emotion", emotion)):
        if record is not None and not isinstance(record, Mapping):
            raise NPCBehaviorError(f"{name} must be an object or None")

    npc_id = player_id = None
    if relationship is not None:
        npc_id, player_id = relationship.get("npc_id"), relationship.get("player_id")
        if not isinstance(npc_id, str) or not npc_id.strip() or not isinstance(player_id, str) or not player_id.strip():
            raise NPCBehaviorError("relationship must include NPC and player scope IDs")
    if emotion is not None:
        emotion_npc, emotion_player = emotion.get("npc_id"), emotion.get("player_id")
        if not isinstance(emotion_npc, str) or not emotion_npc.strip() or not isinstance(emotion_player, str) or not emotion_player.strip():
            raise NPCBehaviorError("emotion must include NPC and player scope IDs")
        if npc_id is not None and (npc_id, player_id) != (emotion_npc, emotion_player):
            raise NPCBehaviorError("relationship and emotion scopes do not match")
        npc_id, player_id = emotion_npc, emotion_player
    actor_id = context.get("actor_id")
    if npc_id is not None and actor_id is not None and actor_id != npc_id:
        raise NPCBehaviorError("context actor_id does not match the NPC scope")
    if (npc_id is None) != (player_id is None):
        raise NPCBehaviorError("NPC context scope is incomplete")
    if npc_id is not None and (
        not isinstance(npc_id, str) or not npc_id.strip()
        or not isinstance(player_id, str) or not player_id.strip()
    ):
        raise NPCBehaviorError("NPC context scope IDs must be non-empty strings")

    memories = context.get("npc_memories", [])
    if not isinstance(memories, list):
        raise NPCBehaviorError("npc_memories must be a list")
    memory_tags: set[str] = set()
    for item in memories:
        if not isinstance(item, Mapping) or item.get("source") not in TRUSTED_SOURCES:
            continue
        # Without an explicit pair scope, memory must not affect behavior.
        if npc_id is None or not _scope_matches(item, npc_id, player_id):
            continue
        tags = item.get("tags", [])
        if isinstance(tags, (list, tuple)):
            memory_tags.update(tag for tag in tags if isinstance(tag, str))

    goals = context.get("goals", [])
    if not isinstance(goals, list):
        raise NPCBehaviorError("goals must be a list")
    goal_tags: set[str] = set()
    for goal in goals:
        if isinstance(goal, Mapping) and isinstance(goal.get("tag"), str):
            goal_tags.add(goal["tag"])

    mood = _mood(emotion)
    relation_score = _relationship_score(relationship)
    scores = {action: 0 for action in ACTION_CATALOG}
    reasons: dict[str, list[str]] = {action: [] for action in ACTION_CATALOG}

    def add(action: str, points: int, reason: str) -> None:
        scores[action] += points
        reasons[action].append(reason)

    # Game adapter signals are explicit, current facts—not language guesses.
    if signals["under_threat"]:
        add("guard_player", 40, "game_state_under_threat")
        add("keep_distance", 15, "game_state_under_threat")
        if signals["escape_route_available"]:
            add("flee", 25, "escape_route_available")
    if signals["player_needs_help"] or signals["player_is_injured"]:
        add("offer_help", 35, "player_needs_help")
        add("guard_player", 12, "player_needs_help")
    if signals["npc_has_task"] or "continue_task" in goal_tags:
        add("continue_task", 30, "active_task")
    if "survive" in goal_tags and signals["under_threat"] and signals["escape_route_available"]:
        add("flee", 8, "survival_goal")

    # Authored personality preferences affect style of behavior, not facts.
    personality_weights = {
        "friendly": {"approach_player": 8, "offer_help": 8},
        "shy": {"keep_distance": 10},
        "cold": {"continue_task": 8, "keep_distance": 4},
        "humorous": {"approach_player": 5},
        "angry": {"keep_distance": 8, "de_escalate": 4},
        "neutral": {},
    }
    for action, points in personality_weights[personality].items():
        add(action, points, f"personality_{personality}")

    # Emotion is used as a bounded signal; it never overrides hard game facts.
    emotion_weights = {
        "afraid": {"flee": 32, "keep_distance": 18, "guard_player": -8},
        "angry": {"keep_distance": 18, "de_escalate": 16},
        "sad": {"keep_distance": 5},
        "suspicious": {"keep_distance": 18, "de_escalate": 8},
        "happy": {"approach_player": 8, "offer_help": 5},
        "trusting": {"approach_player": 10, "guard_player": 8},
        "calm": {},
    }
    for action, points in emotion_weights[mood].items():
        add(action, points, f"emotion_{mood}")

    if relation_score >= 60:
        add("approach_player", 12, "trusted_relationship")
        add("guard_player", 10, "trusted_relationship")
    elif relation_score >= 20:
        add("approach_player", 6, "friendly_relationship")
        add("offer_help", 5, "friendly_relationship")
    elif relation_score <= -60:
        add("keep_distance", 22, "hostile_relationship")
        add("flee", 10, "hostile_relationship")
    elif relation_score <= -20:
        add("keep_distance", 12, "unfriendly_relationship")
        add("de_escalate", 8, "unfriendly_relationship")

    for tag, weights in MEMORY_CUES.items():
        if tag in memory_tags:
            for action, points in weights.items():
                add(action, points, f"trusted_memory_{tag}")

    candidates = [action for action in allowed_actions if action in ACTION_CATALOG]
    if not candidates:
        return {
            "status": "abstained", "proposal": None,
            "reason": "no_supported_action_in_engine_allowlist",
            "execution": "not_performed",
        }

    # Deterministic tie-break: action ID ascending.
    ranked = sorted(candidates, key=lambda action: (-scores[action], action))
    selected = ranked[0]
    if scores[selected] <= 0:
        if "idle" not in candidates:
            return {
                "status": "abstained", "proposal": None,
                "reason": "no_positive_behavior_signal",
                "execution": "not_performed",
            }
        selected = "idle"

    return {
        "status": "proposed",
        "proposal": {
            "action_id": selected,
            "score": scores[selected],
            "reason_tags": sorted(set(reasons[selected])),
        },
        "mood": mood,
        "relationship_score": relation_score,
        "considered_actions": sorted(candidates),
        "execution": "not_performed",
        "authority": "game_engine_required",
    }
