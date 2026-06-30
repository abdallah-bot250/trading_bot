import time
import requests
from datetime import datetime, timedelta
from market_analyzer import get_top_free_signals, generate_signal, get_scan_symbols
from ai_model import predict_trade
from spot_futures_engine import record_trade_type, type_allowed_for_user
import ccxt
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_TOKEN")
AUTO_TRADE_EXCHANGE = os.environ.get("AUTO_TRADE_EXCHANGE", "binance").strip().lower()
ENABLE_SIGNAL_TRACKING = os.environ.get("ENABLE_SIGNAL_TRACKING", "true").lower() in ["1", "true", "yes", "on"]
SIGNAL_TRACKING_NOTIFY = os.environ.get("SIGNAL_TRACKING_NOTIFY", "true").lower() in ["1", "true", "yes", "on"]
SIGNAL_DEBUG_LOGS = os.environ.get("SIGNAL_DEBUG_LOGS", "").strip().lower() in {"1", "true", "yes", "debug"}

# ================= CONFIG =================
MAX_DAILY_TRADES = 4
MAX_CONSECUTIVE_LOSSES = 2
MAX_DAILY_LOSS_PERCENT = 4
PAIR_COOLDOWN_MINUTES = 45
GLOBAL_LOOP_SLEEP = 80
MIN_CONFIDENCE = 66
AUTO_TRADE_PLANS = {"vip", "pro_2y"}
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
LAST_UNLINKED_USER_LOG = {}

# ================= LOG =================
LAST_LOG_CACHE = {}
LOG_THROTTLE_SECONDS = int(os.environ.get("LOG_THROTTLE_SECONDS", "900"))


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def log_once(key, msg, ttl=LOG_THROTTLE_SECONDS):
    now = time.time()
    last_seen = LAST_LOG_CACHE.get(key, 0)
    if now - last_seen >= ttl:
        LAST_LOG_CACHE[key] = now
        log(msg)

def signal_log_summary(signal):
    try:
        return (
            f"pair={signal.get('pair')} direction={signal.get('direction')} "
            f"type={signal.get('type', 'N/A')} tf={signal.get('timeframe', 'N/A')} "
            f"conf={signal.get('confidence')} rr={signal.get('risk_reward')} "
            f"regime={signal.get('market_regime', signal.get('adaptive_regime', 'N/A'))} "
            f"strategy={signal.get('strategy_name', signal.get('setup_type', 'N/A'))}"
        )
    except Exception:
        return "signal_summary_unavailable"


def log_unlinked_user_once(email):
    safe_email = str(email or "").strip().lower()
    if not safe_email:
        safe_email = "unknown"
    now = time.time()
    last_seen = LAST_UNLINKED_USER_LOG.get(safe_email, 0)
    if now - last_seen >= LOG_THROTTLE_SECONDS:
        LAST_UNLINKED_USER_LOG[safe_email] = now
        log(f"TELEGRAM_SKIP_UNLINKED_USER email={safe_email}")


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
    """Send Telegram message with explicit production logs.

    Returns:
        True  -> Telegram accepted the message.
        False -> skipped/failed. The log explains if the user blocked the bot,
                 chat id is wrong, token is missing, or Telegram API failed.
    """
    try:
        if not TOKEN:
            log(f"TELEGRAM_SEND_FAILED token_missing chat_id={chat_id}")
            return False
        if not chat_id:
            log("TELEGRAM_SEND_FAILED chat_id_missing")
            return False

        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=12
        )

        response_text = r.text or ""
        if r.status_code != 200:
            lower_text = response_text.lower()
            if r.status_code in (400, 403) and (
                "bot was blocked" in lower_text
                or "chat not found" in lower_text
                or "user is deactivated" in lower_text
                or "forbidden" in lower_text
            ):
                log(f"BOT_DISCONNECTED_OR_BLOCKED chat_id={chat_id} status={r.status_code} response={response_text[:300]}")
                try:
                    write_log(chat_id, "WARNING", f"Bot disconnected or blocked: {r.status_code}")
                except Exception:
                    pass
            else:
                log(f"TELEGRAM_SEND_FAILED chat_id={chat_id} status={r.status_code} response={response_text[:500]}")
            return False

        try:
            data = r.json()
        except Exception:
            log(f"TELEGRAM_SEND_FAILED invalid_json chat_id={chat_id} response={response_text[:300]}")
            return False

        if not data.get("ok"):
            log(f"TELEGRAM_SEND_FAILED api_not_ok chat_id={chat_id} response={data}")
            return False

        log(f"TELEGRAM_SEND_OK chat_id={chat_id}")
        return True

    except requests.exceptions.Timeout:
        log(f"TELEGRAM_SEND_FAILED timeout chat_id={chat_id}")
        return False
    except Exception as e:
        log(f"TELEGRAM_SEND_FAILED exception chat_id={chat_id} error={e}")
        return False
    
