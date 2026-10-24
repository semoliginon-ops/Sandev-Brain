import unittest

from heldout_intent_eval import CASES, run_evaluation


class HeldoutIntentEvaluationTests(unittest.TestCase):
    def test_holdout_has_expected_intent_and_safety_coverage(self):
        self.assertGreaterEqual(len(CASES), 25)
        labels = {expected for _, expected in CASES}
        self.assertTrue({
            "greeting", "thanks", "farewell", "help_request", "danger",
            "heal_request", "tactical_attack", "tactical_defend", "comfort",
            "banter", "unknown",
        }.issubset(labels))

    def test_report_preserves_every_case_and_real_mismatches(self):
        report = run_evaluation()
        self.assertEqual(report["total"], len(CASES))
        self.assertEqual(len(report["rows"]), len(CASES))
        self.assertEqual(
            report["correct"],
            sum(bool(row["passed"]) for row in report["rows"]),
        )
        self.assertEqual(
            report["accuracy"],
            report["correct"] / report["total"],
        )
        self.assertIn("per_expected_intent", report)
        self.assertIn("status_counts", report)


if __name__ == "__main__":
    unittest.main()
