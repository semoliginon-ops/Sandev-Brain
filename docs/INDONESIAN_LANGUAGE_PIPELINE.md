# Indonesian Language Pipeline

## Purpose

SANDEV Brain must understand player language as well as make game decisions. This document separates the implemented baseline from the intended pipeline so that rule matching is not mistaken for open-ended language understanding.

## Current message path

1. **Raw input** — `context.py:build_context` preserves the player's message verbatim within configured limits and labels it `raw_uninterpreted_input`. The host remains authoritative for world state.
2. **Intent baseline** — `intent.py:classify_intent` normalizes text and matches curated Indonesian phrases. It can return `matched`, `unknown`, or `ambiguous`; the score is rule-match strength, not a calibrated probability.
3. **Interpretation envelope** — `intent.py:interpret_message` wraps the baseline with explicit `speech_act`, `temporal_scope`, `negation`, clarification fields, target-grounding status, and `execution_allowed: false`. These fields are conservative heuristics, not full grammatical analysis.
4. **Command safeguards** — `command.py:interpret_player_command` rejects or abstains on unsupported action wording, negation, questions/action alternatives, recounted actions, future intentions, and multi-step instructions it cannot safely plan.
5. **Entity grounding** — `grounding.py` resolves names and aliases against the current engine-supplied entity list. Pronouns and spatial descriptions require explicit context or relation metadata from the host.
6. **Conversation response** — `conversation.py` and `language.py` select a curated authored response when the message and trusted context match a supported pattern. They do not generate novel sentences.
7. **Proposal and validation** — a recognized action can become a non-executable proposal. The engine bridge and host game must validate it against the latest authoritative state and game rules.
8. **Outcome and memory** — only explicit engine-confirmed outcomes may be recorded as such. A model suggestion, interpreted request, or pending proposal is not a world event.

## Interpretation envelope

`interpret_message(message, context=None)` returns a versioned envelope with:

- `speech_act`: command, question, statement, mention, cancellation, or unclear;
- `temporal_scope`: immediate, past/recounted, future/intended, or unspecified;
- `negation`: detected, not detected, or uncertain;
- `intent` and `intent_status`: a supported label or unknown plus baseline status;
- `target_grounding`: unresolved for action intents until a separate grounding step, otherwise not applicable;
- `needs_clarification` and `clarification_reason`;
- `execution_allowed`: always `false` at this stage.

This is a first explicit interface, not a claim that all Indonesian grammar is understood. In particular, `not_detected` does not prove a message is positive; rule-based negation and temporal-scope checks are incomplete. A downstream host must still ground targets, validate actions, and execute through its authoritative rules.

## Evaluation rules

- Keep development examples separate from a fresh, untouched evaluation set.
- Do not tune rules or phrase lists against the held-out set.
- Report total accuracy and per-intent results, including unknown/ambiguous cases and false action proposals.
- Include Indonesian casual spelling, paraphrases, mixed clauses, negation, correction, questions, quoted/recounted actions, future plans, pronouns, and target ambiguity.
- Prioritize safety errors separately: a conversational mention or future intention becoming an immediate action is more serious than a supported request returning unknown.
- Treat a perfect score on hand-authored regression cases as regression coverage, not proof of general language ability.

## Current limitations

The current interpreter is deterministic and narrow. It does not reliably solve open-domain dialogue, indirect requests, sarcasm, long-range conversational intent, or all Indonesian grammatical scope. The curated response selector does not create new language. A future language component must be evaluated independently and must never bypass grounding, proposal validation, or host-engine confirmation.

## Acceptance criteria for the next implementation stage

1. The interpretation output distinguishes commands from questions, statements, mentions, cancellation, and future intentions, using conservative heuristic signals.
2. Ambiguous or low-evidence messages request clarification or abstain.
3. Entity references are resolved only from current host-provided entities and explicit context.
4. Language interpretation cannot execute an action or claim an outcome.
5. Regression and untouched evaluation sets are reported separately.
