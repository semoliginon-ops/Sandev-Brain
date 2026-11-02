"""Focused Indonesian paraphrase probes for the bounded intent baseline.

These are development regression probes, not an independent or held-out benchmark.
"""
import unittest

from intent import classify_intent


class ParaphraseProbeTests(unittest.TestCase):
    def test_distinct_comfort_paraphrases_share_intent(self):
        variants = (
            "Aku khawatir dan ingin teman bicara",
            "Aku kehilangan semangat, tolong temani aku",
            "Rasanya hampa dan aku ingin ditemani",
        )
        for message in variants:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["status"], "matched", result)
                self.assertEqual(result["intent"], "comfort", result)

    def test_unsupported_or_ambiguous_nearby_messages_abstain(self):
        variants = (
            "Aku sedang memikirkan banyak hal",
            "Menurutmu, kenapa orang bisa merasa kesepian?",
            "Aku takut bahaya, tapi jangan serang siapa pun",
        )
        for message in variants:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertIn(result["status"], {"unknown", "ambiguous"}, result)

    def test_paraphrase_probes_do_not_promote_action_mentions(self):
        variants = (
            "Aku sedang cerita soal menyerang musuh",
            "Aku ingin menyerang musuh nanti",
            "Jangan menyerang musuh sekarang",
        )
        for message in variants:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertNotEqual(result["intent"], "tactical_attack", result)


if __name__ == "__main__":
    unittest.main()
