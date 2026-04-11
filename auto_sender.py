import time
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
from trade_tracker import add_trade, update_trades
from market_analyzer import get_price
import requests

# =========================================
# TELEGRAM SEND FUNCTION
# =========================================
def send_to_telegram(message, chat_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code != 200:
            print(f"Telegram send failed to {chat_id}: {response.text}")

    except Exception as e:
        print(f"Telegram error: {e}")


# =========================================
# TRADE RESULT NOTIFIER (TP / SL)
# =========================================
def notify_trade_result(trade):
    try:
        # 👇 مهم: استورد هنا عشان تتجنب circular import
        from app import get_users   # أو غيرها حسب مكان get_users عندك

        users = get_users()

        pair = trade["pair"]
        status = trade["status"]
        pnl = trade.get("pnl", 0)
        direction = trade["direction"]

        if status == "TP":
            msg = f"""
✅ <b>{pair}</b> TP HIT

📈 Direction: {direction}
💰 Profit: +{pnl}%
"""
        elif status == "SL":
            msg = f"""
❌ <b>{pair}</b> SL HIT

📉 Direction: {direction}
💰 Loss: {pnl}%
"""
        else:
            return

        # 👇 إرسال لكل المستخدمين
        for user in users:
            chat_id = user.get("chat_id")

            if not chat_id:
                continue

            try:
                send_to_telegram(msg, chat_id)
            except Exception as e:
                print(f"Send error to {chat_id}: {e}")

    except Exception as e:
        print(f"notify_trade_result error: {e}")

load_dotenv()

# ================= ENV =================
FERNET_KEY = os.environ.get("FERNET_KEY", "").strip()
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
BASE_URL = os.environ.get("BASE_URL", "").strip().rstrip("/")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "").strip()

if not FERNET_KEY:
    raise Exception("FERNET_KEY missing in environment variables")

cipher = Fernet(FERNET_KEY.encode())

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def log(msg):
    logging.info(msg)

# ================= REQUEST SESSION =================
session_requests = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504], allowed_methods=["GET","POST"])
adapter = HTTPAdapter(max_retries=retry)
session_requests.mount("http://", adapter)
session_requests.mount("https://", adapter)

# ================= CONFIG =================
MAX_DAILY_TRADES = 4
MAX_CONSECUTIVE_LOSSES = 2
MAX_DAILY_LOSS_PERCENT = 4
PAIR_COOLDOWN_MINUTES = 45
GLOBAL_LOOP_SLEEP = 80
MIN_CONFIDENCE = 66
DUPLICATE_WINDOW_SECONDS = 300
NO_SIGNAL_NOTIFY_COOLDOWN_MINUTES = 360

# 🔥 EXECUTION LOCK (حماية من تكرار الصفقات)
EXECUTION_LOCK = {}
EXECUTION_LOCK_EXPIRY = 120

MAX_ENTRY_DEVIATION_PERCENT = 0.25
SIGNAL_FRESHNESS_SECONDS = 180
MAX_OPEN_TRADES_PER_USER = 2
FREE_SIGNALS_LIMIT = 2

MAX_SIGNALS_PER_CYCLE = 2
ULTRA_MODE = True

# ================= MEMORY =================
LAST_SIGNAL_CACHE = {}
RECENT_SIGNAL_MEMORY = {}
LAST_NO_SIGNAL_NOTIFY = {}
# ================= SIGNAL CONTROL =================
USER_SIGNAL_MEMORY = {}
USER_SIGNAL_EXPIRY = 900  # 15 دقيقة

PAIR_COOLDOWN = {
    "5m": 300,
    "15m": 600,
    "1h": 1800
}


# ================= HELPERS =================
def build_signal_signature(signal):
    try:
        pair = signal.get("pair")
        direction = signal.get("direction")
        timeframe = signal.get("timeframe", "5m")
        entry = round(float(signal.get("entry", 0)), 2)

        return f"{pair}_{direction}_{timeframe}_{entry}"

    except Exception as e:
        log(f"signature error: {e}")
        return None


def is_signal_blocked(chat_id, signal):
    try:
        now = time.time()
        signature = build_signal_signature(signal)

        if not signature:
            return False

        timeframe = signal.get("timeframe", "5m")
        cooldown = PAIR_COOLDOWN.get(timeframe, 300)

        if chat_id not in USER_SIGNAL_MEMORY:
            USER_SIGNAL_MEMORY[chat_id] = {}

        user_memory = USER_SIGNAL_MEMORY[chat_id]

        # تنظيف القديم
        expired = []
        for sig, t in user_memory.items():
            if now - t > USER_SIGNAL_EXPIRY:
                expired.append(sig)

        for k in expired:
            del user_memory[k]

        # منع التكرار
        if signature in user_memory:
            if now - user_memory[signature] < cooldown:
                return True

        user_memory[signature] = now
        return False

    except Exception as e:
        log(f"signal block error: {e}")
        return False

