"""Sequential, snapshot-aware execution coordinator for SANDEV Brain.

The executor never mutates game state itself. The host callback must atomically
compare the expected version, enforce authoritative game rules, execute exactly
one action, and return explicit engine confirmation.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from planner import plan_player_command, validate_plan_step


class SequentialExecutionError(ValueError):
    """Raised when executor configuration or an input plan is malformed."""


class SequentialActionExecutor:
    """Re-plan, validate, and delegate one step at a time against fresh snapshots.

    Snapshot callback contract:
        get_snapshot() -> {
            "state_version": <required opaque version>,
            "entities": [<current engine entities>],
            "context": {<optional current context>},
        }

    Engine callback contract:
        execute_step(proposal, snapshot, expected_version) -> {
            "confirmed": bool,
            "result": {<engine-confirmed outcome>},
        }

    The host callback MUST atomically re-check the live state version, candidate,
    allow-list, and preconditions before changing the world. This coordinator is
    a sequencing helper, not an authoritative engine or transaction manager.
    """

    def __init__(self, *, max_steps: int = 10):
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= 10:
            raise SequentialExecutionError("max_steps must be an integer between 1 and 10")
        self.max_steps = max_steps

    @staticmethod
    def _read_snapshot(get_snapshot: Callable[[], Mapping[str, Any]]) -> dict[str, Any]:
        raw = get_snapshot()
        if not isinstance(raw, Mapping):
            raise SequentialExecutionError("snapshot must be an object")
        version = raw.get("state_version")
        entities = raw.get("entities")
        context = raw.get("context", {})
        if version is None:
            raise SequentialExecutionError("snapshot state_version is required")
        if not isinstance(entities, (list, tuple)):
            raise SequentialExecutionError("snapshot entities must be a list")
        if not isinstance(context, Mapping):
            raise SequentialExecutionError("snapshot context must be an object")
        normalized_context = dict(context)
        if "state_version" in normalized_context and normalized_context["state_version"] != version:
            raise SequentialExecutionError("snapshot context state_version does not match snapshot")
        normalized_context["state_version"] = version
        return {
            **dict(raw),
            "state_version": version,
            "entities": list(entities),
            "context": normalized_context,
        }

    def execute(
        self,
        plan: Mapping[str, Any],
        *,
        get_snapshot: Callable[[], Mapping[str, Any]],
        execute_step: Callable[[Mapping[str, Any], Mapping[str, Any], Any], Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Execute a proposed sequence with a fresh parse/validation per step."""
        if not isinstance(plan, Mapping) or plan.get("status") != "plan_proposal":
            raise SequentialExecutionError("plan must be a plan_proposal")
        if plan.get("execution_allowed") is not False:
            raise SequentialExecutionError("plan must remain non-executable")
        steps = plan.get("steps")
        if not isinstance(steps, list) or not steps:
            raise SequentialExecutionError("plan must contain at least one step")
        if len(steps) > self.max_steps:
            raise SequentialExecutionError("plan exceeds executor max_steps")
        if not callable(get_snapshot) or not callable(execute_step):
            raise SequentialExecutionError("snapshot and engine callbacks must be callable")

        outcomes: list[dict[str, Any]] = []
        for index, planned_step in enumerate(steps, start=1):
            if not isinstance(planned_step, Mapping) or planned_step.get("index") != index:
                return {
                    "accepted": False, "status": "stopped", "reason": "malformed_plan_step",
                    "completed_steps": outcomes, "next_step": index,
                    "execution_confirmed": False,
                }
            command = planned_step.get("command")
            if not isinstance(command, str) or not command.strip():
                return {
                    "accepted": False, "status": "stopped", "reason": "step_command_missing",
                    "completed_steps": outcomes, "next_step": index,
                    "execution_confirmed": False,
                }

            try:
                snapshot = self._read_snapshot(get_snapshot)
                fresh_plan = plan_player_command(
                    command,
                    snapshot["entities"],
                    context=snapshot["context"],
                    max_steps=1,
                )
                if fresh_plan.get("status") != "plan_proposal" or fresh_plan.get("step_count") != 1:
                    return {
                        "accepted": False, "status": "stopped",
                        "reason": "step_no_longer_resolves_in_current_snapshot",
                        "detail": fresh_plan.get("reason"),
                        "completed_steps": outcomes, "next_step": index,
                        "execution_confirmed": False,
                    }
                validation = validate_plan_step(
                    fresh_plan,
                    1,
                    snapshot["entities"],
                    current_state_version=snapshot["state_version"],
                    current_context=snapshot["context"],
                )
                if not validation.get("accepted"):
                    return {
                        "accepted": False, "status": "stopped",
                        "reason": validation.get("reason", "step_revalidation_failed"),
                        "completed_steps": outcomes, "next_step": index,
                        "execution_confirmed": False,
                    }
                engine_response = execute_step(
                    validation["proposal"], snapshot, snapshot["state_version"]
                )
                if not isinstance(engine_response, Mapping):
                    raise SequentialExecutionError("engine response must be an object")
                confirmed = engine_response.get("confirmed")
                if not isinstance(confirmed, bool):
                    raise SequentialExecutionError("engine response must include boolean confirmed")
                result = engine_response.get("result", {})
                if not isinstance(result, Mapping):
                    raise SequentialExecutionError("engine result must be an object")
            except Exception as exc:
                return {
                    "accepted": False, "status": "stopped",
                    "reason": "snapshot_or_engine_callback_failed",
                    "error_type": type(exc).__name__,
                    "completed_steps": outcomes, "next_step": index,
                    "execution_confirmed": False,
                }

            if not confirmed:
                return {
                    "accepted": False, "status": "stopped",
                    "reason": "engine_did_not_confirm_step",
                    "completed_steps": outcomes, "next_step": index,
                    "execution_confirmed": False,
                }
            outcomes.append({
                "step_index": index,
                "command": command,
                "execution_confirmed": True,
                "result": dict(result),
                "state_version_before": snapshot["state_version"],
            })

        return {
            "accepted": True,
            "status": "completed",
            "completed_steps": outcomes,
            "completed_step_count": len(outcomes),
            "execution_confirmed": True,
        }
