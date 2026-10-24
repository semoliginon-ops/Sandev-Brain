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


    def test_recognizes_more_natural_indonesian_paraphrases(self):
        cases = {
            "Pagi, partner!": "greeting",
            "Akhirnya kita berjumpa lagi": "greeting",
            "Aku harus pamit sekarang": "farewell",
            "Nanti kita lanjut lagi, ya": "farewell",
            "Bisa tolong urus masalah ini bareng aku?": "help_request",
            "Aku butuh bantuanmu untuk menyelesaikannya": "help_request",
            "Posisi kita sedang dikepung!": "danger",
            "Ada yang mengincar kita dari arah belakang": "danger",
            "Aku hampir tumbang, cepat pulihkan aku": "heal_request",
            "Bisa pakai ramuan untuk memulihkan kondisiku?": "heal_request",
            "Jadikan musuh itu sasaran utama": "tactical_attack",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["status"], "matched", result)
                self.assertEqual(result["intent"], expected, result)

    def test_mixed_defensive_instruction_prefers_explicit_safe_action(self):
        cases = (
            "Bantu aku berlindung sampai situasi aman",
            "Jaga posisi dan jangan terpancing maju",
            "Jangan dekati mereka, berlindung dulu",
        )
        for message in cases:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["status"], "matched", result)
                self.assertEqual(result["intent"], "tactical_defend", result)

    def test_action_choice_question_stays_ambiguous(self):
        result = classify_intent("Menurutmu menyerang atau bertahan lebih baik?")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["intent"], "unknown")

    def test_negated_healing_request_is_not_a_heal_command(self):
        result = classify_intent("Jangan obati aku dulu, aku masih kuat")
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["intent"], "unknown")

    def test_contrastive_negation_cancels_earlier_action_cue(self):
        cases = (
            "Aku butuh potion, tapi jangan dulu",
            "Aku ingin menyerang, namun jangan sekarang",
            "Aku perlu heal, tetapi tidak sekarang",
        )
        for message in cases:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["status"], "unknown", result)
                self.assertEqual(result["intent"], "unknown", result)

    def test_casual_negated_attack_stays_unknown(self):
        for message in ("Aku nggak mau menyerang", "Aku gak mau serang musuh"):
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["intent"], "unknown", result)

    def test_recounted_or_discussed_actions_are_not_commands(self):
        cases = (
            "Aku cuma cerita soal serang musuh tadi",
            "Apa pendapatmu kalau aku serang musuh?",
            "Aku tadi bilang serang musuh, bukan menyuruh sekarang",
        )
        for message in cases:
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["intent"], "unknown", result)
                self.assertEqual(result["status"], "unknown", result)

    def test_stated_future_intention_is_not_an_immediate_command(self):
        for message in (
            "Aku mau serang musuh nanti",
            "Saya ingin serang musuh besok",
            "Kita akan serang musuh lain waktu",
        ):
            with self.subTest(message=message):
                result = classify_intent(message)
                self.assertEqual(result["status"], "unknown", result)
                self.assertEqual(result["intent"], "unknown", result)

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