def decrypt_text(value):
    try:
        return cipher.decrypt(value.encode()).decode() if value else None
    except Exception as e:
        log(f"decrypt error: {e}")
        return None

def normalize_symbol(symbol):
    return symbol.replace("/", "").upper()

def clean_execution_lock():
    try:
        now = datetime.now()

        for k in list(EXECUTION_LOCK.keys()):
            last_time = EXECUTION_LOCK.get(k)

            if not last_time:
                continue

            if (now - last_time).total_seconds() > EXECUTION_LOCK_EXPIRY:
                del EXECUTION_LOCK[k]

    except Exception as e:
        log(f"clean_execution_lock error: {e}")

LAST_SEND = {}

def can_send(chat_id):
    try:
        now = time.time()

        if chat_id in LAST_SEND:
            if now - LAST_SEND[chat_id] < 2:
                return False

        LAST_SEND[chat_id] = now
        return True

    except Exception as e:
        log(f"can_send error: {e}")
        return True
    
def get_live_price(symbol):
    try:
        r = session_requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={normalize_symbol(symbol)}", timeout=10)
        data = r.json()
        return float(data["price"]) if "price" in data else None
    except Exception as e:
        log(f"price error: {e}")
        return None

# ================= DB =================
def db():
    url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL")
    if not url:
        raise Exception("DATABASE_URL missing")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(url, sslmode="require")

@contextmanager
def get_db():
    conn = db()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except:
            pass

# ================= TELEGRAM =================
def send(chat_id, text):

    if not can_send(chat_id):
        log(f"🚫 Spam blocked for {chat_id}")
        return False

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

        payload = {
            "chat_id": str(chat_id),
            "text": text
        }

        for attempt in range(3):  # retry 3 مرات
            try:
                r = session_requests.post(url, json=payload, timeout=10)

                if r.status_code == 200:
                    return True

                # 🚨 لو تيليجرام عمل Rate Limit
                if r.status_code == 429:
                    wait_time = 2 + attempt
                    log(f"⚠️ Telegram rate limit... retry in {wait_time}s")
                    time.sleep(wait_time)
                    continue

                # أي error تاني
                log(f"❌ Telegram API error: {r.text}")
                return False

            except Exception as inner_e:
                log(f"Retry send error: {inner_e}")
                time.sleep(1)

        return False

    except Exception as e:
        log(f"telegram error: {e}")
        return False

def send_channel(text):
    if not CHANNEL_ID:
        return False
    return send(CHANNEL_ID, text)

# ================= VALIDATION =================
def valid_signal(s):
    try:
        return (
            s and
            s.get("pair") and
            s.get("direction") in ["LONG","SHORT"] and
            s.get("entry") and
            s.get("tp") and
            s.get("sl") and
            float(s.get("confidence",0)) >= MIN_CONFIDENCE
        )
    except:
        return False

def calculate_rr(entry,tp,sl,direction):
    try:
        entry,tp,sl = float(entry),float(tp),float(sl)
        if direction=="LONG":
            return (tp-entry)/(entry-sl)
        return (entry-tp)/(sl-entry)
    except:
        return 0

# ================= ADVANCED FILTER =================
def elite_filter(signal):
    try:
        conf = float(signal.get("confidence",0))
        score = abs(float(signal.get("score",0)))

        if conf >= 90:
            return True
        if conf >= 85 and score >= 5:
            return True
        if conf >= 80 and score >= 6:
            return True

        return False
    except:
        return False

# ================= DUPLICATE =================
def is_duplicate_signal(signal):
    key = f"{signal['pair']}_{signal['direction']}_{signal['entry']}"
    now = datetime.now()

    if key in LAST_SIGNAL_CACHE:
        if (now - LAST_SIGNAL_CACHE[key]).total_seconds() < DUPLICATE_WINDOW_SECONDS:
            return True

    LAST_SIGNAL_CACHE[key] = now
    return False

