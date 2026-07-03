import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import market_analyzer as m  # noqa: E402


def candles(mode, n=240):
    rows = []
    price = 100.0
    for i in range(n):
        if mode == "bull":
            price += 0.10 + (0.02 * math.sin(i / 6))
            spread = 0.55
            volume = 1200 + (i % 12) * 35
        elif mode == "bear":
            price -= 0.10 + (0.02 * math.sin(i / 6))
            spread = 0.55
            volume = 1200 + (i % 12) * 35
        elif mode == "low_volatility":
            price = 100 + math.sin(i / 8) * 0.015
            spread = 0.035
            volume = 1000 + (i % 5) * 5
        elif mode == "low_volume_chop":
            price = 100 + math.sin(i / 4) * 0.22
            spread = 0.42
            volume = 1200 if i < n - 70 else 260
        else:
            price = 100 + math.sin(i / 6) * 0.55
            spread = 0.45
            volume = 950 + (i % 8) * 20

        open_ = price - (spread * 0.18)
        close = price
        high = max(open_, close) + spread
        low = min(open_, close) - spread
        rows.append([i, open_, high, low, close, volume])
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])


def assert_rejection(label, result, expected):
    signal, reason, info = result
    assert signal is None, f"{label} should be NO_TRADE, got signal={signal}"
    text = f"{reason} {info.get('regime', '')} {info.get('reason', '')}".upper()
    assert expected in text, f"{label} expected {expected}, got reason={reason}, info={info}"


def diagnostic_signal():
    return {
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "direction": "LONG",
        "entry": 100.0,
        "tp": 103.0,
        "tp1": 101.2,
        "tp2": 102.0,
        "tp3": 103.0,
        "sl": 98.6,
        "support": 98.8,
        "nearest_support": 98.8,
        "resistance": 104.5,
        "nearest_resistance": 104.5,
        "atr": 0.75,
        "risk_reward": 2.1,
        "confidence": 84,
        "display_confidence": 82,
        "volume_score": 76,
        "volume_state": "STRONG",
        "risk_score": 34,
        "risk_level": "LOW",
        "multi_timeframe": "CONFIRMED",
        "multi_timeframe_score": 82,
    }


