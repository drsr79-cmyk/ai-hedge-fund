"""Secret boundary for the safe paper process.

Popping environment variables is not operating-system isolation. A parent
process, a debugger, or a core dump can still hold a key this function
never sees. The check only proves this process's ``os.environ`` does not
carry the live data or payment credentials at the moment of the call.
"""

from __future__ import annotations

import os

SECRET_ENV = (
    "FINANCIAL_DATASETS_API_KEY",
    "X402_WALLET_PRIVATE_KEY",
    "AIHF_ENABLE_X402",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "DEEPSEEK_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "KIMI_API_KEY",
    "MOONSHOT_API_KEY",
    "MOONSHOT_BASE_URL",
    "TYPESAFE_API_KEY",
)


class SecretPresent(RuntimeError):
    """The safe paper process was asked to run while a live secret was set."""


def require_secretless_process() -> None:
    """Refuse if this process inherited a data key, wallet key, or payment flag.

    Names only are reported. Values are not.
    """
    present = [name for name in SECRET_ENV if os.environ.get(name)]
    if present:
        raise SecretPresent(
            "safe paper process refuses inherited live credentials or payment "
            f"config: {', '.join(present)}. Unset them in this process. "
            "A separate ingestion service would have to own a read-only data "
            "key and write sanitized snapshots; this process does not."
        )


def redact(text: str) -> str:
    """Remove any secret currently in the environment from *text*."""
    for name in SECRET_ENV:
        value = os.environ.get(name)
        if value and value in text:
            text = text.replace(value, "[REDACTED]")
    return text
