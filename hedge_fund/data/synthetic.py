"""Deterministic synthetic market data for the offline paper fixture.

Every series here is invented. Names, prices, and volume are labels for
exercising the paper engine without a network. They are not market data
and not evidence of profitability.
"""

from __future__ import annotations

from datetime import date, timedelta

from hedge_fund.data.models import (
    CompanyFacts,
    CompanyNews,
    Earnings,
    EarningsRecord,
    FinancialMetrics,
    InsiderTrade,
    Price,
    PriceSnapshot,
)

FIXTURE_LABEL = "SYNTHETIC FIXTURE — not market data, not a forecast, not profitability evidence"
# Frozen clock so a demo does not depend on today's date or a vendor calendar.
FROZEN_ASOF = "2024-06-13"
SERIES_START = date(2024, 1, 2)
SERIES_END = date(2024, 6, 12)


def _weekdays(start: date, end: date) -> list[date]:
    days = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _price(ticker: str, index: int) -> float:
    """A smooth, bounded path. Different tickers differ by a fixed offset."""
    seed = sum(ord(ch) for ch in ticker)
    base = 40.0 + (seed % 50)
    wave = ((index % 21) - 10) * 0.15
    return round(base + index * 0.02 + wave, 2)


class SyntheticDataClient:
    """In-memory bars for the fixture universe. No sockets."""

    label = FIXTURE_LABEL

    def __init__(self, tickers: list[str], *, benchmark: str = "SPY") -> None:
        self._names = list(dict.fromkeys([*tickers, benchmark]))
        self._days = _weekdays(SERIES_START, SERIES_END)

    def get_prices(self, ticker, start_date, end_date, **kwargs) -> list[Price]:
        rows = []
        for index, day in enumerate(self._days):
            iso = day.isoformat()
            if start_date <= iso <= end_date:
                close = _price(ticker, index)
                rows.append(Price(
                    open=close, close=close, high=close, low=close,
                    volume=1_000_000, time=f"{iso}T00:00:00Z",
                ))
        return rows

    def get_snapshot(self, ticker: str) -> PriceSnapshot | None:
        if not self._days:
            return None
        close = _price(ticker, len(self._days) - 1)
        return PriceSnapshot(
            ticker=ticker, price=close, time=f"{SERIES_END.isoformat()}T20:00:00Z",
        )

    def get_financial_metrics(self, ticker, end_date, period="ttm", limit=10) -> list[FinancialMetrics]:
        return []

    def get_news(self, ticker, end_date, start_date=None, limit=1000) -> list[CompanyNews]:
        return []

    def get_insider_trades(self, ticker, end_date, start_date=None, limit=1000) -> list[InsiderTrade]:
        return []

    def get_company_facts(self, ticker: str) -> CompanyFacts | None:
        return CompanyFacts(
            ticker=ticker,
            name=f"{FIXTURE_LABEL}: {ticker}",
            sector="Fixture",
            industry="Synthetic",
        )

    def get_earnings(self, ticker: str) -> Earnings | None:
        return None

    def get_earnings_history(self, ticker: str, limit: int = 12) -> list[EarningsRecord]:
        return []

    def get_market_cap(self, ticker: str, end_date: str) -> float | None:
        return None