def main():
    originals = {
        "multi_timeframe_quality": m.multi_timeframe_quality,
        "expert_multi_timeframe_context": m.expert_multi_timeframe_context,
        "get_live_price": m.get_live_price,
        "_entry_manager_market_still_valid": m._entry_manager_market_still_valid,
        "detect_symbol_market_regime": m.detect_symbol_market_regime,
        "expert_volatility_state": m.expert_volatility_state,
        "high_impact_news_guard": m.high_impact_news_guard,
        "smart_money_entry_zone": m.smart_money_entry_zone,
        "trend_exhaustion_filter": m.trend_exhaustion_filter,
        "adaptive_learning_weight": m.adaptive_learning_weight,
    }

    try:
        m.multi_timeframe_quality = lambda symbol, direction, interval, df: {
            "state": "CONFIRMED",
            "score": 82,
            "strong_conflict": False,
            "reason": "diagnostic MTF confirmed",
        }

        bull_regime = m.detect_symbol_market_regime("BTCUSDT", "15m", candles("bull"))
        bear_regime = m.detect_symbol_market_regime("BTCUSDT", "15m", candles("bear"))
        known_states = {
            "STRONG_BULL",
            "WEAK_BULL",
            "STRONG_BEAR",
            "WEAK_BEAR",
            "BREAKOUT",
            "EXPANSION",
            "RANGE",
            "CONSOLIDATION",
            "ACCUMULATION",
            "DISTRIBUTION",
            "FAKE_BREAKOUT",
            "HIGH_VOLATILITY",
            "LOW_VOLATILITY",
            "LOW_VOLUME_CHOP",
            "LOW_LIQUIDITY",
        }
        assert bull_regime["regime"] in known_states, bull_regime
        assert bear_regime["regime"] in known_states, bear_regime
        print(f"MARKET_STATE_OK bull={bull_regime['regime']} bear={bear_regime['regime']}")

        low_vol_df = candles("low_volatility")
        assert_rejection(
            "LOW_VOLATILITY",
            m.build_adaptive_signal_candidate("BTCUSDT", "15m", low_vol_df, paid=True),
            "LOW_VOLATILITY",
        )

        m.detect_symbol_market_regime = lambda symbol, interval, df: {
            "regime": "LOW_VOLUME_CHOP",
            "reason": "diagnostic thin chop volume",
            "close": 100.0,
        }
        chop_df = candles("low_volume_chop")
        assert_rejection(
            "LOW_VOLUME_CHOP",
            m.build_adaptive_signal_candidate("BTCUSDT", "15m", chop_df, paid=True),
            "LOW_VOLUME_CHOP",
        )

        good_regime = {
            "regime": "STRONG_BULL",
            "reason": "diagnostic bullish setup",
            "close": 100.0,
            "ema20": 102.0,
            "ema50": 101.0,
            "ema200": 99.0,
            "rsi": 55,
            "atr": 0.8,
            "volume_ratio": 1.3,
            "volume_state": "STRONG",
            "volume_score": 78,
            "support": 98.5,
            "resistance": 104.0,
            "range_width": 0.025,
            "close_position": 0.55,
            "ema_spread": 0.03,
            "atr_relative": 1.0,
            "upper_wick_ratio": 0.12,
            "lower_wick_ratio": 0.18,
            "long_mtf": {"state": "CONFIRMED", "score": 82, "reason": "diagnostic"},
            "short_mtf": {"state": "CONFLICT", "score": 0, "reason": "diagnostic"},
        }
        m.detect_symbol_market_regime = lambda symbol, interval, df: dict(good_regime)
        m.expert_volatility_state = lambda df: {
            "state": "NORMAL_VOLATILITY",
            "ok": True,
            "reason": "diagnostic ATR tradable",
        }
        m.high_impact_news_guard = lambda: (True, "diagnostic no news")
        m.smart_money_entry_zone = lambda df, direction, regime_info: {
            "ok": True,
            "reason": "diagnostic break retest",
        }
        m.trend_exhaustion_filter = lambda df, direction: (False, "diagnostic not exhausted")
        m.adaptive_learning_weight = lambda strategy, symbol, timeframe, direction: (0, "diagnostic neutral learning")
        m.expert_multi_timeframe_context = lambda symbol, direction, current_df=None: {
            "state": "CONFLICT",
            "score": 0,
            "reason": "4H BULL conflicts with 1H BEAR",
        }
        assert_rejection(
            "MTF_CONFLICT",
            m.build_adaptive_signal_candidate("BTCUSDT", "15m", candles("bull"), paid=True),
            "MTF REJECTED",
        )
        print("NO_TRADE_FILTERS_OK low_volume_chop=True low_volatility=True mtf_conflict=True")

        quality_signal = diagnostic_signal()
        report, reason = m.build_signal_quality_report(quality_signal)
        assert report and reason is None, reason
        assert report["display_confidence"] >= 70, report
        weak_report, weak_reason = m.build_signal_quality_report({**quality_signal, "risk_reward": 1.2})
        assert weak_report is None and "below 1.5" in weak_reason, weak_reason
        print(
            "QUALITY_GATE_OK "
            f"display_conf={report['display_confidence']} final={report['final_score']} reject_low_rr=True"
        )

        m.get_live_price = lambda symbol: (100.04, "diagnostic")
        m.expert_multi_timeframe_context = lambda symbol, direction, current_df=None: {
            "state": "CONFIRMED",
            "score": 90,
            "reason": "diagnostic MTF confirmed",
        }
        m._entry_manager_market_still_valid = lambda symbol, direction, df, current_price: (
            True,
            "diagnostic market still valid",
        )
        managed, entry_reason = m.professional_entry_manager(diagnostic_signal(), candles("bull"))
        assert managed is not None, entry_reason
        assert managed.get("entry_manager", {}).get("updated") is True, managed
        assert float(managed["tp1"]) > float(managed["entry"]) > float(managed["sl"]), managed
        print(
            "ENTRY_MANAGER_OK "
            f"entry={managed['entry']} tp1={managed['tp1']} sl={managed['sl']} rr={managed['risk_reward']}"
        )

        print("ADAPTIVE_DIAGNOSTICS_OK")
    finally:
        for name, func in originals.items():
            setattr(m, name, func)


if __name__ == "__main__":
    main()
