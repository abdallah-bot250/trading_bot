import time
import requests
from datetime import datetime, timedelta
from market_analyzer import get_top_free_signals, generate_signal, SYMBOLS
from ai_model import predict_trade
import ccxt
import os
import psycopg2
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# ================= SAFE IMPORTS =================
import logging
from contextlib import contextmanager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
FERNET_KEY = os.environ.get("FERNET_KEY", "").strip()

if not FERNET_KEY:
    raise Exception("FERNET_KEY missing in environment variables")

cipher = Fernet(FERNET_KEY.encode())

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log(msg):
    logging.info(msg)

# ================= REQUEST SESSION WITH RETRY =================
session_requests = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
adapter = HTTPAdapter(max_retries=retry)
session_requests.mount("http://", adapter)
session_requests.mount("https://", adapter)

def decrypt_text(value):
    if not value:
        return None
    try:
        return cipher.decrypt(value.encode()).decode()
    except Exception as e:
        log(f"decrypt_text error: {e}")
        return None

TOKEN = os.environ.get("TELEGRAM_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "").strip().rstrip("/")

# ================= CONFIG =================
MAX_DAILY_TRADES = 4
MAX_CONSECUTIVE_LOSSES = 2
MAX_DAILY_LOSS_PERCENT = 4
PAIR_COOLDOWN_MINUTES = 45
GLOBAL_LOOP_SLEEP = 80
MIN_CONFIDENCE = 66
DUPLICATE_WINDOW_SECONDS = 300
NO_SIGNAL_NOTIFY_COOLDOWN_MINUTES = 360  # 6 ساعات

# ===== MONSTER FILTERS =====
MAX_ENTRY_DEVIATION_PERCENT = 0.75
SIGNAL_FRESHNESS_SECONDS = 180
MAX_OPEN_TRADES_PER_USER = 2
FREE_SIGNALS_LIMIT = 2

# ===== QUALITY CONTROL =====
MAX_SIGNALS_PER_CYCLE = 2
ULTRA_MODE = True

# ================= DUPLICATE SIGNAL CACHE =================
LAST_SIGNAL_CACHE = {
    "pair": None,
    "direction": None,
    "entry": None,
    "time": None
}

# ================= SIGNAL MEMORY =================
RECENT_SIGNAL_MEMORY = {}
LAST_NO_SIGNAL_NOTIFY = {}

# ================= DB =================
def db():
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL")

    if not database_url:
        raise Exception("DATABASE_URL not found in environment variables")

    database_url = database_url.strip()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(database_url, sslmode="require")

@contextmanager
def get_db():
    conn = db()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass

def normalize_pair(pair):
    try:
        return str(pair).upper().replace("/", "").replace("-", "").strip()
    except Exception:
        return str(pair).upper().strip()

def is_duplicate_open_trade(conn, username, pair, timeframe, direction, cooldown_minutes=25):
    """
    يمنع:
    1) نفس الصفقة لو لسه OPEN
    2) أو لو اتفتحت قريب جدًا (cooldown)
    """
    try:
        c = conn.cursor()

        pair = normalize_pair(pair)
        timeframe = str(timeframe).strip().lower()
        direction = str(direction).strip().upper()

        # ================= 1) OPEN DUPLICATE =================
        c.execute("""
            SELECT id
            FROM trades_log
            WHERE chat_id = %s
              AND UPPER(REPLACE(REPLACE(pair, '/', ''), '-', '')) = %s
              AND LOWER(COALESCE(direction, '')) = %s
              AND UPPER(COALESCE(status, 'OPEN')) = 'OPEN'
            ORDER BY id DESC
            LIMIT 1
        """, (str(username), pair, direction.lower()))

        open_trade = c.fetchone()
        if open_trade:
            return True

        # ================= 2) RECENT DUPLICATE COOLDOWN =================
        c.execute(f"""
            SELECT id
            FROM trades_log
            WHERE chat_id = %s
              AND UPPER(REPLACE(REPLACE(pair, '/', ''), '-', '')) = %s
              AND LOWER(COALESCE(direction, '')) = %s
              AND created_at >= NOW() - INTERVAL '{int(cooldown_minutes)} minutes'
            ORDER BY id DESC
            LIMIT 1
        """, (str(username), pair, direction.lower()))

        recent_trade = c.fetchone()
        if recent_trade:
            return True

        return False

    except Exception as e:
        log(f"is_duplicate_open_trade error: {e}")
        return False

# ================= TELEGRAM =================
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

def send(chat_id, text):
    try:
        if not TOKEN or not chat_id:
            log(f"Telegram skipped: TOKEN or chat_id missing | chat_id={chat_id}")
            return False

        r = session_requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": str(chat_id), "text": text},
            timeout=10
        )

        if r.status_code != 200:
            log(f"Telegram HTTP Error {r.status_code}: {r.text}")
            return False

        data = r.json()
        if not data.get("ok"):
            log(f"Telegram API Error: {data}")
            return False

        return True

    except Exception as e:
        log(f"Telegram Error: {e}")
        return False

def send_channel(text):
    try:
        if not TOKEN or not CHANNEL_ID:
            log("Telegram skipped: TOKEN or CHANNEL_ID missing for channel")
            return False

        r = session_requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": str(CHANNEL_ID),
                "text": text
            },
            timeout=10
        )

        if r.status_code != 200:
            log(f"Channel HTTP Error {r.status_code}: {r.text}")
            return False

        data = r.json()
        if not data.get("ok"):
            log(f"Channel API Error: {data}")
            return False

        log("Signal sent to channel successfully")
        return True

    except Exception as e:
        log(f"Channel send error: {e}")
        return False

