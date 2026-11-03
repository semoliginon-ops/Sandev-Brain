import unittest

from followup import FollowUpInputError, resolve_follow_up


CATALOG = [
    {"id": "npc_aria", "name": "Aria", "aliases": ["kapten Aria"], "source": "engine_confirmed"},
    {"id": "npc_bram", "name": "Bram", "aliases": [], "source": "engine_confirmed"},
]


class FollowUpResolutionTests(unittest.TestCase):
    def test_resolves_unique_recent_trusted_reference(self):
        result = resolve_follow_up(
            "Dia siapa?",
            [{"speaker": "npc", "text": "Aku bertemu Aria di desa."}],
            CATALOG,
        )
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["reference_id"], "npc_aria")

    def test_prefers_most_recent_reference_mention(self):
        result = resolve_follow_up(
            "Ceritakan lebih banyak",
            [{"text": "Aria datang."}, {"text": "Lalu aku bertemu Bram."}],
            CATALOG,
        )
        self.assertEqual(result["reference_id"], "npc_bram")

    def test_abstains_when_latest_turn_mentions_multiple_references(self):
        result = resolve_follow_up(
            "Bagaimana dengan mereka?",
            [{"text": "Aria dan Bram sedang berjaga."}],
            CATALOG,
        )
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["reference_id"])

    def test_ignores_untrusted_catalog_entries(self):
        catalog = CATALOG + [
            {"id": "fake", "name": "Raja Bayangan", "aliases": [], "source": "model_guess"}
        ]
        result = resolve_follow_up(
            "Siapa dia?",
            [{"text": "Raja Bayangan muncul."}],
            catalog,
        )
        self.assertEqual(result["status"], "unresolved")

    def test_does_not_resolve_without_follow_up_cue(self):
        result = resolve_follow_up("Halo!", [{"text": "Aria datang."}], CATALOG)
        self.assertEqual(result["status"], "not_follow_up")

    def test_unresolved_when_dialogue_has_no_catalog_reference(self):
        result = resolve_follow_up("Kenapa dia melakukan itu?", [{"text": "Ada seseorang."}], CATALOG)
        self.assertEqual(result["status"], "unresolved")

    def test_rejects_malformed_trusted_catalog_entry(self):
        with self.assertRaises(FollowUpInputError):
            resolve_follow_up("Dia siapa?", [], [{"id": "x", "source": "engine_confirmed"}])


if __name__ == "__main__":
    unittest.main()
