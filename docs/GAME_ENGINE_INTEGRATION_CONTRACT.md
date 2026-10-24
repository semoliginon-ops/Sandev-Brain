# SANDEV Brain — game engine integration contract

This document defines the boundary between the reusable SANDEV Brain core and a game host. It is a contract for integration, not a claim that any particular game is already connected.

## 1. Responsibilities

**SANDEV Brain may:**
- rank actions that the host has already declared legal;
- consider structured needs, goals, state, and action preconditions;
- return a versioned intent and a short explanation;
- interpret a player message through the separate command/language path and produce a proposal.

**The host game must:**
- provide an authoritative, current snapshot and stable entity/action IDs;
- decide which actions are legal and provide their costs, preconditions, and constraints;
- revalidate the selected action against live state;
- atomically compare the expected state version, validate rules, execute, and report the actual result;
- keep the world unchanged if validation fails;
- only store confirmed engine events as facts about what happened.

An intent or pending proposal is not permission to execute. Never treat generated prose, a model suggestion, or a `pending` status as engine confirmation.

## 2. Generic decision snapshot

The current `decide_from_snapshot()` adapter expects these fields:

- `state`: JSON-like object describing the relevant world state.
- `needs`: object whose numeric values describe urgency/level according to the game's documented convention.
- `goals`: list of `{ "tag": string, "priority": number }`.
- `candidates`: list of legal candidate objects.
- `allowed_actions`: allow-list of candidate `kind` values.
- Optional `game_id` and `state_version`.

Each candidate includes a unique `action_id`, a `kind`, optional `target`, `tags`, `goal_tags`, `preconditions`, `base_score`, and `cost`. The host must define the meaning and units of costs and needs consistently. Unknown game-specific keys can remain in `state`, but the core will not infer their meaning automatically.

Example (illustrative only):

```json
{
  "game_id": "my-rpg",
  "state_version": 42,
  "state": {
    "player": {"hp": 35, "max_hp": 100, "gold": 20},
    "entities": [{"id": "goblin-7", "kind": "enemy", "hp": 18}]
  },
  "needs": {"survival": 0.9, "progress": 0.5},
  "goals": [{"tag": "survive", "priority": 1.0}],
  "candidates": [
    {
      "action_id": "heal-self-1",
      "kind": "use_potion",
      "target": "player",
      "tags": ["healing", "survival"],
      "goal_tags": ["survive"],
      "preconditions": {"player.potions": {"min": 1}},
      "base_score": 0.7,
      "cost": 1
    },
    {
      "action_id": "attack-goblin-7",
      "kind": "attack",
      "target": "goblin-7",
      "tags": ["combat"],
      "goal_tags": ["progress"],
      "preconditions": {"entities.goblin-7.hp": {"min": 1}},
      "base_score": 0.6,
      "cost": 0
    }
  ],
  "allowed_actions": ["use_potion", "attack"]
}
```

The sample precondition paths are illustrative: the host must use a state shape and path convention actually supported by its integration. Never include an action as a candidate if it is already illegal.

## 3. Genre mapping

The core contract stays generic; the host supplies genre-specific candidates and state.

| Genre | Example state and needs | Example candidates |
| --- | --- | --- |
| RPG / card RPG | HP, status effects, mana, inventory, enemy intent, squad health; survival/progress | attack, defend, heal, use item, fuse card, retreat |
| Shooter | ammo, cover, line of sight, incoming threats, squad positions; safety/objective | take cover, reload, flank, suppress, retreat |
| Life simulation | hunger, energy, hygiene, relationships, schedule, home state; comfort/social/progress | eat, sleep, work, talk, clean, travel |
| Strategy | resources, units, terrain, threat, objective timers; economy/control/survival | gather, build, move, defend, negotiate, research |

These labels are examples, not built-in action implementations. The host must define exact legality, target identity, costs, effects, and preconditions for its own game.

## 4. Player language is a separate input path

Natural-language commands must be interpreted and grounded before they can become action proposals. Preserve the original message for dialogue/context, but do not treat raw text as verified world state. Pronouns and entity references must resolve against the current context; ambiguous targets should ask for clarification. Negations, questions, past mentions, and future intentions must not silently become immediate orders.

When a new player message supersedes an older pending proposal, cancel the old proposal for that session. Cancellation is not retroactive: once execution has crossed the host's atomic execution boundary, a later message cannot promise to undo it. Report outcomes only after explicit engine confirmation.

## 5. Execution handoff

The host callback used by `PendingCommandSession.execute_pending()` must implement one atomic operation equivalent to:

1. Compare live state version to the expected version.
2. Re-resolve the action ID and target against the live world.
3. Re-check permissions, legality, resource costs, cooldowns, and preconditions.
4. Execute exactly the validated action once.
5. Return `{"confirmed": true, "result": {...}}` only when the engine can authoritatively confirm the outcome. Return `confirmed: false` on rejection/failure.

If the host cannot guarantee atomic validation and execution, it must not use the callback as though the race were solved by the Python session lock. That lock only coordinates calls through the same session-manager instance; it does not guard other processes or external game-state mutations.

The pending registry is currently in-memory. A process restart loses pending proposals. Persistent storage, idempotency across retries, and distributed locking are future integration work.

## 6. Integration acceptance checklist

- [ ] Stable unique IDs for sessions, entities, candidates, and actions.
- [ ] Snapshot includes a monotonic or otherwise reliable state version.
- [ ] Candidate list contains only actions legal at snapshot time.
- [ ] Needs, goals, score ranges, and cost units are documented for the game.
- [ ] Unknown or ambiguous target resolves to clarification/no action.
- [ ] Host atomically validates current state and executes at most once.
- [ ] A stale version or failed precondition produces no world mutation.
- [ ] Only explicit host confirmation produces a completed action/result.
- [ ] Confirmed outcome tests cover success, rejection, timeout, and duplicate retries.
- [ ] No model weights, network inference, or paid service is required at gameplay runtime.

Passing this checklist for one game does not establish compatibility for every genre. Each host needs its own adapter fixtures and integration tests.
