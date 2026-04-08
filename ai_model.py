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

        # بدل reject سريع، نخليه scoring أذكى
        if rr >= 2.8:
            score += 7
        elif rr >= 2.6:
            score += 6
        elif rr >= 2.3:
            score += 5
        elif rr >= 2.0:
            score += 4
        elif rr >= 1.8:
            score += 3
        elif rr >= 1.7:
            score += 2
        else:
            return False

        # ================= DISTANCE CHECK =================
        tp_distance = abs(tp - entry) / entry
        sl_distance = abs(sl - entry) / entry

        # حماية فقط من الأهداف الميتة
        if entry < 0.1:
            if tp_distance < 0.015:
                return False
            if sl_distance < 0.006:
                return False
        elif entry < 1:
            if tp_distance < 0.012:
                return False
            if sl_distance < 0.005:
                return False
        elif entry < 10:
            if tp_distance < 0.009:
                return False
            if sl_distance < 0.0042:
                return False
        elif entry < 100:
            if tp_distance < 0.008:
                return False
            if sl_distance < 0.0036:
                return False
        else:
            if tp_distance < 0.007:
                return False
            if sl_distance < 0.003:
                return False

        # نقاط إضافية حسب مساحة الهدف
        if tp_distance >= 0.03:
            score += 6
        elif tp_distance >= 0.025:
            score += 5
        elif tp_distance >= 0.018:
            score += 4
        elif tp_distance >= 0.013:
            score += 3
        elif tp_distance >= 0.009:
            score += 2
        else:
            score += 1

        # ================= STOP LOSS QUALITY =================
        # SL لو واسع جدًا بشكل غير منطقي = جودة أقل
        if sl_distance > 0.035:
            score -= 3
        elif sl_distance > 0.025:
            score -= 2
        elif sl_distance > 0.018:
            score -= 1

        # ================= CONFIDENCE =================
        # هنا confidence يقيّم فقط، مش يقتل الصفقة لوحده
        if confidence >= 86:
            score += 6
        elif confidence >= 82:
            score += 5
        elif confidence >= 78:
            score += 4
        elif confidence >= 74:
            score += 3
        elif confidence >= 68:
            score += 2
        elif confidence >= 64:
            score += 1
        else:
            return False

        # ================= TREND =================
        if trend == "UP" and direction == "LONG":
            score += 3
        elif trend == "DOWN" and direction == "SHORT":
            score += 3
        elif trend == "UNKNOWN":
            score -= 1
        else:
            score -= 2

        # ================= TREND POWER =================
        if trend_power == "STRONG_BULL" and direction == "LONG":
            score += 5
        elif trend_power == "STRONG_BEAR" and direction == "SHORT":
            score += 5
        elif trend_power == "MIXED":
            score -= 2
        elif trend_power == "WEAK":
            score -= 3

        # نمنع فقط العكس الصريح جدًا
        if trend_power == "STRONG_BULL" and direction == "SHORT" and confidence < 82:
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG" and confidence < 82:
            return False

        # ================= VOLUME =================
        if volume == "STRONG":
            score += 4
        else:
            score -= 1

        # ================= SMART MONEY =================
        if smc == "LIQUIDITY_BREAK_UP" and direction == "LONG":
            score += 5
        elif smc == "LIQUIDITY_BREAK_DOWN" and direction == "SHORT":
            score += 5
        elif smc == "RANGE":
            score -= 3
        else:
            score -= 1

        # ================= STRUCTURE =================
        if structure == "NEAR_BREAKOUT_HIGH" and direction == "LONG":
            score += 4
        elif structure == "NEAR_BREAKOUT_LOW" and direction == "SHORT":
            score += 4
        elif structure == "MID_RANGE":
            score -= 2
        elif structure == "UNKNOWN":
            score -= 2

        # ================= TIMEFRAME =================
        if tf == "1h":
            score += 5
        elif tf == "15m":
            score += 4
        elif tf == "5m":
            score += 2
        else:
            score -= 1

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
            score += 5

        # ================= EXTRA QUALITY FILTER =================
        # لو الهدف كبير لكن الستوب أكبر من اللازم → reject
        if rr < 1.9 and sl_distance > 0.012 and tf == "5m":
            return False

        # 5m لازم تكون أنضف شوية
        if tf == "5m":
            if confidence < 72:
                return False
            if trend_power == "MIXED" and volume != "STRONG":
                return False

        # ================= MONSTER FILTER =================
        if (
            trend_power == "MIXED"
            and volume != "STRONG"
            and smc == "RANGE"
        ):
            return False

        # ================= WEAK COMBO FILTER =================
        if confidence < 70 and tp_distance < 0.01:
            return False

        if rr < 1.7 and tf == "5m":
            return False

        # ================= BAD STRUCTURE FILTER =================
        # يمنع الصفقة لو structure ضعيف جدًا + trend ضعيف
        if structure == "MID_RANGE" and trend_power == "WEAK":
            return False

        # ================= FINAL DECISION =================
        # Threshold واقعي ومناسب بعد التعديلات
        return score >= 15

    except Exception as e:
        print(f"AI ERROR: {e}")
        return False