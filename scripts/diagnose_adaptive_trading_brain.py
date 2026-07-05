import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import market_analyzer as m  # noqa: E402


def candles(mode="range", n=240):
    rows = []
    price = 100.0
    for i in range(n):
        if mode == "bull":
            price += 0.08 + math.sin(i / 8) * 0.015
            spread = 0.55
            volume = 1300 + (i % 10) * 30
        elif mode == "bear":
            price -= 0.08 + math.sin(i / 8) * 0.015
            spread = 0.55
            volume = 1300 + (i % 10) * 30
        elif mode == "low_volume_chop":
            price = 100 + math.sin(i / 4) * 0.18
            spread = 0.30
            volume = 180 if i > n - 80 else 900
        else:
            price = 100 + math.sin(i / 9) * 1.0
            spread = 0.35
            volume = 900 + (i % 8) * 10
        open_ = price - spread * 0.15
        close = price
        high = max(open_, close) + spread
        low = min(open_, close) - spread
        rows.append([i, open_, high, low, close, volume])
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])


def regime(close_position=0.5, name="RANGE"):
    close = 100.0
    return {
        "regime": name,
        "reason": f"diagnostic {name}",
        "close": close,
        "ema20": 101,
        "ema50": 100,
        "ema200": 99,
        "rsi": 42 if close_position <= 0.2 else 58 if close_position >= 0.8 else 50,
        "atr": 0.7,
        "atr_ratio": 0.007,
        "volume_ratio": 1.1,
        "volume_state": "NORMAL",
        "volume_score": 62,
        "support": 98.0,
        "resistance": 104.0,
        "recent_high": 104.0,
        "recent_low": 98.0,
        "range_width": 0.06,
        "close_position": close_position,
        "ema_spread": 0.02,
        "atr_relative": 1.0,
        "body_ratio": 0.35,
        "upper_wick_ratio": 0.2,
        "lower_wick_ratio": 0.48 if close_position <= 0.2 else 0.2,
        "long_mtf": {"state": "CONFIRMED", "score": 85, "reason": "diagnostic"},
        "short_mtf": {"state": "CONFIRMED", "score": 85, "reason": "diagnostic"},
    }


