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


    def test_step_revalidation_accepts_same_version_and_current_target(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Lindungi Falcon lalu serang Bandit", ENTITIES,
            context={"state_version": 17},
        )
        result = validate_plan_step(plan, 2, ENTITIES, current_state_version=17)
        self.assertTrue(result["accepted"])
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(result["proposal"]["target"]["entity_id"], "enemy-2")

    def test_step_revalidation_rejects_stale_version(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=18)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "stale_plan_state_version")

    def test_step_revalidation_rejects_removed_target(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        result = validate_plan_step(
            plan, 1, [entity for entity in ENTITIES if entity["id"] != "enemy-2"],
            current_state_version=17,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "target_missing_or_not_unique_in_current_snapshot")

    def test_step_revalidation_requires_state_version(self):
        from planner import validate_plan_step
        plan = plan_player_command("Serang Bandit", ENTITIES)
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=None)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "state_version_required_for_revalidation")

    def test_step_revalidation_rejects_duplicate_target_id(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        duplicate = ENTITIES + [{"id": "enemy-2", "name": "Bandit"}]
        result = validate_plan_step(plan, 1, duplicate, current_state_version=17)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "target_missing_or_not_unique_in_current_snapshot")


    def test_step_revalidation_rejects_tampered_intent(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        plan["steps"][0]["proposal"]["intent"] = "delete_world"
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=17)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "unsupported_proposal_intent")

    def test_step_revalidation_rejects_target_inconsistent_with_grounding(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        plan["steps"][0]["proposal"]["target"]["entity_id"] = "enemy-1"
        plan["steps"][0]["proposal"]["target"]["entity_name"] = "Goblin"
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=17)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "target_does_not_match_grounding")

    def test_step_revalidation_rejects_targetless_attack(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        plan["steps"][0]["proposal"]["target"] = None
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=17)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "action_target_required")


    def test_step_revalidation_rejects_tampered_supported_intent(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        plan["steps"][0]["proposal"]["intent"] = "tactical_defend"
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=17)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "proposal_intent_does_not_match_command")

    def test_step_revalidation_rejects_tampered_command(self):
        from planner import validate_plan_step
        plan = plan_player_command(
            "Serang Bandit", ENTITIES, context={"state_version": 17},
        )
        plan["steps"][0]["command"] = "Serang Goblin"
        result = validate_plan_step(plan, 1, ENTITIES, current_state_version=17)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "proposal_target_does_not_match_command")


    def test_contextual_pronoun_revalidates_against_fresh_context(self):
        from planner import validate_plan_step
        context = {"state_version": 17, "focus_entity_id": "enemy-2"}
        plan = plan_player_command("Serang dia", ENTITIES, context=context)
        self.assertEqual(plan["status"], "plan_proposal")
        result = validate_plan_step(
            plan, 1, ENTITIES, current_state_version=17, current_context=context,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["proposal"]["target"]["entity_id"], "enemy-2")
        self.assertFalse(result["execution_allowed"])

    def test_contextual_pronoun_rejects_changed_focus(self):
        from planner import validate_plan_step
        original = {"state_version": 17, "focus_entity_id": "enemy-2"}
        current = {"state_version": 17, "focus_entity_id": "enemy-1"}
        plan = plan_player_command("Serang dia", ENTITIES, context=original)
        result = validate_plan_step(
            plan, 1, ENTITIES, current_state_version=17, current_context=current,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "proposal_target_does_not_match_command")

    def test_contextual_pronoun_rejects_stale_context_version(self):
        from planner import validate_plan_step
        context = {"state_version": 17, "focus_entity_id": "enemy-2"}
        plan = plan_player_command("Serang dia", ENTITIES, context=context)
        stale = {"state_version": 16, "focus_entity_id": "enemy-2"}
        result = validate_plan_step(
            plan, 1, ENTITIES, current_state_version=17, current_context=stale,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "stale_context_state_version")


if __name__ == "__main__":
    unittest.main()
