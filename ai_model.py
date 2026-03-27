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

        # فلتر أساسي صارم
        if rr < 1.7:
            return False

        if rr >= 2.8:
            score += 5
        elif rr >= 2.3:
            score += 4
        elif rr >= 2.0:
            score += 3
        elif rr >= 1.8:
            score += 2
        else:
            score += 1

        # ================= DISTANCE CHECK =================
        tp_distance = abs(tp - entry) / entry
        sl_distance = abs(sl - entry) / entry

        # 🔥 حماية حسب سعر العملة
        if entry < 0.1:
            if tp_distance < 0.015:
                return False
            if sl_distance < 0.0055:
                return False

        elif entry < 1:
            if tp_distance < 0.012:
                return False
            if sl_distance < 0.0045:
                return False

        elif entry < 100:
            if tp_distance < 0.008:
                return False
            if sl_distance < 0.0035:
                return False

        else:
            if tp_distance < 0.007:
                return False
            if sl_distance < 0.003:
                return False

        # Boost على حسب بعد الهدف
        if tp_distance >= 0.025:
            score += 5
        elif tp_distance >= 0.02:
            score += 4
        elif tp_distance >= 0.015:
            score += 3
        elif tp_distance >= 0.01:
            score += 2
        else:
            score += 1

        # ================= CONFIDENCE =================
        if confidence < 68:
            return False

        if confidence >= 93:
            score += 6
        elif confidence >= 89:
            score += 5
        elif confidence >= 84:
            score += 4
        elif confidence >= 78:
            score += 3
        elif confidence >= 72:
            score += 2
        else:
            score += 1

        # ================= TREND =================
        if trend == "UP" and direction == "LONG":
            score += 3
        elif trend == "DOWN" and direction == "SHORT":
            score += 3
        else:
            score -= 4

        # ================= TREND POWER =================
        if trend_power == "STRONG_BULL" and direction == "LONG":
            score += 5
        elif trend_power == "STRONG_BEAR" and direction == "SHORT":
            score += 5
        elif trend_power == "MIXED":
            score -= 4
        else:
            score -= 1

        # ❌ عكس الترند القوي = رفض مباشر
        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False

        # ================= VOLUME =================
        if volume == "STRONG":
            score += 4
        else:
            score -= 2

        # ================= SMART MONEY =================
        if smc == "LIQUIDITY_BREAK_UP" and direction == "LONG":
            score += 5
        elif smc == "LIQUIDITY_BREAK_DOWN" and direction == "SHORT":
            score += 5
        elif smc == "RANGE":
            score -= 3
        else:
            score -= 2

        # ================= STRUCTURE =================
        if structure == "NEAR_BREAKOUT_HIGH" and direction == "LONG":
            score += 4
        elif structure == "NEAR_BREAKOUT_LOW" and direction == "SHORT":
            score += 4
        elif structure == "MID_RANGE":
            score -= 4
        elif structure == "UNKNOWN":
            score -= 3

        # ================= TIMEFRAME =================
        if tf == "1h":
            score += 5
        elif tf == "15m":
            score += 4
        elif tf == "5m":
            score += 2
        else:
            score += 0

        # ================= SMART BOOST =================
        if (
            direction == "LONG"
            and trend == "UP"
            and structure == "NEAR_BREAKOUT_HIGH"
        ):
            score += 3

        if (
            direction == "SHORT"
            and trend == "DOWN"
            and structure == "NEAR_BREAKOUT_LOW"
        ):
            score += 3

        # ================= POWER BOOST =================
        if (
            volume == "STRONG"
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            and smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]
        ):
            score += 5

        # ================= MONSTER FILTER =================
        if (
            trend_power == "MIXED"
            and volume != "STRONG"
            and smc == "RANGE"
        ):
            return False

        if confidence < 72 and tp_distance < 0.01:
            return False

        if rr < 1.8 and tf == "5m":
            return False

        # رفض الصفقات اللي جودتها شكلية فقط
        weak_factors = 0

        if volume != "STRONG":
            weak_factors += 1

        if smc == "RANGE":
            weak_factors += 1

        if structure in ["MID_RANGE", "UNKNOWN"]:
            weak_factors += 1

        if trend_power == "MIXED":
            weak_factors += 1

        if confidence < 75:
            weak_factors += 1

        if weak_factors >= 3:
            return False

        # ================= FINAL DECISION =================
        return score >= 12

    except Exception as e:
        print(f"AI ERROR: {e}")
        return False