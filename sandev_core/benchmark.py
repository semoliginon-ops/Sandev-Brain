"""Small, versioned regression benchmark for the deterministic SANDEV Brain core.

Expected choices are hand-authored acceptance labels, not teacher-model outputs.
Passing means this rule baseline matches these scenarios only; it is not a
measure of general intelligence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from brain import ActionCandidate, choose_action


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    genre: str
    description: str
    state: dict[str, Any]
    needs: dict[str, Any]
    goals: tuple[dict[str, Any], ...]
    candidates: tuple[ActionCandidate, ...]
    allowed_actions: tuple[str, ...]
    expected_action_id: str | None


SCENARIOS = (
    Scenario(
        "life_hunger", "life_sim", "Critical hunger should outrank low-priority work.",
        {"inventory": {"food": 1}, "cash": 10}, {"hunger": 95, "energy": 10},
        ({"tag": "earn_money", "priority": 0.3},),
        (ActionCandidate("eat", "eat", tags=("hunger",), preconditions={"inventory.food": {"min": 1}}),
         ActionCandidate("work", "work", goal_tags=("earn_money",))),
        ("eat", "work", "rest"), "eat",
    ),
    Scenario(
        "life_no_food", "life_sim", "Do not select eating when no food is available.",
        {"inventory": {"food": 0}}, {"hunger": 90},
        (),
        (ActionCandidate("eat", "eat", tags=("hunger",), preconditions={"inventory.food": {"min": 1}}),
         ActionCandidate("buy_food", "buy_food", tags=("hunger",))),
        ("eat", "buy_food"), "buy_food",
    ),
    Scenario(
        "life_goal_saving", "life_sim", "When needs are low, prioritize the explicit savings goal.",
        {"cash": 20}, {"hunger": 10, "energy": 10},
        ({"tag": "save_money", "priority": 1.0},),
        (ActionCandidate("buy_snack", "buy", goal_tags=("fun",), cost=5),
         ActionCandidate("work_shift", "work", goal_tags=("save_money",))),
        ("buy", "work"), "work_shift",
    ),
    Scenario(
        "shooter_cover", "shooter", "High threat should favor cover over optional exploration.",
        {"threat_visible": True}, {"safety": 95},
        (),
        (ActionCandidate("cover", "take_cover", tags=("safety",)),
         ActionCandidate("explore", "explore", base_score=3)),
        ("take_cover", "explore"), "cover",
    ),
    Scenario(
        "shooter_no_reload", "shooter", "A full magazine makes reload infeasible.",
        {"weapon": {"ammo": 30, "capacity": 30}}, {"safety": 70},
        (),
        (ActionCandidate("reload", "reload", tags=("safety",), preconditions={"weapon.ammo": {"max": 0}}),
         ActionCandidate("cover", "take_cover", tags=("safety",))),
        ("reload", "take_cover"), "cover",
    ),
    Scenario(
        "rpg_heal", "rpg", "Critical health should prioritize a valid healing item.",
        {"inventory": {"potion": 1}}, {"health": 100},
        (),
        (ActionCandidate("heal", "use_potion", tags=("health",), preconditions={"inventory.potion": {"min": 1}}),
         ActionCandidate("attack", "attack", base_score=10)),
        ("use_potion", "attack"), "heal",
    ),
    Scenario(
        "rpg_reject_unknown", "rpg", "Unknown actions must not be selected.",
        {"enemy_visible": True}, {"health": 80},
        (),
        (ActionCandidate("cheat", "delete_enemy", tags=("health",)),
         ActionCandidate("attack", "attack", tags=("health",))),
        ("attack", "defend"), "attack",
    ),
    Scenario(
        "no_feasible_action", "generic", "Return no intent when every candidate fails preconditions.",
        {"cash": 2}, {"hunger": 80},
        (),
        (ActionCandidate("buy", "buy_food", tags=("hunger",), preconditions={"cash": {"min": 10}}),),
        ("buy_food",), None,
    ),
)


def run_benchmark() -> dict[str, Any]:
    results = []
    for scenario in SCENARIOS:
        decision = choose_action(
            state=scenario.state,
            needs=scenario.needs,
            goals=scenario.goals,
            candidates=scenario.candidates,
            allowed_actions=scenario.allowed_actions,
        )
        passed = decision.action_id == scenario.expected_action_id
        results.append({
            "scenario_id": scenario.scenario_id,
            "genre": scenario.genre,
            "expected_action_id": scenario.expected_action_id,
            "actual_action_id": decision.action_id,
            "passed": passed,
            "reason": decision.reason,
        })
    passed_count = sum(1 for item in results if item["passed"])
    return {
        "benchmark": "sandev_core_baseline_v1",
        "passed": passed_count,
        "total": len(results),
        "accuracy": passed_count / len(results) if results else 0.0,
        "results": results,
        "interpretation": "Hand-authored regression scenarios only; not a general intelligence score.",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_benchmark(), ensure_ascii=False, indent=2))
