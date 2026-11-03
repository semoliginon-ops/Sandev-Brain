import unittest

from adapter import AdapterInputError, decide_from_snapshot


class GenericAdapterTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "game_id": "plane-shooter-demo",
            "state": {
                "player": {"hp": 40},
                "companion": {"hp": 85},
                "threat": {"incoming": True},
                "weapon": {"ammo": 12, "capacity": 30},
            },
            "needs": {"safety": 90, "team_support": 60},
            "goals": [{"tag": "protect_player", "priority": 0.9}],
            "candidates": [
                {
                    "action_id": "companion-cover",
                    "kind": "take_cover",
                    "target": "companion",
                    "tags": ["safety"],
                    "goal_tags": ["protect_player"],
                    "preconditions": {"threat.incoming": True},
                    "base_score": 1,
                },
                {
                    "action_id": "companion-reload",
                    "kind": "reload",
                    "target": "companion",
                    "tags": ["safety"],
                    "preconditions": {"weapon.ammo": {"max": 0}},
                },
            ],
            "allowed_actions": ["take_cover", "reload", "attack"],
        }

    def test_shooter_snapshot_returns_safe_intent(self):
        result = decide_from_snapshot(self.snapshot)
        self.assertEqual(result["game_id"], "plane-shooter-demo")
        self.assertEqual(result["contract_version"], "1.0")
        self.assertEqual(result["action"], {"type": "take_cover", "target": "companion"})
        self.assertEqual(result["status"], "intent_only_engine_must_validate")
        self.assertEqual(result["rejected"][0]["action_id"], "companion-reload")

    def test_rpg_and_life_sim_can_use_same_contract(self):
        for game_id, action_kind, state in [
            ("rpg-demo", "use_potion", {"hero": {"hp": 10, "potion_count": 1}}),
            ("life-sim-demo", "eat", {"inventory": {"food": 1}}),
        ]:
            snapshot = {
                "game_id": game_id,
                "state": state,
                "needs": {"health" if game_id == "rpg-demo" else "hunger": 95},
                "goals": [],
                "candidates": [{
                    "action_id": "primary-action",
                    "kind": action_kind,
                    "preconditions": (
                        {"hero.potion_count": {"min": 1}}
                        if game_id == "rpg-demo" else {"inventory.food": {"min": 1}}
                    ),
                }],
                "allowed_actions": [action_kind],
            }
            result = decide_from_snapshot(snapshot)
            self.assertEqual(result["action"]["type"], action_kind)
            self.assertEqual(result["game_id"], game_id)

    def test_duplicate_action_ids_are_rejected(self):
        self.snapshot["candidates"].append(dict(self.snapshot["candidates"][0]))
        with self.assertRaisesRegex(AdapterInputError, "duplicate action_id"):
            decide_from_snapshot(self.snapshot)

    def test_invalid_action_shape_is_rejected(self):
        self.snapshot["candidates"][0]["base_score"] = float("nan")
        with self.assertRaisesRegex(AdapterInputError, "finite number"):
            decide_from_snapshot(self.snapshot)

    def test_no_feasible_action_remains_empty_intent(self):
        self.snapshot["candidates"] = [self.snapshot["candidates"][1]]
        result = decide_from_snapshot(self.snapshot)
        self.assertIsNone(result["action"])
        self.assertEqual(result["status"], "intent_only_engine_must_validate")


    def test_optional_npc_behavior_uses_same_adapter_contract(self):
        self.snapshot["npc_behavior"] = {
            "npc_id": "aria",
            "player_id": "player-1",
            "personality": "friendly",
            "state": {"under_threat": True},
            "allowed_actions": ["guard_player", "idle"],
        }
        result = decide_from_snapshot(self.snapshot)
        self.assertEqual(result["action"]["type"], "take_cover")
        self.assertEqual(
            result["npc_behavior"]["proposal"]["action_id"], "guard_player"
        )
        self.assertEqual(
            result["npc_behavior"]["execution"], "not_performed"
        )
        self.assertEqual(
            result["npc_behavior"]["authority"], "game_engine_required"
        )

    def test_npc_behavior_is_optional_and_preserves_legacy_output(self):
        result = decide_from_snapshot(self.snapshot)
        self.assertNotIn("npc_behavior", result)
        self.assertEqual(result["action"]["type"], "take_cover")

    def test_npc_behavior_rejects_missing_scope(self):
        self.snapshot["npc_behavior"] = {
            "npc_id": "aria",
            "allowed_actions": ["idle"],
        }
        with self.assertRaisesRegex(AdapterInputError, "player_id"):
            decide_from_snapshot(self.snapshot)

    def test_npc_behavior_rejects_invalid_personality(self):
        self.snapshot["npc_behavior"] = {
            "npc_id": "aria",
            "player_id": "player-1",
            "personality": "invented",
            "state": {},
            "allowed_actions": ["idle"],
        }
        with self.assertRaisesRegex(AdapterInputError, "unsupported NPC personality"):
            decide_from_snapshot(self.snapshot)

    def test_npc_behavior_memory_requires_matching_scope(self):
        self.snapshot["npc_behavior"] = {
            "npc_id": "aria",
            "player_id": "player-1",
            "state": {},
            "allowed_actions": ["keep_distance", "idle"],
            "goals": [{
                "tag": "avoid_player", "priority": 100,
                "source": "engine_confirmed",
                "npc_id": "aria", "player_id": "player-1",
            }],
            "memories": [{
                "npc_id": "aria",
                "player_id": "player-1",
                "source": "engine_confirmed",
                "tags": ["betrayal"],
            }],
        }
        result = decide_from_snapshot(self.snapshot)
        self.assertEqual(
            result["npc_behavior"]["proposal"]["action_id"], "keep_distance"
        )
        self.assertIn(
            "trusted_memory_betrayal",
            result["npc_behavior"]["proposal"]["reason_tags"],
        )
        self.assertIn(
            "goal_avoid_player_priority_100",
            result["npc_behavior"]["proposal"]["reason_tags"],
        )


if __name__ == "__main__":
    unittest.main()
