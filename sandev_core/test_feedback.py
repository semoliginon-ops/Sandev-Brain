import tempfile
import unittest
from pathlib import Path
from brain import ActionCandidate, choose_action
from feedback import OutcomeLedger

class OutcomeFeedbackTests(unittest.TestCase):
    def test_rejects_unconfirmed_outcome(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = OutcomeLedger(Path(folder) / 'outcomes.json')
            with self.assertRaises(ValueError):
                ledger.record_outcome('rest', success=True, source='teacher_model', turn=1)
            self.assertEqual(ledger.items, [])

    def test_smoothing_and_context_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = OutcomeLedger(Path(folder) / 'outcomes.json')
            self.assertEqual(ledger.adjustment_for('rest', context_tags=['safe']), 0.0)
            for turn in range(5):
                ledger.record_outcome('rest', success=True, source='engine_confirmed', turn=turn, context_tags=['safe'])
            self.assertGreater(ledger.adjustment_for('rest', context_tags=['safe']), 0)
            self.assertEqual(ledger.adjustment_for('rest', context_tags=['combat']), 0.0)
            self.assertLessEqual(ledger.adjustment_for('rest', context_tags=['safe']), 10.0)

    def test_confirmed_feedback_can_change_candidate_ranking(self):
        candidates = [ActionCandidate('a', 'rest'), ActionCandidate('b', 'work')]
        decision = choose_action(state={}, needs={}, goals=[], candidates=candidates,
                                 allowed_actions=['rest', 'work'],
                                 feedback_adjustments={'b': 5.0})
        self.assertEqual(decision.action_id, 'b')
        self.assertIn('confirmed_outcome_feedback', decision.reason)

if __name__ == '__main__':
    unittest.main()
