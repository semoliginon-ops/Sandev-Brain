import { createCharacter, addGoal, planAction, executePlan, tickNeeds } from "../src/index.js";

const character = createCharacter({
  id: "joni", name: "Joni",
  needs: { hunger: 88, energy: 62, social: 45, fun: 50, hygiene: 70 },
  traits: { sociable: 0.7, diligent: 0.6, playful: 0.8 }
});
addGoal(character, { id: "goal-earn", type: "earn_money", priority: 0.55 });
console.log("Sebelum:", character.name, structuredClone(character.needs));
tickNeeds(character, 10);
const plan = planAction(character, { availableActions: ["eat", "sleep", "socialize", "play", "wash", "work", "idle"] });
console.log("Rencana otak:", plan);
const outcome = await executePlan(character, plan, {
  async execute(action) {
    console.log("Game menerima aksi:", action.type);
    return { success: true };
  }
});
console.log("Hasil eksekusi:", outcome);
console.log("Sesudah:", structuredClone(character.needs));
console.log("Ingatan terbaru:", character.memory.at(-1));
