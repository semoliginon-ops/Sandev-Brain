import unittest

from command import CommandInputError, interpret_player_command


ENTITIES = [
    {"id": "enemy-1", "name": "Goblin", "aliases": ["goblin"]},
    {"id": "enemy-2", "name": "Bandit", "aliases": ["bandit"]},
    {"id": "ally-1", "name": "Falcon", "aliases": ["pesawat falcon"]},
]


class PlayerCommandTests(unittest.TestCase):
    def test_explicit_attack_and_current_target_create_non_executable_proposal(self):
        result = interpret_player_command("Serang Goblin", ENTITIES, context={"game_id": "rpg"})
        self.assertEqual(result["status"], "proposal")
        self.assertEqual(result["intent"], "tactical_attack")
        self.assertEqual(result["target"]["entity_id"], "enemy-1")
        self.assertFalse(result["execution_allowed"])

    def test_attack_pronoun_uses_explicit_focus_context(self):
        result = interpret_player_command(
            "Serang dia", ENTITIES, context={"focus_entity_id": "enemy-2"}
        )
        self.assertEqual(result["status"], "proposal")
        self.assertEqual(result["target"]["entity_id"], "enemy-2")
        self.assertFalse(result["execution_allowed"])

    def test_spatial_reference_uses_engine_relation_metadata(self):
        entities = [
            {"id": "ally-1", "name": "Falcon"},
            {"id": "enemy-1", "name": "Bandit", "is_hostile": True, "relations_to": {"ally-1": "behind"}},
        ]
        result = interpret_player_command(
            "Serang musuh di belakangnya", entities, context={"focus_entity_id": "ally-1"}
        )
        self.assertEqual(result["status"], "proposal")
        self.assertEqual(result["target"]["entity_id"], "enemy-1")

    def test_two_target_mentions_are_ambiguous(self):
        result = interpret_player_command("Serang Goblin dan Bandit", ENTITIES)
        self.assertEqual(result["status"], "ambiguous_target")
        self.assertIsNone(result["target"])
        self.assertFalse(result["execution_allowed"])

    def test_multi_step_command_is_not_silently_reduced(self):
        result = interpret_player_command("Lindungi Falcon, lalu serang Bandit", ENTITIES)
        self.assertEqual(result["status"], "needs_planning")
        self.assertFalse(result["execution_allowed"])

    def test_unknown_target_is_not_guessed(self):
        result = interpret_player_command("Serang Naga", ENTITIES)
        self.assertEqual(result["status"], "target_required")
        self.assertIsNone(result["target"])

    def test_negated_attack_does_not_become_proposal(self):
        result = interpret_player_command("Jangan serang Goblin", ENTITIES)
        self.assertNotEqual(result["status"], "proposal")
        self.assertFalse(result["execution_allowed"])

    def test_non_action_chat_is_not_command(self):
        result = interpret_player_command("Halo, apa kabar?", ENTITIES)
        self.assertEqual(result["status"], "not_a_confident_action")

    def test_invalid_entities_raise_domain_error(self):
        with self.assertRaises(CommandInputError):
            interpret_player_command("Serang Goblin", "not a list")

    def test_invalid_message_raises_domain_error(self):
        for message in (None, 42, ["Serang Goblin"]):
            with self.subTest(message=message):
                with self.assertRaises(CommandInputError):
                    interpret_player_command(message, ENTITIES)

    def test_invalid_context_raises_domain_error(self):
        with self.assertRaises(CommandInputError):
            interpret_player_command("Serang Goblin", ENTITIES, context="rpg")


if __name__ == "__main__":
    unittest.main()
