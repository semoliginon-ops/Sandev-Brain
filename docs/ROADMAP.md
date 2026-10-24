# SANDEV Brain Roadmap

## Phase 0 — Define the target
- [ ] Write down the target devices and performance limits.
- [ ] Define what a character must be able to do in SANDEV Life.
- [ ] Build a small repeatable benchmark for decisions, action success, memory, and response time.

## Phase 1 — Reliable simulation brain
- [ ] Define a structured character state: needs, mood, traits, relationships, inventory, location, and current activity.
- [ ] Implement persistent short-term and long-term memory.
- [ ] Define goals and priorities based on character state.
- [ ] Build a planner that produces only valid game actions.
- [ ] Add action execution acknowledgements, retries, timeouts, and clear failure states.
- [ ] Test that autonomous mode actually performs actions instead of only describing them.

## Phase 2 — Dialogue and intent
- [ ] Parse common player commands into structured intents.
- [ ] Connect dialogue choices to real game state and available actions.
- [ ] Add response templates and contextual variation.
- [ ] Test ambiguous, invalid, and contradictory commands.

## Phase 3 — Model research
- [ ] Compare candidate open models and their exact licenses.
- [ ] Record model size, tokenizer, RAM use, startup time, latency, and output quality.
- [ ] Test on representative target devices before considering bundling a model.
- [ ] Keep model inference optional until it meets performance and reliability requirements.

## Phase 4 — Evaluation
Track at least:
- Action execution success rate.
- Goal completion rate.
- Memory consistency across sessions.
- Response latency and timeout rate.
- RAM and storage footprint.
- Player-visible failures and recovery behavior.

## Guiding principles
- Simulation actions must be reliable before dialogue is made more elaborate.
- Do not claim equivalence to a general-purpose LLM without benchmarks.
- Avoid requiring players to install a separate model.
- Avoid mandatory cloud AI calls and quota dependence.
- Review third-party licenses before copying code or distributing weights.
