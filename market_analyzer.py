import requests
import pandas as pd
import numpy as np
import random
import time
import logging
from ai_model import predict_trade
from trade_tracker import add_trade
import ccxt

LAST_SIGNAL_STATE = {}
PAIR_SIGNAL_COOLDOWN = 1800  # 30 دقيقة
PRICE_TOLERANCE = 0.003  # 0.3%

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg):
    logging.info(msg)

# ================= SETTINGS =================
def clean_symbol(symbol):
    try:
        symbol = str(symbol)
        symbol = symbol.replace(":USDT", "")
        symbol = symbol.replace("/", "")
        return symbol.strip().upper()
    except:
        return symbol


def get_all_symbols(limit=50):
    try:

        exchange = ccxt.kucoin({
            "enableRateLimit": True
        })

        markets = exchange.load_markets()

        symbols = []

        for s in markets:
            market = markets[s]

            if (
                "/USDT" in s
                and market.get("active", False)
                and not any(x in s for x in ["UP/", "DOWN/", "BULL/", "BEAR/", ":", "USDT:USDT"])
                and not s.endswith(":USDT")
            ):
                symbols.append(clean_symbol(s))

        # حذف التكرار
        symbols = list(set(symbols))

        # ترتيب عشوائي خفيف عشان ميبقاش نفس العملات دايمًا
        import random
        random.shuffle(symbols)

        # ناخد 35 بس
        symbols = symbols[:35]

        print(f"🔥 Loaded {len(symbols)} symbols from KUCOIN")

        return symbols

    except Exception as e:
        print(f"❌ Error loading symbols from KuCoin: {e}")

        return [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
            "XRPUSDT", "ADAUSDT", "DOGEUSDT",
            "AVAXUSDT", "LINKUSDT", "APTUSDT"
        ]


SYMBOLS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",

    "LTCUSDT","ATOMUSDT","NEARUSDT","FTMUSDT","ALGOUSDT",
    "ICPUSDT","FILUSDT","APTUSDT","ARBUSDT","OPUSDT",

    "SUIUSDT","SEIUSDT","INJUSDT","RNDRUSDT","TIAUSDT",
    "JUPUSDT","PYTHUSDT","WIFUSDT","BONKUSDT","PEPEUSDT",

    "ENSUSDT","DYDXUSDT","GMXUSDT","LDOUSDT","AAVEUSDT",
    "UNIUSDT","CRVUSDT","SNXUSDT","1INCHUSDT","COMPUSDT"
]

# ================= OTHER SETTINGS =================

TIMEFRAMES = ["5m", "15m", "1h"]

REQUEST_TIMEOUT = 5
MIN_SCORE_TO_TRADE = 6
MIN_CONFIDENCE = 72

# منع تكرار نفس الأزواج دايمًا
LAST_USED_PAIRS = []

# كاش لتسريع سحب الداتا ومنع الضغط على الـ API
MARKET_DATA_CACHE = {}

# ================= NEW: CACHE TTL =================
MARKET_CACHE_TTL_SECONDS = 70

# ================= NEW: NEWS CACHE =================
NEWS_CACHE = {
    "value": True,
    "time": 0
}
NEWS_CACHE_TTL_SECONDS = 300


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
        log(f"parse_kucoin_klines_to_df error: {e}")
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
        log(f"parse_binance_klines_to_df error: {e}")
        return None