def send_channel(text):
    try:
        if not TOKEN:
            log("CHANNEL_SEND_FAILED token_missing")
            return False

        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": str(CHANNEL_ID),
                "text": text
            },
            timeout=12
        )

        if r.status_code != 200:
            log(f"CHANNEL_SEND_FAILED status={r.status_code} response={(r.text or '')[:500]}")
            return False

        data = r.json()
        if not data.get("ok"):
            log(f"CHANNEL_SEND_FAILED api_not_ok response={data}")
            return False

        log("CHANNEL_SEND_OK")
        return True

    except requests.exceptions.Timeout:
        log("CHANNEL_SEND_FAILED timeout")
        return False
    except Exception as e:
        log(f"CHANNEL_SEND_FAILED exception={e}")
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

        failures = []
        binance_global_451 = False

        # Primary: Binance global
        for provider, url in [
            ("BINANCE", f"https://api.binance.com/api/v3/ticker/price?symbol={rest_symbol}"),
            ("BINANCE_US", f"https://api.binance.us/api/v3/ticker/price?symbol={rest_symbol}"),
        ]:
            try:
                response = requests.get(url, timeout=10)
                if provider == "BINANCE" and response.status_code == 451:
                    binance_global_451 = True
                    failures.append(f"{provider}=451")
                    continue
                if response.status_code != 200:
                    failures.append(f"{provider}={response.status_code}")
                    continue
                r = response.json()
                if "price" in r:
                    if provider == "BINANCE_US" and binance_global_451:
                        if SIGNAL_DEBUG_LOGS:
                            log(f"MARKET_DATA_SOURCE BINANCE_US symbol={symbol} timeframe=price")
                    return float(r["price"])
                failures.append(f"{provider}=missing_price")
            except Exception as provider_error:
                failures.append(f"{provider}=error:{provider_error}")

        # Fallback: KuCoin when Binance is unavailable or blocks the request.
        try:
            kucoin_symbol = rest_symbol.replace("USDT", "-USDT")
            kucoin_url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_symbol}"
            k = requests.get(kucoin_url, timeout=10).json()
            price = ((k.get("data") or {}).get("price"))
            if price:
                return float(price)
            failures.append("KUCOIN=missing_price")
        except Exception as kucoin_error:
            failures.append(f"KUCOIN=error:{kucoin_error}")

        log(f"WARNING MARKET_DATA_FAILED symbol={symbol} timeframe=price failures={'; '.join(failures)}")
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS signal_log (
        id SERIAL PRIMARY KEY,
        chat_id TEXT,
        plan TEXT,
        pair TEXT,
        direction TEXT,
        signal_type TEXT,
        entry REAL,
        tp REAL,
        sl REAL,
        confidence REAL,
        status TEXT DEFAULT 'SENT',
        outcome TEXT,
        current_price REAL,
        pnl_percent REAL DEFAULT 0,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_signal_log_chat_sent ON signal_log (chat_id, sent_at)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_signal_log_status_sent ON signal_log (status, sent_at)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_signal_log_pair_status ON signal_log (pair, status)")

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


def record_sent_signal(chat_id, plan, signal):
    if not ENABLE_SIGNAL_TRACKING:
        return None
    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
        INSERT INTO signal_log (
            chat_id, plan, pair, direction, signal_type, entry, tp, sl, confidence, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'SENT')
        RETURNING id
        """, (
            str(chat_id),
            str(plan or "trial"),
            signal.get("pair"),
            signal.get("direction"),
            signal.get("type", "FUTURES"),
            float(signal.get("entry", 0)),
            float(signal.get("tp", 0)),
            float(signal.get("sl", 0)),
            float(signal.get("confidence", 0)),
        ))
        row = c.fetchone()
        conn.commit()
        conn.close()
        signal_id = row[0] if row else None
        log(f"Signal tracked id={signal_id} chat_id={chat_id} pair={signal.get('pair')}")
        return signal_id
    except Exception as e:
        log(f"record_sent_signal error: {e}")
        return None

# ================= USERS =================
def get_users():
    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid,
           COALESCE(spot_enabled, 1), COALESCE(futures_enabled, 1), email
    FROM users
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



def _signal_target_ladder(signal):
    try:
        entry = float(signal.get("entry"))
        tp = float(signal.get("tp"))
        direction = str(signal.get("direction") or "").upper()
        if entry <= 0 or tp <= 0 or direction not in ["LONG", "SHORT"]:
            return signal.get("tp"), signal.get("tp"), signal.get("tp")
        if direction == "LONG":
            distance = tp - entry
            if distance <= 0:
                return signal.get("tp"), signal.get("tp"), signal.get("tp")
            return (
                clean_number(entry + distance * 0.50, 6),
                clean_number(entry + distance * 0.78, 6),
                clean_number(tp, 6),
            )
        distance = entry - tp
        if distance <= 0:
            return signal.get("tp"), signal.get("tp"), signal.get("tp")
        return (
            clean_number(entry - distance * 0.50, 6),
            clean_number(entry - distance * 0.78, 6),
            clean_number(tp, 6),
        )
    except Exception:
        return signal.get("tp"), signal.get("tp"), signal.get("tp")

def _plan_signal_profile(plan):
    plan = str(plan or "trial").lower()
    if plan == "trial":
        return "Free Trial: 2 preview signals only. Premium analysis unlocks with a paid plan."
    if plan == "basic":
        return "Basic: more signals with clear Entry, TP and SL."
    if plan == "pro":
        return "Pro: advanced confidence, support/resistance and market context."
    if plan == "vip":
        return "Elite: full signal quality plus automation tools when configured."
    if plan == "pro_2y":
        return "Pro 2 Years: highest access tier with all signal and automation tools."
    return "Nexora signal access"

# ================= FORMAT =================
def format_signal(signal, plan=None):
    tp1, tp2, tp3 = _signal_target_ladder(signal)
    return f"""NEXORA AI TRADER SIGNAL

Pair: {signal['pair']}
Mode: {signal.get('type', 'FUTURES')}
Direction: {signal['direction']}
Timeframe: {signal.get('timeframe', 'N/A')}

Entry: {signal['entry']}
TP1: {tp1}
TP2: {tp2}
TP3: {tp3}
SL: {signal['sl']}

Support: {signal.get('nearest_support', signal.get('support', 'N/A'))}
Resistance: {signal.get('nearest_resistance', signal.get('resistance', 'N/A'))}
Risk/Reward: {signal.get('risk_reward', 'N/A')}
Confidence: {signal.get('confidence', 'N/A')}%
AI Confidence: {signal.get('engine_confidence', signal.get('confidence', 'N/A'))}%
Final Score: {signal.get('final_score', 'N/A')} / 100

Trend: {signal.get('trend', 'N/A')}
EMA Alignment: {signal.get('ema_alignment', 'N/A')}
RSI/Momentum: {signal.get('structure', signal.get('market_structure', 'N/A'))}
Volume: {signal.get('volume', signal.get('volume_state', 'N/A'))}
Market Regime: {signal.get('market_regime', signal.get('adaptive_regime', 'N/A'))}
Strategy: {signal.get('strategy_name', signal.get('setup_type', 'N/A'))}

Why this trade: {signal.get('signal_quality_reason', 'Strong support/resistance validation passed')}
Target Basis: {signal.get('target_basis', 'Support/Resistance')}
Plan Access: {_plan_signal_profile(plan)}

Risk Warning: Crypto trading is risky. This is not financial advice. Use proper position size and never trade money you cannot afford to lose.
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
                confidence >= 75
                and confidence <= 82
                and engine_confidence >= 70
                and score >= 5
                and timeframe in ["5m", "15m"]
                and risk_score <= 64
            )

        if plan == "basic":
            return (
                confidence >= 74
                and engine_confidence >= 70
                and score >= 5
                and volume == "STRONG"
                and risk_score <= 66
            )

        if plan == "pro":
            return (
                confidence >= 78
                and engine_confidence >= 74
                and risk_score <= 60
                and score >= 6
                and volume == "STRONG"
                and trend_power in ["STRONG_BULL", "STRONG_BEAR"]
            )

        if plan == "vip":
            return (
                confidence >= 80
                and engine_confidence >= 76
                and risk_score <= 58
                and score >= 6
            )

        if plan == "pro_2y":
            return (
                confidence >= 82
                and engine_confidence >= 78
                and risk_score <= 56
                and score >= 6
            )

        return False
    except:
        return False
