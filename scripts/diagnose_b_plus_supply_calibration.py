import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FERNET_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from market_analyzer import apply_b_plus_calibration, classify_opportunity_tier
from auto_sender import qualified_opportunity_tier, valid_signal


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def base_signal(**overrides):
    signal = {
        "pair": "SOLUSDT",
        "symbol": "SOLUSDT",
        "direction": "LONG",
        "setup_lifecycle": "CONFIRMED",
        "setup_type": "range_edge_bounce",
        "strategy_name": "range_edge_bounce",
        "confidence": 63,
        "display_confidence": 63,
        "final_score": 82,
        "risk_reward": 1.7,
        "risk_score": 55,
        "entry": 100.0,
        "tp": 103.0,
        "sl": 98.0,
        "structure": "RANGE_EDGE",
        "market_regime": "RANGE",
        "liquidity_context": "NORMAL",
        "liquidity_reason": "sufficient liquidity",
        "entry_location_reason": "confirmed retest near support",
        "smart_money_reason": "retest confirmation",
        "signal_quality_reason": "confirmed range edge bounce",
    }
    signal.update(overrides)
    return signal


def main():
    safe = base_signal()
    ok, reason = apply_b_plus_calibration(safe)
    assert_true(ok, f"safe confirmed setup should calibrate: {reason}")
    assert_true(safe["quality_tier"] == "B_PLUS", "safe setup did not become B_PLUS")
    assert_true(classify_opportunity_tier(safe) == "B_PLUS", "market tier mismatch")
    assert_true(qualified_opportunity_tier(safe) == "B_PLUS", "delivery tier mismatch")
    assert_true(valid_signal(safe), "B_PLUS signal should pass valid_signal")

    cases = [
        ("low liquidity", base_signal(liquidity_context="LOW_LIQUIDITY")),
        ("fake breakout", base_signal(market_regime="FAKE_BREAKOUT", signal_quality_reason="FAKE_BREAKOUT risk")),
        ("mid range", base_signal(structure="MID_RANGE")),
        ("no entry confirmation", base_signal(smart_money_reason="no retest, pullback, liquidity sweep, order block, FVG, or S/R bounce")),
        ("bad rr", base_signal(risk_reward=1.2)),
        ("watchlist", base_signal(setup_lifecycle="WATCHING")),
    ]
    for label, signal in cases:
        ok, reason = apply_b_plus_calibration(signal)
        assert_true(not ok, f"{label} should be rejected, got {reason}")
        assert_true(classify_opportunity_tier(signal) != "B_PLUS", f"{label} should not become B_PLUS")

    print("B_PLUS_SUPPLY_CALIBRATION_OK")


if __name__ == "__main__":
    main()
