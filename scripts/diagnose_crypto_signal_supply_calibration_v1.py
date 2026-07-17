import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import market_analyzer as ma


def _candles(direction="up", rows=40, open_last=False, low_volume=False):
    data = []
    price = 100.0
    for i in range(rows):
        if direction == "up":
            open_price = price
            close = price + 0.35
        elif direction == "down":
            open_price = price
            close = price - 0.35
        else:
            open_price = price
            close = price + (0.1 if i % 2 == 0 else -0.1)
        high = max(open_price, close) + 0.35
        low = min(open_price, close) - 0.35
        volume = 10 if low_volume else 1000
        data.append({
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": volume * close,
            "complete": True,
        })
        price = close
    if open_last:
        data[-1]["complete"] = False
        data[-1]["volume"] = 1
        data[-1]["quote_volume"] = 1
    return pd.DataFrame(data)


def _mtf(major, confirm, setup, trigger, state=None):
    if state is None:
        if major == confirm == "BULL":
            state = "BULL_CONFIRMED"
        elif major == confirm == "BEAR":
            state = "BEAR_CONFIRMED"
        elif major in {"BULL", "BEAR"} and confirm == "RANGE":
            state = "SOFT_CONFLICT"
        elif major == "RANGE" and confirm in {"BULL", "BEAR"}:
            state = "RANGE_WITH_LOWER_TF_TREND"
        else:
            state = "HARD_CONFLICT"
    return {
        "state": state,
        "major": major,
        "confirm": confirm,
        "reason": f"4H {major} 1H {confirm}",
        "frames": {
            ma.FUTURES_SETUP_TIMEFRAME: {"direction": setup, "available": True},
            ma.FUTURES_TRIGGER_TIMEFRAME: {"direction": trigger, "available": True},
        },
    }


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    long_b_plus = ma.b_plus_mtf_path_context(_mtf("BULL", "RANGE", "BULL", "BULL"), "LONG")
    assert_true(long_b_plus["ok"], "4H BULL + 1H RANGE + valid 30m/15m LONG should be B+ allowed")
    soft_signal = {"b_plus_mtf_path": True, "display_confidence": 91, "final_score": 95, "risk_reward": 2.0}
    assert_true(ma.classify_opportunity_tier(soft_signal) == "B_PLUS", "soft alignment must classify B+ only")

    short_b_plus = ma.b_plus_mtf_path_context(_mtf("BEAR", "RANGE", "BEAR", "BEAR"), "SHORT")
    assert_true(short_b_plus["ok"], "4H BEAR + 1H RANGE + valid trigger should be B+ allowed")

    hard_conflict = ma.b_plus_mtf_path_context(_mtf("BULL", "BEAR", "BULL", "BULL", "HARD_CONFLICT"), "LONG")
    assert_true(not hard_conflict["ok"], "4H BULL + 1H BEAR must be rejected")

    macro_range = ma.b_plus_mtf_path_context(_mtf("RANGE", "BULL", "BULL", "BULL"), "LONG")
    assert_true(macro_range["ok"], "4H RANGE + 1H directional with matching setup should be allowed")
    strict_signal = {"display_confidence": 90, "final_score": 94, "risk_reward": 2.0, "quality_checklist_score": 92}
    assert_true(ma.classify_opportunity_tier(strict_signal) == "A_PLUS", "strict alignment can still classify A/A+")

    df = _candles("up", 35)
    recent_idx = len(df) - 3
    prev_high = df.loc[recent_idx - 1, "high"]
    df.loc[recent_idx, "low"] = prev_high - 0.05
    df.loc[recent_idx, "close"] = prev_high + 0.45
    regime = {
        "close": float(df["close"].iloc[-2]),
        "atr": 1.2,
        "support": float(df["low"].tail(10).min()),
        "resistance": float(df["high"].tail(10).max()) + 10,
        "recent_high": float(df["high"].tail(20).max()),
        "recent_low": float(df["low"].tail(20).min()),
        "regime": "STRONG_BULL",
    }
    entry = ma.smart_money_entry_zone(df, "LONG", regime)
    assert_true(entry["ok"], "recent retest 2 candles ago should be allowed")
    assert_true(entry.get("entry_confirmation_age_candles") <= 2, "entry confirmation age should be logged")
    timing_ok, _timing_reason = ma.late_entry_after_confirmation_guard(df, "LONG", regime, entry)
    assert_true(timing_ok, "fresh recent retest should pass late-entry guard")

    stale_df = _candles("up", 35)
    stale_idx = len(stale_df) - 5
    prev_high = stale_df.loc[stale_idx - 1, "high"]
    stale_df.loc[stale_idx, "low"] = prev_high - 0.05
    stale_df.loc[stale_idx, "close"] = prev_high + 0.45
    stale_entry = ma.smart_money_entry_zone(stale_df, "LONG", regime)
    assert_true(not stale_entry["ok"], "retest stale beyond allowed window should be rejected")
    stale_timing, stale_reason = ma.late_entry_after_confirmation_guard(stale_df, "LONG", regime, {"entry_confirmation_age_candles": 3})
    assert_true(not stale_timing and "ENTRY_STALE" in stale_reason, "age 3 confirmation should be ENTRY_STALE")

    volume_df = _candles("up", 30, open_last=True, low_volume=False)
    volume_profile = ma.robust_volume_profile(volume_df)
    assert_true(volume_profile["volume_state"] != "THIN", "open candle volume must not cause LOW_LIQUIDITY")
    assert_true(volume_profile.get("candle_closed") is True, "volume profile should use closed candle")

    thin_df = _candles("up", 30, open_last=False, low_volume=False)
    thin_df.loc[29, "volume"] = 1
    thin_df.loc[29, "quote_volume"] = 1
    thin_profile = ma.robust_volume_profile(thin_df)
    assert_true(thin_profile["volume_state"] == "THIN", "true low liquidity should remain rejected")
    missing_profile = ma.robust_volume_profile(pd.DataFrame([{"open": 1, "high": 1, "low": 1, "close": 1, "volume": 0}]))
    assert_true(missing_profile["volume_state"] == "THIN", "missing/zero volume should fail closed")

    aa_mtf = ma.b_plus_mtf_path_context(_mtf("BULL", "BULL", "BULL", "BULL"), "LONG")
    assert_true(not aa_mtf["ok"], "A/A+ strict MTF path should remain outside B+ helper")

    late_df = _candles("up", 60)
    late_df.loc[len(late_df) - 1, "open"] = late_df.loc[len(late_df) - 2, "close"] * 1.04
    late_df.loc[len(late_df) - 1, "close"] = late_df.loc[len(late_df) - 2, "close"] * 1.08
    late_df.loc[len(late_df) - 1, "high"] = late_df.loc[len(late_df) - 1, "close"] * 1.01
    late_df.loc[len(late_df) - 1, "low"] = late_df.loc[len(late_df) - 2, "close"] * 1.03
    late, _reason = ma.trend_exhaustion_filter(late_df, "LONG")
    assert_true(late, "late/extended entry should remain rejected")
    late_guard_ok, late_guard_reason = ma.late_entry_after_confirmation_guard(
        late_df,
        "LONG",
        {"close": float(late_df["close"].iloc[-1]), "atr": 0.5},
        {"entry_confirmation_age_candles": 2},
    )
    assert_true(not late_guard_ok and "LATE_ENTRY" in late_guard_reason, "late entry after retest should be rejected")

    print("CRYPTO_SIGNAL_SUPPLY_CALIBRATION_DIAGNOSTICS_OK")


if __name__ == "__main__":
    main()
