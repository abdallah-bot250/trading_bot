from flask import Flask, request, render_template, redirect, session, url_for, jsonify
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

# ================= APP =================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

TOKEN = os.environ.get("TELEGRAM_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "https://web-production-c6a34.up.railway.app")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()


# ================= HELPERS =================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


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
                WHEN lifetime_owner = 1 THEN 2
                WHEN is_paid = 1 THEN 3
                ELSE 4
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


def send(chat_id, text):
    if not TOKEN or not chat_id:
        log(f"⚠️ TELEGRAM_TOKEN missing or chat_id empty | chat_id={chat_id}")
        return False

    try:
        user_link = f"{BASE_URL}/login?chat_id={chat_id}"

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
        return "❌ لا توجد إشارة حالياً"

    trade_type = s.get("type", "FUTURES")
    return f"""
🔥 {s.get('pair', 'N/A')}

📊 Type: {trade_type}
📈 Direction: {s.get('direction', 'N/A')}

💰 Entry: {s.get('entry', 'N/A')}
🎯 TP: {s.get('tp', 'N/A')}
🛑 SL: {s.get('sl', 'N/A')}

📊 Confidence: {s.get('confidence', 'N/A')}%
📉 Trend: {s.get('trend', 'N/A')}
📦 Volume: {s.get('volume', 'N/A')}
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

        if user[22] == 1 or user[23] == 1:
            return True

        # trial: أول إشارتين فقط
        if plan == "trial":
            return trades < 2

        # باقات مدفوعة
        if user[4] != 1:
            return False

        if not expiry:
            return False

        if str(expiry).lower() == "lifetime":
            return True

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

        # إضافات أمان لو الجدول قديم
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_secret TEXT")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profit REAL DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trade_amount REAL DEFAULT 10")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trade_type TEXT DEFAULT 'futures'")
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


init_db()


# ================= ROUTES =================
@app.route("/")
def home():
    return "🔥 BOT RUNNING - NEW VERSION OK"


@app.route("/health")
def health():
    return {
        "status": "ok",
        "service": "web",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@app.route("/success")
def success():
    return "✅ تم إنشاء الدفع بنجاح، انتظر تأكيد الشبكة"


@app.route("/cancel")
def cancel():
    return "❌ تم إلغاء الدفع"


@app.route("/debug-users")
def debug_users():
    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
            SELECT id, email, chat_id, plan, is_paid, bot_active, expiry, referral_code, affiliate_balance
            FROM users
            ORDER BY id DESC
        """)
        users = c.fetchall()

        conn.close()

        return f"<pre>{users}</pre>"

    except Exception as e:
        return f"ERROR: {str(e)}"


@app.route("/test-db")
def test_db():
    try:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT NOW()")
        now = c.fetchone()
        conn.close()
        return f"✅ DB OK: {now}"
    except Exception as e:
        return f"❌ DB ERROR: {str(e)}"


