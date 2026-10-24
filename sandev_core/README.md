# SANDEV Brain Core (model-independent)

This folder contains executable, model-independent game-intelligence components. It uses only the Python standard library; it does not download/load model weights and does not call a cloud model.

## Current capability

- Normalize numeric needs into urgency scores and score candidate actions against needs/goals.
- Reject actions outside a game's allow-list or whose preconditions fail.
- Return deterministic action intents with explanations and rejected-candidate lists.
- Validate a shared, versioned adapter contract for different game genres.
- Revalidate a proposed intent against the latest snapshot before the host engine considers execution.
- Assemble a bounded context packet from current state, explicit need urgency, goals, raw player message, recent verified events, and trusted memory.
- Classify a limited set of Indonesian player messages using transparent phrase patterns, with safe unknown/ambiguous results.
- Connect context packets, intent classification, and curated companion dialogue through a small conversation pipeline.
- Select curated dialogue lines by validated intent, genre, explicit urgent needs, and trusted context tags.
- Store only engine-confirmed events and player-approved facts in a structured memory ledger.
- Record engine-confirmed outcomes and apply bounded, smoothed feedback within matching contexts.
- Run regression scenarios across life simulation, shooter, and RPG decision cases.
- Leave execution, world-state changes, and outcome confirmation to the game engine.

## Generic adapter contract

`adapter.py` exposes `decide_from_snapshot(snapshot)`. A game supplies `game_id`, optional `state_version`, structured `state`, numeric `needs` (0–100 urgency), tagged `goals`, candidate actions, and `allowed_actions`. Candidate actions include a stable `action_id`, engine-known `kind`, optional `target`, tags, preconditions, base score, and cost.

The adapter validates candidate shapes, rejects duplicate IDs and non-finite numeric scores, and returns a versioned intent envelope. The game integration must supply current state and legal candidates; the adapter does not connect to a live engine or generate those candidates itself.

## Context packet

`context.py` exposes `build_context(...)`, which assembles a versioned JSON-safe packet with game/actor identifiers, current authoritative state, explicit need urgency, goals, the player's raw message, bounded recent events, and retrieved memories. It preserves the message verbatim within a configurable character limit and marks it as `raw_uninterpreted_input`: context assembly is not language understanding.

Recent events and retrieved memories are included only when their provenance is `engine_confirmed` or `player_approved`. The packet and state have configurable size limits. It does not infer current state from old memory, or generate dialogue, or call a model.

## Indonesian intent and contextual response baseline

`intent.py` exposes `classify_intent(message, context=None)`. It normalizes case and punctuation plus a few casual Indonesian spellings, then matches an auditable set of phrases. Current labels include greeting, thanks, farewell, help request, danger, healing, tactical attack/defense, comfort, and banter. It returns a matched phrase and rule-match strength, or fails closed as `unknown`/`ambiguous`. Immediate negation before a matched phrase is conservatively ignored, but this is not full grammatical negation understanding.

`conversation.py` exposes `respond_to_context(context, response_patterns)`: it validates the context packet, classifies its raw player message, and selects an authored response through `language.py`. Unknown or ambiguous messages yield no response instead of a guessed line. The result includes interpretation and response metadata for auditing. It does not execute game actions or generate novel sentences.

`intent_benchmark.py` provides a small, hand-authored regression set covering known phrases, unsupported messages, and ambiguity. Run it with `PYTHONPATH=sandev_core python -m intent_benchmark`. This is a sanity check, not a held-out or independent intelligence evaluation.

`intent_eval.py` adds an Indonesian paraphrase challenge set with per-intent breakdown and mismatch details. Run it with `PYTHONPATH=sandev_core python -m intent_eval`. It is diagnostic and reports the actual score rather than failing or hiding weak results. This set has been used during rule iteration, so it is a development diagnostic—not a held-out test. Create a fresh, untouched set before making claims about generalization.

The current interpreter is intentionally narrow: match strength is not a calibrated probability, game context is metadata only, and it does not reliably understand complex negation, sarcasm, indirect requests, or unseen phrasing. A context-only guess is not made. Expand it with reviewed examples and evaluate on a held-out set before making stronger language-understanding claims.

`language.py` selects among authored response patterns using the intent label supplied by the interpreter/caller. It can filter by game, trusted context tags, and urgent needs, with a deterministic tie-break and safe no-match result. This selector does not generate new sentences. Open-ended companion chat, spontaneous dialogue, broad Indonesian fluency, and personality consistency are not yet demonstrated.

## Engine bridge and trust boundary

`engine_bridge.py` checks that an intent still matches the current candidate, current allow-list, and current preconditions. If the snapshot includes `state_version`, a mismatched version rejects stale intents. Its success result means only “validated proposal”; it does not execute the action. The real game engine must enforce its authoritative gameplay rules and confirm the outcome.

The memory ledger accepts only `engine_confirmed` events and `player_approved` facts. The outcome ledger accepts only `engine_confirmed` results. Teacher/model-generated suggestions are not trusted as facts. This is a foundation, not a complete belief system; contradiction handling, privacy controls, retention policy, and relationship-specific memory remain future work.

## Tests and benchmark

Run from the repository root:

```sh
PYTHONPATH=sandev_core python -m unittest discover -s sandev_core -v
PYTHONPATH=smollm python -m unittest discover -s smollm -v
PYTHONPATH=sandev_core python -m sandev_core.benchmark
PYTHONPATH=sandev_core python -m intent_benchmark
PYTHONPATH=sandev_core python -m intent_eval
```

The game benchmark and intent regression set use hand-authored labels. Neither is an independent intelligence measurement.

## Language is a core goal

SANDEV Brain is intended to be a game system that is also good at language: understanding player messages, using context and memory, and producing relevant character dialogue. SmolLM2 is a development-time teacher/reference, not a gameplay runtime dependency. The final game-side system remains model-independent; language behavior must be built and evaluated explicitly rather than assumed to transfer automatically.
