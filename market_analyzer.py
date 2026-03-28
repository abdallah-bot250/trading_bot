import requests
import pandas as pd
import numpy as np
import random
from ai_model import predict_trade

# ================= SETTINGS =================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
    "DOTUSDT", "LTCUSDT", "NEARUSDT", "APTUSDT", "FILUSDT",
    "ATOMUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "SUIUSDT",
    "SEIUSDT", "TIAUSDT", "UNIUSDT", "AAVEUSDT", "TRXUSDT",
    "ETCUSDT", "ALGOUSDT", "ICPUSDT", "APTUSDT", "HBARUSDT",
    "FTMUSDT", "RUNEUSDT", "XLMUSDT", "EGLDUSDT", "THETAUSDT",
    "AXSUSDT", "SANDUSDT", "MANAUSDT", "GALAUSDT", "APEUSDT"
]

TIMEFRAMES = ["5m", "15m", "1h"]

REQUEST_TIMEOUT = 12
MIN_SCORE_TO_TRADE = 5
MIN_CONFIDENCE = 70

# منع تكرار نفس الأزواج دايمًا
LAST_USED_PAIRS = []


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
        df = df.sort_values("time").reset_index(drop=True)
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

        df = df.sort_values("time").reset_index(drop=True)
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

    ema20v = ema(df, 20)
    ema50v = ema(df, 50)

    if ema20v.iloc[-1] > ema50v.iloc[-1]:
        return "UP"
    return "DOWN"


def trend_strength(df):
    if len(df) < 100:
        return "WEAK"

    ema20v = ema(df, 20)
    ema50v = ema(df, 50)
    ema100v = ema(df, 100)

    if ema20v.iloc[-1] > ema50v.iloc[-1] > ema100v.iloc[-1]:
        return "STRONG_BULL"
    elif ema20v.iloc[-1] < ema50v.iloc[-1] < ema100v.iloc[-1]:
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

        ema20v = ema(df, 20)
        ema50v = ema(df, 50)

        diff = abs(ema20v.iloc[-1] - ema50v.iloc[-1])
        price = df["close"].iloc[-1]

        if price <= 0:
            return True

        return (diff / price) < 0.0012
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

        return change > 0.0018
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


# ================= SMART TARGET BOOST =================
def smart_target_multiplier(interval, trend_power, volume, structure, direction):
    tp_mult = 1.0
    sl_mult = 1.0

    # ===== Timeframe =====
    if interval == "15m":
        tp_mult += 0.30
        sl_mult += 0.10
    elif interval == "5m":
        tp_mult += 0.10

    # ===== Trend strength =====
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        tp_mult += 0.35
        sl_mult += 0.10
    elif trend_power == "MIXED":
        tp_mult -= 0.10

    # ===== Volume =====
    if volume == "STRONG":
        tp_mult += 0.25

    # ===== Structure =====
    if direction == "LONG" and structure == "NEAR_BREAKOUT_HIGH":
        tp_mult += 0.20

    if direction == "SHORT" and structure == "NEAR_BREAKOUT_LOW":
        tp_mult += 0.20

    return max(tp_mult, 1.0), max(sl_mult, 0.9)


# ================= TP / SL =================
def dynamic_targets(entry, direction, atr_value, trend_power="MIXED", volume="WEAK", timeframe="5m", structure="MID_RANGE"):
    try:
        entry = float(entry)
        atr_value = float(atr_value) if atr_value is not None else 0
    except:
        atr_value = 0

    if entry <= 0:
        return None, None

    # ================= BASE MIN TARGETS =================
    if timeframe == "15m":
        min_tp_percent = 0.0115
        min_sl_percent = 0.0048
        atr_tp_multiplier = 2.9
        atr_sl_multiplier = 1.15
    elif timeframe == "1h":
        min_tp_percent = 0.016
        min_sl_percent = 0.0065
        atr_tp_multiplier = 3.4
        atr_sl_multiplier = 1.3
    else:  # 5m
        min_tp_percent = 0.0085
        min_sl_percent = 0.0038
        atr_tp_multiplier = 2.4
        atr_sl_multiplier = 0.95

    # ================= BOOSTS =================
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        min_tp_percent += 0.0025
        atr_tp_multiplier += 0.5

    if volume == "STRONG":
        min_tp_percent += 0.002
        atr_tp_multiplier += 0.4

    # ================= LOW PRICE COIN PROTECTION =================
    if entry < 1:
        min_tp_percent += 0.004
        min_sl_percent += 0.0012

    if entry < 0.1:
        min_tp_percent += 0.004
        min_sl_percent += 0.0012

    # ================= SMART TARGET SYSTEM =================
    extra_tp_mult, extra_sl_mult = smart_target_multiplier(
        timeframe, trend_power, volume, structure, direction
    )

    atr_tp_multiplier *= extra_tp_mult
    atr_sl_multiplier *= extra_sl_mult

    # ================= ATR MOVE =================
    if pd.isna(atr_value) or atr_value <= 0:
        atr_based_tp = entry * min_tp_percent
        atr_based_sl = entry * min_sl_percent
    else:
        atr_based_tp = atr_value * atr_tp_multiplier
        atr_based_sl = atr_value * atr_sl_multiplier

    # ================= FINAL ENFORCED DISTANCE =================
    tp_move = max(atr_based_tp, entry * min_tp_percent)
    sl_move = max(atr_based_sl, entry * min_sl_percent)

    # ================= RR ENFORCEMENT =================
    min_rr_tp = sl_move * 2.0
    tp_move = max(tp_move, min_rr_tp)

    # ================= ANTI-TINY TARGETS =================
    if entry < 0.1:
        tp_move = max(tp_move, entry * 0.015)
        sl_move = max(sl_move, entry * 0.006)
    elif entry < 1:
        tp_move = max(tp_move, entry * 0.012)
        sl_move = max(sl_move, entry * 0.005)
    elif entry < 100:
        tp_move = max(tp_move, entry * 0.0085)
        sl_move = max(sl_move, entry * 0.0038)
    else:
        tp_move = max(tp_move, entry * 0.007)
        sl_move = max(sl_move, entry * 0.0033)

    # ================= FINAL LEVELS =================
    if direction == "LONG":
        tp = entry + tp_move
        sl = entry - sl_move
    else:
        tp = entry - tp_move
        sl = entry + sl_move

    return tp, sl


# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure, momentum_ok=False, htf_ok=False):
    """
    Confidence واقعي:
    - المتوسط يبقى 60~72
    - القوي 73~82
    - النادر جدًا 83~88
    - بدون أرقام مبالغ فيها
    """

    confidence = 52

    # ================= SCORE CORE =================
    confidence += abs(score) * 2.2

    # ================= VOLUME =================
    if volume == "STRONG":
        confidence += 5
    else:
        confidence -= 4

    # ================= SMART MONEY =================
    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 6
    elif smc == "RANGE":
        confidence -= 6
    else:
        confidence -= 2

    # ================= TREND POWER =================
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 6
    elif trend_power == "MIXED":
        confidence -= 7

    # ================= STRUCTURE =================
    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 5
    elif structure == "MID_RANGE":
        confidence -= 5
    elif structure == "UNKNOWN":
        confidence -= 3

    # ================= MOMENTUM =================
    if momentum_ok:
        confidence += 5
    else:
        confidence -= 5

    # ================= HTF =================
    if htf_ok:
        confidence += 6
    else:
        confidence -= 6

    confidence = int(round(confidence))

    # ================= HARD REALISTIC CAP =================
    if confidence >= 89:
        confidence = 88

    if confidence < 48:
        confidence = 48

    return confidence


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

        # ===== Minimum distance حسب نوع العملة =====
        if entry < 0.1:
            min_reward = entry * 0.015
            min_risk = entry * 0.006
        elif entry < 1:
            min_reward = entry * 0.012
            min_risk = entry * 0.005
        elif entry < 10:
            min_reward = entry * 0.009
            min_risk = entry * 0.0042
        elif entry < 100:
            min_reward = entry * 0.008
            min_risk = entry * 0.0036
        else:
            min_reward = entry * 0.007
            min_risk = entry * 0.003

        if reward < min_reward or risk < min_risk:
            return False

        rr = reward / risk
        if rr < 1.7:
            return False

        return True
    except:
        return False


