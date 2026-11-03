"""Trusted, deterministic NPC daily-routine proposals.

The host game supplies the current in-game clock and authoritative world state.
This module selects an eligible authored routine but never executes it or
changes the world. Routine records are scoped to one NPC and require trusted
provenance.
"""
from __future__ import annotations

from typing import Any, Mapping


class NPCRoutineError(ValueError):
    """Raised when the routine context or trusted schedule is malformed."""


TRUSTED_SOURCES = {"engine_confirmed", "player_approved"}
MAX_ROUTINES = 128
MAX_CONDITIONS = 16


def _valid_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))


def _matches_conditions(conditions: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    for key, expected in conditions.items():
        if not isinstance(key, str) or not key.strip() or not _valid_scalar(expected):
            raise NPCRoutineError("routine conditions must use non-empty keys and scalar values")
        if key not in state or state[key] != expected:
            return False
    return True


def propose_routine(context: Mapping[str, Any], *, allowed_activities: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Select one currently eligible, trusted schedule entry.

    Required context: npc_id, current_minute (0..1439), day_of_week (0..6),
    state (flat authoritative facts), optional world facts and nearby entity IDs,
    and routines. Each trusted routine has
    activity_id, start_minute, end_minute, source, npc_id; optional days,
    priority (0..100), active, state/world conditions, and nearby entity ID
    requirements/exclusions. Windows are start-inclusive,
    end-exclusive and must not cross midnight (split overnight routines).
    """
    if not isinstance(context, Mapping):
        raise NPCRoutineError("context must be an object")
    npc_id = context.get("npc_id")
    if not isinstance(npc_id, str) or not npc_id.strip():
        raise NPCRoutineError("npc_id must be a non-empty string")
    minute = context.get("current_minute")
    day = context.get("day_of_week")
    if isinstance(minute, bool) or not isinstance(minute, int) or not 0 <= minute <= 1439:
        raise NPCRoutineError("current_minute must be an integer from 0 to 1439")
    if isinstance(day, bool) or not isinstance(day, int) or not 0 <= day <= 6:
        raise NPCRoutineError("day_of_week must be an integer from 0 to 6")
    state = context.get("state", {})
    if not isinstance(state, Mapping):
        raise NPCRoutineError("state must be an object")
    if not isinstance(allowed_activities, (list, tuple)) or isinstance(allowed_activities, (str, bytes)):
        raise NPCRoutineError("allowed_activities must be a list or tuple")
    if any(not isinstance(x, str) or not x.strip() for x in allowed_activities):
        raise NPCRoutineError("allowed_activities must contain non-empty activity IDs")
    world = context.get("world", {})
    if not isinstance(world, Mapping):
        raise NPCRoutineError("world must be an object of authoritative facts")
    nearby = context.get("nearby_entity_ids", [])
    if not isinstance(nearby, (list, tuple)) or any(not isinstance(x, str) or not x.strip() for x in nearby):
        raise NPCRoutineError("nearby_entity_ids must contain non-empty entity IDs")
    nearby_ids = set(nearby)
    routines = context.get("routines", [])
    if not isinstance(routines, list):
        raise NPCRoutineError("routines must be a list")
    if len(routines) > MAX_ROUTINES:
        raise NPCRoutineError(f"routines cannot exceed {MAX_ROUTINES} entries")

    eligible = []
    for index, routine in enumerate(routines):
        if not isinstance(routine, Mapping) or routine.get("source") not in TRUSTED_SOURCES:
            continue
        if routine.get("npc_id") != npc_id:
            continue
        activity = routine.get("activity_id")
        if not isinstance(activity, str) or not activity.strip():
            raise NPCRoutineError(f"routines[{index}].activity_id must be non-empty")
        start, end = routine.get("start_minute"), routine.get("end_minute")
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (start, end)) or not (0 <= start < end <= 1440):
            raise NPCRoutineError(f"routines[{index}] must have a valid same-day time window")
        priority = routine.get("priority", 50)
        active = routine.get("active", True)
        if isinstance(priority, bool) or not isinstance(priority, int) or not 0 <= priority <= 100:
            raise NPCRoutineError(f"routines[{index}].priority must be an integer from 0 to 100")
        if not isinstance(active, bool):
            raise NPCRoutineError(f"routines[{index}].active must be a boolean")
        days = routine.get("days", list(range(7)))
        if not isinstance(days, (list, tuple)) or any(
            isinstance(x, bool) or not isinstance(x, int) or not 0 <= x <= 6 for x in days
        ):
            raise NPCRoutineError(f"routines[{index}].days must contain weekdays from 0 to 6")
        conditions = routine.get("conditions", {})
        if not isinstance(conditions, Mapping) or len(conditions) > MAX_CONDITIONS:
            raise NPCRoutineError(f"routines[{index}].conditions must be an object of at most {MAX_CONDITIONS} entries")
        world_conditions = routine.get("world_conditions", {})
        if not isinstance(world_conditions, Mapping) or len(world_conditions) > MAX_CONDITIONS:
            raise NPCRoutineError(f"routines[{index}].world_conditions must be an object of at most {MAX_CONDITIONS} entries")
        requires_nearby = routine.get("requires_nearby", [])
        forbids_nearby = routine.get("forbids_nearby", [])
        for field, ids in (("requires_nearby", requires_nearby), ("forbids_nearby", forbids_nearby)):
            if not isinstance(ids, (list, tuple)) or any(not isinstance(x, str) or not x.strip() for x in ids):
                raise NPCRoutineError(f"routines[{index}].{field} must contain non-empty entity IDs")
        if set(requires_nearby) & set(forbids_nearby):
            raise NPCRoutineError(f"routines[{index}] cannot both require and forbid the same nearby entity")
        if not active or activity not in allowed_activities or day not in days:
            continue
        if not start <= minute < end:
            continue
        if not _matches_conditions(conditions, state):
            continue
        if not _matches_conditions(world_conditions, world):
            continue
        if not set(requires_nearby).issubset(nearby_ids) or set(forbids_nearby) & nearby_ids:
            continue
        eligible.append((priority, -(end - start), activity, start, end))

    if not eligible:
        return {
            "status": "abstained", "proposal": None,
            "reason": "no_eligible_trusted_routine",
            "execution": "not_performed", "authority": "game_engine_required",
        }
    # Highest priority wins; then the narrower schedule window; then stable ID.
    priority, _, activity, start, end = sorted(
        eligible, key=lambda item: (-item[0], -item[1], item[2])
    )[0]
    return {
        "status": "proposed",
        "proposal": {
            "activity_id": activity,
            "priority": priority,
            "schedule_window": {"start_minute": start, "end_minute": end},
        },
        "execution": "not_performed",
        "authority": "game_engine_required",
    }
