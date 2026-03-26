import requests
import pandas as pd
import numpy as np
from ai_model import predict_trade

# ================= SETTINGS =================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
    "DOTUSDT", "LTCUSDT", "TRXUSDT", "NEARUSDT", "APTUSDT"
]

TIMEFRAMES = ["5m", "15m"]

REQUEST_TIMEOUT = 12
MIN_SCORE_TO_TRADE = 5
MIN_CONFIDENCE = 70

# ================= MARKET DATA HELPERS =================
def interval_to_seconds(interval):
    mapping = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "8h": 28800,
        "12h": 43200,
        "1d": 86400,
    }
    return mapping.get(interval, 300)


def get_higher_tf(interval):
    mapping = {
        "5m": "15m",
        "15m": "1h",
        "30m": "4h",
        "1h": "4h",
        "4h": "1d"
    }
    return mapping.get(interval, "15m")


def parse_kucoin_klines_to_df(rows):
    try:
        if not rows or not isinstance(rows, list):
            return None

        parsed = []
        for row in rows:
            # KuCoin format:
            # [time, open, close, high, low, volume, turnover]
            if not isinstance(row, list) or len(row) < 6:
                continue

            parsed.append([
                int(row[0]) * 1000,
                float(row[1]),  # open
                float(row[3]),  # high
                float(row[4]),  # low
                float(row[2]),  # close
                float(row[5])   # volume
            ])

        if not parsed:
            return None

        df = pd.DataFrame(parsed, columns=["time", "open", "high", "low", "close", "volume"])
        return df
    except Exception as e:
        print(f"parse_kucoin_klines_to_df error: {e}")
        return None


def parse_binance_klines_to_df(data):
    try:
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
        print(f"parse_binance_klines_to_df error: {e}")
        return None


