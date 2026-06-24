import time
import requests
from datetime import datetime, timedelta
from market_analyzer import get_top_free_signals, generate_signal, SYMBOLS
from ai_model import predict_trade
from spot_futures_engine import record_trade_type, type_allowed_for_user
import ccxt
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_TOKEN")

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
MAX_ENTRY_DEVIATION_PERCENT = 0.75    # كان 0.35 وخانق الدنيا
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

# ================= LOG =================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# ================= DB =================
def db():
    database_url = os.environ.get("DATABASE_URL")


    if not database_url:
        raise Exception("DATABASE_URL not found in environment variables")

    database_url = database_url.strip()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(database_url, sslmode="require")

# ================= TELEGRAM =================
CHANNEL_ID = -1003722350505
def send(chat_id, text):
    try:
        if not TOKEN or not chat_id:
            log(f"Telegram skipped: TOKEN or chat_id missing | chat_id={chat_id}")
            return False

        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
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
        if not TOKEN:
            log("Telegram skipped: TOKEN missing for channel")
            return False

        r = requests.post(
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

        log("📢 Signal sent to channel successfully")
        return True

    except Exception as e:
        log(f"❌ Channel send error: {e}")
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
    except:
        return symbol

def normalize_symbol_for_rest(symbol):
    try:
        if not symbol:
            return symbol
        return symbol.replace("/", "")
    except:
        return symbol

# ================= MARKET PRICE HELPERS =================
def get_live_price(symbol):
    try:
        rest_symbol = normalize_symbol_for_rest(symbol)

        # الأول Binance
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={rest_symbol}"
        r = requests.get(url, timeout=10).json()
        if "price" in r:
            return float(r["price"])

        # fallback Binance US
        url_us = f"https://api.binance.us/api/v3/ticker/price?symbol={rest_symbol}"
        r2 = requests.get(url_us, timeout=10).json()
        if "price" in r2:
            return float(r2["price"])

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
    except:
        return signal

def signal_not_expired(signal):
    try:
        generated_at = signal.get("generated_at")
        if not generated_at:
            return True

        ts = datetime.fromisoformat(generated_at)
        age = (datetime.now() - ts).total_seconds()
        return age <= SIGNAL_FRESHNESS_SECONDS
    except:
        return True

# ================= ELITE FILTER =================
def elite_trade_filter(signal):
    try:
        confidence = float(signal.get("confidence", 0))
        engine_confidence = float(signal.get("engine_confidence", confidence))
        risk_score = float(signal.get("risk_score", 50))
        score = abs(float(signal.get("score", 0)))
        trend_power = signal.get("trend_power")
        volume = signal.get("volume")
        structure = signal.get("structure")
        timeframe = signal.get("timeframe")

        if risk_score > 58:
            return False

        if confidence >= 88 and engine_confidence >= 84 and score >= 6:
            return True

        if (
            confidence >= 85
            and engine_confidence >= 80
            and score >= 5
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            and volume == "STRONG"
            and structure in ["NEAR_BREAKOUT_HIGH", "NEAR_BREAKOUT_LOW", "MID_RANGE"]
            and timeframe in ["15m", "1h", "5m"]
        ):
            return True

        if (
            confidence >= 82
            and engine_confidence >= 78
            and score >= 5
            and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
        ):
            return True

        return False
    except:
        return False
# ================= INIT TABLES =================
def init_trade_tables():
    conn = db()
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

    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spot_enabled INTEGER DEFAULT 1")
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS futures_enabled INTEGER DEFAULT 1")

    conn.commit()
    conn.close()
    log("Trade tables initialized")

def write_log(chat_id, level, message):
    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
        INSERT INTO bot_logs (chat_id, level, message)
        VALUES (%s, %s, %s)
        """, (chat_id, level, message))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"DB log insert failed: {e}")

# ================= USERS =================
def get_users():
    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid,
           COALESCE(spot_enabled, 1), COALESCE(futures_enabled, 1)
    FROM users
    WHERE chat_id IS NOT NULL
      AND chat_id <> ''
    """)

    users = c.fetchall()
    conn.close()
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
    except:
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
    except:
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
🧠 AI Confidence: {signal.get('engine_confidence', signal.get('confidence', 'N/A'))}%
🛡 Risk Score: {signal.get('risk_score', 'N/A')} / 100 ({signal.get('risk_level', 'N/A')})
⏱ Timeframe: {signal.get('timeframe', 'N/A')}
🔭 Multi-Timeframe: {signal.get('multi_timeframe', 'N/A')}
📉 Trend: {signal.get('trend', 'N/A')}
📦 Volume: {signal.get('volume', 'N/A')}
🌊 Volatility: {signal.get('volatility_state', 'N/A')}
🧱 Structure: {signal.get('market_structure', signal.get('structure', 'N/A'))}
⚖️ Spot/Futures Score: {signal.get('spot_score', 'N/A')} / {signal.get('futures_score', 'N/A')}
🧠 SMC: {signal.get('smc', 'N/A')}

