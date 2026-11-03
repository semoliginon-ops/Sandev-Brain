import tempfile
import unittest
from pathlib import Path

from npc_memory import NPCMemoryError, NPCMemoryLedger, RelationshipLedger


class NPCMemoryLedgerTests(unittest.TestCase):
    def test_memory_is_isolated_by_npc_and_player(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            ledger.record_event("aria", "player-1", "Player saved Aria",
                                source="engine_confirmed", turn=2)
            ledger.record_event("borin", "player-1", "Player helped Borin",
                                source="engine_confirmed", turn=3)
            ledger.record_event("aria", "player-2", "Player met Aria",
                                source="player_approved", turn=4)
            found = ledger.retrieve("aria", "player-1")
            self.assertEqual([item["event"] for item in found], ["Player saved Aria"])
            self.assertEqual(ledger.retrieve("aria", "player-2")[0]["event"],
                             "Player met Aria")

    def test_untrusted_dialogue_cannot_become_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            with self.assertRaises(NPCMemoryError):
                ledger.record_event("aria", "player-1", "Player says I helped",
                                    source="unverified_dialogue", turn=1)
            self.assertEqual(ledger.retrieve("aria", "player-1"), [])

    def test_verified_fact_replaces_only_same_npc_player_fact(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            ledger.remember_fact("aria", "player-1", "home", "North village",
                                 source="engine_confirmed", turn=1)
            ledger.remember_fact("aria", "player-2", "home", "South village",
                                 source="engine_confirmed", turn=1)
            ledger.remember_fact("aria", "player-1", "home", "East village",
                                 source="player_approved", turn=2)
            self.assertEqual(ledger.retrieve("aria", "player-1")[0]["value"],
                             "East village")
            self.assertEqual(ledger.retrieve("aria", "player-2")[0]["value"],
                             "South village")

    def test_priority_decay_demotes_old_memories_but_preserves_important_ones(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json", decay_interval=5)
            ledger.record_event("aria", "player-1", "small talk",
                                source="engine_confirmed", turn=1, importance=1)
            ledger.record_event("aria", "player-1", "kept promise",
                                source="engine_confirmed", turn=1, importance=3,
                                tags=["promise"])
            ledger.record_event("aria", "player-1", "recent greeting",
                                source="engine_confirmed", turn=95, importance=1)
            found = ledger.retrieve("aria", "player-1", current_turn=100)
            self.assertEqual([item["event"] for item in found],
                             ["kept promise", "recent greeting"])

    def test_forget_expired_removes_only_old_low_importance_events(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            ledger.record_event("aria", "player-1", "old minor detail",
                                source="engine_confirmed", turn=1, importance=1)
            ledger.record_event("aria", "player-1", "important promise",
                                source="engine_confirmed", turn=1, importance=3)
            ledger.record_event("aria", "player-1", "recent detail",
                                source="engine_confirmed", turn=95, importance=1)
            removed = ledger.forget_expired(current_turn=100, max_age=50)
            self.assertEqual(removed, 1)
            remaining = [item["event"] for item in ledger.retrieve("aria", "player-1")]
            self.assertEqual(set(remaining), {"important promise", "recent detail"})

    def test_forgetting_rejects_invalid_turn(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json")
            with self.assertRaises(NPCMemoryError):
                ledger.forget_expired(current_turn=-1)

    def test_memory_limit_and_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCMemoryLedger(Path(folder) / "npc-memory.json", max_items=2)
            for turn in range(3):
                ledger.record_event("aria", "player-1", f"event {turn}",
                                    source="engine_confirmed", turn=turn)
            self.assertEqual(len(ledger.retrieve("aria", "player-1", limit=5)), 2)
            with self.assertRaises(NPCMemoryError):
                ledger.retrieve("", "player-1")


class RelationshipLedgerTests(unittest.TestCase):
    def test_trusted_events_change_relationship_deterministically(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = RelationshipLedger(Path(folder) / "relationships.json")
            self.assertEqual(ledger.snapshot("aria", "player-1")["label"], "neutral")
            result = ledger.apply_event("aria", "player-1", "saved_npc",
                                        source="engine_confirmed")
            self.assertEqual(result["score"], 15)
            self.assertEqual(result["label"], "neutral")
            result = ledger.apply_event("aria", "player-1", "kept_promise",
                                        source="player_approved")
            self.assertEqual(result["score"], 25)
            self.assertEqual(result["label"], "friendly")

    def test_untrusted_or_unknown_events_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = RelationshipLedger(Path(folder) / "relationships.json")
            with self.assertRaises(NPCMemoryError):
                ledger.apply_event("aria", "player-1", "saved_npc",
                                   source="unverified_dialogue")
            with self.assertRaises(NPCMemoryError):
                ledger.apply_event("aria", "player-1", "arbitrary_score",
                                   source="engine_confirmed")
            self.assertEqual(ledger.snapshot("aria", "player-1")["score"], 0)

    def test_scores_are_clamped_and_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = RelationshipLedger(Path(folder) / "relationships.json")
            for _ in range(10):
                result = ledger.apply_event("aria", "player-1", "saved_npc",
                                            source="engine_confirmed")
            self.assertEqual(result["score"], 100)
            self.assertEqual(result["label"], "trusted")
            self.assertEqual(ledger.snapshot("aria", "player-2")["score"], 0)
            self.assertEqual(ledger.snapshot("borin", "player-1")["score"], 0)


if __name__ == "__main__":
    unittest.main()
