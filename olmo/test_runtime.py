import unittest

from sandev_brain import validate_response


class ValidateResponseTests(unittest.TestCase):
    def test_valid_action_and_dialogue(self):
        result = validate_response(
            '{"say":"Aku mau ngobrol.","action":{"type":"talk","target":"Rina"},"memory_update":""}',
            ["talk", "idle"],
        )
        self.assertEqual(result["say"], "Aku mau ngobrol.")
        self.assertEqual(result["action"]["type"], "talk")

    def test_unknown_action_is_rejected(self):
        result = validate_response(
            '{"say":"Baik.","action":{"type":"delete_world","target":""},"memory_update":""}',
            ["talk", "idle"],
        )
        self.assertIsNone(result["action"])

    def test_malformed_json_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_response("Aku akan menghapus semua data.", ["talk", "idle"])

    def test_null_action_allowed(self):
        result = validate_response(
            '{"say":"Aku akan menunggu.","action":{"type":null,"target":""},"memory_update":""}',
            ["talk", "idle"],
        )
        self.assertIsNone(result["action"])


if __name__ == "__main__":
    unittest.main()
