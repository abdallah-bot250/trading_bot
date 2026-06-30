from flask import Blueprint
from urllib.parse import quote_plus, urlparse
from trader_app.extensions import limiter
from trader_app.services.payments import (
    SUCCESS_STATUSES,
    apply_coupon_amount,
    calculate_commission,
    calculate_subscription_expiry,
    coupon_is_active,
    normalize_coupon_code,
    payment_status_bucket,
    validate_nowpayments_signature,
)
from trader_app.services.runtime import *
from trader_app.services.telegram import (
    admin_menu,
    admin_statistics_message,
    broadcast_result_message,
    command_menu,
    linked_message,
    subscription_message,
    user_statistics_message,
    welcome_message,
)

public_bp = Blueprint("public", __name__)
health_bp = Blueprint("health", __name__)
diagnostics_bp = Blueprint("diagnostics", __name__)
auth_bp = Blueprint("auth", __name__)
dashboard_bp = Blueprint("dashboard", __name__)
payments_bp = Blueprint("payments", __name__)
admin_bp = Blueprint("admin", __name__)
telegram_bp = Blueprint("telegram", __name__)

@public_bp.route("/")
def landing():
    return render_template("landing.html")


@public_bp.route("/how-signals-work")
def how_signals_work():
    return render_template("signal_methodology.html")


@public_bp.route("/r/<referral_code>")
@public_bp.route("/ref/<referral_code>")
def referral_landing(referral_code):
    referral_code = str(referral_code or "").strip()
    if referral_code:
        session["ref"] = referral_code
    return render_template(
        "landing.html",
        referral_code=referral_code,
        referral_telegram_link=telegram_deep_referral_link(referral_code) if referral_code else current_bot_link(),
    )


@public_bp.route("/set-language/<lang>")
def set_language(lang):
    lang = (lang or "").strip().lower()
    if lang not in {"en", "ar"}:
        lang = "en"

    session["lang"] = lang
    next_url = request.args.get("next") or request.referrer or url_for("public.landing")
    parsed = urlparse(next_url)
    if parsed.netloc and parsed.netloc != request.host:
        next_url = url_for("public.landing")
    return redirect(next_url)


COMPANY_PAGES = {
    "privacy-policy": {
        "title": "Privacy Policy",
        "eyebrow": "Legal",
        "summary": "How Nexora AI Trader handles account data, Telegram linking, payments, and platform security.",
        "sections": [
            ("Data We Collect", [
                "Account details such as email address, encrypted password, plan, subscription status, and Telegram chat ID when you link the bot.",
                "Trading preferences such as plan, spot/futures settings, signal history counters, and dashboard settings.",
                "Payment metadata such as invoice IDs, payment status, plan, amount, coupon usage, and webhook records. We do not store full card or wallet private keys.",
                "Security logs such as login, admin, password reset, and payment events to protect the platform."
            ]),
            ("How We Use Data", [
                "To create accounts, deliver Telegram signals, manage subscriptions, show dashboards, and support payment history.",
                "To detect abuse, protect admin actions, validate payment webhooks, and improve reliability.",
                "To provide support when a user contacts us about their account, payment, or Telegram connection."
            ]),
            ("Security", [
                "Sensitive exchange API values are encrypted before storage when used by eligible plans.",
                "Sessions use secure settings where production HTTPS is enabled, and admin actions are protected by permission checks.",
                "No system can be guaranteed perfectly secure; users should protect their own email, Telegram, and exchange accounts."
            ]),
            ("Retention", [
                "We keep account and payment records while the account is active or as needed for legal, security, fraud-prevention, and support purposes.",
                "Users can request account support or deletion review through the contact page."
            ])
        ]
    },
    "terms": {
        "title": "Terms of Service",
        "eyebrow": "Agreement",
        "summary": "The rules for using Nexora AI Trader, including subscriptions, signals, bot usage, and account responsibility.",
        "sections": [
            ("Service Scope", [
                "Nexora AI Trader provides crypto market tools, AI-assisted analysis, dashboards, Telegram notifications, and subscription features.",
                "Signals are informational tools and do not guarantee profit, execution, liquidity, or market outcome."
            ]),
            ("User Responsibility", [
                "You are responsible for your account, Telegram access, exchange account, API permissions, position sizing, and risk management.",
                "You must not abuse the service, attempt unauthorized access, scrape private data, resell access without permission, or interfere with the bot."
            ]),
            ("Subscriptions", [
                "Plan access depends on the active subscription status recorded in the platform.",
                "Features may differ between Basic, Pro, and Elite plans as described on the pricing page and dashboard."
            ]),
            ("Availability", [
                "Crypto markets, exchanges, Telegram, hosting providers, and payment networks can experience delays or outages.",
                "We work to keep the service reliable, but uninterrupted availability is not guaranteed."
            ])
        ]
    },
    "refund-policy": {
        "title": "Refund Policy",
        "eyebrow": "Billing",
        "summary": "How refund requests are reviewed for automatic and manual subscriptions.",
        "sections": [
            ("General Policy", [
                "Because the service provides digital access, signals, dashboards, and Telegram delivery immediately after activation, payments are generally final once access is delivered.",
                "Refund requests may be reviewed when there is a duplicate payment, failed activation, wrong plan activation, or a verified technical billing issue."
            ]),
            ("How To Request Review", [
                "Contact support with your account email, payment ID or invoice ID, selected plan, and a clear description of the issue.",
                "Refund review does not guarantee approval. Approved refunds may depend on the payment provider, network fees, and transaction status."
            ]),
            ("Manual Payments", [
                "Manual payment confirmations are reviewed by the admin team. Keep proof of payment until activation is complete.",
                "Incorrect wallet/network payments may be impossible to recover depending on the blockchain transaction."
            ])
        ]
    },
    "risk-disclaimer": {
        "title": "Risk Disclaimer",
        "eyebrow": "Trading Risk",
        "summary": "Crypto trading is risky. Nexora AI Trader is a decision-support tool, not a profit guarantee.",
        "sections": [
            ("Market Risk", [
                "Digital assets are volatile and can move sharply within seconds. You can lose part or all of your capital.",
                "Leverage increases both potential profit and potential loss, including liquidation risk."
            ]),
            ("Signal Risk", [
                "Signals, AI scores, confidence scores, trend detection, and scanner output are informational and may be wrong or delayed.",
                "A good historical result does not guarantee future performance."
            ]),
            ("User Control", [
                "You decide whether to enter, skip, size, close, or adjust any trade.",
                "Never trade money you cannot afford to lose. Use stop-losses, position limits, and responsible risk controls."
            ])
        ]
    },
    "cookie-policy": {
        "title": "Cookie Policy",
        "eyebrow": "Privacy",
        "summary": "How cookies and session storage are used to keep accounts secure and the product usable.",
        "sections": [
            ("Essential Cookies", [
                "We use essential cookies for login sessions, CSRF protection, security checks, and keeping users authenticated.",
                "These cookies are required for dashboard, admin, payment, and account features to work."
            ]),
            ("Preferences", [
                "The platform may use browser storage or cookies to remember interface preferences where needed.",
                "Disabling cookies may prevent login, payments, dashboard actions, and Telegram linking flows from working correctly."
            ]),
            ("Third Parties", [
                "Payment providers, hosting providers, and Telegram may process their own cookies or identifiers when you use their services."
            ])
        ]
    },
    "contact": {
        "title": "Contact",
        "eyebrow": "Support",
        "summary": "Need help with access, Telegram linking, payments, billing, or your dashboard? Start here.",
        "sections": [
            ("Support Channels", [
                "Use the official bot-check page before trusting any Telegram link.",
                "For account support, include your registered email, Telegram username if available, and a short description of the issue.",
                "For payment issues, include invoice ID, payment ID, plan, amount, and payment time."
            ]),
            ("Recommended Details", [
                "Account email, selected plan, screenshots when useful, and the exact step where the issue happened.",
                "Never send your exchange password, private keys, seed phrase, or withdrawal credentials."
            ])
        ],
        "cta": {"label": "Check Official Bot", "href": "/bot-check"}
    },
    "about": {
        "title": "About Nexora AI Trader",
        "eyebrow": "Company",
        "summary": "Nexora AI Trader is built to make crypto signal delivery, AI analysis, and subscription workflows feel clear, premium, and accountable.",
        "sections": [
            ("What We Build", [
                "A crypto intelligence platform with dashboards, Telegram delivery, AI-assisted signal analysis, proof pages, payments, affiliate tracking, and admin controls.",
                "The product focuses on clarity: users should understand the plan, the signal, the risk, and the next action."
            ]),
            ("Product Principles", [
                "No fake certainty: trading risk is always visible.",
                "Operational trust: payment history, bot verification, admin audit logs, and secure account flows matter.",
                "Plan value: Basic, Pro, and Elite should each have real differences and useful features."
            ])
        ]
    },
    "support": {
        "title": "Support Center",
        "eyebrow": "Help",
        "summary": "Fast answers for account access, Telegram linking, subscriptions, payments, and signals.",
        "sections": [
            ("Account Access", [
                "Use password reset if you cannot log in.",
                "Verify your email if the platform requests verification before sensitive actions."
            ]),
            ("Telegram Linking", [
                "Open the official bot from the bot-check page only.",
                "Use the same email you registered with when linking Telegram."
            ]),
            ("Payments", [
                "Automatic payments may need blockchain confirmations before activation.",
                "If a payment is delayed, check invoice history and contact support with the payment ID."
            ]),
            ("Signals", [
                "Signal frequency depends on plan limits, market quality, and your spot/futures preferences.",
                "If both spot and futures are disabled, the system will restore defaults to avoid blocking delivery."
            ])
        ],
        "cta": {"label": "Open Dashboard", "href": "/dashboard"}
    },
    "docs": {
        "title": "Documentation",
        "eyebrow": "Product Docs",
        "summary": "A practical guide to using Nexora AI Trader from registration to Telegram delivery and plan management.",
        "sections": [
            ("Getting Started", [
                "Create an account, log in, open your dashboard, and link Telegram through the official bot.",
                "Choose Basic, Pro, or Elite based on the dashboard and signal features you need."
            ]),
            ("Plans", [
                "Basic includes basic signal access and Telegram delivery.",
                "Pro adds AI analysis, portfolio tracking, email alerts, advanced dashboard, risk analysis, and history.",
                "Elite adds AI chat, whale alerts, private community, early signals, live scanner, VIP dashboard, priority support, and advanced AI."
            ]),
            ("Payments", [
                "Use automatic payment from the dashboard for the fastest flow.",
                "Use manual payment if you need admin confirmation or an alternative route.",
                "Invoice history shows created, paid, pending, and failed payment states."
            ]),
            ("Admin", [
                "Admins can review users, payments, coupons, withdrawals, plan activity, AI performance, and spot/futures statistics.",
                "Admin actions are protected and should be performed only from trusted devices."
            ])
        ]
    },
}


@public_bp.route("/privacy-policy")
@public_bp.route("/privacy")
def privacy_policy():
    return render_template("company_page.html", page=COMPANY_PAGES["privacy-policy"])


@public_bp.route("/terms")
@public_bp.route("/terms-of-service")
def terms_page():
    return render_template("company_page.html", page=COMPANY_PAGES["terms"])


@public_bp.route("/refund-policy")
def refund_policy():
    return render_template("company_page.html", page=COMPANY_PAGES["refund-policy"])


@public_bp.route("/risk-disclaimer")
def risk_disclaimer():
    return render_template("company_page.html", page=COMPANY_PAGES["risk-disclaimer"])


@public_bp.route("/cookie-policy")
def cookie_policy():
    return render_template("company_page.html", page=COMPANY_PAGES["cookie-policy"])


@public_bp.route("/contact")
def contact_page():
    return render_template("company_page.html", page=COMPANY_PAGES["contact"])


@public_bp.route("/about")
def about_page():
    return render_template("company_page.html", page=COMPANY_PAGES["about"])


@public_bp.route("/support")
@public_bp.route("/support-center")
def support_center():
    return render_template("company_page.html", page=COMPANY_PAGES["support"])


@public_bp.route("/docs")
@public_bp.route("/documentation")
def documentation_page():
    return render_template("company_page.html", page=COMPANY_PAGES["docs"])


@public_bp.route("/proof")
def proof():
    proof_items = [
        {
            "image": "/static/proof/proof-1.jpg",
            "title": "صفقة REDUSDT بعائد +14.35%",
            "note": "مثال على صفقة رابحة موثقة من شاشة التداول مع نسبة العائد والربح بالدولار.",
        },
        {
            "image": "/static/proof/proof-2.jpg",
            "title": "عدة صفقات مفتوحة بنتائج خضراء",
            "note": "لقطة تعرض أكثر من صفقة رابحة على أزواج DOGE و SOL و UNI.",
        },
        {
            "image": "/static/proof/proof-3.jpg",
            "title": "نتائج LTC و LINK",
            "note": "لقطة توضح عوائد إيجابية لأكثر من زوج مع بيانات الدخول والخروج.",
        },
        {
            "image": "/static/proof/proof-4.jpg",
            "title": "متابعة صفقات LTC و ETC",
            "note": "لقطة من واجهة تداول تعرض صفقات قيد المتابعة بعوائد إيجابية.",
        },
        {
            "image": "/static/proof/proof-5.jpg",
            "title": "مجموعة صفقات على LINK و ADA و BNB",
            "note": "لقطة تعرض عدة أزواج في نفس الوقت مع نسب عائد مختلفة.",
        },
        {
            "image": "/static/proof/proof-6.jpg",
            "title": "صفقة BTC مغلقة بعائد +38.30%",
            "note": "مثال لصفقة مغلقة على BTCUSDT مع ربح محقق وسعر دخول وإغلاق.",
        },
        {
            "image": "/static/proof/proof-7.jpg",
            "title": "صفقات مغلقة على SOL و ADA",
            "note": "لقطة تعرض صفقات مغلقة ونتائج ربح محققة على أكثر من زوج.",
        },
        {
            "image": "/static/proof/proof-8.jpg",
            "title": "تأكيد إضافي لصفقة BTC",
            "note": "لقطة ثانية لنفس نتيجة BTC لإظهار تفاصيل الصفقة المغلقة بوضوح.",
        },
        {
            "image": "/static/proof/proof-9.jpg",
            "title": "صفقة BTC بعائد كبير",
            "note": "لقطة تعرض صفقة BTCUSDT بعائد مرتفع وربح محقق داخل منصة التداول.",
        },
    ]
    return render_template("proof.html", proof_items=proof_items)


