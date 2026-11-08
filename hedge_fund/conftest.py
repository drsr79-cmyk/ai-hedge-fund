"""Shared test fixtures. Credentials are not loaded from dotenv files."""

import pytest

from hedge_fund.features import breakpoints


@pytest.fixture(autouse=True)
def _no_breakpoints_download(monkeypatch):
    """A blind agent built without an injected table must not download the
    breakpoints from a test. Tests that need a table pass their own."""
    def refuse():
        raise RuntimeError("tests must inject MEBreakpoints; no network download")
    monkeypatch.setattr(breakpoints, "load_breakpoints", refuse)
    monkeypatch.setattr(breakpoints, "_shared", None)
