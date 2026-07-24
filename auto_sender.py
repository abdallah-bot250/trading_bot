import time
import json
import secrets
import requests
import hmac
import hashlib
from urllib.parse import parse_qsl
from datetime import datetime, timedelta
from market_analyzer import (
    generate_signal,
    get_scan_symbols,
    get_signal_scan_diagnostics,
    get_top_free_signals,
    reset_signal_scan_diagnostics,
)
from ai_model import predict_trade
from spot_futures_engine import record_trade_type, type_allowed_for_user
from signal_quality_shared import safe_b_plus_eligibility
import ccxt
import os
import psycopg2
from dotenv import load_dotenv

try:
    from forex_analyzer import get_forex_signals, get_forex_scan_summary, forex_auto_trade_status
    from trader_app.services.forex_market_data import provider_configuration_status
except Exception:
    get_forex_signals = None
    get_forex_scan_summary = lambda final_signals=None: {"final_signals": int(final_signals or 0), "error": "forex_module_unavailable"}
    forex_auto_trade_status = lambda: "FOREX_AUTO_TRADE_DISABLED"
    provider_configuration_status = lambda: {"provider": "unavailable", "configured": False, "reason": "FOREX_MODULE_UNAVAILABLE"}

try:
    from trader_app.services.runtime import decrypt_text
    from trader_app.services.exchanges.registry import get_exchange_capability, normalize_exchange_key
    from trader_app.services.user_entitlements import (
        delivery_eligibility_for_signal,
        get_user_entitlements,
        log_delivery_eligibility,
    )
except Exception:
    decrypt_text = None
    get_exchange_capability = None
    normalize_exchange_key = lambda value: str(value or "bybit").strip().lower()
    delivery_eligibility_for_signal = None
    get_user_entitlements = None
    log_delivery_eligibility = None

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_TOKEN")
AUTO_TRADE_EXCHANGE = os.environ.get("AUTO_TRADE_EXCHANGE", "bybit").strip().lower()
ENABLE_SPOT_AUTO_TRADE = os.environ.get("ENABLE_SPOT_AUTO_TRADE", "false").strip().lower() in {"1", "true", "yes", "on"}
MAX_AUTO_TRADE_NOTIONAL_PERCENT = float(os.environ.get("MAX_AUTO_TRADE_NOTIONAL_PERCENT", "0.95") or 0.95)
ENABLE_SIGNAL_TRACKING = os.environ.get("ENABLE_SIGNAL_TRACKING", "true").lower() in ["1", "true", "yes", "on"]
SIGNAL_TRACKING_NOTIFY = os.environ.get("SIGNAL_TRACKING_NOTIFY", "true").lower() in ["1", "true", "yes", "on"]
SIGNAL_DEBUG_LOGS = os.environ.get("SIGNAL_DEBUG_LOGS", "").strip().lower() in {"1", "true", "yes", "debug"}
DIAGNOSTIC_LOGGING = os.environ.get("DIAGNOSTIC_LOGGING", "false").strip().lower() in {"1", "true", "yes", "on"}
NEXORA_PROOF_MODE = os.environ.get("NEXORA_PROOF_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
MIN_DAILY_SIGNAL_TARGET = int(os.environ.get("MIN_DAILY_SIGNAL_TARGET", "0") or 0)
NO_SIGNAL_STATUS_ENABLED = os.environ.get("NO_SIGNAL_STATUS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
FREE_EARN_MODE = os.environ.get("FREE_EARN_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
REWARDED_AD_PROVIDER = os.environ.get("REWARDED_AD_PROVIDER", "none").strip().lower()
FREE_SIGNALS_LIFETIME = int(os.environ.get("FREE_SIGNALS_LIFETIME", "2") or 2)
LOCKED_SIGNAL_TTL_MINUTES = int(os.environ.get("LOCKED_SIGNAL_TTL_MINUTES", "10") or 10)
FREE_UNLOCK_DEMO_MODE = os.environ.get("FREE_UNLOCK_DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
FREE_SOCIAL_UNLOCK_ENABLED = os.environ.get("FREE_SOCIAL_UNLOCK_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
ADSGRAM_REWARD_SECRET = os.environ.get("ADSGRAM_REWARD_SECRET", "").strip()
ADSGRAM_BLOCK_ID = os.environ.get("ADSGRAM_BLOCK_ID", "37291").strip()
ADSGRAM_PLATFORM_ID = os.environ.get("ADSGRAM_PLATFORM_ID", "35044").strip()
ADSGRAM_REQUIRE_SIGNATURE = os.environ.get("ADSGRAM_REQUIRE_SIGNATURE", "false").strip().lower() in {"1", "true", "yes", "on"}

# ================= CONFIG =================
MAX_DAILY_TRADES = 4
MAX_CONSECUTIVE_LOSSES = 2
MAX_DAILY_LOSS_PERCENT = 4
PAIR_COOLDOWN_MINUTES = 45
GLOBAL_LOOP_SLEEP = 80
MIN_CONFIDENCE = 66
AUTO_TRADE_PLANS = {"vip", "pro_2y"}
VIP_ALL_FOREX_CODE = "vip_all_forex"
FOREX_MARKET_TYPES = {"forex", "metal", "metals", "indices", "index", "oil", "commodities", "commodity"}
FOREX_PRODUCT_LABEL = "VIP ALL FOREX"
DUPLICATE_WINDOW_SECONDS = 300
NO_SIGNAL_NOTIFY_COOLDOWN_HOURS = int(os.environ.get("NO_SIGNAL_NOTIFY_COOLDOWN_HOURS", "6") or 6)
NO_SIGNAL_NOTIFY_COOLDOWN_MINUTES = 360  # 6 ساعات

# ===== MONSTER FILTERS =====
MAX_ENTRY_DEVIATION_PERCENT = float(os.environ.get("MAX_ENTRY_DEVIATION_PERCENT", "0.35"))
ENTRY_CHASE_TOLERANCE_PERCENT = float(os.environ.get("ENTRY_CHASE_TOLERANCE_PERCENT", "0.10"))
MAX_TP1_PROGRESS_PERCENT = float(os.environ.get("MAX_TP1_PROGRESS_PERCENT", "45"))
SIGNAL_FRESHNESS_SECONDS = 180
MAX_OPEN_TRADES_PER_USER = 2
MAX_CANDIDATES_PER_SCAN = max(1, int(os.environ.get("MAX_CANDIDATES_PER_SCAN", "6") or 6))
MAX_QUALIFIED_OPPORTUNITIES_PER_CYCLE = max(1, int(os.environ.get("MAX_QUALIFIED_OPPORTUNITIES_PER_CYCLE", str(MAX_CANDIDATES_PER_SCAN)) or MAX_CANDIDATES_PER_SCAN))
MAX_DELIVERIES_PER_CYCLE = max(1, int(os.environ.get("MAX_DELIVERIES_PER_CYCLE", "3") or 3))

# Backward-compatible alias only. This no longer follows FREE_SIGNALS_LIFETIME.
FREE_SIGNALS_LIMIT = MAX_QUALIFIED_OPPORTUNITIES_PER_CYCLE

# ===== QUALITY CONTROL =====
MAX_SIGNALS_PER_CYCLE = MAX_DELIVERIES_PER_CYCLE
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


def mask_email(value):
    email = str(value or "").strip().lower()
    if "@" not in email:
        return "unknown"
    name, domain = email.split("@", 1)
    visible = name[:2] if len(name) >= 2 else name[:1]
    return f"{visible}***@{domain}"


def mask_chat_id(value):
    raw = str(value or "").strip()
    if not raw:
        return "missing"
    return "chat_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


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
            f"display_conf={signal.get('display_confidence', signal.get('confidence'))} rr={signal.get('risk_reward')} "
            f"regime={signal.get('market_regime', signal.get('adaptive_regime', 'N/A'))} "
            f"strategy={signal.get('strategy_name', signal.get('setup_type', 'N/A'))}"
        )
    except Exception:
        return "signal_summary_unavailable"


def signal_display_confidence(signal):
    try:
        return float(signal.get("display_confidence", signal.get("confidence", 0)) or 0)
    except Exception:
        return 0.0


def _safe_float(value, default=None):
    try:
        if value in (None, "", "N/A"):
            return default
        return float(value)
    except Exception:
        return default

def qualified_opportunity_tier(signal):
    try:
        tier = str(signal.get("quality_tier") or signal.get("opportunity_tier") or "").upper()
        display_conf = signal_display_confidence(signal)
        final_score = float(signal.get("final_score", display_conf) or 0)
        rr = float(signal.get("risk_reward", 0) or 0)
        safe_bplus_ok, _ = safe_b_plus_eligibility(signal, allow_borderline_score=True)
        soft_mtf = signal.get("b_plus_mtf_path") is True or signal.get("mtf_path") == "soft_alignment" or signal.get("mtf_soft_conflict") is True
        if soft_mtf:
            if display_conf >= 70 and final_score >= 78 and rr >= 1.5:
                return "B_PLUS"
            return "B_PLUS" if safe_bplus_ok else ("WATCHLIST" if display_conf >= 64 and rr >= 1.3 else "REJECTED")
        if tier in {"A_PLUS", "A", "WATCHLIST", "REJECTED"}:
            return tier
        if tier == "B_PLUS":
            if display_conf < 70 or final_score < 78:
                return "B_PLUS" if safe_bplus_ok else ("WATCHLIST" if display_conf >= 64 and rr >= 1.3 else "REJECTED")
            return "B_PLUS"
        checklist = float(signal.get("quality_checklist_score", final_score) or 0)
        if display_conf >= 88 and final_score >= 92 and rr >= 1.8 and checklist >= 90:
            return "A_PLUS"
        if display_conf >= 80 and final_score >= 86 and rr >= 1.6:
            return "A"
        if display_conf >= 70 and final_score >= 78 and rr >= 1.5:
            return "B_PLUS"
        if display_conf >= 64 and rr >= 1.3:
            return "WATCHLIST"
        return "REJECTED"
    except Exception:
        return "REJECTED"


PLAN_BENEFITS = {
    "trial": {
        "delivery": "free_earn_or_initial_direct",
        "eligible_tiers": {"A_PLUS", "A", "B_PLUS"},
        "plan_rank": 0,
        "auto_trade": False,
        "free_lifetime_signals": FREE_SIGNALS_LIFETIME,
        "ads": "after_free_lifetime_allowance",
    },
    "basic": {
        "delivery": "direct_ad_free",
        "eligible_tiers": {"A_PLUS", "A", "B_PLUS"},
        "plan_rank": 1,
        "auto_trade": False,
        "notes": "Telegram delivery and dashboard tracking.",
    },
    "pro": {
        "delivery": "direct_ad_free",
        "eligible_tiers": {"A_PLUS", "A", "B_PLUS"},
        "plan_rank": 2,
        "auto_trade": False,
        "notes": "Advanced analysis access and broader eligible setups.",
    },
    "vip": {
        "delivery": "direct_ad_free_priority",
        "eligible_tiers": {"A_PLUS", "A", "B_PLUS"},
        "plan_rank": 3,
        "auto_trade": True,
        "elite_filter": True,
        "notes": "Elite access with auto-trading controls for eligible accounts.",
    },
    "pro_2y": {
        "delivery": "highest_direct_ad_free_access",
        "eligible_tiers": {"A_PLUS", "A", "B_PLUS"},
        "plan_rank": 4,
        "auto_trade": True,
        "highest_access": True,
        "notes": "Highest available access; never downgraded by old free-plan caps.",
    },
}


def is_qualified_opportunity(signal):
    return qualified_opportunity_tier(signal) in {"A_PLUS", "A", "B_PLUS"}


def plan_benefit(plan, key, default=None):
    try:
        return PLAN_BENEFITS.get(str(plan or "trial").strip().lower(), {}).get(key, default)
    except Exception:
        return default



def extract_actual_fill_price(order):
    try:
        if not isinstance(order, dict):
            return None
        for key in ("average", "price"):
            value = order.get(key)
            if value not in (None, "", 0, "0"):
                price = float(value)
                if price > 0:
                    return price
        cost = order.get("cost")
        filled = order.get("filled")
        if cost not in (None, "", 0, "0") and filled not in (None, "", 0, "0"):
            cost_f = float(cost)
            filled_f = float(filled)
            if cost_f > 0 and filled_f > 0:
                return cost_f / filled_f
        trades = order.get("trades") or []
        total_cost = 0.0
        total_amount = 0.0
        for trade in trades:
            if not isinstance(trade, dict):
                continue
            amount = float(trade.get("amount") or trade.get("filled") or 0)
            price = float(trade.get("price") or trade.get("average") or 0)
            if amount > 0 and price > 0:
                total_amount += amount
                total_cost += amount * price
        if total_amount > 0 and total_cost > 0:
            return total_cost / total_amount
        return None
    except Exception:
        return None


def log_unlinked_user_once(email):
    safe_email = mask_email(email)
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


def mark_telegram_connection_inactive(chat_id, reason="telegram_blocked"):
    try:
        conn = db()
        c = conn.cursor()
        c.execute(
            """
            UPDATE users
               SET bot_active = 0
             WHERE chat_id = %s
            """,
            (str(chat_id),),
        )
        conn.commit()
        conn.close()
        log(f"TELEGRAM_CONNECTION_INACTIVE chat_ref={mask_chat_id(chat_id)} reason={reason}")
    except Exception as e:
        log(f"TELEGRAM_CONNECTION_INACTIVE_FAILED chat_ref={mask_chat_id(chat_id)} error={e}")

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
            log(f"TELEGRAM_SEND_FAILED token_missing chat_ref={mask_chat_id(chat_id)}")
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
                log(f"BOT_DISCONNECTED_OR_BLOCKED chat_ref={mask_chat_id(chat_id)} status={r.status_code}")
                mark_telegram_connection_inactive(chat_id, f"status_{r.status_code}")
                try:
                    write_log(chat_id, "WARNING", f"Bot disconnected or blocked: {r.status_code}")
                except Exception:
                    pass
            else:
                log(f"TELEGRAM_SEND_FAILED chat_ref={mask_chat_id(chat_id)} status={r.status_code}")
            return False

        try:
            data = r.json()
        except Exception:
            log(f"TELEGRAM_SEND_FAILED invalid_json chat_ref={mask_chat_id(chat_id)}")
            return False

        if not data.get("ok"):
            log(f"TELEGRAM_SEND_FAILED api_not_ok chat_ref={mask_chat_id(chat_id)}")
            return False

        log(f"TELEGRAM_SEND_OK chat_ref={mask_chat_id(chat_id)}")
        return True

    except requests.exceptions.Timeout:
        log(f"TELEGRAM_SEND_FAILED timeout chat_ref={mask_chat_id(chat_id)}")
        return False
    except Exception as e:
        log(f"TELEGRAM_SEND_FAILED exception chat_ref={mask_chat_id(chat_id)} error={e}")
        return False
    


def send_unlock_prompt(chat_id, unlock_url):
    try:
        if not TOKEN:
            log(f"TELEGRAM_UNLOCK_PROMPT_FAILED token_missing chat_ref={mask_chat_id(chat_id)}")
            return False
        payload = {
            "chat_id": chat_id,
            "text": """━━━━━━━━━━━━━━━━━━
NEW NEXORA OPPORTUNITY
━━━━━━━━━━━━━━━━━━

A qualified market opportunity has passed Nexora's analysis and risk checks.

Unlock the full setup:
• Entry
• Stop Loss
• Profit Targets

Watch a short sponsored video to unlock this opportunity for free.

If market conditions change before delivery, your earned unlock will be protected for the next eligible opportunity.

Trading involves risk. Signals support decision-making and do not guarantee profits.""",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "Watch Video & Unlock", "web_app": {"url": unlock_url}}
                ]]
            }
        }
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json=payload,
            timeout=12
        )
        if r.status_code != 200:
            log(f"TELEGRAM_UNLOCK_PROMPT_FAILED chat_ref={mask_chat_id(chat_id)} status={r.status_code}")
            return False
        data = r.json()
        if not data.get("ok"):
            log(f"TELEGRAM_UNLOCK_PROMPT_FAILED api_not_ok chat_ref={mask_chat_id(chat_id)}")
            return False
        return True
    except Exception as e:
        log(f"TELEGRAM_UNLOCK_PROMPT_FAILED exception chat_ref={mask_chat_id(chat_id)} error={e}")
        return False

