import unittest

from intent import IntentInputError, classify_intent, normalize_text
from intent_benchmark import run_benchmark


class IndonesianIntentTests(unittest.TestCase):
    def test_recognizes_casual_indonesian_variants(self):
        for message in ("MAKASIH!!!", "Makasih yaa.", "terima kasih banyak"):
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["intent"], "thanks")
                self.assertEqual(result["status"], "matched")

    def test_recognizes_shooter_tactical_phrases(self):
        result = classify_intent("Tolong lindungi aku!", context={"game_id": "plane_shooter"})
        self.assertEqual(result["intent"], "tactical_defend")
        self.assertEqual(result["game_id"], "plane_shooter")

    def test_recognizes_heal_request(self):
        result = classify_intent("HP-ku rendah, sembuhkan aku!")
        self.assertEqual(result["intent"], "heal_request")

    def test_recognizes_comfort_and_smalltalk(self):
        self.assertEqual(classify_intent("Aku takut, temani aku ya")["intent"], "comfort")
        self.assertEqual(classify_intent("Halo, apa kabar?")["intent"], "greeting")

    def test_unknown_for_unrecognized_message(self):
        result = classify_intent("menurutmu langit sore ini seperti apa?")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["intent"], "unknown")

    def test_ambiguous_message_fails_closed(self):
        result = classify_intent("Awas, lindungi aku!")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["intent"], "unknown")

    def test_action_choice_question_is_not_misread_as_a_command(self):
        result = classify_intent("Menurutmu, kita perlu menyerang atau bertahan?")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["reason"], "action_choice_question_requires_clarification")

    def test_immediate_negation_does_not_trigger_attack(self):
        result = classify_intent("jangan serang musuh")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["intent"], "unknown")

    def test_normalizes_case_and_punctuation(self):
        self.assertEqual(normalize_text("  HAI!!!  "), "hai")
        self.assertEqual(normalize_text("Gak apa-apa"), "tidak apa-apa")


    def test_recognizes_new_paraphrases_conservatively(self):
        cases = {
            "Aku cabut dulu, sampai nanti": "farewell",
            "Mereka mengepung kita dari belakang!": "danger",
            "Kondisiku kritis, perlu pemulihan": "heal_request",
            "Arahkan tembakan ke lawan yang paling dekat": "tactical_attack",
            "Kita perlu berlindung di balik batu": "tactical_defend",
            "Aku lagi down, jangan tinggalin aku sendirian": "comfort",
            "Lempar satu humor receh dong": "banter",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(classify_intent(message)["intent"], expected)

    def test_negated_healing_request_is_not_a_heal_command(self):
        result = classify_intent("Jangan obati aku dulu, aku masih kuat")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["intent"], "unknown")

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(IntentInputError):
            classify_intent(None)
        with self.assertRaises(IntentInputError):
            classify_intent("hai", min_confidence=2)
        with self.assertRaises(IntentInputError):
            classify_intent("hai", patterns=[{"intent": "x", "phrases": ["hai", "hai"]}])

    def test_does_not_guess_from_context_only(self):
        result = classify_intent("hmm...", context={"game_id": "rpg", "needs": {"health": 99}})
        self.assertEqual(result["intent"], "unknown")

    def test_hand_authored_regression_benchmark(self):
        report = run_benchmark()
        self.assertEqual(report["correct"], report["total"], report["rows"])


if __name__ == "__main__":
    unittest.main()
