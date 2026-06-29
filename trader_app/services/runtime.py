from flask import request, render_template, redirect, session, url_for, jsonify, flash
from markupsafe import Markup
import psycopg2
import psycopg2.extras
import os
import requests
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import hmac
import json
from market_analyzer import get_top_free_signals
import random
import string
import re
import secrets
import logging
import smtplib
from email.message import EmailMessage
from cryptography.fernet import Fernet

# ================= RUNTIME SETTINGS =================

TOKEN = os.environ.get("TELEGRAM_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "https://yourdomain.com")
BOT_LINK = os.environ.get("BOT_LINK", "https://t.me/your_bot_username")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()

PLAN_PRICES = {
    "basic": 25,
    "pro": 59.99,
    "vip": 99.99,
    "pro_2y": 999,
}

PLAN_ORIGINAL_PRICES = {
    "basic": 49,
    "pro": 119,
    "vip": 199,
    "pro_2y": 1499,
}

PLAN_DURATIONS_DAYS = {
    "basic": 30,
    "pro": 30,
    "vip": 30,
    "pro_2y": 730,
}

PLAN_LABELS = {
    "trial": "Free Trial",
    "basic": "Basic",
    "pro": "Pro",
    "vip": "Elite",
    "pro_2y": "Pro 2 Years",
}

AUTO_TRADE_PLANS = {"vip", "pro_2y"}


FERNET_KEY = os.environ.get("FERNET_KEY", "").strip()

if not FERNET_KEY:
    raise Exception("FERNET_KEY missing in Railway Variables")

cipher = Fernet(FERNET_KEY.encode())

CSRF_EXEMPT_ENDPOINTS = {
    "webhook",
    "payment_webhook",
    "telegram.webhook",
    "payments.payment_webhook",
}

REDIRECT_EXEMPT_PATHS = {
    "/webhook",
    "/payment-webhook",
    "/health",
    "/api/data",
}


def get_csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def inject_csrf_helpers():
    def csrf_field():
        return Markup(f'<input type="hidden" name="csrf_token" value="{get_csrf_token()}">')

    return {
        "csrf_token": get_csrf_token,
        "csrf_field": csrf_field,
        "bot_link": current_bot_link(),
    }


def protect_post_requests():
    if request.method != "POST":
        return None

    endpoint = request.endpoint or ""
    if endpoint in CSRF_EXEMPT_ENDPOINTS or endpoint.rsplit(".", 1)[-1] in CSRF_EXEMPT_ENDPOINTS:
        return None

    expected = session.get("_csrf_token")
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not expected or not submitted or not hmac.compare_digest(expected, submitted):
        log(f"CSRF blocked endpoint={request.endpoint} ip={request.remote_addr}")
        return "Invalid CSRF token", 403

    return None


def redirect_legacy_domains():
    if request.path in REDIRECT_EXEMPT_PATHS:
        return None

    """Redirect public Railway URLs to the configured custom domain.

    This keeps Telegram, browser bookmarks, and old Railway links on the
    official brand domain without changing internal Railway health checks.
    """
    try:
        canonical = current_base_url()
        if not canonical or canonical in ["https://yourdomain.com", "http://localhost"]:
            return None

        host = (request.host or "").lower()
        canonical_host = canonical.replace("https://", "").replace("http://", "").split("/")[0].lower()
        legacy_hosts = [h.strip().lower() for h in os.environ.get("LEGACY_DOMAINS", "web-production-c6a34.up.railway.app").split(",") if h.strip()]

        if host in legacy_hosts and host != canonical_host:
            target = canonical + request.full_path
            if target.endswith("?"):
                target = target[:-1]
            return redirect(target, code=301)
    except Exception as exc:
        log(f"legacy redirect skipped: {exc}")
    return None

# ================= HELPERS =================
logger = logging.getLogger("ai_crypto_trader")


def log(msg):
    logger.info(str(msg))


def current_base_url():
    return str(os.environ.get("CANONICAL_DOMAIN") or os.environ.get("BASE_URL") or BASE_URL).strip().rstrip("/")


def current_bot_link():
    return str(os.environ.get("BOT_LINK") or BOT_LINK).strip().rstrip("/")


def audit_log(action, email=None, details=None, ip=None):
    safe_action = str(action or "unknown")[:120]
    safe_email = str(email or session.get("user") or "")[:255]
    safe_details = str(details or "")[:1000]
    safe_ip = str(ip or request.headers.get("X-Forwarded-For", request.remote_addr) or "")[:120]

    logger.info("AUDIT action=%s email=%s ip=%s details=%s", safe_action, safe_email, safe_ip, safe_details)

    try:
        conn = db()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO audit_logs (action, email, ip_address, details)
            VALUES (%s, %s, %s, %s)
            """,
            (safe_action, safe_email, safe_ip, safe_details),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("audit_log db write failed: %s", e)


def enforce_session_timeout():
    if not session.get("user"):
        return None

    timeout_minutes = int(os.environ.get("SESSION_TIMEOUT_MINUTES", "60"))
    now = datetime.utcnow()
    last_seen_raw = session.get("_last_seen")

    if last_seen_raw:
        try:
            last_seen = datetime.fromisoformat(last_seen_raw)
            if now - last_seen > timedelta(minutes=timeout_minutes):
                audit_log("session_timeout", session.get("user"))
                session.clear()
                flash("Session expired. Please login again.", "error")
                return redirect("/login")
        except Exception:
            session.clear()
            return redirect("/login")

    session.permanent = True
    session["_last_seen"] = now.isoformat()
    return None


def send_security_email(to_email, subject, body):
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_username = os.environ.get("SMTP_USERNAME", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    from_email = os.environ.get("SECURITY_EMAIL_FROM", smtp_username or "no-reply@example.com").strip()
    smtp_use_ssl = os.environ.get("SMTP_USE_SSL", "").strip().lower() in {"1", "true", "yes"} or smtp_port == 465

    if not smtp_host or not smtp_username or not smtp_password:
        logger.warning("Security email not sent because SMTP is not configured | to=%s subject=%s", to_email, subject)
        return False

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as smtp:
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(msg)
        logger.info("Security email sent | to=%s subject=%s", to_email, subject)
        return True
    except Exception as e:
        logger.error("Security email failed | to=%s subject=%s error=%s", to_email, subject, e)
        return False


def build_absolute_url(path):
    return f"{current_base_url()}{path}"


def create_email_verification_token(email, conn=None):
    token = secrets.token_urlsafe(32)
    own_conn = conn is None
    if own_conn:
        conn = db()
    c = conn.cursor()
    c.execute(
        """
        UPDATE users
        SET email_verification_token = %s,
            email_verification_sent_at = %s
        WHERE LOWER(email) = %s
        """,
        (token, datetime.utcnow().isoformat(), str(email).lower()),
    )
    conn.commit()
    if own_conn:
        conn.close()
    return token


def send_verification_email(email, token):
    link = build_absolute_url(f"/verify-email/{token}")
    sent = send_security_email(email, "Verify your Nexora AI Trader email", f"Verify your account here:\n{link}")
    audit_log("email_verification_sent", email, f"sent={sent}")
    return sent, link


def create_password_reset_token(email):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(minutes=int(os.environ.get("PASSWORD_RESET_MINUTES", "30")))).isoformat()
    conn = db()
    c = conn.cursor()
    c.execute(
        """
        UPDATE users
        SET password_reset_token = %s,
            password_reset_expires_at = %s
        WHERE LOWER(email) = %s
        """,
        (token, expires_at, str(email).lower()),
    )
    updated = c.rowcount
    conn.commit()
    conn.close()
    return token if updated else None


def send_password_reset_email(email, token):
    link = build_absolute_url(f"/reset-password/{token}")
    sent = send_security_email(email, "Reset your Nexora AI Trader password", f"Reset your password here:\n{link}")
    audit_log("password_reset_sent", email, f"sent={sent}")
    return sent, link

def encrypt_text(value):
    if not value:
        return None
    try:
        return cipher.encrypt(value.encode()).decode()
    except Exception as e:
        log(f"encrypt_text error: {e}")
        return None


def decrypt_text(value):
    if not value:
        return None
    try:
        return cipher.decrypt(value.encode()).decode()
    except Exception as e:
        log(f"decrypt_text error: {e}")
        return None

def db():
    """
    Railway-safe Postgres connection
    """
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL")

    if not database_url:
        raise Exception("DATABASE_URL not found in Railway Variables")

    database_url = database_url.strip()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return psycopg2.connect(
        database_url,
        sslmode="require"
    )


def is_admin_email(email):
    try:
        return str(email or "").strip().lower() == ADMIN_EMAIL and ADMIN_EMAIL != ""
    except:
        return False


def admin_required():
    if not session.get("user"):
        return False
    return is_admin_email(session.get("user"))


def generate_referral_code(chat_id):
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"{chat_id}_{random_part}"


def ensure_user_has_referral_code(chat_id, conn):
    cur = conn.cursor()

    cur.execute("""
        SELECT referral_code
        FROM users
        WHERE chat_id = %s
        ORDER BY 
            CASE 
                WHEN is_admin = 1 THEN 1
                WHEN is_paid = 1 THEN 2
                ELSE 3
            END,
            id DESC
        LIMIT 1
    """, (chat_id,))
    result = cur.fetchone()

    if result and result[0]:
        return result[0]

    new_code = generate_referral_code(chat_id)

    cur.execute("""
        UPDATE users
        SET referral_code = %s
        WHERE chat_id = %s
    """, (new_code, chat_id))

    conn.commit()
    return new_code


def telegram_referral_link(referral_code):
    return f"{current_base_url()}/r/{referral_code}"


def telegram_deep_referral_link(referral_code):
    return f"{current_bot_link()}?start=ref_{referral_code}"


def send(chat_id, text):
    if not TOKEN or not chat_id:
        log(f"⚠️ TELEGRAM_TOKEN missing or chat_id empty | chat_id={chat_id}")
        return False
    

    try:
        user_link = f"{current_base_url()}/login?chat_id={chat_id}"

        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": str(chat_id),
                "text": text,
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {
                                "text": "🌐 الدخول إلى حسابك",
                                "url": user_link
                            }
                        ]
                    ]
                }
            },
            timeout=10
        )

        if r.status_code != 200:
            log(f"❌ Telegram send failed: {r.text}")
            return False

        data = r.json()
        if not data.get("ok"):
            log(f"❌ Telegram API error: {data}")
            return False

        return True

    except Exception as e:
        log(f"❌ Telegram Error: {e}")
        return False

    
def format_signal(s):
    if not s:
        return "لا توجد إشارة حالياً"

    trade_type = s.get("type", "FUTURES")
    return f"""
🔥 {s.get('pair', 'N/A')}

📊 Type: {trade_type}
📈 Direction: {s.get('direction', 'N/A')}

💰 Entry: {s.get('entry', 'N/A')}
🎯 TP: {s.get('tp', 'N/A')}
🛑 SL: {s.get('sl', 'N/A')}

📊 Confidence: {s.get('confidence', 'N/A')}%
🧠 AI Confidence: {s.get('engine_confidence', s.get('confidence', 'N/A'))}%
🛡 Risk Score: {s.get('risk_score', 'N/A')} / 100 ({s.get('risk_level', 'N/A')})
🔭 Multi-Timeframe: {s.get('multi_timeframe', 'N/A')}
📉 Trend: {s.get('trend', 'N/A')}
📦 Volume: {s.get('volume', 'N/A')}
🌊 Volatility: {s.get('volatility_state', 'N/A')}
🧱 Structure: {s.get('market_structure', s.get('structure', 'N/A'))}
⚖️ Spot/Futures Score: {s.get('spot_score', 'N/A')} / {s.get('futures_score', 'N/A')}
🧠 Smart Money: {s.get('smc', 'N/A')}
⏱ Timeframe: {s.get('timeframe', 'N/A')}
"""
def can_receive_signals(user):
    """
    user tuple columns:
    0 id
    1 email
    2 password
    3 chat_id
    4 is_paid
    5 plan
    6 trial_start
    7 trades
    8 expiry
    9 api_key
    10 api_secret
    11 profit
    12 trade_amount
    13 trade_type
    14 bot_active
    15 referral_code
    16 referred_by
    17 affiliate_balance
    18 total_referrals
    19 free_basic_unlocked
    20 free_pro_unlocked
    21 free_vip_unlocked
    22 is_admin
    23 lifetime_owner
    """
    try:
        plan = user[5]
        trades = user[7]
        expiry = user[8]

        if user[22] == 1:
            return True

        # trial: أول إشارتين فقط
        if plan == "trial":
            return trades < 2

        # باقات مدفوعة
        if user[4] != 1:
            return False

        if not expiry:
            return False

        expiry_date = datetime.strptime(str(expiry), "%Y-%m-%d")
        return datetime.now() <= expiry_date

    except Exception as e:
        log(f"can_receive_signals error: {e}")
        return False


# ================= INIT DB =================
def init_db():
    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            chat_id TEXT,
            is_paid INTEGER DEFAULT 0,
            plan TEXT DEFAULT 'trial',
            trial_start TEXT,
            trades INTEGER DEFAULT 0,
            expiry TEXT,
            api_key TEXT,
            api_secret TEXT,
            profit REAL DEFAULT 0,
            trade_amount REAL DEFAULT 10,
            trade_type TEXT DEFAULT 'futures',
            spot_enabled INTEGER DEFAULT 1,
            futures_enabled INTEGER DEFAULT 1,
            bot_active INTEGER DEFAULT 0,
            referral_code TEXT,
            referred_by TEXT,
            affiliate_balance REAL DEFAULT 0,
            total_referrals INTEGER DEFAULT 0,
            free_basic_unlocked INTEGER DEFAULT 0,
            free_pro_unlocked INTEGER DEFAULT 0,
            free_vip_unlocked INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            lifetime_owner INTEGER DEFAULT 0
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS affiliate_referrals (
            id SERIAL PRIMARY KEY,
            referrer_chat_id TEXT,
            referred_chat_id TEXT,
            referred_email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS affiliate_commissions (
            id SERIAL PRIMARY KEY,
            referrer_chat_id TEXT,
            referred_chat_id TEXT,
            plan TEXT,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'approved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS affiliate_withdrawals (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            wallet_address TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS telegram_referrals (
            telegram_id TEXT PRIMARY KEY,
            referral_code TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS processed_payments (
            payment_id TEXT PRIMARY KEY,
            order_id TEXT,
            payment_status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS payment_invoices (
            id SERIAL PRIMARY KEY,
            invoice_id TEXT,
            payment_id TEXT,
            chat_id TEXT,
            email TEXT,
            plan TEXT,
            status TEXT DEFAULT 'created',
            amount REAL DEFAULT 0,
            original_amount REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'usd',
            coupon_code TEXT,
            invoice_url TEXT,
            raw_response TEXT,
            paid_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            discount_percent REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            expires_at TEXT,
            max_redemptions INTEGER,
            redemption_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS failed_payments (
            id SERIAL PRIMARY KEY,
            payment_id TEXT,
            invoice_id TEXT,
            order_id TEXT,
            plan TEXT,
            payment_status TEXT,
            reason TEXT,
            raw_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS subscription_renewals (
            id SERIAL PRIMARY KEY,
            chat_id TEXT,
            email TEXT,
            plan TEXT,
            payment_id TEXT,
            previous_expiry TEXT,
            new_expiry TEXT,
            amount REAL DEFAULT 0,
            renewal_type TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            action TEXT,
            email TEXT,
            ip_address TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # إضافات أمان لو الجدول قديم

        try:
            c.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        except Exception as ext_err:
            log(f"pgcrypto extension warning: {ext_err}")

        managed_tables = [
            "users",
            "affiliate_referrals",
            "affiliate_commissions",
            "affiliate_withdrawals",
            "telegram_referrals",
            "processed_payments",
            "payment_invoices",
            "coupons",
            "failed_payments",
            "subscription_renewals",
            "audit_logs",
        ]

        for table_name in managed_tables:
            c.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS uuid TEXT DEFAULT gen_random_uuid()::text")
            c.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            c.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL")
            c.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{table_name}_uuid ON {table_name} (uuid)")
            c.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_deleted_at ON {table_name} (deleted_at)")

        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_secret TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profit REAL DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trade_amount REAL DEFAULT 10")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trade_type TEXT DEFAULT 'futures'")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spot_enabled INTEGER DEFAULT 1")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS futures_enabled INTEGER DEFAULT 1")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spot_auto_trade_enabled INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS futures_auto_trade_enabled INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS max_trade_size REAL DEFAULT 10")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stop_loss_required INTEGER DEFAULT 1")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bot_active INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_paid INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'trial'")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_start TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trades INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS expiry TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS chat_id TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS affiliate_balance REAL DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_referrals INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS free_basic_unlocked INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS free_pro_unlocked INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS free_vip_unlocked INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS lifetime_owner INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_sent_at TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires_at TEXT")
        c.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS plan TEXT")
        c.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS amount REAL DEFAULT 0")
        c.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'usd'")
        c.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS invoice_id TEXT")
        c.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS invoice_url TEXT")
        c.execute("ALTER TABLE processed_payments ADD COLUMN IF NOT EXISTS raw_payload TEXT")
        c.execute("ALTER TABLE affiliate_commissions ADD COLUMN IF NOT EXISTS payment_id TEXT")

        # تنظيف chat_id
        c.execute("""
            UPDATE users
            SET chat_id = TRIM(chat_id)
            WHERE chat_id IS NOT NULL
        """)

        # منع تكرار chat_id
        try:
            c.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS users_chat_id_unique
                ON users (chat_id)
                WHERE chat_id IS NOT NULL AND chat_id <> ''
            """)

            c.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_users_plan_paid ON users (plan, is_paid)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_users_referral_code ON users (referral_code)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_referrals_referrer ON affiliate_referrals (referrer_chat_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_referrals_referred ON affiliate_referrals (referred_chat_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_commissions_referrer ON affiliate_commissions (referrer_chat_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_commissions_status ON affiliate_commissions (status)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_commissions_payment_id ON affiliate_commissions (payment_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_affiliate_withdrawals_chat_status ON affiliate_withdrawals (chat_id, status)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_processed_payments_order_id ON processed_payments (order_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_processed_payments_invoice_id ON processed_payments (invoice_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_chat_created ON payment_invoices (chat_id, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_status ON payment_invoices (status)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_invoice_id ON payment_invoices (invoice_id)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_payment_invoices_status_created ON payment_invoices (status, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_processed_payments_status_created ON processed_payments (payment_status, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_coupons_code ON coupons (code)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_failed_payments_created ON failed_payments (created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_subscription_renewals_chat_created ON subscription_renewals (chat_id, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_subscription_renewals_type_created ON subscription_renewals (renewal_type, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_users_paid_created ON users (is_paid, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_email_created ON audit_logs (email, created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action_created ON audit_logs (action, created_at)")
            c.execute("""
                DO $$
                BEGIN
                    IF to_regclass('public.trades_log') IS NOT NULL THEN
                        CREATE INDEX IF NOT EXISTS ix_trades_log_status_created ON trades_log (status, created_at);
                        CREATE INDEX IF NOT EXISTS ix_trades_log_type_status ON trades_log (LOWER(COALESCE(trade_type, 'futures')), status);
                        CREATE INDEX IF NOT EXISTS ix_trades_log_chat_created ON trades_log (chat_id, created_at);
                        CREATE INDEX IF NOT EXISTS ix_trades_log_closed_pnl ON trades_log (status, pnl);
                    END IF;
                END $$;
            """)

            constraints = [
                ("users", "ck_users_plan", "plan IN ('trial', 'basic', 'pro', 'vip', 'pro_2y')"),
                ("users", "ck_users_trade_type", "trade_type IN ('spot', 'futures')"),
                ("users", "ck_users_flags", "is_paid IN (0, 1) AND bot_active IN (0, 1) AND is_admin IN (0, 1) AND lifetime_owner IN (0, 1) AND spot_enabled IN (0, 1) AND futures_enabled IN (0, 1)"),
                ("affiliate_commissions", "ck_affiliate_commissions_amount_nonnegative", "amount >= 0"),
                ("affiliate_withdrawals", "ck_affiliate_withdrawals_amount_positive", "amount > 0"),
                ("affiliate_withdrawals", "ck_affiliate_withdrawals_status", "status IN ('pending', 'paid', 'rejected')"),
                ("coupons", "ck_coupons_discount_range", "discount_percent >= 0 AND discount_percent <= 95"),
                ("coupons", "ck_coupons_active_flag", "active IN (0, 1)"),
                ("payment_invoices", "ck_payment_invoices_amount_nonnegative", "amount >= 0 AND original_amount >= 0 AND discount_amount >= 0"),
            ]

            for table_name, constraint_name, condition in constraints:
                c.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = '{constraint_name}'
                        ) THEN
                            ALTER TABLE {table_name}
                            ADD CONSTRAINT {constraint_name}
                            CHECK ({condition}) NOT VALID;
                        END IF;
                    END $$;
                """)


        except Exception as idx_err:
            log(f"⚠️ chat_id unique index warning: {idx_err}")

        # فعّل الأدمن تلقائيًا لو الإيميل موجود
        if ADMIN_EMAIL:
            c.execute("""
                UPDATE users
                SET is_admin = 1
                WHERE LOWER(email) = %s
            """, (ADMIN_EMAIL,))

        conn.commit()
        conn.close()
        log("✅ DB initialized successfully")

    except Exception as e:
        log(f"❌ init_db error: {e}")
