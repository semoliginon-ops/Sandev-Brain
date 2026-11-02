import tempfile
import unittest
from pathlib import Path

from companion import CompanionError, CompanionRuntime


PATTERNS = [
    {"id": "warm_hello", "intent": "greeting", "text": "Hai! Senang kamu kembali.", "personality": "warm", "priority": 3},
    {"id": "dry_hello", "intent": "greeting", "text": "Oh. Kamu lagi.", "personality": "dry", "priority": 3},
    {"id": "generic_hello", "intent": "greeting", "text": "Halo, partner.", "priority": 1},
]


class CompanionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "companion-memory.json"
        self.companion = CompanionRuntime(
            self.path, companion_id="npc_aria", personality="warm",
            personality_tags=["kind", "curious"],
        )
        self.snapshot = {
            "game_id": "rpg-demo", "state_version": 4,
            "state": {"player": {"hp": 40}}, "needs": {}, "goals": [],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_personality_selects_compatible_authored_line(self):
        result = self.companion.respond(self.snapshot, "Halo!", PATTERNS)
        self.assertEqual(result["status"], "response_selected")
        self.assertEqual(result["response"]["id"], "warm_hello")
        self.assertEqual(result["personality"], "warm")

    def test_confirmed_interaction_persists_and_changes_relationship(self):
        result = self.companion.record_confirmed_interaction(
            "Player saved Aria from the goblin", source="engine_confirmed",
            turn=7, relationship_delta=3, tags=["rescue"],
        )
        self.assertEqual(result["relationship_score"], 3)
        reloaded = CompanionRuntime(
            self.path, companion_id="npc_aria", personality="warm"
        )
        self.assertEqual(reloaded._relationship_score(), 3)
        memories = reloaded.memory.retrieve(tags=["rescue"])
        self.assertEqual(memories[0]["event"], "Player saved Aria from the goblin")

    def test_unverified_relationship_change_is_rejected(self):
        with self.assertRaises(CompanionError):
            self.companion.record_confirmed_interaction(
                "Player says they helped", source="player_message",
                turn=1, relationship_delta=5,
            )
        self.assertEqual(self.companion._relationship_score(), 0)
        self.assertEqual(self.companion.memory.export(), [])

    def test_relationship_delta_is_bounded(self):
        with self.assertRaises(CompanionError):
            self.companion.record_confirmed_interaction(
                "Huge change", source="engine_confirmed",
                turn=1, relationship_delta=99,
            )

    def test_personal_fact_requires_player_approval(self):
        with self.assertRaises(CompanionError):
            self.companion.remember_player_approved_fact(
                "favorite_food", "ramen", source="player_message", turn=2,
            )
        saved = self.companion.remember_player_approved_fact(
            "favorite_food", "ramen", source="player_approved", turn=2,
        )
        self.assertEqual(saved["value"], "ramen")

    def test_unknown_input_does_not_guess_dialogue(self):
        result = self.companion.respond(
            self.snapshot, "Ceritakan kisah yang belum pernah ada", PATTERNS
        )
        self.assertEqual(result["status"], "no_response")
        self.assertIsNone(result["text"])


if __name__ == "__main__":
    unittest.main()
