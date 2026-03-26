from flask import Flask, request, render_template, redirect, session, url_for
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

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

TOKEN = os.environ.get("TELEGRAM_TOKEN")
BASE_URL = os.environ.get("BASE_URL", "https://web-production-c6a34.up.railway.app")


# ================= LOG =================
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ================= DB =================
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
            bot_active INTEGER DEFAULT 0
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

        conn.commit()
        conn.close()
        log("✅ DB initialized successfully")

    except Exception as e:
        log(f"❌ init_db error: {e}")


# شغّل التهيئة أول ما التطبيق يقوم
init_db()


# ================= TELEGRAM =================
def send(chat_id, text):
    if not TOKEN or not chat_id:
        log(f"⚠️ TELEGRAM_TOKEN missing or chat_id empty | chat_id={chat_id}")
        return False

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": str(chat_id), "text": text},
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


# ================= SIGNAL FORMAT =================
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


# ================= ACCESS CHECK =================
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
    """
    try:
        plan = user[5]
        trades = user[7]
        expiry = user[8]

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

        c.execute("SELECT id, email, chat_id, plan, is_paid, bot_active, expiry FROM users ORDER BY id DESC")
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


@app.route("/register", methods=["GET", "POST"])
def register():
    chat_id = request.args.get("chat_id") or ""

    if request.method == "POST":
        try:
            email = request.form["email"].strip().lower()
            password_raw = request.form["password"].strip()

            if not email or not password_raw:
                return "❌ لازم تكتب الإيميل والباسورد"

            password = generate_password_hash(password_raw)

            conn = db()
            c = conn.cursor()

            # منع التكرار
            c.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing = c.fetchone()

            if existing:
                conn.close()
                return "❌ الإيميل مسجل بالفعل"

            c.execute("""
            INSERT INTO users (
                email, password, chat_id, is_paid, plan, trial_start, trades,
                expiry, api_key, api_secret, profit, trade_amount, trade_type, bot_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                0
            ))

            conn.commit()
            conn.close()

            session["user"] = email
            log(f"✅ New user registered: {email} | chat_id={chat_id}")
            return redirect("/dashboard")

        except Exception as e:
            log(f"❌ Register error: {e}")
            return f"❌ حصل خطأ أثناء التسجيل: {str(e)}"

    return render_template("register.html", chat_id=chat_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            email = request.form["email"].strip().lower()
            password = request.form["password"]

            conn = db()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = c.fetchone()
            conn.close()

            if user and check_password_hash(user[2], password):
                session["user"] = email
                log(f"✅ Login success: {email}")
                return redirect("/dashboard")

            return "❌ بيانات تسجيل الدخول غير صحيحة"

        except Exception as e:
            log(f"❌ Login error: {e}")
            return f"❌ حصل خطأ أثناء تسجيل الدخول: {str(e)}"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


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

        # ❌ مش VIP
        if not user or user[0] != "vip":
            conn.close()
            return "❌ API متاح فقط لباقة VIP"

        # ✅ VIP فقط
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


@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = %s", (session["user"],))
        user = c.fetchone()
        conn.close()

        if not user:
            session.clear()
            return redirect("/login")

        return render_template(
            "dashboard.html",
            plan=user[5],
            expiry=user[8],
            profit=user[11],
            trades=user[7],
            bot_active=user[14],
            trade_amount=user[12],
            trade_type=user[13]
        )

    except Exception as e:
        log(f"❌ dashboard error: {e}")
        return f"❌ حصل خطأ أثناء تحميل الداشبورد: {str(e)}"


@app.route("/toggle-bot", methods=["POST"])
def toggle_bot():
    if not session.get("user"):
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            "SELECT plan, bot_active FROM users WHERE email = %s",
            (session["user"],)
        )
        user = c.fetchone()

        # ❌ مش VIP
        if not user or user[0] != "vip":
            conn.close()
            return "❌ الميزة متاحة لـ VIP فقط"

        new_status = 0 if user[1] == 1 else 1

        c.execute("""
            UPDATE users
            SET bot_active = %s
            WHERE email = %s
        """, (new_status, session["user"]))

        conn.commit()
        conn.close()

        return "🟢 تم تشغيل البوت" if new_status == 1 else "🔴 تم إيقاف البوت"

    except Exception as e:
        log(f"❌ toggle_bot error: {e}")
        return f"❌ حصل خطأ أثناء تشغيل/إيقاف البوت: {str(e)}"


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
            "SELECT chat_id FROM users WHERE email = %s",
            (session["user"],)
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


