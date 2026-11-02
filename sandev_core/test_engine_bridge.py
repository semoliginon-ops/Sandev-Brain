import copy
import unittest

from adapter import AdapterInputError, decide_from_snapshot
from engine_bridge import validate_intent


class EngineBridgeTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "game_id": "plane-shooter-demo",
            "state_version": 17,
            "state": {"threat": {"incoming": True}, "weapon": {"ammo": 12}},
            "needs": {"safety": 90},
            "goals": [],
            "candidates": [
                {"action_id": "cover-now", "kind": "take_cover", "target": "companion",
                 "preconditions": {"threat.incoming": True}},
                {"action_id": "reload", "kind": "reload", "target": "companion",
                 "preconditions": {"weapon.ammo": {"max": 0}}},
            ],
            "allowed_actions": ["take_cover", "reload"],
        }

    def test_valid_intent_is_revalidated_but_not_executed(self):
        intent = decide_from_snapshot(self.snapshot)
        result = validate_intent(self.snapshot, intent)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["action"]["type"], "take_cover")
        self.assertIn("engine_must_execute_and_confirm", result["status"])

    def test_stale_snapshot_version_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        latest = copy.deepcopy(self.snapshot)
        latest["state_version"] = 18
        result = validate_intent(latest, intent)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "stale state version")

    def test_changed_precondition_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        latest = copy.deepcopy(self.snapshot)
        latest["state_version"] = 17
        latest["state"]["threat"]["incoming"] = False
        result = validate_intent(latest, intent)
        self.assertFalse(result["accepted"])
        self.assertIn("precondition failed", result["reason"])

    def test_removed_candidate_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        latest = copy.deepcopy(self.snapshot)
        latest["candidates"] = [latest["candidates"][1]]
        result = validate_intent(latest, intent)
        self.assertFalse(result["accepted"])
        self.assertIn("not uniquely present", result["reason"])

    def test_disallowed_or_tampered_action_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        tampered = copy.deepcopy(intent)
        tampered["action"]["type"] = "delete_world"
        result = validate_intent(self.snapshot, tampered)
        self.assertFalse(result["accepted"])

    def test_unsupported_contract_version_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        intent["contract_version"] = "999.0"
        result = validate_intent(self.snapshot, intent)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "unsupported contract version")

    def test_duplicate_current_candidate_ids_are_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        latest = copy.deepcopy(self.snapshot)
        duplicate = copy.deepcopy(latest["candidates"][0])
        latest["candidates"].append(duplicate)
        result = validate_intent(latest, intent)
        self.assertFalse(result["accepted"])
        self.assertIn("not uniquely present", result["reason"])

    def test_target_tampering_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        intent["action"]["target"] = "enemy-base"
        result = validate_intent(self.snapshot, intent)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "intent does not match current candidate")

    def test_non_string_intent_target_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        intent["action"]["target"] = ["companion"]
        result = validate_intent(self.snapshot, intent)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "intent target must be a string")

    def test_non_string_candidate_target_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        latest = copy.deepcopy(self.snapshot)
        latest["candidates"][0]["target"] = ["companion"]
        result = validate_intent(latest, intent)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "candidate target must be a string")

    def test_malformed_allow_list_is_rejected(self):
        intent = decide_from_snapshot(self.snapshot)
        latest = copy.deepcopy(self.snapshot)
        latest["allowed_actions"] = ["take_cover", None]
        with self.assertRaisesRegex(AdapterInputError, "allowed_actions must contain non-empty strings"):
            validate_intent(latest, intent)

    def test_engine_bridge_never_claims_execution(self):
        intent = decide_from_snapshot(self.snapshot)
        result = validate_intent(self.snapshot, intent)
        self.assertTrue(result["accepted"])
        self.assertIn("proposal", result["status"])
        self.assertNotIn("executed", result)
        self.assertNotIn("success", result)

    def test_empty_intent_is_rejected(self):
        intent = decide_from_snapshot({
            "state": {}, "needs": {}, "goals": [], "candidates": [], "allowed_actions": []
        })
        result = validate_intent({}, intent)
        self.assertFalse(result["accepted"])


class LanguageProposalResolutionTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "game_id": "rpg-demo",
            "state_version": "world-4",
            "state": {"hero": {"mp": 10}, "enemy": {"alive": True}},
            "allowed_actions": ["attack", "defend", "heal"],
            "candidates": [
                {"action_id": "attack-goblin", "kind": "attack", "target": "enemy-1",
                 "preconditions": {"enemy.alive": True}},
                {"action_id": "attack-bandit", "kind": "attack", "target": "enemy-2",
                 "preconditions": {"enemy.alive": True}},
                {"action_id": "heal-self", "kind": "heal", "target": "",
                 "preconditions": {"hero.mp": {"min": 5}}},
            ],
        }
        self.proposal = {
            "status": "proposal", "intent": "tactical_attack",
            "target": {"entity_id": "enemy-1", "entity_name": "Goblin"},
            "execution_allowed": False,
        }
        self.mapping = {"tactical_attack": "attack", "heal_request": "heal"}

    def test_maps_grounded_target_to_unique_current_candidate(self):
        from engine_bridge import resolve_language_proposal
        result = resolve_language_proposal(self.snapshot, self.proposal, action_type_map=self.mapping)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["action_id"], "attack-goblin")
        self.assertEqual(result["action"], {"type": "attack", "target": "enemy-1"})
        self.assertEqual(result["state_version"], "world-4")

    def test_rejects_missing_or_ambiguous_candidate(self):
        from engine_bridge import resolve_language_proposal
        self.snapshot["candidates"].append({
            **self.snapshot["candidates"][0], "action_id": "duplicate-attack"
        })
        result = resolve_language_proposal(self.snapshot, self.proposal, action_type_map=self.mapping)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["candidate_match_count"], 2)

    def test_rejects_action_outside_current_allow_list_and_failed_precondition(self):
        from engine_bridge import resolve_language_proposal
        self.snapshot["allowed_actions"] = ["defend"]
        result = resolve_language_proposal(self.snapshot, self.proposal, action_type_map=self.mapping)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "action not in current allow-list")
        self.snapshot["allowed_actions"] = ["attack"]
        self.snapshot["state"]["enemy"]["alive"] = False
        result = resolve_language_proposal(self.snapshot, self.proposal, action_type_map=self.mapping)
        self.assertFalse(result["accepted"])

    def test_rejects_unmapped_intent_and_unsafe_proposal(self):
        from engine_bridge import resolve_language_proposal
        result = resolve_language_proposal(
            self.snapshot, self.proposal, action_type_map={"heal_request": "heal"}
        )
        self.assertFalse(result["accepted"])
        result = resolve_language_proposal(
            self.snapshot, {**self.proposal, "execution_allowed": True},
            action_type_map=self.mapping,
        )
        self.assertFalse(result["accepted"])

    def test_untargeted_proposal_requires_empty_target_candidate(self):
        from engine_bridge import resolve_language_proposal
        proposal = {
            "status": "proposal", "intent": "heal_request",
            "target": None, "execution_allowed": False,
        }
        result = resolve_language_proposal(self.snapshot, proposal, action_type_map=self.mapping)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["action_id"], "heal-self")


if __name__ == "__main__":
    unittest.main()
