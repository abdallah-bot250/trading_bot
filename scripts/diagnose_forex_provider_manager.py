"""Diagnose Nexora Forex multi-provider selection without requiring live API calls."""
from __future__ import annotations

import os
import sys
import importlib
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trader_app.services import forex_provider_manager as manager  # noqa: E402
from trader_app.services import forex_news  # noqa: E402


@contextmanager
def patched_env(**values):
    keys = set(values)
    previous = {key: os.environ.get(key) for key in keys}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def assert_equal(name: str, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: expected={expected!r} actual={actual!r}")


def assert_true(name: str, value):
    if not value:
        raise AssertionError(f"{name}: expected truthy value")


@dataclass
class FakeQuote:
    ok: bool
    symbol: str = "EURUSD"
    provider: str = "twelvedata"
    bid: Optional[float] = None
    ask: Optional[float] = None
    price: Optional[float] = 1.1
    spread: Optional[float] = None
    timestamp: Optional[str] = "2099-01-01T00:00:00+00:00"
    spread_available: bool = False
    error: Optional[str] = None
    status_code: Optional[int] = None
    fallback_used: bool = False


def scenario(label: str, expected_provider: str, **env):
    with patched_env(
        FOREX_DATA_PROVIDER=env.get("FOREX_DATA_PROVIDER", "twelvedata"),
        TWELVEDATA_API_KEY=env.get("TWELVEDATA_API_KEY"),
        FOREX_DATA_API_KEY=env.get("FOREX_DATA_API_KEY"),
        FINNHUB_API_KEY=env.get("FINNHUB_API_KEY"),
        OANDA_API_TOKEN=env.get("OANDA_API_TOKEN"),
        OANDA_ACCOUNT_ID=env.get("OANDA_ACCOUNT_ID"),
    ):
        selected = manager.selected_provider()
        config = manager.provider_configuration_status()
        assert_equal(label, selected, expected_provider)
        assert_equal(f"{label} config selected", config.get("selected_provider"), expected_provider)
        print(f"{label}: provider_selected={selected} configured={config.get('configured')} priority={config.get('priority')}")


def reload_analyzer(**env):
    with patched_env(**env):
        import forex_analyzer
        return importlib.reload(forex_analyzer)


def test_spread_policy():
    analyzer = reload_analyzer(
        FOREX_REQUIRE_REAL_SPREAD="true",
        FOREX_PRODUCTION_MODE="false",
        FOREX_SHADOW_MODE="true",
    )
    analyzer.get_pricing_quote = lambda symbol: FakeQuote(ok=False, provider="oanda", error="REAL_SPREAD_UNAVAILABLE")
    spread, meta = analyzer._spread_pips("EURUSD")
    assert_true("SHADOW_NO_BID_ASK_SPREAD_UNAVAILABLE", spread is None and meta.get("reason"))
    assert_true("SHADOW_NO_DELIVERY_BLOCK", not analyzer._real_spread_missing_blocks_delivery(spread, meta))
    print("SHADOW_TWELVEDATA_NO_BIDASK: candidate_allowed_for_shadow=true delivery=false")

    analyzer = reload_analyzer(
        FOREX_REQUIRE_REAL_SPREAD="true",
        FOREX_PRODUCTION_MODE="true",
        FOREX_SHADOW_MODE="false",
    )
    analyzer.get_pricing_quote = lambda symbol: FakeQuote(ok=False, provider="oanda", error="REAL_SPREAD_UNAVAILABLE")
    spread, meta = analyzer._spread_pips("EURUSD")
    assert_true("PRODUCTION_NO_BID_ASK_BLOCKED", analyzer._real_spread_missing_blocks_delivery(spread, meta))
    print("PRODUCTION_TWELVEDATA_NO_BIDASK: rejected=REAL_SPREAD_UNAVAILABLE")

    analyzer.get_pricing_quote = lambda symbol: FakeQuote(
        ok=True,
        provider="oanda",
        bid=1.10001,
        ask=1.10011,
        price=1.10006,
        spread=0.00010,
        spread_available=True,
    )
    spread, meta = analyzer._spread_pips("EURUSD")
    assert_true("OANDA_REAL_BID_ASK_ALLOWED", spread is not None and not analyzer._real_spread_missing_blocks_delivery(spread, meta))
    print("TWELVEDATA_CANDLES_OANDA_BIDASK: allowed_if_other_filters_pass=true")

    analyzer.get_pricing_quote = lambda symbol: FakeQuote(
        ok=True,
        provider="oanda",
        bid=1.10001,
        ask=1.10011,
        price=1.10006,
        spread=0.00010,
        spread_available=True,
        timestamp="2000-01-01T00:00:00+00:00",
    )
    spread, meta = analyzer._spread_pips("EURUSD")
    assert_true("STALE_BID_ASK_BLOCKED", analyzer._real_spread_missing_blocks_delivery(spread, meta))
    print("STALE_BIDASK: rejected=true")

    analyzer = reload_analyzer(
        FOREX_REQUIRE_REAL_SPREAD="false",
        FOREX_PRODUCTION_MODE="true",
        FOREX_SHADOW_MODE="false",
    )
    assert_true("REAL_SPREAD_FALSE_UNSAFE", analyzer._unsafe_production_configuration())
    print("UNSAFE_PRODUCTION_CONFIGURATION: production_delivery_blocked_without_real_spread=true")


def main():
    scenario(
        "TWELVEDATA_ONLY",
        "twelvedata",
        FOREX_DATA_PROVIDER="twelvedata",
        TWELVEDATA_API_KEY="td_demo_key",
    )
    scenario(
        "OANDA_ONLY",
        "oanda",
        FOREX_DATA_PROVIDER="auto",
        OANDA_API_TOKEN="oanda_demo_token",
        OANDA_ACCOUNT_ID="oanda_demo_account",
    )
    scenario(
        "BOTH_CONFIGURED",
        "twelvedata",
        FOREX_DATA_PROVIDER="auto",
        TWELVEDATA_API_KEY="td_demo_key",
        OANDA_API_TOKEN="oanda_demo_token",
        OANDA_ACCOUNT_ID="oanda_demo_account",
    )
    scenario(
        "OANDA_DISABLED",
        "twelvedata",
        FOREX_DATA_PROVIDER="auto",
        TWELVEDATA_API_KEY="td_demo_key",
    )
    with patched_env(
        FOREX_DATA_PROVIDER="auto",
        TWELVEDATA_API_KEY=None,
        FOREX_DATA_API_KEY=None,
        FINNHUB_API_KEY=None,
        OANDA_API_TOKEN=None,
        OANDA_ACCOUNT_ID=None,
    ):
        config = manager.provider_configuration_status()
        assert_true("ALL_PROVIDERS_DISABLED configured false", not config.get("configured"))
        print(f"ALL_PROVIDERS_DISABLED: provider_selected={config.get('selected_provider')} reason={config.get('reason')}")

    with patched_env(
        FOREX_REQUIRE_NEWS_CALENDAR="true",
        TRADING_ECONOMICS_API_KEY=None,
        TRADING_ECONOMICS_API_SECRET=None,
        FOREX_NEWS_API_KEY=None,
        FOREX_NEWS_API_SECRET=None,
    ):
        news = forex_news.configuration_status()
        assert_true("TRADING_ECONOMICS_DISABLED", news.get("required") and not news.get("configured"))
        print(f"TRADING_ECONOMICS_DISABLED: provider={news.get('provider')} reason={news.get('reason')}")

    diag = manager.diagnostic_status()
    assert_true("SUPPORTED_SYMBOLS", "EURUSD" in diag.get("supported_symbols", []))
    assert_true("REQUEST_BUDGET_PRESENT", "request_budget" in diag)
    print(f"SUPPORTED_SYMBOLS count={len(diag.get('supported_symbols', []))}")
    print(f"UNSUPPORTED_SYMBOLS count={len(diag.get('unsupported_symbols', []))}")
    print(f"REQUEST_BUDGET {diag.get('request_budget')}")
    test_spread_policy()
    print("FOREX_PROVIDER_MANAGER_OK")


if __name__ == "__main__":
    main()
