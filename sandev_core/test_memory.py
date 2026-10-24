import tempfile
import unittest
from pathlib import Path
from memory import MemoryLedger

class MemoryLedgerTests(unittest.TestCase):
    def test_rejects_unverified_source(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = MemoryLedger(Path(folder) / 'memory.json')
            with self.assertRaises(ValueError):
                ledger.record_event('event', source='teacher_model', turn=1)
            self.assertEqual(ledger.export(), [])

    def test_persists_and_filters_by_tag(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memory.json'
            ledger = MemoryLedger(path)
            ledger.record_event('Player helped Joni', source='engine_confirmed', turn=4, tags=['bond'], importance=2)
            ledger.record_event('Rain started', source='engine_confirmed', turn=5, tags=['weather'], importance=1)
            loaded = MemoryLedger(path)
            found = loaded.retrieve(tags=['bond'])
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]['event'], 'Player helped Joni')

    def test_verified_fact_replaces_old_value(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = MemoryLedger(Path(folder) / 'memory.json')
            ledger.remember_fact('drink', 'coffee', source='player_approved', turn=1)
            ledger.remember_fact('drink', 'tea', source='player_approved', turn=2)
            facts = [item for item in ledger.export() if item.get('key') == 'drink']
            self.assertEqual(len(facts), 1)
            self.assertEqual(facts[0]['value'], 'tea')

    def test_limit_is_enforced(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = MemoryLedger(Path(folder) / 'memory.json', max_items=2)
            for turn in range(4):
                ledger.record_event(f'event {turn}', source='engine_confirmed', turn=turn)
            self.assertEqual(len(ledger.export()), 2)
            self.assertEqual(ledger.export()[0]['event'], 'event 2')

if __name__ == '__main__':
    unittest.main()