# ================= SIGNAL ENGINE =================
# ================= SIGNAL ENGINE =================
def get_monster_signals():
    try:
        signals = get_top_free_signals(limit=FREE_SIGNALS_LIMIT)
        final = []

        for s in signals or []:
            try:
                # ================= ADD TIMESTAMP =================
                if "timestamp" not in s:
                    s["timestamp"] = datetime.utcnow()

                ai = predict_trade(s)
                if not ai.get("approved"):
                    continue

                s["confidence"] = ai.get("confidence", s.get("confidence"))

                if not valid_signal(s):
                    continue

                rr = calculate_rr(s["entry"], s["tp"], s["sl"], s["direction"])
                if rr < 1.2:
                    continue

                if is_duplicate_signal(s):
                    continue

                final.append(s)

            except Exception as e:
                log(f"signal filter error: {e}")

        final = sorted(final, key=lambda x: float(x.get("confidence", 0)), reverse=True)
        return final[:MAX_SIGNALS_PER_CYCLE]

    except Exception as e:
        log(f"signal engine error: {e}")
        return []
    # ================= PLAN ACCESS =================
def is_trial_allowed(trades):
    try:
        return int(trades or 0) < 2
    except:
        return False

def is_paid_plan_active(plan, expiry, is_paid):
    try:
        if int(is_paid or 0) != 1:
            return False

        if str(expiry or "").strip().lower() == "lifetime":
            return True

        if not expiry:
            return False

        expiry_date = datetime.strptime(str(expiry).strip(), "%Y-%m-%d").date()
        return datetime.utcnow().date() <= expiry_date
    except Exception as e:
        log(f"is_paid_plan_active error: {e}")
        return False

def signal_allowed_for_plan(plan, signal):
    try:
        confidence = float(signal.get("confidence", 0))
        score = abs(float(signal.get("score", 0)))
        timeframe = str(signal.get("timeframe", "5m")).lower()

        if plan == "trial":
            return confidence >= 68 and timeframe in ["5m", "15m"]

        if plan == "basic":
            return confidence >= 72 and score >= 4

        if plan == "pro":
            return confidence >= 76 and score >= 5

        if plan == "vip":
            return confidence >= 78 and score >= 5

        return False
    except Exception as e:
        log(f"signal_allowed_for_plan error: {e}")
        return False

# ================= USERS =================
def get_users():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT chat_id, is_paid, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active
                FROM users
                WHERE chat_id IS NOT NULL
                AND chat_id <> ''
            """)
            return c.fetchall()
    except Exception as e:
        log(f"get_users error: {e}")
        return []

# ================= LOGS =================
def write_log(chat_id, level, message):
    try:
        with get_db() as conn:
            c = conn.cursor()

            c.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id SERIAL PRIMARY KEY,
                chat_id TEXT,
                level TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            c.execute("""
            INSERT INTO bot_logs (chat_id, level, message)
            VALUES (%s, %s, %s)
            """, (str(chat_id), str(level), str(message)))

            conn.commit()
    except Exception as e:
        log(f"write_log error: {e}")

# ================= TRADE TABLE INIT =================
def init_trade_tables():
    try:
        with get_db() as conn:
            c = conn.cursor()

            c.execute("""
            CREATE TABLE IF NOT EXISTS trades_log (
                id SERIAL PRIMARY KEY,
                chat_id TEXT,
                pair TEXT,
                direction TEXT,
                trade_type TEXT,
                timeframe TEXT,
                entry REAL,
                tp REAL,
                sl REAL,
                amount REAL,
                exchange_order_id TEXT,
                status TEXT DEFAULT 'OPEN',
                pnl REAL DEFAULT 0,
                result_reason TEXT,
                sent_open_msg BOOLEAN DEFAULT FALSE,
                sent_close_msg BOOLEAN DEFAULT FALSE,
                breakeven_sent INTEGER DEFAULT 0,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP
            )
            """)

            alter_queries = [
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS timeframe TEXT",
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS result_reason TEXT",
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS sent_open_msg BOOLEAN DEFAULT FALSE",
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS sent_close_msg BOOLEAN DEFAULT FALSE",
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS breakeven_sent INTEGER DEFAULT 0",
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE trades_log ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP"
            ]

            for q in alter_queries:
                try:
                    c.execute(q)
                except Exception as e:
                    log(f"ALTER WARNING: {e}")

            conn.commit()

        log("Trade tables initialized")
    except Exception as e:
        log(f"init_trade_tables error: {e}")

# ================= FORMATTERS =================
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
        else:
            return round(price, 8)
    except:
        return price

def format_signal(signal):
    rr = calculate_rr(signal["entry"], signal["tp"], signal["sl"], signal["direction"])
    return f"""🔥 {signal['pair']}

