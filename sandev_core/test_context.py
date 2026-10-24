import tempfile
import unittest
from pathlib import Path

from context import ContextInputError, build_context
from memory import MemoryLedger


class ContextPacketTests(unittest.TestCase):
    def make_ledger(self, folder):
        ledger = MemoryLedger(Path(folder) / "memory.json")
        ledger.record_event(
            "Companion covered the player", source="engine_confirmed",
            turn=3, tags=["combat", "companion"], importance=2,
        )
        ledger.remember_fact(
            "preferred_language", "Indonesian", source="player_approved",
            turn=2, tags=["dialogue"],
        )
        return ledger

    def test_builds_cross_genre_context_and_preserves_message(self):
        snapshots = [
            ("plane_shooter", {"health": 35, "enemy_distance": 12}, "Tutup sisi kiri!"),
            ("rpg", {"hp": 20, "mana": 8}, "Aku butuh potion"),
            ("life_sim", {"hunger": 90, "energy": 25}, "Aku lapar banget"),
        ]
        for game_id, state, message in snapshots:
            with self.subTest(game_id=game_id), tempfile.TemporaryDirectory() as folder:
                ledger = self.make_ledger(folder)
                packet = build_context(
                    {"game_id": game_id, "state_version": 7, "state": state,
                     "goals": [{"tag": "survive", "priority": 0.9}]},
                    actor_id="companion-1", player_message=message,
                    memory_ledger=ledger, memory_tags=["combat", "dialogue"],
                )
                self.assertEqual(packet["game_id"], game_id)
                self.assertEqual(packet["state_version"], 7)
                self.assertEqual(packet["state"], state)
                self.assertEqual(packet["player_message"], message)
                self.assertEqual(packet["player_message_status"], "raw_uninterpreted_input")
                self.assertTrue(packet["memories"])
                self.assertTrue(all(m["source"] in {"engine_confirmed", "player_approved"}
                                    for m in packet["memories"]))

    def test_only_provenance_checked_recent_events_are_included(self):
        packet = build_context(
            {"state": {}}, actor_id="joni",
            recent_events=[
                {"event": "Confirmed hit", "source": "engine_confirmed", "turn": 1},
                {"event": "Untrusted assertion", "source": "teacher_model", "turn": 2},
                {"event": "", "source": "player_approved", "turn": 3},
            ],
        )
        self.assertEqual([event["event"] for event in packet["recent_events"]], ["Confirmed hit"])

    def test_limits_recent_events_and_memories(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = MemoryLedger(Path(folder) / "memory.json")
            for turn in range(5):
                ledger.record_event(f"event {turn}", source="engine_confirmed", turn=turn)
            packet = build_context(
                {"state": {}}, actor_id="hero", memory_ledger=ledger,
                recent_events=[
                    {"event": f"recent {i}", "source": "engine_confirmed"} for i in range(5)
                ],
                max_memories=2, max_recent_events=3,
            )
            self.assertEqual(len(packet["memories"]), 2)
            self.assertEqual(len(packet["recent_events"]), 3)

    def test_rejects_oversized_message_and_state(self):
        with self.assertRaises(ContextInputError):
            build_context({"state": {}}, actor_id="hero", player_message="12345", max_message_chars=4)
        with self.assertRaises(ContextInputError):
            build_context({"state": {"blob": "x" * 100}}, actor_id="hero", max_state_bytes=10)

    def test_rejects_non_json_state(self):
        with self.assertRaises(ContextInputError):
            build_context({"state": {"bad": object()}}, actor_id="hero")

    def test_requires_valid_snapshot_and_actor(self):
        with self.assertRaises(ContextInputError):
            build_context([], actor_id="hero")
        with self.assertRaises(ContextInputError):
            build_context({"state": {}}, actor_id=" ")


if __name__ == "__main__":
    unittest.main()
