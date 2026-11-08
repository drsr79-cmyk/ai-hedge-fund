"""A labelled stand-in analyst for offline paper runs.

The number it returns is a fixed fixture so the engine can size a book
without calling a model. It is not a view about any real company and it
is not evidence that the resulting paper portfolio would make money.
"""

from __future__ import annotations

from hedge_fund.data.protocol import DataClient
from hedge_fund.models import Signal
from hedge_fund.signals.base import QuantModel

FIXTURE_SIGNAL = 0.2  # engineering stub, inside [-1, 1], not a forecast


class FixtureModel(QuantModel):
    """Deterministic long-only stub. See the module docstring."""

    investment_approach = "long_only"
    horizon_days = 1

    @property
    def name(self) -> str:
        return "fixture"

    def predict(self, ticker: str, date: str, data_client: DataClient) -> Signal:
        return Signal(
            model_name=self.name,
            ticker=ticker,
            date=date,
            value=FIXTURE_SIGNAL,
            reasoning=(
                "SYNTHETIC FIXTURE signal. Not a forecast and not profitability evidence."
            ),
            metadata={"fixture": True, "not_a_forecast": True},
        )