📊 Type: {signal.get('type', 'FUTURES')}
📈 Direction: {signal['direction']}

💰 Entry: {format_price(signal['entry'])}
🎯 TP: {format_price(signal['tp'])}
🛑 SL: {format_price(signal['sl'])}
⚖️ RR: {round(rr, 2)}

🎯 Signal Strength: {signal.get('confidence', 'N/A')}%
⏱ Timeframe: {signal.get('timeframe', 'N/A')}
📉 Trend: {signal.get('trend', 'N/A')}
⚡ Trend Power: {signal.get('trend_power', 'N/A')}
📦 Volume: {signal.get('volume', 'N/A')}
🧠 SMC: {signal.get('smc', 'N/A')}
🏗 Structure: {signal.get('structure', 'N/A')}

⚠️ Risk-managed signal. Wait for proper entry.
"""

def format_trade_fail_reason(reason):
    try:
        r = str(reason).strip()

        mapping = {
            "Duplicate trade blocked": "🚫 تم منع التنفيذ لأن نفس الصفقة مفتوحة أو تم تنفيذها قريبًا",
            "فشل سحب السعر الحالي": "🚫 تعذر سحب السعر الحالي من السوق",
            "رصيد USDT أقل من الحد الأدنى": "🚫 الرصيد غير كافٍ (USDT أقل من الحد الأدنى)",
            "قيمة الصفقة أقل من الحد الأدنى": "🚫 قيمة الصفقة أقل من الحد الأدنى المسموح",
            "فشل تنفيذ أمر السوق": "🚫 فشل تنفيذ أمر السوق على Binance",
            "API Key / Secret غير صالحين أو لا يوجد صلاحيات": "🚫 API Key / Secret غير صالحين أو لا توجد صلاحيات تداول Futures",
            "رصيد غير كافي لتنفيذ الصفقة": "🚫 الرصيد غير كافٍ لتنفيذ الصفقة",
            "No futures permission": "🚫 الحساب أو الـ API غير مفعّل لتداول Futures",
            "No spot permission": "🚫 الحساب أو الـ API غير مفعّل لتداول Spot",
            "Hedge mode issue": "🚫 مشكلة في وضع Hedge / Position Mode",
            "Symbol not available": "🚫 الزوج غير متاح للتداول على الحساب أو المنصة",
        }

        for key, value in mapping.items():
            if key.lower() in r.lower():
                return value

        if "insufficient" in r.lower():
            return "🚫 الرصيد غير كافٍ لتنفيذ الصفقة"

        if "margin" in r.lower():
            return "🚫 لا يوجد Margin / Futures Balance كافي"

        if "permission" in r.lower():
            return "🚫 لا توجد صلاحيات تداول كافية على الـ API"

        if "position side" in r.lower():
            return "🚫 مشكلة في إعدادات Hedge Mode / Position Side"

        if "invalid api-key" in r.lower() or "signature" in r.lower() or "api-key" in r.lower():
            return "🚫 API Key / Secret غير صالحين"

        if "notional" in r.lower():
            return "🚫 قيمة الصفقة أقل من الحد الأدنى المطلوب للزوج"

        if "min" in r.lower() and "amount" in r.lower():
            return "🚫 كمية الصفقة أقل من الحد الأدنى المطلوب"

        if "price" in r.lower() and "moved" in r.lower():
            return "🚫 تم رفض التنفيذ لأن السعر تحرك بعيدًا عن نقطة الدخول"

        if "تم رفض التنفيذ لأن السعر تحرك" in r:
            return f"🚫 {r}"

        return f"🚫 سبب التنفيذ: {r}"
    except Exception:
        return "🚫 فشل تنفيذ الصفقة لسبب غير معروف"

# ================= RISK HELPERS =================
def today_bounds():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day, 0, 0, 0)
    end = start + timedelta(days=1)
    return start, end

def get_daily_trade_count(chat_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            start, end = today_bounds()
            c.execute("""
            SELECT COUNT(*) FROM trades_log
            WHERE chat_id = %s
            AND opened_at >= %s
            AND opened_at < %s
            """, (str(chat_id), start, end))
            return int(c.fetchone()[0] or 0)
    except Exception as e:
        log(f"get_daily_trade_count error: {e}")
        return 0

def get_open_trade_count(chat_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT COUNT(*) FROM trades_log
            WHERE chat_id = %s
            AND status = 'OPEN'
            """, (str(chat_id),))
            return int(c.fetchone()[0] or 0)
    except Exception as e:
        log(f"get_open_trade_count error: {e}")
        return 0

