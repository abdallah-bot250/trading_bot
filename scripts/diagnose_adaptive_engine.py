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
            price += 0.18
        elif mode == "bear":
            price -= 0.18
        elif mode == "breakout":
            price += 0.03
            if i > n - 8:
                price += 0.8
        else:
            price = 100 + ((i % 20) - 10) * 0.08
        open_ = price - 0.05
        close = price
        high = max(open_, close) + 0.35
        low = min(open_, close) - 0.35
        volume = 1000 + (i % 10) * 20
        if mode == "breakout" and i > n - 8:
            volume = 2200
        rows.append([i, open_, high, low, close, volume])
    return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])


def main():
    original_mtf = m.multi_timeframe_quality
    m.multi_timeframe_quality = lambda symbol, direction, interval, df: {
        "state": "CONFIRMED",
        "score": 15,
        "strong_conflict": False,
        "reason": "diagnostic confirmed",
    }
    try:
        bull = m.detect_symbol_market_regime("BTCUSDT", "15m", candles("bull"))
        bear = m.detect_symbol_market_regime("BTCUSDT", "15m", candles("bear"))
        rng = m.detect_symbol_market_regime("BTCUSDT", "15m", candles("range"))
        brk = m.detect_symbol_market_regime("BTCUSDT", "15m", candles("breakout"))

        assert bull["regime"] in {"BULL_TREND", "BREAKOUT"}, bull
        assert bear["regime"] in {"BEAR_TREND", "BREAKOUT"}, bear
        assert rng["regime"] in {"RANGE", "LOW_LIQUIDITY"}, rng
        assert brk["regime"] in {"BREAKOUT", "BULL_TREND"}, brk

        long_levels = m._candidate_levels(100, "LONG", {"support": 98, "resistance": 105}, 1.0)
        short_levels = m._candidate_levels(100, "SHORT", {"support": 95, "resistance": 102}, 1.0)
        assert long_levels["tp1"] > long_levels["entry"]
        assert long_levels["sl"] < long_levels["entry"]
        assert short_levels["tp1"] < short_levels["entry"]
        assert short_levels["sl"] > short_levels["entry"]
        print("ADAPTIVE_DIAGNOSTICS_OK")
    finally:
        m.multi_timeframe_quality = original_mtf


if __name__ == "__main__":
    main()
