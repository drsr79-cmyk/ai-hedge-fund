"""Operator review notes for a paper fund.

A note is text stored next to the ledger. Nothing in this module edits
strategy source, changes the safe-profile rules, enables payments, or
promotes a new model into the running fund. There is no trainer and no
updater here.

The existing scorecard can grade past views against later recorded marks.
That is a retrospective measurement. It is not evidence of improvement,
and it does not deploy code.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

NOTES_FILE = "review-notes.jsonl"


class PromotionRefused(PermissionError):
    """Code and security controls are not promoted from a review note."""


def append_note(directory: str | Path, *, session: str, note: str) -> Path:
    """Append one review note. The note is not executed."""
    if not session or not note.strip():
        raise ValueError("a review note needs a session and text")
    path = Path(directory) / NOTES_FILE
    record = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": session,
        "note": note,
        "effect": "recorded-only",
    }
    with path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    return path


def promote_strategy(*_args, **_kwargs) -> None:
    """Manual gate. This always refuses; it does not write files."""
    raise PromotionRefused(
        "promotion is manual. Review notes are not applied to strategy code, "
        "the kill switch, or payment settings."
    )
