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
    if not isinstance(action_id, str) or not action_id.strip():
        return {"accepted": False, "status": "rejected", "reason": "missing action id"}
    if not isinstance(action, Mapping) or not isinstance(action.get("type"), str) or not action["type"].strip():
        return {"accepted": False, "status": "rejected", "reason": "empty or malformed intent"}
    target = action.get("target", "")
    if not isinstance(target, str):
        return {"accepted": False, "status": "rejected", "reason": "intent target must be a string"}

    if "state_version" in snapshot and intent.get("state_version") != snapshot.get("state_version"):
        return {"accepted": False, "status": "rejected", "reason": "stale state version"}

    candidates = snapshot.get("candidates")
    allowed = snapshot.get("allowed_actions")
    state = snapshot.get("state")
    if not isinstance(candidates, (list, tuple)) or not isinstance(allowed, (list, tuple)) or not isinstance(state, Mapping):
        raise AdapterInputError("snapshot requires candidates, allowed_actions, and object state")
    if any(not isinstance(kind, str) or not kind.strip() for kind in allowed):
        raise AdapterInputError("allowed_actions must contain non-empty strings")
    if action["type"] not in allowed:
        return {"accepted": False, "status": "rejected", "reason": "action not in current allow-list"}

    matches = [item for item in candidates if isinstance(item, Mapping) and item.get("action_id") == action_id]
    if len(matches) != 1:
        return {"accepted": False, "status": "rejected", "reason": "action id is not uniquely present in current candidates"}
    candidate = matches[0]
    if not isinstance(candidate.get("action_id"), str) or not candidate["action_id"].strip():
        return {"accepted": False, "status": "rejected", "reason": "candidate action id must be a non-empty string"}
    if not isinstance(candidate.get("kind"), str) or not candidate["kind"].strip():
        return {"accepted": False, "status": "rejected", "reason": "candidate kind must be a non-empty string"}
    candidate_target = candidate.get("target", "")
    if not isinstance(candidate_target, str):
        return {"accepted": False, "status": "rejected", "reason": "candidate target must be a string"}
    if candidate.get("kind") != action["type"] or candidate_target != target:
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
        "action": {"type": action["type"], "target": target},
        "state_version": snapshot.get("state_version"),
    }


def resolve_language_proposal(
    snapshot: Mapping[str, Any],
    proposal: Mapping[str, Any],
    *,
    action_type_map: Mapping[str, str],
) -> dict[str, Any]:
    """Map a grounded language proposal to one unique current engine candidate.

    Games must explicitly provide intent->action-kind mappings. Targeted
    proposals match candidate.target to the grounded entity_id; untargeted
    proposals match the empty target. The returned object is validation only.
    """
    if not isinstance(snapshot, Mapping) or not isinstance(proposal, Mapping):
        raise AdapterInputError("snapshot and proposal must be objects")
    if proposal.get("status") != "proposal" or proposal.get("execution_allowed") is not False:
        return {"accepted": False, "status": "rejected", "reason": "language proposal is not safely actionable"}
    if not isinstance(action_type_map, Mapping):
        raise AdapterInputError("action_type_map must be an object")
    intent_name = proposal.get("intent")
    action_type = action_type_map.get(intent_name)
    if not isinstance(action_type, str) or not action_type.strip():
        return {"accepted": False, "status": "rejected", "reason": "intent has no game action mapping"}

    target_ref = proposal.get("target")
    if target_ref is None:
        target_id = ""
    elif isinstance(target_ref, Mapping) and isinstance(target_ref.get("entity_id"), str):
        target_id = target_ref["entity_id"]
    else:
        return {"accepted": False, "status": "rejected", "reason": "malformed grounded target"}

    candidates = snapshot.get("candidates")
    if not isinstance(candidates, (list, tuple)):
        raise AdapterInputError("snapshot candidates must be a list")
    matches = [
        candidate for candidate in candidates
        if isinstance(candidate, Mapping)
        and candidate.get("kind") == action_type
        and candidate.get("target", "") == target_id
    ]
    if len(matches) != 1:
        return {
            "accepted": False, "status": "rejected",
            "reason": "no_unique_current_candidate_for_language_proposal",
            "candidate_match_count": len(matches),
        }
    candidate = matches[0]
    intent = {
        "contract_version": "1.0",
        "action_id": candidate.get("action_id"),
        "action": {"type": action_type, "target": target_id},
        "state_version": snapshot.get("state_version"),
    }
    return validate_intent(snapshot, intent)
