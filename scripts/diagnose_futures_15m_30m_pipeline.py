import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import market_analyzer as ma  # noqa: E402


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def candles(direction="up", rows=260, start=100.0, step=0.10, impulse=False, flat=False):
    data = []
    price = start
    for i in range(rows):
        if flat:
            drift = 0.01 if i % 2 == 0 else -0.01
        else:
            drift = step if direction == "up" else -step
        open_ = price
        close = max(0.1, price + drift)
        spread = 0.28 if not impulse or i < rows - 1 else 4.0
        high = max(open_, close) + spread
        low = min(open_, close) - spread
        volume = 1000 + (i % 17) * 15
        data.append({"time": i, "open": open_, "high": high, "low": low, "close": close, "volume": volume})
        price = close
    return pd.DataFrame(data)


def range_fixture(last_open, last_high, last_low, last_close, rows=110, previous_high=100.0, previous_low=90.0):
    data = []
    for i in range(rows - 1):
        close = 95.0 + (0.05 if i % 2 == 0 else -0.05)
        data.append({
            "time": i,
            "open": 95.0,
            "high": previous_high - 0.15 if i < rows - 2 else previous_high,
            "low": previous_low + 0.15 if i < rows - 2 else previous_low,
            "close": close,
            "volume": 3000 + i,
        })
    data.append({"time": rows - 1, "open": last_open, "high": last_high, "low": last_low, "close": last_close, "volume": 5000})
    return pd.DataFrame(data)


def fake_cache_factory(frames):
    def fake_cached(symbol, interval="5m", limit=250, ttl=None):
        return frames.get(interval)
    return fake_cached


