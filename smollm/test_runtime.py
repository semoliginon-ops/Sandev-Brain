import json
import tempfile
import unittest
from pathlib import Path
from sandev_brain import MemoryStore, validate_response

class RuntimeTests(unittest.TestCase):
    def test_valid_response(self):
        raw = json.dumps({"say":"Hai!", "action":{"type":"talk","target":"Joni"}, "memory_update":{"event":"Bertemu Joni","importance":2}}, ensure_ascii=False)
        result = validate_response(raw, ["talk", "move"])
        self.assertEqual(result["action"]["type"], "talk")
        self.assertEqual(result["memory_update"]["event"], "Bertemu Joni")

    def test_unknown_action_is_rejected(self):
        raw = '{"say":"Oke","action":{"type":"hack_world","target":""},"memory_update":{"event":"","importance":0}}'
        self.assertIsNone(validate_response(raw, ["talk", "move"])["action"])

    def test_invalid_json_fails_closed(self):
        with self.assertRaises(ValueError): validate_response("not json", ["talk"])

    def test_code_fence_is_accepted(self):
        fence = chr(96) * 3
        raw = fence + 'json\n{"say":"Halo","action":null,"memory_update":{"event":"","importance":0}}\n' + fence
        self.assertEqual(validate_response(raw, ["talk"])["say"], "Halo")

    def test_memory_persists_confirmed_events(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            MemoryStore(path).add_confirmed_event("Joni memberi hadiah", importance=3, turn=8)
            loaded = MemoryStore(path)
            self.assertEqual(loaded.relevant()[0]["event"], "Joni memberi hadiah")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))[0]["turn"], 8)

if __name__ == "__main__": unittest.main()
