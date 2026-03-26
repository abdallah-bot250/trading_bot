import requests
import pandas as pd
import numpy as np

# ================= SETTINGS =================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
    "DOTUSDT", "LTCUSDT", "TRXUSDT", "NEARUSDT", "APTUSDT"
]

TIMEFRAMES = ["5m", "15m"]
REQUEST_TIMEOUT = 10


# ================= MARKET DATA =================
def get_market_data(symbol, interval="5m", limit=250):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            print(f"❌ No kline data for {symbol} {interval}")
            return None

        df = pd.DataFrame(data)
        if df.empty:
            print(f"❌ Empty dataframe for {symbol} {interval}")
            return None

        df = df[[0, 1, 2, 3, 4, 5]]
        df.columns = ["time", "open", "high", "low", "close", "volume"]

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        return df

    except Exception as e:
        print(f"❌ get_market_data error {symbol} {interval}: {e}")
        return None


# ================= RSI =================
def rsi(df, period=14):
    try:
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        avg_loss = avg_loss.replace(0, 0.000001)
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    except:
        return pd.Series([50] * len(df))


# ================= MACD =================
def macd(df):
    try:
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()

        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        return macd_line, signal_line
    except:
        fallback = pd.Series([0] * len(df))
        return fallback, fallback


# ================= EMA =================
def ema(df, period):
    try:
        return df["close"].ewm(span=period, adjust=False).mean()
    except:
        return pd.Series([0] * len(df))


# ================= ATR =================
def atr(df, period=14):
    try:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean().fillna(method="bfill").fillna(0)
    except:
        return pd.Series([0] * len(df))


# ================= TREND =================
def detect_trend(df):
    try:
        ema20 = ema(df, 20)
        ema50 = ema(df, 50)
        return "UP" if ema20.iloc[-1] >= ema50.iloc[-1] else "DOWN"
    except:
        return "UP"


def trend_strength(df):
    try:
        ema20 = ema(df, 20)
        ema50 = ema(df, 50)
        ema100 = ema(df, 100)

        if ema20.iloc[-1] > ema50.iloc[-1] > ema100.iloc[-1]:
            return "STRONG_BULL"
        elif ema20.iloc[-1] < ema50.iloc[-1] < ema100.iloc[-1]:
            return "STRONG_BEAR"
        return "MIXED"
    except:
        return "MIXED"


# ================= VOLUME =================
def volume_strength(df):
    try:
        avg_volume = df["volume"].rolling(20).mean()
        if pd.notna(avg_volume.iloc[-1]) and df["volume"].iloc[-1] >= avg_volume.iloc[-1]:
            return "STRONG"
        return "WEAK"
    except:
        return "WEAK"


# ================= SMART MONEY =================
def detect_smc(df):
    try:
        highs = df["high"].rolling(10).max()
        lows = df["low"].rolling(10).min()

        if pd.notna(highs.iloc[-2]) and df["close"].iloc[-1] > highs.iloc[-2]:
            return "LIQUIDITY_BREAK_UP"
        elif pd.notna(lows.iloc[-2]) and df["close"].iloc[-1] < lows.iloc[-2]:
            return "LIQUIDITY_BREAK_DOWN"

        return "RANGE"
    except:
        return "RANGE"


# ================= STRUCTURE =================
def market_structure(df):
    try:
        recent_high = df["high"].tail(20).max()
        recent_low = df["low"].tail(20).min()
        current = df["close"].iloc[-1]

        if current >= recent_high * 0.998:
            return "NEAR_BREAKOUT_HIGH"
        elif current <= recent_low * 1.002:
            return "NEAR_BREAKOUT_LOW"

        return "MID_RANGE"
    except:
        return "MID_RANGE"


# ================= SCORE =================
def ai_score(rsi_val, macd_val, signal_val, trend, volume, smc, trend_power, structure):
    score = 0

    # RSI
    if rsi_val < 35:
        score += 2
    elif rsi_val > 65:
        score -= 2
    else:
        score += 1

    # MACD
    if macd_val >= signal_val:
        score += 2
    else:
        score -= 2

    # TREND
    if trend == "UP":
        score += 1
    else:
        score -= 1

    # VOLUME
    if volume == "STRONG":
        score += 1

    # SMC
    if smc == "LIQUIDITY_BREAK_UP":
        score += 2
    elif smc == "LIQUIDITY_BREAK_DOWN":
        score -= 2

    # TREND POWER
    if trend_power == "STRONG_BULL":
        score += 1
    elif trend_power == "STRONG_BEAR":
        score -= 1

    # STRUCTURE
    if structure == "NEAR_BREAKOUT_HIGH":
        score += 1
    elif structure == "NEAR_BREAKOUT_LOW":
        score -= 1

    return score


