# SANDEV Brain — progress measurement baseline

This file defines a stable, evidence-based way to estimate progress toward the product in [ROADMAP.md](ROADMAP.md). The percentage is a planning estimate of implemented, verified product milestones. It is **not** a measure of intelligence, dialogue quality, or LLM equivalence.

## Scoring rules

- `[x]` verified implementation with focused tests or equivalent evidence = **1.00**.
- `[~]` partial foundation exists, but the acceptance criterion is not complete = **0.25**.
- `[ ]` not implemented or not demonstrated = **0.00**.
- Documentation alone, commit count, file count, and CI success without the relevant capability do not earn completion points.
- A passing test proves only the behavior it covers. Open-ended language quality, real game integration, offline operation, and device performance need their own evidence.

For each category:

`category completion = sum(criterion points) / number of criteria`

`weighted contribution = category completion × category weight`

The overall estimate is the sum of weighted contributions. Keep the categories, weights, and criteria stable between reports. Change them only when the product scope or acceptance criteria materially change, and explain the effect on comparability.

## Baseline weights and criteria

| Category | Weight | Acceptance criteria represented | Status points | Category completion | Contribution |
| --- | ---: | --- | ---: | ---: | ---: |
| Core decision and safe action handoff | 15% | Deterministic need/goal scoring [x]; versioned proposal and latest-state revalidation [~]; multi-step proposal coordination [~]; integration into a real game with confirmed state changes [ ] | 1 + 0.25 + 0.25 + 0 | 37.5% | 5.63% |
| Context and memory | 15% | Provenance-restricted persistent ledger [x]; bounded context assembly and retrieval [~]; complete contradiction, expiry, privacy, and forgetting policies [ ] | 1 + 0.25 + 0 | 41.7% | 6.25% |
| Cross-genre adapters | 15% | Versioned generic snapshot contract [x]; hand-authored regression scenarios across multiple genres [~]; two materially different real game integrations using the same core [ ] | 1 + 0.25 + 0 | 41.7% | 6.25% |
| Natural language and dialogue | 30% | Limited Indonesian intent parsing [~]; entity grounding [~]; curated contextual response selection [~]; bounded compositional dialogue [~]; varied open-ended contextual NPC dialogue [ ]; robust multi-turn and indirect language across genres [ ]; fresh independently held-out Indonesian evaluation with human review [ ] | 0.25 × 4 + 0 × 3 | 14.3% | 4.29% |
| Runtime independence | 10% | Model-independent core with teacher/research harness kept separate [~]; verified packaged gameplay offline without GGUF, weights, loader, or cloud inference [ ] | 0.25 + 0 | 12.5% | 1.25% |
| Reliability and evaluation | 10% | CPU-only core/research regression suite [~]; small cross-genre decision scenarios [~]; independent held-out language and behavior suites [ ] | 0.25 + 0.25 + 0 | 16.7% | 1.67% |
| Lightweight packaging and device proof | 5% | Measurable target-device budgets [ ]; measured package/storage/RAM/startup/latency [ ]; verified lightweight release packaging [ ] | 0 + 0 + 0 | 0.0% | 0.00% |

**Baseline overall estimate: 25.3% (approximately 25%).**

## Evidence and limitations at baseline

- **Core decision/action:** `sandev_core/brain.py`, `adapter.py`, `engine_bridge.py`, `planner.py`, `pending_command_session.py`, and `sequential_executor.py`, with corresponding tests. These produce and validate proposals; no real host game integration has been demonstrated.
- **Context/memory:** `context.py`, `memory.py`, `npc_memory.py`, `facts.py`, and their tests provide bounded context, provenance checks, scoped memories, and some decay/forgetting behavior. Comprehensive contradiction, privacy, retention, and forgetting policies remain incomplete.
- **Cross-genre:** the generic adapter and regression examples cover life simulation, shooter, and RPG shapes. Examples are not actual integrations into two shipped or running games.
- **Language/dialogue:** `intent.py`, `language.py`, `followup.py`, `conversation.py`, `response_composer.py`, and `compositional_dialogue.py` provide limited intent rules, grounding, curated replies, and bounded composition. They do not demonstrate open-ended LLM-level dialogue. Existing small evaluation sets do not replace fresh, independent human-reviewed evaluation.
- **Runtime independence:** the deterministic core is separated from `smollm/` research code, and CI exercises the core without downloading model weights. A packaged offline game build has not yet been verified.
- **Reliability/evaluation:** CPU-only tests and GitHub Actions are present, but the roadmap still marks broad held-out language/behavior evaluation as incomplete.
- **Packaging:** no defensible package-size, RAM, startup, or latency measurements on target devices have been established. The under-1-GB goal remains an aspiration, not a verified result.

## Updating this baseline

At each 22.00 WIB report, inspect the current roadmap, source, tests, and latest completed CI. Change a criterion's score only when new implementation and evidence justify it. Keep this denominator and weighting unchanged where possible. A narrow bug fix can improve reliability without changing a broad milestone's completion score; report the daily change separately from overall product progress.
