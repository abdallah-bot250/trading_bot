import numpy as np
from signal_quality_shared import safe_b_plus_eligibility

AI_NORMAL_APPROVAL_CONFIDENCE = 75
AI_REDUCED_SIZE_MIN_CONFIDENCE = 70
AI_REDUCED_SIZE_MULTIPLIER = 0.5

TRUE_LOW_LIQUIDITY_VOLUME_RATIO_MIN = 0.12
TRUE_LOW_LIQUIDITY_SCORE_MIN = 35

# ================= AI DECISION ENGINE =================
def predict_trade(signal):
    score = 0

    try:
        entry = float(signal.get("entry", 0))
        tp = float(signal.get("tp", 0))
        sl = float(signal.get("sl", 0))
        direction = signal.get("direction")

        confidence = float(signal.get("confidence", 0))
        trend = signal.get("trend")
        trend_power = signal.get("trend_power")
        volume = signal.get("volume")
        smc = signal.get("smc")
        structure = signal.get("structure")
        tf = signal.get("timeframe")

        if entry <= 0 or tp <= 0 or sl <= 0:
            return False

        # ================= BASIC LEVEL CHECK =================
        if direction == "LONG":
            if not (tp > entry and sl < entry):
                return False
        elif direction == "SHORT":
            if not (tp < entry and sl > entry):
                return False
        else:
            return False

        # ================= RISK REWARD =================
        if direction == "LONG":
            reward = tp - entry
            risk = entry - sl
        else:
            reward = entry - tp
            risk = sl - entry

        if reward <= 0 or risk <= 0:
            return False

        rr = reward / risk

        if rr >= 2.5:
            score += 5
        elif rr >= 2.1:
            score += 4
        elif rr >= 1.8:
            score += 3
        elif rr >= 1.6:
            score += 2
        else:
            return False

        # ================= DISTANCE CHECK =================
        tp_distance = abs(tp - entry) / entry
        sl_distance = abs(sl - entry) / entry

        if entry < 1:
            if tp_distance < 0.012:
                return False
        else:
            if tp_distance < 0.008:
                return False

        if sl_distance < 0.0032:
            return False

        if tp_distance >= 0.02:
            score += 4
        elif tp_distance >= 0.015:
            score += 3
        elif tp_distance >= 0.01:
            score += 2
        else:
            score += 1

        # ================= CONFIDENCE =================
        if confidence >= 86:
            score += 5
        elif confidence >= 80:
            score += 4
        elif confidence >= 74:
            score += 3
        elif confidence >= 68:
            score += 2
        else:
            return False

        # ================= TREND =================
        if trend == "UP" and direction == "LONG":
            score += 2
        elif trend == "DOWN" and direction == "SHORT":
            score += 2
        else:
            score -= 2

        # ================= TREND POWER =================
        if trend_power == "STRONG_BULL" and direction == "LONG":
            score += 4
        elif trend_power == "STRONG_BEAR" and direction == "SHORT":
            score += 4
        elif trend_power == "MIXED":
            score -= 4

        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False

        # ================= VOLUME =================
        if volume == "STRONG":
            score += 3
        else:
            score -= 2

        # ================= SMART MONEY =================
        if smc == "LIQUIDITY_BREAK_UP" and direction == "LONG":
            score += 4
        elif smc == "LIQUIDITY_BREAK_DOWN" and direction == "SHORT":
            score += 4
        elif smc == "RANGE":
            score -= 3
        else:
            score -= 1

        # ================= STRUCTURE =================
        if structure == "NEAR_BREAKOUT_HIGH" and direction == "LONG":
            score += 3
        elif structure == "NEAR_BREAKOUT_LOW" and direction == "SHORT":
            score += 3
        elif structure == "MID_RANGE":
            score -= 3
        elif structure == "UNKNOWN":
            score -= 2

        # ================= TIMEFRAME =================
        if tf == "1h":
            score += 4
        elif tf == "15m":
            score += 3
        elif tf == "5m":
            score += 2

        # ================= SMART BOOST =================
        if (
            direction == "LONG"
            and trend == "UP"
            and structure == "NEAR_BREAKOUT_HIGH"
        ):
            score += 2

        if (
            direction == "SHORT"
            and trend == "DOWN"
            and structure == "NEAR_BREAKOUT_LOW"
        ):
            score += 2

        # ================= POWER BOOST =================
        if (
            volume == "STRONG"
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            and smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]
        ):
            score += 4

        # ================= MONSTER FILTER =================
        if (
            trend_power == "MIXED"
            and volume != "STRONG"
            and smc == "RANGE"
        ):
            return False

        if confidence < 70 and tp_distance < 0.01:
            return False

        if rr < 1.7 and tf == "5m":
            return False

        # ================= FINAL DECISION =================
        return score >= 8

    except Exception as e:
        print(f"AI ERROR: {e}")
        return False

