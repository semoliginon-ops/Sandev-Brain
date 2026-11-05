# SANDEV Brain Roadmap

## Product target

Build a reusable game-intelligence system whose language capability can approach the quality and flexibility of a local LLM, while remaining adaptable across game genres. The shipped game runtime must not require GGUF, a GGUF loader, bundled LLM weights, or mandatory cloud inference.

Language is a core product goal alongside context, memory, decisions, and safe game actions. The current deterministic language components are an early foundation; they are **not yet equivalent to an LLM** and must not be described as such without independent evaluation.

## Status key

- [x] Implemented in the repository and covered by focused tests.
- [~] Partial foundation exists; integration, coverage, or validation remains.
- [ ] Not implemented or not yet demonstrated.

## Current verified baseline

The current `smollm2-adaptation` branch contains:

- A model-independent decision core with need/goal scoring, action allow-lists, precondition checks, and deterministic intent output.
- A versioned generic game snapshot adapter, with regression examples for life simulation, shooter, and RPG.
- A file-backed memory ledger that accepts only engine-confirmed events and player-approved facts.
- Bounded context assembly, a limited phrase-based Indonesian intent baseline, curated response selection, and an early deterministic compositional-dialogue experiment.
- A conservative command/planning path that returns proposals, plus validation and sequential-execution coordination that require the host engine to confirm actual outcomes.
- CPU-only tests that do not download model weights.

Important gaps remain: there is no demonstrated open-ended, naturally generative Indonesian NPC conversation; the current phrase matcher and authored/compositional responses are not LLM-level language ability. No real commercial/game-engine integration, trained language artifact, independent broad language benchmark, or target-phone performance result has been established.

## Phase 0 — Define and measure the target

- [~] Document the product boundary and reusable cross-genre integration contract.
- [ ] Define target devices, RAM/storage limits, latency budgets, and offline requirements with measurable acceptance thresholds.
- [~] Maintain a small decision regression benchmark; expand it into repeatable measurements for language quality, context use, memory consistency, action outcomes, and response time.
- [ ] Define representative NPC tasks and human-reviewed acceptance criteria for natural, contextual dialogue.

## Phase 1 — Reliable reusable game-intelligence foundation

- [x] Define a versioned generic snapshot contract for game state, needs, goals, legal candidates, and action allow-lists.
- [x] Implement deterministic need/goal scoring, precondition checks, and safe no-action fallback.
- [x] Implement a file-backed memory ledger with provenance restrictions and bounded retrieval.
- [~] Assemble bounded context from current state, recent trusted events, and retrieved memories; complete contradiction, expiry, privacy, and forgetting policies.
- [~] Produce versioned action proposals and revalidate them against current candidates/state; real host-engine validation and atomic execution remain integration responsibilities.
- [~] Coordinate multi-step proposals against fresh snapshots and explicit engine confirmations; retry/timeout policy and real-engine failure recovery remain to be proven in host integrations.
- [ ] Integrate the contract into at least one real game and verify actual state changes and confirmed outcomes.

## Phase 2 — Natural language, dialogue, and intent

- [~] Parse a limited set of Indonesian commands with conservative unknown/ambiguous handling.
- [~] Ground supported entity references and command proposals against game-provided entities and legal actions.
- [~] Select curated responses using intent, genre, trusted context, and authored personality/emotion signals.
- [~] Prototype bounded compositional dialogue from validated semantic frames.
- [ ] Build a language system that can produce varied, coherent, context-aware NPC dialogue beyond fixed phrase patterns and authored response catalogs.
- [ ] Support multi-turn conversation, indirect requests, nuanced negation, paraphrases, questions, humor, and changing relationships robustly across genres.
- [ ] Evaluate Indonesian fluency, relevance, grounding, consistency, repetition, and safety on a fresh, independently held-out dataset with human review.

## Phase 3 — Teacher research and lightweight implementation

- [~] Maintain a teacher/research harness and starter train/evaluation data without making teacher weights a game-runtime dependency.
- [ ] Compare candidate teacher approaches and document exact licenses, data rights, tokenizer requirements, and reproducibility.
- [ ] Establish a validated method to transfer useful language behavior into a compact, ordinary game asset or other model-independent runtime representation.
- [ ] Run training/adaptation experiments only when suitable compute and evaluation gates are available; record actual artifacts and reproducible results.
- [ ] Measure storage, RAM, startup time, and latency on representative target devices before setting a shipping footprint.
- [ ] Verify that the shipped runtime works offline without GGUF, an LLM loader, model weights, or cloud inference.

## Phase 4 — Cross-genre evaluation and release readiness

- [~] Keep CPU-only regression tests for the model-independent core and research harness.
- [~] Maintain small hand-authored decision scenarios across life simulation, shooter, and RPG; these are regression checks, not general-intelligence scores.
- [ ] Add independent held-out language and behavior suites, including multi-turn and cross-genre scenarios.
- [ ] Measure action validity, engine-confirmed success, goal completion, memory consistency, response latency, RAM, and storage.
- [ ] Test at least two materially different game integrations using the same core contract with genre-specific adapters.
- [ ] Document compatibility, failure recovery, security boundaries, licensing, and developer integration steps before release.

## Guiding principles

- The central target is LLM-level language capability inside a reusable game system, not a general-purpose LLM product.
- Language, context, memory, decision-making, and safe action proposals must work together; do not reduce the goal to a rule-based action selector.
- A test passing proves only the behavior covered by that test. It does not prove naturalness, intelligence, generalization, or equivalence to an LLM.
- The game engine remains authoritative for world state, action legality, execution, and outcome confirmation.
- Teacher models are development aids; the final game runtime must not require their weights or a mandatory online model service.
- Keep the system lightweight and cross-genre, but treat any size target (including under 1 GB) as unverified until measured.
- Prefer small, testable increments and preserve the ability to work from a phone-friendly workflow.