# ================= MARKET DATA =================
def get_market_data(symbol, interval="5m", limit=250):
    """
    Priority:
    1) Binance
    2) Binance US
    3) KuCoin
    """

    global MARKET_DATA_CACHE

    cache_key = f"{symbol}_{interval}_{limit}"

    # ================= SAFE CACHE TTL =================

    cached = MARKET_DATA_CACHE.get(cache_key)

    if (
        isinstance(cached, dict)
        and "data" in cached
        and "time" in cached
   ):
        cache_age = time.time() - cached["time"]

        if cache_age <= MARKET_CACHE_TTL_SECONDS:
           return cached["data"]
        else:
            MARKET_DATA_CACHE.pop(cache_key, None)

    KUCOIN_TF_MAP = {
        "1m": "1min",
        "3m": "3min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1hour",
        "2h": "2hour",
        "4h": "4hour",
        "6h": "6hour",
        "8h": "8hour",
        "12h": "12hour",
        "1d": "1day",
    }
    symbol = symbol.replace("/", "-")

    interval_map = {
      "1m": "1min",
      "5m": "5min",
      "15m": "15min",
      "1h": "1hour"
}

    interval = interval_map.get(interval, interval)

    endpoints = [
        ("KUCOIN", f"https://api.kucoin.com/api/v1/market/candles?type={interval}&symbol={symbol}"),
        ("BINANCE", f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
    ]

    for source_name, url in endpoints:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            log(f"{source_name} STATUS {symbol} {interval}: {response.status_code}")

            if response.status_code == 451:
                log(f"{source_name} restricted for {symbol} {interval}")
                continue

            if response.status_code != 200:
                log(f"{source_name} bad status for {symbol} {interval}: {response.status_code}")
                continue

            try:
                data = response.json()
            except Exception:
                log(f"{source_name} invalid JSON for {symbol} {interval}")
                data = None

            if isinstance(data, dict):
                log(f"{source_name} API error for {symbol} {interval}: {data}")
                continue

            df = parse_binance_klines_to_df(data)
            if df is not None and not df.empty:
                MARKET_DATA_CACHE[cache_key] = {
                    "data": df.copy(),
                    "time": time.time()
                }
                return df.copy()

            log(f"{source_name} no kline data for {symbol} {interval}")

        except Exception as e:
            log(f"{source_name} request failed for {symbol} {interval}: {e}")
            continue

    # ================= FALLBACK TO KUCOIN =================
    try:
        kucoin_interval = KUCOIN_TF_MAP.get(interval, interval)
        kucoin_symbol = symbol.replace("USDT", "-USDT")
# 🔥 تجاهل الرموز الغريبة
        if "-" not in kucoin_symbol:
             return None

        kucoin_url = f"https://api.kucoin.com/api/v1/market/candles?type={kucoin_interval}&symbol={kucoin_symbol}"
        response = requests.get(kucoin_url, timeout=REQUEST_TIMEOUT)

        log(f"KUCOIN STATUS {symbol} {interval}: {response.status_code}")

        if response.status_code != 200:
            log(f"KUCOIN bad status for {symbol} {interval}: {response.status_code}")
            return None

        data = response.json()

        if not isinstance(data, dict) or "data" not in data:
            log(f"KUCOIN invalid response for {symbol} {interval}: {data}")
            return None

        candles = data["data"]

# 🔥 خد آخر عدد محدد
        candles = candles[:limit]

# 🔥 اعكس الترتيب (مهم جدًا)
        candles = list(reversed(candles))

        if not candles:
            log(f"KUCOIN no candles for {symbol} {interval}")
            return None

        df = parse_kucoin_klines_to_df(candles)
        if df is not None and not df.empty:
            log(f"🔥 KUCOIN DATA USED for {symbol} {interval}")
            MARKET_DATA_CACHE[cache_key] = {
                "data": df.copy(),
                "time": time.time()
            }
            return df.copy()

        log(f"KUCOIN parsed empty df for {symbol} {interval}")
        return None

    except Exception as e:
        log(f"KUCOIN API error for {symbol} {interval}: {e}")
        return None
    
def get_price(symbol):
    try:
        df = get_market_data(symbol, "1m", limit=2)

        if df is None or len(df) == 0:
            return None

        return float(df["close"].iloc[-1])

    except Exception as e:
        log(f"get_price error for {symbol}: {e}")
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
    except Exception:
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
    except Exception:
        return False


# ================= LATE ENTRY FILTER =================
def late_entry_filter(df, direction):
    try:
        if df is None or len(df) < 30:
            return False

        close = float(df["close"].iloc[-1])
        open_price = float(df["open"].iloc[-1])
        high = float(df["high"].iloc[-1])
        low = float(df["low"].iloc[-1])

        ema20v = ema(df, 20).iloc[-1]
        ema50v = ema(df, 50).iloc[-1]
        atr_val = atr(df).iloc[-1]

        if pd.isna(ema20v) or pd.isna(ema50v) or pd.isna(atr_val) or atr_val <= 0 or close <= 0:
            return False

        candle_body = abs(close - open_price)
        candle_range = abs(high - low)

        if candle_range > (atr_val * 3.1):
            return True

        if candle_body > (atr_val * 2.15):
            return True

        dist_ema20 = abs(close - ema20v) / close
        dist_ema50 = abs(close - ema50v) / close

        if dist_ema20 > 0.017:
            return True

        if dist_ema50 > 0.028:
            return True

        if direction == "LONG":
            recent_push = (close - df["close"].iloc[-4]) / df["close"].iloc[-4]
            if recent_push > 0.017:
                return True

        if direction == "SHORT":
            recent_push = (df["close"].iloc[-4] - close) / df["close"].iloc[-4]
            if recent_push > 0.017:
                return True

        return False
    except Exception as e:
        log(f"late_entry_filter error: {e}")
        return False


# ================= SUPPORT / RESISTANCE FILTER =================
def support_resistance_filter(df, direction):
    try:
        if df is None or len(df) < 40:
            return True

        close = float(df["close"].iloc[-1])
        atr_val = atr(df).iloc[-1]

        if pd.isna(atr_val) or atr_val <= 0 or close <= 0:
            return True

        recent_high = float(df["high"].tail(25).max())
        recent_low = float(df["low"].tail(25).min())

        resistance_distance = abs(recent_high - close)
        support_distance = abs(close - recent_low)

        if direction == "LONG":
            if recent_high > close and resistance_distance < (atr_val * 1.15):
                return False

        if direction == "SHORT":
            if recent_low < close and support_distance < (atr_val * 1.15):
                return False

        return True
    except Exception as e:
        log(f"support_resistance_filter error: {e}")
        return True


# ================= PULLBACK ENTRY QUALITY =================
def pullback_entry_quality(df, direction):
    try:
        if df is None or len(df) < 25:
            return False

        close = float(df["close"].iloc[-1])
        ema20v = float(ema(df, 20).iloc[-1])
        ema50v = float(ema(df, 50).iloc[-1])

        if close <= 0 or ema20v <= 0 or ema50v <= 0:
            return False

        dist_ema20 = abs(close - ema20v) / close
        dist_ema50 = abs(close - ema50v) / close

        if dist_ema20 > 0.016:
            return False

        if dist_ema50 > 0.028:
            return False

        closes = df["close"].tail(5).tolist()

        if direction == "LONG":
            if closes[-1] > closes[-2] > closes[-3]:
                recent_push = (closes[-1] - closes[-4]) / closes[-4]
                if recent_push > 0.0085:
                    return False

        if direction == "SHORT":
            if closes[-1] < closes[-2] < closes[-3]:
                recent_push = (closes[-4] - closes[-1]) / closes[-4]
                if recent_push > 0.0085:
                    return False

        last_low = float(df["low"].iloc[-1])
        last_high = float(df["high"].iloc[-1])

        if direction == "LONG":
            if last_low > ema20v * 1.014:
                return False

        if direction == "SHORT":
            if last_high < ema20v * 0.986:
                return False

        return True
    except Exception as e:
        log(f"pullback_entry_quality error: {e}")
        return False


# ================= REJECTION WICK FILTER =================
def rejection_wick_filter(df, direction):
    try:
        if df is None or len(df) < 5:
            return True

        last = df.iloc[-1]

        open_price = float(last["open"])
        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])

        body = abs(close - open_price)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low

        if body <= 0:
            body = 0.0000001

        if direction == "LONG":
            if upper_wick > body * 2.2 and close < high:
                return False

        if direction == "SHORT":
            if lower_wick > body * 2.2 and close > low:
                return False

        return True
    except Exception as e:
        log(f"rejection_wick_filter error: {e}")
        return True