def free_earn_base_url():
    raw = (
        os.environ.get("BASE_URL")
        or os.environ.get("CANONICAL_DOMAIN")
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        or ""
    ).strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    return raw.rstrip("/")

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
            log("CHANNEL_SEND_FAILED api_not_ok")
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
def normalize_symbol_for_ccxt(symbol, trade_type=None, exchange_name=None):
    try:
        if not symbol:
            return symbol

        exchange_name = (exchange_name or AUTO_TRADE_EXCHANGE or "bybit").lower()
        trade_type = str(trade_type or "spot").lower()

        if "/" in symbol:
            if exchange_name == "bybit" and trade_type == "futures" and ":" not in symbol and symbol.endswith("/USDT"):
                return f"{symbol}:USDT"
            return symbol

        if symbol.endswith("USDT"):
            base = symbol[:-4]
            if exchange_name == "bybit" and trade_type == "futures":
                return f"{base}/USDT:USDT"
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

def _safe_signal_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default

def _signal_primary_target(signal):
    tp1 = _safe_signal_float(signal.get("tp1"))
    if tp1 > 0:
        return tp1
    try:
        ladder = _signal_target_ladder(signal)
        return _safe_signal_float(ladder[0])
    except Exception:
        return _safe_signal_float(signal.get("tp"))

def validate_signal_entry_freshness(signal, current_price=None, context="SEND"):
    """Return one freshness decision for Telegram sends and auto execution."""
    try:
        pair = signal.get("pair")
        direction = str(signal.get("direction") or "").upper()
        entry = _safe_signal_float(signal.get("entry"))
        tp = _safe_signal_float(signal.get("tp"))
        tp1 = _signal_primary_target(signal)
        sl = _safe_signal_float(signal.get("sl"))
        if not pair or entry <= 0 or direction not in ["LONG", "SHORT"]:
            return False, "invalid_signal_geometry", current_price

        if signal_market_bucket(signal) == "forex":
            data_timestamp = signal.get("data_timestamp") or signal.get("generated_at")
            if not data_timestamp:
                return False, "forex_data_timestamp_missing", current_price
            try:
                text = str(data_timestamp).replace("Z", "+00:00")
                ts = datetime.fromisoformat(text)
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                max_age = int(os.environ.get("FOREX_MAX_CANDLE_STALE_SECONDS", "1800") or 1800)
                age = (datetime.utcnow() - ts).total_seconds()
                if age > max_age:
                    return False, "forex_stale_data", current_price
            except Exception:
                return False, "forex_data_timestamp_invalid", current_price
            signal["live_price_checked"] = entry
            return True, "forex_data_fresh", entry

        if current_price is None:
            current_price = get_live_price(pair)
        if current_price is None or current_price <= 0:
            return False, "live_price_unavailable", current_price

        deviation = abs(current_price - entry) / entry * 100

        if deviation > MAX_ENTRY_DEVIATION_PERCENT:
            log(
                f"SIGNAL_REJECTED_STALE context={context} pair={pair} direction={direction} "
                f"entry={entry} current={current_price} deviation={round(deviation,4)}%"
            )
            return False, "price_moved_too_far_from_entry", current_price

        chase = ENTRY_CHASE_TOLERANCE_PERCENT / 100.0

        if direction == "LONG":
            if tp and current_price >= tp:
                log(f"SIGNAL_REJECTED_TARGET_ALREADY_HIT context={context} pair={pair} direction=LONG current={current_price} tp={tp}")
                return False, "target_already_hit", current_price
            if sl and current_price <= sl:
                log(f"SIGNAL_REJECTED_STOP_ALREADY_HIT context={context} pair={pair} direction=LONG current={current_price} sl={sl}")
                return False, "stop_already_hit", current_price
            if current_price > entry * (1 + chase):
                log(
                    f"SIGNAL_REJECTED_CHASE context={context} pair={pair} direction=LONG "
                    f"entry={entry} current={current_price} tolerance={ENTRY_CHASE_TOLERANCE_PERCENT}%"
                )
                return False, "long_entry_already_chased", current_price
            if tp1 and tp1 > entry and current_price > entry:
                progress = ((current_price - entry) / (tp1 - entry)) * 100
                if progress >= MAX_TP1_PROGRESS_PERCENT:
                    log(
                        f"SIGNAL_REJECTED_TP1_PROGRESS context={context} pair={pair} direction=LONG "
                        f"entry={entry} current={current_price} tp1={tp1} progress={round(progress,2)}%"
                    )
                    return False, "long_too_close_to_tp1", current_price

        if direction == "SHORT":
            if tp and current_price <= tp:
                log(f"SIGNAL_REJECTED_TARGET_ALREADY_HIT context={context} pair={pair} direction=SHORT current={current_price} tp={tp}")
                return False, "target_already_hit", current_price
            if sl and current_price >= sl:
                log(f"SIGNAL_REJECTED_STOP_ALREADY_HIT context={context} pair={pair} direction=SHORT current={current_price} sl={sl}")
                return False, "stop_already_hit", current_price
            if current_price < entry * (1 - chase):
                log(
                    f"SIGNAL_REJECTED_CHASE context={context} pair={pair} direction=SHORT "
                    f"entry={entry} current={current_price} tolerance={ENTRY_CHASE_TOLERANCE_PERCENT}%"
                )
                return False, "short_entry_already_chased", current_price
            if tp1 and tp1 < entry and current_price < entry:
                progress = ((entry - current_price) / (entry - tp1)) * 100
                if progress >= MAX_TP1_PROGRESS_PERCENT:
                    log(
                        f"SIGNAL_REJECTED_TP1_PROGRESS context={context} pair={pair} direction=SHORT "
                        f"entry={entry} current={current_price} tp1={tp1} progress={round(progress,2)}%"
                    )
                    return False, "short_too_close_to_tp1", current_price

        signal["live_price_checked"] = clean_number(current_price, 8) if "clean_number" in globals() else current_price
        return True, "fresh", current_price
    except Exception as e:
        log(f"validate_signal_entry_freshness error: {e}")
        return False, "freshness_validation_error", current_price

