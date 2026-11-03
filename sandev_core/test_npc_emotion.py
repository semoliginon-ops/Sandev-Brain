import tempfile
import unittest
from pathlib import Path

from npc_emotion import NPCEmotionError, NPCEmotionLedger
from context import build_context, ContextInputError


class NPCEmotionLedgerTests(unittest.TestCase):
    def test_trusted_events_change_emotions_and_derive_mood(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json")
            initial = ledger.snapshot("aria", "player-1")
            self.assertEqual(initial["mood"], "calm")
            result = ledger.apply_event(
                "aria", "player-1", "saved_npc",
                source="engine_confirmed", turn=1,
            )
            self.assertEqual(result["values"]["joy"], 62)
            self.assertEqual(result["values"]["fear"], 0)
            self.assertEqual(result["mood"], "happy")

    def test_untrusted_and_unknown_events_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json")
            with self.assertRaises(NPCEmotionError):
                ledger.apply_event("aria", "player-1", "saved_npc",
                                   source="unverified_dialogue", turn=1)
            with self.assertRaises(NPCEmotionError):
                ledger.apply_event("aria", "player-1", "invented_event",
                                   source="engine_confirmed", turn=1)
            self.assertEqual(ledger.snapshot("aria", "player-1")["mood"], "calm")

    def test_emotions_are_isolated_by_npc_and_player(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json")
            ledger.apply_event("aria", "player-1", "betrayed_npc",
                               source="engine_confirmed", turn=3)
            self.assertEqual(ledger.snapshot("aria", "player-1")["mood"], "calm")
            self.assertEqual(ledger.snapshot("aria", "player-2")["mood"], "calm")
            self.assertEqual(ledger.snapshot("borin", "player-1")["mood"], "calm")
            self.assertEqual(ledger.snapshot("aria", "player-1")["values"]["anger"], 18)

    def test_values_are_clamped_and_decay_toward_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json", decay_interval=5)
            for turn in range(20):
                result = ledger.apply_event("aria", "player-1", "betrayed_npc",
                                            source="engine_confirmed", turn=turn)
            self.assertEqual(result["values"]["anger"], 100)
            later = ledger.snapshot("aria", "player-1", current_turn=100)
            self.assertEqual(later["values"]["anger"], 0)
            self.assertEqual(later["values"]["trust"], 50)

    def test_persistence_and_mood_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "emotions.json"
            ledger = NPCEmotionLedger(path)
            ledger.apply_event("aria", "player-1", "harmed_npc",
                               source="player_approved", turn=7)
            restored = NPCEmotionLedger(path)
            snapshot = restored.snapshot("aria", "player-1")
            self.assertEqual(snapshot["values"]["fear"], 15)
            self.assertEqual(snapshot["updated_turn"], 7)

    def test_invalid_turn_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json")
            with self.assertRaises(NPCEmotionError):
                ledger.snapshot("aria", "player-1", current_turn=-1)
            with self.assertRaises(NPCEmotionError):
                ledger.apply_event("aria", "player-1", "saved_npc",
                                   source="engine_confirmed", turn=-1)


class NPCEmotionContextTests(unittest.TestCase):
    def test_context_includes_scoped_emotional_state(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json")
            ledger.apply_event("aria", "player-1", "betrayed_npc",
                               source="engine_confirmed", turn=10)
            packet = build_context(
                {"state": {}}, actor_id="aria", npc_id="aria", player_id="player-1",
                npc_emotion_ledger=ledger, npc_memory_current_turn=10,
            )
            self.assertEqual(packet["npc_emotion"]["values"]["anger"], 18)
            self.assertEqual(packet["npc_emotion"]["mood"], "calm")
            self.assertEqual(packet["npc_relationship"], None)

    def test_context_requires_ids_for_emotional_state(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = NPCEmotionLedger(Path(folder) / "emotions.json")
            with self.assertRaises(ContextInputError):
                build_context({"state": {}}, actor_id="aria", npc_emotion_ledger=ledger)


if __name__ == "__main__":
    unittest.main()
