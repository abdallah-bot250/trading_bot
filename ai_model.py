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


# ✅ RR ثابت ومظبوط
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


# ❌ كان بيرجع % → عملناها decimal عشان consistency
def percent_distance(a, b):
    try:
        a = safe_float(a)
        b = safe_float(b)
        if a <= 0:
            return 0
        return abs((b - a) / a)  # 🔥 بدون *100
    except Exception:
        return 0


def is_valid_direction(direction):
    return normalize_text(direction) in ["LONG", "SHORT"]


def signal_shape_valid(entry, tp, sl, direction):
    try:
        entry = safe_float(entry)
        tp = safe_float(tp)
        sl = safe_float(sl)
        direction = normalize_text(direction)

        if entry <= 0 or tp <= 0 or sl <= 0:
            return False

        if direction == "LONG":
            return tp > entry > sl
        elif direction == "SHORT":
            return tp < entry < sl

        return False
    except Exception:
        return False


# ✅ خففنا القسوة
def trend_direction_alignment(direction, trend, trend_power):
    try:
        direction = normalize_text(direction)
        trend = normalize_text(trend)
        trend_power = normalize_text(trend_power)

        # منع التضارب القاتل فقط
        if direction == "LONG" and trend_power == "STRONG_BEAR":
            return False

        if direction == "SHORT" and trend_power == "STRONG_BULL":
            return False

        return True
    except Exception:
        return True


# ✅ تقليل القسوة
def market_quality_penalty(volume, trend_power, structure, smc):
    penalty = 0

    volume = normalize_text(volume)
    trend_power = normalize_text(trend_power)
    structure = normalize_text(structure)
    smc = normalize_text(smc)

    if volume == "WEAK":
        penalty += 3

    if trend_power == "WEAK":
        penalty += 4
    elif trend_power == "MIXED":
        penalty += 1

    if structure in ["CHOPPY", "RANGE"]:
        penalty += 3

    if smc in ["RANGE", "NONE", "UNKNOWN"]:
        penalty += 1

    return penalty


# ================= SCORE COMPONENTS =================

def score_confidence(confidence):
    confidence = safe_float(confidence)

    if confidence >= 90:
        return 20
    elif confidence >= 85:
        return 16
    elif confidence >= 80:
        return 13
    elif confidence >= 75:
        return 10
    elif confidence >= 70:
        return 6
    return 0


def score_rr(rr):
    rr = safe_float(rr)

    if rr >= 3.0:
        return 18
    elif rr >= 2.5:
        return 15
    elif rr >= 2.0:
        return 12
    elif rr >= 1.7:
        return 9
    elif rr >= 1.5:
        return 6
    return 0


def score_volume(volume):
    volume = normalize_text(volume)

    if volume == "STRONG":
        return 10
    elif volume == "MEDIUM":
        return 5
    elif volume == "WEAK":
        return 1
    return 0


def score_trend(trend, trend_power):
    trend = normalize_text(trend)
    trend_power = normalize_text(trend_power)

    score = 0

    if trend in ["UP", "DOWN"]:
        score += 5

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        score += 9
    elif trend_power in ["BULL", "BEAR"]:
        score += 5
    elif trend_power == "MIXED":
        score += 1
    elif trend_power == "WEAK":
        score -= 2

    return score


def score_structure(structure):
    structure = normalize_text(structure)

    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        return 8
    elif structure == "MID_RANGE":
        return 3
    elif structure in ["CHOPPY", "RANGE"]:
        return -2
    return 0


def score_smc(smc):
    smc = normalize_text(smc)

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        return 8
    elif smc in ["BOS", "CHOCH"]:
        return 6
    return 0


def score_timeframe(tf):
    tf = normalize_text(tf)

    if tf == "1H":
        return 8
    elif tf == "15M":
        return 6
    elif tf == "5M":
        return 4
    return 0


# ✅ متظبط مع decimal system
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
                return -15
        elif direction == "SHORT":
            if not (tp < entry < sl):
                return -15

        tp_dist = percent_distance(entry, tp)
        sl_dist = percent_distance(entry, sl)

        score = 0

        # SL
        if sl_dist < 0.001:
            score -= 10
        elif 0.002 <= sl_dist <= 0.02:
            score += 4

        # TP
        if tp_dist < 0.002:
            score -= 10
        elif 0.003 <= tp_dist <= 0.05:
            score += 5

        return score

    except Exception:
        return -5

