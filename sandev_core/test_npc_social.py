import unittest

from npc_social import NPCSocialError, propose_social_interaction


class NPCSocialTests(unittest.TestCase):
    def setUp(self):
        self.context = {
            "npc_id": "aria",
            "nearby_npc_ids": ["bima", "citra"],
            "state": {"wants_socialize": True},
            "relationships": [
                {"npc_a_id": "aria", "npc_b_id": "bima", "score": 70,
                 "source": "engine_confirmed"},
                {"npc_a_id": "citra", "npc_b_id": "aria", "score": 35,
                 "source": "player_approved"},
            ],
        }

    def test_trusted_friendly_relationship_proposes_social_action(self):
        result = propose_social_interaction(
            self.context, personality="friendly",
            allowed_actions=["greet", "converse", "offer_help", "invite_group"],
        )
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["proposal"]["target_npc_id"], "bima")
        self.assertEqual(result["proposal"]["action_id"], "greet")
        self.assertEqual(result["execution"], "not_performed")
        self.assertEqual(result["authority"], "game_engine_required")

    def test_hostile_relationship_prefers_avoidance_or_deescalation(self):
        context = {
            "npc_id": "aria", "nearby_npc_ids": ["bima"],
            "relationships": [{
                "npc_a_id": "aria", "npc_b_id": "bima", "score": -85,
                "source": "engine_confirmed",
            }],
        }
        result = propose_social_interaction(
            context, allowed_actions=["avoid", "de_escalate"]
        )
        self.assertEqual(result["proposal"]["action_id"], "avoid")

    def test_conflict_and_help_are_game_supplied_signals(self):
        context = {
            "npc_id": "aria", "nearby_npc_ids": ["bima"],
            "state": {"conflict_active": True, "target_needs_help": True},
            "relationships": [{
                "npc_a_id": "aria", "npc_b_id": "bima", "score": 10,
                "source": "engine_confirmed",
            }],
        }
        result = propose_social_interaction(
            context, allowed_actions=["de_escalate", "offer_help"]
        )
        self.assertEqual(result["proposal"]["action_id"], "de_escalate")

    def test_untrusted_or_non_nearby_relationships_do_not_influence(self):
        context = {
            "npc_id": "aria", "nearby_npc_ids": ["bima"],
            "relationships": [
                {"npc_a_id": "aria", "npc_b_id": "bima", "score": 90,
                 "source": "model_guess"},
                {"npc_a_id": "aria", "npc_b_id": "citra", "score": 90,
                 "source": "engine_confirmed"},
            ],
        }
        result = propose_social_interaction(
            context, allowed_actions=["greet", "converse", "avoid"]
        )
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["proposal"])

    def test_actor_pair_order_is_irrelevant(self):
        context = {
            "npc_id": "aria", "nearby_npc_ids": ["bima"],
            "relationships": [{
                "npc_a_id": "bima", "npc_b_id": "aria", "score": 80,
                "source": "engine_confirmed",
            }],
        }
        result = propose_social_interaction(
            context, allowed_actions=["greet"]
        )
        self.assertEqual(result["proposal"]["target_npc_id"], "bima")

    def test_allowlist_is_enforced_and_empty_context_abstains(self):
        result = propose_social_interaction(
            self.context, allowed_actions=["attack", "teleport"]
        )
        self.assertEqual(result["status"], "abstained")
        self.assertEqual(result["execution"], "not_performed")
        empty = propose_social_interaction(
            {"npc_id": "aria", "nearby_npc_ids": ["bima"]},
            allowed_actions=["greet"],
        )
        self.assertEqual(empty["status"], "abstained")

    def test_selection_is_deterministic(self):
        first = propose_social_interaction(
            self.context, allowed_actions=["greet", "converse", "offer_help"]
        )
        second = propose_social_interaction(
            self.context, allowed_actions=["greet", "converse", "offer_help"]
        )
        self.assertEqual(first, second)

    def test_invalid_nearby_and_state_inputs_are_rejected(self):
        with self.assertRaisesRegex(NPCSocialError, "duplicates"):
            propose_social_interaction(
                {"npc_id": "aria", "nearby_npc_ids": ["bima", "bima"]},
                allowed_actions=["greet"],
            )
        with self.assertRaisesRegex(NPCSocialError, "must be a boolean"):
            propose_social_interaction(
                {"npc_id": "aria", "state": {"wants_socialize": "yes"}},
                allowed_actions=["greet"],
            )

    def test_invalid_trusted_relationship_score_is_rejected(self):
        context = {
            "npc_id": "aria", "nearby_npc_ids": ["bima"],
            "relationships": [{
                "npc_a_id": "aria", "npc_b_id": "bima", "score": 101,
                "source": "engine_confirmed",
            }],
        }
        with self.assertRaisesRegex(NPCSocialError, "score"):
            propose_social_interaction(context, allowed_actions=["greet"])

    def test_actor_cannot_be_listed_as_nearby(self):
        with self.assertRaisesRegex(NPCSocialError, "cannot appear"):
            propose_social_interaction(
                {"npc_id": "aria", "nearby_npc_ids": ["aria"]},
                allowed_actions=["greet"],
            )


if __name__ == "__main__":
    unittest.main()
