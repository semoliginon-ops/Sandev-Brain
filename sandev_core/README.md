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
- Coordinate sequential proposals against fresh snapshots while leaving authoritative execution and outcome confirmation to the game engine.
- Leave world-state changes and outcome confirmation to the game engine.

## Generic adapter contract

`adapter.py` exposes `decide_from_snapshot(snapshot)`. A game supplies `game_id`, optional `state_version`, structured `state`, numeric `needs` (0–100 urgency), tagged `goals`, candidate actions, and `allowed_actions`. Candidate actions include a stable `action_id`, engine-known `kind`, optional `target`, tags, preconditions, base score, and cost.

The adapter validates candidate shapes, rejects duplicate IDs and non-finite numeric scores, and returns a versioned intent envelope. The game integration must supply current state and legal candidates; the adapter does not connect to a live engine or generate those candidates itself.

An optional `npc_behavior` object can be included in the same snapshot to request a separate NPC behavior proposal. It contains `npc_id`, `player_id`, `allowed_actions`, and optional `personality`, `state`, `goals`, `relationship`, `emotion`, and `memories`. The NPC allow-list is independent of the primary action allow-list. The result is returned under `npc_behavior`; it is advisory only (`execution: not_performed`) and the game engine must validate and execute any action itself. Scoped memories and NPC goals are ignored unless their NPC/player IDs match the supplied pair and their provenance is trusted. NPC goal records use `tag`, optional integer `priority` (0–100, default 50), optional boolean `active` (default true), `source` (`engine_confirmed` or `player_approved`), `npc_id`, and `player_id`. Supported motivation tags include `survive`, `seek_shelter`, `protect_player`, `protect_territory`, `help_player`, `continue_task`, `complete_quest`, `earn_money`, `find_family`, `seek_revenge`, `socialize`, and `avoid_player`. Priority scales authored action preferences; unknown, inactive, untrusted, or incorrectly scoped goals cannot affect a proposal. Goals never bypass the NPC action allow-list. Omitting this object preserves the original adapter response.

## Context packet

`context.py` exposes `build_context(...)`, which assembles a versioned JSON-safe packet with game/actor identifiers, current authoritative state, explicit need urgency, goals, the player's raw message, bounded recent events, and retrieved memories. It preserves the message verbatim within a configurable character limit and marks it as `raw_uninterpreted_input`: context assembly is not language understanding.

When `max_conversation_turns` is set, the context builder retains the newest turns (not the oldest prefix) using a bounded rolling buffer. This protects immediate follow-up context while preserving the `unverified_dialogue` trust label; recent dialogue is never promoted into verified world facts.

Recent events and retrieved memories are included only when their provenance is `engine_confirmed` or `player_approved`. The packet and state have configurable size limits. It does not infer current state from old memory, or generate dialogue, or call a model.

## Indonesian intent and contextual response baseline

`intent.py` exposes `classify_intent(message, context=None)`. It normalizes case and punctuation plus a few casual Indonesian spellings, then matches an auditable set of phrases. Current labels include greeting, thanks, farewell, help request, danger, healing, tactical attack/defense, comfort, and banter. It returns a matched phrase and rule-match strength, or fails closed as `unknown`/`ambiguous`. Immediate negation before a matched phrase is conservatively ignored, but this is not full grammatical negation understanding.

`conversation.py` exposes `respond_to_context(context, response_patterns)`: it validates the context packet, classifies its raw player message, and selects an authored response through `language.py`. Unknown or ambiguous messages yield no response instead of a guessed line. The result includes interpretation and response metadata for auditing. It does not execute game actions or generate novel sentences.

`intent_benchmark.py` provides a small, hand-authored regression set covering known phrases, unsupported messages, and ambiguity. Run it with `PYTHONPATH=sandev_core python -m intent_benchmark`. This is a sanity check, not a held-out or independent intelligence evaluation.

`intent_eval.py` adds an Indonesian paraphrase challenge set with per-intent breakdown and mismatch details. Run it with `PYTHONPATH=sandev_core python -m intent_eval`. It is diagnostic and reports the actual score rather than failing or hiding weak results. This set has been used during rule iteration, so it is a development diagnostic—not a held-out test. Create a fresh, untouched set before making claims about generalization.

