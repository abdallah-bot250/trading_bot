import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import auto_sender as au  # noqa: E402
import market_analyzer as ma  # noqa: E402


def assert_true(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"PASS {name}")


def _candle(ts, open_, high, low, close):
    return {"timestamp": ts, "open": open_, "high": high, "low": low, "close": close}


def test_spot_forensics():
    base = datetime(2026, 8, 12, 10, 0, 0)
    candles = [
        _candle(base + timedelta(minutes=i * 15), 100 + i * 0.05, 100.7 + i * 0.05, 99.4 + i * 0.03, 100.2 + i * 0.04)
        for i in range(20)
    ]
    candles.append(_candle(base + timedelta(minutes=300), 100.2, 103.0, 97.8, 102.2))
    atr = au._calculate_atr_from_candles(candles, 14)
    assert_true("SPOT ATR calculated", atr is not None and atr > 0)
    metrics = au._spot_trade_path_metrics(candles, "LONG", base.isoformat(), 100, 98, 102, 104, None)
    assert_true("SPOT same candle SL/TP ambiguous", metrics["same_candle_ambiguous"] is True)
    classification = au._classify_spot_loss(metrics, atr, 0.7, "trend_pullback", "BULL")
    assert_true("SPOT ambiguous classification", classification == "AMBIGUOUS_INTRABAR_ORDER")

    normal_loss_metrics = {
        "same_candle_ambiguous": False,
        "sl_before_later_target": False,
        "sl_time": base,
        "tp1_time": None,
    }
    assert_true(
        "SPOT suitable SL remains valid loss",
        au._classify_spot_loss(normal_loss_metrics, atr, 1.6, "trend_pullback", "BULL") == "NORMAL_VALID_LOSS",
    )
    assert_true(
        "SPOT noise SL classification",
        au._classify_spot_loss({"same_candle_ambiguous": False, "sl_before_later_target": True}, atr, 0.6, "trend_pullback", "BULL") == "STOP_INSIDE_NORMAL_NOISE",
    )
    entry = 100.0
    tp1 = 102.0
    widened_sl = 98.9
    recalculated_rr = abs(tp1 - entry) / abs(entry - widened_sl)
    assert_true("SPOT wider SL preserves RR when above minimum", recalculated_rr >= 1.5)
    too_wide_sl = 98.5
    rejected_rr = abs(tp1 - entry) / abs(entry - too_wide_sl)
    assert_true("SPOT wider SL below minimum would reject", rejected_rr < 1.5)


def test_futures_provider_okx_primary():
    original_fetch = ma._fetch_futures_json
    original_order = ma._futures_provider_order
    ma.FUTURES_PROVIDER_CYCLE_LOCK.clear()
    ma.FUTURES_PROVIDER_HEALTH_CACHE.clear()
    ma.SIGNAL_SCAN_DIAGNOSTICS.clear()
    ma.SIGNAL_SCAN_DIAGNOSTICS["scan_cycle_id"] = "stabilization-okx-cycle"

    def fake_fetch(provider, endpoint, url, fallback_used=False):
        provider = str(provider).upper()
        if provider == "BINANCE_FUTURES":
            return None, 451, "blocked", None
        if provider == "BYBIT":
            return None, 403, "forbidden", None
        if provider == "OKX" and endpoint == "exchangeInfo":
            return {"data": [{"instId": "ARC-USDT-SWAP", "state": "live"}]}, 200, "ok", None
        if provider == "OKX" and endpoint == "ticker/24hr":
            return {"data": [{"instId": "ARC-USDT-SWAP", "last": "1"}]}, 200, "ok", None
        if provider == "OKX" and endpoint == "klines":
            rows = []
            now = 1800000000
            for i in range(8):
                rows.append([now + i * 900000, "1", "1.2", "0.9", "1.1", "100"])
            return {"data": rows}, 200, "ok", None
        return None, 500, "unexpected", None

    try:
        ma._fetch_futures_json = fake_fetch
        ma._futures_provider_order = lambda: ["BINANCE_FUTURES", "BYBIT", "OKX", "KUCOIN_FUTURES"]
        df = ma.get_futures_market_data("ARCUSDT", "15m", limit=5)
        assert_true("FUTURES OKX selected when valid candles exist", df is not None and not df.empty)
        provider = str(df.get("futures_data_provider", [""])[0])
        assert_true("FUTURES OKX remains active provider", provider == "OKX")
    finally:
        ma._fetch_futures_json = original_fetch
        ma._futures_provider_order = original_order
        ma.FUTURES_PROVIDER_CYCLE_LOCK.clear()
        ma.FUTURES_PROVIDER_HEALTH_CACHE.clear()
        ma.SIGNAL_SCAN_DIAGNOSTICS.clear()