# ================= HIGHER TF CONFIRMATION =================
def higher_timeframe_confirmation(symbol, direction, current_interval):
    try:
        higher_tf = get_higher_tf(current_interval)
        df_htf = get_market_data(symbol, higher_tf, limit=200)

        if df_htf is None or len(df_htf) < 60:
            return False

        trend_htf = detect_trend(df_htf)
        trend_power_htf = trend_strength(df_htf)
        smc_htf = detect_smc(df_htf)

        if direction == "LONG":
            return (
                trend_htf == "UP"
                and trend_power_htf in ["STRONG_BULL", "MIXED"]
                and smc_htf != "LIQUIDITY_BREAK_DOWN"
            )

        elif direction == "SHORT":
            return (
                trend_htf == "DOWN"
                and trend_power_htf in ["STRONG_BEAR", "MIXED"]
                and smc_htf != "LIQUIDITY_BREAK_UP"
            )

        return False
    except Exception as e:
        log(f"higher_timeframe_confirmation error for {symbol} {current_interval}: {e}")
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
    except Exception:
        return True


# ================= NEWS FILTER =================
def news_filter():
    global NEWS_CACHE

    try:
        now = time.time()

        if (now - NEWS_CACHE["time"]) <= NEWS_CACHE_TTL_SECONDS:
            return NEWS_CACHE["value"]

        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN"
        data = requests.get(url, timeout=REQUEST_TIMEOUT).json()

        titles = [x["title"].lower() for x in data.get("Data", [])[:8]]
        danger = [
            "crash", "hack", "ban", "sec", "regulation",
            "lawsuit", "exploit", "liquidation", "collapse"
        ]

        hits = 0
        for t in titles:
            for k in danger:
                if k in t:
                    hits += 1

        result = hits < 4

        NEWS_CACHE["value"] = result
        NEWS_CACHE["time"] = now

        return result
    except Exception:
        return True