def get_consecutive_losses(chat_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
            SELECT pnl FROM trades_log
            WHERE chat_id = %s
            AND status IN ('SL_HIT', 'CLOSED')
            ORDER BY id DESC
            LIMIT 10
            """, (str(chat_id),))
            rows = c.fetchall()

        losses = 0
        for row in rows:
            pnl = float(row[0] or 0)
            if pnl < 0:
                losses += 1
            else:
                break

        return losses
    except Exception as e:
        log(f"get_consecutive_losses error: {e}")
        return 0

def get_daily_loss(chat_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            start, end = today_bounds()
            c.execute("""
            SELECT COALESCE(SUM(pnl), 0) FROM trades_log
            WHERE chat_id = %s
            AND status IN ('SL_HIT', 'CLOSED')
            AND opened_at >= %s
            AND opened_at < %s
            """, (str(chat_id), start, end))
            return float(c.fetchone()[0] or 0)
    except Exception as e:
        log(f"get_daily_loss error: {e}")
        return 0.0

def has_open_trade(chat_id, pair=None):
    try:
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

            return c.fetchone() is not None
    except Exception as e:
        log(f"has_open_trade error: {e}")
        return False

def pair_in_cooldown(chat_id, pair):
    try:
        with get_db() as conn:
            c = conn.cursor()
            cooldown_time = datetime.now() - timedelta(minutes=PAIR_COOLDOWN_MINUTES)

            c.execute("""
            SELECT id FROM trades_log
            WHERE chat_id = %s
            AND pair = %s
            AND opened_at >= %s
            ORDER BY id DESC
            LIMIT 1
            """, (str(chat_id), pair, cooldown_time))

            return c.fetchone() is not None
    except Exception as e:
        log(f"pair_in_cooldown error: {e}")
        return False
    
def is_trade_locked(chat_id, signal):
    try:
        entry = round(float(signal['entry']), 1)
        key = f"{chat_id}_{signal['pair']}_{signal['direction']}_{entry}"
        now = datetime.now()

        if key in EXECUTION_LOCK:
            last_time = EXECUTION_LOCK[key]
            if (now - last_time).total_seconds() < EXECUTION_LOCK_EXPIRY:
                return True

        EXECUTION_LOCK[key] = now
        return False

    except Exception as e:
        log(f"lock error: {e}")
        return True    

def can_trade_user(chat_id, trade_amount):
    if get_daily_trade_count(chat_id) >= MAX_DAILY_TRADES:
        return False, "🚫 تم الوصول للحد الأقصى للصفقات اليوم"

    if get_open_trade_count(chat_id) >= MAX_OPEN_TRADES_PER_USER:
        return False, "🚫 لديك الحد الأقصى من الصفقات المفتوحة"

    if get_consecutive_losses(chat_id) >= MAX_CONSECUTIVE_LOSSES:
        return False, "🚫 تم إيقاف التداول بسبب خسائر متتالية"

    daily_loss = get_daily_loss(chat_id)
    max_loss_allowed = float(trade_amount or 10) * (MAX_DAILY_LOSS_PERCENT / 100)

    if daily_loss <= -abs(max_loss_allowed):
        return False, "🚫 تم إيقاف التداول بسبب الوصول لحد الخسارة اليومية"

    return True, "OK"

# ================= EXCHANGE =================
def normalize_symbol_for_ccxt(symbol):
    try:
        if not symbol:
            return symbol
        if "/" in symbol:
            return symbol
        if symbol.endswith("USDT"):
            return f"{symbol[:-4]}/USDT"
        return symbol
    except:
        return symbol

def get_exchange(api_key, api_secret, trade_type):
    try:
        import ccxt

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

        # 🔥 مهم جدًا
        exchange.set_sandbox_mode(False)

        # 🔥 تحميل الماركت (بيحل مشاكل كتير)
        exchange.load_markets()

        return exchange

    except Exception as e:
        print(f"Exchange init error: {e}")
        return None

def check_api_permissions(exchange, trade_type):
    try:
        exchange.load_markets()
        exchange.fetch_balance()

        if trade_type == "futures":
            try:
                exchange.fapiPrivateGetAccount()
                return True, "OK"
            except Exception as e:
                return False, f"No futures permission: {e}"

        return True, "OK"

    except ccxt.AuthenticationError as e:
        return False, f"API Key / Secret غير صالحين أو لا يوجد صلاحيات: {e}"
    except Exception as e:
        return False, str(e)

# ================= EXECUTION =================
def execute_trade(api_key, api_secret, signal, trade_type, risk_percent, chat_id):
    conn = None
    try:
        # ================= SAFE DECRYPT =================
        try:
            dec_key = decrypt_text(api_key)
            dec_secret = decrypt_text(api_secret)

            if dec_key and dec_secret:
                api_key = dec_key
                api_secret = dec_secret
        except:
            pass

        # ================= VALIDATION =================
        if not api_key or not api_secret:
            return None, "API KEY / SECRET invalid"

        exchange = get_exchange(api_key, api_secret, trade_type)
        exchange.load_markets()

        perm_ok, perm_msg = check_api_permissions(exchange, trade_type)
        if not perm_ok:
            return None, perm_msg

        raw_symbol = signal["pair"]
        symbol = normalize_symbol_for_ccxt(raw_symbol)

        if symbol not in exchange.markets:
            return None, f"Symbol not available: {symbol}"

        # ================= SIGNAL DATA =================
        entry = float(signal["entry"])
        tp = float(signal["tp"])
        sl = float(signal["sl"])
        side = "buy" if signal["direction"] == "LONG" else "sell"

        live_price = get_live_price(raw_symbol)
        if live_price is None:
            return None, "فشل سحب السعر الحالي"

        # ================= SIGNAL FRESHNESS =================
        signal_time = signal.get("timestamp")
        if signal_time:
            try:
                age = (datetime.utcnow() - signal_time).total_seconds()
                if age > SIGNAL_FRESHNESS_SECONDS:
                    return None, "تم رفض التنفيذ لأن الإشارة قديمة"
            except:
                pass

        # ================= PRICE DEVIATION =================
        deviation = abs(live_price - entry) / entry * 100
        if deviation > MAX_ENTRY_DEVIATION_PERCENT:
            return None, f"تم رفض التنفيذ لأن السعر تحرك ({round(deviation,4)}%)"

        # ================= LEVERAGE =================
        leverage = 10

        if trade_type == "futures":
            try:
                exchange.set_position_mode(True)
            except Exception as e:
                log(f"Hedge mode warning: {e}")

            try:
                exchange.set_leverage(leverage, symbol)
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

        # ================= POSITION SIZE =================
        position_notional = capital_to_use * leverage if trade_type == "futures" else capital_to_use
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

        # ================= ORDER =================
        params = {}
        if trade_type == "futures":
            params = {
                "positionSide": "LONG" if signal["direction"] == "LONG" else "SHORT"
            }

        order = exchange.create_market_order(symbol, side, amount, params=params)

        if not order or not order.get("id"):
            return None, "فشل تنفيذ أمر السوق"

        # ================= REAL ENTRY =================
        real_entry = entry
        try:
            if order.get("average"):
                real_entry = float(order.get("average"))
            elif order.get("price"):
                real_entry = float(order.get("price"))
        except:
            pass

        # ================= SAVE TRADE =================
        conn = db()
        c = conn.cursor()

        c.execute("""
        INSERT INTO trades_log (
            chat_id, pair, direction, trade_type, timeframe, entry, tp, sl, amount,
            exchange_order_id, status, pnl, result_reason, sent_open_msg, sent_close_msg, breakeven_sent
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(chat_id),
            raw_symbol,
            signal["direction"],
            trade_type,
            signal.get("timeframe", "5m"),
            real_entry,
            tp,
            sl,
            amount,
            str(order.get("id")),
            "OPEN",
            0,
            None,
            True,
            False,
            0
        ))
        conn.commit()
        conn.close()

        signal["real_entry"] = round(real_entry, 8)
        return order, "OK"

    except ccxt.InsufficientFunds as e:
        log(f"execute_trade insufficient funds: {e}")
        if conn:
            conn.close()
        return None, "رصيد غير كافي لتنفيذ الصفقة"

    except ccxt.InvalidOrder as e:
        log(f"execute_trade invalid order: {e}")
        if conn:
            conn.close()
        return None, f"أمر غير صالح: {e}"

    except ccxt.AuthenticationError as e:
        log(f"execute_trade auth error: {e}")
        if conn:
            conn.close()
        return None, f"API ERROR: {e}"

    except Exception as e:
        log(f"execute_trade full error: {e}")
        if conn:
            conn.close()
        return None, f"Trade Error: {e}"