# ================= EXCHANGE =================
def get_exchange(api_key, api_secret, trade_type):
    """Return the configured exchange for real auto-trading.

    Market-data fallback is handled in market_analyzer.py. Real order execution
    uses user API keys, so the exchange must match the user account. By default
    we keep Binance for backwards compatibility. Set AUTO_TRADE_EXCHANGE to
    binanceus or kucoin when selling/deploying for users whose keys are there.
    Futures execution is only enabled on exchanges where the current code has
    explicit support.
    """
    exchange_name = AUTO_TRADE_EXCHANGE or "binance"
    trade_type = str(trade_type or "spot").lower()
    default_type = "future" if trade_type == "futures" else "spot"

    if exchange_name == "kucoin":
        if trade_type == "futures":
            raise Exception("KuCoin auto futures execution is not enabled in this build. Use spot or set AUTO_TRADE_EXCHANGE=binance.")
        return ccxt.kucoin({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })

    if exchange_name in ["binanceus", "binance_us"]:
        if trade_type == "futures":
            raise Exception("Binance US does not support futures execution in this build. Use spot or set AUTO_TRADE_EXCHANGE=binance.")
        return ccxt.binanceus({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })

    return ccxt.binance({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {"defaultType": default_type}
    })

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

# ================= SIGNAL TRACKING MONITOR =================
def update_signal_outcomes():
    if not ENABLE_SIGNAL_TRACKING:
        return
    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
        SELECT id, chat_id, pair, direction, entry, tp, sl
        FROM signal_log
        WHERE status = 'SENT'
        ORDER BY sent_at ASC
        LIMIT 200
        """)
        open_signals = c.fetchall()

        for row in open_signals:
            signal_id, chat_id, pair, direction, entry, tp, sl = row
            try:
                current_price = get_live_price(pair)
                if current_price is None:
                    continue

                outcome = None
                pnl_percent = 0
                if direction == "LONG":
                    if current_price >= tp:
                        outcome = "TP_HIT"
                        pnl_percent = ((tp - entry) / entry) * 100
                    elif current_price <= sl:
                        outcome = "SL_HIT"
                        pnl_percent = ((sl - entry) / entry) * 100
                elif direction == "SHORT":
                    if current_price <= tp:
                        outcome = "TP_HIT"
                        pnl_percent = ((entry - tp) / entry) * 100
                    elif current_price >= sl:
                        outcome = "SL_HIT"
                        pnl_percent = ((entry - sl) / entry) * 100

                if outcome:
                    c.execute("""
                    UPDATE signal_log
                    SET status = 'CLOSED', outcome = %s, current_price = %s, pnl_percent = %s, closed_at = NOW()
                    WHERE id = %s
                    """, (outcome, float(current_price), round(float(pnl_percent), 4), signal_id))
                    conn.commit()

                    if SIGNAL_TRACKING_NOTIFY:
                        icon = "✅" if outcome == "TP_HIT" else "🛑"
                        clean_pnl_percent = clean_number(pnl_percent, 2)
                        what_happened = "TP Hit" if outcome == "TP_HIT" else "SL Hit" if outcome == "SL_HIT" else "Manual/Unknown Exit"
                        send(chat_id, f"""{icon} Signal Update