# ================= AI SCORE =================
def ai_score(rsi_val, macd_val, signal_val, trend, volume, smc, trend_power, structure):
    score = 0

    if rsi_val < 35:
        score += 1.5
    elif rsi_val > 65:
        score -= 1.5
    elif 52 <= rsi_val <= 62:
        score += 1
    elif 38 <= rsi_val <= 48:
        score -= 1

    if macd_val > signal_val:
        score += 1.5
    else:
        score -= 1.5

    if trend == "UP":
        score += 2
    elif trend == "DOWN":
        score -= 2

    if volume == "STRONG":
        score += 1.5

    if smc == "LIQUIDITY_BREAK_UP":
        score += 1.5
    elif smc == "LIQUIDITY_BREAK_DOWN":
        score -= 1.5

    if trend_power == "STRONG_BULL":
        score += 1.5
    elif trend_power == "STRONG_BEAR":
        score -= 1.5

    if structure == "NEAR_BREAKOUT_HIGH":
        score += 1
    elif structure == "NEAR_BREAKOUT_LOW":
        score -= 1

    return score


# ================= SMART TARGET BOOST =================
def smart_target_multiplier(interval, trend_power, volume, structure, direction):
    tp_mult = 1.0
    sl_mult = 1.0

    if interval == "15m":
        tp_mult += 0.30
        sl_mult += 0.10
    elif interval == "5m":
        tp_mult += 0.10

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        tp_mult += 0.15
        sl_mult += 0.10
    elif trend_power == "MIXED":
        tp_mult -= 0.10

    if volume == "STRONG":
        tp_mult += 0.25

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
    except Exception:
        atr_value = 0

    if entry <= 0:
        return None, None

    if timeframe == "15m":
        min_tp_percent = 0.012
        min_sl_percent = 0.0062
        atr_tp_multiplier = 2.9
        atr_sl_multiplier = 1.55
    elif timeframe == "1h":
        min_tp_percent = 0.017
        min_sl_percent = 0.008
        atr_tp_multiplier = 3.4
        atr_sl_multiplier = 1.7
    else:
        min_tp_percent = 0.009
        min_sl_percent = 0.0052
        atr_tp_multiplier = 2.4
        atr_sl_multiplier = 1.35

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        min_tp_percent += 0.0025
        atr_tp_multiplier += 0.3

    if volume == "STRONG":
        min_tp_percent += 0.002
        atr_tp_multiplier += 0.4

    if entry < 1:
        min_tp_percent += 0.004
        min_sl_percent += 0.0012

    if entry < 0.1:
        min_tp_percent += 0.004
        min_sl_percent += 0.0012

    extra_tp_mult, extra_sl_mult = smart_target_multiplier(
        timeframe, trend_power, volume, structure, direction
    )

    atr_tp_multiplier *= extra_tp_mult
    atr_sl_multiplier *= extra_sl_mult

    if pd.isna(atr_value) or atr_value <= 0:
        atr_based_tp = entry * min_tp_percent
        atr_based_sl = entry * min_sl_percent
    else:
        atr_based_tp = atr_value * atr_tp_multiplier
        atr_based_sl = atr_value * atr_sl_multiplier

    tp_move = max(atr_based_tp, entry * min_tp_percent)
    sl_move = max(atr_based_sl, entry * min_sl_percent)

    min_rr_tp = sl_move * 2.25
    tp_move = max(tp_move, min_rr_tp)

    if timeframe == "5m":
        tp_move = max(tp_move, entry * 0.0105)
    elif timeframe == "15m":
        tp_move = max(tp_move, entry * 0.0135)
    elif timeframe == "1h":
        tp_move = max(tp_move, entry * 0.018)

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

    if direction == "LONG":
        tp = entry + tp_move
        sl = entry - sl_move
    else:
        tp = entry - tp_move
        sl = entry + sl_move

    return tp, sl


