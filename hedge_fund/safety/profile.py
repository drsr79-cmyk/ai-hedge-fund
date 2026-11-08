"""Process profile: safe (default) or an explicit network opt-in.

Safe profile drops inherited credentials and never enables payments.
Network profile still does not read a working-directory ``.env`` and does
not turn on x402 unless ``AIHF_ENABLE_X402=1``.
"""

from __future__ import annotations

import os

SAFE = "safe"
NETWORK = "network"

# Names the app will not inherit while the safe profile is in force.
CREDENTIAL_ENV = (
    "FINANCIAL_DATASETS_API_KEY",
    "X402_WALLET_PRIVATE_KEY",
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
    "LANGCHAIN_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING",
    "AIHF_ENABLE_X402",
)


def current_profile() -> str:
    """The active profile. Unset means safe. Anything else is refused."""
    raw = os.environ.get("AIHF_PROFILE", SAFE).strip().lower()
    if raw not in (SAFE, NETWORK):
        raise ValueError(
            f"AIHF_PROFILE must be {SAFE!r} or {NETWORK!r} (got {raw!r}). "
            "Safe is the default and does not use credentials or the network."
        )
    return raw


def x402_payments_allowed() -> bool:
    """Wallet payments stay off unless the operator opts in twice.

    Safe profile cannot enable them. Network profile also needs
    ``AIHF_ENABLE_X402=1``. A wallet key alone is not permission to pay.
    """
    if current_profile() != NETWORK:
        return False
    return os.environ.get("AIHF_ENABLE_X402") == "1"


def apply_profile_credentials() -> None:
    """Load credentials only for an explicit network profile.

    Safe profile removes inherited provider secrets from this process so a
    shell export or a previous tool cannot be reused by accident. Network
    profile loads ``~/.hedge-fund/.env`` only when ``AIHF_LOAD_DOTENV=1``
    and never reads a ``.env`` in the working directory.
    """
    if current_profile() == SAFE:
        for name in CREDENTIAL_ENV:
            os.environ.pop(name, None)
        return
    if os.environ.get("AIHF_LOAD_DOTENV") != "1":
        return
    from dotenv import load_dotenv

    from hedge_fund.paths import ENV_PATH

    load_dotenv(ENV_PATH, override=False)