# ================= SYMBOL HELPERS =================
def normalize_symbol_for_ccxt(symbol):
    try:
        if not symbol:
            return symbol

        if "/" in symbol:
            return symbol

        if symbol.endswith("USDT"):
            base = symbol[:-4]
            return f"{base}/USDT"

        return symbol
    except Exception:
        return symbol

def normalize_symbol_for_rest(symbol):
    try:
        if not symbol:
            return symbol
        return symbol.replace("/", "")
    except Exception:
        return symbol

# ================= MARKET PRICE HELPERS =================
def get_live_price(symbol):
    try:
        rest_symbol = normalize_symbol_for_rest(symbol)

        url = f"https://api.binance.com/api/v3/ticker/price?symbol={rest_symbol}"
        r = session_requests.get(url, timeout=10)
        data = r.json()
        if "price" in data:
            return float(data["price"])

        url_us = f"https://api.binance.us/api/v3/ticker/price?symbol={rest_symbol}"
        r2 = session_requests.get(url_us, timeout=10)
        data2 = r2.json()
        if "price" in data2:
            return float(data2["price"])

        return None
    except Exception as e:
        log(f"get_live_price error for {symbol}: {e}")
        return None

def signal_is_fresh(signal):
    try:
        pair = signal.get("pair")
        entry = float(signal.get("entry", 0))
        if not pair or entry <= 0:
            return False

        current_price = get_live_price(pair)
        if current_price is None or current_price <= 0:
            return False

        deviation = abs(current_price - entry) / entry * 100

        if deviation > MAX_ENTRY_DEVIATION_PERCENT:
            log(f"Signal rejected (stale price): {pair} | entry={entry} current={current_price} deviation={round(deviation,4)}%")
            return False

        return True
    except Exception as e:
        log(f"signal_is_fresh error: {e}")
        return False

def attach_signal_timestamp(signal):
    try:
        signal["generated_at"] = datetime.now().isoformat()
        return signal
    except Exception:
        return signal

def signal_not_expired(signal):
    try:
        generated_at = signal.get("generated_at")
        if not generated_at:
            return True

        ts = datetime.fromisoformat(generated_at)
        age = (datetime.now() - ts).total_seconds()
        return age <= SIGNAL_FRESHNESS_SECONDS
    except Exception:
        return True

# ================= ELITE FILTER =================
def elite_trade_filter(signal):
    try:
        confidence = float(signal.get("confidence", 0))
        score = abs(float(signal.get("score", 0)))
        trend_power = signal.get("trend_power")
        volume = signal.get("volume")
        structure = signal.get("structure")
        timeframe = signal.get("timeframe")

        if confidence >= 90 and score >= 6:
            return True

        if (
            confidence >= 85
            and score >= 5
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            and volume == "STRONG"
            and structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW", "MID_RANGE"]
            and timeframe in ["15m", "1h", "5m"]
        ):
            return True

        if (
            confidence >= 82
            and score >= 5
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
        ):
            return True

        return False
    except Exception:
        return False

# ================= INIT TABLES =================
def init_trade_tables():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS trades_log (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            pair TEXT,
            direction TEXT,
            trade_type TEXT,
            entry REAL,
            tp REAL,
            sl REAL,
            amount REAL,
            exchange_order_id TEXT,
            status TEXT DEFAULT 'OPEN',
            pnl REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS bot_logs (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            level TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()

    log("Trade tables initialized")

def write_log(chat_id, level, message):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
            INSERT INTO bot_logs (chat_id, level, message)
            VALUES (%s, %s, %s)
            """, (str(chat_id), str(level), str(message)))
            conn.commit()
    except Exception as e:
        log(f"DB log insert failed: {e}")

# ================= USERS =================
def get_users():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
            SELECT chat_id, is_paid, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active
            FROM users
            WHERE chat_id IS NOT NULL
            AND chat_id <> ''
        """)

        users = c.fetchall()
        return users

# ================= VALIDATION =================
def valid_signal(signal):
    try:
        return (
            signal
            and signal.get("pair")
            and signal.get("direction") in ["LONG", "SHORT"]
            and signal.get("entry") is not None
            and signal.get("tp") is not None
            and signal.get("sl") is not None
            and float(signal.get("confidence", 0)) >= MIN_CONFIDENCE
        )
    except Exception:
        return False

def logical_signal(signal):
    try:
        entry = float(signal["entry"])
        tp = float(signal["tp"])
        sl = float(signal["sl"])
        direction = signal["direction"]

        if direction == "LONG":
            return tp > entry and sl < entry
        elif direction == "SHORT":
            return tp < entry and sl > entry
        return False
    except Exception:
        return False

# ================= FORMAT =================
def format_signal(signal):
    return f"""🔥 {signal['pair']}

📊 Type: {signal.get('type', 'FUTURES')}
📈 Direction: {signal['direction']}

💰 Entry: {signal['entry']}
🎯 TP: {signal['tp']}
🛑 SL: {signal['sl']}

🎯 Signal Strength: {signal['confidence']}%
⏱ Timeframe: {signal.get('timeframe', 'N/A')}
📉 Trend: {signal.get('trend', 'N/A')}
📦 Volume: {signal.get('volume', 'N/A')}
🧠 SMC: {signal.get('smc', 'N/A')}

⚠️ Risk-managed signal. Wait for proper entry.
"""

# ================= ACCESS HELPERS =================
def is_trial_allowed(trades):
    return (trades or 0) < 2

def is_paid_plan_active(plan, expiry, is_paid):
    try:
        if int(is_paid) != 1:
            return False

        if str(expiry).strip().lower() == "lifetime":
            return True

        if not expiry:
            return False

        expiry_date = datetime.strptime(str(expiry).strip(), "%Y-%m-%d").date()
        today = datetime.utcnow().date()

        return expiry_date >= today

    except Exception as e:
        log(f"is_paid_plan_active error: {e}")
        return False

# ================= PLAN FILTER =================
def signal_allowed_for_plan(plan, signal):
    try:
        confidence = float(signal.get("confidence", 0))
        score = abs(float(signal.get("score", 0)))
        timeframe = signal.get("timeframe", "5m")
        volume = signal.get("volume", "WEAK")
        trend_power = signal.get("trend_power", "MIXED")

        if plan == "trial":
            return (
                confidence >= 68
                and score >= 5
                and timeframe in ["5m", "15m"]
            )

        if plan == "basic":
            return (
                confidence >= 72
                and score >= 5
                and volume == "STRONG"
            )

        if plan == "pro":
            return (
                confidence >= 76
                and score >= 6
                and volume == "STRONG"
                and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            )

        if plan == "vip":
            return (
                confidence >= 78
                and score >= 6
            )

        return False
    except Exception:
        return False

# ================= EXCHANGE =================
def get_exchange(api_key, api_secret, trade_type):
    default_type = "future" if trade_type == "futures" else "spot"

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {
            "defaultType": default_type,
            "adjustForTimeDifference": True
        }
    })

    return exchange

