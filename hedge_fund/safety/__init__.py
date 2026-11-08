"""Fail-closed controls for paper research.

Engineering defaults in this package are not an investment policy and are
not evidence that a book is safe, profitable, or suitable for real money.
"""

from hedge_fund.safety.approval import ApprovalRequired, approval_token, pending_fingerprint
from hedge_fund.safety.profile import (
    NETWORK,
    SAFE,
    apply_profile_credentials,
    current_profile,
    x402_payments_allowed,
)

__all__ = [
    "NETWORK",
    "SAFE",
    "ApprovalRequired",
    "apply_profile_credentials",
    "approval_token",
    "current_profile",
    "pending_fingerprint",
    "x402_payments_allowed",
]
