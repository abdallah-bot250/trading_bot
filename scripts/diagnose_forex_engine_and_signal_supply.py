import importlib.util
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def install_runtime_stubs():
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
    sys.modules.setdefault("pandas", types.ModuleType("pandas"))
    sys.modules.setdefault("numpy", types.ModuleType("numpy"))


def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_forex_market_data_module():
    install_runtime_stubs()
    module_name = "trader_app.services.forex_market_data"
    if module_name in sys.modules:
        return sys.modules[module_name]
    trader_app_stub = types.ModuleType("trader_app")
    services_stub = types.ModuleType("trader_app.services")
    sys.modules.setdefault("trader_app", trader_app_stub)
    sys.modules.setdefault("trader_app.services", services_stub)
    module = load_module_from_path(module_name, ROOT / "trader_app" / "services" / "forex_market_data.py")
    setattr(services_stub, "forex_market_data", module)
    return module


def install_market_analyzer_stubs():
    install_runtime_stubs()
    if "ai_model" not in sys.modules:
        ai_model = types.ModuleType("ai_model")
        ai_model.predict_trade = lambda signal: True
        sys.modules["ai_model"] = ai_model
    if "ai_engine" not in sys.modules:
        ai_engine = types.ModuleType("ai_engine")
        ai_engine.build_ai_engine_report = lambda *args, **kwargs: {}
        sys.modules["ai_engine"] = ai_engine
    if "spot_futures_engine" not in sys.modules:
        sfe = types.ModuleType("spot_futures_engine")
        sfe.choose_trade_type = lambda *args, **kwargs: "spot"
        sfe.evaluate_trade_types = lambda *args, **kwargs: {}
        sfe.record_trade_type = lambda *args, **kwargs: None
        sys.modules["spot_futures_engine"] = sfe


def test_forex_market_data_no_fake_output():
    fmd = load_forex_market_data_module()

    previous_key = os.environ.get("FOREX_DATA_API_KEY")
    original_key = fmd.FOREX_API_KEY
    os.environ["FOREX_DATA_API_KEY"] = ""
    fmd.FOREX_API_KEY = ""
    try:
        result = fmd.get_ohlcv("EURUSD", "15m", outputsize=20)
        assert_true(result.ok is False, "Forex data without API key must not return fake candles")
        assert_true(result.error == "API_KEY_MISSING", f"Unexpected missing-key error: {result.error}")
        assert_true(fmd.normalize_forex_symbol("eur/usd") == "EURUSD", "Forex symbol normalization failed")
        assert_true(fmd.pip_size("EURUSD") == 0.0001, "EURUSD pip size failed")
        assert_true(fmd.pip_size("USDJPY") == 0.01, "USDJPY pip size failed")
        assert_true(fmd.asset_class_for_symbol("XAUUSD") == "metal", "XAUUSD asset class failed")
        status = fmd.provider_configuration_status()
        assert_true(status["configured"] is False, "Missing Forex key should report configured=false")
        assert_true(status["reason"] == "API_KEY_MISSING", f"Unexpected provider reason: {status['reason']}")
    finally:
        fmd.FOREX_API_KEY = original_key
        if previous_key is None:
            os.environ.pop("FOREX_DATA_API_KEY", None)
        else:
            os.environ["FOREX_DATA_API_KEY"] = previous_key


def test_forex_analyzer_provider_guard_is_present():
    text = (ROOT / "forex_analyzer.py").read_text(encoding="utf-8", errors="replace")
    assert_true("provider_configuration_status" in text, "Forex analyzer must check provider configuration")
    assert_true("FOREX_PROVIDER_STATUS" in text, "Forex provider status startup/scan log missing")
    assert_true("disabled_reason" in text, "Forex disabled reason must be exposed in summary")
    assert_true("symbols_requested" in text, "Forex summary must include symbols_requested")
    assert_true("requests_failed" in text, "Forex summary must include requests_failed")


