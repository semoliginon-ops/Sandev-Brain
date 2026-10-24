"""Engine-side validation bridge for SANDEV Brain action intents.

This is a safety boundary/demo contract, not a game-engine implementation.
The real host engine must still apply authoritative gameplay rules.
"""
from __future__ import annotations

from typing import Any, Mapping

from adapter import AdapterInputError
from brain import _preconditions_met


def validate_intent(snapshot: Mapping[str, Any], intent: Mapping[str, Any]) -> dict[str, Any]:
    """Re-check a proposed intent against the latest engine-provided snapshot.

    If state_version is present in the snapshot, the intent must carry the same
    version. A valid result is still only a command proposal for the host engine;
    this function never executes the command or reports a game outcome.
    """
    if not isinstance(snapshot, Mapping):
        raise AdapterInputError("snapshot must be an object")
    if not isinstance(intent, Mapping):
        raise AdapterInputError("intent must be an object")
    if intent.get("contract_version") != "1.0":
        return {"accepted": False, "status": "rejected", "reason": "unsupported contract version"}

    action_id = intent.get("action_id")
    action = intent.get("action")
    if not isinstance(action_id, str) or not action_id:
        return {"accepted": False, "status": "rejected", "reason": "missing action id"}
    if not isinstance(action, Mapping) or not isinstance(action.get("type"), str):
        return {"accepted": False, "status": "rejected", "reason": "empty or malformed intent"}

    if "state_version" in snapshot and intent.get("state_version") != snapshot.get("state_version"):
        return {"accepted": False, "status": "rejected", "reason": "stale state version"}

    candidates = snapshot.get("candidates")
    allowed = snapshot.get("allowed_actions")
    state = snapshot.get("state")
    if not isinstance(candidates, (list, tuple)) or not isinstance(allowed, (list, tuple)) or not isinstance(state, Mapping):
        raise AdapterInputError("snapshot requires candidates, allowed_actions, and object state")
    if action["type"] not in allowed:
        return {"accepted": False, "status": "rejected", "reason": "action not in current allow-list"}

    matches = [item for item in candidates if isinstance(item, Mapping) and item.get("action_id") == action_id]
    if len(matches) != 1:
        return {"accepted": False, "status": "rejected", "reason": "action id is not uniquely present in current candidates"}
    candidate = matches[0]
    if candidate.get("kind") != action.get("type") or candidate.get("target", "") != action.get("target", ""):
        return {"accepted": False, "status": "rejected", "reason": "intent does not match current candidate"}
    preconditions = candidate.get("preconditions", {})
    if not isinstance(preconditions, Mapping):
        raise AdapterInputError("candidate preconditions must be an object")
    feasible, reason = _preconditions_met(state, preconditions)
    if not feasible:
        return {"accepted": False, "status": "rejected", "reason": reason}

    return {
        "accepted": True,
        "status": "validated_proposal_engine_must_execute_and_confirm",
        "game_id": snapshot.get("game_id", "unspecified"),
        "action_id": action_id,
        "action": {"type": action["type"], "target": action.get("target", "")},
        "state_version": snapshot.get("state_version"),
    }
