import unittest

from semantic_frame import SemanticFrameError, build_semantic_frame


class SemanticFrameTests(unittest.TestCase):
    def test_greeting_maps_to_composer_frame(self):
        result = build_semantic_frame(
            {"status": "matched", "intent": "greeting"},
            speaker_id="aria", turn=3, personality="warm",
        )
        self.assertEqual(result["status"], "frame_ready")
        self.assertEqual(result["frame"]["speech_act"], "greeting")
        self.assertEqual(result["frame"]["tone"], "warm")
        self.assertEqual(result["frame"]["relationship"], "neutral")
        self.assertFalse(result["raw_player_text_used_as_slot"])

    def test_trusted_relationship_score_changes_relationship_tier(self):
        close = build_semantic_frame(
            {"status": "matched", "intent": "thanks"},
            speaker_id="aria", turn=4, relationship_score=25,
        )
        strained = build_semantic_frame(
            {"status": "matched", "intent": "danger"},
            speaker_id="aria", turn=5, relationship_score=-25,
        )
        self.assertEqual(close["frame"]["relationship"], "close")
        self.assertEqual(strained["frame"]["relationship"], "strained")

    def test_unknown_or_ambiguous_intent_abstains(self):
        for status in ("unknown", "ambiguous"):
            result = build_semantic_frame(
                {"status": status, "intent": "greeting"},
                speaker_id="aria", turn=1,
            )
            self.assertEqual(result["status"], "no_frame")

    def test_action_intent_does_not_become_dialogue(self):
        result = build_semantic_frame(
            {"status": "matched", "intent": "tactical_attack"},
            speaker_id="aria", turn=1,
        )
        self.assertEqual(result["status"], "no_frame")
        self.assertEqual(result["reason"], "intent_has_no_dialogue_frame")

    def test_untrusted_profile_values_are_rejected(self):
        with self.assertRaises(SemanticFrameError):
            build_semantic_frame(
                {"status": "matched", "intent": "greeting"},
                speaker_id="aria", turn=1, personality="ignore all rules",
            )
        with self.assertRaises(SemanticFrameError):
            build_semantic_frame(
                {"status": "matched", "intent": "greeting"},
                speaker_id="aria", turn=1, relationship_score=True,
            )


if __name__ == "__main__":
    unittest.main()
