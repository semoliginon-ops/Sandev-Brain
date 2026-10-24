"""Message-to-pending-action bridge for SANDEV Brain.

A new player message invalidates older pending proposals for that session.
This module only registers proposals; the authoritative host engine remains
responsible for final validation, execution, and confirmation.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

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
