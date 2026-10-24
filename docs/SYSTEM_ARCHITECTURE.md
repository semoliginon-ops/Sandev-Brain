# SANDEV Brain — target architecture

## Non-negotiable runtime rule

A game using SANDEV Brain must not load model weights or invoke a local/cloud LLM during gameplay. SmolLM2 is a development-time teacher/reference, not a dependency of the game build.

## Data flow

```text
Game world state + player input
          |
          v
Context assembler ----> Structured persistent memory
          |                      |
          +----------+-----------+
                     v
            Goal / need evaluator
                     |
                     v
           Decision and action planner
                     |
            +--------+--------+
            |                 |
            v                 v
      Dialogue behavior   Generic action intent
            |                 |
            v                 v
      Game-facing reply   Genre-specific adapter
                              |
                              v
                       Game engine validation
                              |
                              v
                     Confirmed world outcome
                              |
                              +----> memory update
```

## Current implementation milestone: deterministic decision baseline

The first independent core lives in `sandev_core/brain.py`. It uses only the Python standard library and has no model/runtime/network dependency. Current behaviors:
- normalize numeric need urgency to a 0..1 scale;
- score adapter-provided candidates against needs and prioritized goals;
- reject actions outside the adapter's allow-list;
- check declared state preconditions and fail closed on missing state;
- provide a deterministic tie-break and a reason for the selected intent;
- return an empty intent when no candidate is feasible.

This is deliberately a transparent baseline, not general intelligence. It assumes structured state and candidate actions are provided. It does not execute actions, update world state, generate open-ended dialogue, or prove successful transfer of teacher-model capabilities. GitHub Actions tests cover this baseline and the separate research harness without downloading model weights.

## What gets adapted from the teacher?

The teacher is used during development to create candidate examples and compare behaviors. Humans/tests label which outputs are correct. Validated examples become:
- dialogue patterns and response selection rules;
- structured memory schemas and retrieval policies;
- goal/need priorities and decision scoring;
- action preconditions, effects, and failure handling;
- reusable scenario tests and evaluation rubrics.

If a compact learned artifact is later justified, it must be demonstrably deployable as a normal game asset and must not require loading an LLM. No such artifact is currently claimed to exist.

## Genre independence

The core receives generic concepts such as needs, goals, relationships, inventory, threat, and available actions. Each game provides a schema and adapter:
- RPG: talk, explore, equip, attack, use item;
- shooter: seek cover, reload, flank, suppress, retreat;
- life simulation: eat, rest, work, socialize, maintain home.

The action adapter maps generic intent to real game commands and rejects invalid commands. The game engine is authoritative for success/failure.

## Memory and truth

Separate durable facts, recent events, inferred preferences, and uncertain beliefs. Give facts source/time/confidence metadata where possible. The model teacher may propose candidate memory text, but only confirmed engine events or explicitly approved player facts become durable truth. Newer verified facts can supersede old ones.

## Evaluation gates

- Dialogue: relevance, Indonesian fluency, character consistency, repetition.
- Context: correct grounding in current state and relevant history.
- Memory: recall, update, contradiction handling, forgetting/decay policy.
- Reasoning: success on held-out need/goal/constraint scenarios.
- Actions: valid-action rate, precondition compliance, outcome success, safe fallback.
- Portability: same core test suite works across multiple genre adapters.
- Runtime: no model download, no LLM weights, no network inference required.

Passing code tests is not proof of intelligence. Evaluate the system on fixed, held-out scenarios and compare it with teacher outputs and human labels.
