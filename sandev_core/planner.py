"""Conservative multi-step command planner; proposals only, never execution."""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from command import CommandInputError, interpret_player_command
from intent import normalize_text


class PlannerInputError(ValueError):
    """Raised when planner inputs are malformed."""


_CONNECTOR = re.compile(r"\s*,?\s+(dan kemudian|setelah itu|lalu|kemudian)\s+", re.IGNORECASE)
_UNSUPPORTED_CONNECTOR = re.compile(r"\bsekaligus\b", re.IGNORECASE)


def _split_steps(message: str, max_steps: int) -> tuple[list[str], list[str]]:
    matches = list(_CONNECTOR.finditer(message))
    clauses: list[str] = []
    connectors: list[str] = []
    start = 0
    for match in matches:
        clause = message[start:match.start()].strip(" ,")
        if not clause:
            raise PlannerInputError("sequence contains an empty step")
        clauses.append(clause)
        connectors.append(normalize_text(match.group(1)))
        start = match.end()
    tail = message[start:].strip(" ,")
    if not tail:
        raise PlannerInputError("sequence ends with a connector")
    clauses.append(tail)
    if len(clauses) > max_steps:
        raise PlannerInputError("sequence exceeds max_steps")
    return clauses, connectors


def plan_player_command(
    message: str,
    entities: Sequence[Mapping[str, Any]],
    *,
    context: Mapping[str, Any] | None = None,
    max_steps: int = 5,
) -> dict[str, Any]:
    """Resolve each step against one snapshot and return proposals only."""
    if not isinstance(message, str):
        raise PlannerInputError("message must be a string")
    if not isinstance(entities, (list, tuple)):
        raise PlannerInputError("entities must be a list or tuple")
    if context is not None and not isinstance(context, Mapping):
        raise PlannerInputError("context must be an object")
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= 10:
        raise PlannerInputError("max_steps must be an integer between 1 and 10")

    normalized = normalize_text(message)
    if re.search(r"\b(lalu|kemudian|dan kemudian|setelah itu)\s*$", normalized):
        return {
            "status": "rejected", "reason": "sequence ends with a connector",
            "steps": [], "step_count": 0,
            "state_version": context.get("state_version") if context else None,
            "execution_allowed": False,
        }
    if _UNSUPPORTED_CONNECTOR.search(normalized):
        return {
            "status": "needs_clarification", "reason": "unsupported_sequence_connector",
            "steps": [], "step_count": 0,
            "state_version": context.get("state_version") if context else None,
            "execution_allowed": False,
        }

    try:
        clauses, connectors = _split_steps(message, max_steps)
    except PlannerInputError as exc:
        return {
            "status": "rejected", "reason": str(exc), "steps": [], "step_count": 0,
            "state_version": context.get("state_version") if context else None,
            "execution_allowed": False,
        }

    if len(clauses) == 1:
        proposal = interpret_player_command(message, entities, context=context)
        if proposal.get("status") != "proposal":
            return {
                "status": "needs_clarification", "reason": "single_command_not_confidently_resolved",
                "steps": [], "step_count": 0,
                "state_version": context.get("state_version") if context else None,
                "command_result": proposal, "execution_allowed": False,
            }
        return {
            "status": "plan_proposal", "reason": "single_step_proposal_only",
            "steps": [{"index": 1, "command": message.strip(), "proposal": proposal}],
            "step_count": 1, "connectors": [],
            "state_version": context.get("state_version") if context else None,
            "execution_allowed": False,
        }

    steps: list[dict[str, Any]] = []
    for index, clause in enumerate(clauses, start=1):
        try:
            proposal = interpret_player_command(clause, entities, context=context)
        except CommandInputError as exc:
            return {
                "status": "rejected", "reason": "step_input_invalid", "failed_step": index,
                "detail": str(exc), "steps": [], "step_count": 0,
                "state_version": context.get("state_version") if context else None,
                "execution_allowed": False,
            }
        if proposal.get("status") != "proposal":
            return {
                "status": "needs_clarification", "reason": "step_not_confidently_resolved",
                "failed_step": index, "failed_command": clause, "command_result": proposal,
                "steps": [], "step_count": 0,
                "state_version": context.get("state_version") if context else None,
                "execution_allowed": False,
            }
        if proposal.get("intent") == "tactical_defend" and proposal.get("target") is None:
            return {
                "status": "needs_clarification", "reason": "defense_target_must_be_grounded_in_sequence",
                "failed_step": index, "failed_command": clause, "steps": [], "step_count": 0,
                "state_version": context.get("state_version") if context else None,
                "execution_allowed": False,
            }
        steps.append({"index": index, "command": clause, "proposal": proposal})

    return {
        "status": "plan_proposal", "reason": "all_steps_resolved_against_current_snapshot",
        "steps": steps, "step_count": len(steps), "connectors": connectors,
        "state_version": context.get("state_version") if context else None,
        "execution_allowed": False,
        "engine_requirement": "revalidate_each_step_against_fresh_state_and_stop_on_any_change",
    }


if __name__ == "__main__":
    import json
    import sys
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise PlannerInputError("input must be a JSON object")
    print(json.dumps(plan_player_command(
        payload.get("message"), payload.get("entities"),
        context=payload.get("context"), max_steps=payload.get("max_steps", 5),
    ), ensure_ascii=False))
