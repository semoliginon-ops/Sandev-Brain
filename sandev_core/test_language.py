import unittest

from language import LanguageInputError, select_response


def context(game_id="plane_shooter", state=None, memories=None, events=None):
    return {
        "context_version": "1.0",
        "game_id": game_id,
        "actor_id": "companion",
        "state_version": 2,
        "state": state or {"health": 35},
        "needs": {},
        "goals": [],
        "player_message": "Tolong lindungi aku!",
        "player_message_status": "raw_uninterpreted_input",
        "recent_events": events or [],
        "memories": memories or [],
        "memory_tags_used": [],
    }


class ContextualLanguageTests(unittest.TestCase):
    def test_selects_matching_shooter_line(self):
        patterns = [
            {"id": "b", "intent": "danger", "text": "Awas! Aku menutup sisi kananmu!",
             "games": ["plane_shooter"], "required_tags": ["companion"], "priority": 1},
            {"id": "a", "intent": "greeting", "text": "Halo, siap bertempur?"},
        ]
        result = select_response(
            context(events=[{"event": "covered player", "source": "engine_confirmed",
                             "tags": ["companion"]}]),
            patterns, intent="danger",
        )
        self.assertEqual(result["id"], "b")
        self.assertIn("menutup sisi kananmu", result["text"])
        self.assertEqual(result["source"], "curated_pattern")

    def test_uses_relevant_memory_tags(self):
        result = select_response(
            context(memories=[{"kind": "fact", "source": "player_approved",
                               "tags": ["friendly"]}]),
            [{"id": "friendly", "intent": "comfort", "text": "Tenang, aku di sini.",
              "required_tags": ["friendly"]}],
            intent="comfort",
        )
        self.assertEqual(result["text"], "Tenang, aku di sini.")

    def test_does_not_use_untrusted_memory(self):
        result = select_response(
            context(memories=[{"source": "teacher_model", "tags": ["friendly"]}]),
            [{"id": "friendly", "intent": "comfort", "text": "Tenang, aku di sini.",
              "required_tags": ["friendly"]}],
            intent="comfort",
        )
        self.assertEqual(result["status"], "no_matching_response")

    def test_avoids_inappropriate_line_when_need_is_critical(self):
        result = select_response(
            {**context(), "needs": {"health": 95}},
            [{"id": "joke", "intent": "banter", "text": "Waktunya bercanda!",
              "forbidden_needs": ["health"]}],
            intent="banter",
        )
        self.assertEqual(result["status"], "no_matching_response")

    def test_no_match_returns_safe_empty_result(self):
        result = select_response(context(), [], intent="unknown")
        self.assertIsNone(result["text"])
        self.assertEqual(result["status"], "no_matching_response")

    def test_rejects_context_without_raw_input_status(self):
        data = context()
        data["player_message_status"] = "interpreted"
        with self.assertRaises(LanguageInputError):
            select_response(data, [], intent="greeting")

    def test_rejects_duplicate_pattern_ids(self):
        patterns = [
            {"id": "same", "intent": "hello", "text": "Hai!"},
            {"id": "same", "intent": "hello", "text": "Halo!"},
        ]
        with self.assertRaises(LanguageInputError):
            select_response(context(), patterns, intent="hello")


if __name__ == "__main__":
    unittest.main()