# ================= CONFIDENCE =================
def calculate_confidence(score, volume, smc, trend_power, structure, momentum_ok=False, htf_ok=False):
    confidence = 52

    confidence += abs(score) * 2.2

    if volume == "STRONG":
        confidence += 5
    else:
        confidence -= 4

    if smc in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"]:
        confidence += 6
    elif smc == "RANGE":
        confidence -= 6
    else:
        confidence -= 2

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        confidence += 6
    elif trend_power == "MIXED":
        confidence -= 7

    if structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"]:
        confidence += 5
    elif structure == "MID_RANGE":
        confidence -= 5
    elif structure == "UNKNOWN":
        confidence -= 3

    if momentum_ok:
        confidence += 5
    else:
        confidence -= 5

    if htf_ok:
        confidence += 6
    else:
        confidence -= 6

    confidence = int(round(confidence))

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
    except Exception:
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
        if rr < 1.4:
            return False

        return True
    except Exception:
        return False


# ================= STRONG SIGNAL FILTER =================
def strong_signal_filter(df, trend, trend_power, direction):
    try:
        if df is None or len(df) < 60:
            return False

        if is_choppy(df):
            return False

        # نخلي الفلتر أقل قسوة من قبل علشان الفيوتشر يرجع
        if trend_power == "STRONG_BULL" and direction == "SHORT":
            return False

        if trend_power == "STRONG_BEAR" and direction == "LONG":
            return False

        last = df["close"].iloc[-1]
        prev = df["close"].iloc[-4]

        if prev <= 0:
            return False

        move = abs(last - prev) / prev

        if move < 0.0022:
            return False

        recent_range = (df["high"].tail(3) - df["low"].tail(3)).mean()
        if recent_range <= 0:
            return False

        atr_val = atr(df).iloc[-1]
        if pd.isna(atr_val) or atr_val <= 0:
            return False

        if (atr_val / last) < 0.0009:
            return False

        return True

    except Exception:
        return False

def should_block_signal(symbol, direction, entry_price):
    try:
        now = time.time()

        if symbol not in LAST_SIGNAL_STATE:
            return False

        last = LAST_SIGNAL_STATE[symbol]

        last_time = last.get("time", 0)
        last_direction = last.get("direction")
        last_entry = last.get("entry", 0)

        # ✅ Cooldown check
        if (now - last_time) < PAIR_SIGNAL_COOLDOWN:
            # نفس الاتجاه
            if last_direction == direction:
                return True

        # ✅ Price tolerance check
        if last_entry > 0:
            price_diff = abs(entry_price - last_entry) / last_entry

            if price_diff < PRICE_TOLERANCE and last_direction == direction:
                return True

        return False

    except Exception:
        return False    
    
