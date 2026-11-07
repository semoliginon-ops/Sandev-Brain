import unittest

from intent_dev_eval import CASES, run_evaluation


class IntentDevelopmentEvaluationTests(unittest.TestCase):
    def test_dataset_is_large_enough_and_has_all_supported_labels(self):
        self.assertGreaterEqual(len(CASES), 30)
        labels = {expected for _, expected in CASES}
        self.assertTrue({
            "greeting", "thanks", "farewell", "help_request", "danger",
            "heal_request", "tactical_attack", "tactical_defend", "comfort",
            "banter", "unknown",
        }.issubset(labels))

    def test_compositional_fallback_recognizes_paraphrases_conservatively(self):
        from intent import classify_intent

        examples = {
            "Salam, bagaimana keadaanmu?": "greeting",
            "Bantuan tadi sungguh berharga buatku": "thanks",
            "Aku undur diri dulu ya": "farewell",
            "Aku kesulitan mengurus ini sendirian": "help_request",
            "Ancaman musuh semakin mendekat": "danger",
            "Aku butuh ramuan penyembuh sekarang": "heal_request",
            "Bidik penyerang yang paling berbahaya": "tactical_attack",
            "Kita perlu memperkuat pertahanan di utara": "tactical_defend",
            "Aku merasa hampa dan ingin ada teman bicara": "comfort",
            "Ada humor ringan buatku?": "banter",
        }
        for message, expected in examples.items():
            with self.subTest(message=message):
                self.assertEqual(classify_intent(message)["intent"], expected)

    def test_unknown_and_negated_instructions_do_not_become_actions(self):
        from intent import classify_intent

        self.assertEqual(classify_intent("Tolong hitung jumlah bintang di langit")["intent"], "unknown")
        self.assertEqual(classify_intent("Jangan serang musuh")["intent"], "unknown")
        result = classify_intent("Haruskah kita bertahan atau mengejar mereka?")
        self.assertIn(result["status"], {"unknown", "ambiguous"})
        self.assertEqual(result["intent"], "unknown")

    def test_compositional_fallback_abstains_on_mixed_or_unsupported_messages(self):
        from intent import classify_intent

        cases = (
            "Aku sedih, kasih lelucon lucu dong",
            "Tolong serang musuh dan pulihkan darahku",
            "Aku ingin tahu sejarah kerajaan ini",
        )
        for message in cases:
            with self.subTest(message=message):
                self.assertEqual(classify_intent(message)["intent"], "unknown")

    def test_negated_paraphrases_never_become_compositional_actions(self):
        from intent import classify_intent

        cases = (
            "Jangan lumpuhkan penyerang",
            "Tidak perlu menyerbu gerombolan itu",
            "Aku tidak ingin bertahan di sisi utara",
        )
        for message in cases:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["intent"], "unknown")
                self.assertNotEqual(result["status"], "matched")

    def test_evaluation_reports_all_examples_and_mismatches(self):
        report = run_evaluation()
        self.assertEqual(report["total"], len(CASES))
        self.assertEqual(len(report["rows"]), len(CASES))
        self.assertEqual(report["correct"], sum(bool(row["passed"]) for row in report["rows"]))
        self.assertIn("per_expected_intent", report)
        self.assertIn("status_counts", report)


if __name__ == "__main__":
    unittest.main()