# ================= NO SIGNAL =================
def should_notify_no_signal(chat_id):
    try:
        now = datetime.now()

        if chat_id not in LAST_NO_SIGNAL_NOTIFY:
            LAST_NO_SIGNAL_NOTIFY[chat_id] = now
            return True

        diff_minutes = (now - LAST_NO_SIGNAL_NOTIFY[chat_id]).total_seconds() / 60
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
                    write_log(chat_id, "INFO", "No-signal market warning sent")

            except Exception as inner_e:
                log(f"notify_users_no_signal inner error: {inner_e}")
    except Exception as e:
        log(f"notify_users_no_signal error: {e}")

# ================= TRADE TRACKER =================
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
                        continue

                    pnl = 0
                    should_close = False
                    new_status = None

                    if direction == "LONG":
                        if current_price >= tp:
                            pnl = (tp - entry) * amount
                            should_close = True
                            new_status = "TP_HIT"
                        elif current_price <= sl:
                            pnl = (sl - entry) * amount
                            should_close = True
                            new_status = "SL_HIT"

                    elif direction == "SHORT":
                        if current_price <= tp:
                            pnl = (entry - tp) * amount
                            should_close = True
                            new_status = "TP_HIT"
                        elif current_price >= sl:
                            pnl = (entry - sl) * amount
                            should_close = True
                            new_status = "SL_HIT"

                    if should_close:
                        c.execute("""
                        UPDATE trades_log
                        SET status = %s,
                            pnl = %s,
                            closed_at = NOW(),
                            sent_close_msg = TRUE
                        WHERE id = %s
                        """, (new_status, round(pnl, 4), trade_id))

                        c.execute("""
                        UPDATE users
                        SET profit = COALESCE(profit, 0) + %s
                        WHERE chat_id = %s
                        """, (round(pnl, 4), str(chat_id)))

                        conn.commit()

                        result_emoji = "✅" if pnl > 0 else "❌"

                        send(chat_id, f"""📌 تم إغلاق الصفقة

🔥 {pair}
📊 Direction: {direction}
📍 Result: {new_status}
💵 Entry: {format_price(entry)}
📍 Exit Price: {format_price(current_price)}
{result_emoji} PNL: {round(pnl, 4)} USDT
""")

                except Exception as e:
                    log(f"trade monitor inner error: {e}")

    except Exception as e:
        log(f"update_closed_trades error: {e}")