Pair: {pair}
Direction: {direction}
Entry: {clean_number(entry, 6)}
Exit: {clean_number(current_price, 6)}
Close Reason: {what_happened}
PNL: {clean_pnl_percent}%
PNL %: {clean_pnl_percent}%
Duration: N/A
What happened: {what_happened}
""")
                    write_log(chat_id, "INFO", f"Signal outcome {pair} {outcome} pnl={round(float(pnl_percent), 4)}%")
            except Exception as inner_e:
                log(f"Signal tracking row error id={signal_id}: {inner_e}")

        conn.close()
    except Exception as e:
        log(f"update_signal_outcomes error: {e}")


def clean_number(value, digits=4):
    try:
        value = round(float(value or 0), digits)
        if value == 0:
            value = 0.0
        return value
    except Exception:
        return value


def trade_close_reason(direction, current_price, tp, sl):
    try:
        direction = str(direction or "").upper()
        current_price = float(current_price)
        tp = float(tp)
        sl = float(sl)
        if direction == "LONG":
            if current_price >= tp:
                return "TP Hit"
            if current_price <= sl:
                return "SL Hit"
        if direction == "SHORT":
            if current_price <= tp:
                return "TP Hit"
            if current_price >= sl:
                return "SL Hit"
    except Exception:
        pass
    return "Manual/Unknown Exit"


def format_duration(created_at):
    if not created_at:
        return "N/A"
    try:
        delta = datetime.now() - created_at
        seconds = max(int(delta.total_seconds()), 0)
        hours, rem = divmod(seconds, 3600)
        minutes, _ = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except Exception:
        return "N/A"

# ================= TRADE MONITOR =================
def update_closed_trades():
    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
        SELECT id, chat_id, pair, direction, entry, tp, sl, amount, created_at
        FROM trades_log
        WHERE status = 'OPEN'
        """)
        open_trades = c.fetchall()

        for trade in open_trades:
            trade_id, chat_id, pair, direction, entry, tp, sl, amount, created_at = trade

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
                    close_reason = trade_close_reason(direction, current_price, tp, sl)
                    pnl = clean_number(pnl, 4)
                    pnl_percent = 0.0
                    try:
                        if direction == "LONG":
                            pnl_percent = ((float(current_price) - float(entry)) / float(entry)) * 100
                        elif direction == "SHORT":
                            pnl_percent = ((float(entry) - float(current_price)) / float(entry)) * 100
                    except Exception:
                        pnl_percent = 0.0
                    pnl_percent = clean_number(pnl_percent, 2)
                    duration_text = format_duration(created_at)

                    c.execute("""
                    UPDATE trades_log
                    SET status = 'CLOSED', pnl = %s, closed_at = NOW()
                    WHERE id = %s
                    """, (pnl, trade_id))

                    c.execute("""
                    UPDATE users
                    SET profit = COALESCE(profit, 0) + %s
                    WHERE chat_id = %s
                    """, (pnl, chat_id))

                    conn.commit()
                    write_log(chat_id, "INFO", f"Trade closed {pair} reason={close_reason} pnl={pnl}")

                    what_happened = close_reason if close_reason in ["TP Hit", "SL Hit"] else "Manual/Unknown Exit"
                    send(chat_id, f"""📌 Trade Closed

Pair: {pair}
Direction: {direction}
Entry: {clean_number(entry, 6)}
Exit: {clean_number(current_price, 6)}
Close Reason: {close_reason}
PNL: {pnl} USDT
PNL %: {pnl_percent}%
Duration: {duration_text}
What happened: {what_happened}
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
                from market_analyzer import TIMEFRAMES

                for symbol in get_scan_symbols():
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
                log(f"Logical invalid signal skipped: {signal_log_summary(s)}")
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
                email = type_flags[2] if len(type_flags) > 2 else ""

                if not chat_id:
                    log_unlinked_user_once(email)
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
            log_once("loop-tick", "Loop tick...")

            update_closed_trades()
            update_signal_outcomes()
            log("Closed trades and signal outcomes updated")

            signals = get_monster_signals()
            log(f"Signals fetched: {len(signals) if signals else 0}")

            users = get_users()
            log(f"Users loaded: {len(users)}")

            if not signals:
                log("No signals found")

    # ===== Notify users market is not safe now =====
                notify_users_no_signal(users)

                time.sleep(30)
                continue

            for signal in signals:
                log(f"Processing signal: {signal_log_summary(signal)}")

                for user in users:
                    chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid, *type_flags = user
                    spot_enabled = int(type_flags[0]) if len(type_flags) > 0 else 1
                    futures_enabled = int(type_flags[1]) if len(type_flags) > 1 else 1
                    email = type_flags[2] if len(type_flags) > 2 else ""

                    if not chat_id:
                        log_unlinked_user_once(email)
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
                            log(f"Elite filter rejected: {signal['pair']}")
                            continue

                    # ===== RE-CHECK FRESHNESS BEFORE SEND =====
                    # بدل ما نرفضها نهائيًا، نديها فرصة طالما لسه كويسة
                    if not signal_is_fresh(signal):
                        log(f"⚠️ price moved slightly but sending anyway: {signal['pair']}")

                    # ===== SEND SIGNAL =====
                    msg = format_signal(signal, plan)
                    sent_ok = send(chat_id, msg)

                    if sent_ok:
                        log(f"SIGNAL_SENT chat_id={chat_id} pair={signal['pair']} type={signal.get('type', 'FUTURES')}")
                        write_log(chat_id, "INFO", f"Signal sent {signal['pair']} {signal['direction']} conf={signal['confidence']}")
                        record_sent_signal(chat_id, plan, signal)

                        if plan == "trial":
                            increment_trade(chat_id)
                    else:
                        log(f"SIGNAL_SEND_FAILED chat_id={chat_id} pair={signal.get('pair')}")

                    # ===== AUTO TRADE FOR VIP =====
                    if plan in AUTO_TRADE_PLANS and bot_active == 1 and api_key and api_secret:
                        try:
                            can_trade, reason = can_trade_user(chat_id, trade_amount)
                            if not can_trade:
                                log(f"Auto trade blocked for {chat_id}: {reason}")
                                continue

                            if has_open_trade(chat_id, signal["pair"]):
                                log(f"Auto trade skipped: already open trade on {signal['pair']} for {chat_id}")
                                continue

                            if pair_in_cooldown(chat_id, signal["pair"]):
                                log(f"Auto trade skipped: cooldown active on {signal['pair']} for {chat_id}")
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
                                send(chat_id, f"""🤖 تم تنفيذ صفقة تلقائيًا

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

