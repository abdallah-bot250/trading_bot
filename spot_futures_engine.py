from datetime import datetime


TYPE_MEMORY = {
    "recent_types": [],
    "spot_today": 0,
    "futures_today": 0,
    "date": datetime.utcnow().date().isoformat(),
}


def _reset_daily_memory_if_needed():
    today = datetime.utcnow().date().isoformat()
    if TYPE_MEMORY.get("date") != today:
        TYPE_MEMORY["date"] = today
        TYPE_MEMORY["spot_today"] = 0
        TYPE_MEMORY["futures_today"] = 0


def _clamp(value, low=0, high=100):
    return max(low, min(high, int(round(value))))


def evaluate_trade_types(direction, trend, trend_power, confidence, htf_ok, structure, volume, volatility_state, risk_score, timeframe):
    confidence = float(confidence or 0)
    risk_score = float(risk_score or 50)

    spot_score = 42
    futures_score = 42

    if direction == "LONG":
        spot_score += 10
        if trend == "UP":
            spot_score += 10
        if trend_power == "STRONG_BULL":
            spot_score += 14
        if structure in ["NEAR_BREAKOUT_HIGH", "MID_RANGE", "BULLISH_STRUCTURE"]:
            spot_score += 8
    else:
        futures_score += 10

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        futures_score += 12
    if volume == "STRONG":
        spot_score += 5
        futures_score += 7
    if htf_ok:
        spot_score += 8
        futures_score += 8

    if volatility_state == "TRADEABLE":
        spot_score += 7
        futures_score += 8
    elif volatility_state == "HIGH":
        futures_score += 6
        spot_score -= 5
    elif volatility_state == "EXTREME":
        futures_score -= 10
        spot_score -= 12
    elif volatility_state == "TOO_QUIET":
        spot_score -= 8
        futures_score -= 8

    if timeframe == "1h":
        spot_score += 5
    elif timeframe in ["15m", "30m"]:
        futures_score += 5

    spot_score += (confidence - 70) * 0.25
    futures_score += (confidence - 70) * 0.28
    spot_score -= max(0, risk_score - 45) * 0.30
    futures_score -= max(0, risk_score - 55) * 0.26

    return {
        "SPOT": _clamp(spot_score),
        "FUTURES": _clamp(futures_score),
    }


def choose_trade_type(type_scores):
    _reset_daily_memory_if_needed()
    scores = dict(type_scores or {})

    recent = TYPE_MEMORY.get("recent_types", [])
    if len(recent) >= 3 and len(set(recent[-3:])) == 1:
        dominant = recent[-1]
        other = "SPOT" if dominant == "FUTURES" else "FUTURES"
        scores[other] = scores.get(other, 0) + 10

    if TYPE_MEMORY.get("spot_today", 0) == 0:
        scores["SPOT"] = scores.get("SPOT", 0) + 4
    if TYPE_MEMORY.get("futures_today", 0) == 0:
        scores["FUTURES"] = scores.get("FUTURES", 0) + 4

    selected = "SPOT" if scores.get("SPOT", 0) >= scores.get("FUTURES", 0) else "FUTURES"
    if selected == "SPOT" and scores.get("SPOT", 0) < 55 and scores.get("FUTURES", 0) >= 55:
        selected = "FUTURES"
    if selected == "FUTURES" and scores.get("FUTURES", 0) < 55 and scores.get("SPOT", 0) >= 55:
        selected = "SPOT"

    return selected, scores


def record_trade_type(trade_type):
    _reset_daily_memory_if_needed()
    trade_type = str(trade_type or "FUTURES").upper()
    TYPE_MEMORY["recent_types"].append(trade_type)
    TYPE_MEMORY["recent_types"] = TYPE_MEMORY["recent_types"][-8:]
    if trade_type == "SPOT":
        TYPE_MEMORY["spot_today"] += 1
    elif trade_type == "FUTURES":
        TYPE_MEMORY["futures_today"] += 1


def type_allowed_for_user(signal_type, spot_enabled=True, futures_enabled=True):
    signal_type = str(signal_type or "FUTURES").upper()
    if signal_type == "SPOT":
        return bool(spot_enabled)
    if signal_type == "FUTURES":
        return bool(futures_enabled)
    return False
