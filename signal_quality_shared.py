"""Shared signal-quality gates used by analyzer, AI checks, and delivery.

This module is deliberately dependency-light so it can be imported from the
signal engine, Telegram sender, and the AI validation layer without creating
runtime cycles.
"""

B_PLUS_CONFIRMED_SETUPS = {
    "range_edge_bounce",
    "trend_pullback_continuation",
    "trend_following_confirmed",
    "accumulation_reclaim",
    "distribution_rejection",
    "break_and_retest",
}

B_PLUS_HARD_REJECT_MARKERS = (
    "LOW_LIQUIDITY",
    "LOW_VOLUME_CHOP",
    "FAKE_BREAKOUT",
    "HARD_CONFLICT",
    "HARD MTF CONFLICT",
    "STALE",
    "EXPIRED",
    "INVALID RR",
    "INVALID ENTRY",
    "INVALID GEOMETRY",
    "MID-RANGE",
    "MID_RANGE",
    "NO RETEST",
    "NO ENTRY",
    "NOT ENOUGH ROOM",
    "LATE_ENTRY",
    "ENTRY_MOVED",
    "CHASE",
    "TARGET_ALREADY_HIT",
    "STOP_ALREADY_HIT",
)


def _safe_float(value, default=0.0):
    try:
        if value in (None, "", "N/A"):
            return default
        return float(value)
    except Exception:
        return default


def signal_display_confidence(signal):
    return _safe_float(signal.get("display_confidence", signal.get("confidence", 0)), 0)


def b_plus_setup_name(signal):
    return str(
        signal.get("setup_type")
        or signal.get("strategy_name")
        or signal.get("adaptive_playbook")
        or ""
    ).strip().lower().replace(" ", "_").replace("-", "_")


def valid_signal_geometry(signal):
    direction = str(signal.get("direction") or "").upper()
    entry = _safe_float(signal.get("entry"), 0)
    tp = _safe_float(signal.get("tp1") or signal.get("tp"), 0)
    sl = _safe_float(signal.get("sl"), 0)
    if entry <= 0 or tp <= 0 or sl <= 0:
        return False
    if direction == "LONG":
        return tp > entry and sl < entry
    if direction == "SHORT":
        return tp < entry and sl > entry
    return False


def _b_plus_context_text(signal):
    parts = [
        signal.get("market_regime"),
        signal.get("liquidity_context"),
        signal.get("liquidity_reason"),
        signal.get("entry_location_reason"),
        signal.get("smart_money_reason"),
        signal.get("signal_quality_reason"),
        signal.get("final_score_reason"),
        signal.get("self_review"),
        signal.get("entry_timing_reason"),
        signal.get("freshness_reason"),
        signal.get("signal_status"),
        signal.get("rejection_reason"),
        signal.get("structure"),
    ]
    return " ".join(str(part or "") for part in parts).upper()


def has_hard_rejection_context(signal):
    text = _b_plus_context_text(signal)
    return any(marker in text for marker in B_PLUS_HARD_REJECT_MARKERS)


def mtf_is_b_plus_approved(signal):
    if signal.get("b_plus_mtf_path") is True or signal.get("mtf_path") == "soft_alignment":
        return True
    mtf = signal.get("expert_mtf") or {}
    if isinstance(mtf, dict):
        if mtf.get("state") == "CONFIRMED" and not signal.get("mtf_soft_conflict"):
            return True
        if mtf.get("b_plus_mtf_path") is True:
            return True
        ctx = mtf.get("b_plus_mtf_context") or {}
        if isinstance(ctx, dict) and ctx.get("ok") is True:
            return True
    if signal.get("mtf_soft_conflict") is True:
        return False
    return True


def entry_confirmation_is_fresh(signal):
    age = signal.get("entry_confirmation_age_candles")
    if age in (None, "", "N/A"):
        return not has_hard_rejection_context(signal)
    try:
        return int(age) in {0, 1, 2} and not has_hard_rejection_context(signal)
    except Exception:
        return False


def safe_b_plus_eligibility(signal, allow_borderline_score=False):
    """Return (ok, reason) for the only allowed B+ consistency bypass.

    This does not lower global thresholds. It only recognizes signals already
    explicitly calibrated as B+ and still passing hard safety checks.
    """
    try:
        if signal.get("b_plus_calibrated") is not True:
            return False, "not_explicitly_b_plus_calibrated"
        if str(signal.get("setup_lifecycle") or "").upper() != "CONFIRMED":
            return False, "setup_not_confirmed"
        setup = b_plus_setup_name(signal)
        if setup not in B_PLUS_CONFIRMED_SETUPS:
            return False, f"setup_not_allowed:{setup or 'unknown'}"
        rr = _safe_float(signal.get("risk_reward"), 0)
        if rr < 1.5:
            return False, f"bad_rr:{rr}"
        if not valid_signal_geometry(signal):
            return False, "invalid_geometry"
        if not entry_confirmation_is_fresh(signal):
            return False, "entry_not_fresh"
        if has_hard_rejection_context(signal):
            return False, "hard_reject_marker_present"
        risk_level = str(signal.get("risk_level") or "").upper()
        risk_score = _safe_float(signal.get("risk_score"), 50)
        if risk_level == "HIGH" or risk_score >= 72:
            return False, f"risk_not_safe:{risk_level or risk_score}"
        volume_state = str(signal.get("volume_state") or signal.get("volume_gate") or "").upper()
        volume_score = _safe_float(signal.get("volume_score"), 50)
        if volume_state == "THIN" or volume_score < 45:
            return False, f"volume_not_safe:{volume_state or volume_score}"
        if not mtf_is_b_plus_approved(signal):
            return False, "mtf_not_approved"
        final_score = _safe_float(signal.get("final_score"), signal_display_confidence(signal))
        if final_score < 78:
            if not allow_borderline_score or final_score < 77:
                return False, f"final_score_below_b_plus:{final_score}"
            if risk_level not in {"LOW", "MEDIUM", ""}:
                return False, "borderline_score_unsafe_risk"
            if volume_state in {"THIN", "LOW"}:
                return False, "borderline_score_unsafe_volume"
            signal["b_plus_borderline_score_rule"] = True
        return True, "safe_b_plus_eligible"
    except Exception as exc:
        return False, f"safe_b_plus_error:{exc}"
