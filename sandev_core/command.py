"""Conservative interpretation of player commands into engine-checkable proposals.

This layer composes curated intent classification and current-snapshot entity
grounding. It does not execute commands or guess missing targets.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from grounding import GroundingInputError, ground_entities, resolve_context_reference
from intent import IntentInputError, classify_intent, normalize_text


class CommandInputError(ValueError):
    """Raised when command interpretation inputs are malformed."""


_ACTION_INTENTS = {"tactical_attack", "tactical_defend", "heal_request", "help_request"}
_MULTI_STEP_MARKERS = (
    r"\bkemudian\b",
    r"\blalu\b",
    r"\bsetelah\b",
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
    """Return a cautious proposal, never an executable game action."""
    if not isinstance(message, str):
        raise CommandInputError("message must be a string")
    if context is not None and not isinstance(context, Mapping):
        raise CommandInputError("context must be an object")

    try:
        normalized = normalize_text(message)
        interpretation = classify_intent(
            message,
            context={"game_id": context.get("game_id", "unspecified")} if context is not None else None,
        )
        grounding = ground_entities(message, entities)
        if grounding["status"] == "unresolved" and context is not None:
            contextual = resolve_context_reference(message, entities, context=context)
            if contextual["status"] != "unresolved" or contextual["reason"] != "no_supported_context_reference":
                grounding = contextual
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

    # Narrow imperative grammar: recognize an explicit attack verb even if
    # the phrase classifier lacks that exact sentence. The target is still
    # required to resolve against the current entity list below.
    explicit_attack = re.match(r"^(serang|tembak|hantam|bidik)\b", normalized)
    explicit_defend = re.match(r"^(lindungi|jaga|pertahankan)\b", normalized)
    if interpretation["status"] != "matched" and explicit_attack:
        interpretation = {
            **interpretation,
            "status": "matched",
            "intent": "tactical_attack",
            "reason": "explicit_attack_verb",
        }
    elif interpretation["status"] != "matched" and explicit_defend:
        interpretation = {
            **interpretation,
            "status": "matched",
            "intent": "tactical_defend",
            "reason": "explicit_defend_verb",
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
    target_required = intent == "tactical_attack"
    # Do not silently prefer a named entity when the same command also uses
    # a contextual pronoun. The pronoun may refer to a different entity, and
    # the current grammar cannot safely determine whether this is correction,
    # conjunction, or a choice (e.g. "Serang dia atau Goblin").
    if (
        target_required
        and grounding["status"] == "grounded"
        and re.search(r"\b(dia|dirinya)\b", normalized)
    ):
        return {
            "status": "ambiguous_target",
            "intent": intent,
            "target": None,
            "grounding": {
                **grounding,
                "status": "ambiguous",
                "entity_id": None,
                "entity_name": None,
                "candidates": grounding.get("candidates", []),
                "reason": "named_target_conflicts_with_contextual_pronoun",
            },
            "reason": "named_target_conflicts_with_contextual_pronoun",
            "execution_allowed": False,
        }
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


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise CommandInputError("input must be a JSON object")
    result = interpret_player_command(
        payload.get("message"),
        payload.get("entities"),
        context=payload.get("context"),
    )
    print(json.dumps(result, ensure_ascii=False))
