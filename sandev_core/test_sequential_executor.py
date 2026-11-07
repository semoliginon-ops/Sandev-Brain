import unittest

from planner import plan_player_command
from sequential_executor import SequentialActionExecutor, SequentialExecutionError


ENTITIES = [
    {"id": "enemy-1", "name": "Goblin", "aliases": ["goblin"]},
    {"id": "enemy-2", "name": "Bandit", "aliases": ["bandit"]},
]


class SequentialActionExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor = SequentialActionExecutor(max_steps=5)
        self.snapshot = {
            "state_version": 1,
            "entities": [dict(item) for item in ENTITIES],
            "context": {"game_id": "rpg"},
        }

    def make_plan(self, message="Serang Goblin lalu serang Bandit"):
        return plan_player_command(
            message, self.snapshot["entities"],
            context={"game_id": "rpg", "state_version": self.snapshot["state_version"]},
        )

    def test_executes_steps_sequentially_using_fresh_versions(self):
        plan = self.make_plan()
        calls = []

        def engine(proposal, snapshot, expected_version):
            calls.append((proposal["target"]["entity_id"], expected_version))
            self.snapshot["state_version"] += 1
            return {"confirmed": True, "result": {"damage": 10}}

        result = self.executor.execute(
            plan,
            get_snapshot=lambda: self.snapshot,
            execute_step=engine,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(calls, [("enemy-1", 1), ("enemy-2", 2)])
        self.assertEqual(result["completed_step_count"], 2)

    def test_stops_when_later_target_disappears(self):
        plan = self.make_plan()
        calls = []

        def engine(proposal, snapshot, expected_version):
            calls.append(proposal["target"]["entity_id"])
            self.snapshot["state_version"] += 1
            self.snapshot["entities"] = [
                item for item in self.snapshot["entities"] if item["id"] != "enemy-2"
            ]
            return {"confirmed": True, "result": {"damage": 10}}

        result = self.executor.execute(
            plan, get_snapshot=lambda: self.snapshot, execute_step=engine,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["reason"], "step_no_longer_resolves_in_current_snapshot")
        self.assertEqual(calls, ["enemy-1"])
        self.assertEqual(len(result["completed_steps"]), 1)

    def test_stops_immediately_when_engine_does_not_confirm(self):
        plan = self.make_plan()
        calls = []

        def engine(proposal, snapshot, expected_version):
            calls.append(expected_version)
            return {"confirmed": False, "result": {}}

        result = self.executor.execute(
            plan, get_snapshot=lambda: self.snapshot, execute_step=engine,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "engine_did_not_confirm_step")
        self.assertEqual(calls, [1])
        self.assertEqual(result["completed_steps"], [])

    def test_does_not_call_engine_if_snapshot_is_invalid(self):
        plan = self.make_plan()
        calls = []
        result = self.executor.execute(
            plan,
            get_snapshot=lambda: {"entities": ENTITIES},
            execute_step=lambda *args: calls.append(True) or {"confirmed": True},
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "snapshot_or_engine_callback_failed")
        self.assertEqual(calls, [])

    def test_rejects_malformed_or_executable_plan(self):
        with self.assertRaises(SequentialExecutionError):
            self.executor.execute(
                {"status": "plan_proposal", "execution_allowed": True, "steps": []},
                get_snapshot=lambda: self.snapshot,
                execute_step=lambda *args: {"confirmed": True},
            )

    def test_rejects_plan_over_configured_step_limit(self):
        plan = self.make_plan()
        plan["steps"] = plan["steps"] * 3
        plan["steps"] = [
            {**step, "index": index}
            for index, step in enumerate(plan["steps"], start=1)
        ]
        with self.assertRaises(SequentialExecutionError):
            self.executor.execute(
                plan, get_snapshot=lambda: self.snapshot,
                execute_step=lambda *args: {"confirmed": True},
            )

    def test_stops_when_engine_callback_raises(self):
        plan = self.make_plan()

        def broken_engine(*args):
            raise RuntimeError("engine offline")

        result = self.executor.execute(
            plan, get_snapshot=lambda: self.snapshot, execute_step=broken_engine,
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "snapshot_or_engine_callback_failed")
        self.assertEqual(result["error_type"], "RuntimeError")


    def test_executor_can_gate_each_step_through_engine_bridge(self):
        from engine_bridge import resolve_language_proposal
        plan = self.make_plan()
        self.snapshot["candidates"] = [
            {"action_id": "attack-enemy-1", "kind": "attack", "target": "enemy-1",
             "preconditions": {"combat.enabled": True}},
            {"action_id": "attack-enemy-2", "kind": "attack", "target": "enemy-2",
             "preconditions": {"combat.enabled": True}},
        ]
        self.snapshot["allowed_actions"] = ["attack"]
        self.snapshot["state"] = {"combat": {"enabled": True}}
        checked = []

        def engine(proposal, snapshot, expected_version):
            validation = resolve_language_proposal(
                snapshot, proposal, action_type_map={"tactical_attack": "attack"},
            )
            self.assertTrue(validation["accepted"])
            self.assertEqual(validation["state_version"], expected_version)
            checked.append(validation["action_id"])
            self.snapshot["state_version"] += 1
            return {"confirmed": True, "result": {"action_id": validation["action_id"]}}

        result = self.executor.execute(
            plan, get_snapshot=lambda: self.snapshot, execute_step=engine,
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(checked, ["attack-enemy-1", "attack-enemy-2"])


if __name__ == "__main__":
    unittest.main()
