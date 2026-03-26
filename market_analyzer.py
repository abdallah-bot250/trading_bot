import requests
import pandas as pd
import numpy as np
from ai_model import predict_trade

# ================= SETTINGS =================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
TIMEFRAMES = ["5m", "15m", "1h"]

REQUEST_TIMEOUT = 10
MIN_SCORE_TO_TRADE = 5
MIN_CONFIDENCE = 70

# ================= MARKET DATA =================
def get_market_data(symbol, interval="5m", limit=250):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()

        if not isinstance(data, list):
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
    except:
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
    ema50 = ema(df, 50)
    ema200 = ema(df, 200)

    if len(df) < 200:
        return "UNKNOWN"

    if ema50.iloc[-1] > ema200.iloc[-1]:
        return "UP"
    else:
        return "DOWN"

def trend_strength(df):
    ema20 = ema(df, 20)
    ema50 = ema(df, 50)
    ema200 = ema(df, 200)

    if len(df) < 200:
        return "WEAK"

    if ema20.iloc[-1] > ema50.iloc[-1] > ema200.iloc[-1]:
        return "STRONG_BULL"
    elif ema20.iloc[-1] < ema50.iloc[-1] < ema200.iloc[-1]:
        return "STRONG_BEAR"
    return "MIXED"

# ================= VOLUME =================
def volume_strength(df):
    avg_volume = df["volume"].rolling(20).mean()
    if pd.notna(avg_volume.iloc[-1]) and df["volume"].iloc[-1] > avg_volume.iloc[-1] * 1.2:
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

    if current >= recent_high * 0.995:
        return "NEAR_BREAKOUT_HIGH"
    elif current <= recent_low * 1.005:
        return "NEAR_BREAKOUT_LOW"
    return "MID_RANGE"

# ================= VOLATILITY FILTER =================
def volatility_ok(df):
    try:
        atr_val = atr(df).iloc[-1]
        close_val = df["close"].iloc[-1]

        if pd.isna(atr_val) or close_val <= 0:
            return False

        ratio = atr_val / close_val

        # منع السوق الميت أو المبالغ فيه
        return 0.002 <= ratio <= 0.05
    except:
        return False

# ================= NEWS FILTER =================
def news_filter():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()

        titles = [x["title"].lower() for x in data.get("Data", [])[:8]]
        danger = [
            "crash", "hack", "ban", "sec", "regulation",
            "lawsuit", "exploit", "liquidation", "collapse"
        ]

        for t in titles:
            for k in danger:
                if k in t:
                    return False
        return True
    except:
        return True

# ================= AI SCORE =================
def ai_score(rsi_val, macd_val, signal_val, trend, volume, smc, trend_power, structure):
    score = 0

    # RSI
    if rsi_val < 30:
        score += 3
    elif rsi_val > 70:
        score -= 3
    elif 45 <= rsi_val <= 60:
        score += 1

    # MACD
    if macd_val > signal_val:
        score += 3
    else:
        score -= 3

    # TREND
    if trend == "UP":
        score += 2
    elif trend == "DOWN":
        score -= 2

    # VOLUME
    if volume == "STRONG":
        score += 2

    # SMC
    if smc == "LIQUIDITY_BREAK_UP":
        score += 3
    elif smc == "LIQUIDITY_BREAK_DOWN":
        score -= 3

    # TREND POWER
    if trend_power == "STRONG_BULL":
        score += 2
    elif trend_power == "STRONG_BEAR":
        score -= 2

    # STRUCTURE
    if structure == "NEAR_BREAKOUT_HIGH":
        score += 2
    elif structure == "NEAR_BREAKOUT_LOW":
        score -= 2

    return score

# ================= TP / SL =================
def dynamic_targets(entry, direction, atr_value):
    if pd.isna(atr_value) or atr_value <= 0:
        if direction == "LONG":
            return entry * 1.03, entry * 0.98
        else:
            return entry * 0.97, entry * 1.02

    if direction == "LONG":
        tp = entry + (atr_value * 2.2)
        sl = entry - (atr_value * 1.2)
    else:
        tp = entry - (atr_value * 2.2)
        sl = entry + (atr_value * 1.2)

    return tp, sl

# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure):
    confidence = 60 + abs(score) * 4

    if volume == "STRONG":
        confidence += 3

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 3

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 4

    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 3

    return min(97, max(50, int(confidence)))

# ================= GENERATE PAID SIGNAL =================
def generate_signal(symbol, interval="5m"):
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 200:
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

    news_ok = news_filter()

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

    if not news_ok:
        return None

    if score >= MIN_SCORE_TO_TRADE:
        direction = "LONG"
    elif score <= -MIN_SCORE_TO_TRADE:
        direction = "SHORT"
    else:
        return None

    # فلترة ضد الترند القوي
    if direction == "LONG" and trend_power == "STRONG_BEAR":
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL":
        return None

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val)

    confidence = calculate_confidence(score, volume, smc, trend_power, structure)

    # المدفوع يفضل قوي
    if confidence < MIN_CONFIDENCE:
        return None

    # نوع الصفقة
    if direction == "LONG" and confidence < 82:
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

    # AI FILTER صارم للمدفوع
    try:
        if not predict_trade(signal):
            return None
    except:
        return None

    return signal


# ================= GENERATE FREE SIGNAL =================
def generate_free_signal(symbol, interval="5m"):
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 200:
        return None

    # للمجاني: نخلي الفلتر أخف شوية
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

    # أخف من المدفوع
    relaxed_score = max(MIN_SCORE_TO_TRADE - 4, 1)

    if score >= relaxed_score:
        direction = "LONG"
    elif score <= -relaxed_score:
        direction = "SHORT"
    else:
        return None

    # فلترة ضد الترند القوي
    if direction == "LONG" and trend_power == "STRONG_BEAR":
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL":
        return None

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val)

    confidence = calculate_confidence(score, volume, smc, trend_power, structure)

    # أخف بوضوح للمجاني
    if confidence < 45:
        return None

    if direction == "LONG" and confidence < 82:
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

    # AI FILTER أخف للمجاني
    try:
        ai_result = predict_trade(signal)
        if ai_result is False and confidence < 70:
            return None
    except:
        pass

    return signal


# ================= FREE SIGNALS ONLY =================
def get_top_free_signals(limit=2):
    signals = []

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            try:
                s = generate_free_signal(symbol, tf)

                if s:
                    ranking_score = float(s.get("confidence", 0)) + abs(float(s.get("score", 0)))
                    s["ranking_score"] = ranking_score
                    signals.append(s)
            except:
                continue

    signals = sorted(signals, key=lambda x: x["ranking_score"], reverse=True)

    unique_signals = []
    used_pairs = set()

    for signal in signals:
        if signal["pair"] not in used_pairs:
            unique_signals.append(signal)
            used_pairs.add(signal["pair"])

        if len(unique_signals) >= limit:
            break

    return unique_signals[:limit]