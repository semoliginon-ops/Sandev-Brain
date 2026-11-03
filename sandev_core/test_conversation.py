import unittest

from conversation import ConversationPipelineError, respond_to_context


def context(message, *, game_id="plane_shooter", needs=None, conversation_history=None):
    return {
        "context_version": "1.0",
        "game_id": game_id,
        "actor_id": "companion_1",
        "state_version": 3,
        "state": {},
        "needs": needs or {},
        "goals": [],
        "player_message": message,
        "player_message_status": "raw_uninterpreted_input",
        "recent_events": [],
        "conversation_history": conversation_history or [],
        "memories": [],
        "memory_tags_used": [],
    }


PATTERNS = [
    {"id": "hello_shooter", "intent": "greeting", "text": "Halo, pilot! Aku siap menemanimu.", "games": ["plane_shooter"], "priority": 2},
    {"id": "hello_general", "intent": "greeting", "text": "Halo! Senang bertemu denganmu.", "priority": 1},
    {"id": "thanks", "intent": "thanks", "text": "Sama-sama! Kita hadapi misi ini bersama.", "games": ["plane_shooter"]},
    {"id": "banter", "intent": "banter", "text": "Siap! Aku punya satu lelucon.", "forbidden_needs": ["health"]},
]


class ConversationPipelineTests(unittest.TestCase):
    def test_connects_message_to_contextual_response(self):
        result = respond_to_context(context("Halo!"), PATTERNS)
        self.assertEqual(result["status"], "response_selected")
        self.assertEqual(result["interpretation"]["intent"], "greeting")
        self.assertEqual(result["response"]["id"], "hello_shooter")
        self.assertEqual(result["text"], "Halo, pilot! Aku siap menemanimu.")

    def test_curated_reply_uses_npc_personality_profile(self):
        result = respond_to_context(context("Halo!"), PATTERNS, npc_personality="friendly")
        self.assertEqual(result["status"], "response_selected")
        self.assertEqual(result["text"], "Dengan senang hati, Halo, pilot! Aku siap menemanimu.")

    def test_unknown_message_does_not_guess_or_reply(self):
        result = respond_to_context(context("ceritakan tentang bintang yang jauh"), PATTERNS)
        self.assertEqual(result["status"], "no_response")
        self.assertIsNone(result["text"])
        self.assertEqual(result["interpretation"]["intent"], "unknown")

    def test_ambiguous_message_does_not_reply(self):
        result = respond_to_context(context("Awas, lindungi aku!"), PATTERNS)
        self.assertEqual(result["status"], "no_response")
        self.assertEqual(result["interpretation"]["status"], "ambiguous")

    def test_urgent_need_filters_inappropriate_banter(self):
        result = respond_to_context(context("lucu dong", needs={"health": 95}), PATTERNS)
        self.assertEqual(result["status"], "no_response")
        self.assertEqual(result["reason"], "no_curated_response_for_intent_and_context")

    def test_invalid_context_fails_closed(self):
        with self.assertRaises(ConversationPipelineError):
            respond_to_context({"player_message": "hai"}, PATTERNS)


    def test_follow_up_resolution_is_attached_without_inventing_response(self):
        history = [{"speaker": "npc", "text": "Aku bertemu Aria di desa.", "turn": 1}]
        catalog = [{"id": "npc_aria", "name": "Aria", "aliases": [], "source": "engine_confirmed"}]
        result = respond_to_context(context("Dia siapa?", conversation_history=history), PATTERNS, reference_catalog=catalog)
        self.assertEqual(result["follow_up"]["status"], "resolved")
        self.assertEqual(result["follow_up"]["reference_id"], "npc_aria")
        self.assertEqual(result["status"], "no_response")
        self.assertIsNone(result["text"])

    def test_follow_up_retrieves_only_trusted_entity_fact(self):
        history = [{"speaker": "npc", "text": "Aku bertemu Aria di desa.", "turn": 1}]
        catalog = [{"id": "npc_aria", "name": "Aria", "aliases": [], "source": "engine_confirmed"}]
        facts = [
            {"id": "aria_family", "entity_id": "npc_aria", "aspect": "family",
             "value": "Memiliki adik bernama Lio.", "source": "engine_confirmed"},
            {"id": "guess", "entity_id": "npc_aria", "aspect": "family",
             "value": "Putri kerajaan.", "source": "model_guess"},
        ]
        result = respond_to_context(
            context("Bagaimana dengan keluarganya?", conversation_history=history),
            PATTERNS, reference_catalog=catalog, entity_facts=facts,
        )
        self.assertEqual(result["follow_up"]["reference_id"], "npc_aria")
        self.assertEqual(result["fact_lookup"]["status"], "found")
        self.assertEqual(result["fact_lookup"]["fact"]["id"], "aria_family")
        self.assertEqual(result["status"], "fact_response_selected")
        self.assertEqual(result["text"], "Yang kutahu, Memiliki adik bernama Lio.")
        self.assertEqual(result["fact_response"]["status"], "composed")

    def test_follow_up_fact_lookup_abstains_for_missing_fact(self):
        history = [{"speaker": "npc", "text": "Aku bertemu Aria.", "turn": 1}]
        catalog = [{"id": "npc_aria", "name": "Aria", "aliases": [], "source": "engine_confirmed"}]
        result = respond_to_context(
            context("Bagaimana dengan keluarganya?", conversation_history=history),
            PATTERNS, reference_catalog=catalog,
        )
        self.assertEqual(result["fact_lookup"]["status"], "not_found")
        self.assertIsNone(result["fact_lookup"]["fact"])
        self.assertEqual(result["fact_response"]["status"], "abstained")
        self.assertIsNone(result["text"])

    def test_follow_up_does_not_resolve_untrusted_catalog_reference(self):
        history = [{"speaker": "npc", "text": "Raja Bayangan muncul.", "turn": 1}]
        catalog = [{"id": "npc_shadow", "name": "Raja Bayangan", "aliases": [], "source": "model_guess"}]
        result = respond_to_context(context("Dia siapa?", conversation_history=history), PATTERNS, reference_catalog=catalog)
        self.assertEqual(result["follow_up"]["status"], "unresolved")
        self.assertEqual(result["status"], "no_response")

    def test_curated_dialogue_uses_emotional_delivery_cue(self):
        ctx = context("Halo!")
        ctx["npc_emotion"] = {
            "values": {"joy": 50, "fear": 0, "anger": 75,
                       "sadness": 0, "trust": 20, "suspicion": 0},
            "mood": "happy",
        }
        result = respond_to_context(ctx, PATTERNS)
        self.assertEqual(result["status"], "response_selected")
        self.assertEqual(result["response"]["mood"], "angry")
        self.assertEqual(result["text"],
                         "*menjawab dengan nada marah* Halo, pilot! Aku siap menemanimu.")

    def test_fact_follow_up_uses_emotional_delivery_cue(self):
        history = [{"speaker": "npc", "text": "Aku bertemu Aria di desa.", "turn": 1}]
        catalog = [{"id": "npc_aria", "name": "Aria", "aliases": [], "source": "engine_confirmed"}]
        facts = [{"id": "aria_family", "entity_id": "npc_aria", "aspect": "family",
                  "value": "Memiliki adik bernama Lio.", "source": "engine_confirmed"}]
        ctx = context("Bagaimana dengan keluarganya?", conversation_history=history)
        ctx["npc_emotion"] = {
            "values": {"joy": 50, "fear": 0, "anger": 0,
                       "sadness": 70, "trust": 50, "suspicion": 0},
            "mood": "calm",
        }
        result = respond_to_context(ctx, PATTERNS, reference_catalog=catalog, entity_facts=facts)
        self.assertEqual(result["status"], "fact_response_selected")
        self.assertEqual(result["fact_response"]["mood"], "sad")
        self.assertEqual(result["text"],
                         "*menunduk sedih* Yang kutahu, Memiliki adik bernama Lio.")

if __name__ == "__main__":
    unittest.main()
