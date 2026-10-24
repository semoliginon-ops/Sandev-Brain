"""Message-to-pending-action bridge for SANDEV Brain.

A new player message invalidates older pending proposals for that session.
This module only registers proposals; the authoritative host engine remains
responsible for final validation, execution, and confirmation.
"""
from __future__ import annotations

import re
from threading import RLock
from typing import Any, Callable, Mapping, Sequence

from command import interpret_player_command
from pending_actions import PendingActionRegistry


_CANCEL_PREFIX = re.compile(
    r"^(?:tolong\s+)?(?:batal(?:kan|in)?|cancel(?:led)?|stop|hentikan|batalkan perintah(?:nya)?)(?:\b|$)"
    r"|^jangan(?:\s+dulu)?(?:\s+(?:lanjut(?:kan)?|teruskan|eksekusi|jalankan|serang|tembak|hantam|bidik)(?:\s+.+)?)?[.!?]*$",
    flags=re.IGNORECASE,
)


class PendingCommandSession:
    """Connect incoming player messages to command interpretation and lifecycle."""

    def __init__(self, registry: PendingActionRegistry | None = None, *, ttl_seconds: float = 30.0):
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be a positive number")
        self.registry = registry or PendingActionRegistry()
        self.ttl_seconds = float(ttl_seconds)
        self._locks_guard = RLock()
        self._session_locks: dict[str, RLock] = {}

    def _session_lock(self, session_id: str) -> RLock:
        with self._locks_guard:
            return self._session_locks.setdefault(session_id, RLock())

    def handle_message(
        self,
        session_id: str,
        message: str,
        entities: Sequence[Mapping[str, Any]],
        *,
        state_version: Any,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invalidate prior pending proposals before interpreting the latest message."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(message, str):
            raise ValueError("message must be a string")
        if state_version is None:
            raise ValueError("state_version is required")

        with self._session_lock(session_id):
            return self._handle_message_locked(
                session_id, message, entities, state_version=state_version, context=context
            )

    def _handle_message_locked(
        self,
        session_id: str,
        message: str,
        entities: Sequence[Mapping[str, Any]],
        *,
        state_version: Any,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        invalidated = self.registry.cancel(
            session_id,
            reason="superseded_by_new_player_message",
        )
        if _CANCEL_PREFIX.search(message.strip()):
            return {
                "status": "cancelled",
                "intent": "cancel_pending",
                "cancelled_action_ids": invalidated.get("action_ids", []),
                "invalidated_action_ids": invalidated.get("action_ids", []),
                "reason": "explicit_player_cancellation",
                "execution_allowed": False,
            }

        proposal = interpret_player_command(message, entities, context=context)
        response = {
            **proposal,
            "invalidated_action_ids": invalidated.get("action_ids", []),
        }
        if proposal.get("status") != "proposal":
            return response

        pending = self.registry.submit(
            session_id,
            state_version,
            proposal,
            ttl_seconds=self.ttl_seconds,
        )
        return {
            **response,
            "status": "pending",
            "action_id": pending["action_id"],
            "pending_expires_at": pending["expires_at"],
            "reason": "proposal_registered_awaiting_host_validation",
            "execution_allowed": False,
        }


    def execute_pending(
        self,
        session_id: str,
        action_id: str,
        *,
        get_current_state_version: Callable[[], Any],
        engine_execute_if_version_matches: Callable[[Mapping[str, Any], Any], Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Authorize and delegate execution while serializing this session's messages.

        The host callback MUST atomically compare the live state version with the
        expected version, validate game rules, execute the action, and return
        {"confirmed": bool, "result": {...}}. This lock only coordinates callers
        using this PendingCommandSession instance; it cannot lock external engine
        mutations or other processes.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("action_id must be a non-empty string")
        if not callable(get_current_state_version):
            raise ValueError("get_current_state_version must be callable")
        if not callable(engine_execute_if_version_matches):
            raise ValueError("engine_execute_if_version_matches must be callable")

        with self._session_lock(session_id):
            current_version = get_current_state_version()
            authorization = self.registry.authorize_execution(
                action_id, session_id, current_version
            )
            if not authorization.get("authorized"):
                return {
                    "accepted": False,
                    "status": "rejected",
                    "reason": authorization.get("reason", "authorization_failed"),
                    "execution_confirmed": False,
                }

            try:
                engine_response = engine_execute_if_version_matches(
                    authorization["payload"], authorization["state_version"]
                )
                if not isinstance(engine_response, Mapping):
                    raise ValueError("engine response must be an object")
                confirmed = engine_response.get("confirmed")
                if not isinstance(confirmed, bool):
                    raise ValueError("engine response must include boolean confirmed")
                engine_result = engine_response.get("result", {})
                if not isinstance(engine_result, Mapping):
                    raise ValueError("engine result must be an object")
            except Exception as exc:
                self.registry.record_engine_result(
                    action_id, session_id, engine_confirmed=False
                )
                return {
                    "accepted": False,
                    "status": "failed",
                    "reason": "host_engine_execution_or_validation_error",
                    "error_type": type(exc).__name__,
                    "execution_confirmed": False,
                }

            recorded = self.registry.record_engine_result(
                action_id,
                session_id,
                engine_confirmed=confirmed,
                result=engine_result,
            )
            if not recorded.get("recorded") or not confirmed:
                return {
                    "accepted": False,
                    "status": "failed",
                    "reason": recorded.get("reason", "engine_did_not_confirm_execution"),
                    "execution_confirmed": False,
                }
            return {
                "accepted": True,
                "status": "completed",
                "action_id": action_id,
                "execution_confirmed": True,
                "result": dict(engine_result),
            }
