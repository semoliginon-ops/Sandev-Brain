import tempfile
import unittest
from pathlib import Path

from context import ContextInputError, build_context
from memory import MemoryLedger
from npc_memory import NPCMemoryLedger, RelationshipLedger


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

    def test_preserves_optional_host_focus_entity_id(self):
        packet = build_context(
            {"state": {}, "focus_entity_id": "npc_aria"},
            actor_id="aria",
        )
        self.assertEqual(packet["focus_entity_id"], "npc_aria")

    def test_rejects_malformed_host_focus_entity_id(self):
        for focus_id in ("", "  ", 42, []):
            with self.subTest(focus_id=focus_id), self.assertRaises(ContextInputError):
                build_context(
                    {"state": {}, "focus_entity_id": focus_id},
                    actor_id="aria",
                )

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

    def test_includes_bounded_dialogue_as_unverified_context(self):
        history = [
            {"speaker": "player", "text": "Kamu tinggal di mana?", "turn": 1},
            {"speaker": "npc", "text": "Di desa utara.", "turn": 1},
            {"speaker": "player", "text": "Siapa yang tinggal bersamamu?", "turn": 2},
        ]
        packet = build_context(
            {"state": {}}, actor_id="aria", conversation_history=history,
            max_conversation_turns=2,
        )
        self.assertEqual([x["text"] for x in packet["conversation_history"]],
                         ["Di desa utara.", "Siapa yang tinggal bersamamu?"])
        self.assertTrue(all(x["trust"] == "unverified_dialogue"
                            for x in packet["conversation_history"]))

    def test_context_keeps_latest_dialogue_turns_not_oldest_prefix(self):
        history = [
            {"speaker": "player", "text": f"Pesan lama {i}", "turn": i}
            for i in range(30)
        ]
        packet = build_context(
            {"state": {}}, actor_id="aria",
            conversation_history=history, max_conversation_turns=4,
        )
        self.assertEqual(
            [item["text"] for item in packet["conversation_history"]],
            ["Pesan lama 26", "Pesan lama 27", "Pesan lama 28", "Pesan lama 29"],
        )

    def test_zero_dialogue_budget_retains_no_turns(self):
        packet = build_context(
            {"state": {}}, actor_id="aria",
            conversation_history=[
                {"speaker": "player", "text": "Halo", "turn": 1},
            ],
            max_conversation_turns=0,
        )
        self.assertEqual(packet["conversation_history"], [])

    def test_rejects_malformed_dialogue_history(self):
        with self.assertRaises(ContextInputError):
            build_context({"state": {}}, actor_id="aria",
                          conversation_history=[{"speaker": "system", "text": "x", "turn": 1}])

    def test_rejects_non_json_state(self):
        with self.assertRaises(ContextInputError):
            build_context({"state": {"bad": object()}}, actor_id="hero")

    def test_requires_valid_snapshot_and_actor(self):
        with self.assertRaises(ContextInputError):
            build_context([], actor_id="hero")
        with self.assertRaises(ContextInputError):
            build_context({"state": {}}, actor_id=" ")


    def test_context_includes_only_the_selected_npc_player_memory_and_relationship(self):
        with tempfile.TemporaryDirectory() as folder:
            memories = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            relationships = RelationshipLedger(Path(folder) / "relationships.json")
            memories.record_event("aria", "player-1", "Player saved Aria",
                                  source="engine_confirmed", turn=4)
            memories.record_event("borin", "player-1", "Player helped Borin",
                                  source="engine_confirmed", turn=5)
            relationships.apply_event("aria", "player-1", "saved_npc",
                                       source="engine_confirmed")
            packet = build_context(
                {"state": {}}, actor_id="aria",
                npc_memory_ledger=memories,
                npc_relationship_ledger=relationships,
                npc_id="aria", player_id="player-1",
            )
            self.assertEqual([item["event"] for item in packet["npc_memories"]],
                             ["Player saved Aria"])
            self.assertEqual(packet["npc_relationship"]["score"], 15)
            self.assertEqual(packet["npc_relationship"]["label"], "neutral")

    def test_scoped_context_requires_both_identity_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            memories = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            with self.assertRaises(ContextInputError):
                build_context({"state": {}}, actor_id="aria",
                              npc_memory_ledger=memories, npc_id="aria")


if __name__ == "__main__":
    unittest.main()
