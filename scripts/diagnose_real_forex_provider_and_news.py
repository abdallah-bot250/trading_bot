import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def reload_modules():
    for name in [
        "trader_app.services.forex_providers.oanda",
        "trader_app.services.forex_providers.tradingeconomics",
        "trader_app.services.forex_market_data",
        "trader_app.services.forex_news",
        "forex_analyzer",
    ]:
        sys.modules.pop(name, None)
    import trader_app.services.forex_providers.oanda as oanda
    import trader_app.services.forex_providers.tradingeconomics as tradingeconomics
    import trader_app.services.forex_market_data as market
    import trader_app.services.forex_news as news
    import forex_analyzer
    return oanda, tradingeconomics, market, news, forex_analyzer


def test_oanda_mapping_and_configuration():
    os.environ["FOREX_DATA_PROVIDER"] = "oanda"
    os.environ["OANDA_API_TOKEN"] = "test-token"
    os.environ["OANDA_ACCOUNT_ID"] = "test-account"
    oanda, _te, market, _news, _fx = reload_modules()
    assert_true(market.provider_symbol("EURUSD") == "EUR_USD", "EURUSD OANDA mapping failed")
    assert_true(market.provider_symbol("XAUUSD") == "XAU_USD", "XAUUSD OANDA mapping failed")
    assert_true(market.provider_interval("15m") == "M15", "M15 mapping failed")
    status = market.provider_configuration_status()
    assert_true(status["provider"] == "oanda" and status["configured"], "OANDA configured status failed")
    assert_true(oanda.configuration_status()["environment"] in {"practice", "live", ""}, "OANDA environment missing")


def test_complete_candles_and_bid_ask_extraction():
    os.environ["FOREX_DATA_PROVIDER"] = "oanda"
    os.environ["OANDA_API_TOKEN"] = "test-token"
    os.environ["OANDA_ACCOUNT_ID"] = "test-account"
    oanda, _te, market, _news, _fx = reload_modules()
    oanda.account_instruments = lambda force=False: ({"EUR_USD": {"name": "EUR_USD"}}, None)
    oanda.get_candles = lambda symbol, timeframe, count=120: oanda.OandaCandles(
        True,
        "EUR_USD",
        timeframe,
        [{"time": f"2026-07-16T00:{i:02d}:00Z", "open": 1.1, "high": 1.11, "low": 1.09, "close": 1.105, "volume": 100, "complete": True} for i in range(60)],
        data_timestamp="2026-07-16T00:59:00Z",
    )
    oanda.get_pricing = lambda symbol: oanda.OandaPricing(
        True,
        "EUR_USD",
        bid=1.105,
        ask=1.10512,
        price=1.10506,
        spread=0.00012,
        timestamp="2099-01-01T00:00:00Z",
        tradeable=True,
        status="tradeable",
    )
    candles = market.get_ohlcv("EURUSD", "15m")
    quote = market.get_quote("EURUSD")
    assert_true(candles.ok and all(c.get("complete") for c in candles.candles), "OANDA complete candle handling failed")
    assert_true(quote.ok and quote.bid and quote.ask and quote.ask > quote.bid, "OANDA real bid/ask extraction failed")
    assert_true(round((quote.ask - quote.bid) / market.pip_size("EURUSD"), 2) == 1.2, "EURUSD spread pips failed")
    assert_true(market.pip_size("USDJPY") == 0.01, "USDJPY pip size failed")
    assert_true(market.pip_size("XAUUSD") == 0.01, "XAUUSD pip size failed")


def test_unsupported_and_not_tradeable_rejections():
    os.environ["FOREX_DATA_PROVIDER"] = "oanda"
    os.environ["OANDA_API_TOKEN"] = "test-token"
    os.environ["OANDA_ACCOUNT_ID"] = "test-account"
    oanda, _te, market, _news, _fx = reload_modules()
    oanda.account_instruments = lambda force=False: ({"EUR_USD": {"name": "EUR_USD"}}, None)
    unsupported = market.get_quote("US30")
    assert_true(not unsupported.ok and unsupported.error == "SYMBOL_NOT_SUPPORTED", "unsupported OANDA asset must fail closed")
    oanda.get_pricing = lambda symbol: oanda.OandaPricing(False, "EUR_USD", tradeable=False, status="halted", error="MARKET_NOT_TRADEABLE")
    closed = market.get_quote("EURUSD")
    assert_true(not closed.ok and closed.error == "MARKET_NOT_TRADEABLE", "closed market rejection failed")


def test_trading_economics_news_windows_and_fail_closed():
    os.environ["FOREX_NEWS_PROVIDER"] = "tradingeconomics"
    os.environ["FOREX_REQUIRE_NEWS_CALENDAR"] = "true"
    os.environ["TRADING_ECONOMICS_API_KEY"] = "key"
    os.environ["TRADING_ECONOMICS_API_SECRET"] = "secret"
    _oanda, te, _market, news, _fx = reload_modules()
    class Result:
        ok = True
        error = None
        events = [{
            "event_id": "nfp",
            "country": "United States",
            "currency": "USD",
            "title": "Nonfarm Payrolls",
            "category": "Jobs",
            "importance": 3,
            "scheduled_utc": "2026-07-16T12:30:00+00:00",
            "forecast": None,
            "previous": None,
            "actual": None,
        }]
    te.load_events = lambda now=None: Result()
    from datetime import datetime, timezone
    decision = news.news_decision("EURUSD", now=datetime(2026, 7, 16, 12, 10, tzinfo=timezone.utc))
    assert_true(decision.blocked and decision.reason == "HIGH_IMPACT_NEWS_WINDOW", "high impact news window failed")
    os.environ["TRADING_ECONOMICS_API_KEY"] = ""
    os.environ["TRADING_ECONOMICS_API_SECRET"] = ""
    _oanda, _te, _market, news, _fx = reload_modules()
    decision = news.news_decision("EURUSD")
    assert_true(not decision.ok and decision.blocked and decision.reason == "API_KEY_MISSING", "news fail-closed failed")


def test_shadow_mode_prevents_delivery_marker():
    os.environ["FOREX_SHADOW_MODE"] = "true"
    os.environ["FOREX_PRODUCTION_MODE"] = "false"
    _oanda, _te, _market, _news, fx = reload_modules()
    assert_true(fx.forex_readiness_status()["auto_trade_status"].startswith("FOREX_AUTO_TRADE_DISABLED"), "Forex auto trade must remain disabled")
    assert_true(fx.forex_readiness_status()["checks"]["shadow_mode_enabled"], "Shadow mode marker missing")


if __name__ == "__main__":
    test_oanda_mapping_and_configuration()
    test_complete_candles_and_bid_ask_extraction()
    test_unsupported_and_not_tradeable_rejections()
    test_trading_economics_news_windows_and_fail_closed()
    test_shadow_mode_prevents_delivery_marker()
    print("REAL_FOREX_PROVIDER_AND_NEWS_OK")