def calculate_smart_tp_sl(df, entry, direction):
    try:
        atr_val = df["atr"].iloc[-1]
        last_close = df["close"].iloc[-1]

        if atr_val <= 0:
            return entry, entry

        # 🔥 multiplier ذكي حسب السوق
        if atr_val / last_close > 0.01:
            tp_multiplier = 1.2   # سوق متحرك
            sl_multiplier = 0.8
        else:
            tp_multiplier = 0.8   # سوق هادي
            sl_multiplier = 0.6

        if direction == "LONG":
            tp = entry + (atr_val * tp_multiplier)
            sl = entry - (atr_val * sl_multiplier)

        elif direction == "SHORT":
            tp = entry - (atr_val * tp_multiplier)
            sl = entry + (atr_val * sl_multiplier)

        else:
            return entry, entry

        return round(tp, 6), round(sl, 6)

    except Exception:
        return entry, entry 
    
# ================= SUPPORT / RESISTANCE =================
def find_support_resistance(candles):
    try:
        supports = []
        resistances = []

        for i in range(2, len(candles)-2):
            low = candles[i][3]
            high = candles[i][2]

            if (
                low < candles[i-1][3] and
                low < candles[i+1][3] and
                low < candles[i-2][3] and
                low < candles[i+2][3]
            ):
                supports.append(low)

            if (
                high > candles[i-1][2] and
                high > candles[i+1][2] and
                high > candles[i-2][2] and
                high > candles[i+2][2]
            ):
                resistances.append(high)

        return supports, resistances

    except Exception as e:
        print(f"SR error: {e}")
        return [], []
      


# ================= INTERNAL SIGNAL BUILDER =================
def smart_entry_filter(df, direction, entry, atr_val):
    try:
        price = float(df["close"].iloc[-1])
        distance = abs(price - entry) / entry

        if distance > 0.004:
            return False

        recent_move = abs(df["close"].iloc[-1] - df["close"].iloc[-4]) / df["close"].iloc[-4]

        if recent_move > 0.006:
            pullback = abs(df["close"].iloc[-1] - df["close"].iloc[-2])
            if pullback < atr_val * 0.35:
                return False

        return True
    except:
        return True


def liquidity_sweep_filter(df, direction):
    try:
        highs = df["high"].values
        lows = df["low"].values

        last_high = highs[-2]
        last_low = lows[-2]

        current_high = highs[-1]
        current_low = lows[-1]

        if direction == "LONG":
            return current_low < last_low and df["close"].iloc[-1] > last_low

        if direction == "SHORT":
            return current_high > last_high and df["close"].iloc[-1] < last_high

        return False
    except:
        return True


