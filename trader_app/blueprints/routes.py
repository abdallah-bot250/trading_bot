from flask import Blueprint
from urllib.parse import urlparse
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
                "Features may differ between Starter, Pro, and Elite plans as described on the pricing page and dashboard."
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
                "Plan value: Starter, Pro, and Elite should each have real differences and useful features."
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
                "Choose Starter, Pro, or Elite based on the dashboard and signal features you need."
            ]),
            ("Plans", [
                "Starter includes basic signal access and Telegram delivery.",
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
    return render_template(
        "bot_check.html",
        bot_link=os.environ.get("BOT_LINK", BOT_LINK),
        base_url=BASE_URL,
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


# ================= REGISTER =================
@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("8 per minute", methods=["POST"])
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
                    audit_log("register_existing_bad_password", email)
                    flash("❌ هذا الإيميل مسجل بالفعل لكن كلمة السر غير صحيحة", "error")
                    return redirect(url_for("auth.register", chat_id=chat_id, ref=ref))

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
                audit_log("register_existing_login", email, f"chat_id_linked={bool(chat_id)}")

                log(f"✅ Existing user logged in from register: {email} | chat_id={chat_id} | ref={final_ref}")

                flash("✅ تم تسجيل الدخول بنجاح", "success")
                flash("مهم جدًا: افتح البوت الرسمي واتبع رابط الربط الآمن، ثم سجل دخولك من الموقع لتأكيد Telegram.", "success")

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

            log(f"✅ New user registered: {email} | chat_id={chat_id} | ref={final_ref}")

            flash("✅ تم إنشاء الحساب بنجاح", "success")
            flash("مهم جدًا: افتح البوت الرسمي واتبع رابط الربط الآمن، ثم سجل دخولك من الموقع لتأكيد Telegram.", "success")

            return redirect("/dashboard")

        except Exception as e:
            log(f"❌ Register error: {e}")
            flash("❌ حصل خطأ أثناء التسجيل", "error")
            return redirect(url_for("auth.register", chat_id=chat_id, ref=ref))

    return render_template("register.html", chat_id=chat_id, ref=ref)


# ================= LOGIN =================
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
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
              audit_log("login_unknown_email", email)
              flash("❌ الإيميل غير موجود", "error")
              return redirect("/login")

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
                audit_log("login_success", email, f"chat_id_linked={bool(chat_id)}")
                log(f"✅ Login success: {email} | chat_id={chat_id}")
                conn.close()
                return redirect("/dashboard")

            conn.close()
            audit_log("login_bad_password", email)
            flash("❌ الباسورد غير صحيح", "error")
            return redirect("/login")

        except Exception as e:
         log(f"❌ Login error: {e}")
         flash("❌ حصل خطأ أثناء تسجيل الدخول", "error")
         return redirect("/login")

    return render_template("login.html")


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
        if email:
            try:
                token = create_password_reset_token(email)
                if token:
                    sent, link = send_password_reset_email(email, token)
                    if not sent:
                        flash(f"Reset link: {link}", "success")
                audit_log("password_reset_requested", email)
            except Exception as e:
                log(f"forgot_password error: {e}")
        flash("If this email exists, password reset instructions were sent.", "success")
        return redirect("/login")

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

        type_stats = {
            "spot_today": 0,
            "futures_today": 0,
            "spot_win_rate": 0,
            "futures_win_rate": 0,
            "spot_profit": 0,
            "futures_profit": 0,
        }
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
                log(f"spot_futures stats unavailable: {stats_error}")

        conn.close()

        is_linked = True if user.get("chat_id") else False
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
            dashboard_title = "Starter Dashboard"
            dashboard_subtitle = "Clean starter workspace with 5 signals per day, Telegram delivery, basic analysis, and essential tracking."

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
        }
        notifications = []
        if not is_linked:
            notifications.append("Link Telegram to receive signals and activate the full experience.")
        if plan in ("trial", "basic") and user.get("is_paid", 0) != 1:
            notifications.append("Starter includes 5 signals per day, Telegram, basic analysis, and the Starter dashboard.")
        if plan in AUTO_TRADE_PLANS and not user.get("api_key"):
            notifications.append("Elite automation needs API keys before auto trading can run.")
        if user.get("bot_active", 0) == 1:
            notifications.append("Bot is running and ready to send signals when market quality is high.")
        if not notifications:
            notifications.append("Workspace is healthy. Watch AI Score and recent activity for updates.")

        recent_activity = [
            {"label": "Dashboard loaded", "value": dashboard_title},
            {"label": "Current plan", "value": plan.upper()},
            {"label": "Telegram link", "value": "Connected" if is_linked else "Pending"},
            {"label": "Bot status", "value": "Running" if user.get("bot_active", 0) == 1 else "Stopped"},
            {"label": "Affiliate balance", "value": f"${round(affiliate_balance, 2)}"},
        ]

        return render_template(
            "dashboard.html",
            plan=plan,
            expiry=user.get("expiry"),
            profit=profit,
            trades=trades,
            bot_active=user.get("bot_active", 0),
            trade_amount=trade_amount,
            trade_type=user.get("trade_type", "futures"),
            spot_enabled=int(user.get("spot_enabled", 1) if user.get("spot_enabled") is not None else 1),
            futures_enabled=int(user.get("futures_enabled", 1) if user.get("futures_enabled") is not None else 1),
            referral_link=referral_link,
            affiliate_balance=round(affiliate_balance, 2),
            total_referrals=refs_count,
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
            recent_activity=recent_activity
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

    try:
        conn = db()
        c = conn.cursor()

        c.execute("""
            SELECT is_admin, lifetime_owner
            FROM users
            WHERE LOWER(email) = %s
            LIMIT 1
        """, (email,))
        row = c.fetchone()

        conn.close()

        if not row:
            return False

        is_admin_flag = int(row[0] or 0)
        # لازم يكون الأدمن الحقيقي من الداتابيز + يطابق ADMIN_EMAIL
        return is_admin_flag == 1 and is_admin_email(email)

    except Exception as e:
        log(f"is_current_admin error: {e}")
        return False


@admin_bp.route("/admin")
def admin_dashboard():
    if not session.get("user"):
        return redirect("/login")

    if not is_current_admin():
        return "❌ غير مصرح"

    try:
        conn = db()
        c = conn.cursor()

        def safe_scalar(query, params=(), default=0):
            try:
                c.execute(query, params)
                row = c.fetchone()
                return row[0] if row and row[0] is not None else default
            except Exception as metric_error:
                log(f"admin metric unavailable: {metric_error}")
                return default

        def safe_rows(query, params=()):
            try:
                c.execute(query, params)
                return c.fetchall()
            except Exception as metric_error:
                log(f"admin rows unavailable: {metric_error}")
                return []

        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE is_paid = 1")
        paid_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE COALESCE(chat_id, '') != ''")
        linked_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE bot_active = 1")
        active_bots = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE plan = 'basic'")
        basic_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE plan = 'pro'")
        pro_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE plan = 'vip'")
        vip_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE plan = 'pro_2y'")
        pro_2y_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE 1 = 0")
        lifetime_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE COALESCE(is_paid, 0) != 1")
        free_users = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0) FROM affiliate_commissions")
        total_affiliate_paid = float(c.fetchone()[0] or 0)

        c.execute("""
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
        """, (PLAN_PRICES["basic"], PLAN_PRICES["pro"], PLAN_PRICES["vip"], PLAN_PRICES["pro_2y"]))
        revenue = round(float(c.fetchone()[0] or 0), 2)

        c.execute("SELECT COUNT(*) FROM affiliate_withdrawals WHERE status != 'paid'")
        pending_withdrawals = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0) FROM affiliate_withdrawals WHERE status != 'paid'")
        pending_withdrawal_amount = round(float(c.fetchone()[0] or 0), 2)

        c.execute("SELECT COUNT(*) FROM affiliate_withdrawals WHERE status = 'paid'")
        paid_withdrawals = c.fetchone()[0]

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
        active_plans_count = int(basic_users or 0) + int(pro_users or 0) + int(vip_users or 0)
        ai_score = min(99, max(50, round(62 + (signal_win_rate * 0.25) + min(signals_total, 100) * 0.08 + (8 if signals_profit > 0 else 0), 2)))
        avg_signal_pnl = round(signals_profit / signals_closed, 2) if signals_closed else 0

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
        }

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

        c.execute("""
            SELECT id, code, discount_percent, active, expires_at, max_redemptions, redemption_count, created_at
            FROM coupons
            ORDER BY id DESC
            LIMIT 60
        """)
        coupons = c.fetchall()

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
            admin_overview=admin_overview
        )

    except Exception as e:
        log(f"admin_dashboard error: {e}")
        return f"❌ Error: {str(e)}"


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
    }


def is_telegram_admin_user(user):
    if not user:
        return False
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
                    register_link = f"{BASE_URL}/register?chat_id={chat_id}"

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
                    register_link = f"{BASE_URL}/register?chat_id={chat_id}"
                    send(chat_id, f"""لم يتم العثور على هذا الإيميل في الموقع.

سجل حسابك من الرابط الآمن:
{register_link}
""")
                    return "ok", 200

                login_link = f"{BASE_URL}/login?chat_id={chat_id}"
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
@payments_bp.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    data = request.get_json(silent=True) or {}
    raw_payload = json.dumps(data, ensure_ascii=False)

    try:
        signature = request.headers.get("x-nowpayments-sig", "").strip()
        ipn_secret = os.environ.get("NOWPAYMENTS_IPN_SECRET", "").strip()
        valid_signature, generated_sig = validate_nowpayments_signature(data, signature, ipn_secret)

        if not valid_signature:
            log("❌ Missing NOWPayments signature or IPN secret")
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
            log(f"❌ Invalid NOWPayments signature | recv={signature} | gen={generated_sig}")
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