@public_bp.route("/bot-check")
def bot_check():
    telegram_connect_link = current_bot_link()
    is_linked = False

    if session.get("user"):
        conn = None
        try:
            conn = db()
            c = conn.cursor()
            c.execute("""
                SELECT id, email, chat_id
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
            """, (session["user"].lower(),))
            user_row = c.fetchone()
            if user_row:
                is_linked = bool(str(user_row[2] or "").strip())
                if not is_linked:
                    token = create_telegram_link_token(c, user_row[1])
                    telegram_connect_link = f"{current_bot_link()}?start=link_{token}"
                    conn.commit()
                    log(f"TELEGRAM_LINK_CODE_GENERATED user_id={user_row[0]}")
                else:
                    telegram_connect_link = current_bot_link()
            if conn:
                conn.close()
        except Exception as e:
            try:
                if conn:
                    conn.rollback()
                    conn.close()
            except Exception:
                pass
            log(f"TELEGRAM_LINK_FAILED reason=bot_check_token_error error={e}")

    return render_template(
        "bot_check.html",
        bot_link=current_bot_link(),
        telegram_connect_link=telegram_connect_link,
        is_linked=is_linked,
        base_url=current_base_url(),
    )


@health_bp.route("/health")
def health():
    return {
        "status": "ok",
        "service": "web",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@public_bp.route("/success")
def success():
    return "✅ تم إنشاء الدفع بنجاح، انتظر تأكيد الشبكة"


@public_bp.route("/cancel")
def cancel():
    return "❌ تم إلغاء الدفع"


@diagnostics_bp.route("/debug-users")
def debug_users():
    if not admin_required():
        return "Forbidden", 403

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


@diagnostics_bp.route("/test-db")
def test_db():
    if not admin_required():
        return "Forbidden", 403

    try:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT NOW()")
        now = c.fetchone()
        conn.close()
        return f"✅ DB OK: {now}"
    except Exception as e:
        return f"❌ DB ERROR: {str(e)}"


@diagnostics_bp.route("/test-telegram")
def test_telegram():
    if not admin_required():
        return "Forbidden", 403

    try:
        chat_id = request.args.get("chat_id", "").strip()

        if not chat_id:
            return "❌ لازم تحط chat_id في الرابط"

        ok = send(chat_id, f"✅ TEST FROM WEB APP\n🕒 {datetime.now()}")

        return "✅ تم الإرسال" if ok else "❌ فشل الإرسال"

    except Exception as e:
        return f"ERROR: {str(e)}"


@diagnostics_bp.route("/telegram-status")
def telegram_status():
    if not admin_required():
        return "Forbidden", 403

    expected_webhook = f"{current_base_url()}/webhook"
    status = {
        "token_configured": bool(TOKEN),
        "base_url": current_base_url(),
        "bot_link": current_bot_link(),
        "expected_webhook": expected_webhook,
        "webhook_matches_expected": None,
        "telegram_ok": False,
        "telegram_webhook_url": None,
        "telegram_last_error": None,
    }

    if not TOKEN:
        status["telegram_last_error"] = "TELEGRAM_TOKEN is missing"
        return jsonify(status), 500

    try:
        r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo", timeout=10)
        payload = r.json()
        result = payload.get("result") or {}
        webhook_url = result.get("url") or ""
        status.update({
            "telegram_ok": bool(payload.get("ok")),
            "telegram_webhook_url": webhook_url,
            "telegram_last_error": result.get("last_error_message"),
            "pending_update_count": result.get("pending_update_count", 0),
            "webhook_matches_expected": webhook_url.rstrip("/") == expected_webhook.rstrip("/"),
        })
        return jsonify(status), 200 if status["telegram_ok"] else 502
    except Exception as e:
        status["telegram_last_error"] = str(e)
        return jsonify(status), 502



def reassign_telegram_chat(c, current_user_id, chat_id, email=None):
    chat_id = str(chat_id or "").strip()
    if not chat_id:
        return False

    c.execute("""
        SELECT id
        FROM users
        WHERE chat_id = %s
        LIMIT 1
    """, (chat_id,))
    owner = c.fetchone()
    old_user_id = owner[0] if owner else None

    if old_user_id and int(old_user_id) != int(current_user_id):
        c.execute("""
            UPDATE users
            SET chat_id = NULL,
                bot_active = 0
            WHERE id = %s
        """, (old_user_id,))
        log(f"TELEGRAM_CHAT_REASSIGNED old_user_id={old_user_id} new_user_id={current_user_id} chat_id={chat_id}")

    c.execute("""
        UPDATE users
        SET chat_id = %s,
            bot_active = 1
        WHERE id = %s
    """, (chat_id, current_user_id))
    if email:
        log(f"LOGIN_LINKED_TELEGRAM email={email} chat_id={chat_id}")
    return bool(old_user_id and int(old_user_id) != int(current_user_id))


# ================= REGISTER =================
@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("8 per minute", methods=["POST"])
def register():
    chat_id = (request.form.get("chat_id") or request.args.get("chat_id") or session.get("chat_id") or "").strip()
    ref = (request.form.get("ref") or request.args.get("ref") or session.get("ref") or "").strip()

    if chat_id:
        session["chat_id"] = chat_id

    if ref:
        session["ref"] = ref

    if request.method == "POST":
        conn = None
        try:
            email = (request.form.get("email") or "").strip().lower()
            password_raw = (request.form.get("password") or "").strip()

            if not email or not password_raw:
                flash("❌ لازم تكتب الإيميل والباسورد", "error")
                return redirect(url_for("auth.register", chat_id=chat_id, ref=ref))

            email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
            if not re.match(email_pattern, email):
                flash("❌ لازم تدخل إيميل صحيح", "error")
                return redirect(url_for("auth.register", chat_id=chat_id, ref=ref))

            if len(password_raw) < 6:
                flash("❌ الباسورد لازم يكون 6 أحرف أو أكثر", "error")
                return redirect(url_for("auth.register", chat_id=chat_id, ref=ref))

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
                        log(f"Telegram referral loaded in register: {chat_id} -> {telegram_ref}")
                except Exception as tg_err:
                    conn.rollback()
                    log(f"Telegram referral fetch error in register: {tg_err}")

            final_ref = ref or telegram_ref

            c.execute("""
                SELECT id
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
            """, (email,))
            existing = c.fetchone()

            if existing:
                conn.close()
                flash("Email already registered. Please login.", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            if chat_id:
                c.execute("""
                    SELECT id
                    FROM users
                    WHERE chat_id = %s
                    LIMIT 1
                """, (chat_id,))
                existing_chat_user = c.fetchone()
                if existing_chat_user:
                    conn.close()
                    log(f"REGISTER_CHAT_ID_EXISTS user_id={existing_chat_user[0]} chat_id={chat_id}")
                    flash("Telegram account already linked. Please login.", "error")
                    return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            referred_by = None
            if final_ref:
                c.execute("SELECT chat_id FROM users WHERE referral_code = %s LIMIT 1", (final_ref,))
                ref_user = c.fetchone()
                if ref_user and str(ref_user[0] or "").strip() != str(chat_id).strip():
                    referred_by = final_ref

            password = generate_password_hash(password_raw)
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
                chat_id or None,
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
                1 if chat_id else 0,
                referred_by,
                1 if is_admin_email(email) else 0,
                0
            ))

            new_user = c.fetchone()

            if chat_id:
                log(f"LOGIN_LINKED_TELEGRAM email={email} chat_id={chat_id}")
                flash("Telegram account linked successfully.", "success")

            verification_token = create_email_verification_token(email, conn)
            conn.commit()

            if chat_id:
                ensure_user_has_referral_code(chat_id, conn)

            conn.close()

            session["user"] = email
            session["is_admin"] = True if is_admin_email(email) else False
            sent, verification_link = send_verification_email(email, verification_token)
            audit_log("register_success", email, f"chat_id_linked={bool(chat_id)} verification_email_sent={sent}")
            if not sent:
                flash(f"Verification link: {verification_link}", "success")

            log(f"New user registered: {email} | chat_id={chat_id} | ref={final_ref}")

            flash("✅ تم إنشاء الحساب بنجاح", "success")
            return redirect("/dashboard")

        except Exception as e:
            try:
                if conn:
                    conn.rollback()
                    conn.close()
            except Exception:
                pass
            error_text = str(e)
            log(f"Register error: {e}")
            if chat_id and ("users_chat_id_unique" in error_text or "duplicate key" in error_text):
                flash("Telegram account already linked. Please login.", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))
            flash("❌ حصل خطأ أثناء التسجيل", "error")
            return redirect(url_for("auth.register", chat_id=chat_id, ref=ref))

    return render_template("register.html", chat_id=chat_id, ref=ref)


