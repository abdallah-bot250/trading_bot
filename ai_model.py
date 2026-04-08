import math
import logging

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg):
    logging.info(msg)

# ================= SAFE FLOAT =================
def safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

# ================= NORMALIZE =================
def normalize_text(v):
    try:
        return str(v).strip().upper()
    except Exception:
        return ""

# ================= HELPERS =================
def clamp(value, min_value, max_value):
    try:
        return max(min_value, min(float(value), max_value))
    except Exception:
        return min_value

def rr_ratio(entry, tp, sl, direction):
    try:
        entry = safe_float(entry)
        tp = safe_float(tp)
        sl = safe_float(sl)
        direction = normalize_text(direction)

        if direction == "LONG":
            risk = entry - sl
            reward = tp - entry
        elif direction == "SHORT":
            risk = sl - entry
            reward = entry - tp
        else:
            return 0

        if risk <= 0 or reward <= 0:
            return 0

        return round(reward / risk, 4)
    except Exception:
        return 0

def percent_distance(a, b):
    try:
        a = safe_float(a)
        b = safe_float(b)
        if a == 0:
            return 0
        return abs((b - a) / a) * 100
    except Exception:
        return 0

# ================= SCORE COMPONENTS =================
def score_confidence(confidence):
    confidence = safe_float(confidence)

    if confidence >= 95:
        return 25
    elif confidence >= 90:
        return 22
    elif confidence >= 85:
        return 19
    elif confidence >= 80:
        return 16
    elif confidence >= 75:
        return 12
    elif confidence >= 70:
        return 8
    elif confidence >= 65:
        return 4
    return 0

def score_rr(rr):
    rr = safe_float(rr)

    if rr >= 3.0:
        return 20
    elif rr >= 2.5:
        return 17
    elif rr >= 2.0:
        return 14
    elif rr >= 1.7:
        return 11
    elif rr >= 1.5:
        return 8
    elif rr >= 1.2:
        return 5
    return 0

def score_volume(volume):
    volume = normalize_text(volume)

    if volume == "STRONG":
        return 12
    elif volume == "MEDIUM":
        return 7
    elif volume == "WEAK":
        return 2
    return 0

def score_trend(trend, trend_power):
    trend = normalize_text(trend)
    trend_power = normalize_text(trend_power)

    score = 0

    if trend in ["UP", "DOWN"]:
        score += 6

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        score += 10
    elif trend_power in ["BULL", "BEAR"]:
        score += 6
    elif trend_power in ["MIXED"]:
        score += 2
    elif trend_power in ["WEAK"]:
        score -= 3

    return score