def signal_is_fresh(signal):
    """Reject stale/chased signals before Telegram send or auto execution."""
    try:
        ok, _, _ = validate_signal_entry_freshness(signal, context="SEND")
        return ok
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
    CREATE TABLE IF NOT EXISTS notification_state (
        id SERIAL PRIMARY KEY,
        chat_id TEXT NOT NULL,
        notification_type TEXT NOT NULL,
        plan TEXT DEFAULT '',
        idempotency_key TEXT NOT NULL,
        last_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (chat_id, notification_type, plan)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_notification_state_key ON notification_state (idempotency_key)")

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
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS timeframe TEXT")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS display_confidence REAL")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS final_score REAL")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS risk_reward REAL")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS tier TEXT")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'telegram'")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS delivery_mode TEXT")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS locked INTEGER DEFAULT 0")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS unlocked INTEGER DEFAULT 1")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS take_profits TEXT")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS stop_loss REAL")
    c.execute("ALTER TABLE signal_log ADD COLUMN IF NOT EXISTS signal_payload TEXT")

    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spot_enabled INTEGER DEFAULT 1")
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS futures_enabled INTEGER DEFAULT 1")


    c.execute("""
    CREATE TABLE IF NOT EXISTS free_signal_unlocks (
        id SERIAL PRIMARY KEY,
        token TEXT UNIQUE NOT NULL,
        chat_id TEXT NOT NULL,
        plan TEXT DEFAULT 'trial',
        signal_payload TEXT NOT NULL,
        unlocked INTEGER DEFAULT 0,
        credit_granted INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        unlocked_at TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_free_unlock_token ON free_signal_unlocks (token)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_free_unlock_chat_created ON free_signal_unlocks (chat_id, created_at)")

    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS ad_rewarded INTEGER DEFAULT 0")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS reward_provider TEXT")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS reward_payload_keys TEXT")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS rewarded_at TIMESTAMP")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS adsgram_user_id TEXT")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS adsgram_bound_at TIMESTAMP")
    c.execute("CREATE INDEX IF NOT EXISTS ix_free_unlock_adsgram_user ON free_signal_unlocks (adsgram_user_id)")

    c.execute("""
    CREATE TABLE IF NOT EXISTS free_signal_unlock_credits (
        chat_id TEXT PRIMARY KEY,
        credits INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

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


def record_sent_signal(chat_id, plan, signal, delivery_mode=None, locked=False, unlocked=True, source="telegram"):
    if not ENABLE_SIGNAL_TRACKING:
        return None
    try:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", ("signal_log",))
        columns = {(row[0] if not hasattr(row, "get") else row.get("column_name")) for row in (c.fetchall() or [])}
        tp1, tp2, _tp3 = _signal_target_ladder(signal)
        tp_values = [
            tp1,
            tp2,
        ]
        tp_values = [v for v in tp_values if v not in (None, "", "N/A")]
        if not tp_values and signal.get("tp") not in (None, "", "N/A"):
            tp_values = [signal.get("tp")]
        user_final_tp = _safe_float(tp_values[-1] if tp_values else signal.get("tp", signal.get("tp1")), 0)
        insert_columns = ["chat_id", "plan", "pair", "direction", "signal_type", "entry", "tp", "sl", "status"]
        values = [
            str(chat_id),
            str(plan or "trial"),
            signal.get("pair"),
            signal.get("direction"),
            signal.get("type", "FUTURES"),
            float(signal.get("entry", 0)),
            float(user_final_tp or 0),
            float(signal.get("sl", 0)),
            "SENT",
        ]
        optional_values = {
            "confidence": float(signal.get("display_confidence", signal.get("confidence", 0)) or 0),
            "display_confidence": float(signal.get("display_confidence", signal.get("confidence", 0)) or 0),
            "final_score": float(signal.get("final_score", signal.get("score", 0)) or 0),
            "risk_reward": float(signal.get("risk_reward", 0) or 0),
            "tier": signal.get("qualified_tier") or signal.get("tier") or signal.get("opportunity_tier"),
            "timeframe": signal.get("timeframe"),
            "source": source or "telegram",
            "delivery_mode": delivery_mode or ("free_earn" if str(plan or "").lower() == "trial" else "paid"),
            "locked": 1 if locked else 0,
            "unlocked": 1 if unlocked else 0,
            "take_profits": json.dumps(tp_values, separators=(",", ":"), default=str),
            "stop_loss": float(signal.get("sl", 0) or 0),
            "signal_payload": json.dumps(_free_signal_payload(signal), separators=(",", ":"), default=str),
        }
        for column, value in optional_values.items():
            if column in columns:
                insert_columns.append(column)
                values.append(value)
        placeholders = ", ".join(["%s"] * len(insert_columns))
        c.execute(f"""
        INSERT INTO signal_log ({", ".join(insert_columns)})
        VALUES ({placeholders})
        RETURNING id
        """, tuple(values))
        row = c.fetchone()
        conn.commit()
        conn.close()
        signal_id = row[0] if row else None
        log(f"Signal tracked id={signal_id} chat_ref={mask_chat_id(chat_id)} pair={signal.get('pair')}")
        if NEXORA_PROOF_MODE:
            log(
                f"PROOF_SIGNAL_RECORDED id={signal_id} pair={signal.get('pair')} "
                f"direction={signal.get('direction')} display_conf={signal_display_confidence(signal)}"
            )
        return signal_id
    except Exception as e:
        log(f"record_sent_signal error: {e}")
        return None



# ================= FREE EARN UNLOCK =================
def _free_signal_payload(signal):
    allowed = {
        "pair", "type", "direction", "timeframe", "entry", "tp", "tp1", "tp2", "sl",
        "display_confidence", "confidence", "risk_reward", "market_regime", "adaptive_regime",
        "strategy_name", "setup_type", "signal_quality_reason", "reason", "created_at",
        "expires_at", "risk_score", "score", "volume", "engine_confidence"
    }
    payload = {key: signal.get(key) for key in allowed if key in signal}
    try:
        tp1, tp2, _tp3 = _signal_target_ladder(signal)
        payload["tp1"] = tp1
        payload["tp2"] = tp2
        payload["tp"] = tp2
    except Exception:
        pass
    return payload

def ensure_free_earn_tables():
    conn = db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS free_signal_unlocks (
        id SERIAL PRIMARY KEY,
        token TEXT UNIQUE NOT NULL,
        chat_id TEXT NOT NULL,
        plan TEXT DEFAULT 'trial',
        signal_payload TEXT NOT NULL,
        unlocked INTEGER DEFAULT 0,
        credit_granted INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        unlocked_at TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS ix_free_unlock_token ON free_signal_unlocks (token)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_free_unlock_chat_created ON free_signal_unlocks (chat_id, created_at)")

    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS ad_rewarded INTEGER DEFAULT 0")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS reward_provider TEXT")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS reward_payload_keys TEXT")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS rewarded_at TIMESTAMP")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS adsgram_user_id TEXT")
    c.execute("ALTER TABLE free_signal_unlocks ADD COLUMN IF NOT EXISTS adsgram_bound_at TIMESTAMP")
    c.execute("CREATE INDEX IF NOT EXISTS ix_free_unlock_adsgram_user ON free_signal_unlocks (adsgram_user_id)")
    c.execute("""
    CREATE TABLE IF NOT EXISTS free_signal_unlock_credits (
        chat_id TEXT PRIMARY KEY,
        credits INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def free_unlock_credits(chat_id):
    try:
        ensure_free_earn_tables()
        conn = db()
        c = conn.cursor()
        c.execute("SELECT COALESCE(credits, 0) FROM free_signal_unlock_credits WHERE chat_id = %s", (str(chat_id),))
        row = c.fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception as e:
        log(f"FREE_UNLOCK_CREDIT_READ_FAILED chat_ref={mask_chat_id(chat_id)} error={e}")
        return 0

def add_free_unlock_credit(chat_id):
    try:
        ensure_free_earn_tables()
        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO free_signal_unlock_credits (chat_id, credits, updated_at)
            VALUES (%s, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (chat_id)
            DO UPDATE SET credits = free_signal_unlock_credits.credits + 1,
                          updated_at = CURRENT_TIMESTAMP
        """, (str(chat_id),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log(f"FREE_UNLOCK_CREDIT_GRANT_FAILED chat_ref={mask_chat_id(chat_id)} error={e}")
        return False

def consume_free_unlock_credit(chat_id):
    try:
        ensure_free_earn_tables()
        conn = db()
        c = conn.cursor()
        c.execute("SELECT COALESCE(credits, 0) FROM free_signal_unlock_credits WHERE chat_id = %s FOR UPDATE", (str(chat_id),))
        row = c.fetchone()
        credits = int(row[0]) if row else 0
        if credits <= 0:
            conn.rollback()
            conn.close()
            return False
        c.execute("""
            UPDATE free_signal_unlock_credits
            SET credits = credits - 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = %s
        """, (str(chat_id),))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log(f"FREE_UNLOCK_CREDIT_CONSUME_FAILED chat_ref={mask_chat_id(chat_id)} error={e}")
        return False

def create_pending_locked_signal(chat_id, plan, signal):
    try:
        ensure_free_earn_tables()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=max(1, LOCKED_SIGNAL_TTL_MINUTES))
        payload = json.dumps(_free_signal_payload(signal), separators=(",", ":"), default=str)
        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO free_signal_unlocks (token, chat_id, plan, signal_payload, expires_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (token, str(chat_id), str(plan or "trial"), payload, expires_at))
        conn.commit()
        conn.close()
        return token
    except Exception as e:
        log(f"FREE_LOCKED_SIGNAL_CREATE_FAILED chat_ref={mask_chat_id(chat_id)} pair={signal.get('pair')} error={e}")
        return None

def free_unlock_attempt_allowed(chat_id):
    try:
        ensure_free_earn_tables()
        conn = db()
        c = conn.cursor()
        since = datetime.now() - timedelta(minutes=2)
        c.execute("""
            SELECT COUNT(*) FROM free_signal_unlocks
            WHERE chat_id = %s AND unlocked_at >= %s
        """, (str(chat_id), since))
        row = c.fetchone()
        conn.close()
        return int(row[0] or 0) < 3
    except Exception:
        return True

def process_free_unlock_token(token, demo_allowed=False, reward_provider=None, reward_payload_keys=None):
    try:
        ensure_free_earn_tables()
        conn = db()
        c = conn.cursor()
        c.execute("""
            SELECT id, chat_id, plan, signal_payload, unlocked, credit_granted, expires_at, COALESCE(ad_rewarded, 0)
            FROM free_signal_unlocks
            WHERE token = %s
            FOR UPDATE
        """, (str(token),))
        row = c.fetchone()
        if not row:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "invalid_token"}
        unlock_id, chat_id, plan, payload, unlocked, credit_granted, expires_at, ad_rewarded = row
        if int(unlocked or 0) == 1:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "already_used"}
        if reward_provider == "adsgram" and int(ad_rewarded or 0) == 1:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "already_rewarded"}
        if datetime.now() > expires_at:
            if int(credit_granted or 0) != 1:
                c.execute("UPDATE free_signal_unlocks SET credit_granted = 1 WHERE id = %s", (unlock_id,))
                conn.commit()
                conn.close()
                add_free_unlock_credit(chat_id)
                log(f"FREE_UNLOCK_CREDIT_GRANTED_STALE_SIGNAL chat_ref={mask_chat_id(chat_id)}")
                return {"ok": False, "reason": "expired_credit_granted"}
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "expired"}
        if not free_unlock_attempt_allowed(chat_id):
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "rate_limited"}
        if REWARDED_AD_PROVIDER == "none" and not demo_allowed:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "ads_not_configured"}
        if reward_provider:
            is_rewarded_ad = 1 if reward_provider == "adsgram" else 0
            c.execute("""
                UPDATE free_signal_unlocks
                SET ad_rewarded = %s,
                    reward_provider = %s,
                    reward_payload_keys = %s,
                    rewarded_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (is_rewarded_ad, str(reward_provider), ",".join(reward_payload_keys or []), unlock_id))
        if demo_allowed:
            log("FREE_UNLOCK_DEMO_USED")
        signal = json.loads(payload or "{}")
        if not signal_is_fresh(signal):
            if int(credit_granted or 0) != 1:
                c.execute("UPDATE free_signal_unlocks SET credit_granted = 1 WHERE id = %s", (unlock_id,))
                conn.commit()
                conn.close()
                add_free_unlock_credit(chat_id)
                log(f"FREE_UNLOCK_CREDIT_GRANTED_STALE_SIGNAL chat_ref={mask_chat_id(chat_id)}")
                return {"ok": False, "reason": "stale_credit_granted"}
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "stale"}
        msg = format_signal(signal, plan)
        sent_ok = send(chat_id, msg)
        if not sent_ok:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "telegram_send_failed"}
        c.execute("""
            UPDATE free_signal_unlocks
            SET unlocked = 1,
                unlocked_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (unlock_id,))
        conn.commit()
        conn.close()
        record_sent_signal(chat_id, plan, signal, delivery_mode="free_earn", locked=True, unlocked=True)
        increment_trade(chat_id)
        write_log(chat_id, "INFO", f"Free earned signal unlocked {signal.get('pair')} {signal.get('direction')}")
        log(f"FREE_SIGNAL_UNLOCKED_AND_SENT chat_ref={mask_chat_id(chat_id)} pair={signal.get('pair')}")
        return {"ok": True, "reason": "sent"}
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        log(f"FREE_UNLOCK_PROCESS_FAILED token_present={bool(token)} error={e}")
        return {"ok": False, "reason": "error"}






def process_social_unlock_token(token):
    if not FREE_SOCIAL_UNLOCK_ENABLED:
        log("FREE_SOCIAL_UNLOCK_REJECTED reason=disabled")
        return {"ok": False, "reason": "social_unlock_disabled"}
    log("FREE_SOCIAL_UNLOCK_REQUESTED token_present=True")
    result = process_free_unlock_token(
        token,
        demo_allowed=False,
        reward_provider="social_follow",
        reward_payload_keys=["facebook", "instagram", "telegram"],
    )
    if result.get("ok"):
        log("FREE_SOCIAL_UNLOCK_SENT")
    elif result.get("reason") in {"expired_credit_granted", "stale_credit_granted"}:
        log("FREE_SOCIAL_UNLOCK_CREDIT_GRANTED")
    else:
        log(f"FREE_SOCIAL_UNLOCK_REJECTED reason={result.get('reason')}")
    return result
def verify_telegram_webapp_init_data(init_data):
    if not TOKEN:
        return False, "", "telegram_token_missing"
    if not init_data:
        return False, "", "missing_init_data"
    try:
        parsed = dict(parse_qsl(str(init_data), keep_blank_values=True))
        received_hash = parsed.pop("hash", "")
        if not received_hash:
            return False, "", "missing_hash"
        data_check = "\n".join(f"{key}={parsed[key]}" for key in sorted(parsed))
        secret_key = hmac.new(b"WebAppData", TOKEN.encode("utf-8"), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, received_hash):
            return False, "", "bad_signature"
        user_data = json.loads(parsed.get("user") or "{}")
        user_id = str(user_data.get("id") or "").strip()
        if not user_id:
            return False, "", "missing_user_id"
        return True, user_id, "ok"
    except Exception as e:
        log(f"ADSGRAM_BIND_VERIFY_FAILED error={e}")
        return False, "", "verify_error"

