# SANDEV Brain Core (model-independent)

This folder contains executable, model-independent game-intelligence components. It uses only the Python standard library; it does not download/load model weights and does not call a cloud model.

## Current capability

- Normalize numeric needs into urgency scores and score candidate actions against needs/goals.
- Reject actions outside a game's allow-list or whose preconditions fail.
- Return deterministic action intents with explanations and rejected-candidate lists.
- Validate a shared, versioned adapter contract for different game genres.
- Revalidate a proposed intent against the latest snapshot before the host engine considers execution.
- Assemble a bounded context packet from current state, goals, raw player message, recent verified events, and trusted memory.
- Store only engine-confirmed events and player-approved facts in a structured memory ledger.
- Record engine-confirmed outcomes and apply bounded, smoothed feedback within matching contexts.
- Run regression scenarios across life simulation, shooter, and RPG decision cases.
- Leave execution, world-state changes, and outcome confirmation to the game engine.

## Generic adapter contract

`adapter.py` exposes `decide_from_snapshot(snapshot)`. A game supplies `game_id`, optional `state_version`, structured `state`, numeric `needs` (0–100 urgency), tagged `goals`, candidate actions, and `allowed_actions`. Candidate actions include a stable `action_id`, engine-known `kind`, optional `target`, tags, preconditions, base score, and cost.

The adapter validates candidate shapes, rejects duplicate IDs and non-finite numeric scores, and returns a versioned intent envelope. The game integration must supply current state and legal candidates; the adapter does not connect to a live engine or generate those candidates itself.

## Context packet

`context.py` exposes `build_context(...)`, which assembles a versioned JSON-safe packet with game/actor identifiers, current authoritative state, goals, the player's raw message, bounded recent events, and retrieved memories. It preserves the message verbatim within a configurable character limit and marks it as `raw_uninterpreted_input`: context assembly is not language understanding.

Recent events and retrieved memories are included only when their provenance is `engine_confirmed` or `player_approved`. The packet and state have configurable size limits. It does not infer current state from old memory, decide what a message means, generate dialogue, or call a model. Future language behavior can consume this packet and must be evaluated separately.

## Engine bridge and trust boundary

`engine_bridge.py` checks that an intent still matches the current candidate, current allow-list, and current preconditions. If the snapshot includes `state_version`, a mismatched version rejects stale intents. Its success result means only “validated proposal”; it does not execute the action. The real game engine must enforce its authoritative gameplay rules and confirm the outcome.

The memory ledger accepts only `engine_confirmed` events and `player_approved` facts. The outcome ledger accepts only `engine_confirmed` results. Teacher/model-generated suggestions are not trusted as facts. This is a foundation, not a complete belief system; contradiction handling, privacy controls, retention policy, and relationship-specific memory remain future work.

## Tests and benchmark

Run from the repository root:

```sh
PYTHONPATH=sandev_core python -m unittest discover -s sandev_core -v
PYTHONPATH=smollm python -m unittest discover -s smollm -v
PYTHONPATH=sandev_core python -m sandev_core.benchmark
```

The small benchmark uses hand-authored regression labels. It is not an independent intelligence measurement.

## Language is a core goal

SANDEV Brain is intended to be a game system that is also good at language: understanding player messages, using context and memory, and producing relevant character dialogue. The teacher model is a development reference, not a runtime dependency. The standalone language/dialogue implementation is still future work; open-ended companion chat, spontaneous contextual lines, Indonesian fluency, and personality consistency have not yet been demonstrated. They must be built and tested explicitly rather than assumed to transfer automatically.