⚠️ Risk-managed signal. Wait for proper entry.
"""
# ================= ACCESS HELPERS =================
def is_trial_allowed(trades):
    return (trades or 0) < 2

def is_paid_plan_active(plan, expiry, is_paid):
    if plan == "trial":
        return True

    if is_paid != 1:
        return False

    if not expiry:
        return False

    if str(expiry).lower() == "lifetime":
        return True

    try:
        expiry_date = datetime.strptime(str(expiry), "%Y-%m-%d")
        return datetime.now() <= expiry_date
    except:
        return False

# ================= PLAN FILTER =================
def signal_allowed_for_plan(plan, signal):
    try:
        confidence = float(signal.get("confidence", 0))
        engine_confidence = float(signal.get("engine_confidence", confidence))
        risk_score = float(signal.get("risk_score", 50))
        score = abs(float(signal.get("score", 0)))
        timeframe = signal.get("timeframe", "5m")
        volume = signal.get("volume", "WEAK")
        trend_power = signal.get("trend_power", "MIXED")

        if risk_score >= 72:
            return False

        if plan == "trial":
            return (
                confidence >= 68
                and engine_confidence >= 65
                and score >= 5
                and timeframe in ["5m", "15m"]
            )

        if plan == "basic":
            return (
                confidence >= 72
                and engine_confidence >= 68
                and score >= 5
                and volume == "STRONG"
            )

        if plan == "pro":
            return (
                confidence >= 76
                and engine_confidence >= 72
                and risk_score <= 62
                and score >= 6
                and volume == "STRONG"
                and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            )

        if plan == "vip":
            return (
                confidence >= 78
                and engine_confidence >= 75
                and risk_score <= 58
                and score >= 6
            )

        return False
    except:
        return False
# ================= EXCHANGE =================
def get_exchange(api_key, api_secret, trade_type):
    default_type = "future" if trade_type == "futures" else "spot"

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {"defaultType": default_type}
    })

    return exchange

# ================= SAFETY HELPERS =================
def today_bounds():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day, 0, 0, 0)
    end = start + timedelta(days=1)
    return start, end

def get_daily_trade_count(chat_id):
    conn = db()
    c = conn.cursor()

    start, end = today_bounds()
    c.execute("""
    SELECT COUNT(*) FROM trades_log
    WHERE chat_id = %s
    AND created_at >= %s
    AND created_at < %s
    """, (chat_id, start, end))

    count = c.fetchone()[0]
    conn.close()
    return count

def get_open_trade_count(chat_id):
    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT COUNT(*) FROM trades_log
    WHERE chat_id = %s
    AND status = 'OPEN'
    """, (chat_id,))

    count = c.fetchone()[0]
    conn.close()
    return count