# ================= TP / SL =================
def dynamic_targets(entry, direction, atr_value):
    try:
        if pd.isna(atr_value) or atr_value <= 0:
            atr_value = entry * 0.005

        if direction == "LONG":
            tp = entry + (atr_value * 1.5)
            sl = entry - (atr_value * 0.8)
        else:
            tp = entry - (atr_value * 1.5)
            sl = entry + (atr_value * 0.8)

        return tp, sl
    except:
        if direction == "LONG":
            return entry * 1.01, entry * 0.995
        else:
            return entry * 0.99, entry * 1.005


# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure):
    confidence = 60 + abs(score) * 4

    if volume == "STRONG":
        confidence += 2

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 2

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 2

    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 2

    return min(92, max(55, int(confidence)))


# ================= ALWAYS GENERATE SIGNAL =================
def generate_free_signal(symbol, interval="5m"):
    try:
        df = get_market_data(symbol, interval)
        if df is None or len(df) < 30:
            return None

        df["rsi"] = rsi(df)
        macd_line, signal_line = macd(df)
        df["atr"] = atr(df)

        trend = detect_trend(df)
        trend_power = trend_strength(df)
        volume = volume_strength(df)
        smc = detect_smc(df)
        structure = market_structure(df)

        rsi_val = df["rsi"].iloc[-1]
        macd_val = macd_line.iloc[-1]
        signal_val = signal_line.iloc[-1]
        atr_val = df["atr"].iloc[-1]
        entry = float(df["close"].iloc[-1])

        if pd.isna(rsi_val):
            rsi_val = 50
        if pd.isna(macd_val):
            macd_val = 0
        if pd.isna(signal_val):
            signal_val = 0
        if pd.isna(atr_val) or atr_val <= 0:
            atr_val = entry * 0.005

        score = ai_score(
            rsi_val,
            macd_val,
            signal_val,
            trend,
            volume,
            smc,
            trend_power,
            structure
        )

        # ======== هنا النووي الحقيقي ========
        # مفيش return None
        direction = "LONG" if score >= 0 else "SHORT"

        tp, sl = dynamic_targets(entry, direction, atr_val)
        confidence = calculate_confidence(score, volume, smc, trend_power, structure)

        if direction == "LONG" and confidence < 80:
            trade_type = "SPOT"
        else:
            trade_type = "FUTURES"

        signal = {
            "pair": symbol,
            "timeframe": interval,
            "type": trade_type,
            "direction": direction,
            "entry": round(entry, 4),
            "tp": round(tp, 4),
            "sl": round(sl, 4),
            "confidence": confidence,
            "trend": trend,
            "volume": volume,
            "smc": smc,
            "trend_power": trend_power,
            "structure": structure,
            "score": score
        }

        print(f"✅ SIGNAL BUILT: {signal['pair']} {signal['timeframe']} {signal['direction']} conf={signal['confidence']} score={signal['score']}")
        return signal

    except Exception as e:
        print(f"❌ generate_free_signal error {symbol} {interval}: {e}")
        return None


# ================= TOP FREE SIGNALS =================
def get_top_free_signals(limit=2):
    candidates = []

    print(f"Dynamic symbols loaded: {SYMBOLS}")

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            signal = generate_free_signal(symbol, tf)
            if signal:
                signal["ranking_score"] = signal["confidence"] + abs(signal["score"])
                candidates.append(signal)

    # لو حتى السوق مجنون/هادي -> هيرتب وخلاص
    candidates = sorted(candidates, key=lambda x: x["ranking_score"], reverse=True)

    best = []
    used_pairs = set()

    for s in candidates:
        if s["pair"] not in used_pairs:
            best.append(s)
            used_pairs.add(s["pair"])

        if len(best) >= limit:
            break

    print(f"Top signals selected: {best}")
    return best