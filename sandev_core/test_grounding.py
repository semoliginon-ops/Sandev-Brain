import unittest

from grounding import GroundingInputError, ground_entities, resolve_context_reference


class EntityGroundingTests(unittest.TestCase):
    def test_grounds_current_entity_by_name_or_alias(self):
        entities = [
            {"id": "enemy-1", "name": "Goblin Penjaga", "aliases": ["goblin", "penjaga"]},
            {"id": "enemy-2", "name": "Naga Api", "aliases": ["naga"]},
        ]
        result = ground_entities("Tolong serang si goblin!", entities)
        self.assertEqual(result["status"], "grounded")
        self.assertEqual(result["entity_id"], "enemy-1")
        self.assertEqual(result["matched_alias"], "goblin")

    def test_longest_alias_wins_for_specific_name(self):
        entities = [
            {"id": "enemy-1", "name": "Goblin", "aliases": []},
            {"id": "enemy-2", "name": "Goblin Elite", "aliases": ["elite"]},
        ]
        result = ground_entities("Serang Goblin Elite sekarang", entities)
        self.assertEqual(result["status"], "grounded")
        self.assertEqual(result["entity_id"], "enemy-2")

    def test_equal_mentions_of_different_entities_are_ambiguous(self):
        entities = [
            {"id": "enemy-1", "name": "Goblin", "aliases": []},
            {"id": "enemy-2", "name": "Bandit", "aliases": []},
        ]
        result = ground_entities("Serang Goblin dan Bandit", entities)
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["entity_id"])
        self.assertEqual({item["entity_id"] for item in result["candidates"]}, {"enemy-1", "enemy-2"})

    def test_does_not_guess_when_entity_is_not_in_current_snapshot(self):
        result = ground_entities("Serang naga", [{"id": "enemy-1", "name": "Goblin"}])
        self.assertEqual(result["status"], "unresolved")
        self.assertIsNone(result["entity_id"])

    def test_word_boundaries_prevent_partial_name_matches(self):
        result = ground_entities("Serang goblinoid", [{"id": "enemy-1", "name": "goblin"}])
        self.assertEqual(result["status"], "unresolved")

    def test_rejects_duplicate_ids_and_malformed_entities(self):
        with self.assertRaises(GroundingInputError):
            ground_entities("goblin", [
                {"id": "same", "name": "Goblin"},
                {"id": "same", "name": "Goblin lain"},
            ])
        with self.assertRaises(GroundingInputError):
            ground_entities("goblin", [{"id": "x", "name": "Goblin", "aliases": "gob"}])

    def test_pronoun_resolves_only_from_explicit_focus_id(self):
        entities = [
            {"id": "ally-1", "name": "Falcon"},
            {"id": "enemy-1", "name": "Bandit"},
        ]
        result = resolve_context_reference("Serang dia", entities, context={"focus_entity_id": "enemy-1"})
        self.assertEqual(result["status"], "grounded")
        self.assertEqual(result["entity_id"], "enemy-1")

    def test_pronoun_without_focus_is_not_guessed(self):
        result = resolve_context_reference("Serang dia", [{"id": "a", "name": "Falcon"}], context={})
        self.assertEqual(result["status"], "unresolved")

    def test_unique_hostile_behind_focus_uses_engine_relation(self):
        entities = [
            {"id": "ally-1", "name": "Falcon"},
            {"id": "enemy-1", "name": "Bandit", "is_hostile": True, "relations_to": {"ally-1": "behind"}},
            {"id": "enemy-2", "name": "Goblin", "is_hostile": True, "relations_to": {"ally-1": "ahead"}},
        ]
        result = resolve_context_reference(
            "Serang musuh di belakangnya", entities, context={"focus_entity_id": "ally-1"}
        )
        self.assertEqual(result["status"], "grounded")
        self.assertEqual(result["entity_id"], "enemy-1")

    def test_multiple_hostiles_behind_focus_are_ambiguous(self):
        entities = [
            {"id": "ally-1", "name": "Falcon"},
            {"id": "enemy-1", "name": "Bandit", "is_hostile": True, "relations_to": {"ally-1": "behind"}},
            {"id": "enemy-2", "name": "Goblin", "is_hostile": True, "relations_to": {"ally-1": "behind"}},
        ]
        result = resolve_context_reference(
            "Serang musuh di belakangnya", entities, context={"focus_entity_id": "ally-1"}
        )
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["entity_id"])

    def test_cross_genre_entity_names(self):
        cases = [
            ("plane shooter", "Lindungi pesawat Falcon", [{"id": "ally-1", "name": "Falcon"}], "ally-1"),
            ("rpg", "Bantu Raka melawan Naga", [{"id": "ally-1", "name": "Raka"}, {"id": "enemy-1", "name": "Naga"}], None),
            ("life sim", "Ajak Budi bicara", [{"id": "npc-1", "name": "Budi"}], "npc-1"),
        ]
        for game_id, message, entities, expected in cases:
            with self.subTest(game_id=game_id):
                result = ground_entities(message, entities)
                if expected is None:
                    self.assertEqual(result["status"], "ambiguous")
                else:
                    self.assertEqual(result["entity_id"], expected)


if __name__ == "__main__":
    unittest.main()
