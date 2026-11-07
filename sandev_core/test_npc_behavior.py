import unittest

from npc_behavior import NPCBehaviorError, propose_behavior


def emotion(**overrides):
    values = {"joy": 50, "fear": 0, "anger": 0, "sadness": 0,
              "trust": 50, "suspicion": 0}
    values.update(overrides)
    return {"npc_id": "aria", "player_id": "player-1", "values": values}


def relationship(score=0):
    return {"npc_id": "aria", "player_id": "player-1", "score": score,
            "label": "deliberately_untrusted_label"}


class NPCBehaviorProposalTests(unittest.TestCase):
    def test_threat_proposes_guard_without_executing(self):
        result = propose_behavior(
            {"actor_id": "aria", "state": {"under_threat": True}},
            allowed_actions=["guard_player", "idle"],
        )
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["proposal"]["action_id"], "guard_player")
        self.assertEqual(result["execution"], "not_performed")
        self.assertEqual(result["authority"], "game_engine_required")

    def test_help_signal_proposes_help_only_if_allowlisted(self):
        result = propose_behavior(
            {"state": {"player_needs_help": True}},
            allowed_actions=["offer_help"],
        )
        self.assertEqual(result["proposal"]["action_id"], "offer_help")
        denied = propose_behavior(
            {"state": {"player_needs_help": True}},
            allowed_actions=["idle"],
        )
        self.assertEqual(denied["proposal"]["action_id"], "idle")

    def test_emotion_and_relationship_influence_behavior(self):
        result = propose_behavior(
            {"npc_emotion": emotion(fear=75),
             "npc_relationship": relationship(-70), "state": {}},
            allowed_actions=["flee", "approach_player", "keep_distance"],
        )
        self.assertEqual(result["mood"], "afraid")
        self.assertEqual(result["proposal"]["action_id"], "flee")

    def test_personality_influences_behavior(self):
        result = propose_behavior(
            {"state": {}}, personality="shy",
            allowed_actions=["keep_distance", "approach_player"],
        )
        self.assertEqual(result["proposal"]["action_id"], "keep_distance")

    def test_trusted_scoped_memory_can_influence_behavior(self):
        context = {
            "npc_relationship": relationship(),
            "npc_memories": [
                {"npc_id": "aria", "player_id": "player-1",
                 "source": "engine_confirmed", "tags": ["betrayal"]},
                {"npc_id": "aria", "player_id": "player-1",
                 "source": "model_guess", "tags": ["saved"]},
                {"npc_id": "borin", "player_id": "player-1",
                 "source": "engine_confirmed", "tags": ["saved"]},
            ],
            "state": {},
        }
        result = propose_behavior(
            context, allowed_actions=["keep_distance", "approach_player"],
        )
        self.assertEqual(result["proposal"]["action_id"], "keep_distance")
        self.assertIn("trusted_memory_betrayal",
                      result["proposal"]["reason_tags"])

    def test_unscoped_memory_is_ignored(self):
        result = propose_behavior(
            {"npc_memories": [{"source": "engine_confirmed",
                               "tags": ["betrayal"]}], "state": {}},
            allowed_actions=["keep_distance", "idle"],
        )
        self.assertEqual(result["proposal"]["action_id"], "idle")

    def test_scope_mismatch_is_rejected(self):
        with self.assertRaises(NPCBehaviorError):
            propose_behavior(
                {"npc_relationship": relationship(),
                 "npc_emotion": {"npc_id": "borin", "player_id": "player-1",
                                 "values": emotion()["values"]}},
                allowed_actions=["idle"],
            )

    def test_context_actor_must_match_npc_scope(self):
        with self.assertRaises(NPCBehaviorError):
            propose_behavior(
                {"actor_id": "borin", "npc_relationship": relationship()},
                allowed_actions=["idle"],
            )

    def test_unknown_actions_are_never_proposed(self):
        result = propose_behavior(
            {"state": {"under_threat": True}},
            allowed_actions=["delete_save", "teleport_anywhere"],
        )
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["proposal"])

    def test_empty_allowlist_abstains(self):
        result = propose_behavior({"state": {}}, allowed_actions=[])
        self.assertEqual(result["status"], "abstained")
        self.assertEqual(result["execution"], "not_performed")

    def test_idle_is_safe_fallback_when_allowlisted(self):
        result = propose_behavior({"state": {}}, allowed_actions=["idle"])
        self.assertEqual(result["proposal"]["action_id"], "idle")

    def test_tie_break_is_deterministic(self):
        context = {"state": {"under_threat": True}}
        first = propose_behavior(context, allowed_actions=["keep_distance", "guard_player"])
        second = propose_behavior(context, allowed_actions=["guard_player", "keep_distance"])
        self.assertEqual(first["proposal"], second["proposal"])

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(NPCBehaviorError):
            propose_behavior([], allowed_actions=["idle"])
        with self.assertRaises(NPCBehaviorError):
            propose_behavior({"state": {"under_threat": "yes"}}, allowed_actions=["idle"])
        with self.assertRaises(NPCBehaviorError):
            propose_behavior({"npc_emotion": emotion(fear=True)},
                             allowed_actions=["idle"])
        with self.assertRaises(NPCBehaviorError):
            propose_behavior({"npc_relationship": relationship(101)},
                             allowed_actions=["idle"])
        with self.assertRaises(NPCBehaviorError):
            propose_behavior({"state": {}}, personality="unknown",
                             allowed_actions=["idle"])

    def test_untrusted_or_unscoped_goals_cannot_change_behavior(self):
        base = {"npc_id": "aria", "player_id": "player-1",
                "state": {"under_threat": True, "escape_route_available": True}}
        untrusted = dict(base, goals=[{
            "tag": "survive", "priority": 100, "source": "model_guess",
            "npc_id": "aria", "player_id": "player-1",
        }])
        wrong_scope = dict(base, goals=[{
            "tag": "survive", "priority": 100, "source": "engine_confirmed",
            "npc_id": "borin", "player_id": "player-1",
        }])
        for context in (untrusted, wrong_scope):
            result = propose_behavior(
                context, allowed_actions=["flee", "guard_player"]
            )
            self.assertEqual(result["proposal"]["action_id"], "guard_player")
            self.assertFalse(any(
                reason.startswith("goal_survive")
                for reason in result["proposal"]["reason_tags"]
            ))

    def test_goal_priority_changes_motivation_strength(self):
        base = {"npc_id": "aria", "player_id": "player-1",
                "state": {"under_threat": True, "escape_route_available": True}}
        def with_priority(priority):
            return propose_behavior(
                dict(base, goals=[{
                    "tag": "survive", "priority": priority,
                    "source": "engine_confirmed",
                    "npc_id": "aria", "player_id": "player-1",
                }]),
                allowed_actions=["flee", "guard_player"],
            )
        self.assertEqual(with_priority(100)["proposal"]["action_id"], "flee")
        self.assertEqual(with_priority(10)["proposal"]["action_id"], "guard_player")

    def test_inactive_and_unknown_goals_do_not_motivate(self):
        context = {
            "npc_id": "aria", "player_id": "player-1",
            "state": {"under_threat": True, "escape_route_available": True},
            "goals": [
                {"tag": "survive", "priority": 100, "active": False,
                 "source": "engine_confirmed", "npc_id": "aria", "player_id": "player-1"},
                {"tag": "invented_goal", "priority": 100, "active": True,
                 "source": "engine_confirmed", "npc_id": "aria", "player_id": "player-1"},
            ],
        }
        result = propose_behavior(context, allowed_actions=["flee", "guard_player"])
        self.assertEqual(result["proposal"]["action_id"], "guard_player")

    def test_invalid_trusted_goal_priority_is_rejected(self):
        context = {
            "npc_id": "aria", "player_id": "player-1", "state": {},
            "goals": [{
                "tag": "survive", "priority": 101,
                "source": "engine_confirmed", "npc_id": "aria", "player_id": "player-1",
            }],
        }
        with self.assertRaisesRegex(NPCBehaviorError, "priority"):
            propose_behavior(context, allowed_actions=["flee"])

    def test_goal_and_escape_signals_are_combined(self):
        result = propose_behavior(
            {"npc_id": "aria", "player_id": "player-1",
             "state": {"under_threat": True, "escape_route_available": True},
             "goals": [{"tag": "survive", "priority": 100,
                        "source": "engine_confirmed",
                        "npc_id": "aria", "player_id": "player-1"}]},
            allowed_actions=["flee", "guard_player"],
        )
        self.assertEqual(result["proposal"]["action_id"], "flee")


if __name__ == "__main__":
    unittest.main()