def test_delivery_routing_and_diagnostics():
    auto_sender_text = (ROOT / "auto_sender.py").read_text(encoding="utf-8", errors="replace")
    assert_true('VIP_ALL_FOREX_CODE = "vip_all_forex"' in auto_sender_text, "vip_all_forex code missing")
    assert_true('signal_market_bucket(signal) == "forex"' in auto_sender_text, "Forex delivery branch missing")
    assert_true("FOREX_AUTO_TRADE_DISABLED" in auto_sender_text, "Forex auto-trade disabled guard missing")
    assert_true("log_forex_scan_summary" in auto_sender_text, "Forex scan summary integration missing")
    assert_true("CRYPTO_SCAN_SUMMARY" in auto_sender_text, "Crypto scan summary log missing")
    assert_true("DELIVERY_SUMMARY" in auto_sender_text, "Delivery summary log missing")


def test_symbol_mode_and_quality_profile_defaults():
    install_market_analyzer_stubs()
    import market_analyzer

    assert_true(market_analyzer.SIGNAL_QUALITY_PROFILE in {"conservative", "balanced", "strict"}, "Unknown quality profile")
    assert_true(market_analyzer.MIN_SPOT_FINAL_SCORE >= 88, "Conservative spot threshold must preserve production behavior")
    assert_true(market_analyzer.MIN_FUTURES_FINAL_SCORE >= 90, "Conservative futures threshold must preserve production behavior")
    assert_true(market_analyzer.MAX_DYNAMIC_SYMBOLS == 120, "MAX_DYNAMIC_SYMBOLS default must be 120")
    assert_true(market_analyzer.MIN_DYNAMIC_SYMBOLS >= 20, "MIN_DYNAMIC_SYMBOLS default must protect against one-symbol scans")
    assert_true(market_analyzer.SINGLE_SYMBOL_MODE is False, "SINGLE_SYMBOL_MODE must be false by default")


def test_binance_us_exchange_info_ticker_gap_keeps_minimum_universe():
    install_market_analyzer_stubs()
    import market_analyzer

    original_safe_json = market_analyzer._safe_market_json
    original_cache = dict(market_analyzer.DYNAMIC_SYMBOL_CACHE)
    try:
        symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
            "DOGEUSDT", "TRXUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT",
            "BCHUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT", "OPUSDT",
            "HBARUSDT", "XLMUSDT", "ETCUSDT", "FILUSDT", "AAVEUSDT", "UNIUSDT",
            "SUIUSDT", "ICPUSDT", "FETUSDT", "TONUSDT",
        ]

        def fake_safe_json(url, timeout=12):
            if "binance.us/api/v3/exchangeInfo" in url:
                return {"symbols": [{"symbol": s, "status": "TRADING", "permissions": ["SPOT"]} for s in symbols]}, 200
            if "binance.us/api/v3/ticker/24hr" in url:
                return [{"symbol": "BTCUSDT", "quoteVolume": "999999999"}], 200
            return None, 451

        market_analyzer._safe_market_json = fake_safe_json
        market_analyzer.DYNAMIC_SYMBOL_CACHE["symbols"] = None
        selected = market_analyzer.get_scan_symbols(force_refresh=True)
        assert_true(len(selected) >= 20, f"Expected >=20 symbols, got {len(selected)}")
        assert_true("BTCUSDT" in selected and "ETHUSDT" in selected, "Core Binance US symbols missing")
    finally:
        market_analyzer._safe_market_json = original_safe_json
        market_analyzer.DYNAMIC_SYMBOL_CACHE.clear()
        market_analyzer.DYNAMIC_SYMBOL_CACHE.update(original_cache)


def main():
    test_forex_market_data_no_fake_output()
    test_forex_analyzer_provider_guard_is_present()
    test_delivery_routing_and_diagnostics()
    test_symbol_mode_and_quality_profile_defaults()
    test_binance_us_exchange_info_ticker_gap_keeps_minimum_universe()
    print("FOREX_ENGINE_AND_SIGNAL_SUPPLY_OK")


if __name__ == "__main__":
    main()