The current interpreter is intentionally narrow: match strength is not a calibrated probability, game context is metadata only, and it does not reliably understand complex negation, sarcasm, indirect requests, or unseen phrasing. A context-only guess is not made. Expand it with reviewed examples and evaluate on a held-out set before making stronger language-understanding claims.

`language.py` selects among authored response patterns using the intent label supplied by the interpreter/caller. It can filter by game, trusted context tags, and urgent needs, with a deterministic tie-break and safe no-match result. This selector does not generate new sentences. Open-ended companion chat, spontaneous dialogue, broad Indonesian fluency, and personality consistency are not yet demonstrated.

`compositional_dialogue.py` adds an early, bounded sentence-composition experiment. It accepts a game-produced semantic frame (speech act, tone, topic, relationship tier) and combines independently selected phrase components into a new line. It is deterministic, length-bounded, and rejects unsupported frame values; it never inserts raw player text into generated slots. This is compositional phrase grammar—not open-ended language generation, not a general Indonesian parser, and not evidence of LLM-level ability. Run its tests with `PYTHONPATH=sandev_core python -m unittest sandev_core.test_compositional_dialogue -v`.


`semantic_frame.py` converts a confidently matched interpretation into a bounded dialogue frame. It retains the semantic intent, source speech act, temporal scope, negation state, target-grounding status, confidence, game identifier, and trusted profile data. When given the versioned `interpret_message` envelope, it rejects questions, commands, mentions, cancellations, negated or uncertain interpretations, and any input that attempts to authorize execution. The legacy matched-intent input remains supported for compatibility. This is a validated semantic representation layer—not a raw-text parser or a generalization breakthrough. Run tests with `PYTHONPATH=sandev_core python -m unittest sandev_core.test_semantic_frame -v`.



`test_paraphrase_probes.py` adds focused probes for alternate comfort phrasings and nearby ambiguous/unsafe messages. Run with `PYTHONPATH=sandev_core python -m unittest sandev_core.test_paraphrase_probes -v`. These examples are development regression probes, not independent held-out evaluation; a fresh blind test set is still required before claiming generalization.

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

For the stage-by-stage message path, proposed interpretation fields, evaluation rules, and explicit limitations, see [Indonesian Language Pipeline](../docs/INDONESIAN_LANGUAGE_PIPELINE.md). The proposed shared interpretation envelope is a design target; it is not yet a fully implemented API.


SANDEV Brain is intended to be a game system that is also good at language: understanding player messages, using context and memory, and producing relevant character dialogue. SmolLM2 is a development-time teacher/reference, not a gameplay runtime dependency. The final game-side system remains model-independent; language behavior must be built and evaluated explicitly rather than assumed to transfer automatically.


## Entity grounding and contextual references

`grounding.py` exposes `ground_entities(message, entities)` for exact names and aliases from the current engine snapshot. It prefers a uniquely matching longest alias and returns ambiguity rather than choosing between equally plausible entities.

`resolve_context_reference(message, entities, context=...)` supports a deliberately small set of contextual references:
- “dia/dirinya” only when the engine supplies a valid `focus_entity_id`;
- “musuh di belakangnya” only when exactly one current entity is explicitly marked `is_hostile: true` and its engine-supplied `relations_to[focus_entity_id]` is `"behind"`.

The resolver does not infer spatial relationships from coordinates or invent a focus entity. Missing context yields unresolved results; multiple matching hostile entities yield ambiguity. `command.py` uses this resolver only when direct name grounding did not resolve the message. All command outputs remain proposals with `execution_allowed: false`; the game engine must revalidate and execute any action.


## Multi-step command planning

`planner.py` exposes `plan_player_command(message, entities, context=None, max_steps=5)`. It supports explicit sequential connectors such as “lalu”, “kemudian”, “setelah itu”, and “dan kemudian”, then interprets each clause independently against the current entity snapshot. It deliberately does not split on plain “dan” and refuses unsupported sequencing such as “sekaligus” rather than guessing whether actions are sequential or simultaneous.

A plan is returned only when every step resolves confidently. If any step has an unknown or ambiguous target, the planner returns no partial step list and requests clarification. A named defense target must also be grounded. Outputs always set `execution_allowed: false`; they are not a queue the game should blindly execute. The host engine must revalidate each step against a fresh snapshot immediately before execution and stop if the state version, target, preconditions, or legal actions change. This planner is a deterministic parser over a narrow grammar, not general natural-language planning.