# ================= MAIN AI FILTER =================
def predict_trade(signal):
    try:
        if not signal or not isinstance(signal, dict):
            return {
                "approved": False,
                "confidence": 0,
                "score": 0,
                "ranking_score": 0,
                "reason": "invalid_signal",
                "rr": 0,
                "flags": ["invalid_signal"]
            }

        pair = signal.get("pair", "")
        direction = normalize_text(signal.get("direction", ""))
        entry = safe_float(signal.get("entry", 0))
        tp = safe_float(signal.get("tp2", signal.get("tp1", 0)))
        sl = safe_float(signal.get("sl", 0))
        confidence = safe_float(signal.get("confidence", 0))
        volume = signal.get("volume", "WEAK")
        trend = signal.get("trend", "UNKNOWN")
        trend_power = signal.get("trend_power", "MIXED")
        structure = signal.get("structure", "MID_RANGE")
        smc = signal.get("smc", "RANGE")
        timeframe = signal.get("timeframe", "5m")

        if not pair or not is_valid_direction(direction) or entry <= 0 or tp <= 0 or sl <= 0:
            return {
                "approved": False,
                "confidence": 0,
                "score": -100,
                "ranking_score": 0,
                "reason": "missing_or_invalid_fields",
                "rr": 0,
                "flags": ["missing_or_invalid_fields"]
            }

        # ================= INIT =================
        ai_score = 0
        reason_flags = []

        # ================= SIGNAL SHAPE =================
        if not signal_shape_valid(entry, tp, sl, direction):
            ai_score -= 25
            reason_flags.append("bad_signal_shape")

        # ================= RR =================
        rr = rr_ratio(entry, tp, sl, direction)

        if rr <= 0:
            return {
                "approved": False,
                "confidence": 0,
                "score": -100,
                "ranking_score": 0,
                "reason": "bad_rr",
                "rr": 0,
                "flags": ["bad_rr"]
            }

        # ================= TREND ALIGNMENT =================
        if not trend_direction_alignment(direction, trend, trend_power):
            ai_score -= 18
            reason_flags.append("trend_conflict")

        # ================= BASE SCORING =================
        ai_score += score_confidence(confidence)
        ai_score += score_rr(rr)
        ai_score += score_volume(volume)
        ai_score += score_trend(trend, trend_power)
        ai_score += score_structure(structure)
        ai_score += score_smc(smc)
        ai_score += score_timeframe(timeframe)
        ai_score += score_signal_shape(entry, tp, sl, direction)

        # ================= PENALTIES (مخففة ومتوازنة) =================
        quality_penalty = market_quality_penalty(volume, trend_power, structure, smc)
        ai_score -= quality_penalty

        if quality_penalty > 0:
            reason_flags.append(f"market_penalty_{quality_penalty}")

        if rr < 1.2:
            ai_score -= 8
            reason_flags.append("low_rr")

        if confidence < 68:
            ai_score -= 6
            reason_flags.append("low_conf")

        # ================= BONUS =================
        if rr >= 2.0 and confidence >= 76:
            ai_score += 5
            reason_flags.append("strong_rr_conf")

        if normalize_text(volume) == "STRONG" and normalize_text(trend_power) in ["STRONG_BULL", "STRONG_BEAR"]:
            ai_score += 5
            reason_flags.append("trend_volume_alignment")

        if normalize_text(structure) in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
            ai_score += 4

        if normalize_text(timeframe) == "1H":
            ai_score += 4

        # ================= CONFIDENCE (متوازن) =================
        adjusted_confidence = confidence

        if ai_score >= 80:
            adjusted_confidence += 6
        elif ai_score >= 70:
            adjusted_confidence += 4
        elif ai_score >= 60:
            adjusted_confidence += 2
        elif ai_score < 40:
            adjusted_confidence -= 8
        elif ai_score < 50:
            adjusted_confidence -= 4

        adjusted_confidence = clamp(adjusted_confidence, 1, 99)

        # ================= RANKING =================
        ranking_score = (
            adjusted_confidence
            + (rr * 9)
            + score_trend(trend, trend_power)
            + score_structure(structure)
            + score_smc(smc)
        )

        ranking_score = round(ranking_score, 2)

        # ================= APPROVAL (مشددة للجودة) =================
        approved = False
        reason = "rejected"

# 🎯 المستوى العادي
        if adjusted_confidence >= 65 and ai_score >= 42 and rr >= 1.25:
            approved = True
            reason = "approved"

# 🔥 مستوى قوي
        if adjusted_confidence >= 70 and ai_score >= 49 and rr >= 1.3:
            approved = True
            reason = "strong"

# 💎 مستوى جامد جدًا
        if adjusted_confidence >= 75 and ai_score >= 56 and rr >= 1.45:
             approved = True
             reason = "elite"

        # ================= FINAL SAFETY =================
        if approved:
            if normalize_text(volume) == "WEAK":
             if rr < 1.2 and adjusted_confidence < 72:
                approved = False
                reason = "weak_volume_reject"
                reason_flags.append("weak_volume")

            if normalize_text(structure) in ["CHOPPY", "RANGE"]:
              if rr < 1.4:
                approved = False
                reason = "bad_structure_reject"
                reason_flags.append("bad_structure")

        result = {
            "approved": approved,
            "confidence": round(adjusted_confidence, 2),
            "score": round(ai_score, 2),
            "ranking_score": ranking_score,
            "reason": reason,
            "rr": round(rr, 4),
            "flags": reason_flags
        }

        # 🔥 logging بس للإشارات المقبولة
        if approved:
            log(f"AI RESULT => {pair} | {result}")

        return result

    except Exception as e:
        log(f"predict_trade error: {e}")
        return {
            "approved": False,
            "confidence": 0,
            "score": -100,
            "ranking_score": 0,
            "reason": f"ai_error:{e}",
            "rr": 0,
            "flags": [f"ai_error:{e}"]
        }