# ================= MARKET DATA =================
def get_market_data(symbol, interval="5m", limit=250):
    """
    Priority:
    1) Binance
    2) Binance US
    3) KuCoin
    """
    endpoints = [
        ("BINANCE", f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"),
        ("BINANCE_US", f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
    ]

    for source_name, url in endpoints:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            print(f"🌐 {source_name} STATUS {symbol} {interval}: {response.status_code}")

            try:
                data = response.json()
            except Exception:
                print(f"❌ {source_name} invalid JSON for {symbol} {interval}")
                data = None

            if isinstance(data, dict):
                print(f"⚠️ {source_name} API error for {symbol} {interval}: {data}")
                continue

            df = parse_binance_klines_to_df(data)
            if df is not None and not df.empty:
                return df

            print(f"❌ {source_name} no kline data for {symbol} {interval}")

        except Exception as e:
            print(f"❌ {source_name} request failed for {symbol} {interval}: {e}")

    # ---------- Fallback: KuCoin ----------
    try:
        kucoin_symbol = symbol.replace("USDT", "-USDT")
        kucoin_type = interval

        url = f"https://api.kucoin.com/api/v1/market/candles?type={kucoin_type}&symbol={kucoin_symbol}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        print(f"🌐 KUCOIN STATUS {symbol} {interval}: {response.status_code}")

        data = response.json()

        if not isinstance(data, dict):
            print(f"❌ KUCOIN invalid response for {symbol} {interval}: {data}")
            return None

        if data.get("code") != "200000":
            print(f"⚠️ KUCOIN API error for {symbol} {interval}: {data}")
            return None

        rows = data.get("data", [])
        if rows:
            rows = rows[:limit]

        df = parse_kucoin_klines_to_df(rows)
        if df is not None and not df.empty:
            print(f"✅ KUCOIN fallback success for {symbol} {interval}")
            return df

        print(f"❌ KUCOIN no kline data for {symbol} {interval}")
        return None

    except Exception as e:
        print(f"❌ KUCOIN request failed for {symbol} {interval}: {e}")
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

    if pd.notna(avg_volume.iloc[-1]) and df["volume"].iloc[-1] > avg_volume.iloc[-1] * 1.08:
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

    if current >= recent_high * 0.997:
        return "NEAR_BREAKOUT_HIGH"
    elif current <= recent_low * 1.003:
        return "NEAR_BREAKOUT_LOW"

    return "MID_RANGE"


# ================= CHOPPY MARKET FILTER =================
def is_choppy(df):
    try:
        if df is None or len(df) < 50:
            return True

        ema20 = ema(df, 20)
        ema50 = ema(df, 50)

        diff = abs(ema20.iloc[-1] - ema50.iloc[-1])
        price = df["close"].iloc[-1]

        if price <= 0:
            return True

        return (diff / price) < 0.0015
    except:
        return True


# ================= MOMENTUM FILTER =================
def strong_momentum(df):
    try:
        if df is None or len(df) < 5:
            return False

        last = df["close"].iloc[-1]
        prev = df["close"].iloc[-3]

        if prev <= 0:
            return False

        change = abs(last - prev) / prev

        return change > 0.002
    except:
        return False


# ================= HIGHER TF CONFIRMATION =================
def higher_timeframe_confirmation(symbol, direction, current_interval):
    try:
        higher_tf = get_higher_tf(current_interval)
        df_htf = get_market_data(symbol, higher_tf, limit=200)

        if df_htf is None or len(df_htf) < 50:
            return False

        trend_htf = detect_trend(df_htf)
        trend_power_htf = trend_strength(df_htf)

        if direction == "LONG":
            return trend_htf == "UP" or trend_power_htf == "STRONG_BULL"
        elif direction == "SHORT":
            return trend_htf == "DOWN" or trend_power_htf == "STRONG_BEAR"

        return False
    except Exception as e:
        print(f"higher_timeframe_confirmation error for {symbol} {current_interval}: {e}")
        return False


# ================= VOLATILITY FILTER =================
def volatility_ok(df):
    try:
        atr_val = atr(df).iloc[-1]
        close_val = df["close"].iloc[-1]

        if pd.isna(atr_val) or close_val <= 0:
            return True

        ratio = atr_val / close_val
        return 0.0007 <= ratio <= 0.06
    except:
        return True


# ================= NEWS FILTER =================
def news_filter():
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()

        titles = [x["title"].lower() for x in data.get("Data", [])[:6]]
        danger = [
            "crash", "hack", "ban", "sec", "regulation",
            "lawsuit", "exploit", "liquidation", "collapse"
        ]

        hits = 0
        for t in titles:
            for k in danger:
                if k in t:
                    hits += 1

        return hits < 4
    except:
        return True


# ================= AI SCORE =================
def ai_score(rsi_val, macd_val, signal_val, trend, volume, smc, trend_power, structure):
    score = 0

    # RSI
    if rsi_val < 32:
        score += 2
    elif rsi_val > 68:
        score -= 2
    elif 45 <= rsi_val <= 58:
        score += 1

    # MACD
    if macd_val > signal_val:
        score += 2
    else:
        score -= 2

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
        score += 2
    elif smc == "LIQUIDITY_BREAK_DOWN":
        score -= 2

    # TREND POWER
    if trend_power == "STRONG_BULL":
        score += 2
    elif trend_power == "STRONG_BEAR":
        score -= 2

    # STRUCTURE
    if structure == "NEAR_BREAKOUT_HIGH":
        score += 1
    elif structure == "NEAR_BREAKOUT_LOW":
        score -= 1

    return score


# ================= TP / SL =================
# ================= TP / SL =================
def dynamic_targets(entry, direction, atr_value):
    try:
        entry = float(entry)
        atr_value = float(atr_value) if atr_value is not None else 0
    except:
        atr_value = 0

    if pd.isna(atr_value) or atr_value <= 0:
        if direction == "LONG":
            return entry * 1.02, entry * 0.99
        else:
            return entry * 0.98, entry * 1.01

    # Minimum move protection
    min_move = entry * 0.003   # 0.3%
    real_move = max(atr_value * 1.8, min_move)

    if direction == "LONG":
        tp = entry + real_move
        sl = entry - (real_move * 0.65)
    else:
        tp = entry - real_move
        sl = entry + (real_move * 0.65)

    return tp, sl


# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure, momentum_ok=False, htf_ok=False):
    confidence = 58 + abs(score) * 4

    if volume == "STRONG":
        confidence += 4

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 4

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 5

    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 3

    if momentum_ok:
        confidence += 5

    if htf_ok:
        confidence += 7

    return min(96, max(50, int(confidence)))

# ================= PRICE FORMAT =================
def format_price(price):
    try:
        price = float(price)

        if price >= 1000:
            return round(price, 2)
        elif price >= 100:
            return round(price, 3)
        elif price >= 1:
            return round(price, 4)
        elif price >= 0.1:
            return round(price, 5)
        elif price >= 0.01:
            return round(price, 6)
        elif price >= 0.001:
            return round(price, 7)
        else:
            return round(price, 8)
    except:
        return price
    
    # ================= SIGNAL VALIDATION =================
def signal_levels_valid(entry, tp, sl, direction):
    try:
        entry = float(entry)
        tp = float(tp)
        sl = float(sl)

        if entry <= 0 or tp <= 0 or sl <= 0:
            return False

        if direction == "LONG":
            if not (tp > entry and sl < entry):
                return False

            reward = tp - entry
            risk = entry - sl

        elif direction == "SHORT":
            if not (tp < entry and sl > entry):
                return False

            reward = entry - tp
            risk = sl - entry
        else:
            return False

        if reward <= 0 or risk <= 0:
            return False

        # أقل حركة مطلوبة = 0.15%
        min_distance = entry * 0.0015
        if reward < min_distance or risk < min_distance:
            return False

        # لازم الـ RR يبقى معقول
        rr = reward / risk
        if rr < 1.2:
            return False

        return True
    except:
        return False
    
    # ================= STRONG SIGNAL FILTER =================
def strong_signal_filter(df, trend, trend_power, direction):
    try:
        if df is None or len(df) < 50:
            return False

        # ❌ لو السوق عرضي → ارفض
        if is_choppy(df):
            return False

        # ❌ لازم الاتجاه يكون واضح
        if trend_power == "MIXED":
            return False

        # ❌ منع عكس الترند القوي
        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False

        # ✅ لازم في حركة (Momentum)
        last = df["close"].iloc[-1]
        prev = df["close"].iloc[-4]

        if prev <= 0:
            return False

        move = abs(last - prev) / prev

        if move < 0.0025:  # 0.25%
            return False

        return True

    except:
        return False


# ================= GENERATE PAID SIGNAL =================
def generate_signal(symbol, interval="5m"):
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 100:
        return None

    if is_choppy(df):
        return None

    if not strong_momentum(df):
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

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)
    if not htf_ok:
        return None

    # فلترة ضد الاتجاه القوي المعاكس
    if direction == "LONG" and trend_power == "STRONG_BEAR":
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL":
        return None

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val)
    momentum_ok = strong_momentum(df)
    confidence = calculate_confidence(score, volume, smc, trend_power, structure, momentum_ok, htf_ok)

    if not signal_levels_valid(entry, tp, sl, direction):
      return None

    if confidence < MIN_CONFIDENCE:
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
        "entry": format_price(entry),
        "tp": format_price(tp),
        "sl": format_price(sl),
        "confidence": confidence,
        "trend": trend,
        "volume": volume,
        "smc": smc,
        "trend_power": trend_power,
        "structure": structure,
        "score": score
    }

    try:
        if not predict_trade(signal):
            return None
    except Exception as e:
        print(f"AI model error in generate_signal {symbol} {interval}: {e}")
        return None

    return signal