def explain_predict_trade(signal):
    """Return (allowed, reason) for the AI validation gate.

    This keeps the legacy predict_trade decision but exposes the blocking reason
    so the signal engine is no longer a black box in production logs.
    """
    try:
        entry = float(signal.get("entry", 0))
        tp = float(signal.get("tp", 0))
        sl = float(signal.get("sl", 0))
        direction = signal.get("direction")
        confidence = float(signal.get("display_confidence", signal.get("confidence", 0)) or 0)
        rr = float(signal.get("risk_reward", 0) or 0)
        volume_state = str(signal.get("volume_state", signal.get("volume", ""))).upper()
        risk_level = str(signal.get("risk_level", "")).upper()
        market_regime = str(signal.get("market_regime", signal.get("adaptive_regime", ""))).upper()
        trend_power = signal.get("trend_power")
        structure = signal.get("structure")
        tf = signal.get("timeframe")
        safe_bplus_ok, safe_bplus_reason = safe_b_plus_eligibility(signal, allow_borderline_score=True)
        volume_ratio_raw = signal.get("volume_ratio")
        liquidity_score_raw = signal.get("liquidity_score", signal.get("volume_score"))
        try:
            volume_ratio = float(volume_ratio_raw)
        except Exception:
            volume_ratio = None
        try:
            liquidity_score = float(liquidity_score_raw)
        except Exception:
            liquidity_score = None

        mtf_state = str((signal.get("expert_mtf") or {}).get("state") or signal.get("mtf_state") or "").upper()
        mtf_reason = str((signal.get("expert_mtf") or {}).get("reason") or signal.get("mtf_reason") or "").upper()
        hard_mtf_conflict = (
            bool(signal.get("mtf_hard_conflict"))
            or mtf_state == "HARD_CONFLICT"
            or "HARD_CONFLICT" in mtf_reason
        )
        setup_confirmed = bool(
            signal.get("setup_confirmed")
            or signal.get("strategy_name")
            or signal.get("setup_type")
            or signal.get("smart_money_setup")
            or signal.get("futures_30m_setup")
        )
        true_low_liquidity = (
            bool(signal.get("liquidity_invalid"))
            or bool(signal.get("liquidity_hard_reject"))
            or market_regime in {"LOW_LIQUIDITY", "LOW_VOLUME_CHOP"}
            or volume_ratio is None
            or liquidity_score is None
            or volume_ratio < TRUE_LOW_LIQUIDITY_VOLUME_RATIO_MIN
            or liquidity_score < TRUE_LOW_LIQUIDITY_SCORE_MIN
        )

        if entry <= 0 or tp <= 0 or sl <= 0:
            return False, "invalid entry/tp/sl"
        if direction == "LONG" and not (tp > entry and sl < entry):
            return False, "invalid LONG geometry"
        if direction == "SHORT" and not (tp < entry and sl > entry):
            return False, "invalid SHORT geometry"
        if direction not in ["LONG", "SHORT"]:
            return False, "invalid direction"
        if rr and rr < 1.5:
            return False, f"RR {round(rr, 2)} below 1.5"
        if hard_mtf_conflict:
            return False, "hard MTF conflict"
        if true_low_liquidity:
            return False, "TRUE_LOW_LIQUIDITY_HARD_REJECT"
        if confidence < 70 and not safe_bplus_ok:
            return False, f"display confidence {round(confidence, 2)} below 70"
        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False, "SHORT against strong bull trend"
        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False, "LONG against strong bear trend"
        if structure == "MID_RANGE" and tf == "5m" and confidence < 82:
            return False, "5m mid-range setup lacks edge"
        playbook_confidence = float(
            signal.get("playbook_confidence", signal.get("raw_confidence", signal.get("confidence", confidence))) or 0
        )
        thin_soft_risk = volume_state == "THIN"
        if risk_level == "HIGH" and confidence < 82:
            if (
                setup_confirmed
                and playbook_confidence >= 80
                and confidence >= AI_REDUCED_SIZE_MIN_CONFIDENCE
                and not thin_soft_risk
            ):
                signal["approval_type"] = "REDUCED_SIZE_APPROVAL"
                signal["risk_tier"] = "HIGH"
                signal["size_multiplier"] = AI_REDUCED_SIZE_MULTIPLIER
                return True, "REDUCED_SIZE_APPROVAL high risk with confirmed setup"
            return False, "high risk requires stronger confidence"
        if confidence < 70 and safe_bplus_ok:
            return True, f"approved safe calibrated B+ ({safe_bplus_reason})"

        if confidence >= AI_NORMAL_APPROVAL_CONFIDENCE:
            signal.setdefault("approval_type", "NORMAL_APPROVAL")
            signal.setdefault("risk_tier", risk_level or "NORMAL")
            signal.setdefault("size_multiplier", 1.0)
            return True, "approved normal confidence" if not thin_soft_risk else "approved normal confidence with THIN_VOLUME_SOFT_RISK"

        if confidence >= AI_REDUCED_SIZE_MIN_CONFIDENCE:
            if thin_soft_risk and not (
                setup_confirmed
                and playbook_confidence >= 80
                and rr >= 1.8
                and risk_level in {"LOW", "MEDIUM", "NORMAL", "MODERATE", ""}
            ):
                return False, "THIN_VOLUME_SOFT_RISK requires stronger playbook/RR"
            signal["approval_type"] = "REDUCED_SIZE_APPROVAL"
            signal["risk_tier"] = "ELEVATED" if thin_soft_risk else (risk_level or "ELEVATED")
            signal["size_multiplier"] = AI_REDUCED_SIZE_MULTIPLIER
            return True, "REDUCED_SIZE_APPROVAL confidence 70-74" if not thin_soft_risk else "REDUCED_SIZE_APPROVAL THIN_VOLUME_SOFT_RISK"

        allowed = predict_trade({**signal, "confidence": confidence})
        return (True, "approved") if allowed else (False, "legacy score below threshold")
    except Exception as e:
        return False, f"AI explain error: {e}"
