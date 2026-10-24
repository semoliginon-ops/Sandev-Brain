import unittest
from threading import Event, Thread

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

    def test_execute_pending_requires_host_confirmation(self):
        proposal = self.handle("Serang Goblin", version="v3")
        calls = []

        def engine(payload, expected_version):
            calls.append((payload, expected_version))
            return {"confirmed": True, "result": {"damage": 12}}

        result = self.session.execute_pending(
            "player-1",
            proposal["action_id"],
            get_current_state_version=lambda: "v3",
            engine_execute_if_version_matches=engine,
        )
        self.assertTrue(result["accepted"])
        self.assertTrue(result["execution_confirmed"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(calls[0][1], "v3")
        self.assertEqual(self.registry.get(proposal["action_id"], "player-1")["status"], "completed")

    def test_execute_pending_rejects_stale_version_without_calling_engine(self):
        proposal = self.handle("Serang Goblin", version="v3")
        calls = []
        result = self.session.execute_pending(
            "player-1",
            proposal["action_id"],
            get_current_state_version=lambda: "v4",
            engine_execute_if_version_matches=lambda payload, version: calls.append(True) or {"confirmed": True},
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["execution_confirmed"])
        self.assertEqual(calls, [])

    def test_execute_pending_does_not_claim_success_without_confirmation(self):
        proposal = self.handle("Serang Goblin", version="v3")
        result = self.session.execute_pending(
            "player-1",
            proposal["action_id"],
            get_current_state_version=lambda: "v3",
            engine_execute_if_version_matches=lambda payload, version: {"confirmed": False, "result": {}},
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["execution_confirmed"])
        self.assertEqual(self.registry.get(proposal["action_id"], "player-1")["status"], "failed")

    def test_execute_pending_marks_host_exception_as_failed(self):
        proposal = self.handle("Serang Goblin", version="v3")

        def engine(payload, version):
            raise RuntimeError("engine unavailable")

        result = self.session.execute_pending(
            "player-1",
            proposal["action_id"],
            get_current_state_version=lambda: "v3",
            engine_execute_if_version_matches=engine,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["execution_confirmed"])
        self.assertEqual(self.registry.get(proposal["action_id"], "player-1")["status"], "failed")

    def test_state_version_lookup_error_cancels_proposal_without_engine_call(self):
        proposal = self.handle("Serang Goblin", version="v3")
        calls = []

        def broken_version():
            raise RuntimeError("state snapshot unavailable")

        result = self.session.execute_pending(
            "player-1",
            proposal["action_id"],
            get_current_state_version=broken_version,
            engine_execute_if_version_matches=lambda payload, version: calls.append(True) or {"confirmed": True},
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["execution_confirmed"])
        self.assertEqual(result["reason"], "current_state_version_unavailable")
        self.assertEqual(calls, [])
        self.assertEqual(self.registry.get(proposal["action_id"], "player-1")["status"], "cancelled")

    def test_new_message_waits_until_execution_boundary_finishes(self):
        proposal = self.handle("Serang Goblin", version="v3")
        engine_entered = Event()
        release_engine = Event()
        cancel_finished = Event()
        execution_result = []
        cancel_result = []

        def engine(payload, expected_version):
            engine_entered.set()
            if not release_engine.wait(timeout=3):
                raise TimeoutError("test did not release engine callback")
            return {"confirmed": True, "result": {"damage": 5}}

        def execute():
            execution_result.append(self.session.execute_pending(
                "player-1",
                proposal["action_id"],
                get_current_state_version=lambda: "v3",
                engine_execute_if_version_matches=engine,
            ))

        def cancel():
            cancel_result.append(self.handle("Batal"))
            cancel_finished.set()

        execution_thread = Thread(target=execute)
        execution_thread.start()
        self.assertTrue(engine_entered.wait(timeout=2), "engine callback was not entered")
        cancel_thread = Thread(target=cancel)
        cancel_thread.start()
        try:
            self.assertFalse(cancel_finished.wait(timeout=0.1), "message handling should wait on the session lock")
        finally:
            release_engine.set()
            execution_thread.join(timeout=3)
            cancel_thread.join(timeout=3)

        self.assertFalse(execution_thread.is_alive(), "execution thread did not finish")
        self.assertFalse(cancel_thread.is_alive(), "message thread did not finish")
        self.assertTrue(execution_result[0]["execution_confirmed"])
        self.assertEqual(self.registry.get(proposal["action_id"], "player-1")["status"], "completed")
        self.assertEqual(cancel_result[0]["status"], "cancelled")
        self.assertNotIn(proposal["action_id"], cancel_result[0]["cancelled_action_ids"])

    def test_state_version_is_stored_for_execution_gate(self):
        result = self.handle("Serang Goblin", version="world-7")
        authorization = self.registry.authorize_execution(
            result["action_id"], "player-1", current_state_version="world-8", now=101.0
        )
        self.assertFalse(authorization["authorized"])
        self.assertEqual(authorization["reason"], "state_version_changed")


    def test_cancel_wins_before_execution_and_engine_is_never_called(self):
        proposal = self.handle("Serang Goblin", version="v5")
        cancelled = self.handle("Batal", version="v5")
        self.assertIn(proposal["action_id"], cancelled["cancelled_action_ids"])
        calls = []
        result = self.session.execute_pending(
            "player-1",
            proposal["action_id"],
            get_current_state_version=lambda: "v5",
            engine_execute_if_version_matches=lambda payload, version: calls.append(True)
            or {"confirmed": True, "result": {}},
        )
        self.assertFalse(result["accepted"])
        self.assertFalse(result["execution_confirmed"])
        self.assertEqual(calls, [])
        self.assertEqual(
            self.registry.get(proposal["action_id"], "player-1")["status"],
            "cancelled",
        )

    def test_two_concurrent_execute_attempts_reach_engine_only_once(self):
        proposal = self.handle("Serang Goblin", version="v6")
        engine_entered = Event()
        release_engine = Event()
        results = []
        calls = []

        def engine(payload, expected_version):
            calls.append(expected_version)
            engine_entered.set()
            if not release_engine.wait(timeout=3):
                raise TimeoutError("test did not release engine callback")
            return {"confirmed": True, "result": {"damage": 7}}

        def execute():
            results.append(self.session.execute_pending(
                "player-1",
                proposal["action_id"],
                get_current_state_version=lambda: "v6",
                engine_execute_if_version_matches=engine,
            ))

        first = Thread(target=execute)
        second = Thread(target=execute)
        first.start()
        self.assertTrue(engine_entered.wait(timeout=2), "engine callback was not entered")
        second.start()
        try:
            self.assertEqual(len(calls), 1, "second attempt must wait behind the session lock")
        finally:
            release_engine.set()
            first.join(timeout=3)
            second.join(timeout=3)

        self.assertFalse(first.is_alive(), "first execution thread did not finish")
        self.assertFalse(second.is_alive(), "second execution thread did not finish")
        self.assertEqual(len(calls), 1, "the engine must receive at most one execution call")
        self.assertEqual(sum(bool(item["execution_confirmed"]) for item in results), 1)
        self.assertEqual(sum(bool(item["accepted"]) for item in results), 1)
        self.assertEqual(self.registry.get(proposal["action_id"], "player-1")["status"], "completed")


if __name__ == "__main__":
    unittest.main()
