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


def validate_plan_step(
    plan: Mapping[str, Any],
    step_index: int,
    current_entities: Sequence[Mapping[str, Any]],
    *,
    current_state_version: Any,
) -> dict[str, Any]:
    """Revalidate one proposal's snapshot and target before the engine maps it.

    This guard is not a substitute for engine_bridge.validate_intent: the host
    engine must still map the proposal to a currently legal candidate and check
    action preconditions. A plan step is rejected when the snapshot version is
    missing/stale or the referenced target is no longer uniquely present.
    """
    def reject(reason: str) -> dict[str, Any]:
        return {"accepted": False, "status": "rejected", "reason": reason,
                "execution_allowed": False}

    if not isinstance(plan, Mapping) or plan.get("status") != "plan_proposal":
        return reject("invalid_plan")
    if plan.get("execution_allowed") is not False:
        return reject("plan_must_remain_non_executable")
    if not isinstance(step_index, int) or isinstance(step_index, bool) or step_index < 1:
        return reject("invalid_step_index")
    steps = plan.get("steps")
    if not isinstance(steps, list) or step_index > len(steps):
        return reject("step_index_out_of_range")
    planned_version = plan.get("state_version")
    if planned_version is None or current_state_version is None:
        return reject("state_version_required_for_revalidation")
    if planned_version != current_state_version:
        return reject("stale_plan_state_version")
    if not isinstance(current_entities, (list, tuple)):
        return reject("current_entities_must_be_a_list")

    step = steps[step_index - 1]
    if not isinstance(step, Mapping) or step.get("index") != step_index:
        return reject("malformed_plan_step")
    proposal = step.get("proposal")
    if not isinstance(proposal, Mapping) or proposal.get("status") != "proposal":
        return reject("step_is_not_a_proposal")
    if proposal.get("execution_allowed") is not False:
        return reject("step_must_remain_non_executable")
    command = step.get("command")
    if not isinstance(command, str) or not command.strip():
        return reject("step_command_missing")

    # Re-interpret the original step against the current entity snapshot.
    # Do not trust mutable plan fields as the source of intent/target truth.
    try:
        recomputed = interpret_player_command(command, current_entities)
    except CommandInputError:
        return reject("step_command_cannot_be_revalidated")
    if recomputed.get("status") != "proposal":
        return reject("step_command_no_longer_resolves")
    intent = proposal.get("intent")
    if intent != recomputed.get("intent"):
        return reject("proposal_intent_does_not_match_command")
    if proposal.get("target") != recomputed.get("target"):
        return reject("proposal_target_does_not_match_command")
    proposal_grounding = proposal.get("grounding")
    recomputed_grounding = recomputed.get("grounding")
    if not isinstance(proposal_grounding, Mapping) or not isinstance(recomputed_grounding, Mapping):
        return reject("proposal_grounding_missing")
    for field in ("status", "entity_id", "entity_name"):
        if proposal_grounding.get(field) != recomputed_grounding.get(field):
            return reject("proposal_grounding_does_not_match_command")

    allowed_intents = {"tactical_attack", "tactical_defend", "heal_request", "help_request"}
    if intent not in allowed_intents:
        return reject("unsupported_proposal_intent")

    target = proposal.get("target")
    if intent in {"tactical_attack", "tactical_defend"} and target is None:
        return reject("action_target_required")
    grounding = proposal.get("grounding")
    if target is not None:
        if not isinstance(target, Mapping):
            return reject("malformed_target_reference")
        target_id = target.get("entity_id")
        target_name = target.get("entity_name")
        if not isinstance(target_id, str) or not target_id or not isinstance(target_name, str):
            return reject("malformed_target_reference")
        if not isinstance(grounding, Mapping) or grounding.get("status") != "grounded":
            return reject("target_not_grounded_by_proposal")
        if grounding.get("entity_id") != target_id or grounding.get("entity_name") != target_name:
            return reject("target_does_not_match_grounding")
        matches = [
            entity for entity in current_entities
            if isinstance(entity, Mapping) and entity.get("id") == target_id
        ]
        if len(matches) != 1:
            return reject("target_missing_or_not_unique_in_current_snapshot")
        if matches[0].get("name") != target_name:
            return reject("target_identity_changed")
    return {
        "accepted": True,
        "status": "validated_step_proposal_engine_must_check_current_action_legality",
        "step_index": step_index,
        "command": step.get("command"),
        "proposal": dict(proposal),
        "state_version": current_state_version,
        "execution_allowed": False,
        "engine_requirement": "map_to_current_legal_candidate_and_revalidate_preconditions_before_execution",
    }