def _build_signal(symbol, interval="5m", is_paid=False, prechecked_news_ok=None):
    df = get_market_data(symbol, interval)
    if df is None or len(df) < (100 if is_paid else 60):
        return None

    choppy = is_choppy(df)
    momentum_ok = strong_momentum(df)
    vol_ok = volatility_ok(df)

    if choppy and not is_paid:
        return None
    if not vol_ok and not is_paid:
        return None

    df["rsi"] = rsi(df)
    macd_line, signal_line = macd(df)
    df["atr"] = atr(df)

    trend = detect_trend(df)
    trend_power = trend_strength(df)
    volume = volume_strength(df)
    smc = detect_smc(df)
    structure = market_structure(df)

    news_ok = prechecked_news_ok if prechecked_news_ok is not None else news_filter()

    rsi_val = df["rsi"].iloc[-1]
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    atr_val = df["atr"].iloc[-1]

    if pd.isna(rsi_val) or pd.isna(macd_val) or pd.isna(signal_val) or pd.isna(atr_val):
        return None

    score = ai_score(
        rsi_val, macd_val, signal_val,
        trend, volume, smc, trend_power, structure
    )

    penalty = 0.0
    if choppy: penalty += 0.3
    if not momentum_ok: penalty += 0.3
    if not vol_ok: penalty += 0.2
    if not news_ok: penalty += 0.2

    score -= penalty

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
        score += 0.4

    ENTRY_THRESHOLD = MIN_SCORE_TO_TRADE - (0.4 if is_paid else 0.2)

    if score >= ENTRY_THRESHOLD:
        direction = "LONG"
    elif score <= -ENTRY_THRESHOLD:
        direction = "SHORT"
    else:
        return None

    price = float(df["close"].iloc[-1])

    if should_block_signal(symbol, direction, price):
        return None

    if direction == "LONG" and trend == "DOWN" and abs(score) < 4:
        return None
    if direction == "SHORT" and trend == "UP" and abs(score) < 4:
        return None

    # 🔥 Liquidity sweep
    if not liquidity_sweep_filter(df, direction):
       pass

    # 🔥 Fake candle
    candle_size = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    if candle_size > atr_val * 1.2:
        return None

    # ================= ENTRY =================
    candles = df.values.tolist()
    supports, resistances = find_support_resistance(candles)

    if direction == "LONG":
        valid_supports = [s for s in supports if s < price]
        entry = max(valid_supports) if valid_supports else price - (atr_val * 0.5)

    elif direction == "SHORT":
        valid_res = [r for r in resistances if r > price]
        entry = min(valid_res) if valid_res else price + (atr_val * 0.5)

    if not smart_entry_filter(df, direction, entry, atr_val):
        return None

    # ================= SL =================
    if direction == "LONG":
        valid_supports = [s for s in supports if s < entry]
        sl = max(valid_supports) - (atr_val * 0.3) if valid_supports else entry - atr_val * 1.5

    elif direction == "SHORT":
        valid_res = [r for r in resistances if r > entry]
        sl = min(valid_res) + (atr_val * 0.3) if valid_res else entry + atr_val * 1.5

    # ================= TP =================
    tp_full, _ = dynamic_targets(entry, direction, atr_val, trend_power, volume, interval, structure)

    if tp_full is None or sl is None:
        return None

    # 🔥 Multi TP
    tp1 = entry + (tp_full - entry) * 0.5
    tp2 = tp_full

    rr = abs(tp2 - entry) / max(abs(entry - sl), 1e-9)
    
    if rr > 2.2:
      tp2 = entry + (tp2 - entry) * 0.85

    # 🔥 إعادة حساب RR بعد التعديل
    rr = abs(tp2 - entry) / max(abs(entry - sl), 1e-9)

    min_rr = 1.3 if is_paid else 1.2

    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
       min_rr += 0.3

    if rr < min_rr:
       return None

    confidence = calculate_confidence(
        score, volume, smc, trend_power, structure, momentum_ok, True
    )

    if not news_ok: confidence -= 3
    if choppy: confidence -= 2
    if not momentum_ok: confidence -= 3

    min_conf = 68 if is_paid else 63

# لو السوق قوي
    if trend_power in ["STRONG_BULL", "STRONG_BEAR"]:
      min_conf += 4

# لو السوق متلخبط
    elif trend_power == "MIXED":
      min_conf -= 3

    if confidence < min_conf:
      return None
    
    signal_freshness_check = True

    from datetime import datetime, timezone

    signal = {
        "pair": symbol,
        "timeframe": interval,
        "type": "FUTURES",
        "direction": direction,
        "entry": float(format_price(entry)),
        "tp1": float(format_price(tp1)),   # 🔥 جديد
        "tp2": float(format_price(tp2)),   # 🔥 جديد
        "sl": float(format_price(sl)),
        "confidence": float(round(confidence, 2)),
        "trend": trend,
        "trend_power": trend_power,
        "volume": volume,
        "smc": smc,
        "structure": structure,
        "score": float(round(score, 2)),
        "rr": float(round(rr, 2)),
        "signal_time": datetime.now(timezone.utc).isoformat()
    }

    try:
        ai_result = predict_trade(signal)

        if not ai_result.get("approved"):
            return None

        signal["confidence"] = float(ai_result.get("confidence", signal["confidence"]))
        signal["rr"] = float(ai_result.get("rr", rr))

    except:
        return None

    LAST_SIGNAL_STATE[symbol] = {
        "time": time.time(),
        "direction": direction,
        "entry": entry
    }
    log(f"🔥 SIGNAL PASSED: {symbol} | {direction} | score={score} | conf={confidence} | rr={rr}")

    return signal


