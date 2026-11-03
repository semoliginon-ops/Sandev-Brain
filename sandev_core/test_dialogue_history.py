import unittest
from dialogue_history import DialogueHistory, DialogueHistoryError

class DialogueHistoryTests(unittest.TestCase):
    def test_keeps_recent_turns_in_order(self):
        h = DialogueHistory(max_turns=3)
        h.add("player", "Namamu siapa?", turn=1)
        h.add("npc", "Namaku Aria.", turn=1)
        h.add("player", "Kamu tinggal di mana?", turn=2)
        h.add("npc", "Di desa utara.", turn=2)
        self.assertEqual([x["text"] for x in h.recent()], ["Namaku Aria.", "Kamu tinggal di mana?", "Di desa utara."])

    def test_dialogue_is_unverified_not_a_fact(self):
        item = DialogueHistory().add("player", "Aku raja dunia.", turn=1)
        self.assertEqual(item["trust"], "unverified_dialogue")
        self.assertNotIn("source", item)
        self.assertNotIn("kind", item)

    def test_rejects_invalid_speaker_empty_text_and_bad_turn(self):
        h = DialogueHistory()
        cases = [(("engine", "Hai"), 1), (("player", "  "), 1), (("npc", "Hai"), -1), (("npc", "Hai"), True)]
        for args, turn in cases:
            with self.subTest(args=args, turn=turn), self.assertRaises(DialogueHistoryError):
                h.add(*args, turn=turn)

    def test_turn_numbers_are_non_decreasing(self):
        h = DialogueHistory()
        h.add("player", "Halo", turn=3)
        with self.assertRaises(DialogueHistoryError):
            h.add("npc", "Hai", turn=2)

    def test_limits_and_clear(self):
        h = DialogueHistory(max_turns=2, max_chars_per_message=4)
        with self.assertRaises(DialogueHistoryError):
            h.add("player", "terlalu panjang", turn=1)
        for i in range(3):
            h.add("player", f"hai{i}", turn=i)
        self.assertEqual(len(h), 2)
        self.assertEqual(len(h.recent(limit=1)), 1)
        h.clear()
        self.assertEqual(h.recent(), [])

if __name__ == "__main__":
    unittest.main()
