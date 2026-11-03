import unittest
from response_composer import compose_fact_response

class ResponseComposerTests(unittest.TestCase):
    def test_trusted_fact_is_composed(self):
        fact = {"id": "f1", "entity_id": "npc_aria", "aspect": "family", "value": "Aria memiliki adik bernama Lio.", "source": "engine_confirmed"}
        result = compose_fact_response("npc_aria", "family", {"status": "found", "fact": fact})
        self.assertEqual(result["status"], "composed")
        self.assertEqual(result["text"], "Yang kutahu, Aria memiliki adik bernama Lio.")

    def test_untrusted_fact_is_not_composed(self):
        fact = {"id": "f1", "entity_id": "npc_aria", "aspect": "family", "value": "Unknown.", "source": "model_guess"}
        result = compose_fact_response("npc_aria", "family", {"status": "found", "fact": fact})
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["text"])

    def test_missing_fact_is_not_composed(self):
        result = compose_fact_response("npc_aria", "family", {"status": "not_found", "fact": None})
        self.assertEqual(result["status"], "abstained")

if __name__ == "__main__":
    unittest.main()