# ================= TELEGRAM WEBHOOK =================
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
            conn = db()
            c = conn.cursor()

            try:
                c.execute("""
                    SELECT id, email, trades, is_paid
                    FROM users
                    WHERE chat_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                """, (chat_id,))
                user = c.fetchone()

                if user:
                    user_id = user[0]
                    email = user[1]
                    trades = int(user[2] or 0)
                    is_paid = bool(user[3])

                    send(chat_id, "✅ حسابك مربوط بالفعل بالموقع.")

                    # ================= لو المستخدم مدفوع =================
                    if is_paid:
                        send(chat_id, "🔥 اشتراكك مفعل، وهتوصلك الإشارات المدفوعة تلقائيًا.")
                        return "ok", 200

                    # ================= الإشارتين المجانيين =================
                    if trades < 2:
                        free_signals = get_top_free_signals(limit=2)
                        log(f"🎯 Free signals returned: {free_signals}")

                        if not free_signals:
                            send(chat_id, "❌ لا توجد فرصه قويه من فضلك انتظر حتي يكون لديك صفقه قويه ")
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
⏱ الفريم: {signal.get('timeframe', 'N/A')}
""")

                                if success:
                                    sent_count += 1

                            # نزود العداد فقط لو الرسائل اتبعت فعلاً
                            if sent_count > 0:
                                c.execute("""
                                    UPDATE users
                                    SET trades = LEAST(COALESCE(trades, 0) + %s, 2)
                                    WHERE id = %s
                                """, (sent_count, user_id))
                                conn.commit()

                                send(chat_id, f"🎁 تم إرسال {sent_count} إشارة مجانية حقيقية من البوت.")
                            else:
                                send(chat_id, "❌ حصلت مشكلة أثناء إرسال الإشارات المجانية. حاول /start مرة تانية.")
                    else:
                        send(chat_id, "📌 أنت استلمت الإشارتين المجانيين بالفعل.")

                else:
                    register_link = f"{BASE_URL}/register?chat_id={chat_id}"
                    send(chat_id, f"""🔥 أهلاً بيك في AI Crypto Trader

اربط حسابك من هنا:
{register_link}

🚀 بعد التسجيل ابعت /start علشان تستقبل الإشارات المجانية.
""")

            except Exception as db_err:
                log(f"❌ /start DB Error: {db_err}")
                send(chat_id, "❌ حصل خطأ أثناء التحقق من حسابك. حاول تاني بعد شوية.")
            finally:
                conn.close()

        # ================= HELP / DEFAULT =================
        else:
            send(chat_id, "👋 ابعت /start علشان تربط حسابك بالموقع.")

    except Exception as e:
        log(f"❌ Telegram Webhook Error: {e}")

    return "ok", 200


# ================= PAYMENT WEBHOOK =================
@app.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    data = request.get_json(silent=True) or {}

    try:
        # 🔐 تحقق من التوقيع
        signature = request.headers.get("x-nowpayments-sig", "").strip()
        ipn_secret = os.environ.get("NOWPAYMENTS_IPN_SECRET", "").strip()

        if not signature or not ipn_secret:
            log("❌ Missing NOWPayments signature or IPN secret")
            return "missing signature", 403

        # IMPORTANT: NOWPayments expects JSON body serialized in a stable way
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
                UPDATE users
                SET is_paid = 1, plan = %s, expiry = %s
                WHERE chat_id = %s
            """, (plan, expiry, chat_id))

            conn.commit()

            c.execute(
                "SELECT chat_id FROM users WHERE chat_id = %s",
                (chat_id,)
            )
            user = c.fetchone()

            conn.close()

            if user and user[0]:
                send(user[0], f"""🔥 تم تفعيل اشتراكك بنجاح!

📦 الباقة: {plan}
⏳ المدة: 30 يوم

🚀 هتوصلك الإشارات تلقائي الآن
""")

            log(f"✅ Payment activated for chat_id={chat_id}, plan={plan}")

    except Exception as e:
        log(f"❌ Webhook Error: {e}")

    return "OK"


# ============== START ==============
if __name__ == "__main__":
    log("🚀 Flask app started")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))