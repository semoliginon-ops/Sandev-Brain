import unittest
from brain import ActionCandidate, choose_action, decision_to_dict, evaluate_needs


class CoreDecisionTests(unittest.TestCase):
    def test_need_urgency_is_clamped_and_normalized(self):
        self.assertEqual(evaluate_needs({"hunger": 75, "energy": -4, "fun": 150, "bad": "high"}),
                         {"hunger": 0.75, "energy": 0.0, "fun": 1.0})

    def test_life_sim_chooses_food_when_hunger_is_critical(self):
        decision = choose_action(
            state={"inventory": {"food": 2}, "cash": 10},
            needs={"hunger": 95, "energy": 20},
            goals=[{"tag": "save_money", "priority": 0.8}],
            candidates=[
                ActionCandidate("eat-now", "eat", tags=("hunger",),
                                preconditions={"inventory.food": {"min": 1}}),
                ActionCandidate("work", "work", goal_tags=("save_money",)),
            ],
            allowed_actions=["eat", "work", "rest"],
        )
        self.assertEqual(decision.kind, "eat")
        self.assertEqual(decision.action_id, "eat-now")

    def test_shooter_adapter_rejects_impossible_reload(self):
        decision = choose_action(
            state={"weapon": {"ammo": 30, "magazine_capacity": 30}},
            needs={"safety": 70},
            goals=[],
            candidates=[
                ActionCandidate("reload", "reload", tags=("safety",),
                                preconditions={"weapon.ammo": {"max": 0}}),
                ActionCandidate("cover", "take_cover", tags=("safety",)),
            ],
            allowed_actions=["reload", "take_cover"],
        )
        self.assertEqual(decision.kind, "take_cover")
        self.assertEqual(decision.rejected[0]["action_id"], "reload")

    def test_rpg_action_allow_list_is_enforced(self):
        decision = choose_action(
            state={"enemy_visible": True}, needs={"health": 80}, goals=[],
            candidates=[
                ActionCandidate("cheat", "delete_enemy", tags=("health",)),
                ActionCandidate("potion", "use_potion", tags=("health",)),
            ],
            allowed_actions=["use_potion", "attack"],
        )
        self.assertEqual(decision.kind, "use_potion")
        self.assertEqual(decision.rejected[0]["reason"], "action not in allow-list")

    def test_no_feasible_action_returns_safe_empty_intent(self):
        decision = choose_action(
            state={"cash": 2}, needs={}, goals=[],
            candidates=[ActionCandidate("buy", "buy_food", preconditions={"cash": {"min": 10}})],
            allowed_actions=["buy_food"],
        )
        self.assertIsNone(decision.kind)
        self.assertEqual(decision.reason, "no feasible allowed action")

    def test_output_explicitly_says_intent_not_execution(self):
        decision = choose_action(state={}, needs={}, goals=[],
                                 candidates=[ActionCandidate("idle", "stay")],
                                 allowed_actions=["stay"])
        self.assertEqual(decision_to_dict(decision)["status"], "intent_only_engine_must_validate")


if __name__ == "__main__":
    unittest.main()
