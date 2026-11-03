import unittest

from npc_routine import NPCRoutineError, propose_routine


def entry(activity, start=480, end=600, **extra):
    return {
        "activity_id": activity, "start_minute": start, "end_minute": end,
        "source": "engine_confirmed", "npc_id": "aria", **extra,
    }


class NPCRoutineTests(unittest.TestCase):
    def context(self, **overrides):
        data = {
            "npc_id": "aria", "current_minute": 510, "day_of_week": 1,
            "state": {"rain": False, "has_work": True},
            "routines": [entry("work")],
        }
        data.update(overrides)
        return data

    def test_selects_active_routine_inside_inclusive_exclusive_window(self):
        result = propose_routine(self.context(), allowed_activities=["work"])
        self.assertEqual(result["proposal"]["activity_id"], "work")
        self.assertEqual(result["execution"], "not_performed")

    def test_time_window_start_included_end_excluded(self):
        self.assertEqual(propose_routine(self.context(current_minute=480), allowed_activities=["work"])["status"], "proposed")
        self.assertEqual(propose_routine(self.context(current_minute=600), allowed_activities=["work"])["status"], "abstained")

    def test_day_filter_and_conditions_use_explicit_state(self):
        routine = entry("market", days=[5], conditions={"rain": False})
        self.assertEqual(propose_routine(self.context(routines=[routine]), allowed_activities=["market"])["status"], "abstained")
        self.assertEqual(propose_routine(self.context(day_of_week=5, routines=[routine]), allowed_activities=["market"])["proposal"]["activity_id"], "market")

    def test_priority_then_narrow_window_breaks_overlap(self):
        routines = [entry("work", priority=50), entry("urgent", 500, 520, priority=80)]
        result = propose_routine(self.context(routines=routines), allowed_activities=["work", "urgent"])
        self.assertEqual(result["proposal"]["activity_id"], "urgent")

    def test_ties_are_deterministic(self):
        result = propose_routine(self.context(routines=[entry("zeta"), entry("alpha")]), allowed_activities=["zeta", "alpha"])
        self.assertEqual(result["proposal"]["activity_id"], "alpha")

    def test_untrusted_wrong_scope_inactive_and_disallowed_are_ignored(self):
        untrusted = entry("steal", priority=100, source="model_guess")
        wrong_scope = entry("fight", priority=100, npc_id="borin")
        inactive = entry("sleep", priority=100, active=False)
        result = propose_routine(self.context(routines=[untrusted, wrong_scope, inactive, entry("work")]), allowed_activities=["work", "sleep", "fight", "steal"])
        self.assertEqual(result["proposal"]["activity_id"], "work")

    def test_no_eligible_routine_abstains(self):
        result = propose_routine(self.context(routines=[]), allowed_activities=["work"])
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["proposal"])

    def test_invalid_time_priority_and_conditions_rejected(self):
        with self.assertRaisesRegex(NPCRoutineError, "time window"):
            propose_routine(self.context(routines=[entry("bad", 700, 600)]), allowed_activities=["bad"])
        with self.assertRaisesRegex(NPCRoutineError, "priority"):
            propose_routine(self.context(routines=[entry("bad", priority=101)]), allowed_activities=["bad"])
        with self.assertRaisesRegex(NPCRoutineError, "conditions"):
            propose_routine(self.context(routines=[entry("bad", conditions={"rain": []})]), allowed_activities=["bad"])

    def test_world_conditions_react_to_weather_and_location(self):
        routine = entry("shelter", world_conditions={"weather": "rain", "location": "market"})
        result = propose_routine(self.context(routines=[routine], world={"weather": "rain", "location": "market"}), allowed_activities=["shelter"])
        self.assertEqual(result["proposal"]["activity_id"], "shelter")
        mismatch = propose_routine(self.context(routines=[routine], world={"weather": "clear", "location": "market"}), allowed_activities=["shelter"])
        self.assertEqual(mismatch["status"], "abstained")

    def test_nearby_entities_can_enable_or_block_routine(self):
        routine = entry("trade", requires_nearby=["merchant-1"])
        result = propose_routine(self.context(routines=[routine], nearby_entity_ids=["merchant-1"]), allowed_activities=["trade"])
        self.assertEqual(result["proposal"]["activity_id"], "trade")
        blocked = propose_routine(self.context(routines=[entry("hide", forbids_nearby=["guard-1"])], nearby_entity_ids=["guard-1"]), allowed_activities=["hide"])
        self.assertEqual(blocked["status"], "abstained")

    def test_world_and_nearby_facts_are_not_inferred(self):
        routine = entry("trade", world_conditions={"weather": "clear"}, requires_nearby=["merchant-1"])
        result = propose_routine(self.context(routines=[routine], world={}, nearby_entity_ids=[]), allowed_activities=["trade"])
        self.assertEqual(result["status"], "abstained")

    def test_invalid_world_conditions_and_nearby_ids_rejected(self):
        with self.assertRaisesRegex(NPCRoutineError, "world_conditions"):
            propose_routine(self.context(routines=[entry("bad", world_conditions={"weather": []})]), allowed_activities=["bad"])
        with self.assertRaisesRegex(NPCRoutineError, "nearby_entity_ids"):
            propose_routine(self.context(nearby_entity_ids=[""]), allowed_activities=["work"])

    def test_invalid_context_rejected(self):
        with self.assertRaisesRegex(NPCRoutineError, "current_minute"):
            propose_routine(self.context(current_minute=1440), allowed_activities=["work"])
        with self.assertRaisesRegex(NPCRoutineError, "day_of_week"):
            propose_routine(self.context(day_of_week=7), allowed_activities=["work"])


if __name__ == "__main__":
    unittest.main()