# ================= SAFETY HELPERS =================
def today_bounds():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day, 0, 0, 0)
    end = start + timedelta(days=1)
    return start, end

def get_daily_trade_count(chat_id):
    with get_db() as conn:
        c = conn.cursor()

        start, end = today_bounds()
        c.execute("""
        SELECT COUNT(*) FROM trades_log
        WHERE chat_id = %s
        AND created_at >= %s
        AND created_at < %s
        """, (str(chat_id), start, end))

        return c.fetchone()[0]

def get_open_trade_count(chat_id):
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
        SELECT COUNT(*) FROM trades_log
        WHERE chat_id = %s
        AND status = 'OPEN'
        """, (str(chat_id),))

        return c.fetchone()[0]

def get_consecutive_losses(chat_id):
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
        SELECT pnl FROM trades_log
        WHERE chat_id = %s
        AND status = 'CLOSED'
        ORDER BY created_at DESC
        LIMIT 10
        """, (str(chat_id),))

        rows = c.fetchall()

    losses = 0
    for row in rows:
        pnl = row[0] or 0
        if pnl < 0:
            losses += 1
        else:
            break

    return losses

def get_daily_loss(chat_id):
    with get_db() as conn:
        c = conn.cursor()

        start, end = today_bounds()
        c.execute("""
        SELECT COALESCE(SUM(pnl), 0) FROM trades_log
        WHERE chat_id = %s
        AND status = 'CLOSED'
        AND created_at >= %s
        AND created_at < %s
        """, (str(chat_id), start, end))

        return c.fetchone()[0] or 0

def has_open_trade(chat_id, pair=None):
    with get_db() as conn:
        c = conn.cursor()

        if pair:
            c.execute("""
            SELECT id FROM trades_log
            WHERE chat_id = %s AND pair = %s AND status = 'OPEN'
            LIMIT 1
            """, (str(chat_id), pair))
        else:
            c.execute("""
            SELECT id FROM trades_log
            WHERE chat_id = %s AND status = 'OPEN'
            LIMIT 1
            """, (str(chat_id),))

        row = c.fetchone()
        return row is not None

def pair_in_cooldown(chat_id, pair):
    with get_db() as conn:
        c = conn.cursor()

        cooldown_time = datetime.now() - timedelta(minutes=PAIR_COOLDOWN_MINUTES)

        c.execute("""
        SELECT id FROM trades_log
        WHERE chat_id = %s AND pair = %s AND created_at >= %s
        ORDER BY created_at DESC
        LIMIT 1
        """, (str(chat_id), pair, cooldown_time))

        row = c.fetchone()
        return row is not None

def can_trade_user(chat_id, trade_amount):
    if get_daily_trade_count(chat_id) >= MAX_DAILY_TRADES:
        return False, "🚫 تم الوصول للحد الأقصى للصفقات اليوم"

    if get_open_trade_count(chat_id) >= MAX_OPEN_TRADES_PER_USER:
        return False, "🚫 لديك الحد الأقصى من الصفقات المفتوحة"

    if get_consecutive_losses(chat_id) >= MAX_CONSECUTIVE_LOSSES:
        return False, "🚫 تم إيقاف التداول بسبب خسائر متتالية"

    daily_loss = get_daily_loss(chat_id)
    max_loss_allowed = (float(trade_amount or 10)) * (MAX_DAILY_LOSS_PERCENT / 100)

    if daily_loss <= -abs(max_loss_allowed):
        return False, "🚫 تم إيقاف التداول بسبب الوصول لحد الخسارة اليومية"

    return True, "OK"

# ================= ORDER HELPERS =================
def validate_symbol_amount(exchange, symbol, amount):
    try:
        market = exchange.market(symbol)
        min_amount = market.get("limits", {}).get("amount", {}).get("min", 0)

        if min_amount and amount < min_amount:
            return False, f"Amount too small. min={min_amount}"

        return True, "OK"
    except Exception as e:
        return False, str(e)

def calculate_amount(usdt_balance, risk_percent, entry_price):
    capital = usdt_balance * risk_percent
    if entry_price <= 0:
        return 0
    amount = capital / entry_price
    return round(amount, 6)

