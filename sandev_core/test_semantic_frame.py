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


    def test_rich_interpretation_envelope_preserves_semantic_scope(self):
        result = build_semantic_frame(
            {
                "schema_version": "1.0",
                "speech_act": "statement",
                "temporal_scope": "unspecified",
                "negation": "not_detected",
                "intent": "help_request",
                "intent_status": "matched",
                "confidence": 0.9,
                "target_grounding": "not_applicable",
                "needs_clarification": False,
                "clarification_reason": None,
                "execution_allowed": False,
                "game_id": "fantasy_rpg",
            },
            speaker_id="aria", turn=8, personality="warm",
        )
        self.assertEqual(result["status"], "frame_ready")
        frame = result["frame"]
        self.assertEqual(frame["intent"], "help_request")
        self.assertEqual(frame["source_speech_act"], "statement")
        self.assertEqual(frame["temporal_scope"], "unspecified")
        self.assertEqual(frame["negation"], "not_detected")
        self.assertEqual(frame["game_id"], "fantasy_rpg")
        self.assertEqual(frame["confidence"], 0.9)
        self.assertFalse(result["execution_allowed"])

    def test_rich_question_or_uncertain_interpretation_does_not_become_dialogue(self):
        base = {
            "schema_version": "1.0",
            "speech_act": "question",
            "temporal_scope": "unspecified",
            "negation": "not_detected",
            "intent": "help_request",
            "intent_status": "matched",
            "confidence": 0.9,
            "target_grounding": "not_applicable",
            "needs_clarification": True,
            "execution_allowed": False,
            "game_id": "life_sim",
        }
        result = build_semantic_frame(base, speaker_id="aria", turn=9)
        self.assertEqual(result["status"], "no_frame")
        self.assertEqual(
            result["reason"],
            "interpretation_requires_clarification_or_is_not_a_clear_dialogue_act",
        )

        negated = dict(base, speech_act="statement", needs_clarification=False,
                       negation="detected")
        self.assertEqual(
            build_semantic_frame(negated, speaker_id="aria", turn=10)["status"],
            "no_frame",
        )

    def test_rich_interpretation_rejects_execution_authorization(self):
        envelope = {
            "schema_version": "1.0",
            "speech_act": "statement",
            "temporal_scope": "unspecified",
            "negation": "not_detected",
            "intent": "greeting",
            "intent_status": "matched",
            "confidence": 0.9,
            "target_grounding": "not_applicable",
            "needs_clarification": False,
            "execution_allowed": True,
            "game_id": "open_world",
        }
        with self.assertRaises(SemanticFrameError):
            build_semantic_frame(envelope, speaker_id="aria", turn=1)

    def test_rich_interpretation_rejects_invalid_confidence_and_schema(self):
        envelope = {
            "schema_version": "1.0",
            "speech_act": "statement",
            "temporal_scope": "unspecified",
            "negation": "not_detected",
            "intent": "greeting",
            "intent_status": "matched",
            "confidence": True,
            "target_grounding": "not_applicable",
            "needs_clarification": False,
            "execution_allowed": False,
            "game_id": "open_world",
        }
        with self.assertRaises(SemanticFrameError):
            build_semantic_frame(envelope, speaker_id="aria", turn=1)
        with self.assertRaises(SemanticFrameError):
            build_semantic_frame(dict(envelope, schema_version="99.0", confidence=0.8),
                                 speaker_id="aria", turn=1)


if __name__ == "__main__":
    unittest.main()
