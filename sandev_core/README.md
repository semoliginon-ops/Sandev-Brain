# SANDEV Brain Core (model-independent)

This folder is the first executable, model-independent game-intelligence module.
It uses only Python's standard library; it does not download or load model weights
and does not call a cloud model.

## Current capability

- Normalize numeric needs into urgency scores.
- Score available actions against urgent needs and long-term goals.
- Reject actions absent from a game's allow-list.
- Reject candidates whose declared state preconditions are not met.
- Return a deterministic action intent with an explanation and rejected-candidate list.
- Leave all world-state changes and success/failure confirmation to the game engine.

## Adapter contract

A game adapter provides a structured state snapshot, numeric needs (0–100, where
higher means more urgent), goals such as `{"tag":"save_money","priority":0.8}`,
and candidate actions. Each candidate declares a stable `action_id`, engine-known
action `kind`, optional target, need tags, goal tags, preconditions, base score,
and optional cost.

Preconditions support exact values and simple numeric/object conditions: `min`,
`max`, `equals`, and `not_equals`. Dotted paths address nested state fields.
Missing fields fail closed. The core only proposes an intent; the adapter/engine
must independently validate and execute it, then report the confirmed outcome.

## Test locally

From the repository root:

```sh
PYTHONPATH=sandev_core python -m unittest discover -s sandev_core -v
PYTHONPATH=smollm python -m unittest discover -s smollm -v
```

## Limits — not yet a finished AI

This is a transparent rule/scoring baseline, not general language understanding,
not trained intelligence, and not evidence that teacher-model capabilities have
been transferred. It currently needs structured game state and pre-authored
candidate actions. Next work should add outcome-based evaluation, goal conflict
handling, structured memory integration, and more cross-genre scenarios before
calling it production-ready.
