import os
import sys
import importlib.util
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_forex_market_data_module():
    module_name = "trader_app.services.forex_market_data"
    if module_name in sys.modules:
        return sys.modules[module_name]
    if "requests" not in sys.modules:
        requests_stub = types.ModuleType("requests")
        class Timeout(Exception):
            pass
        class RequestException(Exception):
            pass
        def _blocked_get(*args, **kwargs):
            raise RequestException("network disabled in diagnostic")
        requests_stub.get = _blocked_get
        requests_stub.exceptions = types.SimpleNamespace(Timeout=Timeout, RequestException=RequestException)
        sys.modules["requests"] = requests_stub
    trader_app_stub = types.ModuleType("trader_app")
    services_stub = types.ModuleType("trader_app.services")
    sys.modules.setdefault("trader_app", trader_app_stub)
    sys.modules.setdefault("trader_app.services", services_stub)
    module = load_module_from_path(module_name, ROOT / "trader_app" / "services" / "forex_market_data.py")
    setattr(services_stub, "forex_market_data", module)
    return module


def load_forex_analyzer_module():
    load_forex_market_data_module()
    return load_module_from_path("forex_analyzer_diag", ROOT / "forex_analyzer.py")


def test_forex_market_data_no_fake_output():
    fmd = load_forex_market_data_module()

    previous_key = os.environ.get("FOREX_DATA_API_KEY")
    os.environ["FOREX_DATA_API_KEY"] = ""
    try:
        result = fmd.get_ohlcv("EURUSD", "15m", outputsize=20)
        assert_true(result.ok is False, "Forex data without API key must not return fake candles")
        assert_true(result.error == "missing_forex_api_key", f"Unexpected missing-key error: {result.error}")
        assert_true(fmd.normalize_forex_symbol("eur/usd") == "EURUSD", "Forex symbol normalization failed")
        assert_true(fmd.pip_size("EURUSD") == 0.0001, "EURUSD pip size failed")
        assert_true(fmd.pip_size("USDJPY") == 0.01, "USDJPY pip size failed")
        assert_true(fmd.asset_class_for_symbol("XAUUSD") == "metal", "XAUUSD asset class failed")
    finally:
        if previous_key is None:
            os.environ.pop("FOREX_DATA_API_KEY", None)
        else:
            os.environ["FOREX_DATA_API_KEY"] = previous_key


def test_forex_provider_failure_timeout_stale_and_filters():
    fmd = load_forex_market_data_module()
    forex_analyzer = load_forex_analyzer_module()
    import pandas as pd

    original_key = fmd.FOREX_API_KEY
    original_get = fmd.requests.get
    original_cache = dict(fmd._CACHE)
    try:
        fmd.FOREX_API_KEY = "diagnostic_key"
        fmd._CACHE.clear()

        class TimeoutResponse:
            pass

        def timeout_get(*args, **kwargs):
            raise fmd.requests.exceptions.Timeout("diagnostic timeout")

        fmd.requests.get = timeout_get
        timeout_result = fmd.get_ohlcv("EURUSD", "15m", outputsize=80)
        assert_true(timeout_result.ok is False and timeout_result.error == "timeout", "Forex timeout must be reported safely")

        class StaleResponse:
            status_code = 200
            def json(self):
                rows = []
                for i in range(90):
                    rows.append({
                        "datetime": f"2020-01-01 00:{i % 60:02d}:00",
                        "open": "1.1000",
                        "high": "1.1020",
                        "low": "1.0980",
                        "close": "1.1010",
                        "volume": "1000",
                    })
                return {"values": rows}

        fmd._CACHE.clear()
        fmd.requests.get = lambda *args, **kwargs: StaleResponse()
        stale_result = fmd.get_ohlcv("EURUSD", "15m", outputsize=80)
        assert_true(stale_result.ok is False and stale_result.error == "stale_data", "Stale Forex candles must be rejected")

        flat_frame = pd.DataFrame([
            {"open": 1.1, "high": 1.10001, "low": 1.09999, "close": 1.1, "volume": 1000}
            for _ in range(80)
        ])
        vol_ok, vol_reason, _ = forex_analyzer._volatility_ok("EURUSD", flat_frame)
        assert_true(vol_ok is False and "atr_too_low" in vol_reason, "Low-volatility Forex frame must be rejected")

        wide_frame = pd.DataFrame([
            {"open": 1.1, "high": 1.2, "low": 1.0, "close": 1.11, "volume": 1000}
            for _ in range(80)
        ])
        spread = forex_analyzer._spread_pips("EURUSD", wide_frame)
        assert_true(spread > 2.5, "Spread proxy should reject wide candle conditions")

        assert_true(forex_analyzer._session(datetime(2026, 1, 1, 8, tzinfo=timezone.utc)) == "London", "London session detection failed")
        original_news = forex_analyzer.FOREX_NEWS_BLACKOUT_ACTIVE
        forex_analyzer.FOREX_NEWS_BLACKOUT_ACTIVE = True
        news_ok, news_reason = forex_analyzer._news_ok()
        assert_true(news_ok is False and "news" in news_reason, "News blackout must block Forex signals")
        forex_analyzer.FOREX_NEWS_BLACKOUT_ACTIVE = original_news
    finally:
        fmd.FOREX_API_KEY = original_key
        fmd.requests.get = original_get
        fmd._CACHE.clear()
        fmd._CACHE.update(original_cache)