### Per-step planner revalidation

`planner.py` also exposes `validate_plan_step(plan, step_index, current_entities, current_state_version=...)`. It rejects stale/missing state versions and targets that disappeared, became duplicated, or changed identity. Acceptance means only that the plan step still references the same snapshot and entity; the host engine must still map it to a currently legal action candidate and run `engine_bridge.validate_intent` before execution. After an action changes the world/state version, the remaining command should be re-planned against the new snapshot rather than blindly continuing an old sequence.


### Sequential action executor

`sequential_executor.py` exposes `SequentialActionExecutor.execute(plan, get_snapshot=..., execute_step=...)`. It takes the original plan's command text, obtains a fresh engine snapshot for each step, re-interprets that command against the current entities/context, and validates the resulting single-step proposal against that snapshot's state version. It delegates exactly one step at a time and proceeds only when the host callback explicitly returns `{"confirmed": true, "result": {...}}`.

The snapshot callback must provide `state_version` and current `entities`, plus optional current `context`. The engine callback receives the validated proposal, snapshot, and expected version. The host MUST atomically compare the live version, check the current candidate/allow-list/preconditions, execute the action, and return authoritative confirmation. If a target disappears, a command no longer resolves, a callback fails, or the engine does not confirm, the sequence stops and reports already-confirmed steps. This coordinator does not execute game actions, roll back prior steps, or make a multi-step sequence transactional. Run its tests with `PYTHONPATH=sandev_core python -m unittest sandev_core.test_sequential_executor -v`.


### Language proposal to live engine candidate mapping

`engine_bridge.py` exposes `resolve_language_proposal(snapshot, proposal, action_type_map=...)`. Each game integration must explicitly map language intents (for example, `tactical_attack`) to its own engine action kinds (for example, `attack`). The bridge then requires exactly one current candidate with the mapped kind and grounded entity ID as its target, and passes that candidate through the existing allow-list, state-version, and precondition checks in `validate_intent`. Untargeted proposals match only candidates with an empty target. Missing, duplicate, unmapped, stale, disallowed, or infeasible candidates are rejected.

This is the boundary between language meaning and game-specific mechanics: SANDEV does not assume every game uses the same action names. The game still owns the mapping and must atomically revalidate and execute the returned validated candidate. A successful bridge result is not an execution confirmation. The sequential executor's `execute_step` callback can call this resolver before asking the host engine to execute each step. Tests cover grounded-target mapping, duplicate candidates, allow-list/precondition rejection, and sequential use of the bridge.


### Indonesian intent diagnostic set

`heldout_intent_eval.py` contains 30 manually authored examples and reports overall accuracy, per-label accuracy, statuses, a confusion matrix, and every mismatch. The initial results have now been inspected, so treat this set as a diagnostic—not a pristine holdout or statistically representative benchmark. Run it with `PYTHONPATH=sandev_core python -m heldout_intent_eval`. Unknown predictions count as incorrect for examples with a specific expected intent. After further rule iteration, create a newly authored holdout before making generalization claims.

### Deterministic RPG runtime simulator

`game_runtime.py` provides a small end-to-end RPG simulator with a player, Goblin, Bandit, and one healing potion. It accepts a narrow Indonesian command, grounds the target against the current world, maps the language proposal to one current engine candidate, validates the allow-list/version/preconditions, and mutates the world only inside the engine callback. The callback returns explicit confirmation; the simulator then produces a short authored result line and a fresh world snapshot.

Try it from the repository root:

```sh
PYTHONPATH=sandev_core python -m game_runtime
```

Enter one command per line, such as `Serang Goblin` or `Pulihkan HP`. The simulator is a deterministic integration proof, not open-ended NPC language generation, a production game engine, or evidence of LLM-level language ability. Its command grammar and response lines remain limited and authored. Tests run with `PYTHONPATH=sandev_core python -m unittest sandev_core.test_game_runtime -v`.


### Companion personality and verified relationship memory

