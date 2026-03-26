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
MIN_SCORE_TO_TRADE = 2
MIN_CONFIDENCE = 50


# ================= MARKET DATA =================
def get_market_data(symbol, interval="5m", limit=250):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = response.json()

        if not isinstance(data, list) or len(data) == 0:
            return None

        df = pd.DataFrame(data)
        if df.empty:
            return None

        df = df[[0, 1, 2, 3, 4, 5]]
        df.columns = ["time", "open", "high", "low", "close", "volume"]

        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        return df
    except Exception as e:
        print(f"get_market_data error {symbol} {interval}: {e}")
        return None


# ================= RSI =================
def rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean().replace(0, np.nan)

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ================= MACD =================
def macd(df):
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()

    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    return macd_line, signal_line


# ================= EMA =================
def ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()


# ================= ATR =================
def atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ================= TREND =================
def detect_trend(df):
    if len(df) < 50:
        return "UNKNOWN"

    ema20 = ema(df, 20)
    ema50 = ema(df, 50)

    if ema20.iloc[-1] > ema50.iloc[-1]:
        return "UP"
    return "DOWN"


def trend_strength(df):
    if len(df) < 50:
        return "WEAK"

    ema20 = ema(df, 20)
    ema50 = ema(df, 50)
    ema100 = ema(df, 100)

    if ema20.iloc[-1] > ema50.iloc[-1] > ema100.iloc[-1]:
        return "STRONG_BULL"
    elif ema20.iloc[-1] < ema50.iloc[-1] < ema100.iloc[-1]:
        return "STRONG_BEAR"
    return "MIXED"


# ================= VOLUME =================
def volume_strength(df):
    avg_volume = df["volume"].rolling(20).mean()

    if pd.notna(avg_volume.iloc[-1]) and df["volume"].iloc[-1] > avg_volume.iloc[-1] * 1.03:
        return "STRONG"

    return "WEAK"


# ================= SMART MONEY =================
def detect_smc(df):
    highs = df["high"].rolling(10).max()
    lows = df["low"].rolling(10).min()

    if len(df) < 12:
        return "RANGE"

    if pd.notna(highs.iloc[-2]) and df["close"].iloc[-1] > highs.iloc[-2]:
        return "LIQUIDITY_BREAK_UP"
    elif pd.notna(lows.iloc[-2]) and df["close"].iloc[-1] < lows.iloc[-2]:
        return "LIQUIDITY_BREAK_DOWN"

    return "RANGE"


# ================= STRUCTURE =================
def market_structure(df):
    if len(df) < 20:
        return "UNKNOWN"

    recent_high = df["high"].tail(20).max()
    recent_low = df["low"].tail(20).min()
    current = df["close"].iloc[-1]

    if current >= recent_high * 0.998:
        return "NEAR_BREAKOUT_HIGH"
    elif current <= recent_low * 1.002:
        return "NEAR_BREAKOUT_LOW"

    return "MID_RANGE"


# ================= VOLATILITY FILTER =================
def volatility_ok(df):
    try:
        atr_val = atr(df).iloc[-1]
        close_val = df["close"].iloc[-1]

        if pd.isna(atr_val) or close_val <= 0:
            return True

        ratio = atr_val / close_val
        return 0.0003 <= ratio <= 0.10
    except:
        return True


# ================= AI SCORE =================
def ai_score(rsi_val, macd_val, signal_val, trend, volume, smc, trend_power, structure):
    score = 0

    if rsi_val < 35:
        score += 2
    elif rsi_val > 65:
        score -= 2
    elif 42 <= rsi_val <= 60:
        score += 1

    if macd_val > signal_val:
        score += 2
    else:
        score -= 2

    if trend == "UP":
        score += 1
    elif trend == "DOWN":
        score -= 1

    if volume == "STRONG":
        score += 1

    if smc == "LIQUIDITY_BREAK_UP":
        score += 2
    elif smc == "LIQUIDITY_BREAK_DOWN":
        score -= 2

    if trend_power == "STRONG_BULL":
        score += 1
    elif trend_power == "STRONG_BEAR":
        score -= 1

    if structure == "NEAR_BREAKOUT_HIGH":
        score += 1
    elif structure == "NEAR_BREAKOUT_LOW":
        score -= 1

    return score


# ================= TP / SL =================
def dynamic_targets(entry, direction, atr_value):
    if pd.isna(atr_value) or atr_value <= 0:
        if direction == "LONG":
            return entry * 1.015, entry * 0.992
        else:
            return entry * 0.985, entry * 1.008

    if direction == "LONG":
        tp = entry + (atr_value * 1.5)
        sl = entry - (atr_value * 0.8)
    else:
        tp = entry - (atr_value * 1.5)
        sl = entry + (atr_value * 0.8)

    return tp, sl


# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure):
    confidence = 58 + abs(score) * 5

    if volume == "STRONG":
        confidence += 3

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 3

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 2

    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 2

    return min(92, max(50, int(confidence)))


# ================= GENERATE FREE SIGNAL =================
def generate_free_signal(symbol, interval="5m"):
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 50:
        return None

    if not volatility_ok(df):
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

    if pd.isna(rsi_val) or pd.isna(macd_val) or pd.isna(signal_val):
        return None

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

    # ===== فتح السوق بالقوة بدل الخنق =====
    if score >= 0:
        direction = "LONG"
    else:
        direction = "SHORT"

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val)
    confidence = calculate_confidence(score, volume, smc, trend_power, structure)

    if confidence < MIN_CONFIDENCE:
        return None

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

    return signal


# ================= TOP FREE SIGNALS =================
def get_top_free_signals(limit=2):
    candidates = []

    print(f"Dynamic symbols loaded: {SYMBOLS}")

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            try:
                signal = generate_free_signal(symbol, tf)
                if signal:
                    signal["ranking_score"] = signal["confidence"] + abs(signal["score"])
                    candidates.append(signal)
                    print(f"Signal candidate found: {signal['pair']} {signal['timeframe']} {signal['direction']} conf={signal['confidence']}")
            except Exception as e:
                print(f"Signal generation error for {symbol} {tf}: {e}")
                continue

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