@app.route("/test-telegram")
def test_telegram():
    try:
        chat_id = request.args.get("chat_id", "").strip()

        if not chat_id:
            return "❌ لازم تحط chat_id في الرابط"

        ok = send(chat_id, f"✅ TEST FROM WEB APP\n🕒 {datetime.now()}")

        return "✅ تم الإرسال" if ok else "❌ فشل الإرسال"

    except Exception as e:
        return f"ERROR: {str(e)}"


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    chat_id = (request.args.get("chat_id") or session.get("chat_id") or "").strip()
    ref = (request.args.get("ref") or session.get("ref") or "").strip()

    if request.args.get("chat_id"):
        session["chat_id"] = request.args.get("chat_id").strip()

    if request.args.get("ref"):
        session["ref"] = request.args.get("ref").strip()

    if request.method == "POST":
        try:
            email = (request.form.get("email") or "").strip().lower()
            password_raw = (request.form.get("password") or "").strip()

            if not email or not password_raw:
                return "❌ لازم تكتب الإيميل والباسورد"

            email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
            if not re.match(email_pattern, email):
                return "❌ لازم تدخل إيميل صحيح"

            if len(password_raw) < 6:
                return "❌ الباسورد لازم يكون 6 أحرف أو أكثر"

            conn = db()
            c = conn.cursor()

            telegram_ref = None
            if chat_id and not ref:
                try:
                    c.execute("""
                        SELECT referral_code
                        FROM telegram_referrals
                        WHERE telegram_id = %s
                        LIMIT 1
                    """, (chat_id,))
                    tg_ref = c.fetchone()
                    if tg_ref and tg_ref[0]:
                        telegram_ref = str(tg_ref[0]).strip()
                        log(f"✅ Telegram referral loaded in register: {chat_id} -> {telegram_ref}")
                except Exception as tg_err:
                    log(f"❌ Telegram referral fetch error in register: {tg_err}")

            final_ref = ref or telegram_ref

            c.execute("""
                SELECT id, email, password, chat_id, is_admin, plan, is_paid
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
            """, (email,))
            existing = c.fetchone()

            if existing:
                user_id = existing[0]
                stored_password = existing[2]

                if not check_password_hash(stored_password, password_raw):
                    conn.close()
                    return "❌ هذا الإيميل مسجل بالفعل لكن كلمة السر غير صحيحة"

                if chat_id:
                    c.execute("""
                        UPDATE users
                        SET chat_id = NULL
                        WHERE chat_id = %s AND id != %s
                    """, (chat_id, user_id))

                    c.execute("""
                        UPDATE users
                        SET chat_id = %s
                        WHERE id = %s
                    """, (chat_id, user_id))
                    conn.commit()

                    ensure_user_has_referral_code(chat_id, conn)

                if final_ref:
                    c.execute("""
                        SELECT referred_by, chat_id
                        FROM users
                        WHERE id = %s
                        LIMIT 1
                    """, (user_id,))
                    existing_user_data = c.fetchone()

                    current_referred_by = existing_user_data[0] if existing_user_data else None
                    current_chat_id = str(existing_user_data[1] or "").strip() if existing_user_data else ""

                    c.execute("SELECT chat_id FROM users WHERE referral_code = %s LIMIT 1", (final_ref,))
                    ref_user = c.fetchone()

                    if ref_user and not current_referred_by:
                        ref_owner_chat_id = str(ref_user[0] or "").strip()
                        if ref_owner_chat_id != current_chat_id:
                            c.execute("""
                                UPDATE users
                                SET referred_by = %s
                                WHERE id = %s
                            """, (final_ref, user_id))
                            conn.commit()
                            log(f"✅ Existing user referred_by updated: {email} -> {final_ref}")

                if is_admin_email(email):
                    c.execute("""
                        UPDATE users
                        SET is_admin = 1
                        WHERE id = %s
                    """, (user_id,))
                    conn.commit()

                conn.close()

                session["user"] = email
                session["is_admin"] = True if is_admin_email(email) else False

                log(f"✅ Existing user logged in from register: {email} | chat_id={chat_id} | ref={final_ref}")
                return redirect("/dashboard")

            password = generate_password_hash(password_raw)

            referred_by = None
            if final_ref:
                c.execute("SELECT chat_id FROM users WHERE referral_code = %s LIMIT 1", (final_ref,))
                ref_user = c.fetchone()
                if ref_user and str(ref_user[0] or "").strip() != str(chat_id).strip():
                    referred_by = final_ref

            c.execute("""
            INSERT INTO users (
                email, password, chat_id, is_paid, plan, trial_start, trades,
                expiry, api_key, api_secret, profit, trade_amount, trade_type,
                bot_active, referred_by, is_admin, lifetime_owner
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """, (
                email,
                password,
                chat_id,
                0,
                "trial",
                datetime.now().strftime("%Y-%m-%d"),
                0,
                None,
                None,
                None,
                0,
                10,
                "futures",
                0,
                referred_by,
                1 if is_admin_email(email) else 0,
                0
            ))

            new_user = c.fetchone()
            conn.commit()

            if chat_id:
                ensure_user_has_referral_code(chat_id, conn)

            conn.close()

            session["user"] = email
            session["is_admin"] = True if is_admin_email(email) else False

            log(f"✅ New user registered: {email} | chat_id={chat_id} | ref={final_ref}")
            return redirect("/dashboard")

        except Exception as e:
            log(f"❌ Register error: {e}")
            return f"❌ حصل خطأ أثناء التسجيل: {str(e)}"

    return render_template("register.html", chat_id=chat_id, ref=ref)


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    chat_id = (request.args.get("chat_id") or session.get("chat_id") or "").strip()

    if request.args.get("chat_id"):
        session["chat_id"] = request.args.get("chat_id").strip()

    if request.method == "POST":
        try:
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()

            if not email or not password:
                return "❌ لازم تكتب الإيميل والباسورد"

            email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
            if not re.match(email_pattern, email):
                return "❌ لازم تدخل إيميل صحيح"

            conn = db()
            c = conn.cursor()

            c.execute("""
                SELECT * FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
            """, (email,))
            user = c.fetchone()

            if not user:
                conn.close()
                return "❌ الإيميل غير موجود"

            stored_password = str(user[2] or "").strip()

            if check_password_hash(stored_password, password):
                user_id = user[0]

                if chat_id:
                    c.execute("""
                        UPDATE users
                        SET chat_id = NULL
                        WHERE chat_id = %s AND id != %s
                    """, (chat_id, user_id))

                    c.execute("""
                        UPDATE users
                        SET chat_id = %s
                        WHERE id = %s
                    """, (chat_id, user_id))
                    conn.commit()

                    ensure_user_has_referral_code(chat_id, conn)

                session["user"] = email
                session["is_admin"] = True if is_admin_email(email) else False
                log(f"✅ Login success: {email} | chat_id={chat_id}")
                conn.close()
                return redirect("/dashboard")

            conn.close()
            return "❌ الباسورد غير صحيح"

        except Exception as e:
            log(f"❌ Login error: {e}")
            return f"❌ حصل خطأ أثناء تسجيل الدخول: {str(e)}"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ================= SAVE API =================
