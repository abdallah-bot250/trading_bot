import numpy as np

# ================= AI DECISION ENGINE =================

def predict_trade(signal):
    score = 0

    try:
        entry = float(signal.get("entry", 0))
        tp = float(signal.get("tp", 0))
        sl = float(signal.get("sl", 0))
        direction = signal.get("direction")

        if entry <= 0 or tp <= 0 or sl <= 0:
            return False

        # ================= RISK REWARD =================
        if direction == "LONG":
            reward = tp - entry
            risk = entry - sl
        elif direction == "SHORT":
            reward = entry - tp
            risk = sl - entry
        else:
            return False

        if reward <= 0 or risk <= 0:
            return False

        rr = reward / risk

        # 🔥 فلتر RR
        if rr >= 2:
            score += 3
        elif rr >= 1.5:
            score += 2
        elif rr >= 1.2:
            score += 1
        else:
            return False  # ❌ صفقة ضعيفة

        # ================= CONFIDENCE =================
        confidence = signal.get("confidence", 0)

        if confidence >= 90:
            score += 4
        elif confidence >= 80:
            score += 3
        elif confidence >= 70:
            score += 2
        else:
            return False  # ❌ استبعد الضعيف

        # ================= TREND =================
        trend = signal.get("trend")
        trend_power = signal.get("trend_power")

        if trend == "UP" and direction == "LONG":
            score += 2
        elif trend == "DOWN" and direction == "SHORT":
            score += 2
        else:
            score -= 2

        # 🔥 قوة الترند
        if trend_power == "STRONG_BULL" and direction == "LONG":
            score += 3
        elif trend_power == "STRONG_BEAR" and direction == "SHORT":
            score += 3
        elif trend_power == "MIXED":
            score -= 2

        # ================= VOLUME =================
        if signal.get("volume") == "STRONG":
            score += 2
        else:
            score -= 1

        # ================= SMART MONEY =================
        smc = signal.get("smc")

        if smc == "LIQUIDITY_BREAK_UP" and direction == "LONG":
            score += 3
        elif smc == "LIQUIDITY_BREAK_DOWN" and direction == "SHORT":
            score += 3
        else:
            score -= 2

        # ================= STRUCTURE =================
        structure = signal.get("structure")

        if structure == "NEAR_BREAKOUT_HIGH" and direction == "LONG":
            score += 2
        elif structure == "NEAR_BREAKOUT_LOW" and direction == "SHORT":
            score += 2
        elif structure == "MID_RANGE":
            score -= 2  # ❌ سوق عرضي

        # ================= TIMEFRAME =================
        tf = signal.get("timeframe")

        if tf == "1h":
            score += 3
        elif tf == "15m":
            score += 2
        elif tf == "5m":
            score += 1

        # ================= TP DISTANCE =================
        tp_distance = abs(tp - entry) / entry

        if tp_distance < 0.002:
            return False  # ❌ هدف قريب جدًا (زي مشكلتك القديمة)

        if tp_distance > 0.01:
            score += 2

        # ================= FINAL BOOST =================
        if (
            signal.get("volume") == "STRONG"
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            and smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]
        ):
            score += 3

        # ================= FINAL DECISION =================
        return score >= 8  # 🔥 كان 3 بقى 8 = فلترة قوية جدًا

    except Exception as e:
        print(f"AI ERROR: {e}")
        return False