import unittest

from facts import FactLookupError, retrieve_entity_fact


FACTS = [
    {"id": "aria_family", "entity_id": "npc_aria", "aspect": "family",
     "value": "Memiliki seorang adik bernama Lio.", "source": "engine_confirmed"},
    {"id": "aria_home", "entity_id": "npc_aria", "aspect": "location",
     "value": "Desa Utara.", "source": "player_approved"},
]


class TrustedFactLookupTests(unittest.TestCase):
    def test_returns_unique_trusted_fact(self):
        result = retrieve_entity_fact("npc_aria", "family", FACTS)
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["fact"]["value"], "Memiliki seorang adik bernama Lio.")
        self.assertEqual(result["fact"]["source"], "engine_confirmed")

    def test_ignores_untrusted_model_guess(self):
        facts = FACTS + [
            {"id": "guess", "entity_id": "npc_aria", "aspect": "family",
             "value": "Anak raja.", "source": "model_guess"}
        ]
        result = retrieve_entity_fact("npc_aria", "family", facts)
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["fact"]["id"], "aria_family")

    def test_does_not_return_facts_for_another_entity(self):
        result = retrieve_entity_fact("npc_bram", "family", FACTS)
        self.assertEqual(result["status"], "not_found")

    def test_abstains_on_conflicting_trusted_facts(self):
        facts = FACTS + [
            {"id": "aria_family_alt", "entity_id": "npc_aria", "aspect": "family",
             "value": "Tidak memiliki saudara.", "source": "engine_confirmed"}
        ]
        result = retrieve_entity_fact("npc_aria", "family", facts)
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["fact"])

    def test_missing_reference_or_aspect_does_not_search(self):
        result = retrieve_entity_fact(None, "family", FACTS)
        self.assertEqual(result["status"], "not_attempted")

    def test_rejects_malformed_trusted_fact(self):
        with self.assertRaises(FactLookupError):
            retrieve_entity_fact("npc_aria", "family", [
                {"id": "bad", "entity_id": "npc_aria", "aspect": "family",
                 "source": "engine_confirmed"}
            ])


if __name__ == "__main__":
    unittest.main()
