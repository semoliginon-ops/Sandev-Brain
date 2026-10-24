"""In-memory pending-action lifecycle gate for SANDEV Brain.

This module manages proposals only; it never performs gameplay actions.
The host must call authorize_execution immediately at the serialized execution
boundary, then let the authoritative engine execute and confirm the result.
Persist records in the host if pending actions must survive process restarts.
"""
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from time import monotonic
from typing import Any, Mapping
from uuid import uuid4


class PendingActionError(ValueError):
    """Raised when a pending-action request is malformed."""


class PendingActionRegistry:
    """Thread-safe lifecycle registry for proposals awaiting host execution."""

    _TERMINAL = {"cancelled", "expired", "replaced", "completed", "failed"}

    def __init__(self, *, clock=monotonic) -> None:
        self._clock = clock
        self._lock = RLock()
        self._records: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _nonempty(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PendingActionError(f"{field} must be a non-empty string")
        return value.strip()

    def submit(
        self,
        session_id: str,
        state_version: Any,
        payload: Mapping[str, Any],
        *,
        ttl_seconds: float = 30.0,
        action_id: str | None = None,
        now: float | None = None,
    ) -> dict[str, Any]:
        """Register a proposal. Submitting does not authorize or execute it."""
        session = self._nonempty(session_id, "session_id")
        if state_version is None:
            raise PendingActionError("state_version is required")
        if not isinstance(payload, Mapping):
            raise PendingActionError("payload must be an object")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
            raise PendingActionError("ttl_seconds must be a positive number")
        identifier = self._nonempty(action_id, "action_id") if action_id is not None else uuid4().hex
        timestamp = self._clock() if now is None else now
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise PendingActionError("now must be numeric")

        with self._lock:
            if identifier in self._records:
                raise PendingActionError("action_id must be unique")
            record = {
                "action_id": identifier,
                "session_id": session,
                "state_version": state_version,
                "payload": deepcopy(dict(payload)),
                "status": "pending",
                "created_at": timestamp,
                "expires_at": timestamp + float(ttl_seconds),
                "reason": "awaiting_host_validation",
            }
            self._records[identifier] = record
            return deepcopy(record)

    def cancel(
        self,
        session_id: str,
        *,
        action_id: str | None = None,
        reason: str = "user_cancelled",
    ) -> dict[str, Any]:
        """Cancel one pending proposal or all pending proposals in a session."""
        session = self._nonempty(session_id, "session_id")
        if not isinstance(reason, str) or not reason.strip():
            raise PendingActionError("reason must be a non-empty string")
        with self._lock:
            if action_id is not None:
                identifier = self._nonempty(action_id, "action_id")
                record = self._records.get(identifier)
                if record is None or record["session_id"] != session:
                    return {"cancelled": False, "reason": "pending_action_not_found"}
                targets = [record]
            else:
                targets = [
                    record for record in self._records.values()
                    if record["session_id"] == session and record["status"] == "pending"
                ]
            cancelled = []
            skipped = []
            for record in targets:
                if record["status"] == "pending":
                    record["status"] = "cancelled"
                    record["reason"] = reason.strip()
                    cancelled.append(record["action_id"])
                else:
                    skipped.append(record["action_id"])
            return {
                "cancelled": bool(cancelled),
                "action_ids": cancelled,
                "skipped_action_ids": skipped,
                "reason": reason.strip() if cancelled else "no_matching_pending_action",
            }

    def authorize_execution(
        self,
        action_id: str,
        session_id: str,
        current_state_version: Any,
        *,
        now: float | None = None,
    ) -> dict[str, Any]:
        """Atomically transition pending -> authorized only for fresh, live proposals.

        This is a lifecycle gate, not proof that the engine executed anything.
        The host must serialize this gate with its execution boundary.
        """
        identifier = self._nonempty(action_id, "action_id")
        session = self._nonempty(session_id, "session_id")
        timestamp = self._clock() if now is None else now
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise PendingActionError("now must be numeric")

        with self._lock:
            record = self._records.get(identifier)
            if record is None or record["session_id"] != session:
                return {"authorized": False, "status": "rejected", "reason": "pending_action_not_found"}
            if record["status"] != "pending":
                return {
                    "authorized": False, "status": "rejected",
                    "reason": "action_not_pending", "action_status": record["status"],
                }
            if timestamp >= record["expires_at"]:
                record["status"] = "expired"
                record["reason"] = "pending_action_expired"
                return {"authorized": False, "status": "rejected", "reason": record["reason"]}
            if current_state_version is None or current_state_version != record["state_version"]:
                record["status"] = "cancelled"
                record["reason"] = "state_version_changed"
                return {"authorized": False, "status": "rejected", "reason": record["reason"]}
            record["status"] = "authorized"
            record["reason"] = "awaiting_authoritative_engine_execution"
            return {
                "authorized": True,
                "status": "authorized_proposal_engine_must_execute_and_confirm",
                "action_id": identifier,
                "payload": deepcopy(record["payload"]),
                "state_version": record["state_version"],
                "execution_confirmed": False,
            }

    def record_engine_result(
        self,
        action_id: str,
        session_id: str,
        *,
        engine_confirmed: bool,
        result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record the authoritative host result; never infer success from authorization."""
        identifier = self._nonempty(action_id, "action_id")
        session = self._nonempty(session_id, "session_id")
        if not isinstance(engine_confirmed, bool):
            raise PendingActionError("engine_confirmed must be a boolean")
        if result is not None and not isinstance(result, Mapping):
            raise PendingActionError("result must be an object")
        with self._lock:
            record = self._records.get(identifier)
            if record is None or record["session_id"] != session:
                return {"recorded": False, "reason": "pending_action_not_found"}
            if record["status"] != "authorized":
                return {"recorded": False, "reason": "action_not_authorized"}
            if not engine_confirmed:
                record["status"] = "failed"
                record["reason"] = "engine_did_not_confirm_execution"
                return {"recorded": True, "status": "failed", "execution_confirmed": False}
            record["status"] = "completed"
            record["reason"] = "authoritative_engine_confirmation_received"
            record["engine_result"] = deepcopy(dict(result or {}))
            return {"recorded": True, "status": "completed", "execution_confirmed": True}

    def get(self, action_id: str, session_id: str) -> dict[str, Any] | None:
        """Return a defensive copy of a session-owned record."""
        identifier = self._nonempty(action_id, "action_id")
        session = self._nonempty(session_id, "session_id")
        with self._lock:
            record = self._records.get(identifier)
            if record is None or record["session_id"] != session:
                return None
            return deepcopy(record)
