import time
import requests
import pandas as pd
import numpy as np
import random
import json
import os
from datetime import datetime
from ai_model import predict_trade
from ai_engine import build_ai_engine_report
from spot_futures_engine import choose_trade_type, evaluate_trade_types, record_trade_type

# ================= SETTINGS =================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "LTCUSDT"
]

TIMEFRAMES = ["5m", "15m", "1h"]

REQUEST_TIMEOUT = 12
MIN_SCORE_TO_TRADE = 5
MIN_CONFIDENCE = 70
MARKET_SOURCE_LOG_CACHE = {}
MARKET_SOURCE_LOG_TTL_SECONDS = 900
MARKET_CONTEXT_CACHE = {}
MARKET_CONTEXT_TTL_SECONDS = 180
SIGNAL_SKIP_LOG_CACHE = {}
SIGNAL_SKIP_LOG_TTL_SECONDS = 600
LAST_DRY_RUN_SKIPS = []
MIN_SPOT_FINAL_SCORE = 88
MIN_FUTURES_FINAL_SCORE = 90
MAX_DYNAMIC_SYMBOLS = int(os.environ.get("MAX_DYNAMIC_SYMBOLS", "120"))
MIN_DYNAMIC_QUOTE_VOLUME = float(os.environ.get("MIN_DYNAMIC_QUOTE_VOLUME", "5000000"))
DYNAMIC_SYMBOLS_TTL_SECONDS = int(os.environ.get("DYNAMIC_SYMBOLS_TTL_SECONDS", "1800"))
DYNAMIC_SYMBOL_CACHE = {"time": 0, "symbols": None}
EXCLUDED_BASE_ASSETS = {
    "USDC", "BUSD", "FDUSD", "TUSD", "USDP", "DAI", "UST", "USTC",
    "EUR", "TRY", "GBP", "BRL", "AUD", "BIDR", "NGN", "RUB", "UAH",
}
EXCLUDED_SYMBOL_PARTS = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def _safe_market_json(url, timeout=REQUEST_TIMEOUT):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None, response.status_code
        return response.json(), 200
    except Exception as e:
        return None, str(e)


def _is_tradeable_usdt_symbol(symbol):
    try:
        symbol = str(symbol or "").upper().strip()
        if not symbol.endswith("USDT"):
            return False
        if any(part in symbol for part in EXCLUDED_SYMBOL_PARTS):
            return False
        base = symbol[:-4]
        if not base or base in EXCLUDED_BASE_ASSETS:
            return False
        if any(ch in base for ch in ["_", "-", "/"]):
            return False
        return True
    except Exception:
        return False


def _ticker_volume_map(url):
    data, status = _safe_market_json(url)
    volumes = {}
    if not isinstance(data, list):
        return volumes, status
    for row in data:
        try:
            symbol = str(row.get("symbol") or "").upper()
            if not _is_tradeable_usdt_symbol(symbol):
                continue
            quote_volume = float(row.get("quoteVolume") or 0)
            if quote_volume >= MIN_DYNAMIC_QUOTE_VOLUME:
                volumes[symbol] = max(volumes.get(symbol, 0), quote_volume)
        except Exception:
            continue
    return volumes, status


def _exchange_symbols(url, market_type):
    data, status = _safe_market_json(url)
    symbols = set()
    if not isinstance(data, dict):
        return symbols, status
    for row in data.get("symbols", []):
        try:
            symbol = str(row.get("symbol") or "").upper()
            if not _is_tradeable_usdt_symbol(symbol):
                continue
            if market_type == "spot":
                if row.get("status") != "TRADING":
                    continue
                permissions = row.get("permissions") or []
                if permissions and "SPOT" not in permissions and "TRADING" not in permissions:
                    continue
            else:
                if row.get("status") != "TRADING":
                    continue
                if row.get("contractType") not in (None, "PERPETUAL"):
                    continue
            symbols.add(symbol)
        except Exception:
            continue
    return symbols, status


def _rank_symbol_universe(symbols, volume_maps):
    ranked = []
    for symbol in symbols:
        volume = max([volume_map.get(symbol, 0) for volume_map in volume_maps] or [0])
        if volume >= MIN_DYNAMIC_QUOTE_VOLUME:
            ranked.append((symbol, volume))
    if not ranked:
        ranked = [(symbol, 0) for symbol in symbols]
    ranked.sort(key=lambda item: item[1], reverse=True)

    pinned = [symbol for symbol in SYMBOLS if symbol in {item[0] for item in ranked}]
    ordered = []
    seen = set()
    for symbol in pinned + [item[0] for item in ranked]:
        if symbol in seen:
            continue
        seen.add(symbol)
        ordered.append(symbol)
        if MAX_DYNAMIC_SYMBOLS > 0 and len(ordered) >= MAX_DYNAMIC_SYMBOLS:
            break
    return ordered


def get_scan_symbols(force_refresh=False):
    """Load a broad Binance Spot/Futures USDT universe, then scan only liquid symbols.

    This keeps the bot from being locked to a tiny fixed list without choking the
    worker by scanning hundreds of weak pairs every cycle.
    """
    now = time.time()
    cached = DYNAMIC_SYMBOL_CACHE.get("symbols")
    if cached and not force_refresh and now - DYNAMIC_SYMBOL_CACHE.get("time", 0) < DYNAMIC_SYMBOLS_TTL_SECONDS:
        return list(cached)

    all_symbols = set()
    volume_maps = []
    failures = []

    for url, market_type, label in [
        ("https://api.binance.com/api/v3/exchangeInfo", "spot", "BINANCE_SPOT"),
        ("https://api.binance.us/api/v3/exchangeInfo", "spot", "BINANCE_US_SPOT"),
        ("https://fapi.binance.com/fapi/v1/exchangeInfo", "futures", "BINANCE_FUTURES"),
    ]:
        symbols, status = _exchange_symbols(url, market_type)
        if symbols:
            all_symbols.update(symbols)
        else:
            failures.append(f"{label}={status}")

    for url, label in [
        ("https://api.binance.com/api/v3/ticker/24hr", "BINANCE_SPOT_TICKER"),
        ("https://api.binance.us/api/v3/ticker/24hr", "BINANCE_US_TICKER"),
        ("https://fapi.binance.com/fapi/v1/ticker/24hr", "BINANCE_FUTURES_TICKER"),
    ]:
        volume_map, status = _ticker_volume_map(url)
        if volume_map:
            volume_maps.append(volume_map)
            all_symbols.update(volume_map.keys())
        else:
            failures.append(f"{label}={status}")

    if all_symbols:
        selected = _rank_symbol_universe(all_symbols, volume_maps)
    else:
        selected = list(SYMBOLS)

    if not selected:
        selected = list(SYMBOLS)

    DYNAMIC_SYMBOL_CACHE["time"] = now
    DYNAMIC_SYMBOL_CACHE["symbols"] = selected
    symbol_limit = MAX_DYNAMIC_SYMBOLS if MAX_DYNAMIC_SYMBOLS > 0 else "ALL"
    print(f"DYNAMIC_SYMBOL_UNIVERSE loaded={len(selected)} max={symbol_limit} failures={'; '.join(failures[:4])}")
    return list(selected)


