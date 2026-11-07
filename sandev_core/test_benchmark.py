import unittest
from benchmark import SCENARIOS, run_benchmark

class BenchmarkTests(unittest.TestCase):
    def test_scenario_ids_are_unique(self):
        ids = [scenario.scenario_id for scenario in SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_baseline_matches_hand_authored_expectations(self):
        report = run_benchmark()
        self.assertEqual(report['total'], len(SCENARIOS))
        self.assertEqual(report['passed'], report['total'], report['results'])
        self.assertEqual(report['accuracy'], 1.0)

    def test_benchmark_is_labeled_as_regression_not_intelligence(self):
        self.assertIn('not a general intelligence score', run_benchmark()['interpretation'])

if __name__ == '__main__':
    unittest.main()
