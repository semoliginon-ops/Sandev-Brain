import unittest

from grounding import GroundingInputError, ground_entities


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
            {"id": "enemy-2", "name": "Naga", "aliases": []},
        ]
        result = ground_entities("Serang Goblin dan Naga", entities)
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

    def test_cross_genre_entity_names(self):
        cases = [
            ("plane shooter", "Lindungi pesawat Falcon", [{"id": "ally-1", "name": "Falcon"}], "ally-1"),
            ("rpg", "Bantu Raka melawan bos", [{"id": "ally-1", "name": "Raka"}, {"id": "boss-1", "name": "Bos"}], None),
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