# ================= STRONG SIGNAL FILTER =================
def strong_signal_filter(df, trend, trend_power, direction):
    try:
        if df is None or len(df) < 60:
            return False

        if is_choppy(df):
            return False

        # منع السوق المكسّر
        if trend_power == "MIXED":
            return False

        # منع عكس الترند القوي
        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False

        last = df["close"].iloc[-1]
        prev = df["close"].iloc[-4]

        if prev <= 0:
            return False

        move = abs(last - prev) / prev

        # لازم حركة محترمة
        if move < 0.003:
            return False

        # لازم آخر 3 شموع مايبقوش ضعاف
        recent_range = (df["high"].tail(3) - df["low"].tail(3)).mean()
        if recent_range <= 0:
            return False

        # ATR لازم يبقى محترم
        atr_val = atr(df).iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            return False

        if (atr_val / last) < 0.001:
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

    # صارم لكن عملي
    if score >= MIN_SCORE_TO_TRADE:
        direction = "LONG"
    elif score <= -MIN_SCORE_TO_TRADE:
        direction = "SHORT"
    else:
        return None

    if not strong_signal_filter(df, trend, trend_power, direction):
        return None

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)

    # منع العكس القوي جدًا فقط
    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < (MIN_SCORE_TO_TRADE + 2):
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < (MIN_SCORE_TO_TRADE + 2):
        return None

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val, trend_power, volume, interval)

    if tp is None or sl is None:
        return None

    # ===== Reject dead / tiny targets =====
    tp_distance = abs(tp - entry) / entry
    sl_distance = abs(sl - entry) / entry

    if tp_distance < 0.0085:
        return None

    if sl_distance < 0.0035:
        return None

    momentum_ok = strong_momentum(df)
    confidence = calculate_confidence(
        score, volume, smc, trend_power, structure, momentum_ok, htf_ok
    )

    if not signal_levels_valid(entry, tp, sl, direction):
        return None

    # مدفوع = لازم يكون نضيف
    min_paid_conf = 74 + (5 if not htf_ok else 0)

    if confidence < min_paid_conf:
        return None

    # ================= TRADE TYPE SMART DECISION =================
    if (
        direction == "LONG"
        and trend == "UP"
        and trend_power == "STRONG_BULL"
        and htf_ok
        and confidence >= 78
        and structure in ["NEAR_BREAKOUT_HIGH", "MID_RANGE"]
    ):
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
    if df is None or len(df) < 60:
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

    if score >= 5:
        direction = "LONG"
    elif score <= -5:
        direction = "SHORT"
    else:
        return None

    if not strong_signal_filter(df, trend, trend_power, direction):
        return None

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)

    if not htf_ok and abs(score) < 6:
        return None

    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < 6:
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < 6:
        return None

    entry = df["close"].iloc[-1]
    tp, sl = dynamic_targets(entry, direction, atr_val, trend_power, volume, interval)

    if tp is None or sl is None:
        return None

    tp_distance = abs(tp - entry) / entry
    sl_distance = abs(sl - entry) / entry

    if tp_distance < 0.0075:
        return None

    if sl_distance < 0.003:
        return None

    momentum_ok = strong_momentum(df)
    confidence = calculate_confidence(
        score, volume, smc, trend_power, structure, momentum_ok, htf_ok
    )

    if not signal_levels_valid(entry, tp, sl, direction):
        return None

    min_free_conf = 66 + (5 if not htf_ok else 0)

    if confidence < min_free_conf:
        return None

    # ================= TRADE TYPE SMART DECISION =================
    if (
        direction == "LONG"
        and trend == "UP"
        and trend_power == "STRONG_BULL"
        and htf_ok
        and confidence >= 78
        and structure in ["NEAR_BREAKOUT_HIGH", "MID_RANGE"]
    ):
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
        print(f"AI model error in generate_free_signal {symbol} {interval}: {e}")
        return None

    return signal


# ================= FREE SIGNALS ONLY =================
def get_top_free_signals(limit=2):
    global LAST_USED_PAIRS

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
                        + (6 if signal["volume"] == "STRONG" else 0)
                        + (6 if signal["trend_power"] in ["STRONG_BULL", "STRONG_BEAR"] else 0)
                        + (5 if signal["timeframe"] == "15m" else 0)
                        + (4 if signal["structure"] in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"] else 0)
                        + (3 if signal["smc"] in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"] else 0)
                    )

                    candidates.append(signal)
                    print(
                        f"✅ Candidate: {signal['pair']} {signal['timeframe']} "
                        f"{signal['direction']} conf={signal['confidence']} score={signal['score']}"
                    )
            except Exception as e:
                print(f"Signal generation error for {symbol} {tf}: {e}")
                continue

    # ================= KEEP BEST SIGNAL ONLY PER PAIR =================
    best_per_pair = {}

    for s in candidates:
        pair = s["pair"]
        if pair not in best_per_pair or s["ranking_score"] > best_per_pair[pair]["ranking_score"]:
            best_per_pair[pair] = s

    candidates = list(best_per_pair.values())

    if not candidates:
        print("Top signals selected: []")
        return []

    candidates = sorted(candidates, key=lambda x: x["ranking_score"], reverse=True)

    top_pool = candidates[:6] if len(candidates) >= 6 else candidates[:]

    # تنويع بسيط بدون تدمير الجودة
    if len(top_pool) > 2:
        shuffled_tail = top_pool[1:]
        random.shuffle(shuffled_tail)
        top_pool = [top_pool[0]] + shuffled_tail

    remaining = [x for x in candidates if x not in top_pool]
    candidates = top_pool + remaining

    best = []
    used_pairs = set()

    # أول محاولة: استبعاد الأزواج المستخدمة مؤخرًا
    for s in candidates:
        if s["pair"] in LAST_USED_PAIRS:
            continue

        if s["pair"] not in used_pairs:
            best.append(s)
            used_pairs.add(s["pair"])

            LAST_USED_PAIRS.append(s["pair"])
            if len(LAST_USED_PAIRS) > 6:
                LAST_USED_PAIRS.pop(0)

        if len(best) >= limit:
            break

    # لو ماكفوش، رجّع من الباقي عادي
    if len(best) < limit:
        for s in candidates:
            if s["pair"] not in used_pairs:
                best.append(s)
                used_pairs.add(s["pair"])

            if len(best) >= limit:
                break

    print(f"Top signals selected: {best}")
    return best