def main():
    originals = {
        "adaptive_mtf_playbook_context": m.adaptive_mtf_playbook_context,
        "btc_market_context": m.btc_market_context,
        "expert_multi_timeframe_context": m.expert_multi_timeframe_context,
        "expert_volatility_state": m.expert_volatility_state,
        "high_impact_news_guard": m.high_impact_news_guard,
        "smart_money_entry_zone": m.smart_money_entry_zone,
        "trend_exhaustion_filter": m.trend_exhaustion_filter,
        "detect_symbol_market_regime": m.detect_symbol_market_regime,
        "adaptive_learning_weight": m.adaptive_learning_weight,
        "_candidate_levels": m._candidate_levels,
    }
    try:
        range_mtf = lambda *a, **k: {"state": "RANGE_CONFIRMED", "reason": "diagnostic range", "major": "RANGE", "confirm": "RANGE", "frames": {}}
        bull_mtf = lambda *a, **k: {"state": "BULL_CONFIRMED", "reason": "diagnostic bull", "major": "BULL", "confirm": "BULL", "frames": {}}
        hard_conflict = lambda *a, **k: {"state": "HARD_CONFLICT", "reason": "4H BULL conflicts with 1H BEAR", "major": "BULL", "confirm": "BEAR", "frames": {}}
        m.btc_market_context = lambda: {"btc_context": "STRONG_BULL", "btc_risk_mode": "NORMAL", "btc_alignment_score": 70}
        m.expert_volatility_state = lambda df: {"state": "NORMAL_VOLATILITY", "ok": True, "reason": "diagnostic ATR tradable"}
        m.high_impact_news_guard = lambda: (True, "no high impact news diagnostic")
        m.smart_money_entry_zone = lambda df, direction, info: {"ok": True, "setup": "Break + Retest" if info.get("regime") in ["BREAKOUT", "EXPANSION"] else "Bounce from Support", "reason": "diagnostic smart entry"}
        m.trend_exhaustion_filter = lambda df, direction: (False, "diagnostic not exhausted")
        m.adaptive_learning_weight = lambda strategy, symbol, timeframe, direction: (0, "diagnostic neutral")

        m.adaptive_mtf_playbook_context = range_mtf
        edge = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.12), {"liquidity_score": 60, "rejection_wick": True}, m.btc_market_context())
        assert edge.get("ok") and edge.get("strategy_name") == "range_edge_bounce", edge
        mid = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.50), {"liquidity_score": 60}, m.btc_market_context())
        assert not mid.get("ok") and "mid-range" in mid.get("reason", ""), mid
        print("RANGE_EDGE_OK")

        fake = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.5, "FAKE_BREAKOUT"), {"liquidity_score": 30}, m.btc_market_context())
        assert not fake.get("ok"), fake
        low_chop = m.adaptive_market_playbook("BTCUSDT", "15m", candles("low_volume_chop"), regime(0.5, "LOW_VOLUME_CHOP"), {"liquidity_score": 25}, m.btc_market_context())
        assert not low_chop.get("ok") and low_chop.get("stage") == "WATCHING", low_chop
        print("NO_TRADE_PLAYBOOKS_OK")

        accum_wait = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.16, "ACCUMULATION"), {"liquidity_score": 55}, m.btc_market_context())
        assert not accum_wait.get("ok"), accum_wait
        accum = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.16, "ACCUMULATION"), {"liquidity_score": 78, "liquidity_sweep": True, "reclaim_after_sweep": True}, m.btc_market_context())
        assert accum.get("ok") and accum.get("direction") == "LONG", accum
        print("ACCUMULATION_RECLAIM_OK")

        m.adaptive_mtf_playbook_context = hard_conflict
        conflict = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.2, "STRONG_BULL"), {"liquidity_score": 70}, m.btc_market_context())
        assert not conflict.get("ok") and "MTF" in conflict.get("reason", ""), conflict
        print("MTF_CONFLICT_OK")

        risk = m.adaptive_dynamic_risk_brain(regime(0.2, "STRONG_BULL"), {"btc_risk_mode": "DEFENSIVE"}, {"liquidity_score": 70}, {"state": "BULL_CONFIRMED"})
        assert risk.get("risk_mode") == "DEFENSIVE", risk
        sig_a = {"pair": "ETHUSDT", "direction": "LONG", "display_confidence": 82, "volume_score": 80, "btc_alignment_score": 35}
        sig_b = {"pair": "ETHUSDT", "direction": "LONG", "display_confidence": 82, "volume_score": 80, "btc_alignment_score": 75}
        m.relative_strength_context("ETHUSDT", sig_a)
        m.relative_strength_context("ETHUSDT", sig_b)
        assert sig_b["relative_strength_score"] > sig_a["relative_strength_score"], (sig_a, sig_b)
        assert "entry" not in sig_a and "tp" not in sig_a, sig_a
        print("BTC_AND_RELATIVE_STRENGTH_OK")

        m.adaptive_mtf_playbook_context = range_mtf
        m.ADAPTIVE_WATCHLIST.clear()
        _ = m.adaptive_market_playbook("BTCUSDT", "15m", candles(), regime(0.5), {"liquidity_score": 60}, m.btc_market_context())
        assert m.ADAPTIVE_WATCHLIST and "entry" not in m.ADAPTIVE_WATCHLIST[-1], m.ADAPTIVE_WATCHLIST
        print("WATCHLIST_NO_SIGNAL_OK")

        m.adaptive_mtf_playbook_context = bull_mtf
        m.expert_multi_timeframe_context = lambda *a, **k: {"state": "CONFIRMED", "score": 90, "reason": "diagnostic confirmed"}
        m.detect_symbol_market_regime = lambda *a, **k: regime(0.24, "STRONG_BULL")
        m._candidate_levels = lambda entry, direction, info, atr_val, rr_min=1.5: {
            "entry": 100.0, "sl": 98.5, "tp": 103.0, "tp1": 101.2,
            "tp2": 102.1, "tp3": 103.0, "risk_reward": 2.0,
            "support": 98.0, "resistance": 104.0,
        }
        signal, reason, info = m.build_adaptive_signal_candidate("BTCUSDT", "15m", candles("bull"), paid=True)
        assert signal is not None, (reason, info)
        assert signal["direction"] == "LONG" and signal.get("adaptive_playbook") == "STRONG_TREND", signal
        assert signal.get("opportunity_score", 0) > 0, signal
        print("CONFIRMED_CANDIDATE_OK")

        print("ADAPTIVE_TRADING_BRAIN_OK")
    finally:
        for name, func in originals.items():
            setattr(m, name, func)


if __name__ == "__main__":
    main()
