"""Generic game-to-core adapter contract.

A game supplies a JSON-like snapshot and engine-approved action candidates.
This module validates the envelope and translates it to the deterministic core.
It never executes actions, mutates game state, or calls an AI/model service.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from brain import ActionCandidate, choose_action, decision_to_dict


class AdapterInputError(ValueError):
    """Raised when a game snapshot violates the public adapter contract."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AdapterInputError(f"{name} must be an object")
    return value


def _string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise AdapterInputError(f"{name} must be a {'string' if allow_empty else 'non-empty string'}")
    return value


def _string_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AdapterInputError(f"{name} must be a list of non-empty strings")
    return tuple(value)


def _number(value: Any, name: str, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise AdapterInputError(f"{name} must be a finite number")
    return float(value)


def decide_from_snapshot(
    snapshot: Mapping[str, Any],
    *,
    feedback_adjustments: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Validate a generic snapshot and return an intent-only decision envelope.

    Required fields: state, needs, goals, candidates, allowed_actions.
    Optional fields: game_id and state_version. Unknown game-specific state keys are preserved.
    The host game must validate the returned intent again before execution.
    """
    data = _mapping(snapshot, "snapshot")
    state = _mapping(data.get("state"), "state")
    needs = _mapping(data.get("needs"), "needs")
    goals_raw = data.get("goals")
    candidates_raw = data.get("candidates")
    allowed = _string_list(data.get("allowed_actions"), "allowed_actions")

    if not isinstance(goals_raw, (list, tuple)):
        raise AdapterInputError("goals must be a list")
    if not isinstance(candidates_raw, (list, tuple)):
        raise AdapterInputError("candidates must be a list")

    goals = []
    for index, item in enumerate(goals_raw):
        goal = _mapping(item, f"goals[{index}]")
        goals.append({
            "tag": _string(goal.get("tag"), f"goals[{index}].tag"),
            "priority": _number(goal.get("priority"), f"goals[{index}].priority", 0.5),
        })

    candidates = []
    seen_ids: set[str] = set()
    for index, item in enumerate(candidates_raw):
        candidate = _mapping(item, f"candidates[{index}]")
        prefix = f"candidates[{index}]"
        action_id = _string(candidate.get("action_id"), f"{prefix}.action_id")
        if action_id in seen_ids:
            raise AdapterInputError(f"duplicate action_id: {action_id}")
        seen_ids.add(action_id)
        preconditions = candidate.get("preconditions", {})
        if not isinstance(preconditions, Mapping):
            raise AdapterInputError(f"{prefix}.preconditions must be an object")
        candidates.append(ActionCandidate(
            action_id=action_id,
            kind=_string(candidate.get("kind"), f"{prefix}.kind"),
            target=_string(candidate.get("target", ""), f"{prefix}.target", allow_empty=True),
            tags=_string_list(candidate.get("tags", []), f"{prefix}.tags"),
            goal_tags=_string_list(candidate.get("goal_tags", []), f"{prefix}.goal_tags"),
            preconditions=preconditions,
            base_score=_number(candidate.get("base_score"), f"{prefix}.base_score"),
            cost=_number(candidate.get("cost"), f"{prefix}.cost"),
        ))

    decision = choose_action(
        state=state,
        needs=needs,
        goals=goals,
        candidates=candidates,
        allowed_actions=allowed,
        feedback_adjustments=feedback_adjustments,
    )
    result = decision_to_dict(decision)
    result["contract_version"] = "1.0"
    result["game_id"] = data.get("game_id", "unspecified")
    if "state_version" in data:
        result["state_version"] = data["state_version"]
    result["status"] = "intent_only_engine_must_validate"
    return result