def test_forex_analyzer_signal_shape_with_fixture():
    import pandas as pd
    forex_analyzer = load_forex_analyzer_module()
    fmd = load_forex_market_data_module()
    ForexCandlesResult = fmd.ForexCandlesResult

    now = datetime.now(timezone.utc).replace(microsecond=0)

    def make_frame(rows=90, start=1.08, step=0.00045):
        data = []
        for i in range(rows):
            base = start + i * step
            # Mild pullback on the final candles, still above EMA trend.
            if i > rows - 8:
                base -= (rows - i) * step * 0.55
            data.append(
                {
                    "time": now,
                    "open": base - 0.00015,
                    "high": base + 0.00045,
                    "low": base - 0.00035,
                    "close": base,
                    "volume": 1000 + i,
                }
            )
        return pd.DataFrame(data)

    original_get_ohlcv = forex_analyzer.get_ohlcv
    original_symbols = list(forex_analyzer.FOREX_SYMBOLS)
    original_timeframes = list(forex_analyzer.FOREX_TIMEFRAMES)
    original_news = os.environ.get("FOREX_NEWS_BLACKOUT_ACTIVE")
    original_conf = os.environ.get("FOREX_MIN_CONFIDENCE")
    try:
        forex_analyzer.FOREX_SYMBOLS[:] = ["EURUSD"]
        forex_analyzer.FOREX_TIMEFRAMES[:] = ["5m", "15m", "1h", "4h"]
        os.environ["FOREX_NEWS_BLACKOUT_ACTIVE"] = "false"
        os.environ["FOREX_MIN_CONFIDENCE"] = "60"

        def fake_get_ohlcv(symbol, timeframe, outputsize=120):
            frame = make_frame()
            return ForexCandlesResult(
                ok=True,
                symbol=symbol,
                timeframe=timeframe,
                provider="fixture",
                candles=frame.to_dict("records"),
                data_timestamp=now.isoformat(),
            )

        forex_analyzer.get_ohlcv = fake_get_ohlcv
        signals = forex_analyzer.get_forex_signals(limit=1)
        assert_true(isinstance(signals, list), "Forex analyzer must return a list")
        if signals:
            signal = signals[0]
            assert_true(signal.get("market_type") == "forex", "Forex signal missing market_type=forex")
            assert_true(signal.get("type") == "FOREX", "Forex signal missing type=FOREX")
            assert_true(signal.get("auto_trade_allowed") is False, "Forex auto-trade must stay disabled")
            assert_true(signal.get("risk_reward", 0) >= 1.5, "Forex signal RR below minimum")
    finally:
        forex_analyzer.get_ohlcv = original_get_ohlcv
        forex_analyzer.FOREX_SYMBOLS[:] = original_symbols
        forex_analyzer.FOREX_TIMEFRAMES[:] = original_timeframes
        if original_news is None:
            os.environ.pop("FOREX_NEWS_BLACKOUT_ACTIVE", None)
        else:
            os.environ["FOREX_NEWS_BLACKOUT_ACTIVE"] = original_news
        if original_conf is None:
            os.environ.pop("FOREX_MIN_CONFIDENCE", None)
        else:
            os.environ["FOREX_MIN_CONFIDENCE"] = original_conf


def test_delivery_routing_and_diagnostics():
    import market_analyzer

    auto_sender_text = (ROOT / "auto_sender.py").read_text(encoding="utf-8", errors="replace")
    assert_true('VIP_ALL_FOREX_CODE = "vip_all_forex"' in auto_sender_text, "vip_all_forex code missing")
    assert_true('signal_market_bucket(signal) == "forex"' in auto_sender_text, "Forex market bucket delivery branch missing")
    assert_true('FOREX_AUTO_TRADE_DISABLED' in auto_sender_text, "Forex auto-trade disabled guard missing")
    assert_true('log_forex_scan_summary' in auto_sender_text, "Forex scan summary integration missing")
    assert_true('CRYPTO_SCAN_SUMMARY' in auto_sender_text, "Crypto scan summary log missing")
    assert_true('DELIVERY_SUMMARY' in auto_sender_text, "Delivery summary log missing")

    market_analyzer.reset_signal_scan_diagnostics()
    code = market_analyzer._record_scan_rejection("LOW_LIQUIDITY poor quote volume")
    summary = market_analyzer.get_signal_scan_diagnostics()
    assert_true(code == "LOW_LIQUIDITY", "Rejection reason code classification failed")
    assert_true(summary["rejections_by_code"].get("LOW_LIQUIDITY") == 1, "Rejection code counter failed")


def test_symbol_mode_and_quality_profile_defaults():
    import market_analyzer

    assert_true(market_analyzer.SIGNAL_QUALITY_PROFILE in {"conservative", "balanced", "strict"}, "Unknown quality profile")
    assert_true(market_analyzer.MIN_SPOT_FINAL_SCORE >= 88, "Conservative spot threshold must preserve production behavior")
    assert_true(market_analyzer.MIN_FUTURES_FINAL_SCORE >= 90, "Conservative futures threshold must preserve production behavior")
    assert_true(market_analyzer.MAX_DYNAMIC_SYMBOLS == 120, "MAX_DYNAMIC_SYMBOLS default must be 120")
    assert_true(market_analyzer.SINGLE_SYMBOL_MODE is False, "SINGLE_SYMBOL_MODE must be false by default")


def main():
    test_forex_market_data_no_fake_output()
    test_forex_provider_failure_timeout_stale_and_filters()
    test_forex_analyzer_signal_shape_with_fixture()
    test_delivery_routing_and_diagnostics()
    test_symbol_mode_and_quality_profile_defaults()
    print("FOREX_ENGINE_AND_SIGNAL_SUPPLY_OK")


if __name__ == "__main__":
    main()