def place_protection_orders(exchange, symbol, side, amount, tp_price, sl_price, trade_type, direction):
    try:
        opposite_side = "sell" if side == "buy" else "buy"

        if trade_type == "futures":
            try:
                exchange.create_order(
                    symbol=symbol,
                    type="TAKE_PROFIT_MARKET",
                    side=opposite_side,
                    amount=amount,
                    params={
                        "stopPrice": tp_price,
                        "reduceOnly": True,
                        "positionSide": "LONG" if direction == "LONG" else "SHORT",
                        "workingType": "MARK_PRICE"
                    }
                )
            except Exception as e:
                log(f"TP order warning for {symbol}: {e}")

            try:
                exchange.create_order(
                    symbol=symbol,
                    type="STOP_MARKET",
                    side=opposite_side,
                    amount=amount,
                    params={
                        "stopPrice": sl_price,
                        "reduceOnly": True,
                        "positionSide": "LONG" if direction == "LONG" else "SHORT",
                        "workingType": "MARK_PRICE"
                    }
                )
            except Exception as e:
                log(f"SL order warning for {symbol}: {e}")

        return True, "TP/SL placed"

    except Exception as e:
        return False, f"Protection order error: {e}"

# ================= TRADE EXECUTION =================
def execute_trade(api_key, api_secret, signal, trade_type, risk_percent, chat_id):
    """
    أهم نقطة في المشروع كله
    - تنفيذ آمن
    - بدون over-entry
    - بدون كميات غلط
    - بدون أوامر حماية مضروبة
    """
    conn = None
    try:
        api_key = decrypt_text(api_key)
        api_secret = decrypt_text(api_secret)

        if not api_key or not api_secret:
            return None, "API KEY / SECRET invalid after decrypt"

        exchange = get_exchange(api_key, api_secret, trade_type)
        exchange.load_markets()

        raw_symbol = signal["pair"]
        symbol = normalize_symbol_for_ccxt(raw_symbol)

        entry = float(signal["entry"])
        tp = float(signal["tp"])
        sl = float(signal["sl"])
        side = "buy" if signal["direction"] == "LONG" else "sell"

        # ================= LIVE PRICE SAFETY =================
        live_price = get_live_price(raw_symbol)
        if live_price is None:
            return None, "فشل سحب السعر الحالي"

        deviation = abs(live_price - entry) / entry * 100
        if deviation > MAX_ENTRY_DEVIATION_PERCENT:
            return None, f"تم رفض الصفقة: السعر تحرك ({round(deviation,4)}%)"

        leverage = 10

        if trade_type == "futures":
            try:
                exchange.set_position_mode(True)
                log(f"Hedge mode enabled for {chat_id}")
            except Exception as e:
                log(f"Hedge mode warning: {e}")

            try:
                exchange.set_leverage(leverage, symbol)
                log(f"Leverage set to {leverage}x for {symbol}")
            except Exception as e:
                log(f"Leverage warning: {e}")

        # ================= BALANCE =================
        balance = exchange.fetch_balance()
        usdt_balance = (
            balance.get("USDT", {}).get("free")
            or balance.get("free", {}).get("USDT")
            or 0
        )
        usdt_balance = float(usdt_balance or 0)

        if usdt_balance < 10:
            return None, "رصيد USDT أقل من الحد الأدنى"

        capital_to_use = min(float(risk_percent or 10), usdt_balance * 0.25)

        if capital_to_use < 5:
            return None, "قيمة الصفقة أقل من الحد الأدنى"

        if capital_to_use > usdt_balance:
            return None, f"الرصيد غير كافي. المطلوب {capital_to_use} والمتاح {usdt_balance}"

        # ================= NOTIONAL =================
        if trade_type == "futures":
            position_notional = capital_to_use * leverage
        else:
            position_notional = capital_to_use

        amount = position_notional / live_price
        market = exchange.market(symbol)

        min_amount = market.get("limits", {}).get("amount", {}).get("min", 0)
        amount_precision = market.get("precision", {}).get("amount", None)

        if amount_precision is not None:
            amount = float(exchange.amount_to_precision(symbol, amount))

        if min_amount and amount < min_amount:
            return None, f"الكمية أقل من الحد الأدنى للزوج: min={min_amount}"

        if amount <= 0:
            return None, "كمية الصفقة غير صالحة"

        valid_amount, amount_msg = validate_symbol_amount(exchange, symbol, amount)
        if not valid_amount:
            return None, f"فشل التحقق من الكمية: {amount_msg}"

        log(
            f"TRADE DEBUG | {chat_id} | {symbol} | "
            f"balance={usdt_balance} | capital={capital_to_use} | "
            f"amount={amount} | side={side} | trade_type={trade_type}"
        )

        params = {}

        if trade_type == "futures":
            params = {
                "positionSide": "LONG" if signal["direction"] == "LONG" else "SHORT"
            }

        conn = db()
        c = conn.cursor()

        # ================= DUPLICATE TRADE PROTECTION =================
        if is_duplicate_open_trade(
            conn,
            username=chat_id,
            pair=raw_symbol,
            timeframe=signal.get("timeframe", ""),
            direction=signal["direction"]
        ):
            log(f"Duplicate trade blocked: {raw_symbol} {signal['direction']} {signal.get('timeframe')}")
            try:
                conn.close()
            except Exception:
                pass
            return None, "Duplicate trade blocked"

        # ================= MAIN ORDER =================
        order = exchange.create_market_order(symbol, side, amount, params=params)

        if not order or not order.get("id"):
            try:
                conn.close()
            except Exception:
                pass
            return None, "فشل تنفيذ أمر السوق"

        # ================= REAL FILLED ENTRY =================
        real_entry = entry
        try:
            if order.get("average"):
                real_entry = float(order.get("average"))
            elif order.get("price"):
                real_entry = float(order.get("price"))
        except Exception:
            real_entry = entry

        # ================= PROTECTION =================
        protection_ok, protection_msg = place_protection_orders(
            exchange, symbol, side, amount, tp, sl, trade_type, signal["direction"]
        )

        c.execute("""
        INSERT INTO trades_log (
            chat_id, pair, direction, trade_type, entry, tp, sl, amount,
            exchange_order_id, status, pnl
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(chat_id),
            raw_symbol,
            signal["direction"],
            trade_type,
            real_entry,
            tp,
            sl,
            amount,
            str(order.get("id")),
            "OPEN",
            0
        ))
        conn.commit()
        conn.close()

        return order, protection_msg

    except ccxt.InsufficientFunds as e:
        log(f"execute_trade insufficient funds: {e}")
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return None, "رصيد غير كافي لتنفيذ الصفقة"

    except ccxt.InvalidOrder as e:
        log(f"execute_trade invalid order: {e}")
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return None, f"أمر غير صالح: {e}"

    except ccxt.AuthenticationError as e:
        log(f"execute_trade auth error: {e}")
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return None, "API Key / Secret غير صالحين أو لا يوجد صلاحيات"

    except Exception as e:
        log(f"execute_trade full error: {e}")
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return None, f"Trade Error: {e}"

# ================= TRADE MONITOR =================
def update_closed_trades():
    try:
        with get_db() as conn:
            c = conn.cursor()

            c.execute("""
            SELECT id, chat_id, pair, direction, entry, tp, sl, amount
            FROM trades_log
            WHERE status = 'OPEN'
            """)
            open_trades = c.fetchall()

            for trade in open_trades:
                trade_id, chat_id, pair, direction, entry, tp, sl, amount = trade

                try:
                    current_price = get_live_price(pair)

                    if current_price is None:
                        write_log(chat_id, "ERROR", f"Price fetch failed for {pair}")
                        continue

                    pnl = 0
                    should_close = False
                    close_reason = None

                    if direction == "LONG":
                        if current_price >= tp:
                            pnl = (tp - entry) * amount
                            should_close = True
                            close_reason = "TP HIT 🎯"
                        elif current_price <= sl:
                            pnl = (sl - entry) * amount
                            should_close = True
                            close_reason = "SL HIT 🛑"

                    elif direction == "SHORT":
                        if current_price <= tp:
                            pnl = (entry - tp) * amount
                            should_close = True
                            close_reason = "TP HIT 🎯"
                        elif current_price >= sl:
                            pnl = (entry - sl) * amount
                            should_close = True
                            close_reason = "SL HIT 🛑"

                    if should_close:
                        c.execute("""
                        UPDATE trades_log
                        SET status = 'CLOSED', pnl = %s, closed_at = NOW()
                        WHERE id = %s
                        """, (round(pnl, 4), trade_id))

                        c.execute("""
                        UPDATE users
                        SET profit = COALESCE(profit, 0) + %s
                        WHERE chat_id = %s
                        """, (round(pnl, 4), str(chat_id)))

                        conn.commit()
                        write_log(chat_id, "INFO", f"Trade closed {pair} pnl={round(pnl,4)} reason={close_reason}")

                        result_emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "➖"

                        send(chat_id, f"""📌 تم إغلاق الصفقة

🔥 {pair}
📊 Direction: {direction}
📍 Result: {close_reason}
{result_emoji} PNL: {round(pnl, 4)} USDT
""")

                except Exception as e:
                    write_log(chat_id, "ERROR", f"Trade monitor error for {pair}: {e}")

    except Exception as e:
        log(f"update_closed_trades error: {e}")

# ================= RISK =================
def adjust_risk(profit):
    if profit and profit > 100:
        return 0.015
    elif profit and profit < -50:
        return 0.005
    return 0.01

def increment_trade(chat_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE users
                SET trades = COALESCE(trades, 0) + 1
                WHERE chat_id = %s
            """, (str(chat_id),))
            conn.commit()
    except Exception as e:
        log(f"increment_trade error: {e}")