# ================= GENERATE FREE SIGNAL =================
def generate_free_signal(symbol, interval="5m"):
    df = get_market_data(symbol, interval)
    if df is None or len(df) < 50:
        return None

    # فلترة أخف للمجاني
    if is_choppy(df):
        return None

    if not strong_momentum(df):
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

    # المجاني مش مفتوح على البحري — لازم score محترم
    if score >= 3:
        direction = "LONG"
    elif score <= -3:
        direction = "SHORT"
    else:
        return None

    # تأكيد من فريم أعلى لكن أخف
    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)
    if not htf_ok and abs(score) < 6:
        return None

    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < 7:
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < 7:
        return None

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val)
    momentum_ok = strong_momentum(df)
    confidence = calculate_confidence(score, volume, smc, trend_power, structure, momentum_ok, htf_ok)


    if not signal_levels_valid(entry, tp, sl, direction):
       return None

    if confidence < 60:
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
        "entry": format_price(entry),
        "tp": format_price(tp),
        "sl": format_price(sl),
        "confidence": confidence,
        "trend": trend,
        "volume": volume,
        "smc": smc,
        "trend_power": trend_power,
        "structure": structure,
        "score": score
    }

    return signal


# ================= FREE SIGNALS ONLY =================
def get_top_free_signals(limit=2):
    candidates = []

    print(f"Dynamic symbols loaded: {SYMBOLS}")

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            try:
                signal = generate_free_signal(symbol, tf)
                if signal:
                    signal["ranking_score"] = (
                        signal["confidence"]
                        + abs(signal["score"] * 2)
                        + (5 if signal["volume"] == "STRONG" else 0)
                        + (5 if signal["trend_power"] in ["STRONG_BULL", "STRONG_BEAR"] else 0)
                    )

                    candidates.append(signal)
                    print(
                        f"✅ Candidate: {signal['pair']} {signal['timeframe']} "
                        f"{signal['direction']} conf={signal['confidence']} score={signal['score']}"
                    )
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