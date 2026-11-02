"""Small deterministic RPG runtime proving the language-to-engine boundary.

This is a test simulator, not a general language model or a production game.
All world mutations happen inside the authoritative runtime callback after
fresh candidate, allow-list, state-version, and precondition validation.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from command import interpret_player_command
from engine_bridge import resolve_language_proposal


class GameRuntimeError(ValueError):
    """Raised for invalid simulator configuration or input."""


class GameRuntimeSimulator:
    """A tiny RPG world with a player, two enemies, and one healing potion."""

    ACTION_TYPE_MAP = {
        "tactical_attack": "attack",
        "heal_request": "heal",
    }

    def __init__(self) -> None:
        self.game_id = "sandev-rpg-simulator"
        self.state_version = 1
        self.state: dict[str, Any] = {
            "player": {"hp": 50, "max_hp": 50, "potions": 1},
            "enemies": {
                "goblin": {"hp": 20, "alive": True},
                "bandit": {"hp": 25, "alive": True},
            },
        }
        self._enemy_names = {"goblin": "Goblin", "bandit": "Bandit"}

    def _entities(self) -> list[dict[str, Any]]:
        return [
            {"id": enemy_id, "name": name, "aliases": [name.lower()]}
            for enemy_id, name in self._enemy_names.items()
            if self.state["enemies"][enemy_id]["alive"]
        ]

    def snapshot(self) -> dict[str, Any]:
        """Return an isolated view of the current authoritative world."""
        entities = self._entities()
        candidates = []
        for entity in entities:
            enemy_id = entity["id"]
            candidates.append({
                "action_id": f"attack-{enemy_id}",
                "kind": "attack",
                "target": enemy_id,
                "preconditions": {f"enemies.{enemy_id}.hp": {"min": 1}},
            })
        if self.state["player"]["potions"] > 0:
            candidates.append({
                "action_id": "heal-player",
                "kind": "heal",
                "target": "",
                "preconditions": {"player.potions": {"min": 1}},
            })
        return {
            "game_id": self.game_id,
            "state_version": self.state_version,
            "state": deepcopy(self.state),
            "entities": entities,
            "candidates": candidates,
            "allowed_actions": ["attack", "heal"],
        }

    def _execute_confirmed(
        self, proposal: Mapping[str, Any], expected_version: Any
    ) -> dict[str, Any]:
        """Synchronous host-engine boundary; validate again before mutation."""
        live = self.snapshot()
        if live["state_version"] != expected_version:
            return {"confirmed": False, "result": {"reason": "stale_state_version"}}
        validation = resolve_language_proposal(
            live, proposal, action_type_map=self.ACTION_TYPE_MAP
        )
        if not validation.get("accepted"):
            return {"confirmed": False, "result": {"reason": validation.get("reason")}}

        action_type = validation["action"]["type"]
        target = validation["action"]["target"]
        if action_type == "attack":
            enemy = self.state["enemies"][target]
            enemy["hp"] = max(0, enemy["hp"] - 10)
            enemy["alive"] = enemy["hp"] > 0
            result = {
                "action": "attack", "target": self._enemy_names[target],
                "damage": 10, "target_hp": enemy["hp"],
                "target_defeated": not enemy["alive"],
            }
        elif action_type == "heal":
            player = self.state["player"]
            before = player["hp"]
            player["hp"] = min(player["max_hp"], player["hp"] + 20)
            player["potions"] -= 1
            result = {
                "action": "heal", "healed": player["hp"] - before,
                "player_hp": player["hp"], "potions_left": player["potions"],
            }
        else:
            return {"confirmed": False, "result": {"reason": "unsupported_action"}}

        self.state_version += 1
        result["state_version_after"] = self.state_version
        return {"confirmed": True, "result": result}

    def submit(self, message: str) -> dict[str, Any]:
        """Interpret one player message, validate it, and ask the engine to act."""
        if not isinstance(message, str) or not message.strip():
            raise GameRuntimeError("message must be a non-empty string")
        current = self.snapshot()
        proposal = interpret_player_command(
            message,
            current["entities"],
            context={"game_id": self.game_id, "state_version": current["state_version"]},
        )
        if proposal.get("status") != "proposal":
            return {
                "status": "needs_clarification",
                "reason": proposal.get("reason", "message_not_resolved"),
                "proposal": proposal,
                "world": self.snapshot(),
            }

        validation = resolve_language_proposal(
            current, proposal, action_type_map=self.ACTION_TYPE_MAP
        )
        if not validation.get("accepted"):
            return {
                "status": "rejected",
                "reason": validation.get("reason", "engine_validation_rejected"),
                "proposal": proposal,
                "validation": validation,
                "world": self.snapshot(),
            }

        engine_result = self._execute_confirmed(proposal, current["state_version"])
        if not engine_result.get("confirmed"):
            return {
                "status": "rejected",
                "reason": engine_result.get("result", {}).get("reason", "engine_not_confirmed"),
                "proposal": proposal,
                "validation": validation,
                "engine": engine_result,
                "world": self.snapshot(),
            }

        outcome = engine_result["result"]
        if outcome["action"] == "attack":
            if outcome["target_defeated"]:
                line = f"{outcome['target']} tumbang! Seranganmu menghasilkan {outcome['damage']} damage."
            else:
                line = (
                    f"Aku menyerang {outcome['target']} dan menghasilkan "
                    f"{outcome['damage']} damage. HP musuh tersisa {outcome['target_hp']}."
                )
        else:
            line = (
                f"Ramuan digunakan. HP pulih {outcome['healed']} menjadi "
                f"{outcome['player_hp']}. Sisa ramuan: {outcome['potions_left']}."
            )
        return {
            "status": "executed",
            "proposal": proposal,
            "validation": validation,
            "engine": engine_result,
            "response": line,
            "world": self.snapshot(),
        }


if __name__ == "__main__":
    import json
    import sys

    runtime = GameRuntimeSimulator()
    for raw in sys.stdin:
        try:
            result = runtime.submit(raw.rstrip("\n"))
            print(json.dumps(result, ensure_ascii=False))
        except GameRuntimeError as exc:
            print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=False))
