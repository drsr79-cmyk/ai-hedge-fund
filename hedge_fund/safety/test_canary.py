"""Fake-key tests. Nothing here is a real credential or a live host.

These tests monkeypatch ``requests`` inside the process. That is not
operating-system isolation: it cannot see a raw socket opened by another
library, a subprocess, or a future import that bypasses the stub. A
rejected URL in these tests proves this client raised before calling the
stubbed session, not that the machine's network stack was sealed.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from hedge_fund.backtesting.test_fund import FakeAnalyst, FakeDataClient, SERIES
from hedge_fund.data.client import FDClient, FDClientError
from hedge_fund.data.sessions import NEW_YORK
from hedge_fund.features.snapshot import FundamentalsSnapshot, PeriodFundamentals
from hedge_fund.fund import Fund, FundSpec
from hedge_fund.paper import deploy, Ledger, tick
from hedge_fund.paper.review import PromotionRefused, append_note, promote_strategy
from hedge_fund.safety.profile import apply_profile_credentials
from hedge_fund.safety.secrets import SecretPresent
from hedge_fund.signals.buffett import BuffettAgent

CANARY = "CANARY-FD-KEY-9f3e2a7b-do-not-leak"
WALLET = "CANARY-WALLET-0xabc-do-not-pay"


class _Response:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text
        self.headers = {}

    def json(self):
        return self._payload


def _price_row():
    return {"open": 1, "close": 1, "high": 1, "low": 1, "volume": 1, "time": "2024-01-02T00:00:00Z"}


def _client(monkeypatch):
    """A client whose session raises if a test forgets that the stub is not a firewall."""
    monkeypatch.setenv("AIHF_PROFILE", "network")
    client = FDClient(api_key=CANARY)
    calls = []

    def request(method, url, **kwargs):
        calls.append({"method": method, "url": url, "headers": dict(client._session.headers), **kwargs})
        if "evil" in url or "169.254" in url or "canary.invalid" in url:
            raise AssertionError(f"session was asked to contact {url}")
        return _Response(200, {"prices": [_price_row()]})

    client._session.request = request
    return client, calls


def test_redirect_is_not_followed_and_does_not_echo_the_key(monkeypatch):
    client, calls = _client(monkeypatch)

    def once(method, url, **kwargs):
        calls.append(url)
        assert kwargs["allow_redirects"] is False
        return _Response(302, text=f"go away {CANARY}")

    client._session.request = once
    with pytest.raises(FDClientError, match="redirect") as exc:
        client.get_prices("AAPL", "2024-01-01", "2024-01-05")
    assert CANARY not in str(exc.value)
    assert calls == ["https://api.financialdatasets.ai/prices/"]


@pytest.mark.parametrize("next_url", [
    "https://evil.example/prices",
    "http://169.254.169.254/latest",
    "https://api.financialdatasets.ai.evil.example/prices",
    "https://user:secret@api.financialdatasets.ai/prices",
    "https://api.financialdatasets.ai:8443/prices",
    "https://api.financialdatasets.ai%2e.evil.example/prices",
])
def test_pagination_to_another_host_is_refused_before_a_second_request(monkeypatch, next_url):
    client, calls = _client(monkeypatch)

    def first(method, url, **kwargs):
        calls.append(url)
        return _Response(200, {"prices": [_price_row()], "next_page_url": next_url})

    client._session.request = first
    with pytest.raises(FDClientError) as exc:
        client.get_prices("AAPL", "2024-01-01", "2024-01-05")
    assert calls == ["https://api.financialdatasets.ai/prices/"]
    assert CANARY not in str(exc.value)
    assert "evil" not in str(exc.value)
    assert "169.254" not in str(exc.value)


def test_custom_endpoint_cannot_be_used_as_the_data_host(monkeypatch):
    client, calls = _client(monkeypatch)
    monkeypatch.setenv("OPENAI_API_BASE", "https://canary.invalid/v1")
    monkeypatch.setenv("MOONSHOT_BASE_URL", "https://canary.invalid/kimi")
    for target in (
        "https://canary.invalid/v1/prices",
        "https://evil.example/v1",
        "http://api.financialdatasets.ai/prices/",
    ):
        with pytest.raises(FDClientError):
            client._request("GET", target)
    assert calls == []
    assert client._session.headers["X-API-Key"] == CANARY


def test_error_body_that_echoes_the_key_is_redacted(monkeypatch, caplog):
    client, _calls = _client(monkeypatch)

    def echo(method, url, **kwargs):
        return _Response(500, text=f"server echoed {CANARY}")

    client._session.request = echo
    with pytest.raises(FDClientError) as exc:
        client.get_prices("AAPL", "2024-01-01", "2024-01-05")
    assert CANARY not in str(exc.value)
    assert CANARY not in caplog.text


def test_model_prompt_does_not_receive_the_data_key(monkeypatch):
    monkeypatch.setenv("FINANCIAL_DATASETS_API_KEY", CANARY)
    monkeypatch.setenv("OPENAI_API_BASE", "https://canary.invalid/v1")
    system = BuffettAgent.get_system_prompt(BuffettAgent)
    snapshot = FundamentalsSnapshot(
        ticker="FIXA",
        as_of="2024-06-01",
        sector="Fixture",
        periods=[PeriodFundamentals(report_period="2024-03-31", filing_date="2024-05-01")],
    )
    rendered = snapshot.render(blind=False)
    assert CANARY not in system
    assert CANARY not in rendered
    assert "canary.invalid" not in system
    assert "canary.invalid" not in rendered


def test_safe_profile_rejects_inherited_key_and_payment_flag(monkeypatch):
    monkeypatch.setenv("FINANCIAL_DATASETS_API_KEY", CANARY)
    monkeypatch.setenv("X402_WALLET_PRIVATE_KEY", WALLET)
    monkeypatch.setenv("AIHF_ENABLE_X402", "1")
    monkeypatch.setenv("OPENAI_API_BASE", "https://canary.invalid/v1")
    monkeypatch.delenv("AIHF_PROFILE", raising=False)
    apply_profile_credentials()
    assert "FINANCIAL_DATASETS_API_KEY" not in __import__("os").environ
    assert "X402_WALLET_PRIVATE_KEY" not in __import__("os").environ
    assert "AIHF_ENABLE_X402" not in __import__("os").environ
    assert "OPENAI_API_BASE" not in __import__("os").environ


def test_safe_tick_refuses_when_a_live_key_is_still_set(monkeypatch, tmp_path):
    monkeypatch.delenv("AIHF_PROFILE", raising=False)
    monkeypatch.setenv("FINANCIAL_DATASETS_API_KEY", CANARY)
    monkeypatch.setitem(
        __import__("hedge_fund.signals", fromlist=["ALPHA_MODEL_REGISTRY"]).ALPHA_MODEL_REGISTRY,
        "a", FakeAnalyst,
    )
    spec = FundSpec(
        schema_version=2, name="paper-fund",
        strategies=[{"name": "solo", "models": [{"name": "a"}], "blend": {"mode": "long_only"}}],
        risk={"max_position_pct": 0.1, "max_gross_exposure": 1}, capital=100_000,
        costs={"spread_bps": 0, "commission_per_share": 0},
    )
    directory = deploy("alpha", spec, ["AAPL"], root=tmp_path)
    before = (directory / "broker.json").read_text()
    with pytest.raises(SecretPresent, match="FINANCIAL_DATASETS_API_KEY"):
        tick(directory, FakeDataClient(SERIES), build_fund=lambda s: Fund(s, models={"solo": [FakeAnalyst("a", {"AAPL": 1})]}),
             now=lambda: datetime(2024, 6, 13, 12, tzinfo=NEW_YORK))
    assert (directory / "broker.json").read_text() == before
    assert Ledger(directory).sessions() == []
    dumped = json.dumps({"broker": before, "events": ""})
    assert CANARY not in dumped


def test_review_notes_do_not_promote_code_or_change_controls(tmp_path, monkeypatch):
    monkeypatch.setenv("AIHF_PROFILE", "safe")
    note_path = append_note(tmp_path, session="2024-06-03", note="loss review: fixture only, not a model update")
    text = note_path.read_text()
    assert "recorded-only" in text
    assert CANARY not in text
    control = tmp_path / "control.json"
    control.write_text('{"halted": true}')
    before = control.read_text()
    with pytest.raises(PromotionRefused):
        promote_strategy(tmp_path, note="deploy this")
    assert control.read_text() == before
    assert __import__("os").environ["AIHF_PROFILE"] == "safe"
