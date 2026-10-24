"""Small integration pipeline for context -> intent -> curated dialogue.

This composes existing deterministic modules. It does not generate new language,
execute game actions, or treat the player message as verified game state.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from intent import IntentInputError, classify_intent
from language import LanguageInputError, select_response


class ConversationPipelineError(ValueError):
    """Raised when the context packet is not valid for the conversation pipeline."""


def respond_to_context(
    context: Mapping[str, Any],
    response_patterns: Sequence[Mapping[str, Any]],
    *,
    max_chars: int = 280,
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
        interpretation = classify_intent(message, context={"game_id": context.get("game_id", "unspecified")})
    except IntentInputError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    if interpretation["status"] != "matched":
        return {
            "status": "no_response",
            "text": None,
            "interpretation": interpretation,
            "response": None,
            "reason": "intent_not_confidently_matched",
        }

    try:
        response = select_response(
            context, response_patterns, intent=interpretation["intent"], max_chars=max_chars
        )
    except LanguageInputError as exc:
        raise ConversationPipelineError(str(exc)) from exc

    if response["status"] != "no_matching_response":
        return {
            "status": "response_selected",
            "text": response["text"],
            "interpretation": interpretation,
            "response": response,
            "reason": "matched_intent_and_curated_response",
        }
    return {
        "status": "no_response",
        "text": None,
        "interpretation": interpretation,
        "response": response,
        "reason": "no_curated_response_for_intent_and_context",
    }
