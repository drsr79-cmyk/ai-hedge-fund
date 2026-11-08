"""Build the labelled offline paper mandate.

Risk numbers here are proposed engineering defaults so a demo book stays
long-only, unlevered, and size-capped. They are not an approved investment
policy and the fixture signal is not a forecast.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from hedge_fund.data.sessions import NEW_YORK
from hedge_fund.data.synthetic import FROZEN_ASOF, SyntheticDataClient
from hedge_fund.fund import FundSpec, load_strategy
from hedge_fund.safety.approval import approval_token, pending_fingerprint

# Proposed engineering defaults. Not a user-approved investment policy.
ENGINEERING_RISK = {
    "max_position_pct": 0.10,
    "max_gross_exposure": 1.0,
    "halve_drawdown_pct": 0.05,
    "max_drawdown_pct": 0.10,
    "max_adv_pct": 0.05,
}
FIXTURE_UNIVERSE = ["FIXA", "FIXB"]
_STRATEGY = Path(__file__).resolve().parent.parent / "strategies" / "offline-fixture.yaml"


def fixture_spec() -> FundSpec:
    """The only mandate the safe profile will advance."""
    strategy = load_strategy(_STRATEGY)
    return FundSpec(
        schema_version=2,
        name="offline-fixture",
        strategies=[strategy],
        risk=ENGINEERING_RISK,
        capital=100_000.0,
        rebalance="weekly",
        benchmark="SPY",
    )


def is_fixture_mandate(spec: FundSpec) -> bool:
    return all(model.name == "fixture" for strategy in spec.strategies for model in strategy.models)


def frozen_now() -> datetime:
    """The demo clock: the day after the last synthetic session."""
    year, month, day = (int(part) for part in FROZEN_ASOF.split("-"))
    return datetime(year, month, day, 12, tzinfo=NEW_YORK)


def synthetic_client(tickers: list[str], benchmark: str) -> SyntheticDataClient:
    return SyntheticDataClient(tickers, benchmark=benchmark)


def token_for(name: str, session: str, pending) -> str:
    return approval_token(name, session, pending_fingerprint(pending))