@app.route("/save-api", methods=["POST"])
def save_api():
    if not session.get("user"):
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            "SELECT plan FROM users WHERE email = %s",
            (session["user"],)
        )
        user = c.fetchone()

        if not user or user[0] != "vip":
            conn.close()
            return "❌ API متاح فقط لباقة VIP"

        api_key = request.form.get("api_key", "").strip()
        api_secret = request.form.get("api_secret", "").strip()

        if not api_key or not api_secret:
            conn.close()
            return "❌ لازم تدخل API Key و Secret"

        c.execute("""
            UPDATE users
            SET api_key = %s, api_secret = %s
            WHERE email = %s
        """, (api_key, api_secret, session["user"]))

        conn.commit()
        conn.close()

        return "✅ تم ربط الحساب بنجاح"

    except Exception as e:
        log(f"❌ save_api error: {e}")
        return f"❌ حصل خطأ أثناء حفظ API: {str(e)}"


# ================= SAVE SETTINGS =================
@app.route("/save-settings", methods=["POST"])
def save_settings():
    if not session.get("user"):
        return redirect("/login")

    try:
        trade_amount = request.form.get("trade_amount", "10").strip()
        trade_type = request.form.get("trade_type", "futures").strip().lower()

        try:
            trade_amount = float(trade_amount)
        except:
            trade_amount = 10

        if trade_amount <= 0:
            trade_amount = 10

        if trade_type not in ["spot", "futures"]:
            trade_type = "futures"

        conn = db()
        c = conn.cursor()
        c.execute("""
            UPDATE users
            SET trade_amount = %s, trade_type = %s
            WHERE email = %s
        """, (trade_amount, trade_type, session["user"]))
        conn.commit()
        conn.close()

        return "✅ تم حفظ إعدادات التداول"

    except Exception as e:
        log(f"❌ save_settings error: {e}")
        return f"❌ حصل خطأ أثناء حفظ الإعدادات: {str(e)}"


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        c.execute("SELECT * FROM users WHERE LOWER(email) = %s", (session["user"].lower(),))
        user = c.fetchone()

        if not user:
            conn.close()
            session.clear()
            return redirect("/login")

        chat_id = str(user.get("chat_id") or "").strip()

        referral_link = ""
        if chat_id:
            referral_code = user.get("referral_code")
            if not referral_code:
                referral_code = ensure_user_has_referral_code(chat_id, conn)
                c.execute("SELECT * FROM users WHERE LOWER(email) = %s", (session["user"].lower(),))
                user = c.fetchone()

            referral_link = f"https://t.me/pro_crypto_99_bot?start=ref_{user['referral_code']}"

        c.execute("""
            SELECT COUNT(*) AS total_refs
            FROM affiliate_referrals
            WHERE referrer_chat_id = %s
        """, (chat_id,))
        refs_count = c.fetchone()["total_refs"] if chat_id else 0

        c.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_comm
            FROM affiliate_commissions
            WHERE referrer_chat_id = %s
        """, (chat_id,))
        total_comm = c.fetchone()["total_comm"] if chat_id else 0

        c.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_withdrawn
            FROM affiliate_withdrawals
            WHERE chat_id = %s AND status = 'paid'
        """, (chat_id,))
        total_withdrawn = c.fetchone()["total_withdrawn"] if chat_id else 0

        conn.close()

        return render_template(
            "dashboard.html",
            plan=user.get("plan"),
            expiry=user.get("expiry"),
            profit=user.get("profit", 0),
            trades=user.get("trades", 0),
            bot_active=user.get("bot_active", 0),
            trade_amount=user.get("trade_amount", 10),
            trade_type=user.get("trade_type", "futures"),
            referral_link=referral_link,
            affiliate_balance=round(float(user.get("affiliate_balance", 0) or 0), 2),
            total_referrals=refs_count,
            total_commissions=round(float(total_comm or 0), 2),
            total_withdrawn=round(float(total_withdrawn or 0), 2),
            is_admin=user.get("is_admin", 0),
            free_basic_unlocked=user.get("free_basic_unlocked", 0),
            free_pro_unlocked=user.get("free_pro_unlocked", 0),
            free_vip_unlocked=user.get("free_vip_unlocked", 0),
            chat_id=chat_id
        )

    except Exception as e:
        log(f"❌ dashboard error: {e}")
        return f"❌ حصل خطأ أثناء تحميل الداشبورد: {str(e)}"


@app.route("/manual")
def manual():
    if "user" not in session:
        return redirect("/login")
    return render_template("manual.html")


# ================= SIMPLE DATA API =================
@app.route("/api/data")
def api_data():
    if not session.get("user"):
        return jsonify({})

    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT email, profit FROM users WHERE LOWER(email) = %s", (session["user"].lower(),))
        user = c.fetchone()
        conn.close()

        if not user:
            return jsonify({})

        return jsonify({
            user["email"]: {
                "amount": float(user.get("profit", 0) or 0)
            }
        })

    except Exception as e:
        log(f"api_data error: {e}")
        return jsonify({})