# ================= TRIAL COUNTER =================
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

# ================= MAIN LOOP =================
def run():
    log("AUTO FILE STARTED")

    # 🔥 اطبع IP الحقيقي
    try:
        import requests
        ip = requests.get("https://api.ipify.org").text
        log(f"🔥 REAL BOT IP: {ip}")
    except Exception as e:
        log(f"IP check failed: {e}")

    init_trade_tables()
    log("BOT STARTED - FINAL SAFE MODE")
    log("Entering main bot loop...")

    sent_signals = {}

    while True:
        try:
            clean_execution_lock()
            log("Loop tick...")

        # ✅ تحديث الصفقات (أهم سطر)
            update_trades(get_price)

            update_closed_trades()

            signals = get_monster_signals()
            users = get_users()

            if not signals:
                log("No strong signals found")
                notify_users_no_signal(users)
                time.sleep(30)
                continue

            sent_to_channel_pairs = set()

            # تنظيف ذاكرة الإشارات (Memory Leak Fix)
            now = datetime.now()

            for k in list(USER_SIGNAL_MEMORY.keys()):
               if (now - USER_SIGNAL_MEMORY[k]).total_seconds() > USER_SIGNAL_EXPIRY:
                 del USER_SIGNAL_MEMORY[k]

            for signal in signals[:MAX_SIGNALS_PER_CYCLE]:
                try:
                    signal_key = f"{signal.get('pair')}_{signal.get('direction')}"
                    now = time.time()

                    if signal_key in sent_signals:
                      if now - sent_signals[signal_key] < 1800:
                        continue

                    sent_signals[signal_key] = now

                    if CHANNEL_ID and signal_key not in sent_to_channel_pairs:
                       send_channel(format_signal(signal))
                       sent_to_channel_pairs.add(signal_key)

                except Exception as ch_e:
                   log(f"Channel send error: {ch_e}")

                for user in users:
                    try:
                        chat_id, is_paid, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active = user

                        if not chat_id:
                            continue

                        if plan == "trial":
                            if not is_trial_allowed(trades):
                                continue
                        else:
                            if not is_paid_plan_active(plan, expiry, is_paid):
                                continue

                        if not signal_allowed_for_plan(plan, signal):
                            continue

                        signal_id = f"{signal['pair']}_{signal['direction']}"
                        user_key = f"{chat_id}_{signal_id}"

                        now = datetime.now()

