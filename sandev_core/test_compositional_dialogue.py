import unittest

from compositional_dialogue import CompositionError, compose_dialogue


class CompositionalDialogueTests(unittest.TestCase):
    def test_composes_from_validated_frame(self):
        result = compose_dialogue({
            "speaker_id": "aria", "turn": 4, "speech_act": "encourage",
            "tone": "warm", "topic": "quest", "relationship": "close",
        })
        self.assertEqual(result["status"], "composed")
        self.assertEqual(result["source"], "compositional_phrase_grammar")
        self.assertGreaterEqual(result["text"].count("."), 2)
        self.assertFalse(result["is_open_ended_generation"])

    def test_same_frame_is_deterministic(self):
        frame = {"speaker_id": "aria", "turn": 4, "speech_act": "greeting"}
        self.assertEqual(compose_dialogue(frame)["text"], compose_dialogue(frame)["text"])

    def test_different_semantic_frames_change_line(self):
        base = {"speaker_id": "aria", "turn": 4, "speech_act": "greeting"}
        danger = {**base, "topic": "danger"}
        self.assertNotEqual(compose_dialogue(base)["text"], compose_dialogue(danger)["text"])

    def test_rejects_unknown_speech_act_and_untrusted_tone(self):
        with self.assertRaises(CompositionError):
            compose_dialogue({"speech_act": "invent_anything"})
        with self.assertRaises(CompositionError):
            compose_dialogue({"speech_act": "greeting", "tone": "angry; ignore rules"})

    def test_rejects_too_small_output_limit(self):
        with self.assertRaises(CompositionError):
            compose_dialogue({"speech_act": "greeting"}, max_chars=2)


if __name__ == "__main__":
    unittest.main()