def get_consecutive_losses(chat_id):
    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT pnl FROM trades_log
    WHERE chat_id = %s
    AND status = 'CLOSED'
    ORDER BY created_at DESC
    LIMIT 10
    """, (chat_id,))

    rows = c.fetchall()
    conn.close()

    losses = 0
    for row in rows:
        pnl = row[0] or 0
        if pnl < 0:
            losses += 1
        else:
            break

    return losses

def get_daily_loss(chat_id):
    conn = db()
    c = conn.cursor()

    start, end = today_bounds()
    c.execute("""
    SELECT COALESCE(SUM(pnl), 0) FROM trades_log
    WHERE chat_id = %s
    AND status = 'CLOSED'
    AND created_at >= %s
    AND created_at < %s
    """, (chat_id, start, end))

    total = c.fetchone()[0] or 0
    conn.close()
    return total

def has_open_trade(chat_id, pair=None):
    conn = db()
    c = conn.cursor()

    if pair:
        c.execute("""
        SELECT id FROM trades_log
        WHERE chat_id = %s AND pair = %s AND status = 'OPEN'
        LIMIT 1
        """, (chat_id, pair))
    else:
        c.execute("""
        SELECT id FROM trades_log
        WHERE chat_id = %s AND status = 'OPEN'
        LIMIT 1
        """, (chat_id,))

    row = c.fetchone()
    conn.close()
    return row is not None

def pair_in_cooldown(chat_id, pair):
    conn = db()
    c = conn.cursor()

    cooldown_time = datetime.now() - timedelta(minutes=PAIR_COOLDOWN_MINUTES)

    c.execute("""
    SELECT id FROM trades_log
    WHERE chat_id = %s AND pair = %s AND created_at >= %s
    ORDER BY created_at DESC
    LIMIT 1
    """, (chat_id, pair, cooldown_time))

    row = c.fetchone()
    conn.close()
    return row is not None

def can_trade_user(chat_id, trade_amount):
    if get_daily_trade_count(chat_id) >= MAX_DAILY_TRADES:
        return False, "🚫 تم الوصول للحد الأقصى للصفقات اليوم"

    if get_open_trade_count(chat_id) >= MAX_OPEN_TRADES_PER_USER:
        return False, "🚫 لديك الحد الأقصى من الصفقات المفتوحة"

    if get_consecutive_losses(chat_id) >= MAX_CONSECUTIVE_LOSSES:
        return False, "🚫 تم إيقاف التداول بسبب خسائر متتالية"

    daily_loss = get_daily_loss(chat_id)
    max_loss_allowed = (trade_amount or 10) * (MAX_DAILY_LOSS_PERCENT / 100)

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

def place_protection_orders(exchange, symbol, side, amount, tp_price, sl_price, trade_type):
    try:
        opposite_side = "sell" if side == "buy" else "buy"

        if trade_type == "futures":
            exchange.create_order(
                symbol=symbol,
                type="TAKE_PROFIT_MARKET",
                side=opposite_side,
                amount=amount,
                params={"stopPrice": tp_price, "closePosition": False}
            )

            exchange.create_order(
                symbol=symbol,
                type="STOP_MARKET",
                side=opposite_side,
                amount=amount,
                params={"stopPrice": sl_price, "closePosition": False}
            )

        return True, "TP/SL placed"

    except Exception as e:
        return False, f"Protection order error: {e}"

# ================= TRADE EXECUTION =================
def execute_trade(api_key, api_secret, signal, trade_type, risk_percent, chat_id):
    try:
        exchange = get_exchange(api_key, api_secret, trade_type)
        exchange.load_markets()

        raw_symbol = signal["pair"]
        symbol = normalize_symbol_for_ccxt(raw_symbol)

        balance = exchange.fetch_balance()
        usdt_balance = (
            balance.get("USDT", {}).get("free")
            or balance.get("free", {}).get("USDT")
            or 0
        )
        usdt_balance = float(usdt_balance or 0)

        if usdt_balance < 10:
            return None, "رصيد USDT أقل من الحد الأدنى"

        side = "buy" if signal["direction"] == "LONG" else "sell"
        entry = float(signal["entry"])
        tp = float(signal["tp"])
        sl = float(signal["sl"])

        # تأكيد حي قبل التنفيذ
        live_price = get_live_price(raw_symbol)
        if live_price is None:
            return None, "فشل سحب السعر الحالي"

        deviation = abs(live_price - entry) / entry * 100
        if deviation > MAX_ENTRY_DEVIATION_PERCENT:
            return None, f"تم رفض الصفقة: السعر تحرك ({round(deviation,4)}%)"

        amount = calculate_amount(usdt_balance, risk_percent, entry)
        if amount <= 0:
            return None, "كمية الصفقة غير صالحة"

        valid_amount, reason = validate_symbol_amount(exchange, symbol, amount)
        if not valid_amount:
            return None, f"Validation failed: {reason}"

        order = exchange.create_market_order(symbol, side, amount)

        if not order or not order.get("id"):
            return None, "فشل تنفيذ أمر السوق"

        protection_ok, protection_msg = place_protection_orders(
            exchange, symbol, side, amount, tp, sl, trade_type
        )

        conn = db()
        c = conn.cursor()
        c.execute("""
        INSERT INTO trades_log (
            chat_id, pair, direction, trade_type, entry, tp, sl, amount,
            exchange_order_id, status, pnl
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            chat_id,
            raw_symbol,
            signal["direction"],
            trade_type,
            entry,
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

    except Exception as e:
        return None, f"Trade Error: {e}"

# ================= TRADE MONITOR =================
def update_closed_trades():
    try:
        conn = db()
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

                if direction == "LONG":
                    if current_price >= tp:
                        pnl = (tp - entry) * amount
                        should_close = True
                    elif current_price <= sl:
                        pnl = (sl - entry) * amount
                        should_close = True

                elif direction == "SHORT":
                    if current_price <= tp:
                        pnl = (entry - tp) * amount
                        should_close = True
                    elif current_price >= sl:
                        pnl = (entry - sl) * amount
                        should_close = True

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
                    """, (round(pnl, 4), chat_id))

                    conn.commit()
                    write_log(chat_id, "INFO", f"Trade closed {pair} pnl={round(pnl,4)}")

                    send(chat_id, f"""📌 تم إغلاق الصفقة

🔥 {pair}
📊 Direction: {direction}
💰 PNL: {round(pnl, 4)} USDT
""")

            except Exception as e:
                write_log(chat_id, "ERROR", f"Trade monitor error for {pair}: {e}")

        conn.close()

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
        conn = db()
        c = conn.cursor()
        c.execute("""
            UPDATE users
            SET trades = COALESCE(trades, 0) + 1
            WHERE chat_id = %s
        """, (chat_id,))
        conn.commit()
        conn.close()
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
    except:
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

        # مدة منع التكرار حسب الفريم
        cooldown_seconds = 3600  # ساعة كاملة افتراضي
        if timeframe == "15m":
            cooldown_seconds = 7200   # ساعتين
        elif timeframe == "1h":
            cooldown_seconds = 14400  # 4 ساعات

        if key in RECENT_SIGNAL_MEMORY:
            old_entry, old_time = RECENT_SIGNAL_MEMORY[key]
            age = (now - old_time).total_seconds()

            if age < cooldown_seconds:
                diff = abs(entry - old_entry) / old_entry * 100

                # لو نفس العملة ونفس الاتجاه والسعر قريب = تجاهل
                if diff < 0.8:
                    return True

        RECENT_SIGNAL_MEMORY[key] = (entry, now)
        return False
    except:
        return False

# ================= SIGNAL FETCHER =================
def get_monster_signals():
    """
    المجاني: أفضل صفقتين
    المدفوع: نضيف paid 15m القوية
    """
    try:
        signals = get_top_free_signals(limit=FREE_SIGNALS_LIMIT) or []

        # لو السوق ضعيف جدًا، نحاول نجيب صفقة paid واحدة قوية فقط
        if not signals:
            fallback_candidates = []

            try:
                from market_analyzer import SYMBOLS, TIMEFRAMES

                for symbol in SYMBOLS:
                    for tf in TIMEFRAMES:
                        try:
                            s = generate_signal(symbol, tf)
                            if s:
                                fallback_candidates.append(s)
                        except:
                            continue

                fallback_candidates = sorted(
                    fallback_candidates,
                    key=lambda x: (x.get("confidence", 0), abs(x.get("score", 0))),
                    reverse=True
                )

                if fallback_candidates:
                    signals = fallback_candidates[:1]

            except Exception as e:
                log(f"Fallback paid signal error: {e}")

        final_signals = []

        for s in signals:
            s = attach_signal_timestamp(s)

            if not valid_signal(s):
                continue

            if not logical_signal(s):
                log(f"Logical invalid signal skipped: {s}")
                continue

            if not signal_not_expired(s):
                log(f"Expired signal skipped: {s.get('pair')}")
                continue

            if not signal_is_fresh(s):
                log(f"Freshness check failed: {s.get('pair')}")
                continue

            if is_duplicate_signal(s):
                log(f"Duplicate signal skipped: {s.get('pair')}")
                continue

            if is_recent_memory_duplicate(s):
                log(f"Recent memory duplicate skipped: {s.get('pair')}")
                continue

            # 🔥 Ultra mode
            if ULTRA_MODE:
                try:
                    if float(s.get("confidence", 0)) < 75:
                        log(f"Ultra mode rejected: {s.get('pair')} conf={s.get('confidence')}")
                        continue
                except:
                    continue

            final_signals.append(s)
            record_trade_type(s.get("type"))

        # ترتيب الأقوى أولًا
        final_signals = sorted(
            final_signals,
            key=lambda x: (
                float(x.get("confidence", 0)),
                abs(float(x.get("score", 0)))
            ),
            reverse=True
        )

        return final_signals
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
    except:
        return False


def notify_users_no_signal(users):
    try:
        for user in users:
            try:
                chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid, *type_flags = user
                spot_enabled = int(type_flags[0]) if len(type_flags) > 0 else 1
                futures_enabled = int(type_flags[1]) if len(type_flags) > 1 else 1

                if not chat_id:
                    continue

                # ===== ACCESS CHECK =====
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
    log("🚀 BOT STARTED - MONSTER MODE")
    log("Entering main bot loop...")

    while True:
        try:
            log("Loop tick...")

            update_closed_trades()
            log("Closed trades updated")

            signals = get_monster_signals()
            log(f"Signals fetched: {signals}")

            users = get_users()
            log(f"Users loaded: {len(users)}")

            if not signals:
                log("No signals found")

    # ===== Notify users market is not safe now =====
                notify_users_no_signal(users)

                time.sleep(30)
                continue

            for signal in signals:
                log(f"Processing signal: {signal}")

                for user in users:
                    chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid, *type_flags = user
                    spot_enabled = int(type_flags[0]) if len(type_flags) > 0 else 1
                    futures_enabled = int(type_flags[1]) if len(type_flags) > 1 else 1

                    if not chat_id:
                        continue

                    # ===== ACCESS CHECK =====
                    if plan == "trial":
                        if not is_trial_allowed(trades):
                            continue
                    else:
                        if not is_paid_plan_active(plan, expiry, is_paid):
                            continue

                    # ===== PLAN FILTER =====
                    if not signal_allowed_for_plan(plan, signal):
                        log(f"Signal filtered for plan {plan} -> {signal['pair']}")
                        continue

                    if not type_allowed_for_user(signal.get("type"), spot_enabled, futures_enabled):
                        log(f"Signal type filtered for user {chat_id}: {signal.get('type')} disabled")
                        continue

                    # ===== ELITE FILTER (VIP ONLY) =====
                    if plan == "vip":
                        if not elite_trade_filter(signal):
                            log(f"Elite filter rejected for VIP: {signal['pair']}")
                            continue

                    # ===== RE-CHECK FRESHNESS BEFORE SEND =====
                    # بدل ما نرفضها نهائيًا، نديها فرصة طالما لسه كويسة
                    if not signal_is_fresh(signal):
                        log(f"⚠️ price moved slightly but sending anyway: {signal['pair']}")

                    # ===== SEND SIGNAL =====
                    msg = format_signal(signal)
                    sent_ok = send(chat_id, msg)

                    if sent_ok:
                        log(f"Signal sent to {chat_id} -> {signal['pair']}")
                        write_log(chat_id, "INFO", f"Signal sent {signal['pair']} {signal['direction']} conf={signal['confidence']}")

                        if plan == "trial":
                            increment_trade(chat_id)
                    else:
                        log(f"Signal failed to send to {chat_id}")

                    # ===== AUTO TRADE FOR VIP =====
                    if plan == "vip" and bot_active == 1 and api_key and api_secret:
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
                                risk_percent=adjust_risk(profit),
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
""")
                            else:
                                log(f"Auto trade rejected for {chat_id}: {result_msg}")
                                write_log(chat_id, "ERROR", f"Auto trade rejected: {result_msg}")

                        except Exception as e:
                            log(f"Auto trade failed for {chat_id}: {e}")

            time.sleep(GLOBAL_LOOP_SLEEP)

        except Exception as e:
            log(f"RUN LOOP ERROR: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run()

