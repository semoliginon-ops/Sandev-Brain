/**
 * SANDEV Brain Core v0.1
 * Deterministic simulation-focused decision making. No network or model required.
 */
const clamp = (v, min = 0, max = 100) => Math.max(min, Math.min(max, Number.isFinite(v) ? v : min));
const DEFAULT_NEEDS = Object.freeze({ hunger: 25, energy: 80, social: 55, fun: 50, hygiene: 70 });

export function createCharacter(overrides = {}) {
  const now = overrides.now ?? 0;
  const needs = { ...DEFAULT_NEEDS, ...(overrides.needs ?? {}) };
  for (const key of Object.keys(DEFAULT_NEEDS)) needs[key] = clamp(needs[key]);
  return {
    id: overrides.id ?? "character-1",
    name: overrides.name ?? "Karakter",
    traits: { sociable: 0.5, diligent: 0.5, playful: 0.5, ...(overrides.traits ?? {}) },
    needs, mood: clamp(overrides.mood ?? 70),
    location: overrides.location ?? "home",
    inventory: [...(overrides.inventory ?? [])],
    relationships: { ...(overrides.relationships ?? {}) },
    goals: [...(overrides.goals ?? [])], memory: [],
    lastAction: null, createdAt: now, updatedAt: now
  };
}

export function remember(character, event, { now = character.updatedAt, limit = 50 } = {}) {
  if (!event || typeof event.type !== "string") throw new TypeError("Memory event must include a string type.");
  const entry = {
    type: event.type, summary: String(event.summary ?? event.type),
    importance: clamp(event.importance ?? 0.5, 0, 1), at: now,
    details: event.details && typeof event.details === "object" ? { ...event.details } : {}
  };
  character.memory = [...character.memory, entry].sort((a, b) => a.at - b.at).slice(-Math.max(1, limit));
  character.updatedAt = now;
  return entry;
}

export function addGoal(character, goal) {
  if (!goal || typeof goal.id !== "string" || typeof goal.type !== "string") throw new TypeError("Goal must include string id and type.");
  if (!character.goals.some(g => g.id === goal.id)) character.goals.push({
    id: goal.id, type: goal.type, priority: clamp(goal.priority ?? 0.5, 0, 1),
    status: "active", createdAt: goal.createdAt ?? character.updatedAt
  });
  return character.goals.find(g => g.id === goal.id);
}

function makeAction(type, score, reason, payload = {}) { return { id: type, type, score, reason, payload }; }

/** Chooses only from actions supported by the current world snapshot. */
export function planAction(character, world = {}) {
  const available = new Set(world.availableActions ?? ["eat", "sleep", "socialize", "play", "wash", "work", "idle"]);
  const candidates = [];
  const add = (type, score, reason, payload = {}) => { if (available.has(type)) candidates.push(makeAction(type, score, reason, payload)); };
  const n = character.needs;
  add("eat", n.hunger / 100 * 1.2, "Hunger need");
  add("sleep", (100 - n.energy) / 100 * 1.15, "Low energy");
  add("socialize", n.social / 100 * (0.65 + character.traits.sociable * 0.35), "Social need");
  add("play", n.fun / 100 * (0.65 + character.traits.playful * 0.35), "Fun need");
  add("wash", (100 - n.hygiene) / 100 * 0.9, "Hygiene need");
  add("work", 0.25 + character.traits.diligent * 0.25, "Earn resources");
  const goalActions = { earn_money: "work", meet_someone: "socialize", improve_hygiene: "wash", rest: "sleep" };
  for (const goal of character.goals.filter(g => g.status === "active")) {
    const type = goalActions[goal.type];
    if (type && available.has(type)) add(type, 0.4 + goal.priority * 0.6, "Active goal: " + goal.type, { goalId: goal.id });
  }
  add("idle", 0.05, "Fallback safe action");
  if (!candidates.length) return { id: "no-op", type: "no-op", score: 0, reason: "No valid actions available", payload: {} };
  candidates.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  return candidates[0];
}

const NEED_EFFECTS = {
  eat: { hunger: -45, fun: -2 }, sleep: { energy: -65, hunger: 8 },
  socialize: { social: -40, fun: -8 }, play: { fun: -45, energy: 10 },
  wash: { hygiene: -55, energy: 3 }, work: { energy: 18, hunger: 12, fun: 8 },
  idle: { energy: -3, hunger: 2 }
};

/** Apply local effects only after the host game confirms success. */
export function applyActionResult(character, result, { now = character.updatedAt + 1 } = {}) {
  if (!result || typeof result.type !== "string") throw new TypeError("Action result must include a string type.");
  if (result.success !== true) {
    remember(character, { type: "action_failed", summary: "Action failed: " + result.type, importance: 0.7,
      details: { reason: result.reason ?? "unspecified" } }, { now });
    character.lastAction = { type: result.type, success: false, reason: result.reason ?? null };
    return { applied: false, character };
  }
  for (const [need, delta] of Object.entries(NEED_EFFECTS[result.type] ?? {})) {
    character.needs[need] = clamp(character.needs[need] + delta);
  }
  character.lastAction = { type: result.type, success: true, at: now };
  character.updatedAt = now;
  remember(character, { type: "action_succeeded", summary: "Successfully completed: " + result.type,
    importance: 0.4, details: { action: result.type } }, { now });
  if (result.type === "work") character.inventory.push("earned_resource");
  if (result.type === "socialize" && result.targetId) {
    character.relationships[result.targetId] = clamp((character.relationships[result.targetId] ?? 50) + 5);
  }
  if (result.goalId) {
    const goal = character.goals.find(g => g.id === result.goalId);
    if (goal) goal.status = "completed";
  }
  return { applied: true, character };
}

/** Host adapter returns { success: boolean }. Timeout and errors are recorded as failures. */
export async function executePlan(character, plan, adapter, { timeoutMs = 3000, now } = {}) {
  if (!adapter || typeof adapter.execute !== "function") throw new TypeError("An adapter with execute(action) is required.");
  if (!plan || typeof plan.type !== "string" || plan.type === "no-op") return { status: "skipped", reason: plan?.reason ?? "No executable plan" };
  let timer;
  try {
    const timeout = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("ACTION_TIMEOUT")), timeoutMs); });
    const raw = await Promise.race([Promise.resolve().then(() => adapter.execute(plan)), timeout]);
    clearTimeout(timer);
    const result = { ...(raw ?? {}), type: plan.type, success: raw?.success === true, goalId: plan.payload?.goalId };
    applyActionResult(character, result, { now: now ?? character.updatedAt + 1 });
    return { status: result.success ? "succeeded" : "failed", action: plan.type, result };
  } catch (error) {
    clearTimeout(timer);
    const reason = error?.message === "ACTION_TIMEOUT" ? "timeout" : "adapter_error";
    applyActionResult(character, { type: plan.type, success: false, reason }, { now: now ?? character.updatedAt + 1 });
    return { status: "failed", action: plan.type, reason };
  }
}

export function tickNeeds(character, minutes = 10, { now = character.updatedAt + minutes } = {}) {
  if (!Number.isFinite(minutes) || minutes < 0) throw new RangeError("minutes must be non-negative.");
  character.needs.hunger = clamp(character.needs.hunger + minutes * 0.08);
  character.needs.energy = clamp(character.needs.energy - minutes * 0.04);
  character.needs.social = clamp(character.needs.social + minutes * 0.03);
  character.needs.fun = clamp(character.needs.fun + minutes * 0.025);
  character.needs.hygiene = clamp(character.needs.hygiene + minutes * 0.02);
  character.updatedAt = now;
  return character;
}