# ================= DUPLICATE CHECK =================
def is_duplicate_signal(signal):
    try:
        now = datetime.now()

        if (
            LAST_SIGNAL_CACHE["pair"] == signal.get("pair")
            and LAST_SIGNAL_CACHE["direction"] == signal.get("direction")
            and LAST_SIGNAL_CACHE["entry"] == signal.get("entry")
            and LAST_SIGNAL_CACHE["time"] is not None
            and (now - LAST_SIGNAL_CACHE["time"]).total_seconds() < DUPLICATE_WINDOW_SECONDS
        ):
            return True

        LAST_SIGNAL_CACHE["pair"] = signal.get("pair")
        LAST_SIGNAL_CACHE["direction"] = signal.get("direction")
        LAST_SIGNAL_CACHE["entry"] = signal.get("entry")
        LAST_SIGNAL_CACHE["time"] = now

        return False
    except Exception:
        return False

def is_recent_memory_duplicate(signal):
    try:
        pair = signal.get("pair")
        direction = signal.get("direction")
        entry = float(signal.get("entry", 0))
        timeframe = signal.get("timeframe", "5m")

        if not pair or not direction or entry <= 0:
            return False

        key = f"{pair}_{direction}"
        now = datetime.now()

        cooldown_seconds = 3600
        if timeframe == "15m":
            cooldown_seconds = 7200
        elif timeframe == "1h":
            cooldown_seconds = 14400

        if key in RECENT_SIGNAL_MEMORY:
            old_entry, old_time = RECENT_SIGNAL_MEMORY[key]
            age = (now - old_time).total_seconds()

            if age < cooldown_seconds:
                diff = abs(entry - old_entry) / old_entry * 100
                if diff < 0.8:
                    return True

        RECENT_SIGNAL_MEMORY[key] = (entry, now)
        return False
    except Exception:
        return False