def test_futures_provider_fallback():
    original_fetch = ma._fetch_futures_json
    original_order = ma._futures_provider_order
    ma.FUTURES_PROVIDER_CYCLE_LOCK.clear()
    ma.FUTURES_PROVIDER_HEALTH_CACHE.clear()
    ma.SIGNAL_SCAN_DIAGNOSTICS.clear()
    ma.SIGNAL_SCAN_DIAGNOSTICS["scan_cycle_id"] = "stabilization-cycle"

    def fake_fetch(provider, endpoint, url, fallback_used=False):
        provider = str(provider).upper()
        if provider == "BINANCE_FUTURES":
            return None, 451, "blocked", None
        if provider == "BYBIT":
            return None, 403, "forbidden", None
        if provider == "OKX" and endpoint == "exchangeInfo":
            return {"data": [{"instId": "ARC-USDT-SWAP", "state": "live"}]}, 200, "ok", None
        if provider == "OKX" and endpoint == "ticker/24hr":
            return {"data": [{"instId": "ARC-USDT-SWAP", "last": "1"}]}, 200, "ok", None
        if provider == "OKX" and endpoint == "klines":
            return {"data": []}, 200, "empty", None
        if provider == "KUCOIN_FUTURES" and endpoint == "exchangeInfo":
            return {"data": [{"symbol": "ARCUSDTM", "status": "Open"}]}, 200, "ok", None
        if provider == "KUCOIN_FUTURES" and endpoint == "ticker/24hr":
            return {"data": {"symbol": "ARCUSDTM", "price": "1"}}, 200, "ok", None
        if provider == "KUCOIN_FUTURES" and endpoint == "klines":
            rows = []
            now = 1800000000
            for i in range(8):
                rows.append([now + i * 900, "1", "1.2", "0.9", "1.1", "100"])
            return {"data": rows}, 200, "ok", None
        return None, 500, "unexpected", None

    try:
        ma._fetch_futures_json = fake_fetch
        ma._futures_provider_order = lambda: ["BINANCE_FUTURES", "BYBIT", "OKX", "KUCOIN_FUTURES"]
        df = ma.get_futures_market_data("ARCUSDT", "15m", limit=5)
        assert_true("FUTURES falls back after OKX empty symbol candles", df is not None and not df.empty)
        provider = str(df.get("futures_data_provider", [""])[0])
        assert_true("FUTURES KuCoin futures selected per symbol", provider == "KUCOIN_FUTURES")
    finally:
        ma._fetch_futures_json = original_fetch
        ma._futures_provider_order = original_order
        ma.FUTURES_PROVIDER_CYCLE_LOCK.clear()
        ma.FUTURES_PROVIDER_HEALTH_CACHE.clear()
        ma.SIGNAL_SCAN_DIAGNOSTICS.clear()


def test_final_approval_modes():
    normal = {
        "pair": "TESTUSDT",
        "direction": "LONG",
        "entry": 100,
        "tp": 104,
        "sl": 98,
        "risk_reward": 2.0,
        "display_confidence": 82,
        "confidence": 82,
        "playbook_confidence": 86,
        "setup_confirmed": True,
        "risk_level": "LOW",
        "volume_state": "NORMAL",
        "expert_mtf": {"state": "CONFIRMED", "reason": "strict"},
    }
    decision = ma.evaluate_final_approval_mode(normal)
    assert_true("FUTURES normal approval valid signal", decision["approval_type"] == "NORMAL_APPROVAL")

    reduced = dict(normal, display_confidence=72, confidence=72, risk_level="HIGH")
    decision = ma.evaluate_final_approval_mode(reduced)
    assert_true("FUTURES reduced approval soft risk", decision["approval_type"] == "REDUCED_SIZE_APPROVAL")

    hard_mtf = dict(normal, expert_mtf={"state": "HARD_CONFLICT", "reason": "hard_conflict"})
    decision = ma.evaluate_final_approval_mode(hard_mtf)
    assert_true("FUTURES hard MTF conflict rejects", decision["approval_type"] == "REJECT")

    invalid = dict(normal, tp=96)
    decision = ma.evaluate_final_approval_mode(invalid)
    assert_true("FUTURES invalid geometry rejects", decision["approval_type"] == "REJECT")

    stale = dict(normal, stale_entry=True)
    decision = ma.evaluate_final_approval_mode(stale)
    assert_true("FUTURES stale entry rejects", decision["approval_type"] == "REJECT")


def main():
    test_spot_forensics()
    test_futures_provider_okx_primary()
    test_futures_provider_fallback()
    test_final_approval_modes()
    print("SPOT_FUTURES_STABILIZATION_DIAGNOSTICS_OK")


if __name__ == "__main__":
    main()
