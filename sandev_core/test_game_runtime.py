import unittest

from game_runtime import GameRuntimeError, GameRuntimeSimulator


class GameRuntimeSimulatorTests(unittest.TestCase):
    def setUp(self):
        self.runtime = GameRuntimeSimulator()

    def test_attack_flows_from_indonesian_command_to_confirmed_world_change(self):
        result = self.runtime.submit("Serang Goblin")
        self.assertEqual(result["status"], "executed")
        self.assertTrue(result["validation"]["accepted"])
        self.assertTrue(result["engine"]["confirmed"])
        self.assertEqual(result["engine"]["result"]["damage"], 10)
        self.assertEqual(result["world"]["state"]["enemies"]["goblin"]["hp"], 10)
        self.assertEqual(result["world"]["state_version"], 2)
        self.assertIn("Goblin", result["response"])

    def test_heal_uses_potion_and_updates_authoritative_state(self):
        self.runtime.state["player"]["hp"] = 25
        result = self.runtime.submit("Pulihkan HP")
        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["engine"]["result"]["healed"], 20)
        self.assertEqual(result["world"]["state"]["player"]["hp"], 45)
        self.assertEqual(result["world"]["state"]["player"]["potions"], 0)
        self.assertEqual(result["world"]["state_version"], 2)

    def test_removed_enemy_cannot_be_targeted(self):
        self.runtime.state["enemies"]["goblin"]["hp"] = 0
        self.runtime.state["enemies"]["goblin"]["alive"] = False
        result = self.runtime.submit("Serang Goblin")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["world"]["state"]["enemies"]["goblin"]["hp"], 0)
        self.assertEqual(result["world"]["state_version"], 1)

    def test_unknown_message_does_not_change_world(self):
        before = self.runtime.snapshot()
        result = self.runtime.submit("Buka gerbang rahasia dengan sihir")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["world"], before)

    def test_stale_engine_version_is_not_confirmed(self):
        current = self.runtime.snapshot()
        proposal = {
            "status": "proposal",
            "intent": "tactical_attack",
            "target": {"entity_id": "goblin", "entity_name": "Goblin"},
            "execution_allowed": False,
        }
        result = self.runtime._execute_confirmed(proposal, current["state_version"] + 1)
        self.assertFalse(result["confirmed"])
        self.assertEqual(result["result"]["reason"], "stale_state_version")
        self.assertEqual(self.runtime.state["enemies"]["goblin"]["hp"], 20)

    def test_empty_message_is_rejected(self):
        with self.assertRaises(GameRuntimeError):
            self.runtime.submit("   ")


if __name__ == "__main__":
    unittest.main()
