import numpy as np

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