def bind_adsgram_user_to_unlock(token, adsgram_user_id, init_data):
    try:
        ensure_free_earn_tables()
        token = str(token or "").strip()
        requested_user_id = str(adsgram_user_id or "").strip()
        verified, verified_user_id, verify_reason = verify_telegram_webapp_init_data(init_data)
        if not token:
            return {"ok": False, "reason": "missing_token"}
        if not requested_user_id:
            return {"ok": False, "reason": "missing_user_id"}
        if not verified:
            log(f"ADSGRAM_BIND_REJECTED reason={verify_reason}")
            return {"ok": False, "reason": verify_reason}
        if requested_user_id != verified_user_id:
            log("ADSGRAM_BIND_REJECTED reason=user_id_mismatch")
            return {"ok": False, "reason": "user_id_mismatch"}

        conn = db()
        c = conn.cursor()
        c.execute("""
            SELECT id, chat_id, unlocked, credit_granted, expires_at, COALESCE(ad_rewarded, 0)
            FROM free_signal_unlocks
            WHERE token = %s
            FOR UPDATE
        """, (token,))
        row = c.fetchone()
        if not row:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "invalid_token"}
        unlock_id, chat_id, unlocked, credit_granted, expires_at, ad_rewarded = row
        if int(unlocked or 0) == 1 or int(ad_rewarded or 0) == 1:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "already_used"}
        if datetime.now() > expires_at:
            conn.rollback()
            conn.close()
            return {"ok": False, "reason": "expired"}
        if str(chat_id) != verified_user_id:
            conn.rollback()
            conn.close()
            log("ADSGRAM_BIND_REJECTED reason=token_user_mismatch")
            return {"ok": False, "reason": "token_user_mismatch"}

        c.execute("""
            UPDATE free_signal_unlocks
            SET adsgram_user_id = NULL,
                adsgram_bound_at = NULL
            WHERE adsgram_user_id = %s
              AND token <> %s
              AND COALESCE(unlocked, 0) = 0
              AND COALESCE(ad_rewarded, 0) = 0
        """, (verified_user_id, token))
        c.execute("""
            UPDATE free_signal_unlocks
            SET adsgram_user_id = %s,
                adsgram_bound_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (verified_user_id, unlock_id))
        conn.commit()
        conn.close()
        log("ADSGRAM_USER_BOUND user_id_present=True chat_id_present=True")
        return {"ok": True, "reason": "bound"}
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        log(f"ADSGRAM_BIND_FAILED error={e}")
        return {"ok": False, "reason": "error"}

def adsgram_token_for_user(adsgram_user_id):
    try:
        ensure_free_earn_tables()
        conn = db()
        c = conn.cursor()
        c.execute("""
            SELECT token
            FROM free_signal_unlocks
            WHERE adsgram_user_id = %s
              AND COALESCE(unlocked, 0) = 0
              AND COALESCE(ad_rewarded, 0) = 0
              AND expires_at >= %s
            ORDER BY adsgram_bound_at DESC NULLS LAST, created_at DESC
            LIMIT 1
        """, (str(adsgram_user_id or "").strip(), datetime.now()))
        row = c.fetchone()
        conn.close()
        return str(row[0]) if row else ""
    except Exception as e:
        log(f"ADSGRAM_TOKEN_LOOKUP_FAILED user_id_present={bool(adsgram_user_id)} error={e}")
        return ""

def adsgram_signature_status():
    if not ADSGRAM_REQUIRE_SIGNATURE:
        return True, "signature_not_required"
    # AdsGram signature documentation was not provided in this build.
    # Keep this closed when required instead of inventing an unsafe verifier.
    return False, "signature_verification_not_configured"

def process_adsgram_reward(token=None, payload_keys=None, adsgram_user_id=None):
    safe_keys = sorted({str(k) for k in (payload_keys or []) if str(k).lower() not in {"secret", "signature", "hash", "token"}})
    log(f"ADSGRAM_REWARD_RECEIVED user_id_present={bool(adsgram_user_id)} token_present={bool(token)} keys={safe_keys}")
    if REWARDED_AD_PROVIDER != "adsgram":
        log("ADSGRAM_REWARD_REJECTED reason=provider_not_adsgram")
        return {"ok": False, "reason": "provider_not_adsgram"}
    sig_ok, sig_reason = adsgram_signature_status()
    if not sig_ok:
        log(f"ADSGRAM_REWARD_REJECTED reason={sig_reason}")
        return {"ok": False, "reason": sig_reason}
    if not adsgram_user_id:
        log("ADSGRAM_REWARD_REJECTED reason=missing_user_id")
        return {"ok": False, "reason": "missing_user_id"}
    mapped_token = adsgram_token_for_user(adsgram_user_id)
    if not mapped_token:
        log("ADSGRAM_REWARD_REJECTED reason=unknown_user_id")
        return {"ok": False, "reason": "unknown_user_id"}
    if token and str(token) != str(mapped_token):
        log("ADSGRAM_REWARD_REJECTED reason=token_user_mismatch")
        return {"ok": False, "reason": "token_user_mismatch"}
    token = mapped_token
    log("ADSGRAM_REWARD_ACCEPTED")
    result = process_free_unlock_token(
        token,
        demo_allowed=False,
        reward_provider="adsgram",
        reward_payload_keys=safe_keys,
    )
    if result.get("ok"):
        log("ADSGRAM_UNLOCK_SENT")
    elif result.get("reason") in {"expired_credit_granted", "stale_credit_granted"}:
        log("ADSGRAM_UNLOCK_CREDIT_GRANTED")
    else:
        log(f"ADSGRAM_REWARD_REJECTED reason={result.get('reason')}")
    return result

def maybe_handle_free_earn_delivery(chat_id, plan, trades, signal):
    if str(plan or "trial").lower() != "trial":
        return "not_free"
    if not FREE_EARN_MODE:
        return "free_earn_disabled"
    if is_trial_allowed(trades):
        return "direct_free"
    credits = free_unlock_credits(chat_id)
    if credits > 0 and consume_free_unlock_credit(chat_id):
        return "credit_used"
    token = create_pending_locked_signal(chat_id, plan, signal)
    if not token:
        return "lock_create_failed"
    base_url = free_earn_base_url()
    if not base_url:
        log(f"FREE_LOCKED_SIGNAL_NO_BASE_URL chat_ref={mask_chat_id(chat_id)}")
        return "lock_no_base_url"
    unlock_url = f"{base_url}/unlock-signal/{token}"
    if send_unlock_prompt(chat_id, unlock_url):
        log(f"FREE_LOCKED_SIGNAL_CREATED chat_ref={mask_chat_id(chat_id)} pair={signal.get('pair')} ttl_minutes={LOCKED_SIGNAL_TTL_MINUTES}")
        write_log(chat_id, "INFO", f"Locked premium signal ready {signal.get('pair')}")
        return "locked_prompt_sent"
    return "lock_prompt_failed"

# ================= USERS =================
def get_users():
    conn = db()
    c = conn.cursor()

    c.execute("""
    SELECT id, chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid,
           COALESCE(spot_enabled, 1), COALESCE(futures_enabled, 1), email,
           COALESCE(spot_auto_trade_enabled, 0), COALESCE(futures_auto_trade_enabled, 0),
           COALESCE(stop_loss_required, 1)
    FROM users
    """)

    users = c.fetchall()
    conn.close()
    return users


def ensure_user_subscriptions_table(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        product_code TEXT NOT NULL,
        display_name TEXT,
        market_type TEXT,
        status TEXT DEFAULT 'active',
        is_paid INTEGER DEFAULT 0,
        starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NULL,
        payment_provider TEXT,
        payment_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


def has_active_product_subscription(user_id, product_code):
    if not user_id or not product_code:
        return False
    conn = None
    try:
        conn = db()
        ensure_user_subscriptions_table(conn)
        c = conn.cursor()
        c.execute("""
            SELECT 1
            FROM user_subscriptions
            WHERE user_id = %s
              AND product_code = %s
              AND status = 'active'
              AND COALESCE(is_paid, 0) = 1
              AND (expires_at IS NULL OR expires_at >= NOW())
            LIMIT 1
        """, (user_id, product_code))
        return c.fetchone() is not None
    except Exception as e:
        log(f"SUBSCRIPTION_CAPABILITY_CHECK_FAILED user_id={user_id} product={product_code} error={e}")
        return False
    finally:
        if conn:
            conn.close()


def signal_market_bucket(signal):
    market_type = str(
        signal.get("market_type")
        or signal.get("market")
        or signal.get("asset_class")
        or ""
    ).strip().lower()
    if market_type in FOREX_MARKET_TYPES:
        return "forex"

    pair = str(signal.get("pair") or signal.get("symbol") or "").upper().replace("/", "")
    forex_prefixes = ("EUR", "GBP", "JPY", "AUD", "NZD", "CHF", "CAD")
    if pair.startswith(("XAU", "XAG")) or pair in {"US30", "NAS100", "SPX500", "GER40", "UK100", "WTI", "BRENT", "OIL"}:
        return "forex"
    if pair.endswith("USD") and not pair.endswith("USDT") and pair[:3] in forex_prefixes:
        return "forex"
    return "crypto"


def delivery_product_for_signal(user_info, signal):
    market = signal_market_bucket(signal)
    if delivery_eligibility_for_signal:
        try:
            entitlements, allowed, reason = delivery_eligibility_for_signal(user=user_info, signal_market=market)
            if log_delivery_eligibility:
                log_delivery_eligibility(user_info, market, allowed, reason)
            if market == "forex":
                return VIP_ALL_FOREX_CODE, allowed, reason
            return str(entitlements.get("crypto", {}).get("plan_code") or user_info.get("plan") or "trial").strip().lower(), allowed, reason
        except Exception as e:
            log(f"DELIVERY_ELIGIBILITY_SERVICE_FAILED market={market} reason={e}")
    if market == "forex":
        if has_active_product_subscription(user_info.get("user_id"), VIP_ALL_FOREX_CODE):
            return VIP_ALL_FOREX_CODE, True, "eligible"
        return VIP_ALL_FOREX_CODE, False, "vip_all_forex_required"
    return str(user_info.get("plan") or "trial").strip().lower(), True, "eligible"

# ================= VALIDATION =================
def valid_signal(signal):
    try:
        display_conf = signal_display_confidence(signal)
        safe_bplus_ok, _ = safe_b_plus_eligibility(signal, allow_borderline_score=True)
        return (
            signal
            and signal.get("pair")
            and signal.get("direction") in ["LONG", "SHORT"]
            and signal.get("entry") is not None
            and signal.get("tp") is not None
            and signal.get("sl") is not None
            and (
                display_conf >= MIN_CONFIDENCE
                or safe_bplus_ok
            )
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

def _compact_trade_reason(signal):
    reason = str(signal.get("signal_quality_reason") or signal.get("reason") or "").strip()
    if not reason:
        reason = "Trend alignment + MTF confirmation + volume support."
    reason = " ".join(reason.split())
    max_length = 320 if signal_market_bucket(signal) == "forex" else 140
    if len(reason) > max_length:
        reason = reason[: max_length - 3].rstrip() + "..."
    return reason


# ================= FORMAT =================
def _coin_badge(pair):
    try:
        symbol = str(pair or "").upper().replace("/", "")
        for suffix in ("USDT", "USDC", "BUSD", "USD"):
            if symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
                break
        badges = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "BNB": "BNB",
            "SOL": "Solana",
            "XRP": "XRP",
            "ADA": "Cardano",
            "DOGE": "Dogecoin",
            "AVAX": "Avalanche",
            "LINK": "Chainlink",
            "DOT": "Polkadot",
            "LTC": "Litecoin",
            "BCH": "Bitcoin Cash",
            "TRX": "TRON",
            "TON": "Toncoin",
            "SUI": "Sui",
            "NEAR": "NEAR",
            "UNI": "Uniswap",
            "AAVE": "Aave",
        }
        return badges.get(symbol, symbol or "Crypto")
    except Exception:
        return "Crypto"


def format_signal(signal, plan=None):
    tp1, tp2, _tp3 = _signal_target_ladder(signal)
    confidence = signal.get("display_confidence", signal.get("confidence"))
    pair = signal.get("pair", "N/A")
    coin_badge = _coin_badge(pair)
    direction = str(signal.get("direction", "N/A")).upper()
    direction_label = "BUY" if direction == "LONG" else "SELL" if direction == "SHORT" else "SETUP"
    rr = signal.get("risk_reward")
    setup = signal.get("strategy_name") or signal.get("setup_type") or signal.get("market_regime") or signal.get("adaptive_regime")
    why = _compact_trade_reason(signal)
    setup_line = f"\nStrategy: {setup}" if setup else ""
    confidence_line = f"{confidence}%" if confidence not in (None, "", "N/A") else "N/A"
    risk_value = signal.get("risk_percent") or signal.get("risk") or signal.get("recommended_risk") or "1%"

    market_bucket = signal_market_bucket(signal)
    market_details = ""
    risk_label = "Crypto and derivatives trading are risky. Not financial advice."
    if market_bucket == "forex":
        spread_value = signal.get("spread")
        spread_text = "Unavailable" if signal.get("spread_status") == "Unavailable" or spread_value in (None, "", "N/A") else f"{spread_value} pips"
        market_data = signal.get("market_data_provider") or signal.get("provider") or "N/A"
        news_provider = signal.get("news_provider") or "Trading Economics"
        market_details = (
            f"\nSession: {signal.get('session', 'N/A')}"
            f"\nBid/Ask: {signal.get('bid', 'N/A')} / {signal.get('ask', 'N/A')}"
            f"\nSpread: {spread_text}"
            f"\n4H/1H: {signal.get('trend_4h', 'N/A')} / {signal.get('trend_1h', 'N/A')}"
            f"\nSetup: {signal.get('setup_type') or signal.get('setup', 'N/A')}"
            f"\nRSI/MACD/ATR: {signal.get('rsi', 'N/A')} / {signal.get('macd', 'N/A')} / {signal.get('atr', 'N/A')}"
            f"\nS/R: {signal.get('support', 'N/A')} / {signal.get('resistance', 'N/A')}"
            f"\nNews: {news_provider} ({signal.get('news_status', 'N/A')})"
            f"\nMarket Data: {market_data} | {signal.get('data_timestamp_utc') or signal.get('data_timestamp', 'N/A')}"
            f"\nSignal ID: {signal.get('signal_id', 'N/A')}"
        )
        risk_label = "Forex, metals, oil, and indices involve substantial risk. Verify broker spread and size positions conservatively. Not financial advice."
    elif str(signal.get("type", "")).upper() == "FUTURES" and signal.get("futures_macro_trend"):
        market_details = (
            f"\n4H Trend: {signal.get('futures_macro_trend', 'N/A')}"
            f"\n1H Bias: {signal.get('futures_1h_bias', 'N/A')}"
            f"\n30m Setup: {signal.get('futures_30m_setup', 'N/A')}"
            f"\n15m Trigger: {signal.get('futures_15m_trigger', 'N/A')}"
            f"\nEntry Range: {signal.get('entry_range', signal.get('entry', 'N/A'))}"
            f"\nStop Reason: {signal.get('stop_loss_reason', 'Structure + ATR buffer')}"
            f"\nCancel If: {signal.get('cancel_condition', 'Setup expires or 15m structure breaks')}"
            f"\nExpiry: {signal.get('signal_expiry_minutes', 'N/A')} minutes"
            f"\nLeverage: {signal.get('recommended_leverage', 'Conservative leverage only')}"
        )

    return f"""NEXORA AI SIGNAL

{coin_badge} | {pair}
Mode: {signal.get('type', 'FUTURES')}
Direction: {direction_label} {direction}
TF: {signal.get('timeframe', 'N/A')}{market_details}

Entry: {signal.get('entry', 'N/A')}
TP1: {tp1}
TP2: {tp2}
{("TP3: " + str(signal.get('tp3'))) if market_bucket == "forex" and signal.get('tp3') not in (None, "", "N/A") else ""}
SL: {signal.get('sl', 'N/A')}

Confidence: {confidence_line}
Risk: {risk_value}
RR: {rr if rr not in (None, '', 'N/A') else 'N/A'}{setup_line}

Why this trade:
{why}

Manage:
Move SL to breakeven after TP1 only after price confirms and according to your own risk plan.
{("Cancel: " + str(signal.get('cancel_condition'))) if market_bucket == "forex" and signal.get('cancel_condition') else ""}

Risk warning: {risk_label}"""


# ================= ACCESS HELPERS =================
def is_trial_allowed(trades):
    return (trades or 0) < FREE_SIGNALS_LIFETIME

def is_paid_plan_active(plan, expiry, is_paid):
    plan = str(plan or "trial").strip().lower()
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
        plan = str(plan or "trial").strip().lower()
        risk_score = float(signal.get("risk_score", 50))
        tier = qualified_opportunity_tier(signal)

        # This is a final global risk gate, not a subscription feature gate.
        if risk_score >= 72:
            return False

        benefits = PLAN_BENEFITS.get(plan)
        if not benefits:
            return False

        # pro_2y is the highest access tier. It still respects all global safety
        # gates above, but it must not be narrowed by legacy premium thresholds.
        if benefits.get("highest_access"):
            return tier in benefits["eligible_tiers"]

        return tier in benefits["eligible_tiers"]
    except:
        return False


def signal_plan_block_reason(plan, signal):
    try:
        display_confidence = signal_display_confidence(signal)
        engine_confidence = float(signal.get("engine_confidence", display_confidence))
        risk_score = float(signal.get("risk_score", 50))
        score = abs(float(signal.get("score", 0)))
        timeframe = signal.get("timeframe", "5m")
        volume = signal.get("volume", "WEAK")
        trend_power = signal.get("trend_power", "MIXED")

        tier = qualified_opportunity_tier(signal)
        if risk_score >= 72:
            return f"global_risk_filter display_conf={display_confidence} engine_conf={engine_confidence} risk_score={risk_score} score={score}"
        if tier not in PLAN_BENEFITS.get(str(plan or "trial").lower(), {}).get("eligible_tiers", set()):
            return f"tier_not_eligible tier={tier} display_conf={display_confidence} risk_score={risk_score} score={score}"
        return f"eligible tier={tier} display_conf={display_confidence} risk_score={risk_score} score={score}"
    except Exception as e:
        return f"plan_filter_error error={e}"


def log_signal_scan_summary(final_count):
    try:
        summary = get_signal_scan_diagnostics(final_count)
        scan_attempts = int(summary.get("scan_attempts", summary.get("scanned", 0)) or 0)
        rejection_keys = [
            "rejected_low_volatility", "rejected_mtf", "rejected_liquidity",
            "rejected_fake_breakout", "rejected_quality", "rejected_entry",
        ]
        rejection_total = sum(int(summary.get(key, 0) or 0) for key in rejection_keys)
        log(
            "SIGNAL_SCAN_SUMMARY "
            f"unique_symbols_scanned={summary.get('unique_symbols_scanned', summary.get('scanned', 0))} "
            f"scan_attempts={scan_attempts} "
            f"scanned={summary.get('scanned', 0)} "
            f"playbooks_selected={summary.get('playbooks_selected', 0)} "
            f"setups_confirmed={summary.get('setups_confirmed', 0)} "
            f"entry_confirmations_passed={summary.get('entry_confirmations_passed', 0)} "
            f"candidates_built={summary.get('candidates_built', 0)} "
            f"finalized_candidates={summary.get('finalized_candidates', 0)} "
            f"rejected_low_volatility={summary.get('rejected_low_volatility', 0)} "
            f"rejected_mtf={summary.get('rejected_mtf', 0)} "
            f"rejected_liquidity={summary.get('rejected_liquidity', 0)} "
            f"rejected_fake_breakout={summary.get('rejected_fake_breakout', 0)} "
            f"rejected_quality={summary.get('rejected_quality', 0)} "
            f"rejected_entry={summary.get('rejected_entry', 0)} "
            f"mtf_hard_conflict={summary.get('mtf_hard_conflict', 0)} "
            f"mtf_soft_conflict={summary.get('mtf_soft_conflict', 0)} "
            f"entry_missing={summary.get('entry_missing', 0)} "
            f"entry_stale={summary.get('entry_stale', 0)} "
            f"liquidity_invalid={summary.get('liquidity_invalid', 0)} "
            f"quality_score={summary.get('quality_score', 0)} "
            f"late_entry={summary.get('late_entry', 0)} "
            f"risk_reward={summary.get('risk_reward', 0)} "
            f"watchlist={summary.get('watchlist', 0)} "
            f"qualified_b_plus={summary.get('qualified_b_plus', 0)} "
            f"qualified_a={summary.get('qualified_a', 0)} "
            f"qualified_a_plus={summary.get('qualified_a_plus', 0)} "
            f"free_earn_locks_created={summary.get('free_earn_locks_created', 0)} "
            f"paid_deliveries={summary.get('paid_deliveries', 0)} "
            f"rejection_total={rejection_total} "
            f"final_signals={summary.get('final_signals', final_count)}"
        )
        if MIN_DAILY_SIGNAL_TARGET > 0 and int(final_count or 0) < MIN_DAILY_SIGNAL_TARGET:
            log(f"SIGNAL_SUPPLY_LOW target={MIN_DAILY_SIGNAL_TARGET} actual={int(final_count or 0)}")
        return summary
    except Exception as e:
        log(f"SIGNAL_SCAN_SUMMARY_ERROR error={e}")
        return {}


def log_forex_scan_summary(final_count=None):
    try:
        summary = get_forex_scan_summary(final_count)
        log(
            "FOREX_SCAN_SUMMARY "
            f"symbols_requested={summary.get('symbols_requested', summary.get('symbols_scanned', 0))} "
            f"symbols_with_data={summary.get('symbols_with_data', 0)} "
            f"symbols_scanned={summary.get('symbols_scanned', 0)} "
            f"timeframes_scanned={summary.get('timeframes_scanned', 0)} "
            f"data_failures={summary.get('data_failures', 0)} "
            f"requests_failed={summary.get('requests_failed', summary.get('data_failures', 0))} "
            f"disabled={summary.get('disabled', False)} "
            f"disabled_reason={summary.get('disabled_reason', '')} "
            f"rejected_volatility={summary.get('rejected_volatility', 0)} "
            f"rejected_spread={summary.get('rejected_spread', 0)} "
            f"rejected_news={summary.get('rejected_news', 0)} "
            f"rejected_news_provider={summary.get('rejected_news_provider', 0)} "
            f"rejected_real_spread={summary.get('rejected_real_spread', 0)} "
            f"news_provider={summary.get('news_provider', '')} "
            f"news_provider_configured={summary.get('news_provider_configured', False)} "
            f"real_spread_required={summary.get('real_spread_required', False)} "
            f"rejected_quality={summary.get('rejected_quality', 0)} "
            f"passed_candidates={summary.get('passed_candidates', 0)} "
            f"final_signals={summary.get('final_signals', final_count or 0)} "
            f"deliveries={summary.get('deliveries', 0)} "
            f"failure_reasons={json.dumps(summary.get('failure_reasons', {}), sort_keys=True)}"
        )
        return summary
    except Exception as e:
        log(f"FOREX_SCAN_SUMMARY_ERROR error={e}")
        return {}


def log_delivery_summary(total_signals, total_users, sent, locked, blocked):
    try:
        log(
            "DELIVERY_SUMMARY "
            f"signals={int(total_signals or 0)} users={int(total_users or 0)} "
            f"sent={int(sent or 0)} locked={int(locked or 0)} blocked={int(blocked or 0)}"
        )
    except Exception:
        pass


def log_plan_delivery_diag(email, plan, chat_id, eligible, reason_if_not_sent):
    try:
        log(
            "PLAN_DELIVERY_DIAG "
            f"email={mask_email(email)} "
            f"plan={plan or ''} "
            f"chat_id_exists={bool(chat_id)} "
            f"eligible={bool(eligible)} "
            f"reason_if_not_sent={reason_if_not_sent or ''}"
        )
    except Exception:
        pass


def log_pro_2y_block(plan, reason):
    try:
        if str(plan or "").strip().lower() == "pro_2y":
            log(f"PRO_2Y_DELIVERY_BLOCKED reason={reason}")
    except Exception:
        pass


def unpack_delivery_user(user):
    user_id, chat_id, plan, expiry, api_key, api_secret, trade_amount, trade_type, trades, profit, bot_active, is_paid, *type_flags = user
    return {
        "user_id": user_id,
        "chat_id": chat_id,
        "plan": plan,
        "expiry": expiry,
        "api_key": api_key,
        "api_secret": api_secret,
        "trade_amount": trade_amount,
        "trade_type": trade_type,
        "trades": trades,
        "profit": profit,
        "bot_active": bot_active,
        "is_paid": is_paid,
        "spot_enabled": int(type_flags[0]) if len(type_flags) > 0 else 1,
        "futures_enabled": int(type_flags[1]) if len(type_flags) > 1 else 1,
        "email": type_flags[2] if len(type_flags) > 2 else "",
        "spot_auto_trade_enabled": int(type_flags[3]) if len(type_flags) > 3 else 0,
        "futures_auto_trade_enabled": int(type_flags[4]) if len(type_flags) > 4 else 0,
        "stop_loss_required": int(type_flags[5]) if len(type_flags) > 5 else 1,
    }


def delivery_access_status(user_info, qualified_opportunity_available=False):
    if get_user_entitlements:
        try:
            ent = get_user_entitlements(user=user_info)
            if not ent.get("telegram_linked"):
                return False, "missing_chat_id"
            crypto = ent.get("crypto", {})
            if str(crypto.get("plan_code") or "").lower() == "trial":
                if not is_trial_allowed(user_info.get("trades")):
                    if FREE_EARN_MODE and qualified_opportunity_available:
                        return True, "free_earn_lane"
                    return False, "trial_limit_reached"
                return True, "eligible"
            if crypto.get("active"):
                return True, "eligible"
            return False, crypto.get("status") or "subscription_inactive"
        except Exception as e:
            log(f"DELIVERY_ACCESS_SERVICE_FAILED reason={e}")
    plan = str(user_info.get("plan") or "trial").strip().lower()
    if not user_info.get("chat_id"):
        return False, "missing_chat_id"
    if plan == "trial":
        if not is_trial_allowed(user_info.get("trades")):
            if FREE_EARN_MODE and qualified_opportunity_available:
                return True, "free_earn_lane"
            return False, "trial_limit_reached"
        return True, "eligible"
    if not is_paid_plan_active(plan, user_info.get("expiry"), user_info.get("is_paid")):
        return False, "subscription_inactive"
    return True, "eligible"
# ================= EXCHANGE =================
def safe_decrypt_credential(value):
    if not value:
        return ""
    if decrypt_text:
        try:
            decrypted = decrypt_text(value)
            if decrypted:
                return decrypted
        except Exception:
            pass
    return value


def record_execution_event(user_info, signal, status, reason, connection=None, order_id=None, actual_entry=None, payload=None):
    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
        INSERT INTO execution_log (
            user_id, user_email, exchange, connection_id, symbol, direction,
            trade_type, mode, requested_entry, actual_entry, status, reason, order_id, payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_info.get("user_id"),
            user_info.get("email"),
            (connection or {}).get("exchange"),
            (connection or {}).get("id"),
            signal.get("pair"),
            signal.get("direction"),
            "futures" if signal.get("type") == "FUTURES" else "spot",
            (connection or {}).get("mode"),
            signal.get("entry"),
            actual_entry,
            status,
            reason,
            order_id,
            json.dumps(payload or {}, default=str)[:4000],
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        if SIGNAL_DEBUG_LOGS:
            log(f"EXECUTION_LOG_WRITE_FAILED reason={e}")


def load_primary_auto_trade_connection(user_info, signal_trade_type):
    """Return a safe primary exchange connection or None.

    This is additive: legacy Bybit keys still work when no multi-exchange
    connection exists. Spot execution remains disabled unless protected exits
    are explicitly supported.
    """
    email = user_info.get("email")
    user_id = user_info.get("user_id")
    if not email and not user_id:
        return None, "missing_user"
    try:
        conn = db()
        c = conn.cursor()
        if user_id:
            c.execute("""
            SELECT ec.id, ec.exchange, ec.mode, ec.api_key_encrypted, ec.api_secret_encrypted,
                   ec.passphrase_encrypted, ec.auto_trade_enabled, ec.primary_for_futures,
                   ats.emergency_stop, ats.mode AS risk_mode, ats.risk_per_trade
            FROM exchange_connections ec
            LEFT JOIN auto_trade_settings ats ON ats.user_id = ec.user_id
            WHERE ec.user_id = %s
              AND ec.deleted_at IS NULL
              AND COALESCE(ec.auto_trade_enabled, 0) = 1
              AND (%s = 'futures' AND COALESCE(ec.primary_for_futures, 0) = 1)
            ORDER BY ec.last_tested_at DESC NULLS LAST, ec.created_at DESC
            LIMIT 1
            """, (user_id, signal_trade_type))
        else:
            c.execute("""
            SELECT ec.id, ec.exchange, ec.mode, ec.api_key_encrypted, ec.api_secret_encrypted,
                   ec.passphrase_encrypted, ec.auto_trade_enabled, ec.primary_for_futures,
                   ats.emergency_stop, ats.mode AS risk_mode, ats.risk_per_trade
            FROM exchange_connections ec
            LEFT JOIN auto_trade_settings ats ON ats.user_id = ec.user_id
            WHERE LOWER(ec.user_email) = LOWER(%s)
              AND ec.deleted_at IS NULL
              AND COALESCE(ec.auto_trade_enabled, 0) = 1
              AND (%s = 'futures' AND COALESCE(ec.primary_for_futures, 0) = 1)
            ORDER BY ec.last_tested_at DESC NULLS LAST, ec.created_at DESC
            LIMIT 1
            """, (email, signal_trade_type))
        row = c.fetchone()
        conn.close()
        if not row:
            return None, "no_primary_connection"
        connection = {
            "id": row[0],
            "exchange": normalize_exchange_key(row[1]),
            "mode": row[2] or "futures",
            "api_key": safe_decrypt_credential(row[3]),
            "api_secret": safe_decrypt_credential(row[4]),
            "passphrase": safe_decrypt_credential(row[5]),
            "auto_trade_enabled": int(row[6] or 0),
            "primary_for_futures": int(row[7] or 0),
            "emergency_stop": int(row[8] or 0),
            "risk_mode": row[9] or "conservative",
            "risk_per_trade": float(row[10] or 0) if row[10] is not None else None,
        }
        if connection["emergency_stop"]:
            return None, "emergency_stop"
        if signal_trade_type == "spot":
            return None, "spot_auto_disabled_or_unprotected"
        capability = get_exchange_capability(connection["exchange"]) if get_exchange_capability else {"auto_trade_futures": connection["exchange"] in {"bybit", "binance"}}
        if not capability.get("auto_trade_futures"):
            return None, f"exchange_not_live_enabled:{connection['exchange']}"
        return connection, "multi_exchange"
    except Exception as e:
        log(f"MULTI_EXCHANGE_CONNECTION_LOOKUP_FAILED email={mask_email(email)} reason={e}")
        return None, "lookup_failed"


def get_exchange(api_key, api_secret, trade_type, exchange_name=None, passphrase=None):
    """Return the configured exchange for real auto-trading.

    Default is Bybit because Binance can be blocked by region/API permissions.
    Supported AUTO_TRADE_EXCHANGE values: bybit, binance, binanceus, kucoin.
    Use Bybit API keys without withdrawal permission. For futures, this build
    targets USDT-margined perpetuals (for example BTC/USDT:USDT).
    """
    exchange_name = normalize_exchange_key(exchange_name or AUTO_TRADE_EXCHANGE or "bybit")
    trade_type = str(trade_type or "spot").lower()
    default_type = "swap" if trade_type == "futures" else "spot"

    common = {
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
    }

    if exchange_name == "bybit":
        return ccxt.bybit({
            **common,
            "options": {
                "defaultType": default_type,
                "adjustForTimeDifference": True,
                "recvWindow": 10000,
            },
        })

    if exchange_name == "kucoin":
        if trade_type == "futures":
            raise Exception("KuCoin futures execution is not enabled in this build. Use spot or set AUTO_TRADE_EXCHANGE=bybit.")
        return ccxt.kucoin({**common, "password": passphrase} if passphrase else common)

    if exchange_name == "okx":
        return ccxt.okx({
            **common,
            "password": passphrase,
            "options": {"defaultType": "swap" if trade_type == "futures" else "spot"},
        })

    if exchange_name == "bitget":
        return ccxt.bitget({
            **common,
            "password": passphrase,
            "options": {"defaultType": "swap" if trade_type == "futures" else "spot"},
        })

    if exchange_name == "gateio":
        return ccxt.gateio({
            **common,
            "options": {"defaultType": "swap" if trade_type == "futures" else "spot"},
        })

    if exchange_name == "mexc":
        return ccxt.mexc({
            **common,
            "options": {"defaultType": "swap" if trade_type == "futures" else "spot"},
        })

    if exchange_name in ["binanceus", "binance_us"]:
        if trade_type == "futures":
            raise Exception("Binance US does not support futures execution in this build. Use spot or set AUTO_TRADE_EXCHANGE=bybit.")
        return ccxt.binanceus(common)

    # Backwards-compatible Binance mode.
    return ccxt.binance({
        **common,
        "options": {"defaultType": "future" if trade_type == "futures" else "spot"},
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

def calculate_amount(usdt_balance, risk_percent, entry_price, stop_loss_price=None):
    """Return position amount using true risk at the stop-loss.

    Previous logic used risk capital as notional size. That does not control the
    real loss when SL is hit. This version risks `usdt_balance * risk_percent`
    and divides it by the absolute entry-to-SL distance, then caps notional size
    so a tight SL cannot create an oversized order.
    """
    try:
        usdt_balance = float(usdt_balance or 0)
        risk_percent = float(risk_percent or 0)
        entry_price = float(entry_price or 0)
        stop_loss_price = float(stop_loss_price or 0)
    except Exception:
        return 0

    if usdt_balance <= 0 or risk_percent <= 0 or entry_price <= 0 or stop_loss_price <= 0:
        return 0

    loss_per_unit = abs(entry_price - stop_loss_price)
    if loss_per_unit <= 0:
        return 0

    risk_usdt = usdt_balance * risk_percent
    risk_based_amount = risk_usdt / loss_per_unit

    max_notional = usdt_balance * max(0.0, min(MAX_AUTO_TRADE_NOTIONAL_PERCENT, 1.0))
    max_amount_by_balance = max_notional / entry_price
    amount = min(risk_based_amount, max_amount_by_balance)
    return round(max(amount, 0), 6)


def emergency_close_position(exchange, symbol, side, amount, trade_type, reason="protection_failed"):
    """Best-effort immediate close for an unsafe auto-trade.

    This must be called whenever the market order is submitted but protection is
    missing, fill data is unsafe, or validation fails after execution.
    """
    try:
        opposite_side = "sell" if side == "buy" else "buy"
        params = {"reduceOnly": True} if str(trade_type or "").lower() == "futures" else {}
        close_order = exchange.create_order(
            symbol=symbol,
            type="market",
            side=opposite_side,
            amount=amount,
            price=None,
            params=params,
        )
        log(f"AUTO_TRADE_EMERGENCY_CLOSE symbol={symbol} side={opposite_side} amount={amount} reason={reason} close_id={close_order.get('id') if isinstance(close_order, dict) else None}")
        return True, close_order
    except Exception as close_error:
        log(f"AUTO_TRADE_EMERGENCY_CLOSE_FAILED symbol={symbol} amount={amount} reason={reason} error={close_error}")
        return False, None

def place_protection_orders(exchange, symbol, side, amount, tp_price, sl_price, trade_type):
    """Place protective TP/SL where the selected exchange supports it.

    Auto-trading must never silently pretend that protection exists. If we cannot
    place protection for a real futures order, return False so the operator can
    see it in logs and Telegram. Spot market execution is left unprotected by
    design because many exchanges do not support portable spot OCO through CCXT.
    """
    try:
        opposite_side = "sell" if side == "buy" else "buy"
        exchange_id = getattr(exchange, "id", "").lower()
        trade_type = str(trade_type or "spot").lower()

        if trade_type != "futures":
            return False, "Spot auto-trade protection is not implemented safely. Use Spot signals only until OCO/bracket exits are added."

        if exchange_id == "bybit":
            # Bybit supports TP/SL params on USDT perpetual positions. We attach
            # them using the unified edit_position/position trading stop style
            # when available; if unavailable, try reduce-only trigger orders.
            try:
                if hasattr(exchange, "set_position_mode"):
                    pass
            except Exception:
                pass
            try:
                exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side=opposite_side,
                    amount=amount,
                    price=None,
                    params={"reduceOnly": True, "triggerPrice": tp_price, "takeProfit": True},
                )
                exchange.create_order(
                    symbol=symbol,
                    type="market",
                    side=opposite_side,
                    amount=amount,
                    price=None,
                    params={"reduceOnly": True, "triggerPrice": sl_price, "stopLoss": True},
                )
                return True, "Bybit reduce-only TP/SL trigger orders submitted"
            except Exception as trigger_error:
                return False, f"Bybit protection order error: {trigger_error}"

        if exchange_id == "binance":
            exchange.create_order(
                symbol=symbol,
                type="TAKE_PROFIT_MARKET",
                side=opposite_side,
                amount=amount,
                params={"stopPrice": tp_price, "closePosition": False},
            )
            exchange.create_order(
                symbol=symbol,
                type="STOP_MARKET",
                side=opposite_side,
                amount=amount,
                params={"stopPrice": sl_price, "closePosition": False},
            )
            return True, "Binance TP/SL placed"

        return False, f"Protection orders not implemented for exchange={exchange_id}"

    except Exception as e:
        return False, f"Protection order error: {e}"

# ================= TRADE EXECUTION =================
def execute_trade(api_key, api_secret, signal, trade_type, risk_percent, chat_id, exchange_name=None, passphrase=None, connection_id=None, user_info=None):
    try:
        exchange_name = normalize_exchange_key(exchange_name or AUTO_TRADE_EXCHANGE or "bybit")
        connection_ref = {"exchange": exchange_name, "id": connection_id}
        exchange = get_exchange(api_key, api_secret, trade_type, exchange_name=exchange_name, passphrase=passphrase)
        exchange.load_markets()

        raw_symbol = signal["pair"]
        symbol = normalize_symbol_for_ccxt(raw_symbol, trade_type=trade_type, exchange_name=exchange_name)

        if str(trade_type or "spot").lower() == "spot" and not ENABLE_SPOT_AUTO_TRADE:
            record_execution_event(user_info or {}, signal, "SKIPPED", "spot_auto_disabled_or_unprotected", connection_ref)
            return None, "Spot auto-trading is disabled for safety until exchange OCO/SL protection is implemented. Spot signals remain enabled."

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
        display_confidence = signal_display_confidence(signal)
        if display_confidence < 70:
            log(f"SIGNAL_BLOCKED_LOW_DISPLAY_CONF pair={signal.get('pair')} display_conf={display_confidence}")
            record_execution_event(user_info or {}, signal, "REJECTED", "low_display_confidence", connection_ref)
            return None, "Auto trade rejected: display confidence below 70"
        freshness_ok, freshness_reason, live_price = validate_signal_entry_freshness(signal, context="AUTO_TRADE")
        if not freshness_ok:
            record_execution_event(user_info or {}, signal, "REJECTED", f"entry_freshness:{freshness_reason}", connection_ref)
            return None, f"Auto trade rejected by entry freshness guard: {freshness_reason}"

        # تأكيد حي قبل التنفيذ
        live_price = live_price or get_live_price(raw_symbol)
        if live_price is None:
            return None, "فشل سحب السعر الحالي"

        deviation = abs(live_price - entry) / entry * 100
        if deviation > MAX_ENTRY_DEVIATION_PERCENT:
            return None, f"تم رفض الصفقة: السعر تحرك ({round(deviation,4)}%)"

        chase = ENTRY_CHASE_TOLERANCE_PERCENT / 100.0
        if signal["direction"] == "LONG" and live_price > entry * (1 + chase):
            return None, "تم رفض الصفقة: السعر سبق نقطة الدخول للشراء"
        if signal["direction"] == "SHORT" and live_price < entry * (1 - chase):
            return None, "تم رفض الصفقة: السعر سبق نقطة الدخول للبيع"

        if signal["direction"] == "LONG" and sl >= live_price:
            return None, "Auto trade rejected: invalid stop loss for LONG"
        if signal["direction"] == "SHORT" and sl <= live_price:
            return None, "Auto trade rejected: invalid stop loss for SHORT"

        amount = calculate_amount(usdt_balance, risk_percent, live_price, sl)
        if amount <= 0:
            return None, "كمية الصفقة غير صالحة"

        valid_amount, reason = validate_symbol_amount(exchange, symbol, amount)
        if not valid_amount:
            return None, f"Validation failed: {reason}"

        exchange_id = getattr(exchange, "id", "").lower()
        if exchange_id == "bybit" and trade_type == "futures":
            order = exchange.create_order(
                symbol=symbol,
                type="market",
                side=side,
                amount=amount,
                price=None,
                params={
                    "takeProfit": tp,
                    "stopLoss": sl,
                    "tpTriggerBy": "LastPrice",
                    "slTriggerBy": "LastPrice",
                },
            )
            protection_ok, protection_msg = True, "Bybit market order submitted with attached TP/SL params"
        else:
            order = exchange.create_market_order(symbol, side, amount)
            protection_ok, protection_msg = place_protection_orders(
                exchange, symbol, side, amount, tp, sl, trade_type
            )

        if not order or not order.get("id"):
            return None, "فشل تنفيذ أمر السوق"

        if not protection_ok:
            emergency_close_position(exchange, symbol, side, amount, trade_type, reason=f"protection_failed:{protection_msg}")
            return None, f"Auto trade rejected: protection failed and emergency close was attempted: {protection_msg}"

        actual_entry_price = extract_actual_fill_price(order)
        if actual_entry_price is None:
            log(f"AUTO_TRADE_FILL_PRICE_UNAVAILABLE pair={raw_symbol} order_id={order.get('id')} exchange={exchange_id}")
            emergency_close_position(exchange, symbol, side, amount, trade_type, reason="fill_price_unavailable")
            return None, "Auto trade submitted but fill price unavailable; emergency close was attempted and trade was not recorded as OPEN"

        fill_deviation = abs(float(actual_entry_price) - entry) / entry * 100
        if fill_deviation > MAX_ENTRY_DEVIATION_PERCENT:
            log(
                f"AUTO_TRADE_FILL_DEVIATION_TOO_HIGH pair={raw_symbol} order_id={order.get('id')} "
                f"signal_entry={entry} actual_entry={actual_entry_price} deviation={round(fill_deviation, 4)}"
            )
            emergency_close_position(exchange, symbol, side, amount, trade_type, reason="fill_deviation_too_high")
            return None, "Auto trade fill deviation too high; emergency close was attempted and trade was not recorded as OPEN"

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
            float(actual_entry_price),
            tp,
            sl,
            amount,
            str(order.get("id")),
            "OPEN",
            0
        ))
        conn.commit()
        conn.close()
        record_execution_event(
            user_info or {},
            signal,
            "EXECUTED",
            protection_msg,
            connection_ref,
            order_id=str(order.get("id")),
            actual_entry=actual_entry_price,
        )

        return order, protection_msg

    except Exception as e:
        try:
            record_execution_event(
                user_info or {},
                signal,
                "ERROR",
                str(e),
                {"exchange": exchange_name if "exchange_name" in locals() else None, "id": connection_id},
            )
        except Exception:
            pass
        return None, f"Trade Error: {e}"

# ================= SIGNAL TRACKING MONITOR =================
def _user_take_profit_targets(take_profits, fallback_tp):
    targets = []
    try:
        if take_profits:
            raw = json.loads(take_profits) if isinstance(take_profits, str) else take_profits
            if isinstance(raw, (list, tuple)):
                targets = [_safe_float(item) for item in raw]
    except Exception:
        targets = []
    targets = [item for item in targets if item is not None and item > 0]
    fallback = _safe_float(fallback_tp)
    if not targets and fallback and fallback > 0:
        targets = [fallback]
    return targets[:2]


def _target_pnl_percent(direction, entry, target):
    direction = str(direction or "").upper()
    entry = float(entry)
    target = float(target)
    if direction == "LONG":
        return ((target - entry) / entry) * 100
    if direction == "SHORT":
        return ((entry - target) / entry) * 100
    return 0


def update_signal_outcomes():
    if not ENABLE_SIGNAL_TRACKING:
        return
    try:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", ("signal_log",))
        signal_log_columns = {(row[0] if not hasattr(row, "get") else row.get("column_name")) for row in (c.fetchall() or [])}
        take_profits_select = "take_profits" if "take_profits" in signal_log_columns else "NULL AS take_profits"
        outcome_select = "outcome" if "outcome" in signal_log_columns else "NULL AS outcome"
        pnl_select = "COALESCE(pnl_percent, 0)" if "pnl_percent" in signal_log_columns else "0 AS pnl_percent"
        c.execute("""
        SELECT id, chat_id, pair, direction, entry, tp, sl, {take_profits_select}, {outcome_select}, {pnl_select}
        FROM signal_log
        WHERE status IN ('SENT', 'OPEN')
          AND chat_id IS NOT NULL
          AND chat_id <> ''
        ORDER BY sent_at ASC
        LIMIT 200
        """.format(
            take_profits_select=take_profits_select,
            outcome_select=outcome_select,
            pnl_select=pnl_select,
        ))
        open_signals = c.fetchall()

        for row in open_signals:
            signal_id, chat_id, pair, direction, entry, tp, sl, take_profits, existing_outcome, existing_pnl_percent = row
            try:
                current_price = get_live_price(pair)
                if current_price is None:
                    continue

                outcome = None
                next_status = None
                pnl_percent = 0
                direction = str(direction or "").upper()
                entry = float(entry)
                sl = float(sl)
                targets = _user_take_profit_targets(take_profits, tp)
                tp1 = targets[0] if targets else _safe_float(tp)
                tp2 = targets[1] if len(targets) > 1 else tp1
                already_tp1 = str(existing_outcome or "").upper() in {"TP1_HIT", "PARTIAL_WIN_THEN_REVERSED"}

                if direction == "LONG":
                    hit_tp2 = bool(tp2 and current_price >= tp2)
                    hit_tp1 = bool(tp1 and current_price >= tp1)
                    hit_sl = current_price <= sl
                    if hit_tp2:
                        outcome = "TP2_HIT"
                        next_status = "CLOSED"
                        pnl_percent = _target_pnl_percent(direction, entry, tp2)
                    elif hit_tp1 and not already_tp1:
                        outcome = "TP1_HIT"
                        next_status = "OPEN"
                        pnl_percent = _target_pnl_percent(direction, entry, tp1)
                    elif hit_sl:
                        if already_tp1:
                            outcome = "PARTIAL_WIN_THEN_REVERSED"
                            next_status = "CLOSED"
                            pnl_percent = max(float(existing_pnl_percent or 0), _target_pnl_percent(direction, entry, tp1 or tp))
                        else:
                            outcome = "SL_HIT"
                            next_status = "CLOSED"
                            pnl_percent = ((sl - entry) / entry) * 100
                elif direction == "SHORT":
                    hit_tp2 = bool(tp2 and current_price <= tp2)
                    hit_tp1 = bool(tp1 and current_price <= tp1)
                    hit_sl = current_price >= sl
                    if hit_tp2:
                        outcome = "TP2_HIT"
                        next_status = "CLOSED"
                        pnl_percent = _target_pnl_percent(direction, entry, tp2)
                    elif hit_tp1 and not already_tp1:
                        outcome = "TP1_HIT"
                        next_status = "OPEN"
                        pnl_percent = _target_pnl_percent(direction, entry, tp1)
                    elif hit_sl:
                        if already_tp1:
                            outcome = "PARTIAL_WIN_THEN_REVERSED"
                            next_status = "CLOSED"
                            pnl_percent = max(float(existing_pnl_percent or 0), _target_pnl_percent(direction, entry, tp1 or tp))
                        else:
                            outcome = "SL_HIT"
                            next_status = "CLOSED"
                            pnl_percent = ((entry - sl) / entry) * 100

                if outcome:
                    c.execute("""
                    UPDATE signal_log
                    SET status = %s,
                        outcome = %s,
                        current_price = %s,
                        pnl_percent = %s,
                        closed_at = CASE WHEN %s = 'CLOSED' THEN NOW() ELSE closed_at END
                    WHERE id = %s AND chat_id = %s
                    """, (next_status or "OPEN", outcome, float(current_price), round(float(pnl_percent), 4), next_status or "OPEN", signal_id, str(chat_id)))
                    conn.commit()

                    if SIGNAL_TRACKING_NOTIFY:
                        icon = "✅" if outcome in ("TP1_HIT", "TP2_HIT", "TP_HIT", "PARTIAL_WIN_THEN_REVERSED") else "🛑"
                        clean_pnl_percent = clean_number(pnl_percent, 2)
                        what_happened = "TP Hit" if outcome in ("TP1_HIT", "TP2_HIT", "TP_HIT", "PARTIAL_WIN_THEN_REVERSED") else "SL Hit" if outcome == "SL_HIT" else "Manual/Unknown Exit"
                        if outcome == "TP1_HIT":
                            what_happened = "TP1 Hit - partial profit"
                        elif outcome == "TP2_HIT":
                            what_happened = "TP2 Hit - trade completed"
                        elif outcome == "PARTIAL_WIN_THEN_REVERSED":
                            what_happened = "Partial profit secured before reversal"
                        elif outcome == "SL_HIT":
                            what_happened = "SL Hit"
                        outcome_sent = send(chat_id, f"""{icon} NEXORA TRADE RESULT

Market: {pair}
Direction: {direction}
Entry: {clean_number(entry, 6)}
Exit: {clean_number(current_price, 6)}
Result: {what_happened}
Outcome: {clean_pnl_percent}%

This is a tracked signal result, not a new trade opportunity.
Trading involves risk and past outcomes do not guarantee future results.
""")
                        if not outcome_sent:
                            log(f"SIGNAL_OUTCOME_SEND_FAILED signal_id={signal_id} chat_id_present={bool(chat_id)} pair={pair}")
                    write_log(chat_id, "INFO", f"Signal outcome {pair} {outcome} pnl={round(float(pnl_percent), 4)}%")
                    if NEXORA_PROOF_MODE:
                        log(
                            f"PROOF_OUTCOME_RECORDED signal_id={signal_id} pair={pair} "
                            f"outcome={outcome} pnl={round(float(pnl_percent), 4)}"
                        )
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
                    send(chat_id, f"""NEXORA TRADE RESULT

Market: {pair}
Direction: {direction}
Entry: {clean_number(entry, 6)}
Exit: {clean_number(current_price, 6)}
Result: {close_reason}
Tracked PNL: {pnl} USDT
Tracked PNL %: {pnl_percent}%
Duration: {duration_text}

This is a trade result update, not a new trade opportunity.
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
    """Fetch crypto and Forex signals without mixing market engines."""
    try:
        reset_signal_scan_diagnostics()
        crypto_signals = get_top_free_signals(limit=MAX_QUALIFIED_OPPORTUNITIES_PER_CYCLE) or []

        if not crypto_signals:
            fallback_candidates = []
            try:
                from market_analyzer import TIMEFRAMES
                for symbol in get_scan_symbols():
                    for tf in TIMEFRAMES:
                        try:
                            s = generate_signal(symbol, tf)
                            if s:
                                fallback_candidates.append(s)
                        except Exception:
                            continue
                fallback_candidates = sorted(
                    fallback_candidates,
                    key=lambda x: (x.get("confidence", 0), abs(x.get("score", 0))),
                    reverse=True,
                )
                if fallback_candidates:
                    crypto_signals = fallback_candidates[:1]
            except Exception as e:
                log(f"Fallback paid signal error: {e}")

        crypto_summary = log_signal_scan_summary(len(crypto_signals))
        try:
            dominant = max(
                ((k, v) for k, v in crypto_summary.items() if str(k).startswith("rejected_")),
                key=lambda item: int(item[1] or 0),
                default=("none", 0),
            )[0]
        except Exception:
            dominant = "none"
        log(
            "CRYPTO_SCAN_SUMMARY "
            f"unique_symbols_scanned={crypto_summary.get('unique_symbols_scanned', crypto_summary.get('scanned', 0))} "
            f"scan_attempts={crypto_summary.get('scan_attempts', crypto_summary.get('scanned', 0))} "
            f"passed_candidates={crypto_summary.get('candidates_built', 0)} "
            f"final_signals={len(crypto_signals)} "
            f"dominant_rejection={dominant}"
        )

        forex_signals = []
        if get_forex_signals:
            try:
                forex_signals = get_forex_signals() or []
            except Exception as e:
                log(f"FOREX_SIGNAL_FETCH_ERROR error={e}")
                forex_signals = []
        log_forex_scan_summary(len(forex_signals))

        signals = list(crypto_signals) + list(forex_signals)
        final_signals = []

        for s in signals:
            s = attach_signal_timestamp(s)
            if not valid_signal(s):
                continue
            if not logical_signal(s):
                log(f"Logical invalid signal skipped: {signal_log_summary(s)}")
                continue
            if not is_qualified_opportunity(s):
                tier = qualified_opportunity_tier(s)
                log(f"SIGNAL_REJECTED stage=qualified_opportunity reason=tier_{tier} pair={s.get('pair')}")
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
            if ULTRA_MODE:
                try:
                    if signal_display_confidence(s) < 75 and qualified_opportunity_tier(s) != "B_PLUS":
                        log(f"Ultra mode rejected: {s.get('pair')} display_conf={signal_display_confidence(s)}")
                        continue
                except Exception:
                    continue
            final_signals.append(s)
            if signal_market_bucket(s) != "forex":
                record_trade_type(s.get("type"))

        final_signals = sorted(
            final_signals,
            key=lambda x: (signal_display_confidence(x), abs(float(x.get("score", 0) or 0))),
            reverse=True,
        )
        return final_signals[:MAX_DELIVERIES_PER_CYCLE]
    except Exception as e:
        log(f"get_monster_signals error: {e}")
        log_signal_scan_summary(0)
        log_forex_scan_summary(0)
        return []

def should_notify_no_signal(chat_id, plan="trial", state_key="market_wait"):
    try:
        now = datetime.now()
        plan = str(plan or "trial").strip().lower()
        cooldown_minutes = max(NO_SIGNAL_NOTIFY_COOLDOWN_MINUTES, NO_SIGNAL_NOTIFY_COOLDOWN_HOURS * 60)
        idempotency_key = hashlib.sha256(f"no_signal:{chat_id}:{plan}:{state_key}".encode("utf-8")).hexdigest()
        cache_key = f"{chat_id}:{plan}:{state_key}"

        try:
            conn = db()
            c = conn.cursor()
            c.execute(
                """
                SELECT last_sent_at, idempotency_key
                  FROM notification_state
                 WHERE chat_id = %s AND notification_type = %s AND plan = %s
                """,
                (str(chat_id), "NO_SIGNAL_STATUS", plan),
            )
            row = c.fetchone()
            if row and row[0]:
                diff_minutes = (now - row[0]).total_seconds() / 60
                if diff_minutes < cooldown_minutes and row[1] == idempotency_key:
                    conn.close()
                    return False
            c.execute(
                """
                INSERT INTO notification_state (chat_id, notification_type, plan, idempotency_key, last_sent_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (chat_id, notification_type, plan)
                DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key, last_sent_at = CURRENT_TIMESTAMP
                """,
                (str(chat_id), "NO_SIGNAL_STATUS", plan, idempotency_key),
            )
            conn.commit()
            conn.close()
            LAST_NO_SIGNAL_NOTIFY[cache_key] = now
            return True
        except Exception as db_error:
            if SIGNAL_DEBUG_LOGS:
                log(f"NO_SIGNAL_NOTIFY_STATE_DB_FAILED chat_ref={mask_chat_id(chat_id)} error={db_error}")

        if cache_key not in LAST_NO_SIGNAL_NOTIFY:
            LAST_NO_SIGNAL_NOTIFY[cache_key] = now
            return True

        last_time = LAST_NO_SIGNAL_NOTIFY.get(cache_key)
        if not last_time:
            LAST_NO_SIGNAL_NOTIFY[cache_key] = now
            return True

        diff_minutes = (now - last_time).total_seconds() / 60

        if diff_minutes >= cooldown_minutes:
            LAST_NO_SIGNAL_NOTIFY[cache_key] = now
            return True

        return False
    except:
        return False


def classify_no_signal_state(market_reason):
    text = str(market_reason or "").lower()
    if "multi-timeframe" in text:
        return "mtf_unconfirmed"
    if "entry" in text:
        return "entry_not_ready"
    if "liquidity" in text:
        return "liquidity_not_clean"
    if "quality" in text:
        return "quality_below_gate"
    return "market_wait"


def notify_users_no_signal(users):
    try:
        if not NO_SIGNAL_STATUS_ENABLED:
            return
        try:
            scan_summary = get_signal_scan_diagnostics(0) or {}
        except Exception:
            scan_summary = {}

        final_signals = int(scan_summary.get("final_signals", 0) or 0)
        rejected_mtf = int(scan_summary.get("rejected_mtf", 0) or 0)
        rejected_entry = int(scan_summary.get("rejected_entry", 0) or 0)
        rejected_quality = int(scan_summary.get("rejected_quality", 0) or 0)
        rejected_liquidity = int(scan_summary.get("rejected_liquidity", 0) or 0)

        market_reason = "No high-quality final setup passed all safety checks."
        if rejected_mtf:
            market_reason = "Multi-timeframe confirmation was not strong enough."
        elif rejected_entry:
            market_reason = "Price moved away from a professional entry zone."
        elif rejected_liquidity:
            market_reason = "Liquidity was not strong enough for a clean trade."
        elif rejected_quality:
            market_reason = "Signal quality score stayed below the delivery gate."

        for user in users:
            try:
                user_info = unpack_delivery_user(user)
                chat_id = user_info["chat_id"]
                plan = str(user_info["plan"] or "trial").strip().lower()
                trades = user_info["trades"]
                email = user_info["email"]
                bot_active = user_info.get("bot_active")

                if not chat_id:
                    log_unlinked_user_once(email)
                    continue
                if int(bot_active or 0) != 1:
                    continue

                if plan == "trial":
                    if not is_trial_allowed(trades) and not FREE_EARN_MODE:
                        continue
                elif not is_paid_plan_active(plan, user_info["expiry"], user_info["is_paid"]):
                    continue

                state_key = classify_no_signal_state(market_reason)
                if not should_notify_no_signal(chat_id, plan, state_key):
                    continue

                plan_note = "Premium direct delivery is active." if plan != "trial" else "Free Earn waits for a qualified premium signal."
                msg = f"""NEXORA MARKET STATUS

No trade has been sent in this scan.

Reason:
{market_reason}

Plan:
{plan} - {plan_note}

The bot is active, but it will not force weak trades. Quality first.

Risk warning: Crypto trading is risky. Not financial advice."""

                sent_ok = send(chat_id, msg)

                if sent_ok:
                    log(f"NO_SIGNAL_STATUS_SENT plan={plan} chat_id_present=True final_signals={final_signals}")
                    write_log(chat_id, "INFO", f"No-signal status sent plan={plan}")
                else:
                    log(f"NO_SIGNAL_STATUS_FAILED plan={plan} chat_id_present=True")

            except Exception as inner_e:
                log(f"notify_users_no_signal inner error: {inner_e}")

    except Exception as e:
        log(f"notify_users_no_signal error: {e}")

# ================= MAIN =================
def run():
    log("AUTO_SENDER FILE STARTED")
    init_trade_tables()
    try:
        forex_provider_status = provider_configuration_status()
        log(
            "FOREX_PROVIDER_STATUS "
            f"provider={forex_provider_status.get('provider')} "
            f"configured={bool(forex_provider_status.get('configured'))} "
            f"reason={forex_provider_status.get('reason', '')}"
        )
    except Exception as forex_status_error:
        log(f"FOREX_PROVIDER_STATUS_ERROR error={forex_status_error}")
    log(f"🚀 BOT STARTED - MONSTER MODE | auto_exchange={AUTO_TRADE_EXCHANGE}")
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
                for user in users:
                    try:
                        user_info = unpack_delivery_user(user)
                        eligible, reason = delivery_access_status(user_info)
                        if eligible:
                            reason = "no_final_signals"
                        log_plan_delivery_diag(
                            user_info.get("email"),
                            user_info.get("plan"),
                            user_info.get("chat_id"),
                            eligible,
                            reason,
                        )
                    except Exception as diag_e:
                        log(f"PLAN_DELIVERY_DIAG_ERROR reason=no_signal_cycle error={diag_e}")

    # ===== Notify users market is not safe now =====
                notify_users_no_signal(users)

                time.sleep(30)
                continue

            for signal in signals:
                log(f"Processing signal: {signal_log_summary(signal)}")
                signal_sent_users = 0
                delivery_locked_users = 0
                delivery_blocked_users = 0
                display_confidence = signal_display_confidence(signal)
                if display_confidence < 70 and qualified_opportunity_tier(signal) != "B_PLUS":
                    log(f"SIGNAL_BLOCKED_LOW_DISPLAY_CONF pair={signal.get('pair')} display_conf={display_confidence}")
                    for user in users:
                        try:
                            user_info = unpack_delivery_user(user)
                            eligible, _ = delivery_access_status(user_info, qualified_opportunity_available=True)
                            log_plan_delivery_diag(
                                user_info.get("email"),
                                user_info.get("plan"),
                                user_info.get("chat_id"),
                                False,
                                "low_display_confidence",
                            )
                            log_pro_2y_block(user_info.get("plan"), "low_display_confidence")
                        except Exception as diag_e:
                            log(f"PLAN_DELIVERY_DIAG_ERROR reason=low_display_confidence error={diag_e}")
                    continue

                for user in users:
                    user_info = unpack_delivery_user(user)
                    chat_id = user_info["chat_id"]
                    plan = user_info["plan"]
                    expiry = user_info["expiry"]
                    api_key = user_info["api_key"]
                    api_secret = user_info["api_secret"]
                    trade_amount = user_info["trade_amount"]
                    trade_type = user_info["trade_type"]
                    trades = user_info["trades"]
                    profit = user_info["profit"]
                    bot_active = user_info["bot_active"]
                    is_paid = user_info["is_paid"]
                    spot_enabled = user_info["spot_enabled"]
                    futures_enabled = user_info["futures_enabled"]
                    email = user_info["email"]
                    spot_auto_trade_enabled = user_info["spot_auto_trade_enabled"]
                    futures_auto_trade_enabled = user_info["futures_auto_trade_enabled"]
                    stop_loss_required = user_info["stop_loss_required"]

                    if not chat_id:
                        log_unlinked_user_once(email)
                        log_plan_delivery_diag(email, plan, chat_id, False, "missing_chat_id")
                        log_pro_2y_block(plan, "missing_chat_id")
                        delivery_blocked_users += 1
                        continue

                    delivery_product, market_allowed, market_reason = delivery_product_for_signal(user_info, signal)
                    is_forex_signal = delivery_product == VIP_ALL_FOREX_CODE
                    if not market_allowed:
                        log(
                            f"SIGNAL_PLAN_BLOCKED plan={plan} product={delivery_product} pair={signal.get('pair')} "
                            f"display_conf={display_confidence} risk_score={signal.get('risk_score')} "
                            f"reason={market_reason}"
                        )
                        log_plan_delivery_diag(email, plan, chat_id, False, market_reason)
                        delivery_blocked_users += 1
                        continue

                    # ===== ACCESS CHECK =====
                    if not is_forex_signal and plan != "trial":
                        if not is_paid_plan_active(plan, expiry, is_paid):
                            log_plan_delivery_diag(email, plan, chat_id, False, "subscription_inactive")
                            log_pro_2y_block(plan, "subscription_inactive")
                            delivery_blocked_users += 1
                            continue

                    # ===== PLAN FILTER =====
                    # Trial/Free Earn access is handled separately from paid-plan filters.
                    plan_filter_required = (not is_forex_signal) and plan != "trial"
                    if plan_filter_required and not signal_allowed_for_plan(plan, signal):
                        block_reason = signal_plan_block_reason(plan, signal)
                        log(
                            f"SIGNAL_PLAN_BLOCKED plan={plan} pair={signal.get('pair')} "
                            f"display_conf={display_confidence} risk_score={signal.get('risk_score')} "
                            f"reason={block_reason}"
                        )
                        log_plan_delivery_diag(email, plan, chat_id, False, f"plan_filter:{block_reason}")
                        log_pro_2y_block(plan, block_reason)
                        delivery_blocked_users += 1
                        continue

                    if not is_forex_signal and not type_allowed_for_user(signal.get("type"), spot_enabled, futures_enabled):
                        reason = "signal_type_disabled"
                        log(
                            f"SIGNAL_PLAN_BLOCKED plan={plan} pair={signal.get('pair')} "
                            f"display_conf={display_confidence} risk_score={signal.get('risk_score')} "
                            f"reason={reason}"
                        )
                        log_plan_delivery_diag(email, plan, chat_id, False, reason)
                        log_pro_2y_block(plan, reason)
                        delivery_blocked_users += 1
                        continue

                    # ===== ELITE FILTER (VIP ONLY) =====
                    if plan == "vip":
                        if not elite_trade_filter(signal):
                            log(f"Elite filter rejected: {signal['pair']}")
                            log_plan_delivery_diag(email, plan, chat_id, False, "elite_filter_rejected")
                            delivery_blocked_users += 1
                            continue

                    # ===== RE-CHECK FRESHNESS BEFORE SEND =====
                    if not signal_is_fresh(signal):
                        log(f"SIGNAL_SEND_BLOCKED_STALE pair={signal.get('pair')} direction={signal.get('direction')}")
                        log_plan_delivery_diag(email, plan, chat_id, False, "stale_before_send")
                        log_pro_2y_block(plan, "stale_before_send")
                        delivery_blocked_users += 1
                        continue

                    # ===== FREE EARN / SEND SIGNAL =====
                    free_earn_state = "paid_direct" if is_forex_signal else maybe_handle_free_earn_delivery(chat_id, plan, trades, signal)
                    if free_earn_state == "locked_prompt_sent":
                        try:
                            from market_analyzer import _scan_diag_inc
                            _scan_diag_inc("free_earn_locks_created")
                        except Exception:
                            pass
                        log_plan_delivery_diag(email, plan, chat_id, False, "free_earn_locked")
                        delivery_locked_users += 1
                        continue
                    if free_earn_state in {"lock_create_failed", "lock_no_base_url", "lock_prompt_failed"}:
                        log_plan_delivery_diag(email, plan, chat_id, False, free_earn_state)
                        delivery_blocked_users += 1
                        continue
                    if free_earn_state == "credit_used":
                        log(f"FREE_UNLOCK_CREDIT_USED chat_ref={mask_chat_id(chat_id)} pair={signal.get('pair')}")

                    msg = format_signal(signal, delivery_product)
                    sent_ok = send(chat_id, msg)

                    if sent_ok:
                        signal_sent_users += 1
                        log_plan_delivery_diag(email, delivery_product, chat_id, True, "sent")
                        write_log(chat_id, "INFO", f"Signal sent {signal['pair']} {signal['direction']} conf={signal_display_confidence(signal)}")
                        record_sent_signal(chat_id, delivery_product, signal, delivery_mode=("forex_paid" if is_forex_signal else "free_earn_credit" if str(plan).lower() == "trial" else "paid"), locked=False, unlocked=True)
                        if delivery_product != "trial":
                            try:
                                from market_analyzer import _scan_diag_inc
                                _scan_diag_inc("paid_deliveries")
                            except Exception:
                                pass

                        if plan == "trial" and not is_forex_signal:
                            increment_trade(chat_id)
                    else:
                        log(f"SIGNAL_SEND_FAILED chat_ref={mask_chat_id(chat_id)} pair={signal.get('pair')}")
                        log_plan_delivery_diag(email, plan, chat_id, False, "telegram_send_failed")
                        log_pro_2y_block(plan, "telegram_send_failed")
                        delivery_blocked_users += 1

                    # ===== AUTO TRADE FOR VIP =====
                    if is_forex_signal:
                        log(f"FOREX_AUTO_TRADE_DISABLED product={FOREX_PRODUCT_LABEL} pair={signal.get('pair')} reason=execution_not_verified")
                        continue

                    if plan in AUTO_TRADE_PLANS and bot_active == 1:
                        try:
                            signal_trade_type = "futures" if signal.get("type") == "FUTURES" else "spot"
                            primary_connection, connection_reason = load_primary_auto_trade_connection(user_info, signal_trade_type)
                            effective_api_key = primary_connection.get("api_key") if primary_connection else safe_decrypt_credential(api_key)
                            effective_api_secret = primary_connection.get("api_secret") if primary_connection else safe_decrypt_credential(api_secret)
                            effective_passphrase = primary_connection.get("passphrase") if primary_connection else None
                            effective_exchange = primary_connection.get("exchange") if primary_connection else AUTO_TRADE_EXCHANGE
                            effective_connection_id = primary_connection.get("id") if primary_connection else None

                            if not effective_api_key or not effective_api_secret:
                                record_execution_event(user_info, signal, "SKIPPED", f"missing_credentials:{connection_reason}", primary_connection)
                                log(f"AUTO_TRADE_SKIPPED pair={signal.get('pair')} reason=missing_credentials connection={connection_reason}")
                                continue

                            can_trade, reason = can_trade_user(chat_id, trade_amount)
                            if not can_trade:
                                record_execution_event(user_info, signal, "SKIPPED", f"user_risk_gate:{reason}", primary_connection)
                                log(f"Auto trade blocked for {chat_id}: {reason}")
                                continue

                            if has_open_trade(chat_id, signal["pair"]):
                                record_execution_event(user_info, signal, "SKIPPED", "existing_open_trade", primary_connection)
                                log(f"Auto trade skipped: already open trade on {signal['pair']} for {chat_id}")
                                continue

                            if pair_in_cooldown(chat_id, signal["pair"]):
                                record_execution_event(user_info, signal, "SKIPPED", "pair_cooldown", primary_connection)
                                log(f"Auto trade skipped: cooldown active on {signal['pair']} for {chat_id}")
                                continue

                            if signal_trade_type == "spot" and (spot_auto_trade_enabled != 1 or not ENABLE_SPOT_AUTO_TRADE):
                                record_execution_event(user_info, signal, "SKIPPED", "spot_auto_disabled_or_unprotected", primary_connection)
                                log(f"AUTO_TRADE_SKIPPED pair={signal.get('pair')} reason=spot_auto_disabled_or_unprotected")
                                continue
                            if signal_trade_type == "futures" and futures_auto_trade_enabled != 1 and not primary_connection:
                                record_execution_event(user_info, signal, "SKIPPED", "futures_auto_disabled", primary_connection)
                                log(f"AUTO_TRADE_SKIPPED pair={signal.get('pair')} reason=futures_auto_disabled")
                                continue
                            if stop_loss_required == 1 and not signal.get("sl"):
                                record_execution_event(user_info, signal, "SKIPPED", "missing_stop_loss", primary_connection)
                                log(f"AUTO_TRADE_SKIPPED pair={signal.get('pair')} reason=missing_stop_loss")
                                continue

                            order, result_msg = execute_trade(
                                api_key=effective_api_key,
                                api_secret=effective_api_secret,
                                signal=signal,
                                trade_type=signal_trade_type,
                                risk_percent=adjust_risk(profit),
                                chat_id=chat_id,
                                exchange_name=effective_exchange,
                                passphrase=effective_passphrase,
                                connection_id=effective_connection_id,
                                user_info=user_info,
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

                log(f"SIGNAL_SENT pair={signal.get('pair')} direction={signal.get('direction')} users={signal_sent_users}")
                log_delivery_summary(1, len(users), signal_sent_users, delivery_locked_users, delivery_blocked_users)

            time.sleep(GLOBAL_LOOP_SLEEP)

        except Exception as e:
            log(f"RUN LOOP ERROR: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run()
