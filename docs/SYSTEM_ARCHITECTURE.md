# SANDEV Brain — target architecture

## Non-negotiable runtime rule

A game using SANDEV Brain must not load model weights or invoke a local/cloud LLM during gameplay. SmolLM2 is a development-time teacher/reference, not a dependency of the game build.

## Product identity: game intelligence with language ability

SANDEV Brain is intended to be a reusable game-intelligence system that is also capable with language: it should interpret player messages, ground responses in the game and character context, use relevant memory, and produce coherent, context-aware dialogue. Decision-making and language are both core goals, not optional decorations. The standalone dialogue implementation and its quality are still unproven and must be built and evaluated explicitly.

## Data flow

```text
Game world state + player input
          |
          v
Bounded context assembler ----> Verified persistent memory
          |                            |
          +--------------+-------------+
                         v
              +----------+----------+
              |                     |
              v                     v
       Language/dialogue      Goal / need evaluator
          behavior                    |
              |                       v
              v              Decision and action planner
       Game-facing reply               |
                              Generic action intent
                                       |
                                       v
                              Genre adapter contract
                                       |
                                       v
                            Latest-state revalidation
                                       |
                                       v
                             Authoritative game engine
                                       |
                                       v
                             Confirmed world outcome
                                       |
                                       +----> memory/feedback
```

## Current implementation: deterministic decision baseline

`sandev_core/brain.py` scores adapter-provided candidates against need urgency and goals, enforces the allow-list and preconditions, provides explanations, and returns an empty intent when nothing is feasible. `sandev_core/adapter.py` validates a versioned generic snapshot contract across genres. `sandev_core/engine_bridge.py` rechecks candidate identity, allow-list, preconditions, and optional state version before returning a validated proposal. None of these modules executes actions or mutates world state.

`sandev_core/context.py` assembles current state, goals, the raw player message, recent provenance-checked events, and trusted retrieved memories into a bounded JSON-safe packet. This is context preparation, not natural-language understanding or generation. It marks the player message as uninterpreted input so later modules cannot mistake raw text for a verified fact.

This is a transparent baseline, not general intelligence. It still depends on game integrations to provide structured state and candidate actions.

## What gets adapted from the teacher?

During development, the teacher can help generate candidate examples and compare behaviors. Humans and tests label what is correct. Validated examples may inform:
- dialogue patterns, response-selection behavior, and language evaluation cases;
- structured memory schemas and retrieval policies;
- goal/need priorities and decision scoring;
- action preconditions, effects, and failure handling;
- reusable scenario tests and evaluation rubrics.

There is no claim that teacher-model capabilities have already transferred. Any future compact artifact must be justified by evaluation and usable as a normal game asset without an LLM runtime.

## Genre independence

The same core contract can represent RPG actions (talk, explore, equip, attack, use item), shooter actions (seek cover, reload, flank, retreat), and life-simulation actions (eat, rest, work, socialize, maintain home). Each game provides the current state and legal candidate actions. The game engine remains authoritative.

The host-facing schema, genre examples, execution handoff, and acceptance checklist are specified in [GAME_ENGINE_INTEGRATION_CONTRACT.md](GAME_ENGINE_INTEGRATION_CONTRACT.md). Treat it as a checklist for each new game integration, not as evidence that the integration already exists.

## Memory and truth

Separate durable facts, recent events, inferred preferences, and uncertain beliefs. Record provenance and confidence where useful. Teacher-generated suggestions are not game truth; only confirmed engine events or explicitly approved player facts may become durable facts. The context assembler filters history by provenance, but comprehensive contradiction handling, privacy controls, retention, and forgetting policies are still future work.

## Evaluation gates

- Language: relevance, Indonesian fluency, grounding, consistency, repetition, and response safety.
- Context: correct use of current state and relevant history.
- Memory: recall, update, contradiction handling, and forgetting/decay policy.
- Reasoning: success on held-out need/goal/constraint scenarios.
- Actions: valid-action rate, precondition compliance, outcome success, and safe fallback.
- Portability: shared tests across multiple genre adapters.
- Runtime: no model download, LLM weights, or network inference required.

Passing code tests is not proof of intelligence. Evaluate fixed held-out scenarios against teacher outputs and human labels.