def run():
    original_cache = ma.cached_market_data
    original_futures_cache = ma.cached_futures_market_data
    try:
        bull_4h = candles("up", start=100, step=0.18)
        bull_1h = candles("up", start=105, step=0.12)
        bear_4h = candles("down", start=140, step=0.18)
        bear_1h = candles("down", start=135, step=0.12)
        setup_30m_up = candles("up", start=110, step=0.06)
        trigger_15m_up = candles("up", start=113, step=0.04)
        setup_30m_down = candles("down", start=130, step=0.06)
        trigger_15m_down = candles("down", start=127, step=0.04)

        ma.cached_market_data = fake_cache_factory({
            "4h": bull_4h,
            "1h": bull_1h,
            "30m": setup_30m_up,
            "15m": trigger_15m_up,
        })
        ma.cached_futures_market_data = fake_cache_factory({
            "4h": bull_4h,
            "1h": bull_1h,
            "30m": setup_30m_up,
            "15m": trigger_15m_up,
        })
        bias = ma.futures_bias_context("BTCUSDT")
        assert_true(bias["ok"] and bias["macro"] == "BULL", "4H/1H bullish bias should be valid")
        setup = ma.futures_setup_context("BTCUSDT", "LONG", "BULL", setup_30m_up)
        assert_true(setup["ok"] or setup["stage"] == "ARMED", "30m bullish setup should evaluate without 5m")
        trigger = ma.futures_trigger_context("BTCUSDT", "LONG", trigger_15m_up, {"support": None, "resistance": None})
        assert_true(trigger["ok"] or trigger["stage"] in {"ARMED", "INVALIDATED"}, "15m trigger should evaluate without 5m")

        ma.cached_market_data = fake_cache_factory({
            "4h": bear_4h,
            "1h": bear_1h,
            "30m": setup_30m_down,
            "15m": trigger_15m_down,
        })
        ma.cached_futures_market_data = fake_cache_factory({
            "4h": bear_4h,
            "1h": bear_1h,
            "30m": setup_30m_down,
            "15m": trigger_15m_down,
        })
        bias = ma.futures_bias_context("ETHUSDT")
        assert_true(bias["ok"] and bias["macro"] == "BEAR", "4H/1H bearish bias should be valid")

        armed = ma.futures_trigger_context("SOLUSDT", "LONG", candles("down", start=100, step=0.01, flat=True), {"support": 99, "resistance": 104})
        assert_true(armed["stage"] in {"ARMED", "INVALIDATED"}, "Setup without clean trigger must not become a final signal")

        no_setup = ma.futures_setup_context("BNBUSDT", "LONG", "BULL", candles("up", start=100, step=0.001, flat=True))
        assert_true(not no_setup["ok"], "Trigger without a valid 30m setup must be rejected/armed")

        long_breakout_df = range_fixture(99.5, 103.0, 99.8, 102.0)
        context = ma._futures_level_context(long_breakout_df)
        assert_true(context["previous_range_high"] == 100.0, "Previous range high must exclude current candle")
        assert_true(context["recent_high"] == 103.0, "Recent high may include current candle for context")
        assert_true(long_breakout_df["close"].iloc[-1] > context["previous_range_high"], "LONG breakout can be detected against previous high")

        long_sweep_df = range_fixture(91.0, 94.0, 89.4, 92.4)
        context = ma._futures_level_context(long_sweep_df)
        assert_true(context["previous_range_low"] == 90.0, "Previous range low must exclude current candle")
        assert_true(long_sweep_df["low"].iloc[-1] < context["previous_range_low"] and long_sweep_df["close"].iloc[-1] > context["previous_range_low"], "LONG sweep/reclaim can be detected")

        short_breakdown_df = range_fixture(90.5, 91.2, 87.8, 88.8)
        context = ma._futures_level_context(short_breakdown_df)
        assert_true(short_breakdown_df["close"].iloc[-1] < context["previous_range_low"], "SHORT breakdown can be detected against previous low")

        short_sweep_df = range_fixture(99.0, 101.4, 96.0, 98.7)
        context = ma._futures_level_context(short_sweep_df)
        assert_true(short_sweep_df["high"].iloc[-1] > context["previous_range_high"] and short_sweep_df["close"].iloc[-1] < context["previous_range_high"], "SHORT sweep/rejection can be detected")

        no_breakout_df = range_fixture(98.5, 99.6, 94.0, 99.2)
        context = ma._futures_level_context(no_breakout_df)
        assert_true(not (no_breakout_df["close"].iloc[-1] > context["previous_range_high"]), "No false breakout when prior level is not broken")

        conflict_cache = fake_cache_factory({
            "4h": bull_4h,
            "1h": bear_1h,
            "30m": setup_30m_up,
            "15m": trigger_15m_up,
        })
        ma.cached_market_data = conflict_cache
        ma.cached_futures_market_data = conflict_cache
        conflict = ma.futures_bias_context("XRPUSDT")
        assert_true(not conflict["ok"] and "conflict" in conflict["reason"].lower(), "MTF conflict must reject")

        impulse_trigger = ma.futures_trigger_context("AVAXUSDT", "LONG", candles("up", start=100, step=0.02, impulse=True), {"support": 99, "resistance": 102})
        assert_true(not impulse_trigger["ok"], "Large impulse candle before entry must be rejected")

        sample_signal = {
            "type": "FUTURES",
            "pair": "BTCUSDT",
            "direction": "LONG",
            "entry": 100,
            "tp1": 101,
            "tp": 102,
            "sl": 99,
        }
        ma.cached_market_data = fake_cache_factory({
            "4h": bull_4h,
            "1h": bull_1h,
            "30m": setup_30m_up,
            "15m": trigger_15m_up,
        })
        ma.cached_futures_market_data = fake_cache_factory({
            "4h": bull_4h,
            "1h": bull_1h,
            "30m": setup_30m_up,
            "15m": trigger_15m_up,
        })
        rebuilt, reason = ma.futures_apply_execution_frames(sample_signal)
        if rebuilt:
            assert_true(rebuilt["timeframe"] == "15m", "Final Futures signal must use 15m trigger timeframe")
            assert_true("5m" not in str(rebuilt.get("decision_timeframes", "")), "5m must not be in final Futures decision frames")
            assert_true(float(rebuilt["risk_reward"]) >= ma.FUTURES_MIN_RR, "Futures RR must meet minimum")
        else:
            assert_true(reason, "Futures validator must return a clear rejection reason")

        assert_true(ma.TIMEFRAMES == ["15m", "30m", "1h"], "Scanner must not use 5m for final Futures issue path")
        type_scores = ma.evaluate_trade_types("LONG", "UP", "STRONG_BULL", 86, True, "BULLISH_STRUCTURE", "STRONG", "TRADEABLE", 35, "30m")
        selected, adjusted = ma.choose_trade_type(type_scores)
        assert_true(adjusted.get("FUTURES", 0) >= 55, "Futures LONG remains reachable through type scoring when setup is strong")
        print("FUTURES_15M_30M_PIPELINE_OK")
    finally:
        ma.cached_market_data = original_cache
        ma.cached_futures_market_data = original_futures_cache


if __name__ == "__main__":
    run()
