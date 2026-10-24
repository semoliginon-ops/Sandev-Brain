"""Conservative interpretation of player commands into engine-checkable proposals.

This layer composes curated intent classification and current-snapshot entity
grounding. It does not execute commands, infer missing targets, or split a
multi-step sentence into guessed actions.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from grounding import GroundingInputError, ground_entities
from intent import IntentInputError, classify_intent, normalize_text


class CommandInputError(ValueError):
    """Raised when command interpretation inputs are malformed."""


_ACTION_INTENTS = {
    "tactical_attack",
    "tactical_defend",
    "heal_request",
    "help_request",
}
_MULTI_STEP_MARKERS = (
    r"\bkemudian\b",
    r"\blalu\b",
    r"\ setelah\b",
    r"\bsetelah itu\b",
    r"\bsekaligus\b",
    r"\bdan kemudian\b",
)


def interpret_player_command(
    message: str,
    entities: Sequence[Mapping[str, Any]],
    *,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a cautious command proposal, never an executable game action.

    Only a confidently matched curated action intent can become a proposal.
    Multiple-step connectors are withheld for a future planner rather than
    silently reduced to the first recognized action. A mentioned target must
    resolve against the supplied current entity list; equal-length competing
    targets remain ambiguous.
    """
    normalized = normalize_text(message)
    if context is not None and not isinstance(context, Mapping):
        raise CommandInputError("context must be an object")

    try:
        interpretation = classify_intent(
            message,
            context={"game_id": context.get("game_id", "unspecified")} if context is not None else None,
        )
        grounding = ground_entities(message, entities)
    except (IntentInputError, GroundingInputError) as exc:
        raise CommandInputError(str(exc)) from exc

    if any(re.search(marker, normalized) for marker in _MULTI_STEP_MARKERS):
        return {
            "status": "needs_planning",
            "intent": interpretation.get("intent", "unknown"),
            "target": None,
            "grounding": grounding,
            "reason": "multi_step_instruction_not_planned",
            "execution_allowed": False,
        }

    if interpretation["status"] != "matched" or interpretation["intent"] not in _ACTION_INTENTS:
        return {
            "status": "not_a_confident_action",
            "intent": interpretation["intent"],
            "target": None,
            "grounding": grounding,
            "reason": interpretation["reason"],
            "execution_allowed": False,
        }

    intent = interpretation["intent"]
    # For combat/defense commands, explicit targets must resolve when entities
    # are mentioned. Defense can be self-directed without an entity target.
    target_required = intent == "tactical_attack"
    if grounding["status"] == "ambiguous":
        return {
            "status": "ambiguous_target",
            "intent": intent,
            "target": None,
            "grounding": grounding,
            "reason": "target_mentions_are_ambiguous",
            "execution_allowed": False,
        }
    if target_required and grounding["status"] != "grounded":
        return {
            "status": "target_required",
            "intent": intent,
            "target": None,
            "grounding": grounding,
            "reason": "attack_target_not_grounded_in_current_snapshot",
            "execution_allowed": False,
        }

    return {
        "status": "proposal",
        "intent": intent,
        "target": (
            {"entity_id": grounding["entity_id"], "entity_name": grounding["entity_name"]}
            if grounding["status"] == "grounded" else None
        ),
        "grounding": grounding,
        "reason": "single_curated_action_intent_with_current_context",
        "execution_allowed": False,
    }