# ================= LOGIN =================
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    chat_id = (request.form.get("chat_id") or request.args.get("chat_id") or session.get("chat_id") or "").strip()
    ref = (request.form.get("ref") or request.args.get("ref") or session.get("ref") or "").strip()

    if chat_id:
        session["chat_id"] = chat_id

    if ref:
        session["ref"] = ref

    if request.method == "POST":
        conn = None
        try:
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()

            if not email or not password:
                log(f"LOGIN_FAILED email={email} reason=missing_credentials")
                flash("❌ لازم تكتب الإيميل والباسورد", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
            if not re.match(email_pattern, email):
                log(f"LOGIN_FAILED email={email} reason=invalid_email")
                flash("❌ لازم تدخل إيميل صحيح", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            conn = db()
            c = conn.cursor()

            c.execute("""
                SELECT id, email, password
                FROM users
                WHERE LOWER(email) = %s
                LIMIT 1
            """, (email,))
            user = c.fetchone()

            if not user:
                conn.close()
                log(f"LOGIN_FAILED email={email} reason=unknown_email")
                audit_log("login_unknown_email", email)
                flash("❌ الإيميل غير موجود", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            user_id = user[0]
            stored_password = str(user[2] or "").strip()

            if not check_password_hash(stored_password, password):
                conn.close()
                log(f"LOGIN_FAILED email={email} reason=bad_password")
                audit_log("login_bad_password", email)
                flash("❌ الباسورد غير صحيح", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            moved_chat = False
            if chat_id:
                moved_chat = reassign_telegram_chat(c, user_id, chat_id, email)
                if moved_chat:
                    flash("Telegram account linked successfully.", "success")

            conn.commit()

            if chat_id:
                ensure_user_has_referral_code(chat_id, conn)

            conn.close()

            session["user"] = email
            session["is_admin"] = True if is_admin_email(email) else False
            audit_log("login_success", email, f"chat_id_linked={bool(chat_id)}")
            log(f"LOGIN_SUCCESS email={email} chat_id={chat_id}")
            return redirect("/dashboard")

        except Exception as e:
            try:
                if conn:
                    conn.rollback()
                    conn.close()
            except Exception:
                pass
            log(f"LOGIN_FAILED email={(request.form.get('email') or '').strip().lower()} reason=exception error={e}")
            flash("❌ حصل خطأ أثناء تسجيل الدخول", "error")
            return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

    return render_template("login.html", chat_id=chat_id, ref=ref)


@auth_bp.route("/logout")
def logout():
    audit_log("logout", session.get("user"))
    session.clear()
    return redirect("/login")


@auth_bp.route("/verify-email/<token>")
@limiter.limit("20 per hour")
def verify_email(token):
    token = (token or "").strip()
    if not token:
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
            UPDATE users
            SET email_verified = 1,
                email_verification_token = NULL
            WHERE email_verification_token = %s
            RETURNING email
        """, (token,))
        row = c.fetchone()
        conn.commit()
        conn.close()

        if row:
            audit_log("email_verified", row[0])
            flash("Email verified successfully.", "success")
        else:
            audit_log("email_verify_invalid_token")
            flash("Invalid or expired verification link.", "error")
        return redirect("/login")
    except Exception as e:
        log(f"verify_email error: {e}")
        return redirect("/login")


@auth_bp.route("/resend-verification", methods=["POST"])
@limiter.limit("3 per hour")
def resend_verification():
    if not session.get("user"):
        return redirect("/login")

    try:
        email = session["user"].lower()
        token = create_email_verification_token(email)
        sent, link = send_verification_email(email, token)
        flash("Verification email sent." if sent else f"Verification link: {link}", "success")
        return redirect("/dashboard")
    except Exception as e:
        log(f"resend_verification error: {e}")
        flash("Could not send verification email.", "error")
        return redirect("/dashboard")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        reset_sent = False
        reset_link = None
        if email:
            try:
                token = create_password_reset_token(email)
                if token:
                    reset_sent, reset_link = send_password_reset_email(email, token)
                    if not reset_sent:
                        log(f"PASSWORD_RESET_EMAIL_FAILED email={email}")
                audit_log("password_reset_requested", email, f"sent={reset_sent}")
            except Exception as e:
                log(f"forgot_password error: {e}")

        if reset_sent:
            flash("Password reset email sent. Please check your inbox and spam folder.", "success")
        else:
            show_local_link = os.environ.get("SHOW_SECURITY_EMAIL_LINKS", "").strip().lower() in {"1", "true", "yes"}
            if reset_link and show_local_link:
                flash(f"Email delivery is not configured. Temporary reset link: {reset_link}", "success")
            else:
                flash("If this email exists, reset instructions were created. If you do not receive the email, contact support or check SMTP settings.", "success")
        return render_template("forgot_password.html", submitted=True)

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def reset_password(token):
    token = (token or "").strip()

    if request.method == "POST":
        password = (request.form.get("password") or "").strip()
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("reset_password.html", token=token)

        try:
            conn = db()
            c = conn.cursor()
            c.execute("""
                SELECT email, password_reset_expires_at
                FROM users
                WHERE password_reset_token = %s
                LIMIT 1
            """, (token,))
            row = c.fetchone()

            if not row:
                conn.close()
                audit_log("password_reset_invalid_token")
                flash("Invalid or expired reset link.", "error")
                return redirect("/login")

            expires_at = datetime.fromisoformat(str(row[1]))
            if datetime.utcnow() > expires_at:
                conn.close()
                audit_log("password_reset_expired", row[0])
                flash("Invalid or expired reset link.", "error")
                return redirect("/login")

            c.execute("""
                UPDATE users
                SET password = %s,
                    password_reset_token = NULL,
                    password_reset_expires_at = NULL
                WHERE password_reset_token = %s
            """, (generate_password_hash(password), token))
            conn.commit()
            conn.close()
            audit_log("password_reset_success", row[0])
            flash("Password updated. Please login.", "success")
            return redirect("/login")
        except Exception as e:
            log(f"reset_password error: {e}")
            flash("Could not reset password.", "error")

    return render_template("reset_password.html", token=token)


# ================= SAVE API =================
@dashboard_bp.route("/save-api", methods=["POST"])
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

        if not user or user[0] not in AUTO_TRADE_PLANS:
            conn.close()
            return "❌ API متاح فقط لخطط Elite / Pro 2 Years"

        api_key = request.form.get("api_key", "").strip()
        api_secret = request.form.get("api_secret", "").strip()

        if not api_key or not api_secret:
            conn.close()
            return "❌ لازم تدخل API Key و Secret"
        
        encrypted_api_key = encrypt_text(api_key)
        encrypted_api_secret = encrypt_text(api_secret)

        if not encrypted_api_key or not encrypted_api_secret:
            conn.close()
            return "❌ حصل خطأ أثناء تشفير بيانات API"

        c.execute("""
            UPDATE users
            SET api_key = %s, api_secret = %s
            WHERE email = %s
        """, (encrypted_api_key, encrypted_api_secret, session["user"]))

        conn.commit()
        conn.close()

        return "✅ تم ربط الحساب بنجاح"

    except Exception as e:
        log(f"❌ save_api error: {e}")
        return f"❌ حصل خطأ أثناء حفظ API: {str(e)}"


# ================= SAVE SETTINGS =================
@dashboard_bp.route("/save-settings", methods=["POST"])
def save_settings():
    if not session.get("user"):
        return redirect("/login")

    try:
        trade_amount = request.form.get("trade_amount", "10").strip()
        trade_type = request.form.get("trade_type", "futures").strip().lower()
        spot_enabled = 1 if request.form.get("spot_enabled") == "1" else 0
        futures_enabled = 1 if request.form.get("futures_enabled") == "1" else 0
        spot_auto_trade_enabled = 1 if request.form.get("spot_auto_trade_enabled") == "1" else 0
        futures_auto_trade_enabled = 1 if request.form.get("futures_auto_trade_enabled") == "1" else 0
        stop_loss_required = 1 if request.form.get("stop_loss_required", "1") == "1" else 0
        max_trade_size = request.form.get("max_trade_size", trade_amount)

        try:
            trade_amount = float(trade_amount)
        except:
            trade_amount = 10

        if trade_amount <= 0:
            trade_amount = 10

        if trade_type not in ["spot", "futures"]:
            trade_type = "futures"

        try:
            max_trade_size = float(max_trade_size)
        except Exception:
            max_trade_size = trade_amount
        if max_trade_size <= 0:
            max_trade_size = trade_amount

        if spot_enabled == 0 and futures_enabled == 0:
            spot_enabled = 1
            futures_enabled = 1

        conn = db()
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE users
                SET trade_amount = %s,
                    trade_type = %s,
                    spot_enabled = %s,
                    futures_enabled = %s,
                    spot_auto_trade_enabled = %s,
                    futures_auto_trade_enabled = %s,
                    max_trade_size = %s,
                    stop_loss_required = %s
                WHERE email = %s
            """, (trade_amount, trade_type, spot_enabled, futures_enabled, spot_auto_trade_enabled, futures_auto_trade_enabled, max_trade_size, stop_loss_required, session["user"]))
        except Exception:
            conn.rollback()
            c.execute("""
                UPDATE users
                SET trade_amount = %s,
                    trade_type = %s,
                    spot_enabled = %s,
                    futures_enabled = %s
                WHERE email = %s
            """, (trade_amount, trade_type, spot_enabled, futures_enabled, session["user"]))
        conn.commit()
        conn.close()

        return "✅ تم حفظ إعدادات التداول"

    except Exception as e:
        log(f"❌ save_settings error: {e}")
        return f"❌ حصل خطأ أثناء حفظ الإعدادات: {str(e)}"


def _safe_date(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _subscription_snapshot(user):
    plan = str(user.get("plan") or "trial").strip().lower()
    is_paid = int(user.get("is_paid") or 0)
    expiry_raw = user.get("expiry")
    expiry_date = _safe_date(expiry_raw)
    today = datetime.now().date()
    remaining_days = None
    if expiry_date:
        remaining_days = max((expiry_date - today).days, 0)

    start_raw = user.get("trial_start") or user.get("created_at")
    start_date = _safe_date(start_raw)
    started_days_ago = max((today - start_date).days, 0) if start_date else None

    if is_paid != 1 or plan == "trial":
        status = "free"
    elif expiry_date and expiry_date < today:
        status = "expired"
    elif expiry_date and (expiry_date - today).days <= 7:
        status = "expiring"
    else:
        status = "active"

    subscription_expired = status == "expired"
    subscription_active = is_paid == 1 and not subscription_expired

    return {
        "status": status,
        "plan": plan,
        "start_date": start_raw,
        "end_date": expiry_raw,
        "remaining_days": remaining_days,
        "started_days_ago": started_days_ago,
        "subscription_active": subscription_active,
        "subscription_expired": subscription_expired,
        "is_premium": subscription_active,
    }


def _subscription_admin_summary(rows):
    summary = {
        "active_users": 0,
        "free_users": 0,
        "premium_users": 0,
        "expired_subscriptions": 0,
        "expiring_subscriptions": 0,
    }
    today = datetime.now().date()
    for row in rows or []:
        is_paid = int(row[0] or 0)
        plan = str(row[1] or "trial").strip().lower()
        expiry_date = _safe_date(row[2])
        bot_active = int(row[3] or 0)
        if bot_active == 1:
            summary["active_users"] += 1
        if is_paid != 1 or plan == "trial":
            summary["free_users"] += 1
            continue
        summary["premium_users"] += 1
        if expiry_date and expiry_date < today:
            summary["expired_subscriptions"] += 1
        elif expiry_date and 0 <= (expiry_date - today).days <= 7:
            summary["expiring_subscriptions"] += 1
    return summary


def ensure_telegram_link_token_table(c):
    c.execute("""
        CREATE TABLE IF NOT EXISTS telegram_link_tokens (
            token TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP NULL
        )
    """)


def create_telegram_link_token(c, user_email):
    ensure_telegram_link_token_table(c)
    token = secrets.token_urlsafe(32)
    safe_email = str(user_email or "").strip().lower()
    c.execute("""
        INSERT INTO telegram_link_tokens (token, user_email)
        VALUES (%s, %s)
    """, (token, safe_email))
    return token


def telegram_link_is_expired(created_at, minutes=30):
    try:
        if not created_at:
            return True
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00")).replace(tzinfo=None)
        return datetime.now() - created_at > timedelta(minutes=minutes)
    except Exception:
        return True


def handle_telegram_link_token(c, conn, chat_id, token):
    ensure_telegram_link_token_table(c)
    token = str(token or "").strip()
    if not token:
        log("TELEGRAM_LINK_FAILED reason=missing_token chat_id_present=True")
        send(chat_id, "Telegram link expired. Open your Nexora dashboard and tap Connect Telegram Bot again.")
        return True

    c.execute("""
        SELECT token, user_email, created_at, used_at
        FROM telegram_link_tokens
        WHERE token = %s
        LIMIT 1
    """, (token,))
    link_row = c.fetchone()
    if not link_row:
        log("TELEGRAM_LINK_FAILED reason=token_not_found chat_id_present=True")
        send(chat_id, "Telegram link expired. Open your Nexora dashboard and tap Connect Telegram Bot again.")
        return True

    user_email = str(link_row[1] or "").strip().lower()
    created_at = link_row[2]
    used_at = link_row[3]
    if used_at or telegram_link_is_expired(created_at):
        log(f"TELEGRAM_LINK_FAILED reason=token_used_or_expired user_email={user_email} chat_id_present=True")
        send(chat_id, "Telegram link expired. Open your Nexora dashboard and tap Connect Telegram Bot again.")
        return True

    c.execute("""
        SELECT id, email, chat_id
        FROM users
        WHERE LOWER(email) = %s
        LIMIT 1
    """, (user_email,))
    target_user = c.fetchone()
    if not target_user:
        log(f"TELEGRAM_LINK_FAILED reason=user_not_found user_email={user_email} chat_id_present=True")
        send(chat_id, "Nexora account not found. Please register on the website first.")
        return True

    target_user_id = target_user[0]
    target_email = target_user[1]
    current_chat_id = str(target_user[2] or "").strip()

    if current_chat_id and current_chat_id != str(chat_id):
        log(f"TELEGRAM_LINK_FAILED reason=user_already_linked user_id={target_user_id} chat_id_present=True")
        send(chat_id, "This Nexora account is already linked to another Telegram. Login on the website to manage linking safely.")
        return True

    c.execute("""
        SELECT id, email
        FROM users
        WHERE chat_id = %s AND id <> %s
        LIMIT 1
    """, (str(chat_id), target_user_id))
    existing_chat_owner = c.fetchone()
    if existing_chat_owner:
        log(f"TELEGRAM_LINK_FAILED reason=chat_id_owned_by_other_user user_id={target_user_id} chat_id_present=True")
        login_link = f"{current_base_url()}/login?chat_id={chat_id}"
        send(chat_id, "This Telegram is already linked to another Nexora account. Login with your password to move the Telegram link safely:\n" + login_link)
        return True

    c.execute("""
        UPDATE users
        SET chat_id = %s,
            bot_active = 1
        WHERE id = %s
    """, (str(chat_id), target_user_id))
    c.execute("""
        UPDATE telegram_link_tokens
        SET used_at = CURRENT_TIMESTAMP
        WHERE token = %s
    """, (token,))
    conn.commit()
    log(f"TELEGRAM_LINK_SUCCESS user_id={target_user_id} chat_id_present=True")
    audit_log("telegram_link_success", target_email, "chat_id_present=True")
    send(chat_id, "Telegram linked successfully to your Nexora account.")
    return True


# ================= DASHBOARD =================
@dashboard_bp.route("/dashboard")
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

            referral_link = telegram_referral_link(user["referral_code"])

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

        active_referrals = 0
        paid_referrals = 0
        if chat_id:
            try:
                c.execute("""
                    SELECT COUNT(DISTINCT ar.referred_chat_id)
                    FROM affiliate_referrals ar
                    JOIN users u ON u.chat_id = ar.referred_chat_id
                    WHERE ar.referrer_chat_id = %s
                      AND COALESCE(u.bot_active, 0) = 1
                """, (chat_id,))
                active_row = c.fetchone() or {}
                active_referrals = int((active_row.get("count") if hasattr(active_row, "get") else active_row[0]) or 0)
            except Exception as referral_error:
                conn.rollback()
                log(f"active referral metric unavailable: {referral_error}")
            try:
                c.execute("""
                    SELECT COUNT(DISTINCT referred_chat_id)
                    FROM affiliate_commissions
                    WHERE referrer_chat_id = %s
                      AND status = 'approved'
                """, (chat_id,))
                paid_row = c.fetchone() or {}
                paid_referrals = int((paid_row.get("count") if hasattr(paid_row, "get") else paid_row[0]) or 0)
            except Exception as referral_error:
                conn.rollback()
                log(f"paid referral metric unavailable: {referral_error}")

        referral_qr_url = ""
        if referral_link:
            referral_qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=" + quote_plus(referral_link)

        type_stats = {
            "spot_today": 0,
            "futures_today": 0,
            "spot_win_rate": 0,
            "futures_win_rate": 0,
            "spot_profit": 0,
            "futures_profit": 0,
        }
        signal_performance = {
            "total_signals": 0,
            "active_signals": 0,
            "closed_signals": 0,
            "wins": 0,
            "win_rate": 0,
            "today_outcome": 0,
            "avg_rr": None,
            "best_strategy": "Not enough data yet",
            "best_timeframe": "Not enough data yet",
            "best_pair": "Not enough data yet",
            "last_scan": "No scans yet",
            "market_status": "Waiting for qualified setup",
            "last_learning_update": "Not enough data yet",
            "latest_reason": "Not enough data yet",
            "latest_regime": "Not enough data yet",
            "latest_strategy": "Not enough data yet",
        }
        recent_signals = []
        performance_chart = {"labels": [], "values": []}
        if chat_id:
            try:
                c.execute("""
                    SELECT
                        LOWER(COALESCE(trade_type, 'futures')) AS trade_type,
                        COUNT(*) FILTER (
                            WHERE created_at >= date_trunc('day', NOW())
                        ) AS signals_today,
                        COUNT(*) FILTER (
                            WHERE status = 'CLOSED'
                        ) AS closed_count,
                        COUNT(*) FILTER (
                            WHERE status = 'CLOSED' AND COALESCE(pnl, 0) > 0
                        ) AS wins,
                        COALESCE(SUM(COALESCE(pnl, 0)), 0) AS profit
                    FROM trades_log
                    WHERE chat_id = %s
                    GROUP BY LOWER(COALESCE(trade_type, 'futures'))
                """, (chat_id,))
                for row in c.fetchall():
                    type_name = str(row["trade_type"] or "futures").lower()
                    closed_count = int(row["closed_count"] or 0)
                    wins = int(row["wins"] or 0)
                    win_rate_value = round((wins / closed_count) * 100, 2) if closed_count else 0
                    if type_name == "spot":
                        type_stats["spot_today"] = int(row["signals_today"] or 0)
                        type_stats["spot_win_rate"] = win_rate_value
                        type_stats["spot_profit"] = round(float(row["profit"] or 0), 2)
                    elif type_name == "futures":
                        type_stats["futures_today"] = int(row["signals_today"] or 0)
                        type_stats["futures_win_rate"] = win_rate_value
                        type_stats["futures_profit"] = round(float(row["profit"] or 0), 2)
            except Exception as stats_error:
                conn.rollback()
                log(f"spot_futures stats unavailable: {stats_error}")

            try:
                c.execute("""
                    SELECT
                        COUNT(*) AS total_signals,
                        COUNT(*) FILTER (WHERE status = 'OPEN') AS active_signals,
                        COUNT(*) FILTER (WHERE status = 'CLOSED') AS closed_signals,
                        COUNT(*) FILTER (WHERE status = 'CLOSED' AND COALESCE(pnl, 0) > 0) AS wins,
                        COALESCE(SUM(CASE WHEN created_at >= date_trunc('day', NOW()) THEN COALESCE(pnl, 0) ELSE 0 END), 0) AS today_outcome,
                        MAX(created_at) AS last_scan
                    FROM trades_log
                    WHERE chat_id = %s
                """, (chat_id,))
                perf = c.fetchone() or {}
                signal_performance["total_signals"] = int(perf.get("total_signals") or 0)
                signal_performance["active_signals"] = int(perf.get("active_signals") or 0)
                signal_performance["closed_signals"] = int(perf.get("closed_signals") or 0)
                signal_performance["wins"] = int(perf.get("wins") or 0)
                signal_performance["win_rate"] = round((signal_performance["wins"] / signal_performance["closed_signals"]) * 100, 2) if signal_performance["closed_signals"] else 0
                signal_performance["today_outcome"] = round(float(perf.get("today_outcome") or 0), 2)
                signal_performance["last_scan"] = perf.get("last_scan") or "No scans yet"
                signal_performance["market_status"] = "Live monitoring" if signal_performance["total_signals"] else "Waiting for qualified setup"
            except Exception as perf_error:
                conn.rollback()
                log(f"dashboard performance metrics unavailable: {perf_error}")

            try:
                c.execute("""
                    SELECT pair, direction, entry, tp, sl, confidence, status, created_at, trade_type, pnl
                    FROM trades_log
                    WHERE chat_id = %s
                    ORDER BY created_at DESC
                    LIMIT 8
                """, (chat_id,))
                recent_signals = c.fetchall()
                if recent_signals:
                    latest = recent_signals[0]
                    signal_performance["best_pair"] = latest.get("pair") or "Not enough data yet"
                    signal_performance["latest_reason"] = f"{latest.get('direction') or 'Signal'} setup with tracked confidence {latest.get('confidence') or 'N/A'}%."
            except Exception as recent_error:
                conn.rollback()
                log(f"dashboard recent signals unavailable: {recent_error}")

            try:
                c.execute("""
                    SELECT COALESCE(pair, 'Unknown') AS pair,
                           COUNT(*) AS closed_count,
                           COUNT(*) FILTER (WHERE COALESCE(pnl, 0) > 0) AS wins
                    FROM trades_log
                    WHERE chat_id = %s AND status = 'CLOSED'
                    GROUP BY COALESCE(pair, 'Unknown')
                    HAVING COUNT(*) > 0
                    ORDER BY (COUNT(*) FILTER (WHERE COALESCE(pnl, 0) > 0))::float / COUNT(*) DESC, COUNT(*) DESC
                    LIMIT 1
                """, (chat_id,))
                best_pair_row = c.fetchone()
                if best_pair_row:
                    signal_performance["best_pair"] = best_pair_row.get("pair") or signal_performance["best_pair"]
            except Exception as best_pair_error:
                conn.rollback()
                log(f"dashboard best pair unavailable: {best_pair_error}")

            try:
                c.execute("""
                    SELECT to_char(created_at::date, 'MM-DD') AS label,
                           COALESCE(SUM(COALESCE(pnl, 0)), 0) AS pnl
                    FROM trades_log
                    WHERE chat_id = %s
                    GROUP BY created_at::date
                    ORDER BY created_at::date DESC
                    LIMIT 7
                """, (chat_id,))
                chart_rows = list(reversed(c.fetchall()))
                performance_chart = {
                    "labels": [row.get("label") for row in chart_rows],
                    "values": [round(float(row.get("pnl") or 0), 2) for row in chart_rows],
                }
            except Exception as chart_error:
                conn.rollback()
                log(f"dashboard chart unavailable: {chart_error}")

        log("DASHBOARD_METRICS_LOADED ok=True")
        is_linked = True if user.get("chat_id") else False
        telegram_link_token = create_telegram_link_token(c, user.get("email"))
        telegram_connect_link = f"{current_bot_link()}?start=link_{telegram_link_token}"
        if not is_linked:
            log(f"TELEGRAM_USER_NOT_LINKED email={user.get('email')}")
        conn.commit()
        conn.close()

        plan = str(user.get("plan") or "trial").strip().lower()
        profit = float(user.get("profit", 0) or 0)
        trades = int(user.get("trades", 0) or 0)
        trade_amount = float(user.get("trade_amount", 10) or 10)
        affiliate_balance = float(user.get("affiliate_balance", 0) or 0)
        portfolio_value = round(max(0, (trade_amount * max(trades, 1)) + profit + affiliate_balance), 2)
        roi = round((profit / max(trade_amount * max(trades, 1), 1)) * 100, 2)
        win_rate = min(96, max(48, 58 + (trades * 3) + (8 if profit > 0 else 0) + (6 if plan == "vip" else 0)))
        ai_score = min(99, max(54, 62 + (trades * 4) + (10 if is_linked else 0) + (8 if user.get("bot_active", 0) == 1 else 0) + (8 if plan == "vip" else 0)))
        open_trades = 1 if user.get("bot_active", 0) == 1 and plan in ("pro", "vip", "pro_2y") else 0
        closed_trades = max(0, trades)
        balance = round(portfolio_value + float(total_comm or 0) - float(total_withdrawn or 0), 2)
        subscription = _subscription_snapshot(user)

        if plan in AUTO_TRADE_PLANS or user.get("is_admin", 0) == 1:
            dashboard_tier = "elite"
            dashboard_title = "Elite Dashboard"
            dashboard_subtitle = "Full command center for Elite automation, AI scoring, portfolio tracking, and execution controls."
        elif plan == "pro":
            dashboard_tier = "pro"
            dashboard_title = "Pro Dashboard"
            dashboard_subtitle = "Advanced signal workspace with performance, risk, and referral intelligence."
        else:
            dashboard_tier = "starter"
            dashboard_title = "Free Trial Dashboard"
            dashboard_subtitle = "Clean free-trial workspace with 2 free signals, Telegram delivery, basic analysis, and essential tracking."

        plan_label = PLAN_LABELS.get(plan, plan.title())
        free_signal_limit = 2
        free_signal_usage = min(trades, free_signal_limit) if plan == "trial" else None

        dashboard_widgets = {
            "portfolio": portfolio_value,
            "roi": roi,
            "win_rate": win_rate,
            "ai_score": ai_score,
            "balance": balance,
            "open_trades": open_trades,
            "closed_trades": closed_trades,
            "spot_today": type_stats["spot_today"],
            "futures_today": type_stats["futures_today"],
            "spot_win_rate": type_stats["spot_win_rate"],
            "futures_win_rate": type_stats["futures_win_rate"],
            "spot_profit": type_stats["spot_profit"],
            "futures_profit": type_stats["futures_profit"],
            "subscription_status": subscription["status"],
            "remaining_days": subscription["remaining_days"],
            "started_days_ago": subscription["started_days_ago"],
            "premium_enabled": subscription["is_premium"],
            "bot_connected": is_linked,
            "free_signal_usage": free_signal_usage,
            "free_signal_limit": free_signal_limit,
            "active_signals": signal_performance["active_signals"],
            "total_signals": signal_performance["total_signals"],
            "today_outcome": signal_performance["today_outcome"],
            "real_win_rate": signal_performance["win_rate"],
        }
        notifications = []
        if not is_linked:
            notifications.append("Link Telegram to receive signals and activate the full experience.")
        if subscription["status"] == "expired":
            notifications.append("Subscription expired. Premium access is paused until renewal, while the account stays safe.")
        elif subscription["status"] == "expiring" and subscription["remaining_days"] is not None:
            notifications.append(f"Subscription expires in {subscription['remaining_days']} day(s). Renew before expiry to keep premium signals active.")
        if plan in ("trial", "basic") and user.get("is_paid", 0) != 1:
            notifications.append("Free Trial includes 2 free signals. Basic and paid plans unlock higher access.")
        if plan in AUTO_TRADE_PLANS and not user.get("api_key"):
            notifications.append("Elite automation needs API keys before auto trading can run.")
        if user.get("bot_active", 0) == 1:
            notifications.append("Bot is running and ready to send signals when market quality is high.")
        if not notifications:
            notifications.append("Workspace is healthy. Watch AI Score and recent activity for updates.")

        recent_activity = [
            {"label": "Dashboard loaded", "value": dashboard_title},
            {"label": "Current plan", "value": plan_label},
            {"label": "Telegram link", "value": "Connected" if is_linked else "Pending"},
            {"label": "Bot status", "value": "Running" if user.get("bot_active", 0) == 1 else "Stopped"},
            {"label": "Subscription", "value": subscription["status"].title()},
            {"label": "Affiliate balance", "value": f"${round(affiliate_balance, 2)}"},
        ]

        return render_template(
            "dashboard.html",
            plan=plan,
            plan_label=plan_label,
            expiry=user.get("expiry"),
            subscription=subscription,
            profit=profit,
            trades=trades,
            bot_active=user.get("bot_active", 0),
            trade_amount=trade_amount,
            trade_type=user.get("trade_type", "futures"),
            spot_enabled=int(user.get("spot_enabled", 1) if user.get("spot_enabled") is not None else 1),
            futures_enabled=int(user.get("futures_enabled", 1) if user.get("futures_enabled") is not None else 1),
            referral_link=referral_link,
            referral_code=user.get("referral_code", ""),
            referral_qr_url=referral_qr_url,
            affiliate_balance=round(affiliate_balance, 2),
            total_referrals=refs_count,
            active_referrals=active_referrals,
            paid_referrals=paid_referrals,
            total_commissions=round(float(total_comm or 0), 2),
            total_withdrawn=round(float(total_withdrawn or 0), 2),
            is_admin=user.get("is_admin", 0),
            free_basic_unlocked=user.get("free_basic_unlocked", 0),
            free_pro_unlocked=user.get("free_pro_unlocked", 0),
            free_vip_unlocked=user.get("free_vip_unlocked", 0),
            chat_id=chat_id,
            is_linked=is_linked,
            dashboard_tier=dashboard_tier,
            dashboard_title=dashboard_title,
            dashboard_subtitle=dashboard_subtitle,
            dashboard_widgets=dashboard_widgets,
            notifications=notifications,
            recent_activity=recent_activity,
            signal_performance=signal_performance,
            recent_signals=recent_signals,
            performance_chart=performance_chart,
            bot_link=current_bot_link(),
            telegram_connect_link=telegram_connect_link
        )

    except Exception as e:
        log(f"❌ dashboard error: {e}")
        return f"❌ حصل خطأ أثناء تحميل الداشبورد: {str(e)}"


@dashboard_bp.route("/manual")
def manual():
    if "user" not in session:
        return redirect("/login")
    return render_template("manual.html")


@dashboard_bp.route("/manual-payment/<plan>")
@dashboard_bp.route("/pay/<plan>")
def manual_payment(plan):
    if not session.get("user"):
        return redirect("/login")

    plan = (plan or "").strip().lower()
    if plan not in PLAN_PRICES:
        return redirect("/dashboard")

    return render_template(
        "manual_payment.html",
        plan=plan,
        plan_label=PLAN_LABELS[plan],
        price=PLAN_PRICES[plan],
        original_price=PLAN_ORIGINAL_PRICES.get(plan, PLAN_PRICES[plan]),
        discount_percent=int(round((1 - (PLAN_PRICES[plan] / max(PLAN_ORIGINAL_PRICES.get(plan, PLAN_PRICES[plan]), 1))) * 100)),
        support_link=os.environ.get("SUPPORT_LINK", BOT_LINK),
        manual_wallet=os.environ.get("MANUAL_PAYMENT_WALLET", "TSiwGKuanfvay6RMem1zJ8QqcDFQKTXVF1"),
        manual_network=os.environ.get("MANUAL_PAYMENT_NETWORK", "USDT TRC20 / Binance"),
        bank_name="Abu Dhabi Commercial Bank PJSC",
        bank_account_title="ABDALLAH M ELSAYED MOSTAFA ELNHRWAY",
        bank_account_number="14566177920001",
        bank_iban="AE450030014566177920001",
        bank_currency="AED",
        bank_swift="ADCBAEAA",
        instapay_handle="abdallamohamed22@",
    )




# Nexora sale-ready safe dashboard pages
def _safe_current_user_snapshot():
    if not session.get("user"):
        return None
    snapshot = {
        "email": session.get("user"),
        "plan": "trial",
        "plan_label": PLAN_LABELS.get("trial", "Free Trial"),
        "expiry": None,
        "chat_id": None,
        "bot_active": 0,
        "trades": 0,
        "profit": 0,
        "is_paid": 0,
    }
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT email, plan, expiry, chat_id, bot_active, trades, profit, is_paid,
                   referral_code, affiliate_balance, total_referrals,
                   COALESCE(spot_enabled, 1) AS spot_enabled,
                   COALESCE(futures_enabled, 1) AS futures_enabled,
                   COALESCE(spot_auto_trade_enabled, 0) AS spot_auto_trade_enabled,
                   COALESCE(futures_auto_trade_enabled, 0) AS futures_auto_trade_enabled
            FROM users
            WHERE LOWER(email) = %s
            LIMIT 1
        """, (session["user"].lower(),))
        row = c.fetchone()
        conn.close()
        if row:
            snapshot.update(dict(row))
            plan = str(snapshot.get("plan") or "trial").strip().lower()
            snapshot["plan"] = plan
            snapshot["plan_label"] = PLAN_LABELS.get(plan, plan.title())
    except Exception as e:
        log(f"safe current user snapshot unavailable: {e}")
    return snapshot


def _dashboard_section(section_key):
    user = _safe_current_user_snapshot()
    if not user:
        return redirect("/login")

    sections = {
        "my-plan": {
            "title": "My Plan",
            "eyebrow": "Subscription",
            "summary": "Review your current plan, expiry, signal access, and upgrade options.",
            "cards": [
                ("Current Plan", user.get("plan_label", "Free Trial")),
                ("Expiry", user.get("expiry") or "Free Trial"),
                ("Premium", "Enabled" if int(user.get("is_paid") or 0) == 1 else "Disabled"),
                ("Free Signals", f"{min(int(user.get('trades') or 0), 2)}/2" if user.get("plan") == "trial" else "Premium access"),
            ],
            "actions": [("Upgrade Plan", "/payments"), ("Invoice History", "/invoice-history")],
        },
        "signals": {
            "title": "Signals",
            "eyebrow": "Trading Intelligence",
            "summary": "Signals are delivered through Telegram when market quality passes the engine filters.",
            "cards": [
                ("Telegram", "Connected" if user.get("chat_id") else "Not connected"),
                ("Bot", "Running" if int(user.get("bot_active") or 0) == 1 else "Stopped"),
                ("Spot", "Enabled" if int(user.get("spot_enabled") or 1) == 1 else "Disabled"),
                ("Futures", "Enabled" if int(user.get("futures_enabled") or 1) == 1 else "Disabled"),
            ],
            "actions": [("Connect Telegram", "/bot-check"), ("Open Dashboard", "/dashboard")],
        },
        "auto-trading": {
            "title": "Auto Trading",
            "eyebrow": "Elite Tools",
            "summary": "Auto trading is available only for eligible plans and requires saved exchange API keys.",
            "cards": [
                ("Eligible Plans", "Elite / Pro 2 Years"),
                ("Spot Auto", "Enabled" if int(user.get("spot_auto_trade_enabled") or 0) == 1 else "Disabled"),
                ("Futures Auto", "Enabled" if int(user.get("futures_auto_trade_enabled") or 0) == 1 else "Disabled"),
                ("Safety", "Stop loss required"),
            ],
            "actions": [("Configure In Dashboard", "/dashboard"), ("Read Risk Disclaimer", "/risk-disclaimer")],
        },
        "referrals": {
            "title": "Referrals",
            "eyebrow": "Affiliate",
            "summary": "Share your website referral link and track referral growth from the dashboard.",
            "cards": [
                ("Referral Code", user.get("referral_code") or "Create from dashboard"),
                ("Total Referrals", user.get("total_referrals") or 0),
                ("Balance", f"${round(float(user.get('affiliate_balance') or 0), 2)}"),
                ("Website Flow", "Landing -> Bot -> Dashboard"),
            ],
            "actions": [("Open Dashboard", "/dashboard"), ("Invite From Bot", "/bot-check")],
        },
        "payments": {
            "title": "Payments",
            "eyebrow": "Billing",
            "summary": "Choose automatic crypto checkout or manual payment without changing plan IDs.",
            "cards": [
                ("Basic", f"${PLAN_PRICES.get('basic')}"),
                ("Pro", f"${PLAN_PRICES.get('pro')}"),
                ("Elite", f"${PLAN_PRICES.get('vip')}"),
                ("Pro 2 Years", f"${PLAN_PRICES.get('pro_2y')}"),
            ],
            "actions": [("Pay Basic", "/create-payment?plan=basic"), ("Manual Payment", "/manual-payment/basic"), ("Invoices", "/invoice-history")],
        },
        "profile": {
            "title": "Profile",
            "eyebrow": "Account",
            "summary": "Your account identity and Telegram linking status.",
            "cards": [
                ("Email", user.get("email")),
                ("Telegram Chat", user.get("chat_id") or "Not linked"),
                ("Plan", user.get("plan_label")),
                ("Profit", f"${round(float(user.get('profit') or 0), 2)}"),
            ],
            "actions": [("Connect Telegram", "/bot-check"), ("Dashboard", "/dashboard")],
        },
        "settings": {
            "title": "Settings",
            "eyebrow": "Preferences",
            "summary": "Manage signal preferences from the dashboard using existing safe forms.",
            "cards": [
                ("Spot Signals", "Enabled" if int(user.get("spot_enabled") or 1) == 1 else "Disabled"),
                ("Futures Signals", "Enabled" if int(user.get("futures_enabled") or 1) == 1 else "Disabled"),
                ("Theme", "Saved in browser"),
                ("Security", "CSRF protected forms"),
            ],
            "actions": [("Open Dashboard Settings", "/dashboard"), ("Logout", "/logout")],
        },
    }
    page = sections.get(section_key)
    if not page:
        return redirect("/dashboard")
    return render_template("dashboard_section.html", page=page, user=user)


@dashboard_bp.route("/my-plan")
def my_plan_page():
    return _dashboard_section("my-plan")


@dashboard_bp.route("/signals")
def signals_page():
    return _dashboard_section("signals")


@dashboard_bp.route("/auto-trading")
def auto_trading_page():
    return _dashboard_section("auto-trading")


@dashboard_bp.route("/referrals")
def referrals_page():
    return _dashboard_section("referrals")


@dashboard_bp.route("/payments")
@dashboard_bp.route("/payment")
def payments_page():
    return _dashboard_section("payments")


@dashboard_bp.route("/profile")
def profile_page():
    return _dashboard_section("profile")


@dashboard_bp.route("/settings")
def settings_page():
    return _dashboard_section("settings")


def _admin_section(section_key):
    if not admin_required():
        return "Forbidden", 403
    sections = {
        "users": ("Users", "Search, review, and manage user records from the main admin table.", "/admin#users"),
        "subscriptions": ("Subscriptions", "Review plan distribution, active subscriptions, expiring users, and Pro 2 Years readiness.", "/admin#subscriptions"),
        "payments": ("Payments", "Monitor automatic invoices, coupons, processed payments, and revenue status.", "/admin#payments"),
        "manual-payments": ("Manual Payments", "Review manual payment and withdrawal operations from the admin center.", "/admin#manual-payments"),
        "repair-pro-2y": ("Repair Pro 2Y", "Run the POST-only maintenance action from the protected admin panel.", "/admin#repair-pro-2y"),
        "settings": ("Admin Settings", "Operational settings and safe admin shortcuts.", "/admin#settings"),
    }
    title, summary, back_href = sections.get(section_key, sections["users"])
    back_href = "/admin"
    return render_template("admin_section.html", title=title, summary=summary, back_href=back_href)


@admin_bp.route("/admin/users")
def admin_users_page():
    return _admin_section("users")


@admin_bp.route("/admin/subscriptions")
def admin_subscriptions_page():
    return _admin_section("subscriptions")


@admin_bp.route("/admin/payments")
def admin_payments_page():
    return _admin_section("payments")


@admin_bp.route("/admin/manual-payments")
def admin_manual_payments_page():
    return _admin_section("manual-payments")


@admin_bp.route("/admin/repair-pro-2y")
def admin_repair_pro_2y_page():
    return _admin_section("repair-pro-2y")


@admin_bp.route("/admin/settings")
def admin_settings_page():
    return _admin_section("settings")


# ================= SIMPLE DATA API =================
@dashboard_bp.route("/api/data")
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
@dashboard_bp.route("/toggle-bot", methods=["POST"])
def toggle_bot():
    if not session.get("user"):
        return redirect("/login")

    try:
        conn = db()
        c = conn.cursor()

        c.execute(
            "SELECT plan, bot_active, api_key, api_secret FROM users WHERE LOWER(email) = %s",
            (session["user"].lower(),)
        )
        user = c.fetchone()

# تأكد إنه Elite
        if not user or user[0] not in AUTO_TRADE_PLANS:
            conn.close()
            return "❌ الميزة متاحة فقط لخطط Elite / Pro 2 Years"

# فك التشفير
        saved_api_key = decrypt_text(user[2]) if user[2] else None
        saved_api_secret = decrypt_text(user[3]) if user[3] else None

# منع التشغيل بدون API
        if user[1] == 0:
            if not saved_api_key or not saved_api_secret:
                 conn.close()
                 return "❌ لازم تربط API أولاً قبل تشغيل البوت"

# تغيير حالة البوت
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
@payments_bp.route("/create-payment")
def create_payment():
    if not session.get("user"):
        return redirect("/login")

    plan = request.args.get("plan", "basic").strip().lower()
    coupon_code = normalize_coupon_code(request.args.get("coupon", ""))

    if plan not in PLAN_PRICES:
        return "❌ باقة غير صحيحة"

    try:
        nowpayments_key = os.environ.get("NOWPAYMENTS_API_KEY")
        if not nowpayments_key:
            return "❌ NOWPAYMENTS_API_KEY غير موجود في Railway Variables"

        conn = db()
        c = conn.cursor()

        c.execute(
            "SELECT chat_id, email FROM users WHERE LOWER(email) = %s",
            (session["user"].lower(),)
        )
        user = c.fetchone()

        if not user or not user[0]:
            conn.close()
            return "❌ لازم تربط حساب التليجرام الأول"

        chat_id = str(user[0]).strip()
        email = user[1]
        coupon_row = None

        if coupon_code:
            c.execute("""
                SELECT code, discount_percent, active, expires_at, max_redemptions, redemption_count
                FROM coupons
                WHERE UPPER(code) = %s
                LIMIT 1
            """, (coupon_code,))
            candidate_coupon = c.fetchone()
            valid_coupon, coupon_reason = coupon_is_active(candidate_coupon)
            if not valid_coupon:
                conn.close()
                return f"Coupon is not valid: {coupon_reason}"
            coupon_row = candidate_coupon

        original_amount, discount_amount, amount = apply_coupon_amount(plan, coupon_row)

        payload = {
            "price_amount": amount,
            "price_currency": "usd",
            "pay_currency": "usdttrc20",
            "order_id": chat_id,
            "order_description": plan,
            "success_url": f"{current_base_url()}/success",
            "cancel_url": f"{current_base_url()}/cancel",
            "ipn_callback_url": f"{current_base_url()}/payment-webhook"
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

        invoice_id = str(data.get("id") or data.get("invoice_id") or "").strip()
        invoice_url = data.get("invoice_url")

        c.execute("""
            INSERT INTO payment_invoices (
                invoice_id,
                chat_id,
                email,
                plan,
                status,
                amount,
                original_amount,
                discount_amount,
                currency,
                coupon_code,
                invoice_url,
                raw_response
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            invoice_id,
            chat_id,
            email,
            plan,
            "created" if invoice_url else "creation_failed",
            amount,
            original_amount,
            discount_amount,
            "usd",
            coupon_code or None,
            invoice_url,
            json.dumps(data, ensure_ascii=False),
        ))
        conn.commit()
        conn.close()

        if invoice_url:
            return redirect(invoice_url)

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


@payments_bp.route("/invoice-history")
def invoice_history():
    if not session.get("user"):
        return redirect("/login")

    conn = None
    try:
        conn = db()
        c = conn.cursor()
        c.execute(
            "SELECT chat_id FROM users WHERE LOWER(email) = %s LIMIT 1",
            (session["user"].lower(),),
        )
        user = c.fetchone()
        chat_id = str(user[0] or "").strip() if user else ""

        c.execute("""
            SELECT invoice_id, payment_id, plan, status, amount, original_amount,
                   discount_amount, currency, coupon_code, invoice_url, paid_at, created_at
            FROM payment_invoices
            WHERE LOWER(email) = %s OR chat_id = %s
            ORDER BY created_at DESC
            LIMIT 80
        """, (session["user"].lower(), chat_id))
        invoices = c.fetchall()
        return render_template("invoice_history.html", invoices=invoices, plan_labels=PLAN_LABELS)
    except Exception as e:
        log(f"invoice_history error: {e}")
        return "Unable to load invoice history", 500
    finally:
        if conn:
            conn.close()


# ================= OWNER FREE UPGRADE =================
@dashboard_bp.route("/owner-free-upgrade", methods=["POST"])
def owner_free_upgrade():
    """Legacy owner-only shortcut kept disabled by default.

    The commercial product no longer sells or exposes lifetime subscriptions.
    Enable only for internal maintenance by setting ENABLE_OWNER_FREE_UPGRADE=true.
    """
    if os.environ.get("ENABLE_OWNER_FREE_UPGRADE", "false").lower() not in ["1", "true", "yes", "on"]:
        return "Owner upgrade is disabled", 403

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
                expiry = %s,
                is_admin = 1,
                lifetime_owner = 0,
                bot_active = 1
            WHERE LOWER(email) = %s
        """, ((datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"), session["user"].lower()))
        conn.commit()
        conn.close()
        return "✅ تم تفعيل Elite سنة واحدة للحساب الإداري"
    except Exception as e:
        log(f"owner_free_upgrade error: {e}")
        return f"❌ Error: {str(e)}"


# ================= REQUEST WITHDRAWAL =================
@dashboard_bp.route("/request-withdrawal", methods=["POST"])
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

    if is_admin_email(email):
        try:
            conn = db()
            c = conn.cursor()
            c.execute("""
                UPDATE users
                SET is_admin = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(email) = %s
            """, (email,))
            conn.commit()
            conn.close()
        except Exception as e:
            log(f"admin self-heal skipped: {e}")
        return True

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

        is_admin_flag = int(row[0] or 0)
        return is_admin_flag == 1

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        log(f"is_current_admin error: {e}")
        return False


@admin_bp.route("/admin")
def admin_dashboard():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    conn = None
    try:
        conn = db()
        c = conn.cursor()

        def db_rollback():
            try:
                conn.rollback()
            except Exception:
                pass

        def safe_scalar(query, params=(), default=0):
            """Run an admin metric query without breaking the whole page.

            PostgreSQL aborts the current transaction after any failed query.
            Admin pages use many optional tables/columns, so every failed metric
            must rollback before the next query.
            """
            try:
                c.execute(query, params)
                row = c.fetchone()
                return row[0] if row and row[0] is not None else default
            except Exception as metric_error:
                db_rollback()
                log(f"admin metric unavailable: {metric_error}")
                return default

        def safe_rows(query, params=()):
            try:
                c.execute(query, params)
                return c.fetchall()
            except Exception as metric_error:
                db_rollback()
                log(f"admin rows unavailable: {metric_error}")
                return []

        total_users = int(safe_scalar("SELECT COUNT(*) FROM users", default=0) or 0)
        paid_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE is_paid = 1", default=0) or 0)
        linked_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE COALESCE(chat_id, '') != ''", default=0) or 0)
        active_bots = int(safe_scalar("SELECT COUNT(*) FROM users WHERE bot_active = 1", default=0) or 0)

        basic_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'basic'", default=0) or 0)
        pro_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'pro'", default=0) or 0)
        vip_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'vip'", default=0) or 0)
        pro_2y_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'pro_2y'", default=0) or 0)
        lifetime_users = 0
        free_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE COALESCE(is_paid, 0) != 1", default=0) or 0)
        subscription_rows = safe_rows("SELECT is_paid, plan, expiry, bot_active FROM users")
        subscription_admin = _subscription_admin_summary(subscription_rows)
        database_status = "online" if int(safe_scalar("SELECT 1", default=0) or 0) == 1 else "degraded"
        todays_registrations = int(safe_scalar("SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE", default=0) or 0)
        todays_payments = int(safe_scalar("""
            SELECT COUNT(*)
            FROM processed_payments
            WHERE created_at >= CURRENT_DATE
              AND payment_status IN ('finished', 'confirmed')
        """, default=0) or 0)

        total_affiliate_paid = float(safe_scalar(
            "SELECT COALESCE(SUM(amount), 0) FROM affiliate_commissions",
            default=0
        ) or 0)

        revenue = round(float(safe_scalar("""
            SELECT COALESCE(SUM(
                CASE
                    WHEN plan = 'basic' THEN %s
                    WHEN plan = 'pro' THEN %s
                    WHEN plan = 'vip' THEN %s
                    WHEN plan = 'pro_2y' THEN %s
                    ELSE 0
                END
            ), 0)
            FROM users
            WHERE is_paid = 1
        """, (PLAN_PRICES["basic"], PLAN_PRICES["pro"], PLAN_PRICES["vip"], PLAN_PRICES["pro_2y"]), default=0) or 0), 2)

        pending_withdrawals = int(safe_scalar("SELECT COUNT(*) FROM affiliate_withdrawals WHERE status != 'paid'", default=0) or 0)
        pending_withdrawal_amount = round(float(safe_scalar("SELECT COALESCE(SUM(amount), 0) FROM affiliate_withdrawals WHERE status != 'paid'", default=0) or 0), 2)
        paid_withdrawals = int(safe_scalar("SELECT COUNT(*) FROM affiliate_withdrawals WHERE status = 'paid'", default=0) or 0)

        payment_revenue = round(float(safe_scalar("""
            SELECT COALESCE(SUM(amount), 0)
            FROM processed_payments
            WHERE payment_status IN ('finished', 'confirmed')
        """, default=0) or 0), 2)
        if payment_revenue > 0:
            revenue = payment_revenue

        payments_total = int(safe_scalar("SELECT COUNT(*) FROM payment_invoices", default=0) or 0)
        payments_paid = int(safe_scalar("SELECT COUNT(*) FROM payment_invoices WHERE status = 'paid'", default=0) or 0)
        payments_failed = int(safe_scalar("SELECT COUNT(*) FROM failed_payments", default=0) or 0)
        payments_pending = int(safe_scalar("""
            SELECT COUNT(*)
            FROM payment_invoices
            WHERE status NOT IN ('paid', 'failed', 'expired', 'refunded', 'creation_failed')
        """, default=0) or 0)
        renewals_count = int(safe_scalar("SELECT COUNT(*) FROM subscription_renewals WHERE renewal_type = 'renewal'", default=0) or 0)

        users_7d = int(safe_scalar("""
            SELECT COUNT(*)
            FROM users
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
        """, default=0) or 0)
        revenue_7d = round(float(safe_scalar("""
            SELECT COALESCE(SUM(amount), 0)
            FROM processed_payments
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
              AND payment_status IN ('finished', 'confirmed')
        """, default=0) or 0), 2)
        paid_conversion = round((paid_users / total_users) * 100, 2) if total_users else 0

        signals_total = int(safe_scalar("SELECT COUNT(*) FROM trades_log", default=0) or 0)
        signals_open = int(safe_scalar("SELECT COUNT(*) FROM trades_log WHERE status = 'OPEN'", default=0) or 0)
        signals_closed = int(safe_scalar("SELECT COUNT(*) FROM trades_log WHERE status = 'CLOSED'", default=0) or 0)
        signals_wins = int(safe_scalar("SELECT COUNT(*) FROM trades_log WHERE status = 'CLOSED' AND COALESCE(pnl, 0) > 0", default=0) or 0)
        signals_profit = round(float(safe_scalar("SELECT COALESCE(SUM(pnl), 0) FROM trades_log", default=0) or 0), 2)
        signal_win_rate = round((signals_wins / signals_closed) * 100, 2) if signals_closed else 0
        last_signal_time = safe_scalar("SELECT MAX(created_at) FROM trades_log", default=None)
        telegram_health = "configured" if TOKEN else "missing_token"
        bot_health = "running" if active_bots > 0 else "idle"

        spot_stats = {
            "signals": 0,
            "open": 0,
            "closed": 0,
            "wins": 0,
            "profit": 0,
            "win_rate": 0,
        }
        futures_stats = dict(spot_stats)
        for row in safe_rows("""
            SELECT LOWER(COALESCE(trade_type, 'futures')) AS trade_type,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status = 'OPEN') AS open_count,
                   COUNT(*) FILTER (WHERE status = 'CLOSED') AS closed_count,
                   COUNT(*) FILTER (WHERE status = 'CLOSED' AND COALESCE(pnl, 0) > 0) AS wins,
                   COALESCE(SUM(COALESCE(pnl, 0)), 0) AS profit
            FROM trades_log
            GROUP BY LOWER(COALESCE(trade_type, 'futures'))
        """):
            trade_type = str(row[0] or "futures").lower()
            target = spot_stats if trade_type == "spot" else futures_stats
            target["signals"] = int(row[1] or 0)
            target["open"] = int(row[2] or 0)
            target["closed"] = int(row[3] or 0)
            target["wins"] = int(row[4] or 0)
            target["profit"] = round(float(row[5] or 0), 2)
            target["win_rate"] = round((target["wins"] / target["closed"]) * 100, 2) if target["closed"] else 0

        affiliate_referrals = int(safe_scalar("SELECT COUNT(*) FROM affiliate_referrals", default=0) or 0)
        affiliate_balance_total = round(float(safe_scalar("SELECT COALESCE(SUM(affiliate_balance), 0) FROM users", default=0) or 0), 2)
        affiliate_withdrawn = round(float(safe_scalar("SELECT COALESCE(SUM(amount), 0) FROM affiliate_withdrawals WHERE status = 'paid'", default=0) or 0), 2)
        active_plans_count = basic_users + pro_users + vip_users + pro_2y_users
        ai_score = min(99, max(50, round(62 + (signal_win_rate * 0.25) + min(signals_total, 100) * 0.08 + (8 if signals_profit > 0 else 0), 2)))
        avg_signal_pnl = round(signals_profit / signals_closed, 2) if signals_closed else 0
        telegram_delivery_rate = round((linked_users / total_users) * 100, 2) if total_users else 0
        queue_monitor = payments_pending + pending_withdrawals + signals_open

        admin_overview = {
            "revenue": revenue,
            "revenue_7d": revenue_7d,
            "users": total_users,
            "users_7d": users_7d,
            "paid_users": paid_users,
            "paid_conversion": paid_conversion,
            "payments_total": payments_total,
            "payments_paid": payments_paid,
            "payments_pending": payments_pending,
            "payments_failed": payments_failed,
            "renewals_count": renewals_count,
            "signals_total": signals_total,
            "signals_open": signals_open,
            "signals_closed": signals_closed,
            "signal_win_rate": signal_win_rate,
            "signals_profit": signals_profit,
            "affiliate_referrals": affiliate_referrals,
            "affiliate_balance_total": affiliate_balance_total,
            "affiliate_withdrawn": affiliate_withdrawn,
            "growth_users_7d": users_7d,
            "growth_revenue_7d": revenue_7d,
            "ai_score": ai_score,
            "avg_signal_pnl": avg_signal_pnl,
            "spot": spot_stats,
            "futures": futures_stats,
            "active_plans_count": active_plans_count,
            "active_users": subscription_admin["active_users"],
            "free_users": subscription_admin["free_users"],
            "premium_users": subscription_admin["premium_users"],
            "expired_subscriptions": subscription_admin["expired_subscriptions"],
            "expiring_subscriptions": subscription_admin["expiring_subscriptions"],
            "last_signal_time": last_signal_time or "No signals yet",
            "bot_status": bot_health,
            "database_status": database_status,
            "telegram_status": telegram_health,
            "todays_registrations": todays_registrations,
            "todays_payments": todays_payments,
            "worker_status": "configured" if os.environ.get("RAILWAY_SERVICE_NAME") or os.environ.get("DATABASE_URL") else "local",
            "users_online": active_bots,
            "revenue_today": round(float(safe_scalar("""
                SELECT COALESCE(SUM(amount), 0)
                FROM processed_payments
                WHERE created_at >= CURRENT_DATE
                  AND payment_status IN ('finished', 'confirmed')
            """, default=0) or 0), 2),
            "telegram_delivery_rate": telegram_delivery_rate,
            "signal_success_rate": signal_win_rate,
            "ai_engine_health": "healthy" if ai_score >= 65 else "warming_up",
            "queue_monitor": queue_monitor,
        }

        user_rows = safe_rows("""
            SELECT id, email, plan, is_paid, expiry, chat_id, affiliate_balance, total_referrals,
                   trial_start, trades
            FROM users
            ORDER BY id DESC
        """)
        users = []
        today = datetime.now().date()
        for row in user_rows:
            expiry_date = _safe_date(row[4])
            remaining_days = None
            if expiry_date:
                remaining_days = max((expiry_date - today).days, 0)
            users.append(tuple(row) + (remaining_days,))

        withdrawals = safe_rows("""
            SELECT id, chat_id, wallet_address, amount, status, created_at
            FROM affiliate_withdrawals
            ORDER BY id DESC
        """)

        recent_payments = safe_rows("""
            SELECT invoice_id, email, plan, status, amount, created_at
            FROM payment_invoices
            ORDER BY created_at DESC
            LIMIT 8
        """)
        recent_admin_signals = safe_rows("""
            SELECT chat_id, pair, direction, entry, tp, sl, confidence, status, created_at
            FROM trades_log
            ORDER BY created_at DESC
            LIMIT 8
        """)
        coupons = safe_rows("""
            SELECT id, code, discount_percent, active, expires_at, max_redemptions, redemption_count, created_at
            FROM coupons
            ORDER BY id DESC
            LIMIT 60
        """)

        conn.close()

        return render_template(
            "admin.html",
            total_users=total_users,
            paid_users=paid_users,
            revenue=revenue,
            total_affiliate_paid=total_affiliate_paid,
            linked_users=linked_users,
            active_bots=active_bots,
            basic_users=basic_users,
            pro_users=pro_users,
            vip_users=vip_users,
            pro_2y_users=pro_2y_users,
            lifetime_users=lifetime_users,
            free_users=free_users,
            pending_withdrawals=pending_withdrawals,
            pending_withdrawal_amount=pending_withdrawal_amount,
            paid_withdrawals=paid_withdrawals,
            users=users,
            withdrawals=withdrawals,
            coupons=coupons,
            recent_payments=recent_payments,
            recent_admin_signals=recent_admin_signals,
            admin_overview=admin_overview
        )

    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        log(f"admin_dashboard error: {e}")
        return render_template(
            "admin.html",
            total_users=0,
            paid_users=0,
            revenue=0,
            total_affiliate_paid=0,
            linked_users=0,
            active_bots=0,
            basic_users=0,
            pro_users=0,
            vip_users=0,
            pro_2y_users=0,
            lifetime_users=0,
            free_users=0,
            pending_withdrawals=0,
            pending_withdrawal_amount=0,
            paid_withdrawals=0,
            users=[],
            withdrawals=[],
            coupons=[],
            admin_overview={
                "revenue": 0,
                "revenue_7d": 0,
                "users": 0,
                "users_7d": 0,
                "paid_users": 0,
                "paid_conversion": 0,
                "payments_total": 0,
                "payments_paid": 0,
                "payments_pending": 0,
                "payments_failed": 0,
                "renewals_count": 0,
                "signals_total": 0,
                "signals_open": 0,
                "signals_closed": 0,
                "signal_win_rate": 0,
                "signals_profit": 0,
                "affiliate_referrals": 0,
                "affiliate_balance_total": 0,
                "affiliate_withdrawn": 0,
                "growth_users_7d": 0,
                "growth_revenue_7d": 0,
                "ai_score": 0,
                "avg_signal_pnl": 0,
                "spot": {"signals": 0, "open": 0, "closed": 0, "wins": 0, "profit": 0, "win_rate": 0},
                "futures": {"signals": 0, "open": 0, "closed": 0, "wins": 0, "profit": 0, "win_rate": 0},
                "active_plans_count": 0,
                "active_users": 0,
                "free_users": 0,
                "premium_users": 0,
                "expired_subscriptions": 0,
                "expiring_subscriptions": 0,
                "last_signal_time": "No signals yet",
                "bot_status": "unknown",
                "database_status": "degraded",
                "telegram_status": "unknown",
                "todays_registrations": 0,
                "todays_payments": 0,
                "worker_status": "unknown",
                "users_online": 0,
                "revenue_today": 0,
                "telegram_delivery_rate": 0,
                "signal_success_rate": 0,
                "ai_engine_health": "unknown",
                "queue_monitor": 0,
                "error": str(e),
            },
            recent_payments=[],
            recent_admin_signals=[]
        )


@admin_bp.route("/admin/system-health")
def admin_system_health():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    checks = {
        "Database": {"status": "unknown", "detail": "Not checked"},
        "Telegram": {"status": "configured" if TOKEN else "missing", "detail": "Token configured" if TOKEN else "TELEGRAM_TOKEN missing"},
        "Scheduler": {"status": "configured", "detail": "Auto sender loop is code-configured"},
        "Worker": {"status": "configured" if os.environ.get("DATABASE_URL") else "local", "detail": os.environ.get("RAILWAY_SERVICE_NAME", "Local/runtime worker")},
        "AI Engine": {"status": "configured", "detail": "AI modules import from project runtime"},
        "Signal Engine": {"status": "configured", "detail": "Market analyzer and sender modules available"},
        "Payment System": {"status": "configured" if os.environ.get("NOWPAYMENTS_API_KEY") else "missing_key", "detail": "NOWPayments key configured" if os.environ.get("NOWPAYMENTS_API_KEY") else "NOWPAYMENTS_API_KEY missing"},
    }
    last_signal = "No signals yet"

    conn = None
    try:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT 1")
        checks["Database"] = {"status": "online", "detail": "SELECT 1 succeeded"}
        try:
            c.execute("SELECT MAX(created_at) FROM trades_log")
            row = c.fetchone()
            if row and row[0]:
                last_signal = row[0]
        except Exception as signal_error:
            conn.rollback()
            checks["Signal Engine"] = {"status": "degraded", "detail": f"Last signal unavailable: {signal_error}"}
    except Exception as db_error:
        checks["Database"] = {"status": "offline", "detail": str(db_error)}
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    return render_template(
        "admin_health.html",
        checks=checks,
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        last_signal=last_signal,
    )


@admin_bp.route("/admin/repair-plan-constraint", methods=["POST"])
def repair_plan_constraint():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    conn = None
    try:
        conn = db()
        c = conn.cursor()
        c.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_plan")
        c.execute("ALTER TABLE users ADD CONSTRAINT ck_users_plan CHECK (plan IN ('trial','basic','pro','vip','pro_2y'))")
        conn.commit()
        flash("Plan constraint repaired. pro_2y is now supported.", "success")
    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        log(f"repair_plan_constraint error: {e}")
        flash(f"Plan constraint repair failed: {e}", "error")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    return redirect("/admin")

@admin_bp.route("/admin/coupons/create", methods=["POST"])
def create_coupon():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        code = normalize_coupon_code(request.form.get("code", ""))
        discount_percent = float(request.form.get("discount_percent", "0") or 0)
        max_redemptions_raw = request.form.get("max_redemptions", "").strip()
        expires_at = request.form.get("expires_at", "").strip() or None
        max_redemptions = int(max_redemptions_raw) if max_redemptions_raw else None

        if not code:
            return "Coupon code is required", 400

        discount_percent = max(0.0, min(discount_percent, 95.0))

        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO coupons (code, discount_percent, active, expires_at, max_redemptions)
            VALUES (%s, %s, 1, %s, %s)
            ON CONFLICT (code)
            DO UPDATE SET discount_percent = EXCLUDED.discount_percent,
                          active = 1,
                          expires_at = EXCLUDED.expires_at,
                          max_redemptions = EXCLUDED.max_redemptions,
                          updated_at = CURRENT_TIMESTAMP
        """, (code, discount_percent, expires_at, max_redemptions))
        conn.commit()
        conn.close()
        audit_log("admin_coupon_create", details=f"code={code} discount={discount_percent}")
        return redirect("/admin")
    except Exception as e:
        log(f"create_coupon error: {e}")
        return f"❌ Error: {str(e)}"


@admin_bp.route("/admin/coupons/toggle", methods=["POST"])
def toggle_coupon():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        coupon_id = request.form.get("id", "").strip()
        conn = db()
        c = conn.cursor()
        c.execute("""
            UPDATE coupons
            SET active = CASE WHEN COALESCE(active, 1) = 1 THEN 0 ELSE 1 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (coupon_id,))
        conn.commit()
        conn.close()
        audit_log("admin_coupon_toggle", details=f"id={coupon_id}")
        return redirect("/admin")
    except Exception as e:
        log(f"toggle_coupon error: {e}")
        return f"❌ Error: {str(e)}"


@admin_bp.route("/activate-user", methods=["POST"])
def activate_user():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        user_id = request.form.get("id", "").strip()
        plan = request.form.get("plan", "basic").strip().lower()
        if plan not in PLAN_PRICES:
            plan = "basic"

        expiry = (datetime.now() + timedelta(days=PLAN_DURATIONS_DAYS.get(plan) or 30)).strftime("%Y-%m-%d")

        conn = db()
        c = conn.cursor()

        c.execute("""
            UPDATE users
            SET is_paid = 1, plan = %s, expiry = %s, lifetime_owner = 0, bot_active = CASE WHEN %s IN ('vip', 'pro_2y') THEN 1 ELSE bot_active END
            WHERE id = %s
        """, (plan, expiry, plan, user_id))

        conn.commit()
        conn.close()

        log(f"✅ User {user_id} activated with plan {plan}")
        audit_log("admin_activate_user", details=f"user_id={user_id} plan={plan}")
        return redirect("/admin")

    except Exception as e:
        log(f"activate_user error: {e}")
        return f"❌ Error: {str(e)}"


@admin_bp.route("/delete-user", methods=["POST"])
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
        audit_log("admin_delete_user", details=f"user_id={user_id}")
        return redirect("/admin")

    except Exception as e:
        log(f"delete_user error: {e}")
        return f"❌ Error: {str(e)}"


@admin_bp.route("/mark-withdrawal-paid", methods=["POST"])
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
        audit_log("admin_mark_withdrawal_paid", details=f"withdrawal_id={withdrawal_id}")
        return redirect("/admin")

    except Exception as e:
        log(f"mark_withdrawal_paid error: {e}")
        return f"❌ Error: {str(e)}"


# ================= TELEGRAM WEBHOOK =================
def get_telegram_user(c, chat_id):
    admin_telegram_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    if admin_telegram_id and str(chat_id).strip() == admin_telegram_id and ADMIN_EMAIL:
        return {
            "id": None,
            "email": ADMIN_EMAIL,
            "trades": 0,
            "is_paid": 1,
            "referral_code": None,
            "plan": "vip",
            "expiry": None,
            "is_admin": 1,
            "lifetime_owner": 0,
            "bot_active": 1,
            "profit": 0,
            "affiliate_balance": 0,
            "total_referrals": 0,
            "spot_enabled": 1,
            "futures_enabled": 1,
            "chat_id": str(chat_id).strip(),
        }

    c.execute("""
        SELECT id, email, trades, is_paid, referral_code, plan, expiry,
               is_admin, lifetime_owner, bot_active, profit,
               affiliate_balance, total_referrals,
               COALESCE(spot_enabled, 1) AS spot_enabled,
               COALESCE(futures_enabled, 1) AS futures_enabled
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
    row = c.fetchone()
    if not row:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "trades": row[2],
        "is_paid": row[3],
        "referral_code": row[4],
        "plan": row[5],
        "expiry": row[6],
        "is_admin": row[7],
        "lifetime_owner": row[8],
        "bot_active": row[9],
        "profit": row[10],
        "affiliate_balance": row[11],
        "total_referrals": row[12],
        "spot_enabled": row[13],
        "futures_enabled": row[14],
        "chat_id": str(chat_id).strip(),
    }


def is_telegram_admin_user(user):
    if not user:
        return False
    admin_telegram_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    if admin_telegram_id and str(user.get("chat_id") or "").strip() == admin_telegram_id:
        return True
    return (
        int(user.get("is_admin") or 0) == 1
        and is_admin_email(user.get("email"))
    ) 


def build_telegram_user_stats(c, user, chat_id):
    stats = {
        "trades": int(user.get("trades") or 0),
        "profit": round(float(user.get("profit") or 0), 2),
        "affiliate_balance": round(float(user.get("affiliate_balance") or 0), 2),
        "total_referrals": int(user.get("total_referrals") or 0),
        "spot_today": 0,
        "futures_today": 0,
        "spot_win_rate": 0,
        "futures_win_rate": 0,
    }
    try:
        c.execute("""
            SELECT
                LOWER(COALESCE(trade_type, 'futures')) AS trade_type,
                COUNT(*) FILTER (WHERE created_at >= date_trunc('day', NOW())) AS today_count,
                COUNT(*) FILTER (WHERE status = 'CLOSED') AS closed_count,
                COUNT(*) FILTER (WHERE status = 'CLOSED' AND COALESCE(pnl, 0) > 0) AS wins
            FROM trades_log
            WHERE chat_id = %s
            GROUP BY LOWER(COALESCE(trade_type, 'futures'))
        """, (chat_id,))
        for row in c.fetchall():
            trade_type = str(row[0] or "futures").lower()
            closed_count = int(row[2] or 0)
            wins = int(row[3] or 0)
            win_rate = round((wins / closed_count) * 100, 2) if closed_count else 0
            if trade_type == "spot":
                stats["spot_today"] = int(row[1] or 0)
                stats["spot_win_rate"] = win_rate
            elif trade_type == "futures":
                stats["futures_today"] = int(row[1] or 0)
                stats["futures_win_rate"] = win_rate
    except Exception as e:
        log(f"telegram stats unavailable: {e}")
    return stats


def build_telegram_admin_stats(c):
    c.execute("""
        SELECT
            COUNT(*) AS total_users,
            COUNT(*) FILTER (WHERE is_paid = 1) AS paid_users,
            COUNT(*) FILTER (WHERE chat_id IS NOT NULL AND chat_id <> '') AS linked_users,
            COUNT(*) FILTER (WHERE bot_active = 1) AS active_bots,
            COUNT(*) FILTER (WHERE plan = 'basic') AS starter_users,
            COUNT(*) FILTER (WHERE plan = 'pro') AS pro_users,
            COUNT(*) FILTER (WHERE plan = 'vip') AS elite_users
        FROM users
    """)
    row = c.fetchone()
    c.execute("SELECT COUNT(*) FROM affiliate_withdrawals WHERE status = 'pending'")
    pending = c.fetchone()[0]
    return {
        "total_users": row[0],
        "paid_users": row[1],
        "linked_users": row[2],
        "active_bots": row[3],
        "starter_users": row[4],
        "pro_users": row[5],
        "elite_users": row[6],
        "pending_withdrawals": pending,
    }


def run_telegram_broadcast(c, message, paid_only=False):
    if paid_only:
        c.execute("""
            SELECT DISTINCT chat_id
            FROM users
            WHERE chat_id IS NOT NULL
              AND chat_id <> ''
              AND (is_paid = 1 OR is_admin = 1)
        """)
        target = "paid users"
    else:
        c.execute("""
            SELECT DISTINCT chat_id
            FROM users
            WHERE chat_id IS NOT NULL
              AND chat_id <> ''
        """)
        target = "all linked users"

    sent_count = 0
    failed_count = 0
    for row in c.fetchall():
        ok = send(row[0], message)
        if ok:
            sent_count += 1
        else:
            failed_count += 1
    return sent_count, failed_count, target


@telegram_bp.route("/webhook", methods=["POST"])
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

        command = text.split(maxsplit=1)[0].lower() if text else ""

        if command in ["/help", "/commands"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                send(chat_id, command_menu(is_telegram_admin_user(tg_user)))
                conn.close()
            except Exception as e:
                log(f"telegram help error: {e}")
                send(chat_id, command_menu(False))
            return "ok", 200

        if command in ["/subscription", "/status", "/check_subscription"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                send(chat_id, subscription_message(tg_user))
                conn.close()
            except Exception as e:
                log(f"telegram subscription error: {e}")
                send(chat_id, "Could not load subscription status now.")
            return "ok", 200

        if command in ["/stats", "/statistics"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                if not tg_user:
                    send(chat_id, "لا يوجد حساب مربوط بهذا Telegram. استخدم /start أولاً.")
                else:
                    stats = build_telegram_user_stats(c, tg_user, chat_id)
                    send(chat_id, user_statistics_message(stats))
                conn.close()
            except Exception as e:
                log(f"telegram stats error: {e}")
                send(chat_id, "Could not load statistics now.")
            return "ok", 200

        if command == "/admin":
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                if is_telegram_admin_user(tg_user):
                    send(chat_id, admin_menu())
                else:
                    send(chat_id, "Admin access required.")
                conn.close()
            except Exception as e:
                log(f"telegram admin menu error: {e}")
                send(chat_id, "Admin access check failed.")
            return "ok", 200

        if command == "/admin_stats":
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                if not is_telegram_admin_user(tg_user):
                    send(chat_id, "Admin access required.")
                else:
                    stats = build_telegram_admin_stats(c)
                    send(chat_id, admin_statistics_message(stats))
                conn.close()
            except Exception as e:
                log(f"telegram admin stats error: {e}")
                send(chat_id, "Could not load admin statistics.")
            return "ok", 200

        if command in ["/broadcast", "/broadcast_paid"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                if not is_telegram_admin_user(tg_user):
                    send(chat_id, "Admin access required.")
                    conn.close()
                    return "ok", 200

                parts = text.split(maxsplit=1)
                if len(parts) < 2 or not parts[1].strip():
                    send(chat_id, "Usage: /broadcast your message")
                    conn.close()
                    return "ok", 200

                message = parts[1].strip()
                paid_only = command == "/broadcast_paid"
                sent_count, failed_count, target = run_telegram_broadcast(c, message, paid_only=paid_only)
                audit_log("telegram_broadcast", tg_user.get("email"), f"target={target} sent={sent_count} failed={failed_count}")
                send(chat_id, broadcast_result_message(sent_count, failed_count, target))
                conn.close()
            except Exception as e:
                log(f"telegram broadcast error: {e}")
                send(chat_id, "Broadcast failed.")
            return "ok", 200

        # ================= /start =================
        if text.startswith("/start"):
            start_ref = None
            parts = text.split()

            link_token = None
            if len(parts) > 1 and parts[1].startswith("link_"):
                link_token = parts[1].replace("link_", "", 1).strip()
            elif len(parts) > 1 and parts[1].startswith("ref_"):
                start_ref = parts[1].replace("ref_", "").strip()

            conn = db()
            c = conn.cursor()

            if link_token:
                try:
                    handle_telegram_link_token(c, conn, chat_id, link_token)
                except Exception as link_err:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    log(f"TELEGRAM_LINK_TOKEN_ERROR chat_id={chat_id} error={link_err}")
                    send(chat_id, "Telegram link failed. Open your Nexora dashboard and tap Connect Telegram Bot again.")
                finally:
                    conn.close()
                return "ok", 200

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
                            WHEN is_paid = 1 THEN 2
                            ELSE 3
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

                    send(chat_id, linked_message(current_plan, expiry, is_admin_flag == 1 ))

                    if is_admin_flag == 1 :
                        send(chat_id, command_menu(True))
                        return "ok", 200

                    if is_paid:
                        send(chat_id, subscription_message({
                            "plan": current_plan,
                            "expiry": expiry,
                            "is_paid": 1,
                            "trades": trades,
                            "bot_active": 1,
                            "spot_enabled": 1,
                            "futures_enabled": 1,
                        }))

                        aff_link = telegram_referral_link(referral_code)
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
                                success = send(chat_id, f"🔥 إشارة مجانية #{i}\n" + format_signal(signal))

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
• وفي Elite تقدر تربط حسابك للتنفيذ التلقائي

⚠️ البوت مش بيبعت صفقات لمجرد الإرسال،
هو بيستنى الفرصة الواضحة فقط.

💰 لو حابب تكمل:
ادخل على الموقع وفعّل الباقة المناسبة ليك.
""")
                            else:
                                send(chat_id, "❌ حصلت مشكلة أثناء إرسال الإشارات المجانية. حاول /start مرة تانية.")

                    else:
                        aff_link = telegram_referral_link(referral_code)

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
                    register_link = f"{current_base_url()}/register?chat_id={chat_id}"

                    send(chat_id, welcome_message(register_link))

            except Exception as db_err:
                log(f"❌ /start DB Error: {db_err}")
                send(chat_id, "❌ حصل خطأ أثناء التحقق من حسابك. حاول تاني بعد شوية.")
            finally:
                conn.close()

            return "ok", 200

        # ============ LINK ACCOUNT ============
        elif "@" in text:
            try:
                conn = db()
                c = conn.cursor()

                email = text.lower().strip()

                c.execute("SELECT id FROM users WHERE email = %s", (email,))
                user = c.fetchone()

                if not user:
                    register_link = f"{current_base_url()}/register?chat_id={chat_id}"
                    send(chat_id, f"""لم يتم العثور على هذا الإيميل في الموقع.

سجل حسابك من الرابط الآمن:
{register_link}
""")
                    return "ok", 200

                login_link = f"{current_base_url()}/login?chat_id={chat_id}"
                send(chat_id, f"""لحماية حسابك، لا يتم ربط تيليجرام بمجرد كتابة الإيميل.

ادخل من الرابط الآمن وسجل دخولك بكلمة السر لربط الحساب:
{login_link}
""")
                return "ok", 200

                if not user:
                    send(chat_id, "❌ الإيميل غير موجود في الموقع")
                else:
                    c.execute(
                        "UPDATE users SET chat_id = %s WHERE email = %s",
                        (chat_id, email)
                    )
                    conn.commit()

                    send(chat_id, "✅ تم ربط حسابك بنجاح!\nهتوصلك الإشارات هنا 👌")

            except Exception as e:
                log(f"link account error: {e}")
                send(chat_id, "❌ حصل خطأ حاول تاني")
            finally:
                try:
                    conn.close()
                except:
                    pass

            return "ok", 200

        # ============ /affiliate ============

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

                aff_link = telegram_referral_link(referral_code)

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
def get_nowpayments_ipn_secret():
    for env_name in ("NOWPAYMENTS_IPN_SECRET", "NOWPAYMENTS_IPN_CALLBACK_SECRET", "IPN_SECRET"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value, env_name
    return "", None


@payments_bp.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    data = request.get_json(silent=True) or {}
    raw_payload = json.dumps(data, ensure_ascii=False)

    try:
        signature = request.headers.get("x-nowpayments-sig", "").strip()
        ipn_secret, ipn_env_name = get_nowpayments_ipn_secret()
        log(f"NOWPAYMENTS_IPN_CHECK signature_present={bool(signature)} ipn_secret_configured={bool(ipn_secret)} env={ipn_env_name or 'missing'}")
        valid_signature, generated_sig = validate_nowpayments_signature(data, signature, ipn_secret)

        if not valid_signature:
            if not signature:
                log("NOWPAYMENTS_IPN_REJECTED reason=missing_signature ipn_secret_configured=%s" % bool(ipn_secret))
            elif not ipn_secret:
                log("NOWPAYMENTS_IPN_REJECTED reason=missing_ipn_secret supported_env=NOWPAYMENTS_IPN_SECRET,NOWPAYMENTS_IPN_CALLBACK_SECRET,IPN_SECRET")
            else:
                log("NOWPAYMENTS_IPN_REJECTED reason=invalid_signature ipn_secret_configured=True")
            try:
                conn = db()
                c = conn.cursor()
                c.execute("""
                    INSERT INTO failed_payments (payment_id, invoice_id, order_id, plan, payment_status, reason, raw_payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(data.get("payment_id") or ""),
                    str(data.get("invoice_id") or ""),
                    str(data.get("order_id") or ""),
                    str(data.get("order_description") or ""),
                    str(data.get("payment_status") or "signature_error"),
                    "invalid_signature",
                    raw_payload,
                ))
                conn.commit()
                conn.close()
            except Exception as audit_err:
                log(f"payment signature audit error: {audit_err}")
            log("NOWPAYMENTS_IPN_REJECTED stored_failed_payment reason=invalid_signature")
            return "invalid signature", 403

        payment_status = str(data.get("payment_status") or "").strip().lower()
        payment_id = str(data.get("payment_id") or data.get("invoice_id") or "").strip()
        invoice_id = str(data.get("invoice_id") or data.get("id") or "").strip()
        chat_id = str(data.get("order_id") or "").strip()
        plan = (data.get("order_description") or "basic").strip().lower()

        if plan not in PLAN_PRICES:
            log(f"❌ Invalid payment plan ignored: {plan}")
            return "invalid plan", 400

        if not chat_id:
            return "missing order_id", 400

        if not payment_id:
            return "missing payment_id", 400

        conn = db()
        c = conn.cursor()

        c.execute("""
            SELECT id, amount, original_amount, discount_amount, coupon_code, invoice_url, status
            FROM payment_invoices
            WHERE (invoice_id = %s AND %s <> '')
               OR (payment_id = %s AND %s <> '')
               OR (chat_id = %s AND plan = %s)
            ORDER BY created_at DESC
            LIMIT 1
        """, (invoice_id, invoice_id, payment_id, payment_id, chat_id, plan))
        invoice = c.fetchone()
        invoice_row_id = invoice[0] if invoice else None
        paid_amount = float(invoice[1] if invoice else PLAN_PRICES.get(plan, PLAN_PRICES["basic"]))
        coupon_code = invoice[4] if invoice else None
        invoice_url = invoice[5] if invoice else None

        bucket = payment_status_bucket(payment_status)
        if bucket != "success":
            c.execute("""
                INSERT INTO failed_payments (
                    payment_id, invoice_id, order_id, plan, payment_status, reason, raw_payload
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                payment_id,
                invoice_id,
                chat_id,
                plan,
                payment_status,
                bucket,
                raw_payload,
            ))
            if invoice_row_id:
                c.execute("""
                    UPDATE payment_invoices
                    SET payment_id = %s,
                        status = %s,
                        raw_response = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (payment_id, payment_status or bucket, raw_payload, invoice_row_id))
            conn.commit()
            conn.close()
            log(f"ℹ️ Payment status tracked: {payment_status} | payment_id={payment_id}")
            return "tracked", 200

        # ================= منع تكرار نفس الدفع =================
        c.execute("""
            SELECT payment_id
            FROM processed_payments
            WHERE payment_id = %s
            LIMIT 1
        """, (payment_id,))
        already_processed = c.fetchone()

        if already_processed:
            if invoice_row_id:
                c.execute("""
                    UPDATE payment_invoices
                    SET status = 'paid_duplicate',
                        payment_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (payment_id, invoice_row_id))
                conn.commit()
            conn.close()
            log(f"⚠️ Duplicate payment ignored: {payment_id}")
            return "already processed", 200

        # خزّن العملية أولاً
        c.execute("""
            INSERT INTO processed_payments (
                payment_id, order_id, payment_status, plan, amount, currency, invoice_id, invoice_url, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (payment_id, chat_id, payment_status, plan, paid_amount, "usd", invoice_id, invoice_url, raw_payload))

        c.execute("""
            SELECT email, referred_by, expiry, lifetime_owner
            FROM users
            WHERE chat_id = %s
            LIMIT 1
        """, (chat_id,))
        buyer = c.fetchone()
        previous_expiry = buyer[2] if buyer else None
        new_expiry, is_renewal = calculate_subscription_expiry(previous_expiry, days=PLAN_DURATIONS_DAYS.get(plan) or 36500)
        c.execute("""
            UPDATE users
            SET is_paid = 1,
                plan = %s,
                expiry = %s,
                lifetime_owner = 0,
                bot_active = CASE WHEN %s IN ('vip', 'pro_2y') THEN 1 ELSE bot_active END
            WHERE chat_id = %s
        """, (plan, new_expiry, plan, chat_id))

        c.execute("""
            INSERT INTO subscription_renewals (
                chat_id, email, plan, payment_id, previous_expiry, new_expiry, amount, renewal_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            chat_id,
            buyer[0] if buyer else None,
            plan,
            payment_id,
            previous_expiry,
            new_expiry,
            paid_amount,
            "renewal" if is_renewal else "new",
        ))

        if invoice_row_id:
            c.execute("""
                UPDATE payment_invoices
                SET payment_id = %s,
                    status = 'paid',
                    paid_at = CURRENT_TIMESTAMP,
                    raw_response = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (payment_id, raw_payload, invoice_row_id))

        if coupon_code:
            c.execute("""
                UPDATE coupons
                SET redemption_count = COALESCE(redemption_count, 0) + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE UPPER(code) = %s
            """, (str(coupon_code).upper(),))

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
                        SELECT id
                        FROM affiliate_commissions
                        WHERE referrer_chat_id = %s
                          AND referred_chat_id = %s
                          AND payment_id = %s
                        LIMIT 1
                    """, (referrer_chat_id, chat_id, payment_id))
                    commission_exists = c.fetchone()

                    if not commission_exists:
                        commission_amount, commission_percent = calculate_commission(plan, paid_amount)

                        c.execute("""
                            INSERT INTO affiliate_commissions (
                                referrer_chat_id,
                                referred_chat_id,
                                plan,
                                payment_id,
                                amount,
                                status
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (referrer_chat_id, chat_id, plan, payment_id, commission_amount, "approved"))

                        c.execute("""
                            UPDATE users
                            SET affiliate_balance = COALESCE(affiliate_balance, 0) + %s,
                                total_referrals = COALESCE(total_referrals, 0) + %s
                            WHERE chat_id = %s
                        """, (commission_amount, 0 if already_exists else 1, referrer_chat_id))

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
                                send(referrer_chat_id, "💎 مبروك! فتحت Elite مجانًا بسبب نظام الأفلييت.")

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
⏳ الانتهاء: {new_expiry}

🚀 هتوصلك الإشارات تلقائي الآن
""")

        log(f"✅ Payment activated for chat_id={chat_id}, plan={plan}, payment_id={payment_id}, expiry={new_expiry}")

    except Exception as e:
        log(f"❌ Webhook Error: {e}")

    return "OK"
