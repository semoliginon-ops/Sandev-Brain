import json
import tempfile
import unittest
from pathlib import Path

from evaluate import EvaluationError, load_cases, score_prediction, summarize_scores


class DialogueEvaluationTests(unittest.TestCase):
    def test_loads_expanded_eval_dataset_with_multi_turn_context(self):
        cases = load_cases("smollm/data/eval.jsonl")
        self.assertEqual(len(cases), 12)
        self.assertIn("talk", cases[0]["valid_actions"])
        self.assertEqual(cases[0]["expected"]["action"]["type"], "talk")
        self.assertTrue(any(len(case["messages"]) >= 4 for case in cases))
        self.assertTrue(all(case["messages"][-1]["role"] == "user" for case in cases))

    def test_scores_valid_json_and_allowed_action(self):
        raw = json.dumps({
            "say": "Aku siap membantu.",
            "action": {"type": "talk", "target": "Player"},
            "memory_update": {"event": "", "importance": 0},
        })
        expected = {"action": {"type": "talk", "target": "Player"}}
        score = score_prediction(raw, expected, ["talk", "wave"])
        self.assertTrue(score["json_valid"])
        self.assertTrue(score["say_nonempty"])
        self.assertTrue(score["action_valid"])
        self.assertTrue(score["action_match"])

    def test_detects_action_outside_allow_list(self):
        raw = '{"say":"Oke","action":{"type":"teleport","target":"Moon"},"memory_update":{}}'
        score = score_prediction(raw, {"action": None}, ["talk", "wave"])
        self.assertTrue(score["json_valid"])
        self.assertFalse(score["action_valid"])
        self.assertFalse(score["action_match"])

    def test_invalid_json_fails_closed_in_metrics(self):
        score = score_prediction("jawaban bebas tanpa JSON", {"action": None}, ["talk"])
        self.assertFalse(score["json_valid"])
        self.assertFalse(score["say_nonempty"])
        self.assertFalse(score["action_valid"])

    def test_null_action_is_allowed_and_can_match_reference(self):
        raw = '{"say":"Aku belum tahu.","action":null,"memory_update":{"event":"","importance":0}}'
        score = score_prediction(raw, {"action": None}, ["talk"])
        self.assertTrue(score["action_valid"])
        self.assertTrue(score["action_match"])

    def test_summary_states_what_is_not_measured(self):
        summary = summarize_scores([
            {"json_valid": True, "say_nonempty": True, "action_valid": True, "action_match": False},
            {"json_valid": False, "say_nonempty": False, "action_valid": False, "action_match": False},
        ])
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["rates"]["json_valid"], 0.5)
        self.assertIn("naturalness or fluency", summary["not_measured"])

    def test_rejects_eval_row_without_allowed_actions(self):
        row = {"messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "Pesan: halo"},
            {"role": "assistant", "content": '{"say":"Hai","action":null}'},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.jsonl"
            path.write_text(json.dumps(row), encoding="utf-8")
            with self.assertRaises(EvaluationError):
                load_cases(path)


if __name__ == "__main__":
    unittest.main()
