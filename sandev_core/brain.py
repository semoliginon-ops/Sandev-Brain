"""Model-independent, deterministic SANDEV Brain core.

Scores generic game action candidates from structured state. It does not execute
actions, mutate world state, load an LLM, or invent engine-owned facts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ActionCandidate:
    """An adapter-provided action option, not an instruction to execute it."""
    action_id: str
    kind: str
    target: str = ""
    tags: tuple[str, ...] = ()
    goal_tags: tuple[str, ...] = ()
    preconditions: Mapping[str, Any] = field(default_factory=dict)
    base_score: float = 0.0
    cost: float = 0.0


@dataclass(frozen=True)
class Decision:
    action_id: str | None
    kind: str | None
    target: str
    score: float
    reason: str
    rejected: tuple[dict[str, str], ...] = ()


def evaluate_needs(needs: Mapping[str, Any]) -> dict[str, float]:
    """Normalize numeric needs to urgency [0, 1]; larger means more urgent.

    Convention: 0 = no urgency, 100 = critical urgency. Invalid values ignored.
    """
    result: dict[str, float] = {}
    for key, value in needs.items():
        if isinstance(key, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
            result[key] = max(0.0, min(100.0, float(value))) / 100.0
    return result


def _matches(actual: Any, expected: Any) -> bool:
    """Support exact values and a small, explicit condition vocabulary."""
    if isinstance(expected, dict):
        if "min" in expected and (not isinstance(actual, (int, float)) or actual < expected["min"]):
            return False
        if "max" in expected and (not isinstance(actual, (int, float)) or actual > expected["max"]):
            return False
        if "equals" in expected and actual != expected["equals"]:
            return False
        if "not_equals" in expected and actual == expected["not_equals"]:
            return False
        return True
    return actual == expected


def _preconditions_met(state: Mapping[str, Any], conditions: Mapping[str, Any]) -> tuple[bool, str]:
    for path, expected in conditions.items():
        current: Any = state
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return False, f"missing state field: {path}"
            current = current[part]
        if not _matches(current, expected):
            return False, f"precondition failed: {path}"
    return True, ""


def choose_action(
    *,
    state: Mapping[str, Any],
    needs: Mapping[str, Any],
    goals: Sequence[Mapping[str, Any]],
    candidates: Sequence[ActionCandidate],
    allowed_actions: Sequence[str],
    urgency_weight: float = 60.0,
    goal_weight: float = 25.0,
    feedback_adjustments: Mapping[str, float] | None = None,
) -> Decision:
    """Choose a valid, feasible action intent using transparent utility scoring.

    Candidate tags match needs. Each goal mapping has tag and optional priority
    (0..1). Ties are deterministic. The game engine must validate the intent.
    """
    urgency = evaluate_needs(needs)
    goal_scores: dict[str, float] = {}
    for goal in goals:
        tag = goal.get("tag")
        priority = goal.get("priority", 0.5)
        if isinstance(tag, str) and isinstance(priority, (int, float)) and not isinstance(priority, bool):
            goal_scores[tag] = max(goal_scores.get(tag, 0.0), max(0.0, min(1.0, float(priority))))

    allowed = set(allowed_actions)
    rejected: list[dict[str, str]] = []
    scored: list[tuple[float, str, ActionCandidate, str]] = []
    for candidate in candidates:
        if candidate.kind not in allowed:
            rejected.append({"action_id": candidate.action_id, "reason": "action not in allow-list"})
            continue
        feasible, why = _preconditions_met(state, candidate.preconditions)
        if not feasible:
            rejected.append({"action_id": candidate.action_id, "reason": why})
            continue
        need_value = max((urgency.get(tag, 0.0) for tag in candidate.tags), default=0.0)
        goal_value = max((goal_scores.get(tag, 0.0) for tag in candidate.goal_tags), default=0.0)
        feedback = 0.0
        if feedback_adjustments is not None:
            raw_feedback = feedback_adjustments.get(candidate.action_id, 0.0)
            if isinstance(raw_feedback, (int, float)) and not isinstance(raw_feedback, bool):
                feedback = max(-20.0, min(20.0, float(raw_feedback)))
        score = float(candidate.base_score) + urgency_weight * need_value + goal_weight * goal_value - max(0.0, float(candidate.cost)) + feedback
        reason_parts = []
        if need_value:
            best_need = max(candidate.tags, key=lambda tag: urgency.get(tag, 0.0))
            reason_parts.append(f"need:{best_need}={need_value:.2f}")
        if goal_value:
            best_goal = max(candidate.goal_tags, key=lambda tag: goal_scores.get(tag, 0.0))
            reason_parts.append(f"goal:{best_goal}={goal_value:.2f}")
        if candidate.base_score:
            reason_parts.append(f"base={candidate.base_score:.2f}")
        if candidate.cost:
            reason_parts.append(f"cost={max(0.0, candidate.cost):.2f}")
        if feedback:
            reason_parts.append(f"confirmed_outcome_feedback={feedback:.2f}")
        scored.append((score, candidate.action_id, candidate, ", ".join(reason_parts) or "feasible fallback"))

    if not scored:
        return Decision(None, None, "", 0.0, "no feasible allowed action", tuple(rejected))
    score, _, winner, reason = sorted(scored, key=lambda item: (-item[0], item[1]))[0]
    return Decision(winner.action_id, winner.kind, winner.target, score, reason, tuple(rejected))


def decision_to_dict(decision: Decision) -> dict[str, Any]:
    """Serialize intent for an adapter; does not imply execution succeeded."""
    return {
        "action_id": decision.action_id,
        "action": {"type": decision.kind, "target": decision.target} if decision.kind else None,
        "score": round(decision.score, 4),
        "reason": decision.reason,
        "rejected": list(decision.rejected),
        "status": "intent_only_engine_must_validate",
    }