# ================= TOGGLE BOT =================
@app.route("/toggle-bot", methods=["POST"])
def toggle_bot():
    if not session.get("user"):
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            "SELECT plan, bot_active FROM users WHERE LOWER(email) = %s",
            (session["user"].lower(),)
        )
        user = c.fetchone()

        if not user or user[0] != "vip":
            conn.close()
            return "❌ الميزة متاحة لـ VIP فقط"

        new_status = 0 if user[1] == 1 else 1

        c.execute("""
            UPDATE users
            SET bot_active = %s
            WHERE LOWER(email) = %s
        """, (new_status, session["user"].lower()))

        conn.commit()
        conn.close()

        return "🟢 تم تشغيل البوت" if new_status == 1 else "🔴 تم إيقاف البوت"

    except Exception as e:
        log(f"❌ toggle_bot error: {e}")
        return f"❌ حصل خطأ أثناء تشغيل/إيقاف البوت: {str(e)}"


# ================= CREATE PAYMENT =================
@app.route("/create-payment")
def create_payment():
    if not session.get("user"):
        return redirect("/login")

    plan = request.args.get("plan", "basic").strip().lower()

    prices = {
        "basic": 25,
        "pro": 59.99,
        "vip": 100
    }

    if plan not in prices:
        return "❌ باقة غير صحيحة"

    amount = prices[plan]

    try:
        nowpayments_key = os.environ.get("NOWPAYMENTS_API_KEY")
        if not nowpayments_key:
            return "❌ NOWPAYMENTS_API_KEY غير موجود في Railway Variables"

        conn = db()
        c = conn.cursor()

        c.execute(
            "SELECT chat_id FROM users WHERE LOWER(email) = %s",
            (session["user"].lower(),)
        )
        user = c.fetchone()
        conn.close()

        if not user or not user[0]:
            return "❌ لازم تربط حساب التليجرام الأول"

        chat_id = str(user[0]).strip()

        payload = {
            "price_amount": amount,
            "price_currency": "usd",
            "pay_currency": "usdttrc20",
            "order_id": chat_id,
            "order_description": plan,
            "success_url": f"{BASE_URL}/success",
            "cancel_url": f"{BASE_URL}/cancel",
            "ipn_callback_url": f"{BASE_URL}/payment-webhook"
        }

        headers = {
            "x-api-key": nowpayments_key,
            "Content-Type": "application/json"
        }

        r = requests.post(
            "https://api.nowpayments.io/v1/invoice",
            json=payload,
            headers=headers,
            timeout=20
        )

        try:
            data = r.json()
        except:
            data = {"raw_response": r.text}

        log(f"NOWPayments response: {data}")

        if data.get("invoice_url"):
            return redirect(data["invoice_url"])

        return f"""
        <html>
        <head>
        <title>Payment</title>
        <style>
        body {{
            background: #0f172a;
            color: white;
            font-family: Arial;
            text-align: center;
            padding: 50px;
        }}
        .box {{
            background: #1e293b;
            padding: 30px;
            border-radius: 15px;
            width: 350px;
            margin: auto;
        }}
        </style>
        </head>
        <body>
        <div class="box">
            <h2>💰 Payment Error</h2>
            <p>حصل مشكلة في إنشاء صفحة الدفع</p>
            <pre>{data}</pre>
        </div>
        </body>
        </html>
        """

    except Exception as e:
        log(f"❌ create_payment error: {e}")
        return f"Error: {str(e)}"


