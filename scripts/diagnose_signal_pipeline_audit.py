import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FERNET_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

import auto_sender
import market_analyzer


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def signal(tier="A", **overrides):
    base = {
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "type": "FUTURES",
        "direction": "LONG",
        "entry": 100,
        "tp": 103,
        "sl": 98,
        "confidence": 84,
        "display_confidence": 84,
        "final_score": 88,
        "risk_reward": 1.8,
        "risk_score": 45,
        "score": 34,
        "volume": "STRONG",
        "trend_power": "STRONG_BULL",
        "structure": "RANGE_EDGE",
        "quality_tier": tier,
        "opportunity_tier": tier,
        "setup_type": "trend_pullback_continuation",
    }
    base.update(overrides)
    return base


def main():
    market_analyzer.reset_signal_scan_diagnostics()
    safe_a = signal("A")
    market_analyzer._mark_signal_built(safe_a)
    diag = market_analyzer.get_signal_scan_diagnostics(final_signals=1)
    assert_true(diag["candidates_built"] >= 1 and diag["final_signals"] == 1, "safe A should reach candidates_built and final_signals")

    safe_b = signal("B_PLUS", display_confidence=63, confidence=63, final_score=82, b_plus_calibrated=True)
    market_analyzer.mark_opportunity_tier(safe_b)
    assert_true(auto_sender.qualified_opportunity_tier(safe_b) == "B_PLUS", "safe B+ should qualify")
    assert_true(auto_sender.valid_signal(safe_b), "safe B+ should pass delivery valid_signal")

    dangerous = signal("B_PLUS", pair="HBARUSDT", display_confidence=63, confidence=63, final_score=82, risk_reward=1.7, risk_score=79, b_plus_calibrated=True)
    assert_true(not market_analyzer.b_plus_calibration_eligible(dangerous)[0], "dangerous high/thin case should remain rejected")

    exhausted_trial = {
        "chat_id": "5199247792",
        "plan": "trial",
        "trades": 2,
        "expiry": None,
        "is_paid": 0,
    }
    original_free_earn = auto_sender.FREE_EARN_MODE
    auto_sender.FREE_EARN_MODE = True
    eligible, reason = auto_sender.delivery_access_status(exhausted_trial, qualified_opportunity_available=True)
    assert_true(eligible and reason == "free_earn_lane", f"exhausted trial should enter Free Earn lane, got {eligible} {reason}")

    original_create = auto_sender.create_pending_locked_signal
    original_send_unlock = auto_sender.send_unlock_prompt
    original_credits = auto_sender.free_unlock_credits
    original_base = auto_sender.free_earn_base_url
    original_write_log = auto_sender.write_log
    try:
        auto_sender.create_pending_locked_signal = lambda chat_id, plan, sig: "tokentest"
        auto_sender.send_unlock_prompt = lambda chat_id, url: True
        auto_sender.free_unlock_credits = lambda chat_id: 0
        auto_sender.free_earn_base_url = lambda: "https://nexoratrader.net"
        auto_sender.write_log = lambda *args, **kwargs: None
        state = auto_sender.maybe_handle_free_earn_delivery("5199247792", "trial", 2, safe_b)
        assert_true(state == "locked_prompt_sent", f"Free Earn should create locked signal, got {state}")
    finally:
        auto_sender.create_pending_locked_signal = original_create
        auto_sender.send_unlock_prompt = original_send_unlock
        auto_sender.free_unlock_credits = original_credits
        auto_sender.free_earn_base_url = original_base
        auto_sender.write_log = original_write_log
        auto_sender.FREE_EARN_MODE = original_free_earn

    pro_2y_user = {
        "chat_id": "999",
        "plan": "pro_2y",
        "expiry": "2999-01-01",
        "is_paid": 1,
        "trades": 0,
    }
    eligible, reason = auto_sender.delivery_access_status(pro_2y_user, qualified_opportunity_available=True)
    assert_true(eligible and auto_sender.signal_allowed_for_plan("pro_2y", safe_a), f"pro_2y should receive eligible final signal directly: {reason}")

    source = (ROOT / "market_analyzer.py").read_text(encoding="utf-8")
    for marker in ("CANDIDATE_PIPELINE_ENTER", "CANDIDATE_PIPELINE_REJECT", "CANDIDATE_PIPELINE_ACCEPT", "CANDIDATE_APPENDED", "FINAL_SIGNAL_SELECTED"):
        assert_true(marker in source, f"missing pipeline marker {marker}")

    print("SIGNAL_PIPELINE_AUDIT_OK")


if __name__ == "__main__":
    main()