def score_structure(structure):
    structure = normalize_text(structure)

    if structure in ["BREAKOUT", "NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        return 10
    elif structure in ["PULLBACK", "CONTINUATION"]:
        return 7
    elif structure in ["MID_RANGE"]:
        return 4
    elif structure in ["CHOPPY", "RANGE"]:
        return -2
    return 0

def score_smc(smc):
    smc = normalize_text(smc)

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        return 10
    elif smc in ["BOS", "CHOCH"]:
        return 8
    elif smc in ["ORDER_BLOCK", "FVG"]:
        return 6
    elif smc in ["RANGE", "NONE"]:
        return 1
    return 0

def score_timeframe(tf):
    tf = normalize_text(tf)

    if tf == "1H":
        return 10
    elif tf == "15M":
        return 8
    elif tf == "5M":
        return 5
    elif tf == "3M":
        return 3
    elif tf == "1M":
        return 1
    return 0

def score_signal_shape(entry, tp, sl, direction):
    try:
        entry = safe_float(entry)
        tp = safe_float(tp)
        sl = safe_float(sl)
        direction = normalize_text(direction)

        if entry <= 0 or tp <= 0 or sl <= 0:
            return -10

        if direction == "LONG":
            if not (tp > entry > sl):
                return -20
        elif direction == "SHORT":
            if not (tp < entry < sl):
                return -20
        else:
            return -20

        tp_dist = percent_distance(entry, tp)
        sl_dist = percent_distance(entry, sl)

        score = 0

        # منع SL القريب جدًا
        if sl_dist < 0.15:
            score -= 10
        elif sl_dist < 0.25:
            score -= 5
        elif 0.25 <= sl_dist <= 2.0:
            score += 5

        # منع TP القريب جدًا
        if tp_dist < 0.25:
            score -= 10
        elif tp_dist < 0.40:
            score -= 4
        elif 0.40 <= tp_dist <= 4.0:
            score += 6

        return score
    except Exception:
        return -5

# ================= MAIN AI FILTER =================
def predict_trade(signal):
    """
    يرجع:
    {
        "approved": True/False,
        "confidence": new_confidence,
        "score": ai_score,
        "ranking_score": ranking_score,
        "reason": "..."
    }
    """
    try:
        if not signal or not isinstance(signal, dict):
            return {
                "approved": False,
                "confidence": 0,
                "score": 0,
                "ranking_score": 0,
                "reason": "invalid_signal"
            }

        pair = signal.get("pair", "")
        direction = normalize_text(signal.get("direction", ""))
        entry = safe_float(signal.get("entry", 0))
        tp = safe_float(signal.get("tp", 0))
        sl = safe_float(signal.get("sl", 0))
        confidence = safe_float(signal.get("confidence", 0))
        volume = signal.get("volume", "WEAK")
        trend = signal.get("trend", "UNKNOWN")
        trend_power = signal.get("trend_power", "MIXED")
        structure = signal.get("structure", "MID_RANGE")
        smc = signal.get("smc", "RANGE")
        timeframe = signal.get("timeframe", "5m")

        if not pair or direction not in ["LONG", "SHORT"] or entry <= 0 or tp <= 0 or sl <= 0:
            return {
                "approved": False,
                "confidence": 0,
                "score": -100,
                "ranking_score": 0,
                "reason": "missing_or_invalid_fields"
            }

        rr = rr_ratio(entry, tp, sl, direction)

        # ================= AI SCORE BUILD =================
        ai_score = 0
        ai_score += score_confidence(confidence)
        ai_score += score_rr(rr)
        ai_score += score_volume(volume)
        ai_score += score_trend(trend, trend_power)
        ai_score += score_structure(structure)
        ai_score += score_smc(smc)
        ai_score += score_timeframe(timeframe)
        ai_score += score_signal_shape(entry, tp, sl, direction)

        # ================= PENALTIES =================
        reason_flags = []

        if rr < 1.2:
            ai_score -= 15
            reason_flags.append("low_rr")

        if confidence < 68:
            ai_score -= 12
            reason_flags.append("low_conf")

        if normalize_text(volume) == "WEAK":
            ai_score -= 5
            reason_flags.append("weak_volume")

        if normalize_text(trend_power) == "WEAK":
            ai_score -= 6
            reason_flags.append("weak_trend_power")

        if normalize_text(structure) in ["CHOPPY", "RANGE"]:
            ai_score -= 4
            reason_flags.append("bad_structure")

        # ================= BONUS =================
        if rr >= 2.0 and confidence >= 80:
            ai_score += 8
            reason_flags.append("strong_rr_conf_combo")

        if normalize_text(volume) == "STRONG" and normalize_text(trend_power) in ["STRONG_BULL", "STRONG_BEAR"]:
            ai_score += 7
            reason_flags.append("trend_volume_alignment")

        if normalize_text(structure) in ["BREAKOUT", "NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"] and normalize_text(smc) in ["BOS", "CHOCH", "LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
            ai_score += 6
            reason_flags.append("structure_smc_alignment")

        # ================= FINAL AI CONFIDENCE =================
        adjusted_confidence = confidence

        if ai_score >= 80:
            adjusted_confidence += 8
        elif ai_score >= 70:
            adjusted_confidence += 6
        elif ai_score >= 60:
            adjusted_confidence += 4
        elif ai_score >= 50:
            adjusted_confidence += 2
        elif ai_score < 35:
            adjusted_confidence -= 10
        elif ai_score < 45:
            adjusted_confidence -= 6

        adjusted_confidence = clamp(adjusted_confidence, 1, 99)

        # ================= RANKING SCORE =================
        ranking_score = (
            adjusted_confidence
            + (rr * 10)
            + score_volume(volume)
            + score_trend(trend, trend_power)
            + score_structure(structure)
            + score_smc(smc)
            + score_timeframe(timeframe)
        )

        ranking_score = round(ranking_score, 2)

        # ================= APPROVAL =================
        approved = False
        reason = "rejected"

        if adjusted_confidence >= 70 and ai_score >= 40 and rr >= 1.2:
            approved = True
            reason = "approved"

        if adjusted_confidence >= 78 and ai_score >= 50 and rr >= 1.4:
            approved = True
            reason = "strong_approved"

        if adjusted_confidence >= 85 and ai_score >= 60 and rr >= 1.5:
            approved = True
            reason = "elite_approved"

        result = {
            "approved": approved,
            "confidence": round(adjusted_confidence, 2),
            "score": round(ai_score, 2),
            "ranking_score": ranking_score,
            "reason": reason,
            "rr": round(rr, 4),
            "flags": reason_flags
        }

        log(f"AI RESULT => {pair} | {result}")
        return result

    except Exception as e:
        log(f"predict_trade error: {e}")
        return {
            "approved": False,
            "confidence": 0,
            "score": -100,
            "ranking_score": 0,
            "reason": f"ai_error:{e}"
        }