# ================= OWNER FREE UPGRADE =================
@app.route("/owner-free-upgrade")
def owner_free_upgrade():
    if not session.get("user"):
        return redirect("/login")

    if not admin_required():
        return "❌ غير مصرح"

    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
            UPDATE users
            SET is_paid = 1,
                plan = 'vip',
                expiry = 'lifetime',
                is_admin = 1,
                lifetime_owner = 1,
                bot_active = 1
            WHERE LOWER(email) = %s
        """, (session["user"].lower(),))

        conn.commit()
        conn.close()

        return "✅ تم تفعيل VIP مدى الحياة لحسابك"

    except Exception as e:
        log(f"owner_free_upgrade error: {e}")
        return f"❌ Error: {str(e)}"


# ================= REQUEST WITHDRAWAL =================
@app.route("/request-withdrawal", methods=["POST"])
def request_withdrawal():
    if not session.get("user"):
        return redirect("/login")

    try:
        wallet_address = request.form.get("wallet_address", "").strip()
        amount = request.form.get("amount", "0").strip()

        try:
            amount = float(amount)
        except:
            amount = 0

        if not wallet_address:
            return "❌ لازم تدخل عنوان المحفظة"

        if amount < 25:
            return "❌ الحد الأدنى للسحب 25$"

        if amount > 300:
            return "❌ الحد الأقصى للسحب 300$"

        conn = db()
        c = conn.cursor()

        c.execute("""
            SELECT chat_id, affiliate_balance
            FROM users
            WHERE LOWER(email) = %s
        """, (session["user"].lower(),))
        user = c.fetchone()

        if not user:
            conn.close()
            return "❌ المستخدم غير موجود"

        chat_id = str(user[0] or "").strip()
        balance = float(user[1] or 0)

        if amount > balance:
            conn.close()
            return "❌ الرصيد غير كافي"

        c.execute("""
            INSERT INTO affiliate_withdrawals (chat_id, wallet_address, amount, status)
            VALUES (%s, %s, %s, %s)
        """, (chat_id, wallet_address, amount, "pending"))

        c.execute("""
            UPDATE users
            SET affiliate_balance = affiliate_balance - %s
            WHERE LOWER(email) = %s
        """, (amount, session["user"].lower()))

        conn.commit()
        conn.close()

        return "✅ تم إرسال طلب السحب بنجاح"

    except Exception as e:
        log(f"request_withdrawal error: {e}")
        return f"❌ Error: {str(e)}"


# ================= ADMIN =================
def current_admin_email():
    return (session.get("user") or "").strip().lower()


def is_current_admin():
    email = current_admin_email()
    if not email:
        return False

    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
            SELECT is_admin
            FROM users
            WHERE LOWER(email) = %s
            LIMIT 1
        """, (email,))
        row = c.fetchone()
        conn.close()

        if not row:
            return False

        return bool(row[0]) or is_admin_email(email)

    except Exception as e:
        log(f"is_current_admin error: {e}")
        return False


@app.route("/admin")
def admin_dashboard():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        conn = db()
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE is_paid = 1")
        paid_users = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0) FROM affiliate_commissions")
        total_affiliate_paid = float(c.fetchone()[0] or 0)

        revenue = (paid_users * 25)

        c.execute("""
            SELECT id, email, plan, is_paid, expiry, chat_id, affiliate_balance, total_referrals
            FROM users
            ORDER BY id DESC
        """)
        users = c.fetchall()

        c.execute("""
            SELECT id, chat_id, wallet_address, amount, status, created_at
            FROM affiliate_withdrawals
            ORDER BY id DESC
        """)
        withdrawals = c.fetchall()

        conn.close()

        return render_template(
            "admin.html",
            total_users=total_users,
            paid_users=paid_users,
            revenue=revenue,
            total_affiliate_paid=total_affiliate_paid,
            users=users,
            withdrawals=withdrawals
        )

    except Exception as e:
        log(f"admin_dashboard error: {e}")
        return f"❌ Error: {str(e)}"


@app.route("/activate-user", methods=["POST"])
def activate_user():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        user_id = request.form.get("id", "").strip()
        plan = request.form.get("plan", "basic").strip().lower()

        if plan not in ["basic", "pro", "vip"]:
            plan = "basic"

        expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        conn = db()
        c = conn.cursor()

        c.execute("""
            UPDATE users
            SET is_paid = 1, plan = %s, expiry = %s, bot_active = CASE WHEN %s = 'vip' THEN 1 ELSE bot_active END
            WHERE id = %s
        """, (plan, expiry, plan, user_id))

        conn.commit()
        conn.close()

        log(f"✅ User {user_id} activated with plan {plan}")
        return redirect("/admin")

    except Exception as e:
        log(f"activate_user error: {e}")
        return f"❌ Error: {str(e)}"


@app.route("/delete-user", methods=["POST"])
def delete_user():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        user_id = request.form.get("id", "").strip()

        conn = db()
        c = conn.cursor()

        current_email = current_admin_email()
        c.execute("SELECT email FROM users WHERE id = %s LIMIT 1", (user_id,))
        row = c.fetchone()

        if row and row[0].strip().lower() == current_email:
            conn.close()
            return "❌ لا يمكن حذف حساب الأدمن الحالي"

        c.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()

        log(f"🗑️ Deleted user {user_id}")
        return redirect("/admin")

    except Exception as e:
        log(f"delete_user error: {e}")
        return f"❌ Error: {str(e)}"


@app.route("/mark-withdrawal-paid", methods=["POST"])
def mark_withdrawal_paid():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        withdrawal_id = request.form.get("id", "").strip()

        conn = db()
        c = conn.cursor()
        c.execute("""
            UPDATE affiliate_withdrawals
            SET status = 'paid'
            WHERE id = %s
        """, (withdrawal_id,))
        conn.commit()
        conn.close()

        log(f"💸 Withdrawal {withdrawal_id} marked as paid")
        return redirect("/admin")

    except Exception as e:
        log(f"mark_withdrawal_paid error: {e}")
        return f"❌ Error: {str(e)}"


