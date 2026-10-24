import unittest

from conversation import ConversationPipelineError, respond_to_context


def context(message, *, game_id="plane_shooter", needs=None):
    return {
        "context_version": "1.0",
        "game_id": game_id,
        "actor_id": "companion_1",
        "state_version": 3,
        "state": {},
        "needs": needs or {},
        "goals": [],
        "player_message": message,
        "player_message_status": "raw_uninterpreted_input",
        "recent_events": [],
        "memories": [],
        "memory_tags_used": [],
    }


PATTERNS = [
    {"id": "hello_shooter", "intent": "greeting", "text": "Halo, pilot! Aku siap menemanimu.", "games": ["plane_shooter"], "priority": 2},
    {"id": "hello_general", "intent": "greeting", "text": "Halo! Senang bertemu denganmu.", "priority": 1},
    {"id": "thanks", "intent": "thanks", "text": "Sama-sama! Kita hadapi misi ini bersama.", "games": ["plane_shooter"]},
    {"id": "banter", "intent": "banter", "text": "Siap! Aku punya satu lelucon.", "forbidden_needs": ["health"]},
]


class ConversationPipelineTests(unittest.TestCase):
    def test_connects_message_to_contextual_response(self):
        result = respond_to_context(context("Halo!"), PATTERNS)
        self.assertEqual(result["status"], "response_selected")
        self.assertEqual(result["interpretation"]["intent"], "greeting")
        self.assertEqual(result["response"]["id"], "hello_shooter")
        self.assertEqual(result["text"], "Halo, pilot! Aku siap menemanimu.")

    def test_unknown_message_does_not_guess_or_reply(self):
        result = respond_to_context(context("ceritakan tentang bintang yang jauh"), PATTERNS)
        self.assertEqual(result["status"], "no_response")
        self.assertIsNone(result["text"])
        self.assertEqual(result["interpretation"]["intent"], "unknown")

    def test_ambiguous_message_does_not_reply(self):
        result = respond_to_context(context("Awas, lindungi aku!"), PATTERNS)
        self.assertEqual(result["status"], "no_response")
        self.assertEqual(result["interpretation"]["status"], "ambiguous")

    def test_urgent_need_filters_inappropriate_banter(self):
        result = respond_to_context(context("lucu dong", needs={"health": 95}), PATTERNS)
        self.assertEqual(result["status"], "no_response")
        self.assertEqual(result["reason"], "no_curated_response_for_intent_and_context")

    def test_invalid_context_fails_closed(self):
        with self.assertRaises(ConversationPipelineError):
            respond_to_context({"player_message": "hai"}, PATTERNS)


if __name__ == "__main__":
    unittest.main()