# ================= SIGNAL FETCHER =================
def get_monster_signals():
    """
    المجاني: أفضل صفقتين
    المدفوع: fallback لو السوق ميت
    """
    try:
        signals = get_top_free_signals(limit=FREE_SIGNALS_LIMIT)
        log(f"RAW SIGNALS => {signals}")

        if not signals:
            log("No signals from analyzer — using fallback")
            fallback_candidates = []

            try:
                from market_analyzer import SYMBOLS, TIMEFRAMES

                for symbol in SYMBOLS:
                    for tf in TIMEFRAMES:
                        try:
                            s = generate_signal(symbol, tf)
                            if s:
                                if "ranking_score" not in s:
                                    s["ranking_score"] = (
                                        float(s.get("confidence", 0))
                                        + abs(float(s.get("score", 0)) * 2)
                                        + (6 if s.get("volume") == "STRONG" else 0)
                                        + (6 if s.get("trend_power") in ["STRONG_BULL", "STRONG_BEAR"] else 0)
                                        + (5 if s.get("timeframe") == "15m" else 0)
                                        + (4 if s.get("structure") in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW"] else 0)
                                        + (3 if s.get("smc") in ["LIQUIDITY_BREAK_UP", "LIQUIDITY_BREAK_DOWN"] else 0)
                                    )
                                fallback_candidates.append(s)
                        except Exception:
                            continue

                fallback_candidates = sorted(
                    fallback_candidates,
                    key=lambda x: (
                        float(x.get("confidence", 0)),
                        float(x.get("ranking_score", 0)),
                        abs(float(x.get("score", 0)))
                    ),
                    reverse=True
                )

                if fallback_candidates:
                    signals = fallback_candidates[:3]
                    log(f"Fallback signals used: {signals}")

            except Exception as e:
                log(f"Fallback paid signal error: {e}")

        final_signals = []

        market_mode = "dead"
        try:
            strong_count = 0
            for x in signals or []:
                conf = float(x.get("confidence", 0))
                score = float(x.get("score", 0))
                rank = float(x.get("ranking_score", 0))
                volume = str(x.get("volume", "")).upper()

                if conf >= 82 and score >= 6 and rank >= 90 and volume in ["STRONG", "MEDIUM"]:
                    strong_count += 1

            if strong_count >= 3:
                market_mode = "strong"
            elif strong_count >= 1:
                market_mode = "normal"
            else:
                market_mode = "dead"

            log(f"Market mode => {market_mode} | strong_candidates={strong_count}")

        except Exception as e:
            log(f"Market mode detection error: {e}")
            market_mode = "normal"

        if market_mode == "strong":
            min_conf = 82
            min_score = 6.5
            min_rank = 95
            min_rr = 1.8
        elif market_mode == "normal":
            min_conf = 79
            min_score = 5.8
            min_rank = 88
            min_rr = 1.5
        else:
            min_conf = 72
            min_score = 4.8
            min_rank = 78
            min_rr = 1.25

        log(
            f"Filter mode => conf>={min_conf}, score>={min_score}, "
            f"rank>={min_rank}, rr>={min_rr}"
        )

        for s in signals or []:
            s = attach_signal_timestamp(s)

            ai_result = predict_trade(s)

            if not ai_result.get("approved"):
                log(f"❌ AI rejected signal: {s.get('pair')}")
                continue

# تحديث البيانات
            s["confidence"] = ai_result.get("confidence", s.get("confidence"))
            s["ranking_score"] = ai_result.get("ranking_score", s.get("ranking_score"))
            s["ai_score"] = ai_result.get("score", 0)

            if not valid_signal(s):
                log(f"Invalid signal skipped: {s}")
                continue

            if not logical_signal(s):
                log(
                    f"Logical invalid signal skipped: {s.get('pair')} | "
                    f"dir={s.get('direction')} | "
                    f"entry={s.get('entry')} | "
                    f"tp={s.get('tp')} | "
                    f"sl={s.get('sl')}"
                )
                continue

            if not signal_not_expired(s):
                log(
                    f"Expired signal skipped: {s.get('pair')} | "
                    f"tf={s.get('timeframe')}"
                )
                continue

            if not signal_is_fresh(s):
                log(
                    f"Freshness check failed: {s.get('pair')} | "
                    f"tf={s.get('timeframe')} | "
                    f"confidence={s.get('confidence')} | "
                    f"score={s.get('score')} | "
                    f"rank={s.get('ranking_score')}"
                )
                continue

            if is_duplicate_signal(s):
                log(f"Duplicate signal skipped: {s.get('pair')}")
                continue

            if is_recent_memory_duplicate(s):
                log(f"Recent memory duplicate skipped: {s.get('pair')}")
                continue

            try:
                pair = s.get("pair")
                direction = str(s.get("direction", "")).upper()
                entry = float(s.get("entry", 0))
                tp = float(s.get("tp", 0))
                sl = float(s.get("sl", 0))
                confidence = float(s.get("confidence", 0))
                score = abs(float(s.get("score", 0)))
                ranking_score = float(s.get("ranking_score", 0) or 0)
                volume = str(s.get("volume", "")).upper()
                trend = str(s.get("trend", "")).upper()
                trend_power = str(s.get("trend_power", "")).upper()
                structure = str(s.get("structure", "")).upper()
                smc = str(s.get("smc", "")).upper()
                timeframe = str(s.get("timeframe", "")).lower()

                if not pair or not entry or not tp or not sl:
                    log(f"Premium rejected {pair} => missing_data")
                    continue

                if direction not in ["LONG", "SHORT"]:
                    log(f"Premium rejected {pair} => bad_direction")
                    continue

                if confidence < min_conf:
                    log(f"Premium rejected {pair} => low_confidence | tf={timeframe} | conf={confidence} | needed={min_conf}")
                    continue

                if score < min_score:
                    log(f"Premium rejected {pair} => low_score | tf={timeframe} | score={score} | needed={min_score}")
                    continue

                if ranking_score < min_rank:
                    log(f"Premium rejected {pair} => low_ranking | tf={timeframe} | rank={ranking_score} | needed={min_rank}")
                    continue

                if volume not in ["STRONG", "MEDIUM", "WEAK"]:
                    log(f"Premium rejected {pair} => weak_volume | tf={timeframe} | volume={volume}")
                    continue

                if trend not in ["UP", "DOWN"]:
                    log(f"Premium rejected {pair} => bad_trend | tf={timeframe} | trend={trend}")
                    continue

                allowed_structures = [
                    "NEAR_BREAKOUT_HIGH",
                    "NEAR_BREAKOUT_LOW",
                    "BREAKOUT",
                    "PULLBACK",
                    "CONTINUATION",
                    "MID_RANGE",
                    "UNKNOWN"
                ]
                if structure and structure not in allowed_structures:
                    log(f"Premium rejected {pair} => bad_structure:{structure} | tf={timeframe}")
                    continue

                allowed_smc = [
                    "LIQUIDITY_BREAK_UP",
                    "LIQUIDITY_BREAK_DOWN",
                    "BOS",
                    "CHOCH",
                    "ORDER_BLOCK",
                    "FVG",
                    "RANGE"
                ]
                if smc and smc not in allowed_smc:
                    log(f"Premium rejected {pair} => bad_smc:{smc} | tf={timeframe}")
                    continue

                if direction == "LONG":
                    risk = entry - sl
                    reward = tp - entry
                else:
                    risk = sl - entry
                    reward = entry - tp

                if risk <= 0 or reward <= 0:
                    log(f"Premium rejected {pair} => bad_rr | tf={timeframe} | entry={entry} | tp={tp} | sl={sl}")
                    continue

                rr = reward / risk
                if rr < min_rr:
                    log(f"Premium rejected {pair} => low_rr:{round(rr, 2)} | tf={timeframe} | needed={min_rr}")
                    continue

                if market_mode == "strong":
                    if timeframe == "5m" and confidence < 83:
                        log(f"Premium rejected {pair} => strong_market_5m_too_weak")
                        continue
                elif market_mode == "normal":
                    if timeframe == "5m" and confidence < 79:
                        log(f"Premium rejected {pair} => normal_market_5m_too_weak")
                        continue
                else:
                    if timeframe == "5m" and confidence < 72:
                        log(f"Premium rejected {pair} => dead_market_5m_too_weak")
                        continue

            except Exception as premium_e:
                log(f"Premium filter error for {s.get('pair')}: {premium_e}")
                continue

            if ULTRA_MODE:
                try:
                    if market_mode == "strong":
                        if float(s.get("confidence", 0)) < 80:
                            log(f"Ultra mode rejected: {s.get('pair')} conf={s.get('confidence')}")
                            continue
                    elif market_mode == "normal":
                        if float(s.get("confidence", 0)) < 76:
                            log(f"Ultra mode rejected: {s.get('pair')} conf={s.get('confidence')}")
                            continue
                    else:
                        if float(s.get("confidence", 0)) < 70:
                            log(f"Ultra mode rejected: {s.get('pair')} conf={s.get('confidence')}")
                            continue
                except Exception:
                    continue

            log(
                f"Signal approved => {s.get('pair')} | "
                f"tf={s.get('timeframe')} | "
                f"dir={s.get('direction')} | "
                f"conf={s.get('confidence')} | "
                f"score={s.get('score')} | "
                f"rank={s.get('ranking_score')} | "
                f"volume={s.get('volume')} | "
                f"trend={s.get('trend')} | "
                f"market_mode={market_mode}"
            )

            final_signals.append(s)

        final_signals = sorted(
            final_signals,
            key=lambda x: (
                float(x.get("confidence", 0)),
                float(x.get("ranking_score", 0)),
                abs(float(x.get("score", 0)))
            ),
            reverse=True
        )

        log(f"FINAL SIGNALS => {final_signals[:3]}")
        return final_signals[:3]

    except Exception as e:
        log(f"get_monster_signals error: {e}")
        return []

def should_notify_no_signal(chat_id):
    try:
        now = datetime.now()

        if chat_id not in LAST_NO_SIGNAL_NOTIFY:
            LAST_NO_SIGNAL_NOTIFY[chat_id] = now
            return True

        last_time = LAST_NO_SIGNAL_NOTIFY.get(chat_id)
        if not last_time:
            LAST_NO_SIGNAL_NOTIFY[chat_id] = now
            return True

        diff_minutes = (now - last_time).total_seconds() / 60

        if diff_minutes >= NO_SIGNAL_NOTIFY_COOLDOWN_MINUTES:
            LAST_NO_SIGNAL_NOTIFY[chat_id] = now
            return True

        return False
    except Exception as e:
        log(f"should_notify_no_signal error: {e}")
        return False

def notify_users_no_signal(users):
    try:
        for user in users:
            try:
                chat_id, is_paid, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active = user

                log(f"DEBUG USER => chat_id={chat_id}, is_paid={is_paid}, plan={plan}, expiry={expiry}, bot_active={bot_active}")

                if plan == "trial":
                    if not is_trial_allowed(trades):
                        continue
                else:
                    if not is_paid_plan_active(plan, expiry, is_paid):
                        continue

                if not should_notify_no_signal(chat_id):
                    continue

                msg = """⚠️ تنبيه مهم من البوت

نظرًا لسوء تقلبات الأسواق الحالية وعدم وجود فرصة واضحة وقوية بما يكفي الآن،
لن يتم إرسال صفقات في الوقت الحالي.

📌 الرجاء الانتظار حتى تظهر فرصة مناسبة
وذلك حفاظًا على سلامة أموالكم وتقليل احتمالية الخسارة.

🤖 البوت لن يرسل صفقة إلا إذا كانت مطابقة للشروط المطلوبة بأفضل شكل ممكن."""

                sent_ok = send(chat_id, msg)

                if sent_ok:
                    log(f"No-signal notice sent to {chat_id}")
                    write_log(chat_id, "INFO", "No-signal market warning sent")
                else:
                    log(f"Failed sending no-signal notice to {chat_id}")

            except Exception as inner_e:
                log(f"notify_users_no_signal inner error: {inner_e}")

    except Exception as e:
        log(f"notify_users_no_signal error: {e}")

# ================= MAIN =================
def run():
    log("AUTO_SENDER FILE STARTED")
    init_trade_tables()
    log("BOT STARTED - MONSTER MODE")
    log("Entering main bot loop...")

    while True:
        try:
            log("Loop tick...")

            # 1) راقب الصفقات المفتوحة
            update_closed_trades()
            log("Closed trades updated")

            # 2) هات الإشارات
            signals = get_monster_signals()
            log(f"Signals fetched: {signals}")

            # 3) هات المستخدمين
            users = get_users()
            log(f"Users loaded: {len(users)}")

            if not signals:
                log("No signals found")
                notify_users_no_signal(users)
                time.sleep(30)
                continue

            # إرسال القناة مرة واحدة فقط لكل إشارة في نفس الدورة
            sent_to_channel_pairs = set()

            for signal in signals[:MAX_SIGNALS_PER_CYCLE]:
                log(f"Processing signal: {signal}")

                signal_key = f"{signal.get('pair')}_{signal.get('direction')}_{signal.get('entry')}"

                # ===== إرسال للقناة العامة مرة واحدة فقط =====
                try:
                    if CHANNEL_ID and signal_key not in sent_to_channel_pairs:
                        send_channel(format_signal(signal))
                        sent_to_channel_pairs.add(signal_key)
                except Exception as ch_e:
                    log(f"Channel send skipped/error: {ch_e}")

                for user in users:
                    try:
                        chat_id, is_paid, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active = user

                        log(f"DEBUG USER => chat_id={chat_id}, is_paid={is_paid}, plan={plan}, expiry={expiry}, bot_active={bot_active}")

                        if not chat_id:
                            continue

                        # ===== صلاحية الاشتراك =====
                        if plan == "trial":
                            if not is_trial_allowed(trades):
                                continue
                        else:
                            if not is_paid_plan_active(plan, expiry, is_paid):
                                continue

                        # ===== فلترة حسب الباقة =====
                        if not signal_allowed_for_plan(plan, signal):
                            log(f"Signal filtered for plan {plan} -> {signal['pair']}")
                            continue

                        # ===== VIP elite filter =====
                        if plan == "vip":
                            if not elite_trade_filter(signal):
                                log(f"Elite filter rejected for VIP: {signal['pair']}")
                                continue

                        msg = format_signal(signal)
                        sent_ok = send(chat_id, msg)

                        if sent_ok:
                            log(f"Signal sent to {chat_id} -> {signal['pair']}")
                            write_log(chat_id, "INFO", f"Signal sent {signal['pair']} {signal['direction']} conf={signal['confidence']}")

                            if plan == "trial":
                                increment_trade(chat_id)
                        else:
                            log(f"Signal failed to send to {chat_id}")

                        # ================= AUTO TRADE FOR VIP =================
                        if (
                            str(plan).strip().lower() == "vip"
                            and (str(expiry).strip().lower() == "lifetime" or is_paid_plan_active(plan, expiry, is_paid))
                            and int(bot_active) == 1
                            and api_key
                            and api_secret
                        ):
                            try:
                                can_trade, reason = can_trade_user(chat_id, trade_amount)
                                if not can_trade:
                                    log(f"VIP trade blocked for {chat_id}: {reason}")
                                    continue

                                if has_open_trade(chat_id, signal["pair"]):
                                    log(f"VIP skipped: already open trade on {signal['pair']} for {chat_id}")
                                    continue

                                if pair_in_cooldown(chat_id, signal["pair"]):
                                    log(f"VIP skipped: cooldown active on {signal['pair']} for {chat_id}")
                                    continue

                                signal_trade_type = "futures" if signal.get("type") == "FUTURES" else "spot"

                                order, result_msg = execute_trade(
                                    api_key=api_key,
                                    api_secret=api_secret,
                                    signal=signal,
                                    trade_type=signal_trade_type,
                                    risk_percent=trade_amount,
                                    chat_id=chat_id
                                )

                                if order:
                                    log(f"Auto trade executed for {chat_id} -> {signal['pair']}")
                                    send(chat_id, f"""🤖 تم تنفيذ صفقة VIP تلقائيًا

🔥 {signal['pair']}
📈 الاتجاه: {signal['direction']}
💰 الدخول: {signal['entry']}
🎯 الهدف: {signal['tp']}
🛑 الوقف: {signal['sl']}
📦 النوع: {signal.get('type', 'FUTURES')}
🆔 Order ID: {order.get('id')}
""")
                                    write_log(chat_id, "INFO", f"AUTO TRADE EXECUTED {signal['pair']} ORDER={order.get('id')}")
                                else:
                                    log(f"Auto trade rejected for {chat_id}: {result_msg}")
                                    write_log(chat_id, "ERROR", f"Auto trade rejected: {result_msg}")

                            except Exception as e:
                                log(f"Auto trade failed for {chat_id}: {e}")
                                write_log(chat_id, "ERROR", f"AUTO TRADE FAILED: {e}")

                    except Exception as user_loop_error:
                        log(f"user loop error: {user_loop_error}")
                        continue

            time.sleep(GLOBAL_LOOP_SLEEP)

        except Exception as e:
            log(f"RUN LOOP ERROR: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run()