import unittest

from personality import PersonalityError, apply_personality_style


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


if __name__ == "__main__":
    unittest.main()
