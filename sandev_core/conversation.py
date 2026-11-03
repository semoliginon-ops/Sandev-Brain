"""Small integration pipeline for context -> intent -> curated dialogue.

This composes existing deterministic modules. It does not generate new language,
execute game actions, or treat the player message as verified game state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from intent import IntentInputError, classify_intent
from language import LanguageInputError, select_response
from followup import FollowUpInputError, resolve_follow_up
from facts import FactLookupError, retrieve_entity_fact
from response_composer import ResponseComposerError, compose_fact_response
from personality import PersonalityError, apply_personality_style, apply_emotion_style


class ConversationPipelineError(ValueError):
    """Raised when the context packet is not valid for the conversation pipeline."""


def respond_to_context(
    context: Mapping[str, Any],
    response_patterns: Sequence[Mapping[str, Any]],
    *,
    max_chars: int = 280,
    reference_catalog: Sequence[Mapping[str, Any]] = (),
    entity_facts: Sequence[Mapping[str, Any]] = (),
    npc_personality: str = "neutral",
) -> dict[str, Any]:
    """Interpret the raw message in a context packet and select authored dialogue.

    Unknown/ambiguous input deliberately produces no dialogue line, rather than
    guessing an intent. Successful output includes both interpretation metadata
    and the selected authored response for easy auditing.
    """
    if not isinstance(context, Mapping):
        raise ConversationPipelineError("context must be an object")
    if context.get("context_version") != "1.0":
        raise ConversationPipelineError("unsupported context version")
    if context.get("player_message_status") != "raw_uninterpreted_input":
        raise ConversationPipelineError("context must mark player message as uninterpreted")
    message = context.get("player_message")
    if not isinstance(message, str):
        raise ConversationPipelineError("context.player_message must be a string")

    try:
        follow_up = resolve_follow_up(
            message,
            context.get("conversation_history", []),
            reference_catalog,
        )
    except FollowUpInputError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    try:
        fact_lookup = retrieve_entity_fact(
            follow_up.get("reference_id"), follow_up.get("aspect"), entity_facts
        )
    except FactLookupError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    try:
        fact_response = compose_fact_response(
            follow_up.get("reference_id"),
            follow_up.get("aspect"),
            fact_lookup,
            max_chars=max_chars,
            personality=npc_personality,
            emotional_state=context.get("npc_emotion"),
        )
    except ResponseComposerError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    try:
        interpretation = classify_intent(message, context={"game_id": context.get("game_id", "unspecified")})
    except IntentInputError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    if interpretation["status"] != "matched":
        if fact_response["status"] == "composed":
            return {
                "status": "fact_response_selected",
                "text": fact_response["text"],
                "interpretation": interpretation,
                "follow_up": follow_up,
                "fact_lookup": fact_lookup,
                "fact_response": fact_response,
                "response": None,
                "reason": "trusted_fact_composed_for_follow_up",
            }
        return {
            "status": "no_response",
            "text": None,
            "interpretation": interpretation,
            "follow_up": follow_up,
            "fact_lookup": fact_lookup,
            "fact_response": fact_response,
            "response": None,
            "reason": "intent_not_confidently_matched",
        }

    try:
        response = select_response(
            context, response_patterns, intent=interpretation["intent"], max_chars=max_chars
        )
    except LanguageInputError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    if response.get("status") != "no_matching_response":
        try:
            styled_response = apply_personality_style(
                response.get("text", ""), npc_personality, max_chars=max_chars
            )
        except PersonalityError as exc:
            raise ConversationPipelineError(str(exc)) from exc
        if styled_response["status"] != "styled":
            return {
                "status": "no_response", "text": None,
                "interpretation": interpretation, "follow_up": follow_up,
                "fact_lookup": fact_lookup, "fact_response": fact_response,
                "response": response, "reason": styled_response["reason"],
            }
        try:
            emotional_response = apply_emotion_style(
                styled_response["text"], context.get("npc_emotion"), max_chars=max_chars
            )
        except PersonalityError as exc:
            raise ConversationPipelineError(str(exc)) from exc
        if emotional_response["status"] != "styled":
            return {
                "status": "no_response", "text": None,
                "interpretation": interpretation, "follow_up": follow_up,
                "fact_lookup": fact_lookup, "fact_response": fact_response,
                "response": response, "reason": emotional_response["reason"],
            }
        response = dict(response)
        response["text"] = emotional_response["text"]
        response["mood"] = emotional_response["mood"]

    if response.get("status") != "no_matching_response":
        return {
            "status": "response_selected",
            "text": response["text"],
            "interpretation": interpretation,
            "follow_up": follow_up,
            "fact_lookup": fact_lookup,
            "fact_response": fact_response,
            "response": response,
            "reason": "matched_intent_and_curated_response",
        }
    if fact_response["status"] == "composed":
        return {
            "status": "fact_response_selected",
            "text": fact_response["text"],
            "interpretation": interpretation,
            "follow_up": follow_up,
            "fact_lookup": fact_lookup,
            "fact_response": fact_response,
            "response": response,
            "reason": "trusted_fact_composed_after_no_curated_match",
        }
    return {
        "status": "no_response",
        "text": None,
        "interpretation": interpretation,
        "follow_up": follow_up,
        "fact_lookup": fact_lookup,
        "fact_response": fact_response,
        "response": response,
        "reason": "no_curated_response_for_intent_and_context",
    }