`companion.py` composes the bounded context builder, verified memory ledger, intent classifier, and curated response selector for one companion. A game may record a relationship event only after its engine confirms the interaction; each relationship adjustment is limited to -5..+5 and the accumulated score is clamped to -100..100. Personal facts require explicit `player_approved` provenance. Dialogue patterns may declare a `personality` field and `required_personality_tags` so the companion selects only compatible authored lines. Optional `min_relationship` and `max_relationship` bounds (integers from -100 to 100) gate lines by the current engine-confirmed relationship score. Generic patterns remain available as fallback. All verified facts—not only relationship-tagged events—are included in the bounded memory context, so player-approved details can influence dialogue when a pattern requires their tags.

Example:

```python
companion = CompanionRuntime(
    "save/aria-memory.json",
    companion_id="npc_aria",
    personality="warm",
    personality_tags=["kind", "curious"],
)
companion.record_confirmed_interaction(
    "Player saved Aria from a goblin",
    source="engine_confirmed",
    turn=12,
    relationship_delta=3,
    tags=["rescue"],
)
result = companion.respond(snapshot, "Halo!", response_patterns)
```

This layer gives NPCs persistent, provenance-checked history and a simple relationship signal, but dialogue remains selected from authored patterns. It does not yet create new sentences, infer emotional states from arbitrary conversation, or prove human-level relationship understanding. Tests: `PYTHONPATH=sandev_core python -m unittest sandev_core.test_companion -v`.


## NPC daily life and autonomous routine proposals

`npc_routine.py` exposes `propose_routine(context, allowed_activities=...)`. A game supplies an NPC ID, the current in-game minute (0–1439), weekday (0–6), flat authoritative state facts, a trusted schedule list, and an independent activity allow-list. Schedule entries require `activity_id`, same-day `start_minute`/`end_minute`, `source` (`engine_confirmed` or `player_approved`), and matching `npc_id`; optional `days`, `priority` (0–100), `active`, exact-match NPC `conditions`, exact-match world `world_conditions`, and `requires_nearby`/`forbids_nearby` entity-ID lists refine eligibility. The caller supplies authoritative flat `world` facts (such as weather and location) and `nearby_entity_ids`; SANDEV does not infer coordinates, distance, visibility, weather, or who is nearby. Windows include the start and exclude the end; overnight routines should be split across two days. Highest priority wins, then the narrower time window, then stable activity ID. Untrusted, wrong-NPC, inactive, condition-mismatched, or disallowed entries cannot be proposed. Missing eligible routines abstain. The proposal is returned separately under `npc_routine`, with `execution: not_performed`; the host engine must revalidate current time, world state, NPC availability, and activity legality before execution. Omitting `npc_routine` preserves the legacy adapter response. Tests: `PYTHONPATH=sandev_core python -m unittest sandev_core.test_npc_routine -v`.


## Cross-genre NPC social interaction proposals

`npc_social.py` exposes `propose_social_interaction(context, personality=..., allowed_actions=...)` as an optional, genre-neutral channel for NPC-to-NPC interaction. The host game supplies the acting NPC ID, the exact IDs of currently nearby NPCs, an independent social action allow-list, and trusted relationship snapshots for NPC pairs. The module can propose a greeting, conversation, help, avoidance, de-escalation, or group invitation when supported by the supplied relationship and current game-state facts.

Relationship records must identify an unordered NPC pair, carry an integer score from -100 to 100, and use `engine_confirmed` or `player_approved` provenance. Only records involving the acting NPC and an explicitly nearby target are considered. Optional state cues (`wants_socialize`, `conflict_active`, and `target_needs_help`) are booleans supplied by the game; SANDEV does not infer proximity, conflict, social intent, or need from dialogue. Selection is bounded and deterministic, with stable tie-breaking. Missing eligible facts or actions produce abstention.

The result is advisory only (`execution: not_performed`). The game engine must revalidate the target and action, perform the interaction, and confirm the outcome before updating its relationship ledger. The optional adapter field `npc_social` returns this proposal separately and does not change the primary game action. Omit it to preserve the legacy adapter response. This contract is deliberately independent of RPG mechanics: an RPG, life simulation, open-world, survival, strategy, or other game can map these abstract interaction IDs to its own legal actions. Tests: `PYTHONPATH=sandev_core python -m unittest sandev_core.test_npc_social -v`.
