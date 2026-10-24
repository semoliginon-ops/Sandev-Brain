import unittest

from pending_actions import PendingActionRegistry
from pending_command_session import PendingCommandSession


ENTITIES = [
    {"id": "enemy-1", "name": "Goblin", "aliases": ["goblin"]},
    {"id": "enemy-2", "name": "Bandit", "aliases": ["bandit"]},
]


class PendingCommandSessionTests(unittest.TestCase):
    def setUp(self):
        self.registry = PendingActionRegistry(clock=lambda: 100.0)
        self.session = PendingCommandSession(self.registry, ttl_seconds=20)
        self.context = {"game_id": "rpg"}

    def handle(self, message, version="v1", session_id="player-1"):
        return self.session.handle_message(
            session_id,
            message,
            ENTITIES,
            state_version=version,
            context=self.context,
        )

    def test_valid_command_is_registered_as_pending_not_executed(self):
        result = self.handle("Serang Goblin")
        self.assertEqual(result["status"], "pending")
        self.assertFalse(result["execution_allowed"])
        record = self.registry.get(result["action_id"], "player-1")
        self.assertEqual(record["status"], "pending")
        self.assertEqual(record["payload"]["target"]["entity_id"], "enemy-1")

    def test_new_message_invalidates_old_pending_action_before_new_proposal(self):
        old = self.handle("Serang Goblin")
        new = self.handle("Serang Bandit", version="v2")
        self.assertIn(old["action_id"], new["invalidated_action_ids"])
        self.assertEqual(self.registry.get(old["action_id"], "player-1")["status"], "cancelled")
        self.assertEqual(new["status"], "pending")
        self.assertEqual(
            self.registry.get(new["action_id"], "player-1")["payload"]["target"]["entity_id"],
            "enemy-2",
        )

    def test_explicit_cancel_message_cancels_pending_without_creating_new_action(self):
        old = self.handle("Serang Goblin")
        result = self.handle("Batal")
        self.assertEqual(result["status"], "cancelled")
        self.assertIn(old["action_id"], result["cancelled_action_ids"])
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(self.registry.get(old["action_id"], "player-1")["status"], "cancelled")

    def test_negation_message_cannot_leave_old_proposal_pending(self):
        old = self.handle("Serang Goblin")
        result = self.handle("Jangan serang Goblin")
        self.assertNotEqual(result["status"], "pending")
        self.assertIn(old["action_id"], result["invalidated_action_ids"])
        self.assertEqual(self.registry.get(old["action_id"], "player-1")["status"], "cancelled")

    def test_cancel_command_is_case_insensitive_and_accepts_polite_prefix(self):
        old = self.handle("Serang Goblin")
        result = self.handle("Tolong batalkan perintah sebelumnya")
        self.assertEqual(result["status"], "cancelled")
        self.assertIn(old["action_id"], result["cancelled_action_ids"])

    def test_jangan_lupa_is_not_misclassified_as_explicit_cancellation(self):
        old = self.handle("Serang Goblin")
        result = self.handle("Jangan lupa serang Goblin")
        self.assertNotEqual(result["status"], "cancelled")
        self.assertIn(old["action_id"], result["invalidated_action_ids"])
        self.assertEqual(self.registry.get(old["action_id"], "player-1")["status"], "cancelled")

    def test_non_action_chat_also_invalidates_old_pending_proposal(self):
        old = self.handle("Serang Goblin")
        result = self.handle("Halo, apa kabar?")
        self.assertEqual(result["status"], "not_a_confident_action")
        self.assertIn(old["action_id"], result["invalidated_action_ids"])
        self.assertEqual(self.registry.get(old["action_id"], "player-1")["status"], "cancelled")

    def test_ambiguous_target_is_not_registered(self):
        result = self.handle("Serang Goblin dan Bandit")
        self.assertEqual(result["status"], "ambiguous_target")
        self.assertIsNone(result.get("action_id"))

    def test_sessions_are_isolated(self):
        one = self.handle("Serang Goblin", session_id="player-1")
        two = self.handle("Serang Bandit", session_id="player-2")
        self.handle("Batal", session_id="player-2")
        self.assertEqual(self.registry.get(one["action_id"], "player-1")["status"], "pending")
        self.assertEqual(self.registry.get(two["action_id"], "player-2")["status"], "cancelled")

    def test_state_version_is_stored_for_execution_gate(self):
        result = self.handle("Serang Goblin", version="world-7")
        authorization = self.registry.authorize_execution(
            result["action_id"], "player-1", current_state_version="world-8", now=101.0
        )
        self.assertFalse(authorization["authorized"])
        self.assertEqual(authorization["reason"], "state_version_changed")


if __name__ == "__main__":
    unittest.main()
