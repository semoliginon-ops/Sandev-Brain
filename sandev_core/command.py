"""Conservative interpretation of player commands into engine-checkable proposals.

This layer composes curated intent classification and current-snapshot entity
grounding. It does not execute commands or guess missing targets.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from grounding import GroundingInputError, ground_entities, resolve_context_reference
from intent import IntentInputError, interpret_message, normalize_text


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
        language_envelope = interpret_message(
            message,
            context={"game_id": context.get("game_id", "unspecified")} if context is not None else None,
        )
        # Keep the language layer's speech-act and temporal judgments attached
        # to the proposal pipeline. The envelope is descriptive only; it never
        # grants execution permission.
        interpretation = {
            **language_envelope,
            "status": language_envelope["intent_status"],
            "reason": language_envelope["reason"],
        }
        grounding = ground_entities(message, entities)
        if grounding["status"] == "unresolved" and context is not None:
            contextual = resolve_context_reference(message, entities, context=context)
            if contextual["status"] != "unresolved" or contextual["reason"] != "no_supported_context_reference":
                grounding = contextual
        # Enrich the language envelope with the grounding result produced from
        # the current engine snapshot; never infer a target from language alone.
        target_status = grounding["status"]
        language_envelope = {
            **language_envelope,
            "target_grounding": target_status,
        }
        if language_envelope.get("intent") in _ACTION_INTENTS:
            if target_status == "grounded":
                language_envelope.update({
                    "needs_clarification": language_envelope.get("intent_status") in {"unknown", "ambiguous"}
                    or language_envelope.get("speech_act") in {"question", "unclear", "cancellation", "mention"},
                    "clarification_reason": None,
                })
            else:
                language_envelope.update({
                    "needs_clarification": True,
                    "clarification_reason": (
                        "target_reference_is_ambiguous"
                        if target_status == "ambiguous"
                        else "action_target_requires_current_engine_grounding"
                    ),
                })
        interpretation["target_grounding"] = target_status
    except (IntentInputError, GroundingInputError) as exc:
        raise CommandInputError(str(exc)) from exc

    if any(re.search(marker, normalized) for marker in _MULTI_STEP_MARKERS):
        return {
            "status": "needs_planning",
            "intent": interpretation.get("intent", "unknown"),
            "target": None,
            "grounding": grounding,
            "language": language_envelope,
            "reason": "multi_step_instruction_not_planned",
            "execution_allowed": False,
        }

    # Narrow imperative grammar: recognize an explicit attack verb even if
    # the phrase classifier lacks that exact sentence. The target is still
    # required to resolve against the current entity list below.
    explicit_attack = re.match(r"^(serang|tembak|hantam|bidik)\b", normalized)
    explicit_defend = re.match(r"^(lindungi|jaga|pertahankan)\b", normalized)
    # A narrowly recognized imperative can enrich an otherwise unclear
    # language envelope, but only when no question, cancellation, negation, or
    # non-immediate temporal cue conflicts with that reading.
    if (
        interpretation.get("speech_act") == "unclear"
        and (explicit_attack or explicit_defend)
        and "?" not in message
        and interpretation.get("temporal_scope") == "unspecified"
        and interpretation.get("negation") == "not_detected"
    ):
        language_envelope = {
            **language_envelope,
            "speech_act": "command",
            "temporal_scope": "immediate",
            "needs_clarification": False,
            "clarification_reason": None,
        }
        interpretation.update({
            "speech_act": "command",
            "temporal_scope": "immediate",
            "needs_clarification": False,
            "clarification_reason": None,
        })
    # Questions and alternatives are not execution instructions, even when they
    # begin with an imperative verb ("Serang Goblin atau bertahan?").
    # Bypass the generic action-choice guard only when a named entity is
    # actually present in the text. A contextual focus may ground "dia", but
    # must not make "Serang dia atau bertahan?" look like a named-target choice.
    grounded_name = grounding.get("entity_name")
    named_entity_is_in_message = (
        isinstance(grounded_name, str)
        and bool(grounded_name)
        and re.search(
            r"(?<!\w)" + re.escape(normalize_text(grounded_name)) + r"(?!\w)",
            normalized,
        )
    )
    has_conflicting_named_pronoun = bool(
        re.search(r"\b(dia|dirinya)\b", normalized)
        and "atau" in normalized.split()
        and named_entity_is_in_message
    )
    if ("?" in message or "atau" in normalized.split()) and not has_conflicting_named_pronoun and (explicit_attack or explicit_defend):
        return {
            "status": "not_a_confident_action",
            "intent": "unknown",
            "target": None,
            "grounding": grounding,
            "language": language_envelope,
            "reason": "question_or_action_alternative_requires_clarification",
            "execution_allowed": False,
        }
    # The explicit-verb fallback must never override the language envelope's
    # speech-act or time-scope assessment. Past/recounted mentions and future
    # intentions are not immediate action orders; questions and cancellations
    # must be clarified before any proposal is formed.
    if (
        interpretation.get("speech_act") in {"question", "cancellation", "mention"}
        and not has_conflicting_named_pronoun
        or interpretation.get("temporal_scope") in {"future_intended", "past_or_recounted"}
        or interpretation.get("reason") in {
            "conversational_mention_is_not_an_action_order",
            "stated_intention_is_not_an_immediate_action_order",
        }
    ):
        return {
            "status": "not_a_confident_action",
            "intent": "unknown",
            "target": None,
            "grounding": grounding,
            "language": language_envelope,
            "reason": interpretation["reason"] if interpretation.get("reason") in {
                "conversational_mention_is_not_an_action_order",
                "stated_intention_is_not_an_immediate_action_order",
            } else (
                "question_or_cancellation_requires_clarification"
                if interpretation.get("speech_act") in {"question", "cancellation"}
                else "non_immediate_temporal_scope"
            ),
            "execution_allowed": False,
        }

    # If a direct attack command contains a negation anywhere, abstain rather than
    # guessing its scope (e.g. "Serang Goblin, jangan").
    if explicit_attack and any(word in {"tidak", "jangan", "bukan", "belum", "tak", "enggan"} for word in normalized.split()):
        return {
            "status": "not_a_confident_action",
            "intent": "unknown",
            "target": None,
            "grounding": grounding,
            "language": language_envelope,
            "reason": "negated_explicit_attack_requires_clarification",
            "execution_allowed": False,
        }
    if has_conflicting_named_pronoun and explicit_attack:
        # Preserve the ambiguity result for a mixed named-target/pronoun choice;
        # this only lets the explicit ambiguity guard below report the conflict.
        interpretation = {
            **interpretation,
            "status": "matched",
            "intent": "tactical_attack",
            "reason": "named_target_conflicts_with_contextual_pronoun",
        }
    elif interpretation["status"] == "unknown" and explicit_attack:
        interpretation = {
            **interpretation,
            "status": "matched",
            "intent": "tactical_attack",
            "reason": "explicit_attack_verb",
        }
    elif interpretation["status"] == "unknown" and explicit_defend:
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
            "language": language_envelope,
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
        and re.search(r"\b(dan|atau)\b", normalized)
    ):
        return {
            "status": "ambiguous_target",
            "intent": intent,
            "target": None,
            "language": language_envelope,
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
            "language": language_envelope,
            "reason": "target_mentions_are_ambiguous",
            "execution_allowed": False,
        }
    if target_required and grounding["status"] != "grounded":
        return {
            "status": "target_required",
            "intent": intent,
            "target": None,
            "grounding": grounding,
            "language": language_envelope,
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
        "language": language_envelope,
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
