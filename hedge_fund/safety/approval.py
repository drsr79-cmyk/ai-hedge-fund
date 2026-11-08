"""Per-session approval tokens for paper orders.

A token names one fund and one session. It is not permission to run a
later session, and it is not accepted by the unattended runner.
"""

from __future__ import annotations

import hashlib
import json


class ApprovalRequired(RuntimeError):
    """A paper order entry point was reached without a matching token."""

    def __init__(self, name: str, session: str, token: str) -> None:
        self.name = name
        self.session = session
        self.token = token
        super().__init__(
            f"{name}: approval required before paper orders for session {session}\n"
            f"approval-token: {token}\n"
            f"re-run: aihf paper tick {name} --approve {token}"
        )


def pending_fingerprint(pending) -> str:
    """Stable id of the decision an approval is allowed to execute."""
    if pending is None:
        return "none"
    payload = pending.model_dump_json()
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def approval_token(name: str, session: str, pending_id: str) -> str:
    """32 hex chars bound to this fund, session, and pending decision."""
    raw = json.dumps(
        ["aihf-paper-approval-v1", name, session, pending_id],
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
