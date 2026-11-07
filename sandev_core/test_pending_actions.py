import unittest

from pending_actions import PendingActionError, PendingActionRegistry


class PendingActionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.clock_value = 100.0
        self.registry = PendingActionRegistry(clock=lambda: self.clock_value)

    def submit(self, action_id="a1", *, session="session-1", version=7, ttl=30):
        return self.registry.submit(
            session, version, {"type": "attack", "target": "goblin"},
            action_id=action_id, ttl_seconds=ttl,
        )

    def test_submit_is_pending_and_never_claims_execution(self):
        record = self.submit()
        self.assertEqual(record["status"], "pending")
        self.assertEqual(record["state_version"], 7)
        self.assertNotIn("execution_confirmed", record)

    def test_cancelled_action_cannot_be_authorized_later(self):
        self.submit()
        result = self.registry.cancel("session-1", action_id="a1")
        self.assertTrue(result["cancelled"])
        gate = self.registry.authorize_execution("a1", "session-1", 7)
        self.assertFalse(gate["authorized"])
        self.assertEqual(gate["reason"], "action_not_pending")
        self.assertEqual(self.registry.get("a1", "session-1")["status"], "cancelled")

    def test_session_cancel_cancels_only_pending_actions_in_that_session(self):
        self.submit("a1", session="session-1")
        self.submit("b1", session="session-2")
        result = self.registry.cancel("session-1")
        self.assertEqual(result["action_ids"], ["a1"])
        self.assertEqual(self.registry.get("b1", "session-2")["status"], "pending")

    def test_expired_action_is_rejected(self):
        self.submit(ttl=5)
        self.clock_value = 105.0
        result = self.registry.authorize_execution("a1", "session-1", 7)
        self.assertFalse(result["authorized"])
        self.assertEqual(result["reason"], "pending_action_expired")
        self.assertEqual(self.registry.get("a1", "session-1")["status"], "expired")

    def test_changed_state_cancels_instead_of_authorizing(self):
        self.submit()
        result = self.registry.authorize_execution("a1", "session-1", 8)
        self.assertFalse(result["authorized"])
        self.assertEqual(result["reason"], "state_version_changed")
        self.assertEqual(self.registry.get("a1", "session-1")["status"], "cancelled")

    def test_authorization_is_not_execution_confirmation(self):
        self.submit()
        result = self.registry.authorize_execution("a1", "session-1", 7)
        self.assertTrue(result["authorized"])
        self.assertFalse(result["execution_confirmed"])
        self.assertIn("engine_must_execute_and_confirm", result["status"])
        self.assertNotIn("success", result)

    def test_only_authoritative_engine_confirmation_completes_action(self):
        self.submit()
        self.registry.authorize_execution("a1", "session-1", 7)
        unconfirmed = self.registry.record_engine_result(
            "a1", "session-1", engine_confirmed=False,
        )
        self.assertFalse(unconfirmed["execution_confirmed"])
        self.assertEqual(self.registry.get("a1", "session-1")["status"], "failed")

        self.submit("a2")
        self.registry.authorize_execution("a2", "session-1", 7)
        confirmed = self.registry.record_engine_result(
            "a2", "session-1", engine_confirmed=True,
            result={"outcome": "hit", "damage": 12},
        )
        self.assertTrue(confirmed["execution_confirmed"])
        self.assertEqual(self.registry.get("a2", "session-1")["status"], "completed")

    def test_duplicate_ids_and_invalid_ttl_are_rejected(self):
        self.submit()
        with self.assertRaises(PendingActionError):
            self.submit()
        with self.assertRaises(PendingActionError):
            self.registry.submit("session-1", 7, {}, ttl_seconds=0)

    def test_other_session_cannot_cancel_or_read_action(self):
        self.submit()
        result = self.registry.cancel("other-session", action_id="a1")
        self.assertFalse(result["cancelled"])
        self.assertIsNone(self.registry.get("a1", "other-session"))


if __name__ == "__main__":
    unittest.main()
