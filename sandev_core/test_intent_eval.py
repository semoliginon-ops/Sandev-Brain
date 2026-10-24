import unittest

from intent_eval import CASES, run_evaluation


class IntentEvaluationTests(unittest.TestCase):
    def test_challenge_set_has_paraphrase_coverage(self):
        self.assertGreaterEqual(len(CASES), 20)
        labels = {expected for _, expected in CASES}
        self.assertTrue({
            "greeting", "thanks", "farewell", "help_request", "danger",
            "heal_request", "tactical_attack", "tactical_defend", "comfort",
            "banter", "unknown",
        }.issubset(labels))

    def test_evaluation_reports_each_case_without_hiding_mismatches(self):
        report = run_evaluation()
        self.assertEqual(report["total"], len(CASES))
        self.assertEqual(len(report["rows"]), len(CASES))
        self.assertGreaterEqual(report["correct"], 0)
        self.assertLessEqual(report["correct"], report["total"])
        self.assertEqual(
            report["correct"],
            sum(bool(row["passed"]) for row in report["rows"]),
        )
        self.assertIn("per_expected_intent", report)
        self.assertIn("status_counts", report)


if __name__ == "__main__":
    unittest.main()
