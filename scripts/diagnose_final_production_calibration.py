import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_model import explain_predict_trade
from market_analyzer import (
    _duplicate_penalty_markers,
    _finalizer_rejection_bucket,
    _select_final_delivery_candidates,
    _signal_penalty_markers,
    _soft_armed_futures_approval,
    evaluate_final_approval_mode,
)


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
        "volume_ratio": 0.9,
        "liquidity_score": 60,
        "liquidity_invalid": False,
        "market_regime": "ACCUMULATION",
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


def bullish_frame(rows=90):
    data = []
    price = 100.0
    for i in range(rows):
        price += 0.08
        data.append({
            "open": price - 0.05,
            "high": price + 0.12,
            "low": price - 0.12,
            "close": price,
            "volume": 100000 + i,
        })
    return pd.DataFrame(data)


def bearish_frame(rows=90):
    data = []
    price = 110.0
    for i in range(rows):
        price -= 0.08
        data.append({
            "open": price + 0.05,
            "high": price + 0.12,
            "low": price - 0.12,
            "close": price,
            "volume": 100000 + i,
        })
    return pd.DataFrame(data)


def main():
    rejection_cases = [
        ("price in middle of 30m range position=0.42", "MID_RANGE_POSITION"),
        ("mid-range no trade position=0.48", "MID_RANGE_POSITION"),
        ("final_closed_rows=93 required_rows=100", "INSUFFICIENT_HISTORY"),
        ("not enough candles required_rows=100", "INSUFFICIENT_HISTORY"),
        ("range setup requires 4H/1H range context: 4H/1H data unavailable", "RANGE_CONTEXT_UNAVAILABLE"),
        ("invalid LONG/SHORT level geometry", "INVALID_GEOMETRY"),
        ("not enough room to nearest support/resistance for safe RR", "NO_ROOM_FOR_RR"),
        ("HIGH_VOLATILITY: mixed structure without clean trend", "MARKET_REGIME_FILTER"),
        ("medium risk stack: BREAKOUT_CHASE,ENTRY_CONFIRMATION_MISSING", "ENTRY_CONFIRMATION_MISSING"),
        ("completely_new_unmapped_reason", "OTHER_UNKNOWN"),
        ("", "MISSING_REJECTION_REASON"),
        (None, "MISSING_REJECTION_REASON"),
        ("entry_zone_not_touched_or_near", "ENTRY_CONFIRMATION_MISSING"),
        ("15m_direction_opposite", "ENTRY_CONFIRMATION_MISSING"),
        ("trigger_data_missing", "INSUFFICIENT_HISTORY"),
        ("4H BULL blocks SHORT futures", "UNCLEAR_MACRO_TREND"),
        ("LONG TP1 too close to/through resistance", "NO_ROOM_FOR_RR"),
        ("abnormal 15m candle expansion before entry", "MARKET_REGIME_FILTER"),
        ("confidence_below_80", "QUALITY_REPORT"),
    ]
    for reason, expected in rejection_cases:
        assert_true(f"rejection classification {expected}", _finalizer_rejection_bucket(reason) == expected)

    sig = base_signal(confidence_cap_reason="high_risk_cap")
    ok, reason = explain_predict_trade(sig)
    assert_true("duplicate high-risk penalty becomes reduced approval", ok and sig.get("approval_type") == "REDUCED_SIZE_APPROVAL")
    assert_true("reduced size multiplier is 50 percent", sig.get("size_multiplier") == 0.5)

    yom_like = base_signal(
        pair="YOMUSDT",
        confidence=72,
        display_confidence=70,
        playbook_confidence=72,
        risk_level="HIGH",
        confidence_cap_reason="high_risk",
        setup_confirmed=True,
        risk_reward=2.0,
    )
    decision = evaluate_final_approval_mode(yom_like)
    assert_true(
        "Case A YOM-like rejects with one documented approval rule",
        decision["approval_type"] == "REJECT" and "high_risk_requires" in decision["reason"]
    )
    assert_true("Case A high risk penalty is deduped", _signal_penalty_markers(yom_like).count("HIGH_RISK") == 1)

    bdx_like = base_signal(
        pair="BDXUSDT",
        confidence=83,
        display_confidence=68,
        playbook_confidence=83,
        risk_level="HIGH",
        volume_state="THIN",
        confidence_cap_reason="thin_volume_high_risk",
        setup_confirmed=True,
        risk_reward=2.0,
    )
    decision = evaluate_final_approval_mode(bdx_like)
    assert_true("Case B BDX-like confidence 68 rejects", decision["approval_type"] == "REJECT" and "below_70" in decision["reason"])
    assert_true("Case B duplicate markers are unique", len(_duplicate_penalty_markers(bdx_like, "high risk requires stronger confidence")) == len(set(_duplicate_penalty_markers(bdx_like, "high risk requires stronger confidence"))))

    case_c = base_signal(
        pair="CASECUSDT",
        confidence=86,
        display_confidence=72,
        playbook_confidence=86,
        risk_level="HIGH",
        confidence_cap_reason="high_risk",
        setup_confirmed=True,
        risk_reward=2.0,
    )
    decision = evaluate_final_approval_mode(case_c)
    assert_true("Case C high risk confirmed setup becomes reduced approval", decision["approval_type"] == "REDUCED_SIZE_APPROVAL")

    case_d = base_signal(pair="CASEDUSDT", tp=96, tp1=96)
    decision = evaluate_final_approval_mode(case_d)
    assert_true("Case D invalid geometry hard rejects", decision["approval_type"] == "REJECT" and "invalid_LONG_geometry" in decision["reason"])

    case_e = base_signal(pair="CASEEUSDT", expert_mtf={"state": "HARD_CONFLICT", "reason": "4H bull vs 1H bear"})
    decision = evaluate_final_approval_mode(case_e)
    assert_true("Case E hard MTF conflict hard rejects", decision["approval_type"] == "REJECT" and "hard_MTF_conflict" in decision["reason"])

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

    sig = base_signal(
        pair="ONDOUSDT",
        confidence=72,
        display_confidence=72,
        playbook_confidence=88,
        final_score=71,
        risk_level="LOW",
        volume_state="THIN",
        volume_score=35,
        liquidity_score=35,
        volume_ratio=0.7,
        risk_reward=6.09,
        setup_type="accumulation_reclaim",
        strategy_name="accumulation_reclaim",
        confidence_cap_reason="thin_volume",
    )
    ok, reason = explain_predict_trade(sig)
    assert_true("ONDO-like thin volume soft risk becomes reduced approval", ok and sig.get("approval_type") == "REDUCED_SIZE_APPROVAL" and sig.get("size_multiplier") == 0.5)

    sig = base_signal(volume_state="THIN", risk_level="LOW", market_regime="LOW_LIQUIDITY", liquidity_score=35, volume_ratio=0.7)
    ok, reason = explain_predict_trade(sig)
    assert_true("true low liquidity regime rejects", not ok and "LOW_LIQUIDITY" in reason)

    sig = base_signal(volume_state="THIN", risk_level="LOW", liquidity_invalid=True, liquidity_score=60, volume_ratio=0.9)
    ok, reason = explain_predict_trade(sig)
    assert_true("liquidity_invalid rejects", not ok and "LOW_LIQUIDITY" in reason)

    sig = base_signal(confidence=76, display_confidence=76, risk_level="LOW", volume_state="THIN", liquidity_score=35, volume_ratio=0.8)
    ok, reason = explain_predict_trade(sig)
    assert_true("thin volume confidence 76 safe normal approval", ok and sig.get("approval_type") == "NORMAL_APPROVAL")

    sig = base_signal(confidence=71, display_confidence=71, playbook_confidence=72, risk_level="LOW", volume_state="THIN", liquidity_score=35, volume_ratio=0.8, risk_reward=2.0)
    ok, reason = explain_predict_trade(sig)
    assert_true("thin volume weak playbook rejects", not ok and "THIN_VOLUME_SOFT_RISK" in reason)

    sig = base_signal(confidence=72, display_confidence=72, playbook_confidence=88, risk_level="LOW", volume_state="THIN", liquidity_score=35, volume_ratio=0.8, risk_reward=1.4)
    ok, reason = explain_predict_trade(sig)
    assert_true("thin volume bad RR rejects", not ok and "RR" in reason)

    trigger_df = bullish_frame()
    close = float(trigger_df["close"].iloc[-1])
    setup = {"stage": "CONFIRMED", "support": close - 0.2, "recent_low": close - 0.2, "volume_score": 55}
    trigger = {"stage": "ARMED", "reason": "15m candle close not decisive yet"}
    early = _soft_armed_futures_approval(
        "TESTUSDT",
        "LONG",
        base_signal(confidence=82, playbook_confidence=82),
        {"ok": True},
        setup,
        trigger,
        trigger_df,
    )
    assert_true("soft armed confirmed setup becomes early approval", bool(early and early.get("approval_type") == "EARLY_CONFIRMATION_APPROVAL"))

    early = _soft_armed_futures_approval(
        "TESTUSDT",
        "LONG",
        base_signal(confidence=82, playbook_confidence=82),
        {"ok": True},
        setup,
        trigger,
        None,
    )
    assert_true("missing trigger data remains armed reject", early is None)

    gram_df = bearish_frame()
    gram_close = float(gram_df["close"].iloc[-1])
    gram_setup = {"stage": "CONFIRMED", "resistance": gram_close + 0.5, "recent_high": gram_close + 0.5, "volume_score": 55}
    armed_trigger = {"stage": "ARMED", "reason": "15m trigger not confirmed yet"}
    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8),
        {"ok": True},
        gram_setup,
        armed_trigger,
        gram_df,
    )
    assert_true("GRAM-like soft armed valid becomes early confirmation", bool(early and early.get("approval_type") == "EARLY_CONFIRMATION_APPROVAL" and early.get("size_multiplier") == 0.5))

    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8),
        {"ok": True},
        gram_setup,
        armed_trigger,
        bullish_frame(),
    )
    assert_true("soft armed opposite 15m direction rejects", early is None)

    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=79, playbook_confidence=79, risk_reward=1.8),
        {"ok": True},
        gram_setup,
        armed_trigger,
        gram_df,
    )
    assert_true("soft armed confidence 79 rejects", early is None)

    far_setup = {"stage": "CONFIRMED", "resistance": gram_close + 5.0, "recent_high": gram_close + 5.0, "volume_score": 55}
    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8),
        {"ok": True},
        far_setup,
        armed_trigger,
        gram_df,
    )
    assert_true("soft armed far from entry zone rejects", early is None)

    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8),
        {"ok": True, "hard_conflict": True},
        gram_setup,
        armed_trigger,
        gram_df,
    )
    assert_true("soft armed hard MTF conflict rejects", early is None)

    confirmed_trigger = {"ok": True, "stage": "CONFIRMED", "reason": "full trigger confirmed"}
    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8),
        {"ok": True},
        gram_setup,
        confirmed_trigger,
        gram_df,
    )
    assert_true("fully confirmed trigger does not use early approval", early is None)

    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8, stale_entry=True),
        {"ok": True},
        gram_setup,
        armed_trigger,
        gram_df,
    )
    assert_true("soft armed stale entry rejects", early is None)

    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8, liquidity_hard_reject=True),
        {"ok": True},
        gram_setup,
        armed_trigger,
        gram_df,
    )
    assert_true("soft armed hard liquidity reject blocks", early is None)

    early = _soft_armed_futures_approval(
        "GRAMUSDT",
        "SHORT",
        base_signal(direction="SHORT", entry=100, tp=96, tp1=98, sl=102, confidence=86, playbook_confidence=86, risk_reward=1.8),
        {"ok": True},
        {**gram_setup, "stage": "WATCHING"},
        armed_trigger,
        gram_df,
    )
    assert_true("soft trigger without confirmed 30m setup rejects", early is None)

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
