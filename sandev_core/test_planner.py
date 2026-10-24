import unittest

from planner import PlannerInputError, plan_player_command


ENTITIES = [
    {"id": "enemy-1", "name": "Goblin", "aliases": ["goblin"], "is_hostile": True},
    {"id": "enemy-2", "name": "Bandit", "aliases": ["bandit"], "is_hostile": True},
    {"id": "ally-1", "name": "Falcon", "aliases": ["pesawat falcon"]},
]


class MultiStepPlannerTests(unittest.TestCase):
    def test_two_step_sequence_is_grounded_and_never_executable(self):
        result = plan_player_command(
            "Lindungi Falcon, lalu serang Bandit", ENTITIES,
            context={"game_id": "shooter", "state_version": 17},
        )
        self.assertEqual(result["status"], "plan_proposal")
        self.assertEqual(result["step_count"], 2)
        self.assertEqual(result["steps"][0]["proposal"]["intent"], "tactical_defend")
        self.assertEqual(result["steps"][0]["proposal"]["target"]["entity_id"], "ally-1")
        self.assertEqual(result["steps"][1]["proposal"]["target"]["entity_id"], "enemy-2")
        self.assertEqual(result["state_version"], 17)
        self.assertFalse(result["execution_allowed"])
        self.assertTrue(all(not s["proposal"]["execution_allowed"] for s in result["steps"]))

    def test_unknown_target_aborts_entire_plan_without_partial_steps(self):
        result = plan_player_command("Lindungi Falcon lalu serang Naga", ENTITIES)
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["failed_step"], 2)
        self.assertEqual(result["steps"], [])
        self.assertFalse(result["execution_allowed"])

    def test_ambiguous_target_aborts_entire_plan(self):
        entities = ENTITIES + [{"id": "enemy-3", "name": "Bandit", "is_hostile": True}]
        result = plan_player_command("Lindungi Falcon lalu serang Bandit", entities)
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["failed_step"], 2)
        self.assertEqual(result["steps"], [])

    def test_unsupported_connector_is_not_guessed(self):
        result = plan_player_command("Lindungi Falcon sekaligus serang Bandit", ENTITIES)
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["reason"], "unsupported_sequence_connector")
        self.assertEqual(result["steps"], [])

    def test_malformed_sequence_is_rejected(self):
        result = plan_player_command("Lindungi Falcon lalu", ENTITIES)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["steps"], [])

    def test_max_steps_is_enforced(self):
        result = plan_player_command(
            "Serang Goblin lalu serang Bandit lalu serang Goblin", ENTITIES, max_steps=2,
        )
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["steps"], [])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(PlannerInputError):
            plan_player_command(None, ENTITIES)
        with self.assertRaises(PlannerInputError):
            plan_player_command("Serang Goblin", "not-list")
        with self.assertRaises(PlannerInputError):
            plan_player_command("Serang Goblin", ENTITIES, max_steps=0)

    def test_single_step_is_also_proposal_only(self):
        result = plan_player_command("Serang Goblin", ENTITIES)
        self.assertEqual(result["status"], "plan_proposal")
        self.assertEqual(result["step_count"], 1)
        self.assertFalse(result["execution_allowed"])


if __name__ == "__main__":
    unittest.main()