# منع التكرار لنفس المستخدم
                        if user_key in USER_SIGNAL_MEMORY:
                             last_time = USER_SIGNAL_MEMORY[user_key]
                             if (now - last_time).total_seconds() < 600:  # 10 دقايق
                                        continue

                        USER_SIGNAL_MEMORY[user_key] = now

                        # ================= VIP AUTO TRADE =================
                        if (
                            str(plan).strip().lower() == "vip"
                            and (str(expiry).strip().lower() == "lifetime" or is_paid_plan_active(plan, expiry, is_paid))
                            and int(bot_active or 0) == 1
                            and api_key
                            and api_secret
                        ):
                            try:
                                can_trade, reason = can_trade_user(chat_id, trade_amount)
                                if not can_trade:
                                    send(chat_id, f"""{format_signal(signal)}

🤖 تنبيه التنفيذ التلقائي

{reason}
""")
                                    continue

                                if has_open_trade(chat_id, signal["pair"]):
                                    send(chat_id, f"""{format_signal(signal)}

🤖 تنبيه التنفيذ التلقائي

🚫 لديك بالفعل صفقة مفتوحة على نفس الزوج
""")
                                    continue

                                if pair_in_cooldown(chat_id, signal["pair"]):
                                    send(chat_id, f"""{format_signal(signal)}

🤖 تنبيه التنفيذ التلقائي

🚫 هذا الزوج داخل فترة تهدئة (Cooldown)
""")
                                    continue

                                # 🚫 منع تنفيذ مكرر
                                # 🔥 منع تكرار الإشارات (الأهم)
                                if is_signal_blocked(chat_id, signal):
                                   log(f"🚫 BLOCKED SIGNAL: {signal.get('pair')}")
                                   continue

# 🔒 منع تنفيذ مكرر
                                if is_trade_locked(chat_id, signal):
                                  log(f"🔒 LOCKED: {chat_id} | {signal.get('pair')} | {signal.get('direction')}")
                                  continue

                                signal_trade_type = "futures" if signal.get("type", "FUTURES") == "FUTURES" else "spot"

                                order, result_msg = execute_trade(
                                    api_key=api_key,
                                    api_secret=api_secret,
                                    signal=signal,
                                    trade_type=signal_trade_type,
                                    risk_percent=trade_amount,
                                    chat_id=chat_id
                                )
                                log(f"🔥 EXECUTION RESULT: {result_msg}")

                                if order:
                                    real_entry = signal.get("real_entry", signal["entry"])

                                    send(chat_id, f"""{format_signal(signal)}

🤖 تم تنفيذ صفقة VIP تلقائيًا

🔥 {signal['pair']}
📈 الاتجاه: {signal['direction']}
💰 الدخول الفعلي: {format_price(real_entry)}
🎯 الهدف: {format_price(signal['tp'])}
🛑 الوقف: {format_price(signal['sl'])}
📦 النوع: {signal.get('type', 'FUTURES')}
🆔 Order ID: {order.get('id')}

✅ تم فتح الصفقة بنجاح على Binance
""")

                                    write_log(chat_id, "INFO", f"AUTO TRADE EXECUTED {signal['pair']} ORDER={order.get('id')}")

                                else:
                                    fail_reason = format_trade_fail_reason(result_msg)

                                    send(chat_id, f"""{format_signal(signal)}

🤖 فشل التنفيذ التلقائي

{fail_reason}

⚠️ تم إرسال الإشارة فقط ولم يتم فتح الصفقة تلقائيًا.
""")

                                    write_log(chat_id, "ERROR", f"AUTO TRADE FAILED: {result_msg}")

                            except Exception as e:
                                fail_reason = format_trade_fail_reason(str(e))

                                send(chat_id, f"""{format_signal(signal)}

🤖 فشل التنفيذ التلقائي

{fail_reason}

⚠️ تم إرسال الإشارة فقط ولم يتم فتح الصفقة تلقائيًا.
""")

                                write_log(chat_id, "ERROR", f"AUTO TRADE EXCEPTION: {str(e)}")

                        # ================= NORMAL SEND =================
                        else:
                            sent_ok = send(chat_id, format_signal(signal))

                            if sent_ok:
                                write_log(chat_id, "INFO", f"SIGNAL SENT {signal['pair']} {signal['direction']}")

                                if plan == "trial":
                                    increment_trade(chat_id)

                    except Exception as user_loop_error:
                        log(f"user loop error: {user_loop_error}")
                        continue

            time.sleep(GLOBAL_LOOP_SLEEP)

        except Exception as e:
            log(f"RUN LOOP ERROR: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run()