def log_market_source_once(source, symbol, timeframe):
    now = time.time()
    key = (source, symbol, timeframe)
    last_seen = MARKET_SOURCE_LOG_CACHE.get(key, 0)
    if now - last_seen >= MARKET_SOURCE_LOG_TTL_SECONDS:
        MARKET_SOURCE_LOG_CACHE[key] = now
        print(f"MARKET_DATA_SOURCE {source} symbol={symbol} timeframe={timeframe}")

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

    endpoints = [
        ("BINANCE", f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"),
        ("BINANCE_FUTURES", f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"),
        ("BINANCE_US", f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
    ]

    failures = []
    binance_global_451 = False

    for source_name, url in endpoints:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)

            if source_name == "BINANCE" and response.status_code == 451:
                binance_global_451 = True
                failures.append(f"{source_name}=451")
                continue

            if response.status_code != 200:
                failures.append(f"{source_name}={response.status_code}")
                continue

            try:
                data = response.json()
            except Exception as json_error:
                failures.append(f"{source_name}=invalid_json:{json_error}")
                continue

            if isinstance(data, dict):
                failures.append(f"{source_name}=api_error")
                continue

            df = parse_binance_klines_to_df(data)
            if df is not None and not df.empty:
                if source_name == "BINANCE_US" and binance_global_451:
                    log_market_source_once("BINANCE_US", symbol, interval)
                elif source_name == "BINANCE_FUTURES":
                    log_market_source_once("BINANCE_FUTURES", symbol, interval)
                return df

            failures.append(f"{source_name}=empty")

        except Exception as e:
            failures.append(f"{source_name}=request_failed:{e}")
            continue

    # ===================== FALLBACK TO KUCOIN =====================
    try:
        kucoin_interval = KUCOIN_TF_MAP.get(interval, interval)
        kucoin_symbol = symbol.replace("USDT", "-USDT")

        kucoin_url = f"https://api.kucoin.com/api/v1/market/candles?type={kucoin_interval}&symbol={kucoin_symbol}"
        response = requests.get(kucoin_url, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            failures.append(f"KUCOIN={response.status_code}")
            print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
            return None

        data = response.json()

        if not isinstance(data, dict) or "data" not in data:
            failures.append("KUCOIN=invalid_response")
            print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
            return None

        candles = data["data"]

        if not candles:
            failures.append("KUCOIN=empty")
            print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
            return None

        candles = candles[::-1]

        import pandas as pd

        df = pd.DataFrame(candles, columns=[
            "time", "open", "close", "high", "low", "volume", "turnover"
        ])

        df["time"] = pd.to_datetime(df["time"].astype(int), unit="s")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["time", "open", "high", "low", "close", "volume"]]
        df.dropna(inplace=True)

        if df is not None and not df.empty:
            return df

        failures.append("KUCOIN=parsed_empty")
        print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
        return None

    except Exception as e:
        failures.append(f"KUCOIN=api_error:{e}")
        print(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe={interval} failures={'; '.join(failures)}")
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


# ================= NEW: LATE ENTRY FILTER =================
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

        # شمعة انفجارية زيادة = غالبًا دخول متأخر
        if candle_range > (atr_val * 2.4):
            return True

        if candle_body > (atr_val * 1.6):
            return True

        # بعيد جدًا عن المتوسطات
        dist_ema20 = abs(close - ema20v) / close
        dist_ema50 = abs(close - ema50v) / close

        if dist_ema20 > 0.012:
            return True

        if dist_ema50 > 0.02:
            return True

        # داخل LONG بعد شدّة صعود / SHORT بعد شدّة هبوط
        if direction == "LONG":
            recent_push = (close - df["close"].iloc[-4]) / df["close"].iloc[-4]
            if recent_push > 0.012:
                return True

        if direction == "SHORT":
            recent_push = (df["close"].iloc[-4] - close) / df["close"].iloc[-4]
            if recent_push > 0.012:
                return True

        return False
    except Exception as e:
        print(f"late_entry_filter error: {e}")
        return False


# ================= NEW: SUPPORT / RESISTANCE FILTER =================
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

        # LONG تحت مقاومة قريبة جدًا
        if direction == "LONG":
            if recent_high > close and resistance_distance < (atr_val * 1.15):
                return False

        # SHORT فوق دعم قريب جدًا
        if direction == "SHORT":
            if recent_low < close and support_distance < (atr_val * 1.15):
                return False

        return True
    except Exception as e:
        print(f"support_resistance_filter error: {e}")
        return True


# ================= NEW: PULLBACK ENTRY QUALITY =================
def pullback_entry_quality(df, direction):
    try:
        if df is None or len(df) < 25:
            return False

        close = float(df["close"].iloc[-1])
        ema20v = float(ema(df, 20).iloc[-1])

        if close <= 0 or ema20v <= 0:
            return False

        dist = abs(close - ema20v) / close

        # الدخول المثالي يكون قريب نسبيًا من المتوسط
        if dist > 0.0095:
            return False

        # نمنع الدخول لو آخر 3 شمعات كلها في نفس الاتجاه بقوة
        closes = df["close"].tail(4).tolist()

        if direction == "LONG":
            if closes[-1] > closes[-2] > closes[-3] > closes[-4]:
                if ((closes[-1] - closes[-4]) / closes[-4]) > 0.01:
                    return False

        if direction == "SHORT":
            if closes[-1] < closes[-2] < closes[-3] < closes[-4]:
                if ((closes[-4] - closes[-1]) / closes[-4]) > 0.01:
                    return False

        return True
    except Exception as e:
        print(f"pullback_entry_quality error: {e}")
        return False


# ================= NEW: REJECTION WICK FILTER =================
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

        # LONG: لو فيه رفض علوي قوي جدًا → خطر
        if direction == "LONG":
            if upper_wick > body * 2.2 and close < high:
                return False

        # SHORT: لو فيه رفض سفلي قوي جدًا → خطر
        if direction == "SHORT":
            if lower_wick > body * 2.2 and close > low:
                return False

        return True
    except Exception as e:
        print(f"rejection_wick_filter error: {e}")
        return True


# ================= HIGHER TF CONFIRMATION =================
def higher_timeframe_confirmation(symbol, direction, current_interval):
    try:
        higher_tf = get_higher_tf(current_interval)
        df_htf = get_market_data(symbol, higher_tf, limit=200)

        if df_htf is None or len(df_htf) < 50:
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



def cached_market_data(symbol, interval="5m", limit=250, ttl=MARKET_CONTEXT_TTL_SECONDS):
    try:
        key = (symbol, interval, int(limit))
        now = time.time()
        cached = MARKET_CONTEXT_CACHE.get(key)
        if cached and now - cached["time"] <= ttl:
            return cached["df"]
        df = get_market_data(symbol, interval, limit=limit)
        if df is not None and not df.empty:
            MARKET_CONTEXT_CACHE[key] = {"time": now, "df": df}
        return df
    except Exception as e:
        print(f"cached_market_data error {symbol} {interval}: {e}")
        return None


def _safe_ema_value(df, period):
    try:
        value = ema(df, period).iloc[-1]
        return None if pd.isna(value) else float(value)
    except Exception:
        return None


def _lower_highs_lows(df):
    try:
        if df is None or len(df) < 40:
            return False
        recent = df.tail(40)
        first = recent.head(20)
        last = recent.tail(20)
        return float(last["high"].max()) < float(first["high"].max()) and float(last["low"].min()) < float(first["low"].min())
    except Exception:
        return False


def detect_market_regime(btc_candles, eth_candles=None):
    try:
        df = btc_candles
        if df is None or len(df) < 80:
            return "SIDEWAYS"
        close = float(df["close"].iloc[-1])
        if close <= 0:
            return "SIDEWAYS"
        ema50 = _safe_ema_value(df, 50)
        ema200 = _safe_ema_value(df, 200) or _safe_ema_value(df, 100)
        atr_series = atr(df).dropna()
        atr_val = float(atr_series.iloc[-1]) if len(atr_series) else 0
        atr_avg = float(atr_series.tail(30).mean()) if len(atr_series) >= 30 else atr_val
        atr_expanding = bool(atr_avg and atr_val > atr_avg * 1.35)
        momentum_6 = (close - float(df["close"].iloc[-7])) / float(df["close"].iloc[-7]) if float(df["close"].iloc[-7]) else 0
        last = df.iloc[-1]
        last_body = (float(last["open"]) - float(last["close"])) / close if close else 0
        large_red = float(last["close"]) < float(last["open"]) and last_body > 0.018
        lower_structure = _lower_highs_lows(df)

        eth_bearish = False
        if eth_candles is not None and len(eth_candles) >= 80:
            eth50 = _safe_ema_value(eth_candles, 50)
            eth200 = _safe_ema_value(eth_candles, 200) or _safe_ema_value(eth_candles, 100)
            eth_bearish = bool(eth50 and eth200 and eth50 < eth200)

        if large_red or (momentum_6 <= -0.028 and atr_expanding) or (lower_structure and momentum_6 <= -0.018):
            return "DUMP_RISK"
        if ema50 and ema200 and ema50 < ema200 and (momentum_6 < -0.006 or lower_structure or eth_bearish):
            return "BEARISH"
        if atr_expanding and abs(momentum_6) > 0.02:
            return "HIGH_VOLATILITY"
        if ema50 and ema200 and ema50 > ema200 and momentum_6 >= -0.004:
            return "BULLISH"
        return "SIDEWAYS"
    except Exception as e:
        print(f"detect_market_regime error: {e}")
        return "SIDEWAYS"


def multi_timeframe_quality(symbol, direction, current_interval, current_df):
    result = {
        "state": "UNCONFIRMED",
        "score": 0,
        "strong_conflict": False,
        "reason": "insufficient higher timeframe data",
    }
    try:
        frames = {
            current_interval: current_df,
            "15m": cached_market_data(symbol, "15m", limit=220),
            "1h": cached_market_data(symbol, "1h", limit=220),
            "4h": cached_market_data(symbol, "4h", limit=220),
        }
        score = 0
        conflicts = 0
        confirmations = 0
        for tf, frame in frames.items():
            if frame is None or len(frame) < 60:
                continue
            trend = detect_trend(frame)
            power = trend_strength(frame)
            smc_state = detect_smc(frame)
            if direction == "LONG":
                if trend == "UP" and power != "STRONG_BEAR" and smc_state != "LIQUIDITY_BREAK_DOWN":
                    confirmations += 1
                    score += 5 if tf in ["1h", "4h"] else 3
                elif power == "STRONG_BEAR" or smc_state == "LIQUIDITY_BREAK_DOWN":
                    conflicts += 1
            else:
                if trend == "DOWN" and power != "STRONG_BULL" and smc_state != "LIQUIDITY_BREAK_UP":
                    confirmations += 1
                    score += 5 if tf in ["1h", "4h"] else 3
                elif power == "STRONG_BULL" or smc_state == "LIQUIDITY_BREAK_UP":
                    conflicts += 1

        result["score"] = min(score, 18)
        result["strong_conflict"] = conflicts >= 2
        if confirmations >= 3 and not result["strong_conflict"]:
            result["state"] = "CONFIRMED"
            result["reason"] = "5m/15m timing aligns with 1h/4h context"
        elif confirmations >= 2 and conflicts == 0:
            result["state"] = "PARTIAL"
            result["reason"] = "partial multi-timeframe alignment"
        else:
            result["reason"] = f"weak MTF alignment confirmations={confirmations} conflicts={conflicts}"
        return result
    except Exception as e:
        result["reason"] = f"multi-timeframe error: {e}"
        return result


def spot_long_confirmation(df, support):
    try:
        if df is None or len(df) < 25 or support is None:
            return False, "missing support confirmation"
        support = float(support)
        recent = df.tail(8)
        close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        last_open = float(df["open"].iloc[-1])
        last_low = float(df["low"].iloc[-1])
        rsi_series = rsi(df).dropna()
        vol_ma = df["volume"].rolling(20).mean().iloc[-1]
        volume_reclaim = pd.notna(vol_ma) and float(df["volume"].iloc[-1]) > float(vol_ma) * 1.08 and close > support
        support_bounce = recent["low"].min() <= support * 1.004 and close > support * 1.006
        liquidity_sweep = last_low < support * 0.998 and close > support
        higher_low = float(df["low"].iloc[-1]) > float(df["low"].iloc[-3]) and close > prev_close
        bullish_engulfing = close > last_open and close > float(df["open"].iloc[-2]) and last_open <= prev_close
        rsi_recovery = len(rsi_series) >= 3 and float(rsi_series.iloc[-3]) < 38 and float(rsi_series.iloc[-1]) > float(rsi_series.iloc[-2])
        confirmations = []
        if support_bounce:
            confirmations.append("support bounce")
        if liquidity_sweep:
            confirmations.append("liquidity sweep reclaim")
        if volume_reclaim:
            confirmations.append("volume reclaim")
        if higher_low:
            confirmations.append("higher low")
        if bullish_engulfing:
            confirmations.append("bullish engulfing")
        if rsi_recovery:
            confirmations.append("RSI recovery")
        if confirmations:
            return True, ", ".join(confirmations[:3])
        return False, "no spot LONG reversal confirmation near support"
    except Exception as e:
        return False, f"reversal confirmation error: {e}"


def learning_penalty(symbol, direction, setup_type):
    try:
        path = os.path.join(os.path.dirname(__file__), "trades.json")
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as f:
            trades = json.load(f)
        closed = [t for t in trades if str(t.get("status", "")).upper() in ["TP", "SL"]][-80:]
        if not closed:
            return 0
        symbol_losses = sum(1 for t in closed[-25:] if t.get("pair") == symbol and str(t.get("status", "")).upper() == "SL")
        direction_losses = sum(1 for t in closed[-25:] if t.get("direction") == direction and str(t.get("status", "")).upper() == "SL")
        setup_losses = sum(1 for t in closed[-40:] if t.get("setup_type") == setup_type and str(t.get("status", "")).upper() == "SL")
        penalty = min(symbol_losses * 4 + direction_losses * 2 + setup_losses * 3, 18)
        return int(penalty)
    except Exception:
        return 0


def build_market_context(symbol, interval, df, direction):
    btc_1h = cached_market_data("BTCUSDT", "1h", limit=220)
    eth_1h = cached_market_data("ETHUSDT", "1h", limit=220)
    regime = detect_market_regime(btc_1h, eth_1h)
    mtf = multi_timeframe_quality(symbol, direction, interval, df)
    allowed = True
    reason = "market context accepted"
    if direction == "LONG" and regime in ["DUMP_RISK", "BEARISH", "HIGH_VOLATILITY"]:
        allowed = False
        reason = f"{regime} blocks LONG entries"
    elif direction == "SHORT" and regime == "BULLISH":
        allowed = False
        reason = "BULLISH regime blocks SHORT entries"
    elif mtf.get("strong_conflict"):
        allowed = False
        reason = mtf.get("reason", "strong multi-timeframe conflict")
    return {
        "allowed": allowed,
        "skip_reason": reason,
        "market_regime": regime,
        "multi_timeframe_context": mtf,
    }


def final_signal_score(signal, market_context, sr_targets, mtf_context, reversal_reason):
    regime = market_context.get("market_regime", "SIDEWAYS")
    regime_score = {
        "BULLISH": 18,
        "SIDEWAYS": 13,
        "HIGH_VOLATILITY": 9,
        "BEARISH": 7,
        "DUMP_RISK": 0,
    }.get(regime, 10)
    if signal.get("direction") == "SHORT" and regime in ["BEARISH", "DUMP_RISK", "HIGH_VOLATILITY"]:
        regime_score = max(regime_score, 13)

    trend_power = signal.get("trend_power", "MIXED")
    trend_score = 15 if trend_power in ["STRONG_BULL", "STRONG_BEAR"] else 8 if trend_power == "MIXED" else 6
    sr_score = min(20, int(sr_targets.get("support_strength", 0)) + int(sr_targets.get("resistance_strength", 0)) + 8)
    rr = float(sr_targets.get("risk_reward", 0) or 0)
    rr_score = 15 if rr >= 2.0 else 12 if rr >= 1.8 else 8 if rr >= 1.5 else 0
    volume_score = 10 if signal.get("volume") == "STRONG" else 5
    volatility_state = signal.get("volatility_state", "NORMAL")
    volatility_score = 8 if volatility_state in ["NORMAL", "HEALTHY", "MODERATE", "N/A"] else 5
    mtf_score = int(mtf_context.get("score", 0) or 0)
    setup_type = sr_targets.get("setup_type", "S/R_CONTINUATION")
    penalty = learning_penalty(signal.get("pair"), signal.get("direction"), setup_type)
    final_score = max(0, min(100, regime_score + trend_score + sr_score + rr_score + volume_score + volatility_score + mtf_score - penalty))

    reason = (
        f"{regime} regime; {mtf_context.get('state', 'UNCONFIRMED')} MTF; "
        f"S/R strength {sr_targets.get('support_strength')}/{sr_targets.get('resistance_strength')}; "
        f"RR {rr}; {reversal_reason}; learning penalty {penalty}"
    )
    return {
        "final_score": int(final_score),
        "market_regime": regime,
        "multi_timeframe": mtf_context.get("state", signal.get("multi_timeframe", "N/A")),
        "setup_type": setup_type,
        "learning_penalty": penalty,
        "market_regime_score": regime_score,
        "support_resistance_score": sr_score,
        "risk_reward_score": rr_score,
        "final_score_reason": reason,
        "signal_quality_reason": f"{signal.get('signal_quality_reason', 'S/R validated')} | {reason}",
    }


def skip_signal(symbol, interval, reason):
    try:
        key = (symbol, interval, reason)
        now = time.time()
        if now - SIGNAL_SKIP_LOG_CACHE.get(key, 0) >= SIGNAL_SKIP_LOG_TTL_SECONDS:
            SIGNAL_SKIP_LOG_CACHE[key] = now
            print(f"SIGNAL_SKIPPED symbol={symbol} timeframe={interval} reason={reason}")
        LAST_DRY_RUN_SKIPS.append({"symbol": symbol, "timeframe": interval, "skip_reason": reason})
        if len(LAST_DRY_RUN_SKIPS) > 200:
            del LAST_DRY_RUN_SKIPS[:-200]
    except Exception:
        pass
    return None



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


# ================= SUPPORT / RESISTANCE TARGETS =================
def _cluster_price_levels(raw_levels, tolerance_pct=0.0025, limit=8):
    if not raw_levels:
        return []

    raw_levels = sorted(raw_levels, key=lambda item: item[0])
    clusters = []
    for price, index in raw_levels:
        if price <= 0:
            continue
        if not clusters:
            clusters.append({"prices": [price], "strength": 1, "last_index": index})
            continue

        current = clusters[-1]
        avg_price = sum(current["prices"]) / len(current["prices"])
        tolerance = max(avg_price * tolerance_pct, 1e-12)
        if abs(price - avg_price) <= tolerance:
            current["prices"].append(price)
            current["strength"] += 1
            current["last_index"] = max(current["last_index"], index)
        else:
            clusters.append({"prices": [price], "strength": 1, "last_index": index})

    scored = []
    for cluster in clusters:
        avg_price = sum(cluster["prices"]) / len(cluster["prices"])
        scored.append({
            "price": avg_price,
            "strength": cluster["strength"],
            "last_index": cluster["last_index"],
        })

    scored.sort(key=lambda item: (item["strength"], item["last_index"]), reverse=True)
    return [item["price"] for item in scored[:limit]]


def _cluster_price_level_meta(levels, tolerance_pct=0.0025, limit=8):
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda item: item[0])
    clusters = []

    for item in sorted_levels:
        if len(item) >= 4:
            price, index, reaction, volume_confirmation = item[:4]
        elif len(item) >= 3:
            price, index, reaction = item[:3]
            volume_confirmation = False
        else:
            price, index = item[:2]
            reaction = 0
            volume_confirmation = False

        if not clusters:
            clusters.append({
                "prices": [float(price)],
                "indices": [int(index)],
                "reactions": [float(reaction or 0)],
                "volume_hits": 1 if volume_confirmation else 0,
            })
            continue

        current = clusters[-1]
        avg_price = sum(current["prices"]) / len(current["prices"])
        tolerance = max(avg_price * tolerance_pct, 1e-12)
        if abs(float(price) - avg_price) <= tolerance:
            current["prices"].append(float(price))
            current["indices"].append(int(index))
            current["reactions"].append(float(reaction or 0))
            if volume_confirmation:
                current["volume_hits"] += 1
        else:
            clusters.append({
                "prices": [float(price)],
                "indices": [int(index)],
                "reactions": [float(reaction or 0)],
                "volume_hits": 1 if volume_confirmation else 0,
            })

    scored = []
    total_len = max(max((max(c["indices"]) for c in clusters), default=1), 1)
    for cluster in clusters:
        avg_price = sum(cluster["prices"]) / len(cluster["prices"])
        touches = len(cluster["prices"])
        last_seen_index = max(cluster["indices"])
        age = max(total_len - last_seen_index, 0)
        reaction_score = sum(1 for value in cluster["reactions"] if value >= 0.004)
        volume_confirmation = cluster["volume_hits"] > 0
        recency_score = 2 if age <= 35 else 1 if age <= 80 else 0
        strength = touches + reaction_score + recency_score + (1 if volume_confirmation else 0)
        scored.append({
            "price": avg_price,
            "touches": touches,
            "strength": int(strength),
            "last_seen_index": last_seen_index,
            "last_index": last_seen_index,
            "age": age,
            "volume_confirmation": volume_confirmation,
            "reaction_score": reaction_score,
        })

    scored.sort(key=lambda item: (item["strength"], item["touches"], item["last_seen_index"]), reverse=True)
    return scored[:limit]


def calculate_support_resistance(candles):
    try:
        df = candles.tail(220).reset_index(drop=True)
        if len(df) < 50:
            return {"support": [], "resistance": [], "support_meta": [], "resistance_meta": []}

        df = df.copy()
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["high", "low", "close"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        if len(df) < 50:
            return {"support": [], "resistance": [], "support_meta": [], "resistance_meta": []}

        supports = []
        resistances = []
        lows = df["low"].astype(float).tolist()
        highs = df["high"].astype(float).tolist()
        closes = df["close"].astype(float).tolist()
        volumes = df["volume"].astype(float).fillna(0).tolist()
        volume_ma = df["volume"].rolling(20).mean().fillna(0).tolist()
        atr_series = atr(df).fillna(0).tolist()

        for i in range(3, len(df) - 5):
            low_window = lows[i - 3:i + 4]
            high_window = highs[i - 3:i + 4]
            future_closes = closes[i + 1:i + 6]
            atr_here = float(atr_series[i] or 0)
            vol_ok = bool(volume_ma[i] and volumes[i] >= volume_ma[i] * 1.03)

            if lows[i] == min(low_window) and lows[i] < min(lows[i - 1], lows[i + 1]):
                reaction = 0
                if lows[i] > 0 and future_closes:
                    reaction = (max(future_closes) - lows[i]) / lows[i]
                if atr_here <= 0 or reaction >= max(0.0025, (atr_here / max(lows[i], 1e-12)) * 0.45):
                    supports.append((lows[i], i, reaction, vol_ok))

            if highs[i] == max(high_window) and highs[i] > max(highs[i - 1], highs[i + 1]):
                reaction = 0
                if highs[i] > 0 and future_closes:
                    reaction = (highs[i] - min(future_closes)) / highs[i]
                if atr_here <= 0 or reaction >= max(0.0025, (atr_here / max(highs[i], 1e-12)) * 0.45):
                    resistances.append((highs[i], i, reaction, vol_ok))

        support_meta = _cluster_price_level_meta(supports, tolerance_pct=0.003, limit=10)
        resistance_meta = _cluster_price_level_meta(resistances, tolerance_pct=0.003, limit=10)
        # Sale-ready filter: prefer levels that were touched more than once and reacted recently.
        strong_support = [
            item for item in support_meta
            if item["touches"] >= 2 and item["strength"] >= 4 and item.get("age", 999) <= 150
        ]
        strong_resistance = [
            item for item in resistance_meta
            if item["touches"] >= 2 and item["strength"] >= 4 and item.get("age", 999) <= 150
        ]

        return {
            "support": [item["price"] for item in strong_support],
            "resistance": [item["price"] for item in strong_resistance],
            "support_meta": strong_support,
            "resistance_meta": strong_resistance,
        }
    except Exception as e:
        print(f"calculate_support_resistance error: {e}")
        return {"support": [], "resistance": [], "support_meta": [], "resistance_meta": []}


def nearest_support(price, levels):
    try:
        price = float(price)
        below = [float(level) for level in levels if float(level) < price]
        return max(below) if below else None
    except Exception:
        return None


def nearest_resistance(price, levels):
    try:
        price = float(price)
        above = [float(level) for level in levels if float(level) > price]
        return min(above) if above else None
    except Exception:
        return None


def _level_meta_for_price(price, meta_levels):
    try:
        if price is None:
            return {}
        price = float(price)
        if not meta_levels:
            return {}
        return min(meta_levels, key=lambda item: abs(float(item.get("price", 0)) - price))
    except Exception:
        return {}


def sr_based_targets(candles, entry, direction, atr_value=None, min_rr=2.0):
    try:
        entry = float(entry)
        atr_value = float(atr_value or 0)
    except Exception:
        return None

    levels = calculate_support_resistance(candles)
    supports = sorted([float(level) for level in levels.get("support", []) if float(level) > 0])
    resistances = sorted([float(level) for level in levels.get("resistance", []) if float(level) > 0])
    support = nearest_support(entry, supports)
    resistance = nearest_resistance(entry, resistances)

    if support is None or resistance is None:
        return None

    support_meta = _level_meta_for_price(support, levels.get("support_meta", []))
    resistance_meta = _level_meta_for_price(resistance, levels.get("resistance_meta", []))
    support_strength = int(support_meta.get("strength", 0) or 0)
    resistance_strength = int(resistance_meta.get("strength", 0) or 0)
    if (
        support_strength < 4
        or resistance_strength < 4
        or int(support_meta.get("touches", 0) or 0) < 2
        or int(resistance_meta.get("touches", 0) or 0) < 2
    ):
        return None

    min_target_distance = max(entry * 0.007, atr_value * 0.75 if atr_value > 0 else 0)
    buffer = max(entry * 0.002, atr_value * 0.35 if atr_value > 0 else 0)
    preferred_rr = max(float(min_rr or 2.0), 2.0)
    absolute_min_rr = 1.8

    if direction == "LONG":
        if not (support < entry):
            return None
        sl = support - buffer
        if sl <= 0 or sl >= entry:
            return None
        risk = entry - sl
        candidates = [level for level in resistances if level > entry + min_target_distance]
        tp = None
        rr = None
        preferred_found = False
        for level in candidates:
            reward = level - entry
            current_rr = reward / risk if risk > 0 else 0
            if current_rr >= preferred_rr:
                tp = level
                rr = current_rr
                preferred_found = True
                break
            if tp is None and current_rr >= absolute_min_rr:
                tp = level
                rr = current_rr
        if tp is None:
            return None
    elif direction == "SHORT":
        if not (resistance > entry):
            return None
        sl = resistance + buffer
        if sl <= entry:
            return None
        risk = sl - entry
        candidates = [level for level in reversed(supports) if level < entry - min_target_distance]
        tp = None
        rr = None
        preferred_found = False
        for level in candidates:
            reward = entry - level
            current_rr = reward / risk if risk > 0 else 0
            if current_rr >= preferred_rr:
                tp = level
                rr = current_rr
                preferred_found = True
                break
            if tp is None and current_rr >= absolute_min_rr:
                tp = level
                rr = current_rr
        if tp is None:
            return None
    else:
        return None

    setup_type = "S/R_CONTINUATION" if preferred_found else "S/R_MINIMUM_RR"
    quality = "preferred" if preferred_found else "minimum acceptable"
    return {
        "tp": tp,
        "sl": sl,
        "support": support,
        "resistance": resistance,
        "nearest_support": support,
        "nearest_resistance": resistance,
        "support_strength": support_strength,
        "resistance_strength": resistance_strength,
        "risk_reward": round(rr, 2),
        "target_basis": "Strong Support/Resistance",
        "setup_type": setup_type,
        "signal_quality_reason": (
            f"Strong real S/R validated; support strength {support_strength} "
            f"({int(support_meta.get('touches', 0) or 0)} touches), "
            f"resistance strength {resistance_strength} "
            f"({int(resistance_meta.get('touches', 0) or 0)} touches), "
            f"{quality} RR {round(rr, 2)}"
        ),
    }


def _recent_extension_pct(df, direction, lookback=5):
    try:
        if df is None or len(df) < lookback + 2:
            return 0.0
        entry = float(df["close"].iloc[-1])
        ref = float(df["close"].iloc[-lookback-1])
        if entry <= 0 or ref <= 0:
            return 0.0
        if direction == "LONG":
            return (entry - ref) / ref
        return (ref - entry) / ref
    except Exception:
        return 0.0


def _wick_reversal_warning(df, direction):
    try:
        if df is None or len(df) < 4:
            return False
        recent = df.tail(3)
        warnings = 0
        for _, candle in recent.iterrows():
            high = float(candle["high"])
            low = float(candle["low"])
            open_ = float(candle["open"])
            close = float(candle["close"])
            rng = max(high - low, 1e-12)
            upper = high - max(open_, close)
            lower = min(open_, close) - low
            body = abs(close - open_)
            if direction == "LONG" and upper / rng > 0.42 and body / rng < 0.48:
                warnings += 1
            if direction == "SHORT" and lower / rng > 0.42 and body / rng < 0.48:
                warnings += 1
        return warnings >= 2
    except Exception:
        return False


def _sr_reaction_confirmation(df, direction, support, resistance, atr_value, interval="5m"):
    """Confirm that price is reacting from S/R instead of chasing a finished move."""
    try:
        if df is None or len(df) < 35:
            return False, "not enough candles for S/R reaction confirmation"
        recent = df.tail(8)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(last["close"])
        open_ = float(last["open"])
        prev_close = float(prev["close"])
        support = float(support)
        resistance = float(resistance)
        atr_value = float(atr_value) if atr_value is not None and not pd.isna(atr_value) else 0.0
        if close <= 0 or support <= 0 or resistance <= 0 or atr_value <= 0:
            return False, "invalid S/R reaction inputs"

        ema20 = float(ema(df, 20).iloc[-1])
        ema50 = float(ema(df, 50).iloc[-1])
        rsi_series = rsi(df)
        rsi_now = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0

        touch_buffer = max(atr_value * 0.55, close * {"5m": 0.0035, "15m": 0.0055, "1h": 0.009}.get(interval, 0.005))
        reclaim_buffer = max(atr_value * 0.18, close * 0.0015)

        if direction == "LONG":
            touched_support = float(recent["low"].min()) <= support + touch_buffer
            reclaimed = close > support + reclaim_buffer and close >= prev_close
            candle_ok = close > open_ or close > ema20
            trend_ok = close >= ema20 * 0.996 and ema20 >= ema50 * 0.992
            rsi_ok = 42 <= rsi_now <= 68
            if not touched_support:
                return False, "LONG skipped: no fresh support touch/retest"
            if not reclaimed:
                return False, "LONG skipped: support not reclaimed yet"
            if not candle_ok:
                return False, "LONG skipped: weak reaction candle"
            if not trend_ok:
                return False, "LONG skipped: EMA structure not supportive"
            if not rsi_ok:
                return False, f"LONG skipped: RSI {round(rsi_now, 1)} not in safe rebound zone"
            return True, "LONG confirmed by support retest, reclaim, EMA and RSI"

        if direction == "SHORT":
            touched_resistance = float(recent["high"].max()) >= resistance - touch_buffer
            rejected = close < resistance - reclaim_buffer and close <= prev_close
            candle_ok = close < open_ or close < ema20
            trend_ok = close <= ema20 * 1.004 and ema20 <= ema50 * 1.008
            rsi_ok = 32 <= rsi_now <= 58
            if not touched_resistance:
                return False, "SHORT skipped: no fresh resistance touch/retest"
            if not rejected:
                return False, "SHORT skipped: resistance not rejected yet"
            if not candle_ok:
                return False, "SHORT skipped: weak rejection candle"
            if not trend_ok:
                return False, "SHORT skipped: EMA structure not supportive"
            if not rsi_ok:
                return False, f"SHORT skipped: RSI {round(rsi_now, 1)} not in safe rejection zone"
            return True, "SHORT confirmed by resistance retest, rejection, EMA and RSI"

        return False, "unknown direction"
    except Exception as e:
        return False, f"S/R reaction confirmation error: {e}"


def _entry_location_filter(df, direction, sr_targets, atr_value, interval="5m"):
    """Reject entries that are late in the move or too close to the next opposing level."""
    try:
        entry = float(df["close"].iloc[-1])
        support = float(sr_targets.get("support") or sr_targets.get("nearest_support"))
        resistance = float(sr_targets.get("resistance") or sr_targets.get("nearest_resistance"))
        if entry <= 0 or support <= 0 or resistance <= 0 or resistance <= support:
            return False, "invalid support/resistance range"
        rng = resistance - support
        pos = (entry - support) / rng
        atr_value = float(atr_value) if atr_value is not None and not pd.isna(atr_value) else 0.0
        atr_ratio = atr_value / entry if entry else 0.0
        extension_limit = {"5m": 0.0085, "15m": 0.014, "1h": 0.022}.get(interval, 0.012)
        extension = _recent_extension_pct(df, direction, lookback=5)

        if direction == "LONG":
            # The bot must buy near a confirmed support/reclaim, not after the move is almost finished.
            max_support_distance = max(0.006, atr_ratio * 1.15)
            if pos > 0.34:
                return False, f"late LONG entry: price already {round(pos*100, 1)}% through S/R range"
            if (entry - support) / entry > max_support_distance:
                return False, "LONG entry too far from confirmed support"
            if (resistance - entry) / entry < max(0.012, atr_ratio * 1.35):
                return False, "LONG entry too close to resistance"
            if extension > extension_limit * 0.75:
                return False, f"late LONG pump extension {round(extension*100, 2)}%"
            if _wick_reversal_warning(df, direction):
                return False, "LONG rejected by upper-wick exhaustion"
        else:
            # The bot must short near resistance, not after most of the dump has already happened.
            max_resistance_distance = max(0.006, atr_ratio * 1.15)
            if pos < 0.66:
                return False, f"late SHORT entry: price already near support ({round(pos*100, 1)}% range position)"
            if (resistance - entry) / entry > max_resistance_distance:
                return False, "SHORT entry too far from confirmed resistance"
            if (entry - support) / entry < max(0.012, atr_ratio * 1.35):
                return False, "SHORT entry too close to support"
            if extension > extension_limit * 0.75:
                return False, f"late SHORT dump extension {round(extension*100, 2)}%"
            if _wick_reversal_warning(df, direction):
                return False, "SHORT rejected by lower-wick exhaustion"

        reaction_ok, reaction_reason = _sr_reaction_confirmation(df, direction, support, resistance, atr_value, interval)
        if not reaction_ok:
            return False, reaction_reason

        return True, f"entry protected by S/R location and reaction: {reaction_reason}"
    except Exception as e:
        return False, f"entry location filter error: {e}"


def _market_direction_guard(direction, market_context, mtf_context):
    """Hard guard: do not fight BTC/ETH regime or unclear MTF."""
    regime = market_context.get("market_regime", "SIDEWAYS")
    mtf_state = mtf_context.get("state", "UNCONFIRMED")
    if mtf_state != "CONFIRMED":
        return False, f"MTF not confirmed: {mtf_state}"
    if direction == "LONG" and regime in ["DUMP_RISK", "BEARISH", "HIGH_VOLATILITY"]:
        return False, f"{regime} blocks LONG entries"
    if direction == "SHORT" and regime == "BULLISH":
        return False, "BULLISH regime blocks SHORT entries"
    return True, "market direction confirmed"


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
        if rr < 1.8:
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

    market_context = build_market_context(symbol, interval, df, direction)
    if not market_context.get("allowed", True):
        return skip_signal(symbol, interval, market_context.get("skip_reason", "market context rejected"))
    mtf_context = market_context.get("multi_timeframe_context", {})
    market_ok, market_reason = _market_direction_guard(direction, market_context, mtf_context)
    if not market_ok:
        return skip_signal(symbol, interval, market_reason)

    if not strong_signal_filter(df, trend, trend_power, direction):
        return skip_signal(symbol, interval, "local trend/momentum filter rejected setup")

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)

    # منع العكس القوي جدًا فقط
    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < (MIN_SCORE_TO_TRADE + 2):
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < (MIN_SCORE_TO_TRADE + 2):
        return None

    # ================= NEW FILTERS =================
    if late_entry_filter(df, direction):
        return None

    if not support_resistance_filter(df, direction):
        return None

    if not pullback_entry_quality(df, direction):
        return None

    if not rejection_wick_filter(df, direction):
        return None

    entry = df["close"].iloc[-1]
    sr_targets = sr_based_targets(df, entry, direction, atr_val)
    if not sr_targets:
        return None
    tp = sr_targets["tp"]
    sl = sr_targets["sl"]
    location_ok, location_reason = _entry_location_filter(df, direction, sr_targets, atr_val, interval)
    if not location_ok:
        return skip_signal(symbol, interval, location_reason)
    if direction == "LONG":
        reversal_ok, reversal_reason = spot_long_confirmation(df, sr_targets.get("support"))
        if not reversal_ok:
            return skip_signal(symbol, interval, reversal_reason)
    else:
        reversal_reason = "short protected by strong resistance"

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

    signal = {
        "pair": symbol,
        "timeframe": interval,
        "type": "FUTURES",
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
        "score": score,
        "support": format_price(sr_targets["support"]),
        "resistance": format_price(sr_targets["resistance"]),
        "nearest_support": format_price(sr_targets["nearest_support"]),
        "nearest_resistance": format_price(sr_targets["nearest_resistance"]),
        "risk_reward": sr_targets["risk_reward"],
        "support_strength": sr_targets.get("support_strength"),
        "resistance_strength": sr_targets.get("resistance_strength"),
        "target_basis": sr_targets["target_basis"],
        "setup_type": sr_targets.get("setup_type", "S/R_CONTINUATION"),
        "market_regime": market_context.get("market_regime", "SIDEWAYS"),
        "signal_quality_reason": sr_targets.get("signal_quality_reason", "Strong support/resistance validation passed"),
        "entry_location_reason": location_reason,
        "management_note": "If price reaches +0.6R then protect the trade: move SL to breakeven or take partial profit.",
        "breakeven_trigger_r": 0.6
    }

    ai_engine_report = build_ai_engine_report(
        df,
        {
            "timeframe": interval,
            "direction": direction,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "confidence": confidence,
        },
        higher_tf_ok=htf_ok,
    )

    if ai_engine_report["risk_score"] >= 78:
        return None

    type_scores = evaluate_trade_types(
        direction=direction,
        trend=trend,
        trend_power=trend_power,
        confidence=confidence,
        htf_ok=htf_ok,
        structure=structure,
        volume=volume,
        volatility_state=ai_engine_report["volatility_state"],
        risk_score=ai_engine_report["risk_score"],
        timeframe=interval,
    )
    trade_type, adjusted_type_scores = choose_trade_type(type_scores)
    signal["type"] = trade_type

    signal.update({
        "type_scores": adjusted_type_scores,
        "spot_score": adjusted_type_scores.get("SPOT", 0),
        "futures_score": adjusted_type_scores.get("FUTURES", 0),
        "risk_score": ai_engine_report["risk_score"],
        "risk_level": ai_engine_report["risk_level"],
        "engine_confidence": ai_engine_report["engine_confidence"],
        "multi_timeframe": ai_engine_report["multi_timeframe"],
        "multi_timeframe_score": ai_engine_report["multi_timeframe_score"],
        "market_structure": ai_engine_report["market_structure"],
        "structure_score": ai_engine_report["structure_score"],
        "volume_state": ai_engine_report["volume_state"],
        "volume_score": ai_engine_report["volume_score"],
        "volume_ratio": ai_engine_report["volume_ratio"],
        "volatility_state": ai_engine_report["volatility_state"],
        "volatility_score": ai_engine_report["volatility_score"],
        "atr_ratio": ai_engine_report["atr_ratio"],
        "trend_score": ai_engine_report["trend_score"],
        "ema_alignment": ai_engine_report["ema_alignment"],
        "ai_engine": ai_engine_report,
    })

    score_report = final_signal_score(signal, market_context, sr_targets, mtf_context, reversal_reason)
    required_score = MIN_SPOT_FINAL_SCORE if signal.get("type") == "SPOT" else MIN_FUTURES_FINAL_SCORE
    if score_report["final_score"] < required_score:
        return skip_signal(symbol, interval, f"final score {score_report['final_score']} below {required_score}: {score_report['final_score_reason']}")
    signal.update(score_report)

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

    market_context = build_market_context(symbol, interval, df, direction)
    if not market_context.get("allowed", True):
        return skip_signal(symbol, interval, market_context.get("skip_reason", "market context rejected"))
    mtf_context = market_context.get("multi_timeframe_context", {})
    market_ok, market_reason = _market_direction_guard(direction, market_context, mtf_context)
    if not market_ok:
        return skip_signal(symbol, interval, market_reason)

    if not strong_signal_filter(df, trend, trend_power, direction):
        return skip_signal(symbol, interval, "local trend/momentum filter rejected setup")

    htf_ok = higher_timeframe_confirmation(symbol, direction, interval)

    if not htf_ok and abs(score) < 6:
        return None

    if direction == "LONG" and trend_power == "STRONG_BEAR" and abs(score) < 6:
        return None

    if direction == "SHORT" and trend_power == "STRONG_BULL" and abs(score) < 6:
        return None

    # ================= NEW FILTERS =================
    if late_entry_filter(df, direction):
        return None

    if not support_resistance_filter(df, direction):
        return None

    if not pullback_entry_quality(df, direction):
        return None

    if not rejection_wick_filter(df, direction):
        return None

    entry = df["close"].iloc[-1]
    sr_targets = sr_based_targets(df, entry, direction, atr_val)
    if not sr_targets:
        return None
    tp = sr_targets["tp"]
    sl = sr_targets["sl"]
    location_ok, location_reason = _entry_location_filter(df, direction, sr_targets, atr_val, interval)
    if not location_ok:
        return skip_signal(symbol, interval, location_reason)
    if direction == "LONG":
        reversal_ok, reversal_reason = spot_long_confirmation(df, sr_targets.get("support"))
        if not reversal_ok:
            return skip_signal(symbol, interval, reversal_reason)
    else:
        reversal_reason = "short protected by strong resistance"

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

    signal = {
        "pair": symbol,
        "timeframe": interval,
        "type": "FUTURES",
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
        "score": score,
        "support": format_price(sr_targets["support"]),
        "resistance": format_price(sr_targets["resistance"]),
        "nearest_support": format_price(sr_targets["nearest_support"]),
        "nearest_resistance": format_price(sr_targets["nearest_resistance"]),
        "risk_reward": sr_targets["risk_reward"],
        "support_strength": sr_targets.get("support_strength"),
        "resistance_strength": sr_targets.get("resistance_strength"),
        "target_basis": sr_targets["target_basis"],
        "setup_type": sr_targets.get("setup_type", "S/R_CONTINUATION"),
        "market_regime": market_context.get("market_regime", "SIDEWAYS"),
        "signal_quality_reason": sr_targets.get("signal_quality_reason", "Strong support/resistance validation passed"),
        "entry_location_reason": location_reason,
        "management_note": "If price reaches +0.6R then protect the trade: move SL to breakeven or take partial profit.",
        "breakeven_trigger_r": 0.6
    }

    ai_engine_report = build_ai_engine_report(
        df,
        {
            "timeframe": interval,
            "direction": direction,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "confidence": confidence,
        },
        higher_tf_ok=htf_ok,
    )

    if ai_engine_report["risk_score"] >= 82:
        return None

    type_scores = evaluate_trade_types(
        direction=direction,
        trend=trend,
        trend_power=trend_power,
        confidence=confidence,
        htf_ok=htf_ok,
        structure=structure,
        volume=volume,
        volatility_state=ai_engine_report["volatility_state"],
        risk_score=ai_engine_report["risk_score"],
        timeframe=interval,
    )
    trade_type, adjusted_type_scores = choose_trade_type(type_scores)
    signal["type"] = trade_type

    signal.update({
        "type_scores": adjusted_type_scores,
        "spot_score": adjusted_type_scores.get("SPOT", 0),
        "futures_score": adjusted_type_scores.get("FUTURES", 0),
        "risk_score": ai_engine_report["risk_score"],
        "risk_level": ai_engine_report["risk_level"],
        "engine_confidence": ai_engine_report["engine_confidence"],
        "multi_timeframe": ai_engine_report["multi_timeframe"],
        "multi_timeframe_score": ai_engine_report["multi_timeframe_score"],
        "market_structure": ai_engine_report["market_structure"],
        "structure_score": ai_engine_report["structure_score"],
        "volume_state": ai_engine_report["volume_state"],
        "volume_score": ai_engine_report["volume_score"],
        "volume_ratio": ai_engine_report["volume_ratio"],
        "volatility_state": ai_engine_report["volatility_state"],
        "volatility_score": ai_engine_report["volatility_score"],
        "atr_ratio": ai_engine_report["atr_ratio"],
        "trend_score": ai_engine_report["trend_score"],
        "ema_alignment": ai_engine_report["ema_alignment"],
        "ai_engine": ai_engine_report,
    })

    score_report = final_signal_score(signal, market_context, sr_targets, mtf_context, reversal_reason)
    required_score = MIN_SPOT_FINAL_SCORE if signal.get("type") == "SPOT" else MIN_FUTURES_FINAL_SCORE
    if score_report["final_score"] < required_score:
        return skip_signal(symbol, interval, f"final score {score_report['final_score']} below {required_score}: {score_report['final_score_reason']}")
    signal.update(score_report)

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

    scan_symbols = get_scan_symbols()
    print(f"Dynamic symbols loaded: {len(scan_symbols)} symbols")

    for symbol in scan_symbols:
        for tf in TIMEFRAMES:
            try:
                signal = generate_free_signal(symbol, tf)
                if signal:
                    signal["ranking_score"] = (
                        signal["confidence"]
                        + abs(signal["score"] * 2)
                        + max(0, 20 - int(signal.get("risk_score", 50) / 4))
                        + (signal.get("engine_confidence", signal["confidence"]) * 0.18)
                        + (signal.get("multi_timeframe_score", 50) * 0.12)
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
            record_trade_type(s.get("type"))

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
                record_trade_type(s.get("type"))

            if len(best) >= limit:
                break

    print(f"Top signals selected: {best}")
    return best

# ================= DRY RUN / SIGNAL HUNTER VERIFICATION =================
def _dry_signal_view(signal):
    """Return a compact, safe representation of a generated signal for dry-run output."""
    if not signal:
        return None
    return {
        "pair": signal.get("pair"),
        "timeframe": signal.get("timeframe"),
        "type": signal.get("type"),
        "direction": signal.get("direction"),
        "entry": signal.get("entry"),
        "tp": signal.get("tp"),
        "sl": signal.get("sl"),
        "support": signal.get("support"),
        "resistance": signal.get("resistance"),
        "risk_reward": signal.get("risk_reward"),
        "final_score": signal.get("final_score"),
        "market_regime": signal.get("market_regime"),
        "setup_type": signal.get("setup_type"),
        "quality_reason": signal.get("signal_quality_reason") or signal.get("final_score_reason"),
    }


def dry_run_signal_scan(symbols=None, timeframes=None, max_passed=10, verbose=True):
    """
    Dry-run the Signal Hunter without Telegram sends or database writes.

    It scans the conservative whitelist, prints PASSED/SKIPPED reasons, and returns
    a summary dict. This function is intentionally top-level so it can be imported:

        python -c "from market_analyzer import dry_run_signal_scan; print(dry_run_signal_scan())"
    """
    selected_symbols = list(symbols or get_scan_symbols())
    selected_timeframes = list(timeframes or TIMEFRAMES)
    summary = {
        "passed_count": 0,
        "skipped_count": 0,
        "errors_count": 0,
        "passed": [],
        "skipped": [],
        "errors": [],
    }

    for symbol in selected_symbols:
        for tf in selected_timeframes:
            before_skip_count = len(LAST_DRY_RUN_SKIPS)
            try:
                signal = generate_signal(symbol, tf)
                if signal:
                    row = _dry_signal_view(signal)
                    summary["passed_count"] += 1
                    summary["passed"].append(row)
                    if verbose:
                        print(
                            "PASSED "
                            f"symbol={row.get('pair')} tf={row.get('timeframe')} "
                            f"type={row.get('type')} dir={row.get('direction')} "
                            f"score={row.get('final_score')} rr={row.get('risk_reward')} "
                            f"regime={row.get('market_regime')} reason={row.get('quality_reason')}"
                        )
                    if len(summary["passed"]) >= max_passed:
                        continue
                else:
                    # Prefer the explicit skip reason captured by skip_signal(). If a
                    # filter returned None without logging, still report a clear generic reason.
                    reason = "filtered by hunter quality gates"
                    if len(LAST_DRY_RUN_SKIPS) > before_skip_count:
                        last = LAST_DRY_RUN_SKIPS[-1]
                        if last.get("symbol") == symbol and last.get("timeframe") == tf:
                            reason = last.get("skip_reason") or reason
                    row = {"symbol": symbol, "timeframe": tf, "reason": reason}
                    summary["skipped_count"] += 1
                    summary["skipped"].append(row)
                    if verbose:
                        print(f"SKIPPED symbol={symbol} tf={tf} reason={reason}")
            except Exception as exc:
                row = {"symbol": symbol, "timeframe": tf, "error": str(exc)}
                summary["errors_count"] += 1
                summary["errors"].append(row)
                if verbose:
                    print(f"ERROR symbol={symbol} tf={tf} error={exc}")

    if verbose:
        print(
            "DRY_RUN_SUMMARY "
            f"passed={summary['passed_count']} skipped={summary['skipped_count']} errors={summary['errors_count']}"
        )
    return summary
