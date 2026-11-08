"""Paper broker gate: re-read the kill switch before every fill.

Missing ``control.json`` is halted. Cash may not go negative. A long-only
mandate may not open a short. Prices and quantities must be finite.
"""

from __future__ import annotations

from math import isfinite

from hedge_fund.brokers.models import Order
from hedge_fund.paper.ledger import Ledger
from hedge_fund.pipeline.session import FundHalted

# Engineering ceiling, not an investment limit. Stops absurd integer orders.
MAX_SHARES = 1_000_000_000
_CASH_DUST = 0.01


class HaltGate:
    """Delegates to a paper broker and refuses an order the switch does not allow."""

    def __init__(self, inner, ledger: Ledger, *, long_only: bool) -> None:
        self._inner = inner
        self._ledger = ledger
        self._long_only = long_only

    def positions(self):
        return self._inner.positions()

    def cash(self) -> float:
        return self._inner.cash()

    def place_order(self, order: Order):
        reason = self._ledger.halted()
        if reason:
            raise FundHalted(f"kill switch refuses the fill: {reason}")
        if type(order.quantity) is not int or order.quantity <= 0 or order.quantity > MAX_SHARES:
            raise ValueError(f"{order.ticker}: order quantity must be a finite share count")
        if isinstance(order.price, bool) or not isinstance(order.price, (int, float)) or not isfinite(order.price) or order.price <= 0:
            raise ValueError(f"{order.ticker}: order price must be finite and positive")
        current = self._inner.positions().get(order.ticker)
        shares = current.shares if current is not None else 0
        delta = order.quantity if order.side == "buy" else -order.quantity
        new_shares = shares + delta
        if self._long_only and new_shares < 0:
            raise ValueError(f"{order.ticker}: long-only paper book cannot short")
        notion = order.quantity * float(order.price)
        next_cash = self._inner.cash() - notion if order.side == "buy" else self._inner.cash() + notion
        if next_cash < -_CASH_DUST:
            raise ValueError(
                f"{order.ticker}: order would take cash to {next_cash:,.2f}; paper mode does not borrow"
            )
        return self._inner.place_order(order)
