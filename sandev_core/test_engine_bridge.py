import copy
import unittest

from adapter import decide_from_snapshot
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


if __name__ == "__main__":
    unittest.main()
