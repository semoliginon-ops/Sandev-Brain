# SANDEV Brain Core (model-independent)

This folder contains executable, model-independent game-intelligence components.
It uses only the Python standard library; it does not download/load model weights
and does not call a cloud model.

## Current capability

- Normalize numeric needs into urgency scores.
- Score available actions against urgent needs and long-term goals.
- Reject actions absent from a game's allow-list or whose preconditions fail.
- Return deterministic action intents with explanations and rejected-candidate lists.
- Store only engine-confirmed events and player-approved facts in a structured memory ledger.
- Retrieve memories by tags and let newer verified facts replace older values.
- Record engine-confirmed action outcomes and apply bounded, smoothed score nudges
  to the same action kind in the same tagged context.
- Run a small, hand-labeled regression benchmark spanning life simulation, shooter,
  and RPG decision cases.
- Leave world-state changes and action success/failure confirmation to the game engine.

## Adapter contract

A game adapter provides a structured state snapshot, numeric needs (0–100, where
higher means more urgent), goals such as `{"tag":"save_money","priority":0.8}`,
and candidate actions. Each candidate declares a stable `action_id`, engine-known
action `kind`, optional target, need tags, goal tags, preconditions, base score,
and optional cost.

Preconditions support exact values and simple conditions: `min`, `max`, `equals`,
and `not_equals`. Dotted paths address nested state fields. Missing fields fail
closed. Optional feedback adjustments are keyed by candidate `action_id` and
clamped to ±20 score points. The core only proposes an intent; the adapter/engine
must independently validate and execute it, then report the confirmed outcome.

## Memory trust boundary

The memory ledger accepts only `engine_confirmed` events and `player_approved`
facts. The outcome ledger accepts only `engine_confirmed` action results. Both
deliberately reject teacher/model-generated suggestions as trusted evidence.
Outcome feedback is isolated to an exact set of context tags and uses smoothing
plus a minimum-sample confidence ramp, so a single result does not create certainty.
These are foundations, not a complete belief system: advanced contradiction
handling, privacy controls, retention policy, and relationship-specific memory
remain future work.

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

The benchmark checks eight expected choices across a few structured scenarios.
Its expected answers are manually authored regression labels, not independent
human-study results or teacher-model outputs. A perfect score means only that
the current deterministic baseline matches those eight labels; it is not a
general intelligence score.

## Limits — not yet a finished AI

This is a transparent rule/scoring baseline plus verified memory and conservative
outcome feedback, not general language understanding, not trained intelligence,
and not evidence that teacher capabilities have been transferred. It still needs
structured game state and pre-authored candidate actions. Next: broaden the
benchmark and build reusable genre adapters before production.
