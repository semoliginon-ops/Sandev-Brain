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

    def test_evaluation_reports_all_examples_and_mismatches(self):
        report = run_evaluation()
        self.assertEqual(report["total"], len(CASES))
        self.assertEqual(len(report["rows"]), len(CASES))
        self.assertEqual(report["correct"], sum(bool(row["passed"]) for row in report["rows"]))
        self.assertIn("per_expected_intent", report)
        self.assertIn("status_counts", report)


if __name__ == "__main__":
    unittest.main()
