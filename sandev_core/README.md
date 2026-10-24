# SANDEV Brain Core (model-independent)

This folder contains executable, model-independent game-intelligence components. It uses only the Python standard library; it does not download/load model weights and does not call a cloud model.

## Current capability

- Normalize numeric needs into urgency scores.
- Score available actions against urgent needs and long-term goals.
- Reject actions absent from a game's allow-list or whose preconditions fail.
- Return deterministic action intents with explanations and rejected-candidate lists.
- Validate a shared, versioned JSON-like adapter contract for different game genres.
- Store only engine-confirmed events and player-approved facts in a structured memory ledger.
- Retrieve memories by tags and let newer verified facts replace older values.
- Record engine-confirmed action outcomes and apply bounded, smoothed score nudges to the same action kind in the same tagged context.
- Run a small, hand-labeled regression benchmark spanning life simulation, shooter, and RPG decision cases.
- Leave world-state changes and action success/failure confirmation to the game engine.

## Generic adapter contract

adapter.py exposes `decide_from_snapshot(snapshot)`. A game supplies:
- `game_id` (optional identifier);
- `state` (game-specific structured state, preserved without assuming a genre);
- `needs` (numeric urgency values from 0 to 100);
- `goals` (tag and optional priority);
- `candidates` (stable action ID, action kind, optional target/tags/preconditions/score/cost);
- `allowed_actions` (the engine-approved action kinds this actor may request).

The adapter validates the input envelope and candidate shapes, rejects duplicate action IDs and non-finite numeric scores, and returns a versioned intent envelope. The core still checks the action allow-list and preconditions. Example snapshots for a plane shooter companion, RPG hero, and life-simulation character use the same contract. The game engine must independently validate the returned intent immediately before execution; an intent is not proof that an action happened. The adapter does not read a live game engine or automatically create candidates — a game integration must supply current state and legal options.

## Memory trust boundary

The memory ledger accepts only `engine_confirmed` events and `player_approved` facts. The outcome ledger accepts only `engine_confirmed` action results. Both deliberately reject teacher/model-generated suggestions as trusted evidence. Outcome feedback is isolated to an exact set of context tags and uses smoothing plus a minimum-sample confidence ramp, so a single result does not create certainty. These are foundations, not a complete belief system: advanced contradiction handling, privacy controls, retention policy, and relationship-specific memory remain future work.

## Regression benchmark

Run the hand-authored benchmark and view the per-scenario JSON report:

```sh
PYTHONPATH=sandev_core python -m sandev_core.benchmark
```

Run tests from the repository root:

```sh
PYTHONPATH=sandev_core python -m unittest discover -s sandev_core -v
PYTHONPATH=smollm python -m unittest discover -s smollm -v
```

The benchmark checks eight expected choices across a few structured scenarios. Its expected answers are manually authored regression labels, not independent human-study results or teacher-model outputs. A perfect score means only that the current deterministic baseline matches those labels; it is not a general intelligence score.

## Limits — not yet a finished AI

This is a transparent rule/scoring baseline plus verified memory and conservative outcome feedback, not general language understanding, not trained intelligence, and not evidence that teacher capabilities have been transferred. It still needs structured game state and pre-authored candidate actions. Language generation, open-ended companion chat, spontaneous dialogue, and personality continuity are not implemented yet. Next: connect reusable adapters to mock/real game-engine contracts and broaden tests before production.