# ================= TELEGRAM WEBHOOK =================
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}

        message = data.get("message", {}) or {}
        chat = message.get("chat", {}) or {}
        text = (message.get("text") or "").strip()
        chat_id = str(chat.get("id") or "").strip()

        if not chat_id:
            log("⚠️ Telegram webhook received without chat_id")
            return "ok", 200

        log(f"📩 Telegram message | chat_id={chat_id} | text={text}")

        # ================= /start =================
        if text.startswith("/start"):
            start_ref = None
            parts = text.split()

            if len(parts) > 1 and parts[1].startswith("ref_"):
                start_ref = parts[1].replace("ref_", "").strip()

            conn = db()
            c = conn.cursor()

            if start_ref:
                try:
                    c.execute("""
                        CREATE TABLE IF NOT EXISTS telegram_referrals (
                            telegram_id TEXT PRIMARY KEY,
                            referral_code TEXT
                        )
                    """)

                    c.execute("""
                        INSERT INTO telegram_referrals (telegram_id, referral_code)
                        VALUES (%s, %s)
                        ON CONFLICT (telegram_id)
                        DO UPDATE SET referral_code = EXCLUDED.referral_code
                    """, (str(chat_id), start_ref))

                    conn.commit()
                    log(f"✅ Telegram referral saved: {chat_id} -> {start_ref}")

                except Exception as e:
                    log(f"❌ Telegram referral save error: {e}")

            try:
                c.execute("""
                    SELECT id, email, trades, is_paid, referral_code, plan, expiry, is_admin, lifetime_owner
                    FROM users
                    WHERE chat_id = %s
                    ORDER BY 
                        CASE 
                            WHEN is_admin = 1 THEN 1
                            WHEN lifetime_owner = 1 THEN 2
                            WHEN is_paid = 1 THEN 3
                            ELSE 4
                        END,
                        id DESC
                    LIMIT 1
                """, (chat_id,))
                user = c.fetchone()

                if user:
                    user_id = user[0]
                    email = user[1]
                    trades = int(user[2] or 0)
                    is_paid = bool(user[3])
                    referral_code = user[4]
                    current_plan = user[5]
                    expiry = user[6]
                    is_admin_flag = int(user[7] or 0)
                    lifetime_owner = int(user[8] or 0)

                    if not referral_code:
                        referral_code = ensure_user_has_referral_code(chat_id, conn)

                    send(chat_id, "✅ حسابك مربوط بالفعل بالموقع.")

                    if is_admin_flag == 1 or lifetime_owner == 1:
                        send(chat_id, f"""👑 حساب المالك / الأدمن مفعل

📦 الخطة: {current_plan}
⏳ الصلاحية: {expiry}

🚀 هتوصلك الإشارات تلقائيًا.
""")
                        return "ok", 200

                    if is_paid:
                        send(chat_id, "🔥 اشتراكك مفعل، وهتوصلك الإشارات المدفوعة تلقائيًا.")

                        aff_link = f"https://t.me/pro_crypto_99_bot?start=ref_{referral_code}"
                        send(chat_id, f"""💸 رابط الأفلييت الخاص بك:

{aff_link}

📌 كل شخص يدخل من خلالك ويبدأ البوت هيتسجل تحتك.
""")

                        return "ok", 200

                    if trades < 2:
                        free_signals = get_top_free_signals(limit=2)
                        log(f"🎯 Free signals returned: {free_signals}")

                        if not free_signals:
                            send(chat_id, "❌ لا توجد فرصة قوية حاليًا، من فضلك انتظر حتى يظهر دخول قوي.")
                        else:
                            sent_count = 0

                            for i, signal in enumerate(free_signals, 1):
                                success = send(chat_id, f"""🔥 إشارة مجانية #{i}

📊 الزوج: {signal['pair']}
📌 النوع: {signal.get('type', 'FUTURES')}
📈 الاتجاه: {signal['direction']}

📍 الدخول: {signal['entry']}
🎯 الهدف: {signal['tp']}
🛑 وقف الخسارة: {signal['sl']}

📊 الثقة: {signal['confidence']}%
📉 الترند: {signal.get('trend', 'N/A')}
📦 الفوليوم: {signal.get('volume', 'N/A')}
🧠 SMC: {signal.get('smc', 'N/A')}
⏱ الفريم: {signal.get('timeframe', 'N/A')}
""")

                                if success:
                                    sent_count += 1

                            if sent_count > 0:
                                c.execute("""
                                    UPDATE users
                                    SET trades = LEAST(COALESCE(trades, 0) + %s, 2)
                                    WHERE id = %s
                                """, (sent_count, user_id))
                                conn.commit()

                                send(chat_id, f"""🎁 تم إرسال {sent_count} صفقة مجانية من البوت.

📌 مهم:
النسخة المجانية هدفها إنك تشوف طريقة شغل البوت وجودة الفلترة،
لكنها ليست كل إمكانيات النظام.

🚀 في النسخة المدفوعة هتستفيد بـ:
• فرص أقوى
• فلترة أعلى
• إشارات مستمرة حسب حالة السوق
• تقليل الدخول العشوائي
• وفي VIP تقدر تربط حسابك للتنفيذ التلقائي

⚠️ البوت مش بيبعت صفقات لمجرد الإرسال،
هو بيستنى الفرصة الواضحة فقط.

💰 لو حابب تكمل:
ادخل على الموقع وفعّل الباقة المناسبة ليك.
""")
                            else:
                                send(chat_id, "❌ حصلت مشكلة أثناء إرسال الإشارات المجانية. حاول /start مرة تانية.")

                    else:
                        aff_link = f"https://t.me/pro_crypto_99_bot?start=ref_{referral_code}"

                        send(chat_id, f"""📌 أنت استلمت الصفقتين المجانيين بالفعل.

🔥 لو حابب تكمل وتستقبل إشارات أقوى بشكل مستمر،
تقدر تفعّل الباقة المناسبة من الموقع.

💡 البوت بيختار الفرص على حسب حالة السوق،
ومش هدفه كثرة الصفقات... هدفه الجودة أولًا.

💸 ولو حابب تكسب من البوت كمان،
ده رابط الأفلييت الخاص بك:

{aff_link}
""")

                else:
                    register_link = f"{BASE_URL}/register?chat_id={chat_id}"

                    send(chat_id, f"""🔥 أهلاً بيك في AI Crypto Trader

🤖 البوت ده مصمم علشان يفلتر السوق ويختار أفضل الفرص الممكنة فقط،
بدل الدخول العشوائي في أي صفقة.

📌 البوت بيشتغل على:
• تحليل الترند والزخم
• الفوليوم والسيولة
• الفريمات الأكبر للتأكيد
• فلترة الصفقات الضعيفة
• اختيار فرص قليلة لكن أقوى

⚠️ مهم:
البوت مش هدفه يبعت صفقات كتير،
هدفه يبعت صفقات أقوى على قد ما السوق يسمح.

🎁 عندك صفقتين مجانيين بعد التسجيل.

🔗 اربط حسابك من هنا:
{register_link}

🚀 وبعد التسجيل ابعت /start علشان تستقبل أول الصفقات.
""")

            except Exception as db_err:
                log(f"❌ /start DB Error: {db_err}")
                send(chat_id, "❌ حصل خطأ أثناء التحقق من حسابك. حاول تاني بعد شوية.")
            finally:
                conn.close()

            return "ok", 200

        # ================= /affiliate =================
        elif text.startswith("/affiliate"):
            conn = db()
            c = conn.cursor()

            try:
                c.execute("""
                    SELECT referral_code, affiliate_balance, total_referrals
                    FROM users
                    WHERE chat_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (chat_id,))
                user = c.fetchone()

                if not user:
                    send(chat_id, "❌ لازم تسجل في الموقع الأول.")
                    return "ok", 200

                referral_code = user[0]
                balance = float(user[1] or 0)
                refs = int(user[2] or 0)

                if not referral_code:
                    referral_code = ensure_user_has_referral_code(chat_id, conn)

                aff_link = f"https://t.me/pro_crypto_99_bot?start=ref_{referral_code}"

                send(chat_id, f"""💸 نظام الأفلييت

🔗 رابطك:
{aff_link}

👥 عدد الإحالات: {refs}
💰 رصيد العمولة: {round(balance, 2)}$

📌 السحب من الداشبورد
الحد الأدنى: 25$
الحد الأقصى: 300$
⏳ خلال 24 ساعة
""")

            except Exception as e:
                log(f"/affiliate error: {e}")
                send(chat_id, "❌ حصل خطأ أثناء تحميل بيانات الأفلييت.")
            finally:
                conn.close()

        else:
            send(chat_id, """👋 الأوامر المتاحة:

/start - ربط الحساب واستلام الإشارات
/affiliate - عرض رابط الأفلييت والرصيد
""")

    except Exception as e:
        log(f"❌ Telegram Webhook Error: {e}")

    return "ok", 200


# ================= PAYMENT WEBHOOK =================
@app.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    data = request.get_json(silent=True) or {}

    try:
        signature = request.headers.get("x-nowpayments-sig", "").strip()
        ipn_secret = os.environ.get("NOWPAYMENTS_IPN_SECRET", "").strip()

        if not signature or not ipn_secret:
            log("❌ Missing NOWPayments signature or IPN secret")
            return "missing signature", 403

        sorted_data = json.dumps(data, sort_keys=True, separators=(",", ":"))

        generated_sig = hmac.new(
            key=ipn_secret.encode("utf-8"),
            msg=sorted_data.encode("utf-8"),
            digestmod=hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(signature.lower(), generated_sig.lower()):
            log(f"❌ Invalid NOWPayments signature | recv={signature} | gen={generated_sig}")
            return "invalid signature", 403

        payment_status = data.get("payment_status")
        if payment_status in ["finished", "confirmed"]:

            chat_id = str(data.get("order_id") or "").strip()
            plan = (data.get("order_description") or "basic").strip().lower()

            if not chat_id:
                return "missing order_id", 400

            conn = db()
            c = conn.cursor()

            expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            c.execute("""
                SELECT email, referred_by
                FROM users
                WHERE chat_id = %s
                LIMIT 1
            """, (chat_id,))
            buyer = c.fetchone()

            c.execute("""
                UPDATE users
                SET is_paid = 1,
                    plan = %s,
                    expiry = %s,
                    bot_active = CASE WHEN %s = 'vip' THEN 1 ELSE bot_active END
                WHERE chat_id = %s
            """, (plan, expiry, plan, chat_id))

            if buyer:
                buyer_email = buyer[0]
                referred_by = buyer[1]

                if referred_by:
                    c.execute("""
                        SELECT chat_id, email
                        FROM users
                        WHERE referral_code = %s
                        LIMIT 1
                    """, (referred_by,))
                    referrer = c.fetchone()

                    if referrer:
                        referrer_chat_id = str(referrer[0] or "").strip()

                        c.execute("""
                            SELECT id
                            FROM affiliate_referrals
                            WHERE referrer_chat_id = %s
                              AND referred_chat_id = %s
                            LIMIT 1
                        """, (referrer_chat_id, chat_id))
                        already_exists = c.fetchone()

                        if not already_exists:
                            plan_prices = {
                                "basic": 25,
                                "pro": 59.99,
                                "vip": 100
                            }

                            commission_percent_map = {
                                "basic": 0.08,
                                "pro": 0.12,
                                "vip": 0.15
                            }

                            plan_price = float(plan_prices.get(plan, 25))
                            commission_percent = float(commission_percent_map.get(plan, 0.08))
                            commission_amount = round(plan_price * commission_percent, 2)

                            referred_email = buyer_email

                            c.execute("""
                                INSERT INTO affiliate_referrals (
                                    referrer_chat_id,
                                    referred_chat_id,
                                    referred_email
                                )
                                VALUES (%s, %s, %s)
                            """, (referrer_chat_id, chat_id, referred_email))

                            c.execute("""
                                INSERT INTO affiliate_commissions (
                                    referrer_chat_id,
                                    referred_chat_id,
                                    plan,
                                    amount,
                                    status
                                )
                                VALUES (%s, %s, %s, %s, %s)
                            """, (referrer_chat_id, chat_id, plan, commission_amount, "approved"))

                            c.execute("""
                                UPDATE users
                                SET affiliate_balance = COALESCE(affiliate_balance, 0) + %s,
                                    total_referrals = COALESCE(total_referrals, 0) + 1
                                WHERE chat_id = %s
                            """, (commission_amount, referrer_chat_id))

                            c.execute("""
                                SELECT total_referrals, free_basic_unlocked, free_pro_unlocked, free_vip_unlocked
                                FROM users
                                WHERE chat_id = %s
                            """, (referrer_chat_id,))
                            ref_stats = c.fetchone()

                            if ref_stats:
                                total_refs = int(ref_stats[0] or 0)
                                free_basic = int(ref_stats[1] or 0)
                                free_pro = int(ref_stats[2] or 0)
                                free_vip = int(ref_stats[3] or 0)

                                if total_refs >= 15 and free_basic == 0:
                                    c.execute("""
                                        UPDATE users
                                        SET free_basic_unlocked = 1
                                        WHERE chat_id = %s
                                    """, (referrer_chat_id,))
                                    send(referrer_chat_id, "🎁 مبروك! فتحت Basic مجانًا بسبب نظام الأفلييت.")

                                if total_refs >= 25 and free_pro == 0:
                                    c.execute("""
                                        UPDATE users
                                        SET free_pro_unlocked = 1
                                        WHERE chat_id = %s
                                    """, (referrer_chat_id,))
                                    send(referrer_chat_id, "🔥 مبروك! فتحت Pro مجانًا بسبب نظام الأفلييت.")

                                if total_refs >= 32 and free_vip == 0:
                                    c.execute("""
                                        UPDATE users
                                        SET free_vip_unlocked = 1
                                        WHERE chat_id = %s
                                    """, (referrer_chat_id,))
                                    send(referrer_chat_id, "💎 مبروك! فتحت VIP مجانًا بسبب نظام الأفلييت.")

                            send(referrer_chat_id, f"""💸 تم إضافة عمولة جديدة

👤 مستخدم جديد اشترك من خلالك
📦 الخطة: {plan.upper()}
💰 العمولة: {commission_amount}$ ({int(commission_percent * 100)}%)

📌 الرصيد يقدر يتسحب من الداشبورد
""")

            conn.commit()

            c.execute(
                "SELECT chat_id FROM users WHERE chat_id = %s",
                (chat_id,)
            )
            user = c.fetchone()

            conn.close()

            if user and user[0]:
                send(user[0], f"""🔥 تم تفعيل اشتراكك بنجاح!

📦 الباقة: {plan.upper()}
⏳ المدة: 30 يوم

🚀 هتوصلك الإشارات تلقائي الآن
""")

            log(f"✅ Payment activated for chat_id={chat_id}, plan={plan}")

    except Exception as e:
        log(f"❌ Webhook Error: {e}")

    return "OK"


# ================= START =================
if __name__ == "__main__":
    log("🚀 Flask app started")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))