# ================= GENERATE PAID SIGNAL =================
def generate_signal(symbol, interval="5m", prechecked_news_ok=None):
    return _build_signal(symbol, interval, is_paid=True, prechecked_news_ok=prechecked_news_ok)


# ================= GENERATE FREE SIGNAL =================
def generate_free_signal(symbol, interval="5m", prechecked_news_ok=None):
    return _build_signal(symbol, interval, is_paid=False, prechecked_news_ok=prechecked_news_ok)


# ================= FREE SIGNALS ONLY =================
def get_top_free_signals(limit=5):
    global LAST_USED_PAIRS, MARKET_DATA_CACHE

    now = time.time()
    expired_keys = []

    for k, v in list(MARKET_DATA_CACHE.items()):
        try:
            if isinstance(v, dict) and "time" in v:
                if (now - v["time"]) > MARKET_CACHE_TTL_SECONDS:
                    expired_keys.append(k)
        except Exception:
            continue

    for k in expired_keys:
        MARKET_DATA_CACHE.pop(k, None)

    candidates = []
    cycle_news_ok = news_filter()

    log(f"Dynamic symbols loaded: {SYMBOLS}")

    priority_symbols = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
        "BNBUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "APTUSDT"
    ]

    sorted_symbols = priority_symbols + [s for s in SYMBOLS if s not in priority_symbols]
    random.shuffle(sorted_symbols)

# ناخد أول 12 بس بدل 38
    sorted_symbols = sorted_symbols[:50]

    for symbol in sorted_symbols:
        for tf in TIMEFRAMES:
            try:
                signal = generate_free_signal(symbol, tf, prechecked_news_ok=cycle_news_ok)
                if signal:
                    signal["ranking_score"] = (
                        signal.get("ranking_score", 0)
                        + signal["confidence"]
                        + abs(signal["score"] * 2)
                        + (6 if signal["volume"] == "STRONG" else 0)
                        + (6 if signal["trend_power"] in ["STRONG_BULL", "STRONG_BEAR"] else 0)
                        + (5 if signal["timeframe"] == "15m" else 0)
                        + (4 if signal["structure"] in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"] else 0)
                        + (3 if signal["smc"] in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"] else 0)
                        + (2 if signal["type"] == "FUTURES" else 0)
                    )

                    candidates.append(signal)
                    log(
                        f"Candidate: {signal['pair']} {signal['timeframe']} "
                        f"{signal['direction']} conf={signal['confidence']} "
                        f"score={signal['score']} type={signal.get('type')}"
                    )

            except Exception as e:
                log(f"Signal generation error for {symbol} {tf}: {e}")
                continue

    best_per_pair = {}

    for s in candidates:
        pair = s["pair"]
        if pair not in best_per_pair or s["ranking_score"] > best_per_pair[pair]["ranking_score"]:
            best_per_pair[pair] = s

    candidates = list(best_per_pair.values())

    if not candidates:
        log("Top signals selected: []")
        return []

    candidates = sorted(candidates, key=lambda x: x["ranking_score"], reverse=True)

    top_pool = candidates[:6] if len(candidates) >= 6 else candidates[:]

    if len(top_pool) > 2:
        shuffled_tail = top_pool[1:]
        random.shuffle(shuffled_tail)
        top_pool = [top_pool[0]] + shuffled_tail

    remaining = [x for x in candidates if x not in top_pool]
    candidates = top_pool + remaining

    best = []
    used_pairs = set()

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

    if len(best) < limit:
        for s in candidates:
            if s["pair"] not in used_pairs:
                best.append(s)
                used_pairs.add(s["pair"])

            if len(best) >= limit:
                break

    log(f"Top signals selected: {best}")
    return best