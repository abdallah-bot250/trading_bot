import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FERNET_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

from ai_model import explain_predict_trade  # noqa: E402
from auto_sender import is_qualified_opportunity, qualified_opportunity_tier, valid_signal  # noqa: E402
from market_analyzer import apply_b_plus_calibration, classify_opportunity_tier  # noqa: E402
from signal_quality_shared import safe_b_plus_eligibility  # noqa: E402


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def base_signal(**overrides):
    signal = {
        "pair": "SOLUSDT",
        "symbol": "SOLUSDT",
        "direction": "LONG",
        "setup_lifecycle": "CONFIRMED",
        "setup_type": "break_and_retest",
        "strategy_name": "break_and_retest",
        "confidence": 68,
        "display_confidence": 68,
        "final_score": 82,
        "risk_reward": 1.8,
        "risk_score": 55,
        "risk_level": "MEDIUM",
        "volume_state": "NORMAL",
        "volume_score": 62,
        "entry": 100.0,
        "tp": 103.6,
        "tp1": 103.6,
        "sl": 98.0,
        "structure": "RETEST",
        "market_regime": "BULL_TREND",
        "liquidity_context": "NORMAL",
        "liquidity_reason": "sufficient liquidity",
        "entry_location_reason": "confirmed retest near support",
        "smart_money_reason": "recent retest confirmation",
        "signal_quality_reason": "confirmed break and retest with safe room",
        "entry_confirmation_age_candles": 1,
        "expert_mtf": {"state": "CONFIRMED"},
    }
    signal.update(overrides)
    return signal


def main():
    safe = base_signal()
    ok, reason = apply_b_plus_calibration(safe)
    assert_true(ok, f"safe calibrated B+ should apply: {reason}")
    assert_true(safe_b_plus_eligibility(safe, allow_borderline_score=True)[0], "shared helper rejected safe B+")
    assert_true(classify_opportunity_tier(safe) == "B_PLUS", "market analyzer gate mismatch")
    ai_ok, ai_reason = explain_predict_trade(safe)
    assert_true(ai_ok, f"ai_model rejected safe B+: {ai_reason}")
    assert_true(qualified_opportunity_tier(safe) == "B_PLUS", "auto_sender tier mismatch")
    assert_true(is_qualified_opportunity(safe), "auto_sender qualified gate mismatch")
    assert_true(valid_signal(safe), "auto_sender valid_signal mismatch")

    uncalibrated = base_signal()
    assert_true(not safe_b_plus_eligibility(uncalibrated, allow_borderline_score=True)[0], "uncalibrated sub-70 passed helper")
    ai_ok, _ = explain_predict_trade(uncalibrated)
    assert_true(not ai_ok, "uncalibrated sub-70 passed ai_model")
    assert_true(not is_qualified_opportunity(uncalibrated), "uncalibrated sub-70 passed delivery qualification")

    high_risk = base_signal(risk_level="HIGH", risk_score=73)
    ok, _ = apply_b_plus_calibration(high_risk)
    assert_true(not ok, "HIGH-risk calibrated B+ was allowed")

    thin_volume = base_signal(volume_state="THIN", volume_score=40)
    ok, _ = apply_b_plus_calibration(thin_volume)
    assert_true(not ok, "THIN-volume calibrated B+ was allowed")

    auto_77 = base_signal(display_confidence=81, confidence=81, final_score=77, b_plus_calibrated=False)
    assert_true(classify_opportunity_tier(auto_77) != "B_PLUS", "final_score 77 auto-qualified in market analyzer")
    assert_true(qualified_opportunity_tier(auto_77) != "B_PLUS", "final_score 77 auto-qualified in auto_sender")

    print("B_PLUS_CONSISTENCY_OK")


if __name__ == "__main__":
    main()
