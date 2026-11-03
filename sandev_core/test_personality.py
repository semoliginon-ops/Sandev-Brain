import unittest

from personality import PersonalityError, apply_personality_style, apply_emotion_style


class PersonalityTests(unittest.TestCase):
    def test_each_profile_has_its_authored_voice(self):
        expected = {
            "neutral": "Halo!",
            "friendly": "Dengan senang hati, Halo!",
            "shy": "E-eh, Halo!",
            "cold": "Dengar. Halo!",
            "humorous": "Hehe, Halo! Lumayan, kan?",
            "angry": "Hmph. Halo!",
        }
        for profile, text in expected.items():
            with self.subTest(profile=profile):
                result = apply_personality_style("Halo!", profile)
                self.assertEqual(result["status"], "styled")
                self.assertEqual(result["text"], text)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(PersonalityError):
            apply_personality_style("Halo!", "mysterious")

    def test_too_long_styled_reply_abstains(self):
        result = apply_personality_style("Halo!", "friendly", max_chars=5)
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["text"])

    def test_emotional_state_adds_authored_delivery_cue(self):
        state = {"values": {"joy": 50, "fear": 75, "anger": 0,
                           "sadness": 0, "trust": 50, "suspicion": 0},
                 "mood": "happy"}
        result = apply_emotion_style("Aku melihat sesuatu.", state)
        self.assertEqual(result["mood"], "afraid")
        self.assertEqual(result["text"], "*suaranya bergetar* Aku melihat sesuatu.")

    def test_emotional_style_rederives_mood_instead_of_trusting_label(self):
        state = {"values": {"joy": 80, "fear": 0, "anger": 70,
                           "sadness": 0, "trust": 90, "suspicion": 0},
                 "mood": "happy"}
        result = apply_emotion_style("Jangan pergi.", state)
        self.assertEqual(result["mood"], "angry")
        self.assertTrue(result["text"].startswith("*menjawab dengan nada marah* "))

    def test_invalid_emotional_snapshot_is_rejected(self):
        with self.assertRaises(PersonalityError):
            apply_emotion_style("Halo!", {"values": {"fear": 100}})

    def test_emotional_cue_respects_response_length(self):
        state = {"values": {"joy": 0, "fear": 70, "anger": 0,
                           "sadness": 0, "trust": 0, "suspicion": 0}}
        result = apply_emotion_style("Halo!", state, max_chars=5)
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["text"])


if __name__ == "__main__":
    unittest.main()
