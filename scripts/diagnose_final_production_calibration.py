import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_model import explain_predict_trade
from market_analyzer import _select_final_delivery_candidates


def base_signal(**overrides):
    signal = {
        "pair": "TESTUSDT",
        "timeframe": "15m",
        "direction": "LONG",
        "entry": 100,
        "tp": 104,
        "tp1": 102,
        "sl": 98,
        "risk_reward": 2.0,
        "confidence": 72,
        "display_confidence": 72,
        "playbook_confidence": 83,
        "risk_level": "HIGH",
        "risk_score": 70,
        "volume_state": "NORMAL",
        "volume_score": 60,
        "strategy_name": "trend_pullback_continuation",
        "setup_type": "trend_pullback_continuation",
        "setup_confirmed": True,
        "expert_mtf": {"state": "CONFIRMED", "reason": "strict alignment"},
        "structure": "BULLISH_STRUCTURE",
        "trend_power": "WEAK_BULL",
    }
    signal.update(overrides)
    return signal


def assert_true(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"PASS {name}")


def main():
    sig = base_signal(confidence_cap_reason="high_risk_cap")
    ok, reason = explain_predict_trade(sig)
    assert_true("duplicate high-risk penalty becomes reduced approval", ok and sig.get("approval_type") == "REDUCED_SIZE_APPROVAL")
    assert_true("reduced size multiplier is 50 percent", sig.get("size_multiplier") == 0.5)

    sig = base_signal(display_confidence=72, confidence=72, risk_level="HIGH")
    ok, reason = explain_predict_trade(sig)
    assert_true("final confidence 72 high risk no hard reject passes reduced", ok and "REDUCED_SIZE" in reason)

    sig = base_signal(display_confidence=68, confidence=68)
    ok, reason = explain_predict_trade(sig)
    assert_true("final confidence 68 rejects", not ok and "below 70" in reason)

    sig = base_signal(tp=96, tp1=96)
    ok, reason = explain_predict_trade(sig)
    assert_true("invalid LONG geometry rejects", not ok and "geometry" in reason)

    sig = base_signal(expert_mtf={"state": "HARD_CONFLICT", "reason": "4H bull vs 1H bear"})
    ok, reason = explain_predict_trade(sig)
    assert_true("hard MTF conflict rejects", not ok and "MTF" in reason)

    candidates = []
    for i, score in enumerate([99, 96, 94, 91, 88], start=1):
        candidates.append({"pair": f"T{i}USDT", "direction": "LONG", "ranking_score": score})
    selected = _select_final_delivery_candidates(candidates, limit=5)
    assert_true("more than three valid signals choose best three", len(selected) == 3)

    dupes = [
        {"pair": "BTCUSDT", "direction": "LONG", "ranking_score": 99},
        {"pair": "BTCUSDT", "direction": "LONG", "ranking_score": 98},
        {"pair": "ETHUSDT", "direction": "SHORT", "ranking_score": 97},
    ]
    selected = _select_final_delivery_candidates(dupes, limit=3)
    assert_true("duplicate symbol direction selects once", len([s for s in selected if s["pair"] == "BTCUSDT"]) == 1)

    reduced = []
    for i, score in enumerate([99, 96, 94], start=1):
        reduced.append({"pair": f"R{i}USDT", "direction": "LONG", "ranking_score": score, "approval_type": "REDUCED_SIZE_APPROVAL"})
    selected = _select_final_delivery_candidates(reduced, limit=3)
    assert_true("all reduced size sends at most two", len(selected) == 2)

    print("FINAL_PRODUCTION_CALIBRATION_TESTS_OK")


if __name__ == "__main__":
    main()
