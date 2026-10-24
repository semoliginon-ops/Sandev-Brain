import test from "node:test";
import assert from "node:assert/strict";
import { createCharacter, remember, addGoal, planAction, applyActionResult, executePlan, tickNeeds } from "../src/index.js";

test("defaults and need clamping", () => {
  const c = createCharacter({ needs: { hunger: 150, energy: -2 } });
  assert.equal(c.needs.hunger, 100); assert.equal(c.needs.energy, 0); assert.equal(c.needs.social, 55);
});
test("memory is appended and bounded", () => {
  const c = createCharacter();
  remember(c, { type: "met", summary: "Met Alex" }, { now: 1, limit: 2 });
  remember(c, { type: "ate" }, { now: 2, limit: 2 });
  remember(c, { type: "worked" }, { now: 3, limit: 2 });
  assert.equal(c.memory.length, 2); assert.equal(c.memory[0].type, "ate");
});
test("planner prioritizes critical hunger", () => {
  const c = createCharacter({ needs: { hunger: 95, energy: 100, social: 0, fun: 0, hygiene: 100 } });
  assert.equal(planAction(c).type, "eat");
});
test("planner selects only available actions", () => {
  const c = createCharacter({ needs: { hunger: 100, energy: 0 } });
  assert.ok(["idle", "work"].includes(planAction(c, { availableActions: ["idle", "work"] }).type));
});
test("goal completes after successful action", () => {
  const c = createCharacter(); addGoal(c, { id: "g1", type: "earn_money", priority: 1 });
  const p = planAction(c); assert.equal(p.type, "work");
  applyActionResult(c, { type: "work", success: true, goalId: "g1" }, { now: 1 });
  assert.equal(c.goals[0].status, "completed"); assert.ok(c.inventory.includes("earned_resource"));
});
test("failed action does not apply effects", () => {
  const c = createCharacter({ needs: { hunger: 70 } });
  applyActionResult(c, { type: "eat", success: false, reason: "no_food" }, { now: 1 });
  assert.equal(c.needs.hunger, 70); assert.equal(c.lastAction.success, false);
  assert.equal(c.memory.at(-1).type, "action_failed");
});
test("adapter errors are captured", async () => {
  const c = createCharacter();
  const result = await executePlan(c, { type: "work", payload: {} }, { execute: async () => { throw new Error("test"); } });
  assert.equal(result.status, "failed"); assert.equal(c.lastAction.success, false);
});
test("needs stay within bounds after time advances", () => {
  const c = createCharacter({ needs: { hunger: 99, energy: 1 } }); tickNeeds(c, 100);
  assert.equal(c.needs.hunger, 100); assert.equal(c.needs.energy, 0);
});
