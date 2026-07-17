import os
import hmac
import hashlib
from decimal import Decimal, InvalidOperation
from flask import Blueprint, Response, render_template_string
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
    webhook_payload_fingerprint,
)
from trader_app.services.runtime import *
from trader_app.services.telegram import (
    admin_menu,
    admin_statistics_message,
    broadcast_result_message,
    command_menu,
    linked_message,
    main_menu_payload,
    plan_explainer_message,
    should_show_plans_for_text,
    subscription_message,
    telegram_plans_payload,
    user_statistics_message,
    welcome_message,
)
from trader_app.services.subscriptions import (
    VIP_ALL_FOREX_CODE,
    VIP_ALL_FOREX_DISPLAY_NAME,
    VIP_ALL_FOREX_YEARLY_CODE,
    activate_vip_all_forex,
    ensure_user_subscriptions_table,
    get_subscription_duration_days,
    get_user_active_subscriptions,
    get_user_market_capabilities,
    get_user_subscription_cards,
    is_vip_all_forex_payment_code,
)
from trader_app.services.user_entitlements import get_user_entitlements
from trader_app.services.exchanges.connection_test import test_exchange_connection
from trader_app.services.exchanges.encryption import encrypt_credential, decrypt_credential, mask_credential
from trader_app.services.exchanges.registry import (
    EXCHANGE_CAPABILITIES,
    exchange_requires_passphrase,
    get_exchange_capability,
    normalize_exchange_key,
    supported_exchange_options,
)
from trader_app.services.exchanges.risk import DEFAULT_AUTO_TRADE_SETTINGS, normalize_auto_trade_mode, sanitize_float, sanitize_int

public_bp = Blueprint("public", __name__)
health_bp = Blueprint("health", __name__)
diagnostics_bp = Blueprint("diagnostics", __name__)
auth_bp = Blueprint("auth", __name__)
dashboard_bp = Blueprint("dashboard", __name__)
payments_bp = Blueprint("payments", __name__)
admin_bp = Blueprint("admin", __name__)
telegram_bp = Blueprint("telegram", __name__)

TELEGRAM_WEBHOOK_RUNTIME_STATE = {
    "last_accepted_update_at": None,
    "last_rejected_at": None,
    "last_rejected_reason": None,
}


def mask_email_for_log(value):
    email = str(value or "").strip().lower()
    if "@" not in email:
        return "unknown" if not email else email[:2] + "***"
    name, domain = email.split("@", 1)
    return f"{name[:2]}***@{domain}"


def mask_chat_ref(value):
    raw = str(value or "").strip()
    if not raw:
        return "missing"
    return "chat_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


@public_bp.route("/")
def landing():
    return render_template("landing.html")


@public_bp.route("/robots.txt")
def robots_txt():
    base = current_base_url()
    body = "\n".join([
        "User-agent: *",
        "Allow: /$",
        "Allow: /proof",
        "Allow: /bot-check",
        "Allow: /company/privacy-policy",
        "Allow: /company/terms",
        "Allow: /company/risk-disclaimer",
        "Disallow: /dashboard",
        "Disallow: /admin",
        "Disallow: /payments",
        "Disallow: /payment",
        "Disallow: /create-payment",
        "Disallow: /manual-payment",
        "Disallow: /invoice-history",
        "Disallow: /api/",
        "Disallow: /webhook",
        "Disallow: /payment-webhook",
        f"Sitemap: {base}/sitemap.xml",
        "",
    ])
    return Response(body, mimetype="text/plain")


@public_bp.route("/sitemap.xml")
def sitemap_xml():
    base = current_base_url()
    urls = [
        "/",
        "/proof",
        "/bot-check",
        "/company/privacy-policy",
        "/company/terms",
        "/company/refund-policy",
        "/company/risk-disclaimer",
        "/company/cookie-policy",
        "/company/contact",
        "/company/faq",
    ]
    items = "".join(
        f"<url><loc>{base}{path}</loc><changefreq>weekly</changefreq><priority>{'1.0' if path == '/' else '0.7'}</priority></url>"
        for path in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>'
    return Response(xml, mimetype="application/xml")






def _adsgram_extract_token():
    payload = {}
    try:
        if request.is_json:
            payload.update(request.get_json(silent=True) or {})
    except Exception:
        pass
    try:
        payload.update(request.form.to_dict(flat=True))
    except Exception:
        pass
    try:
        payload.update(request.args.to_dict(flat=True))
    except Exception:
        pass

    token = (
        payload.get("token")
        or payload.get("state")
        or payload.get("payload")
        or payload.get("custom_id")
        or ""
    )
    user_id = payload.get("user_id") or payload.get("userId") or payload.get("telegram_user_id") or ""
    return str(token or "").strip(), str(user_id or "").strip(), payload


@public_bp.route("/adsgram/bind-user", methods=["POST"])
def adsgram_bind_user():
    from auto_sender import bind_adsgram_user_to_unlock

    payload = request.get_json(silent=True) or {}
    result = bind_adsgram_user_to_unlock(
        payload.get("token"),
        payload.get("user_id") or payload.get("userId"),
        payload.get("init_data") or payload.get("initData"),
    )
    status_code = 200 if result.get("ok") else 400
    return jsonify({"ok": bool(result.get("ok")), "reason": result.get("reason")}), status_code


@public_bp.route("/adsgram/reward", methods=["GET", "POST"])
def adsgram_reward():
    from auto_sender import process_adsgram_reward

    token, user_id, payload = _adsgram_extract_token()
    result = process_adsgram_reward(token=token, adsgram_user_id=user_id, payload_keys=list(payload.keys()))
    status_code = 200 if result.get("ok") else 400
    return jsonify({"ok": bool(result.get("ok")), "reason": result.get("reason")}), status_code


@public_bp.route("/adsgram/reward-url-info")
def adsgram_reward_url_info():
    if not session.get("user") or not is_current_admin():
        return "غير مصرح", 403
    provider = os.environ.get("REWARDED_AD_PROVIDER", "none").strip().lower()
    platform_id = os.environ.get("ADSGRAM_PLATFORM_ID", "35044").strip()
    block_id = os.environ.get("ADSGRAM_BLOCK_ID", "37291").strip()
    signature_required = os.environ.get("ADSGRAM_REQUIRE_SIGNATURE", "false").strip().lower() in {"1", "true", "yes", "on"}
    reward_url = f"{current_base_url()}/adsgram/reward?user_id=[userId]"
    return render_template(
        "adsgram_reward_info.html",
        reward_url=reward_url,
        provider=provider,
        platform_id=platform_id,
        block_id_present=bool(block_id),
        signature_required=signature_required,
    )


@public_bp.route("/unlock-signal/<token>", methods=["GET", "POST"])
def unlock_signal(token):
    from auto_sender import (
        FREE_UNLOCK_DEMO_MODE,
        REWARDED_AD_PROVIDER,
        LOCKED_SIGNAL_TTL_MINUTES,
        process_free_unlock_token,
        process_social_unlock_token,
        FREE_SOCIAL_UNLOCK_ENABLED,
        ADSGRAM_BLOCK_ID,
        ADSGRAM_PLATFORM_ID,
    )

    status = None
    adsgram_platform_approved = os.environ.get("ADSGRAM_PLATFORM_APPROVED", "false").strip().lower() in {"1", "true", "yes", "approved", "on"}
    if request.method == "POST":
        unlock_method = request.form.get("unlock_method", "").strip().lower()
        if REWARDED_AD_PROVIDER == "adsgram" and not adsgram_platform_approved and FREE_SOCIAL_UNLOCK_ENABLED and unlock_method == "social_follow":
            status = process_social_unlock_token(token)
        elif REWARDED_AD_PROVIDER == "adsgram":
            status = {"ok": False, "reason": "adsgram_callback_required"}
        elif REWARDED_AD_PROVIDER == "none" and not FREE_UNLOCK_DEMO_MODE:
            status = {"ok": False, "reason": "ads_not_configured"}
        else:
            status = process_free_unlock_token(token, demo_allowed=FREE_UNLOCK_DEMO_MODE)
    return render_template(
        "unlock_signal.html",
        token=token,
        status=status,
        rewarded_ad_provider=REWARDED_AD_PROVIDER,
        demo_mode=FREE_UNLOCK_DEMO_MODE,
        ttl_minutes=LOCKED_SIGNAL_TTL_MINUTES,
        adsgram_platform_id=ADSGRAM_PLATFORM_ID,
        adsgram_block_id=ADSGRAM_BLOCK_ID,
        adsgram_platform_approved=adsgram_platform_approved,
        social_unlock_enabled=FREE_SOCIAL_UNLOCK_ENABLED,
        reward_url=f"{current_base_url()}/adsgram/reward?user_id=[userId]",
        social_facebook_url=os.environ.get("SOCIAL_FACEBOOK_URL", "https://www.facebook.com/profile.php?id=61591117963149").strip(),
        social_instagram_url=os.environ.get("SOCIAL_INSTAGRAM_URL", "https://www.instagram.com/nexoraaitrader/?hl=en").strip(),
        social_telegram_url=os.environ.get("SOCIAL_TELEGRAM_URL", current_bot_link()).strip(),
    )


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
    from trader_app.i18n import normalize_language

    lang = (lang or "").strip().lower()
    lang = normalize_language(lang)

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
            ("Official Support Channels", [
                "WhatsApp support: 0568869313.",
                "Facebook page: https://www.facebook.com/profile.php?id=61591117963149.",
                "Use the official bot-check page before trusting any Telegram link."
            ]),
            ("Support Details", [
                "For account support, include your registered email, Telegram username if available, and a short description of the issue.",
                "For payment issues, include invoice ID, payment ID, plan, amount, and payment time."
            ]),
            ("Recommended Details", [
                "Account email, selected plan, screenshots when useful, and the exact step where the issue happened.",
                "Never send your exchange password, private keys, seed phrase, or withdrawal credentials."
            ])
        ],
        "cta": {"label": "Chat on WhatsApp", "href": "https://wa.me/971568869313"}
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
            ("Direct Support", [
                "WhatsApp support: 0568869313.",
                "Facebook page: https://www.facebook.com/profile.php?id=61591117963149.",
                "Send your registered email and a clear description of the issue so support can help faster."
            ]),
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
        "cta": {"label": "Chat on WhatsApp", "href": "https://wa.me/971568869313"}
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
    return render_template("support.html")


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
        log(f"debug_users error: {e}")
        return "Service temporarily unavailable", 503


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
        log(f"test_db error: {e}")
        return "Database service temporarily unavailable", 503


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
        log(f"test_telegram error: {e}")
        return "Service temporarily unavailable", 503


@diagnostics_bp.route("/telegram-status")
def telegram_status():
    if not admin_required():
        return "Forbidden", 403

    expected_webhook = f"{current_base_url()}/webhook"
    current_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or ""
    secret_has_whitespace = any(ch.isspace() for ch in current_secret)
    status = {
        "token_configured": bool(TOKEN),
        "incoming": {
            "secret_configured": bool(current_secret),
            "secret_valid_format": bool(current_secret) and not secret_has_whitespace and len(current_secret) <= 256,
            "route_registered": True,
            "last_accepted_update": TELEGRAM_WEBHOOK_RUNTIME_STATE.get("last_accepted_update_at"),
            "last_rejected_at": TELEGRAM_WEBHOOK_RUNTIME_STATE.get("last_rejected_at"),
            "last_rejected_reason": TELEGRAM_WEBHOOK_RUNTIME_STATE.get("last_rejected_reason"),
            "secret_matches_current_environment": (
                True
                if TELEGRAM_WEBHOOK_RUNTIME_STATE.get("last_accepted_update_at")
                and TELEGRAM_WEBHOOK_RUNTIME_STATE.get("last_rejected_reason") != "invalid_secret"
                else "unknown_until_next_valid_update"
            ),
        },
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
            "telegram_last_error_date": result.get("last_error_date"),
            "max_connections": result.get("max_connections"),
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
        log(f"TELEGRAM_CHAT_REASSIGNED old_user_id={old_user_id} new_user_id={current_user_id} chat_ref={mask_chat_ref(chat_id)}")

    c.execute("""
        UPDATE users
        SET chat_id = %s,
            bot_active = 1
        WHERE id = %s
    """, (chat_id, current_user_id))
    if email:
        log(f"LOGIN_LINKED_TELEGRAM email={mask_email_for_log(email)} chat_ref={mask_chat_ref(chat_id)}")
    return bool(old_user_id and int(old_user_id) != int(current_user_id))



def _dict_value(row, key, index=0, default=None):
    try:
        if row is None:
            return default
        if hasattr(row, "get"):
            return row.get(key, default)
        return row[index]
    except Exception:
        return default


def _safe_referral_metrics(c, conn, referrer_chat_id, referral_code):
    metrics = {
        "registered_referrals_count": 0,
        "active_registered_referrals": 0,
        "paid_referrals_count": 0,
        "affiliate_referrals_count": 0,
    }
    if not referral_code and not referrer_chat_id:
        log("REFERRAL_DASHBOARD_METRICS registered=0 active=0 paid=0")
        return metrics
    try:
        if referral_code:
            c.execute("""
                SELECT COUNT(*) AS count
                FROM users
                WHERE referred_by = %s
            """, (referral_code,))
            metrics["registered_referrals_count"] = int(_dict_value(c.fetchone(), "count", 0, 0) or 0)
    except Exception as e:
        if conn is not None:
            conn.rollback()
        log(f"REFERRAL_REGISTERED_METRIC_UNAVAILABLE error={e}")
    try:
        if referral_code:
            c.execute("""
                SELECT COUNT(*) AS count
                FROM users
                WHERE referred_by = %s
                  AND (COALESCE(bot_active, 0) = 1 OR COALESCE(is_paid, 0) = 1)
            """, (referral_code,))
            metrics["active_registered_referrals"] = int(_dict_value(c.fetchone(), "count", 0, 0) or 0)
    except Exception as e:
        if conn is not None:
            conn.rollback()
        log(f"REFERRAL_ACTIVE_METRIC_UNAVAILABLE error={e}")
    try:
        if referrer_chat_id:
            c.execute("""
                SELECT COUNT(DISTINCT referred_chat_id) AS count
                FROM affiliate_commissions
                WHERE referrer_chat_id = %s
                  AND status = 'approved'
            """, (str(referrer_chat_id),))
            metrics["paid_referrals_count"] = int(_dict_value(c.fetchone(), "count", 0, 0) or 0)
    except Exception as e:
        if conn is not None:
            conn.rollback()
        log(f"REFERRAL_PAID_METRIC_UNAVAILABLE error={e}")
    try:
        if referrer_chat_id:
            c.execute("""
                SELECT COUNT(*) AS count
                FROM affiliate_referrals
                WHERE referrer_chat_id = %s
            """, (str(referrer_chat_id),))
            metrics["affiliate_referrals_count"] = int(_dict_value(c.fetchone(), "count", 0, 0) or 0)
    except Exception as e:
        if conn is not None:
            conn.rollback()
        log(f"REFERRAL_AFFILIATE_ROWS_METRIC_UNAVAILABLE error={e}")
    log(
        "REFERRAL_DASHBOARD_METRICS "
        f"registered={metrics['registered_referrals_count']} "
        f"active={metrics['active_registered_referrals']} "
        f"paid={metrics['paid_referrals_count']}"
    )
    return metrics


def _record_registration_referral(c, conn, referrer_chat_id, referred_chat_id, referred_email):
    if not referrer_chat_id or not referred_chat_id:
        return False
    referrer_chat_id = str(referrer_chat_id).strip()
    referred_chat_id = str(referred_chat_id).strip()
    if not referrer_chat_id or not referred_chat_id:
        return False
    if referrer_chat_id == referred_chat_id:
        log(f"REFERRAL_SELF_REFERRAL_REJECTED referrer={mask_chat_ref(referrer_chat_id)} referred_email={mask_email_for_log(referred_email)}")
        return False
    try:
        c.execute("SAVEPOINT referral_register_sp")
        c.execute("""
            SELECT id
            FROM affiliate_referrals
            WHERE referrer_chat_id = %s
              AND referred_chat_id = %s
            LIMIT 1
        """, (referrer_chat_id, referred_chat_id))
        if c.fetchone():
            c.execute("RELEASE SAVEPOINT referral_register_sp")
            log(f"REFERRAL_DUPLICATE_SKIPPED referrer={mask_chat_ref(referrer_chat_id)} referred_email={mask_email_for_log(referred_email)}")
            return False
        c.execute("""
            INSERT INTO affiliate_referrals (referrer_chat_id, referred_chat_id, referred_email)
            VALUES (%s, %s, %s)
        """, (referrer_chat_id, referred_chat_id, referred_email))
        c.execute("RELEASE SAVEPOINT referral_register_sp")
        log(f"REFERRAL_REGISTERED referrer={mask_chat_ref(referrer_chat_id)} referred_email={mask_email_for_log(referred_email)}")
        return True
    except Exception as e:
        try:
            c.execute("ROLLBACK TO SAVEPOINT referral_register_sp")
            c.execute("RELEASE SAVEPOINT referral_register_sp")
        except Exception:
            pass
        log(f"REFERRAL_REGISTER_ROW_SKIPPED referrer={mask_chat_ref(referrer_chat_id)} referred_email={mask_email_for_log(referred_email)} error={e}")
        return False

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

            if len(password_raw) < 10:
                flash("❌ الباسورد لازم يكون 10 أحرف أو أكثر", "error")
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
                    log(f"REGISTER_CHAT_ID_EXISTS user_id={existing_chat_user[0]} chat_ref={mask_chat_ref(chat_id)}")
                    flash("Telegram account already linked. Please login.", "error")
                    return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            referred_by = None
            referrer_chat_id = None
            if final_ref:
                c.execute("SELECT chat_id, email FROM users WHERE referral_code = %s LIMIT 1", (final_ref,))
                ref_user = c.fetchone()
                if not ref_user:
                    log(f"REFERRAL_INVALID_CODE code={final_ref} referred_email={mask_email_for_log(email)}")
                else:
                    referrer_chat_id = str(ref_user[0] or "").strip()
                    referrer_email = str(ref_user[1] or "").strip().lower() if len(ref_user) > 1 else ""
                    if referrer_chat_id and chat_id and referrer_chat_id == str(chat_id).strip():
                        log(f"REFERRAL_SELF_REFERRAL_REJECTED referrer={mask_chat_ref(referrer_chat_id)} referred_email={mask_email_for_log(email)}")
                    elif referrer_email and referrer_email == email:
                        log(f"REFERRAL_SELF_REFERRAL_REJECTED referrer={mask_email_for_log(referrer_email)} referred_email={mask_email_for_log(email)}")
                    else:
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

            if referred_by and referrer_chat_id and chat_id:
                _record_registration_referral(c, conn, referrer_chat_id, chat_id, email)

            if chat_id:
                log(f"LOGIN_LINKED_TELEGRAM email={mask_email_for_log(email)} chat_ref={mask_chat_ref(chat_id)}")
                flash("Telegram account linked successfully.", "success")

            verification_token = create_email_verification_token(email, conn)
            conn.commit()

            if chat_id:
                ensure_user_has_referral_code(chat_id, conn)

            conn.close()

            session.clear()
            session["user"] = email
            session["is_admin"] = True if is_admin_email(email) else False
            session.permanent = True
            sent, verification_link = send_verification_email(email, verification_token)
            audit_log("register_success", email, f"chat_id_linked={bool(chat_id)} verification_email_sent={sent}")
            if not sent:
                flash(f"Verification link: {verification_link}", "success")

            log(f"NEW_USER_REGISTERED email={mask_email_for_log(email)} chat_ref={mask_chat_ref(chat_id)} ref_present={bool(final_ref)}")

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
                log(f"LOGIN_FAILED email={mask_email_for_log(email)} reason=missing_credentials")
                flash("❌ لازم تكتب الإيميل والباسورد", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
            if not re.match(email_pattern, email):
                log(f"LOGIN_FAILED email={mask_email_for_log(email)} reason=invalid_email")
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
                log(f"LOGIN_FAILED email={mask_email_for_log(email)} reason=unknown_email")
                audit_log("login_unknown_email", email)
                flash("❌ البريد الإلكتروني أو كلمة المرور غير صحيحة", "error")
                return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

            user_id = user[0]
            stored_password = str(user[2] or "").strip()

            if not check_password_hash(stored_password, password):
                conn.close()
                log(f"LOGIN_FAILED email={mask_email_for_log(email)} reason=bad_password")
                audit_log("login_bad_password", email)
                flash("❌ البريد الإلكتروني أو كلمة المرور غير صحيحة", "error")
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

            session.clear()
            session["user"] = email
            session["is_admin"] = True if is_admin_email(email) else False
            session.permanent = True
            audit_log("login_success", email, f"chat_id_linked={bool(chat_id)}")
            log(f"LOGIN_SUCCESS email={mask_email_for_log(email)} chat_ref={mask_chat_ref(chat_id)}")
            return redirect("/dashboard")

        except Exception as e:
            try:
                if conn:
                    conn.rollback()
                    conn.close()
            except Exception:
                pass
            log(f"LOGIN_FAILED email={mask_email_for_log((request.form.get('email') or '').strip().lower())} reason=exception error={e}")
            flash("❌ حصل خطأ أثناء تسجيل الدخول", "error")
            return redirect(url_for("auth.login", chat_id=chat_id, ref=ref))

    return render_template("login.html", chat_id=chat_id, ref=ref)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method != "POST":
        return redirect("/login")
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
                        log(f"PASSWORD_RESET_EMAIL_FAILED email={mask_email_for_log(email)}")
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
        if len(password) < 10:
            flash("Password must be at least 10 characters.", "error")
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
        return "❌ تعذر حفظ بيانات API. راجع السجلات باستخدام رقم الطلب.", 500


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
        enable_spot_auto_trade = os.environ.get("ENABLE_SPOT_AUTO_TRADE", "false").strip().lower() in {"1", "true", "yes", "on"}
        spot_auto_trade_enabled = 1 if (enable_spot_auto_trade and request.form.get("spot_auto_trade_enabled") == "1") else 0
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
        return "❌ تعذر حفظ الإعدادات حاليًا.", 500


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
        send(chat_id, "NEXORA ACCOUNT LINK\n\nThis Telegram link has expired. Open your Nexora dashboard and tap Connect Telegram Bot again to generate a fresh secure link.")
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
        send(chat_id, "NEXORA ACCOUNT LINK\n\nThis Telegram link has expired. Open your Nexora dashboard and tap Connect Telegram Bot again to generate a fresh secure link.")
        return True

    user_email = str(link_row[1] or "").strip().lower()
    created_at = link_row[2]
    used_at = link_row[3]
    if used_at or telegram_link_is_expired(created_at):
        log(f"TELEGRAM_LINK_FAILED reason=token_used_or_expired user_email={mask_email_for_log(user_email)} chat_id_present=True")
        send(chat_id, "NEXORA ACCOUNT LINK\n\nThis Telegram link has expired. Open your Nexora dashboard and tap Connect Telegram Bot again to generate a fresh secure link.")
        return True

    c.execute("""
        SELECT id, email, chat_id
        FROM users
        WHERE LOWER(email) = %s
        LIMIT 1
    """, (user_email,))
    target_user = c.fetchone()
    if not target_user:
        log(f"TELEGRAM_LINK_FAILED reason=user_not_found user_email={mask_email_for_log(user_email)} chat_id_present=True")
        send(chat_id, "NEXORA ACCOUNT LINK\n\nNo Nexora account was found for this secure link. Please register on the website first, then connect Telegram from your dashboard.")
        return True

    target_user_id = target_user[0]
    target_email = target_user[1]
    current_chat_id = str(target_user[2] or "").strip()

    if current_chat_id and current_chat_id != str(chat_id):
        log(f"TELEGRAM_LINK_FAILED reason=user_already_linked user_id={target_user_id} chat_id_present=True")
        send(chat_id, "NEXORA ACCOUNT LINK\n\nThis Nexora account is already linked to another Telegram account. Login on the website to manage linking safely.")
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
    send(chat_id, "NEXORA ACCOUNT LINKED\n\nTelegram is now connected to your Nexora account. Trade opportunities and account updates can be delivered here when eligible.")
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

        referral_metrics = _safe_referral_metrics(c, conn, chat_id, user.get("referral_code"))
        refs_count = referral_metrics["registered_referrals_count"]
        active_referrals = referral_metrics["active_registered_referrals"]
        paid_referrals = referral_metrics["paid_referrals_count"]
        affiliate_referrals_count = referral_metrics["affiliate_referrals_count"]

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

        referral_qr_url = ""
        if referral_link:
            referral_qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=" + quote_plus(referral_link)

        type_stats = {
            "spot_today": 0,
            "futures_today": 0,
            "spot_win_rate": None,
            "futures_win_rate": None,
            "spot_profit": None,
            "futures_profit": None,
        }
        signal_performance = {
            "total_signals": 0,
            "active_signals": 0,
            "closed_signals": 0,
            "wins": 0,
            "win_rate": None,
            "today_outcome": None,
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
            "latest_confidence": None,
            "has_closed_outcomes": False,
        }
        recent_signals = []
        performance_chart = {"labels": [], "values": []}
        signal_columns = set()
        if chat_id:
            try:
                c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", ("signal_log",))
                signal_columns = {
                    (row.get("column_name") if hasattr(row, "get") else row[0])
                    for row in (c.fetchall() or [])
                }
            except Exception as column_error:
                conn.rollback()
                log(f"dashboard signal_log column detection unavailable: {column_error}")

            pnl_expr = "COALESCE(pnl_percent, 0)" if "pnl_percent" in signal_columns else "0"
            confidence_expr = "NULL AS confidence"
            if "display_confidence" in signal_columns:
                confidence_expr = "display_confidence AS confidence"
            elif "final_score" in signal_columns:
                confidence_expr = "final_score AS confidence"
            elif "confidence" in signal_columns:
                confidence_expr = "confidence AS confidence"
            rr_expr = "risk_reward" if "risk_reward" in signal_columns else "NULL"
            strategy_expr = "strategy_name" if "strategy_name" in signal_columns else "NULL"
            timeframe_expr = "timeframe" if "timeframe" in signal_columns else "NULL"
            status_closed = "(status = 'CLOSED' OR outcome IS NOT NULL)"
            status_open = "(status IN ('SENT', 'OPEN'))"

            try:
                c.execute(f"""
                    SELECT
                        LOWER(COALESCE(signal_type, 'futures')) AS trade_type,
                        COUNT(*) FILTER (
                            WHERE sent_at >= date_trunc('day', NOW())
                        ) AS signals_today,
                        COUNT(*) FILTER (
                            WHERE {status_closed}
                        ) AS closed_count,
                        COUNT(*) FILTER (
                            WHERE {status_closed}
                              AND (COALESCE(outcome, '') IN ('TP1_HIT','TP2_HIT','TP3_HIT','TP_HIT') OR {pnl_expr} > 0)
                        ) AS wins,
                        COALESCE(SUM(CASE WHEN {status_closed} THEN {pnl_expr} ELSE 0 END), 0) AS profit
                    FROM signal_log
                    WHERE chat_id = %s
                    GROUP BY LOWER(COALESCE(signal_type, 'futures'))
                """, (chat_id,))
                for row in c.fetchall():
                    type_name = str(row["trade_type"] or "futures").lower()
                    closed_count = int(row["closed_count"] or 0)
                    wins = int(row["wins"] or 0)
                    win_rate_value = round((wins / closed_count) * 100, 2) if closed_count else None
                    profit_value = round(float(row["profit"] or 0), 2) if closed_count else None
                    if type_name == "spot":
                        type_stats["spot_today"] = int(row["signals_today"] or 0)
                        type_stats["spot_win_rate"] = win_rate_value
                        type_stats["spot_profit"] = profit_value
                    elif type_name == "futures":
                        type_stats["futures_today"] = int(row["signals_today"] or 0)
                        type_stats["futures_win_rate"] = win_rate_value
                        type_stats["futures_profit"] = profit_value
            except Exception as stats_error:
                conn.rollback()
                log(f"spot_futures real signal stats unavailable: {stats_error}")

            try:
                c.execute(f"""
                    SELECT
                        COUNT(*) AS total_signals,
                        COUNT(*) FILTER (WHERE {status_open}) AS active_signals,
                        COUNT(*) FILTER (WHERE {status_closed}) AS closed_signals,
                        COUNT(*) FILTER (
                            WHERE {status_closed}
                              AND (COALESCE(outcome, '') IN ('TP1_HIT','TP2_HIT','TP3_HIT','TP_HIT') OR {pnl_expr} > 0)
                        ) AS wins,
                        COALESCE(SUM(CASE WHEN sent_at >= date_trunc('day', NOW()) AND {status_closed} THEN {pnl_expr} ELSE 0 END), 0) AS today_outcome,
                        MAX(sent_at) AS last_scan,
                        AVG({rr_expr}) AS avg_rr,
                        AVG(CASE WHEN {confidence_expr.split(' AS ')[0]} IS NULL THEN NULL ELSE {confidence_expr.split(' AS ')[0]} END) AS avg_confidence
                    FROM signal_log
                    WHERE chat_id = %s
                """, (chat_id,))
                perf = c.fetchone() or {}
                signal_performance["total_signals"] = int(perf.get("total_signals") or 0)
                signal_performance["active_signals"] = int(perf.get("active_signals") or 0)
                signal_performance["closed_signals"] = int(perf.get("closed_signals") or 0)
                signal_performance["wins"] = int(perf.get("wins") or 0)
                signal_performance["has_closed_outcomes"] = bool(signal_performance["closed_signals"])
                signal_performance["win_rate"] = round((signal_performance["wins"] / signal_performance["closed_signals"]) * 100, 2) if signal_performance["closed_signals"] else None
                signal_performance["today_outcome"] = round(float(perf.get("today_outcome") or 0), 2) if signal_performance["closed_signals"] else None
                signal_performance["last_scan"] = perf.get("last_scan") or "No scans yet"
                signal_performance["market_status"] = "Live monitoring" if signal_performance["total_signals"] else "Waiting for qualified setup"
                signal_performance["avg_rr"] = round(float(perf.get("avg_rr")), 2) if perf.get("avg_rr") is not None else None
                signal_performance["latest_confidence"] = round(float(perf.get("avg_confidence")), 2) if perf.get("avg_confidence") is not None else None
            except Exception as perf_error:
                conn.rollback()
                log(f"dashboard real performance metrics unavailable: {perf_error}")

            try:
                c.execute(f"""
                    SELECT pair, direction, entry, tp, sl, {confidence_expr}, status, sent_at AS created_at,
                           signal_type AS trade_type, {pnl_expr} AS pnl, outcome,
                           {strategy_expr} AS strategy_name, {timeframe_expr} AS timeframe, {rr_expr} AS risk_reward
                    FROM signal_log
                    WHERE chat_id = %s
                    ORDER BY sent_at DESC
                    LIMIT 8
                """, (chat_id,))
                recent_signals = c.fetchall()
                if recent_signals:
                    latest = recent_signals[0]
                    signal_performance["best_pair"] = latest.get("pair") or "Not enough data yet"
                    signal_performance["latest_confidence"] = latest.get("confidence") if latest.get("confidence") is not None else signal_performance["latest_confidence"]
                    conf_text = latest.get("confidence") if latest.get("confidence") is not None else "N/A"
                    signal_performance["latest_reason"] = f"{latest.get('direction') or 'Signal'} setup with verified delivery confidence {conf_text}%."
                    if latest.get("strategy_name"):
                        signal_performance["latest_strategy"] = latest.get("strategy_name")
                    if latest.get("timeframe"):
                        signal_performance["best_timeframe"] = latest.get("timeframe")
            except Exception as recent_error:
                conn.rollback()
                log(f"dashboard recent real signals unavailable: {recent_error}")

            try:
                c.execute(f"""
                    SELECT COALESCE(pair, 'Unknown') AS pair,
                           COUNT(*) AS closed_count,
                           COUNT(*) FILTER (
                               WHERE COALESCE(outcome, '') IN ('TP1_HIT','TP2_HIT','TP3_HIT','TP_HIT') OR {pnl_expr} > 0
                           ) AS wins
                    FROM signal_log
                    WHERE chat_id = %s AND {status_closed}
                    GROUP BY COALESCE(pair, 'Unknown')
                    HAVING COUNT(*) > 0
                    ORDER BY (COUNT(*) FILTER (
                        WHERE COALESCE(outcome, '') IN ('TP1_HIT','TP2_HIT','TP3_HIT','TP_HIT') OR {pnl_expr} > 0
                    ))::float / COUNT(*) DESC, COUNT(*) DESC
                    LIMIT 1
                """, (chat_id,))
                best_pair_row = c.fetchone()
                if best_pair_row:
                    signal_performance["best_pair"] = best_pair_row.get("pair") or signal_performance["best_pair"]
            except Exception as best_pair_error:
                conn.rollback()
                log(f"dashboard best verified pair unavailable: {best_pair_error}")

            try:
                c.execute(f"""
                    SELECT to_char(sent_at::date, 'MM-DD') AS label,
                           COALESCE(SUM(CASE WHEN {status_closed} THEN {pnl_expr} ELSE 0 END), 0) AS pnl
                    FROM signal_log
                    WHERE chat_id = %s
                    GROUP BY sent_at::date
                    ORDER BY sent_at::date DESC
                    LIMIT 7
                """, (chat_id,))
                chart_rows = list(reversed(c.fetchall()))
                performance_chart = {
                    "labels": [row.get("label") for row in chart_rows],
                    "values": [round(float(row.get("pnl") or 0), 2) for row in chart_rows],
                }
            except Exception as chart_error:
                conn.rollback()
                log(f"dashboard verified chart unavailable: {chart_error}")



        free_earn_stats = {
            "enabled": os.environ.get("FREE_EARN_MODE", "false").strip().lower() in {"1", "true", "yes", "on"},
            "free_limit": int(os.environ.get("FREE_SIGNALS_LIFETIME", "2") or 2),
            "unlock_credits": 0,
            "locked_pending": 0,
            "successful_unlocks": 0,
        }
        if chat_id:
            try:
                c.execute("SELECT COALESCE(credits, 0) AS credits FROM free_signal_unlock_credits WHERE chat_id = %s", (str(chat_id),))
                credit_row = c.fetchone()
                if credit_row:
                    free_earn_stats["unlock_credits"] = int(credit_row.get("credits", 0) if hasattr(credit_row, "get") else credit_row[0] or 0)
            except Exception as credit_error:
                conn.rollback()
                log(f"dashboard free earn credits unavailable: {credit_error}")
            try:
                c.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE COALESCE(unlocked, 0) = 0 AND expires_at >= NOW()) AS locked_pending,
                        COUNT(*) FILTER (WHERE COALESCE(unlocked, 0) = 1) AS successful_unlocks
                    FROM free_signal_unlocks
                    WHERE chat_id = %s
                """, (str(chat_id),))
                unlock_row = c.fetchone()
                if unlock_row:
                    if hasattr(unlock_row, "get"):
                        free_earn_stats["locked_pending"] = int(unlock_row.get("locked_pending") or 0)
                        free_earn_stats["successful_unlocks"] = int(unlock_row.get("successful_unlocks") or 0)
                    else:
                        free_earn_stats["locked_pending"] = int(unlock_row[0] or 0)
                        free_earn_stats["successful_unlocks"] = int(unlock_row[1] or 0)
            except Exception as unlock_error:
                conn.rollback()
                log(f"dashboard free earn unlocks unavailable: {unlock_error}")

        log("DASHBOARD_METRICS_LOADED ok=True")
        is_linked = True if user.get("chat_id") else False
        telegram_link_token = create_telegram_link_token(c, user.get("email"))
        telegram_connect_link = f"{current_bot_link()}?start=link_{telegram_link_token}"
        if not is_linked:
            log(f"TELEGRAM_USER_NOT_LINKED email={mask_email_for_log(user.get('email'))}")
        active_subscriptions = get_user_subscription_cards(user, conn)
        market_capabilities = get_user_market_capabilities(user.get("id"), user, conn)
        conn.commit()
        conn.close()

        plan = str(user.get("plan") or "trial").strip().lower()
        legacy_profit = float(user.get("profit", 0) or 0)
        trades = int(user.get("trades", 0) or 0)
        trade_amount = float(user.get("trade_amount", 10) or 10)
        affiliate_balance = float(user.get("affiliate_balance", 0) or 0)
        verified_pnl = signal_performance["today_outcome"] if signal_performance["today_outcome"] is not None else None
        verified_win_rate = signal_performance["win_rate"]
        verified_ai_score = signal_performance["latest_confidence"]
        affiliate_net_balance = round(affiliate_balance + float(total_comm or 0) - float(total_withdrawn or 0), 2)
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

        def metric_display(value, suffix="", prefix=""):
            if value is None:
                return "N/A"
            return f"{prefix}{value}{suffix}"

        dashboard_widgets = {
            "portfolio": None,
            "portfolio_display": "N/A",
            "roi": None,
            "roi_display": "N/A",
            "win_rate": verified_win_rate,
            "win_rate_display": metric_display(verified_win_rate, "%"),
            "ai_score": verified_ai_score,
            "ai_score_numeric": float(verified_ai_score or 0),
            "ai_score_display": metric_display(verified_ai_score, "/100"),
            "balance": affiliate_net_balance,
            "balance_display": f"${affiliate_net_balance}",
            "open_trades": signal_performance["active_signals"],
            "closed_trades": signal_performance["closed_signals"],
            "spot_today": type_stats["spot_today"],
            "futures_today": type_stats["futures_today"],
            "spot_win_rate": type_stats["spot_win_rate"],
            "spot_win_rate_display": metric_display(type_stats["spot_win_rate"], "%"),
            "futures_win_rate": type_stats["futures_win_rate"],
            "futures_win_rate_display": metric_display(type_stats["futures_win_rate"], "%"),
            "spot_profit": type_stats["spot_profit"],
            "spot_profit_display": metric_display(type_stats["spot_profit"], prefix="$"),
            "futures_profit": type_stats["futures_profit"],
            "futures_profit_display": metric_display(type_stats["futures_profit"], prefix="$"),
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
            "today_outcome_display": metric_display(signal_performance["today_outcome"], prefix="$"),
            "real_win_rate": verified_win_rate,
            "real_win_rate_display": metric_display(verified_win_rate, "%"),
        }
        dashboard_chart_scores = [
            0,
            0,
            float(verified_win_rate or 0),
            float(verified_ai_score or 0),
            min(max(float(affiliate_net_balance or 0), 0), 100),
            min(signal_performance["closed_signals"], 100),
        ]
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
            profit=legacy_profit,
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
            registered_referrals_count=refs_count,
            active_registered_referrals=active_referrals,
            paid_referrals_count=paid_referrals,
            affiliate_referrals_count=affiliate_referrals_count,
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
            dashboard_chart_scores=dashboard_chart_scores,
            notifications=notifications,
            recent_activity=recent_activity,
            signal_performance=signal_performance,
            recent_signals=recent_signals,
            performance_chart=performance_chart,
            free_earn_stats=free_earn_stats,
            active_subscriptions=active_subscriptions,
            market_capabilities=market_capabilities,
            bot_link=current_bot_link(),
            telegram_connect_link=telegram_connect_link
        )

    except Exception as e:
        log(f"❌ dashboard error: {e}")
        return "❌ تعذر تحميل لوحة التحكم حاليًا.", 500


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
        support_link=os.environ.get("SUPPORT_LINK", "https://wa.me/971568869313"),
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


def _safe_table_columns(cursor, table_name):
    try:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
        """, (table_name,))
        return {
            (row.get("column_name") if hasattr(row, "get") else row[0])
            for row in (cursor.fetchall() or [])
        }
    except Exception as e:
        try:
            cursor.connection.rollback()
        except Exception:
            pass
        log(f"marketing table columns unavailable table={table_name}: {e}")
        return set()


def _safe_rows(cursor, query, params=()):
    try:
        cursor.execute(query, params)
        return cursor.fetchall() or []
    except Exception as e:
        try:
            cursor.connection.rollback()
        except Exception:
            pass
        log(f"marketing rows unavailable: {e}")
        return []


def _safe_scalar(cursor, query, params=(), default=None):
    try:
        cursor.execute(query, params)
        row = cursor.fetchone()
        if not row:
            return default
        value = row.get("value") if hasattr(row, "get") else row[0]
        return default if value is None else value
    except Exception as e:
        try:
            cursor.connection.rollback()
        except Exception:
            pass
        log(f"marketing scalar unavailable: {e}")
        return default


def _num(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _marketing_signal_select(columns):
    def expr(names, alias, default="NULL"):
        for name in names:
            if name in columns:
                return f"{name} AS {alias}"
        return f"{default} AS {alias}"

    return [
        expr(["pair", "symbol"], "pair", "''"),
        expr(["direction", "side"], "direction", "''"),
        expr(["timeframe", "tf"], "timeframe", "'N/A'"),
        expr(["entry", "entry_price"], "entry"),
        expr(["tp1", "take_profit_1", "target_1", "tp"], "tp1"),
        expr(["tp2", "take_profit_2", "target_2"], "tp2"),
        expr(["tp3", "take_profit_3", "target_3"], "tp3"),
        expr(["sl", "stop_loss"], "sl"),
        expr(["display_confidence", "final_score", "confidence"], "confidence"),
        expr(["risk_reward", "rr"], "risk_reward"),
        expr(["status", "result"], "status", "'Open'"),
        expr(["created_at", "sent_at", "timestamp"], "sent_at"),
        expr(["pnl", "profit"], "pnl"),
        expr(["strategy_name", "strategy"], "strategy", "'Not enough data yet'"),
        expr(["regime", "market_regime"], "regime", "'Not enough data yet'"),
        expr(["signal_quality_reason", "reason"], "reason", "'Not enough verified data yet.'"),
        expr(["trade_type", "mode"], "mode", "'FUTURES'"),
    ]


def _load_marketing_signals(chat_id=None, limit=50):
    rows = []
    source = "fallback"
    conn = None
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        for table_name in ("trades_log", "signal_log"):
            columns = _safe_table_columns(c, table_name)
            if not columns:
                continue
            select_sql = ", ".join(_marketing_signal_select(columns))
            where = ""
            params = []
            if chat_id and "chat_id" in columns:
                where = "WHERE chat_id = %s"
                params.append(str(chat_id))
            order_col = "created_at" if "created_at" in columns else ("sent_at" if "sent_at" in columns else None)
            order_sql = f"ORDER BY {order_col} DESC" if order_col else ""
            params.append(int(limit))
            query = f"""
                SELECT {select_sql}
                FROM {table_name}
                {where}
                {order_sql}
                LIMIT %s
            """
            rows = [dict(row) for row in _safe_rows(c, query, tuple(params))]
            if rows:
                source = table_name
                break
        conn.close()
    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        log(f"marketing signals unavailable: {e}")
    return rows, source


def _build_performance_snapshot(rows):
    total = len(rows)
    closed_rows = [
        row for row in rows
        if str(row.get("status") or "").upper() in {"CLOSED", "TP1", "TP2", "TP3", "SL"}
        or _num(row.get("pnl")) is not None
    ]
    wins = 0
    losses = 0
    positive_pnl = 0.0
    negative_pnl = 0.0
    rr_values = []
    pair_counts = {}
    strategy_counts = {}
    timeframe_counts = {}

    for row in rows:
        pair = str(row.get("pair") or "").strip()
        strategy = str(row.get("strategy") or "").strip()
        timeframe = str(row.get("timeframe") or "").strip()
        if pair:
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
        if strategy and strategy != "Not enough data yet":
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        if timeframe and timeframe != "N/A":
            timeframe_counts[timeframe] = timeframe_counts.get(timeframe, 0) + 1

        pnl = _num(row.get("pnl"))
        status = str(row.get("status") or "").upper()
        if pnl is not None:
            if pnl > 0:
                wins += 1
                positive_pnl += pnl
            elif pnl < 0:
                losses += 1
                negative_pnl += abs(pnl)
        elif status.startswith("TP"):
            wins += 1
        elif status == "SL":
            losses += 1

        rr = _num(row.get("risk_reward"))
        if rr is None:
            entry = _num(row.get("entry"))
            tp1 = _num(row.get("tp1"))
            sl = _num(row.get("sl"))
            if entry is not None and tp1 is not None and sl is not None and abs(entry - sl) > 0:
                rr = abs(tp1 - entry) / abs(entry - sl)
        if rr is not None and rr > 0:
            rr_values.append(rr)

    verified = wins + losses
    chart_labels = []
    chart_values = []
    running = 0
    for index, row in enumerate(reversed(rows[-20:]), start=1):
        pnl = _num(row.get("pnl"))
        if pnl is None:
            continue
        running += pnl
        chart_labels.append(str(index))
        chart_values.append(round(running, 2))

    def best(counter):
        if not counter:
            return "Not enough data yet"
        return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]

    return {
        "total_signals": total,
        "verified_trades": verified,
        "win_rate": round((wins / verified) * 100, 2) if verified else None,
        "average_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else None,
        "profit_factor": round(positive_pnl / negative_pnl, 2) if negative_pnl > 0 else None,
        "best_pair": best(pair_counts),
        "best_strategy": best(strategy_counts),
        "best_timeframe": best(timeframe_counts),
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "has_verified_history": verified > 0,
    }


def _marketing_admin_metrics():
    metrics = {
        "ai_health": "No recent scan data",
        "last_scan": "Not available",
        "scan_duration": "Not available",
        "coins_scanned": "Not available",
        "signals_built": 0,
        "signals_rejected": "Not available",
        "top_rejection_reasons": [],
        "telegram_delivery_rate": None,
        "auto_trade_attempts": "Not available",
        "auto_trade_skipped": "Not available",
        "recent_logs": [],
    }
    conn = None
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        metrics["signals_built"] = int(_safe_scalar(c, "SELECT COUNT(*) AS value FROM trades_log", default=0) or 0)
        last_scan = _safe_scalar(c, "SELECT MAX(created_at) AS value FROM trades_log", default=None)
        if last_scan:
            metrics["last_scan"] = last_scan
            metrics["ai_health"] = "Monitoring"
        total_users = int(_safe_scalar(c, "SELECT COUNT(*) AS value FROM users", default=0) or 0)
        linked_users = int(_safe_scalar(c, "SELECT COUNT(*) AS value FROM users WHERE COALESCE(chat_id, '') != ''", default=0) or 0)
        metrics["telegram_delivery_rate"] = round((linked_users / total_users) * 100, 2) if total_users else None

        log_columns = _safe_table_columns(c, "bot_logs")
        if log_columns:
            message_col = "message" if "message" in log_columns else ("event" if "event" in log_columns else None)
            time_col = "created_at" if "created_at" in log_columns else ("timestamp" if "timestamp" in log_columns else None)
            if message_col:
                order_sql = f"ORDER BY {time_col} DESC" if time_col else ""
                metrics["recent_logs"] = _safe_rows(c, f"""
                    SELECT {message_col} AS message {',' + time_col + ' AS created_at' if time_col else ''}
                    FROM bot_logs
                    {order_sql}
                    LIMIT 8
                """)
                metrics["signals_rejected"] = int(_safe_scalar(c, f"""
                    SELECT COUNT(*) AS value
                    FROM bot_logs
                    WHERE {message_col} ILIKE '%reject%' OR {message_col} ILIKE '%skipped%'
                """, default=0) or 0)
                metrics["auto_trade_attempts"] = int(_safe_scalar(c, f"""
                    SELECT COUNT(*) AS value
                    FROM bot_logs
                    WHERE {message_col} ILIKE '%AUTO_TRADE%' OR {message_col} ILIKE '%auto trade%'
                """, default=0) or 0)
                metrics["auto_trade_skipped"] = int(_safe_scalar(c, f"""
                    SELECT COUNT(*) AS value
                    FROM bot_logs
                    WHERE ({message_col} ILIKE '%AUTO_TRADE%' OR {message_col} ILIKE '%auto trade%')
                      AND ({message_col} ILIKE '%skip%' OR {message_col} ILIKE '%blocked%')
                """, default=0) or 0)
        conn.close()
    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        log(f"marketing admin metrics unavailable: {e}")
    return metrics


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
            "actions": [("Pay Basic", "/payments#pricing"), ("Manual Payment", "/manual-payment/basic"), ("Invoices", "/invoice-history")],
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


@dashboard_bp.route("/performance")
def performance_page():
    user = _safe_current_user_snapshot()
    if not user:
        return redirect("/login")
    chat_id = str(user.get("chat_id") or "").strip()
    rows, source = _load_marketing_signals(chat_id, 50) if chat_id else ([], "telegram_not_linked")
    performance = _build_performance_snapshot(rows)
    return render_template(
        "marketing_page.html",
        page_key="performance",
        title="Performance",
        eyebrow="Verified Trading History",
        summary="Read-only view of tracked signals and closed outcomes. If verified history is not available yet, Nexora shows an honest empty state.",
        user=user,
        source=source,
        performance=performance,
        signals=rows[:50],
        ai=None,
        auto_trade=None,
    )


@dashboard_bp.route("/ai")
def ai_analysis_page():
    user = _safe_current_user_snapshot()
    if not user:
        return redirect("/login")
    chat_id = str(user.get("chat_id") or "").strip()
    rows, source = _load_marketing_signals(chat_id, 20) if chat_id else ([], "telegram_not_linked")
    latest = rows[0] if rows else {}
    performance = _build_performance_snapshot(rows)
    ai = {
        "market_regime": latest.get("regime") or "Not enough data yet",
        "latest_summary": latest.get("reason") or "Not enough verified signal data yet.",
        "last_scan": latest.get("sent_at") or "Not available",
        "coins_scanned": "Not available",
        "signals_rejected": "Not available",
        "top_rejection_reasons": [],
        "best_setup": latest.get("pair") or "Not enough data yet",
        "engine_health": "Monitoring" if rows else "Waiting for verified scans",
        "learning_status": "Not enough closed trade history yet" if not performance["has_verified_history"] else "Using verified closed outcomes",
        "best_strategy": performance["best_strategy"],
        "best_timeframe": performance["best_timeframe"],
        "best_pair": performance["best_pair"],
        "confidence": latest.get("confidence"),
    }
    return render_template(
        "marketing_page.html",
        page_key="ai",
        title="Nexora AI Intelligence",
        eyebrow="AI Analysis",
        summary="A clean read-only snapshot of the latest available AI signal context, without inventing market analysis.",
        user=user,
        source=source,
        performance=performance,
        signals=rows[:10],
        ai=ai,
        auto_trade=None,
    )


@dashboard_bp.route("/my-plan")
def my_plan_page():
    return _dashboard_section("my-plan")


@dashboard_bp.route("/signals")
def signals_page():
    user = _safe_current_user_snapshot()
    if not user:
        return redirect("/login")
    chat_id = str(user.get("chat_id") or "").strip()
    rows, source = _load_marketing_signals(chat_id, 50) if chat_id else ([], "telegram_not_linked")
    return render_template(
        "marketing_page.html",
        page_key="signals",
        title="Live Signals",
        eyebrow="Signal Desk",
        summary="Latest tracked signals for your account. Empty means the engine has not found a qualified setup yet or Telegram is not linked.",
        user=user,
        source=source,
        performance=_build_performance_snapshot(rows),
        signals=rows[:50],
        ai=None,
        auto_trade=None,
    )


@dashboard_bp.route("/auto-trading")
def auto_trading_page():
    return _dashboard_section("auto-trading")


def _auto_trade_user():
    if not session.get("user"):
        return None
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT id, email, plan, is_admin, chat_id, spot_auto_trade_enabled,
                   futures_auto_trade_enabled, trade_type
            FROM users
            WHERE LOWER(email) = %s
            LIMIT 1
        """, (session["user"].strip().lower(),))
        user = c.fetchone()
        conn.close()
        return dict(user) if user else None
    except Exception as e:
        log(f"auto_trade_user unavailable: {e}")
        return None


def _auto_trade_plan_allowed(user):
    plan = str((user or {}).get("plan") or "trial").lower()
    return bool((user or {}).get("is_admin")) or plan in AUTO_TRADE_PLANS


def _ensure_auto_trade_settings(user):
    defaults = dict(DEFAULT_AUTO_TRADE_SETTINGS)
    if not user:
        return defaults
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            INSERT INTO auto_trade_settings (user_id, user_email)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (user["id"], user["email"]))
        c.execute("SELECT * FROM auto_trade_settings WHERE user_id = %s", (user["id"],))
        row = c.fetchone()
        conn.commit()
        conn.close()
        if row:
            settings = dict(defaults)
            settings.update(dict(row))
            settings["mode"] = normalize_auto_trade_mode(settings.get("mode"))
            return settings
    except Exception as e:
        log(f"auto_trade_settings unavailable: {e}")
    return defaults


def _load_exchange_connections(user_id):
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT *
            FROM exchange_connections
            WHERE user_id = %s
              AND deleted_at IS NULL
            ORDER BY primary_for_futures DESC, auto_trade_enabled DESC, created_at DESC
        """, (user_id,))
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        for row in rows:
            row["masked_api_key"] = mask_credential(decrypt_credential(row.get("api_key_encrypted")))
            row["capability"] = get_exchange_capability(row.get("exchange"))
        return rows
    except Exception as e:
        log(f"exchange_connections unavailable: {e}")
        return []


def _save_exchange_connection(user, form):
    exchange = normalize_exchange_key(form.get("exchange"))
    capability = get_exchange_capability(exchange)
    mode = str(form.get("mode") or "futures").strip().lower()
    mode = "spot" if mode == "spot" else "futures"
    api_key = str(form.get("api_key") or "").strip()
    api_secret = str(form.get("api_secret") or "").strip()
    passphrase = str(form.get("passphrase") or "").strip()
    label = str(form.get("label") or capability["name"]).strip()[:80]
    if not api_key or not api_secret:
        return False, "API key and secret are required."
    if exchange_requires_passphrase(exchange) and not passphrase:
        return False, f"{capability['name']} requires an API passphrase."

    spot_enabled = 1 if form.get("spot_enabled") == "1" else 0
    futures_enabled = 1 if form.get("futures_enabled", "1") == "1" else 0
    auto_trade_enabled = 1 if form.get("auto_trade_enabled") == "1" else 0
    primary_for_futures = 1 if form.get("primary_for_futures", "1") == "1" else 0
    primary_for_spot = 0

    if mode == "spot" or spot_enabled:
        spot_enabled = 0
        primary_for_spot = 0
        if auto_trade_enabled:
            auto_trade_enabled = 0
            flash("Spot Auto Trade is disabled until OCO/bracket exits are verified.", "warning")

    if auto_trade_enabled and not capability.get("auto_trade_futures"):
        auto_trade_enabled = 0
        flash(f"{capability['name']} is saved for testing/monitoring. Live execution is not enabled for this exchange yet.", "warning")

    test_result = test_exchange_connection(exchange, api_key, api_secret, passphrase, mode=mode)
    status = "connected" if test_result.get("ok") else "needs_review"
    permission_status = test_result.get("permission_status") or ("verified" if test_result.get("ok") else "unknown")

    conn = db()
    c = conn.cursor()
    if primary_for_futures:
        c.execute("""
            UPDATE exchange_connections
            SET primary_for_futures = 0
            WHERE user_id = %s AND deleted_at IS NULL
        """, (user["id"],))
    c.execute("""
        INSERT INTO exchange_connections (
            user_id, user_email, exchange, label, api_key_encrypted, api_secret_encrypted,
            passphrase_encrypted, mode, spot_enabled, futures_enabled, auto_trade_enabled,
            primary_for_spot, primary_for_futures, status, permission_status, last_tested_at,
            last_error, balance_snapshot
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
    """, (
        user["id"], user["email"], exchange, label,
        encrypt_credential(api_key), encrypt_credential(api_secret), encrypt_credential(passphrase),
        mode, spot_enabled, futures_enabled, auto_trade_enabled, primary_for_spot,
        primary_for_futures, status, permission_status, test_result.get("message"),
        str(test_result.get("balance_summary") or {}),
    ))
    conn.commit()
    conn.close()
    audit_log("exchange_connection_saved", user["email"], f"exchange={exchange};status={status};auto={auto_trade_enabled}")
    return True, test_result.get("message") or "Connection saved."


@dashboard_bp.route("/auto-trade")
def auto_trade_dashboard_page():
    user = _auto_trade_user()
    if not user:
        return redirect("/login")
    connections = _load_exchange_connections(user["id"])
    settings = _ensure_auto_trade_settings(user)
    chat_id = str(user.get("chat_id") or "").strip()
    rows, source = _load_marketing_signals(chat_id, 25) if chat_id else ([], "telegram_not_linked")
    return render_template(
        "auto_trade.html",
        user=user,
        connections=connections,
        settings=settings,
        exchanges=supported_exchange_options(),
        capabilities=EXCHANGE_CAPABILITIES,
        plan_allowed=_auto_trade_plan_allowed(user),
        source=source,
        performance=_build_performance_snapshot(rows),
        signals=rows[:10],
    )


@dashboard_bp.route("/auto-trade/test-connection", methods=["POST"])
def auto_trade_test_connection():
    user = _auto_trade_user()
    if not user:
        return jsonify({"ok": False, "message": "Please login first."}), 401
    if not _auto_trade_plan_allowed(user):
        return jsonify({"ok": False, "message": "Auto Trade is available on Elite and Pro 2 Years plans."}), 403
    exchange = normalize_exchange_key(request.form.get("exchange"))
    mode = "spot" if str(request.form.get("mode") or "").lower() == "spot" else "futures"
    result = test_exchange_connection(
        exchange,
        request.form.get("api_key"),
        request.form.get("api_secret"),
        request.form.get("passphrase"),
        mode=mode,
    )
    audit_log("exchange_connection_tested", user["email"], f"exchange={exchange};ok={bool(result.get('ok'))}")
    return jsonify(result)


@dashboard_bp.route("/auto-trade/save-connection", methods=["POST"])
def auto_trade_save_connection():
    user = _auto_trade_user()
    if not user:
        return redirect("/login")
    if not _auto_trade_plan_allowed(user):
        flash("Auto Trade is available on Elite and Pro 2 Years plans.", "error")
        return redirect("/auto-trade")
    try:
        ok, message = _save_exchange_connection(user, request.form)
        flash(message, "success" if ok else "error")
    except Exception as e:
        log(f"save_exchange_connection error: {e}")
        flash("Could not save exchange connection. Please check the credentials and try again.", "error")
    return redirect("/auto-trade")


@dashboard_bp.route("/auto-trade/settings", methods=["POST"])
def auto_trade_save_risk_settings():
    user = _auto_trade_user()
    if not user:
        return redirect("/login")
    settings = {
        "mode": normalize_auto_trade_mode(request.form.get("mode")),
        "risk_per_trade": sanitize_float(request.form.get("risk_per_trade"), 1.0, 0.1, 5.0),
        "max_daily_trades": sanitize_int(request.form.get("max_daily_trades"), 3, 1, 20),
        "max_daily_loss": sanitize_float(request.form.get("max_daily_loss"), 3.0, 0.5, 20.0),
        "max_position_size": sanitize_float(request.form.get("max_position_size"), 50.0, 5.0, 100000.0),
        "allowed_symbols": str(request.form.get("allowed_symbols") or "").upper()[:500],
    }
    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO auto_trade_settings (
                user_id, user_email, mode, risk_per_trade, max_daily_trades,
                max_daily_loss, max_position_size, allowed_symbols, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                user_email = EXCLUDED.user_email,
                mode = EXCLUDED.mode,
                risk_per_trade = EXCLUDED.risk_per_trade,
                max_daily_trades = EXCLUDED.max_daily_trades,
                max_daily_loss = EXCLUDED.max_daily_loss,
                max_position_size = EXCLUDED.max_position_size,
                allowed_symbols = EXCLUDED.allowed_symbols,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user["id"], user["email"], settings["mode"], settings["risk_per_trade"],
            settings["max_daily_trades"], settings["max_daily_loss"],
            settings["max_position_size"], settings["allowed_symbols"],
        ))
        conn.commit()
        conn.close()
        audit_log("auto_trade_settings_updated", user["email"], f"mode={settings['mode']}")
        flash("Risk settings saved.", "success")
    except Exception as e:
        log(f"auto_trade_settings save error: {e}")
        flash("Could not save risk settings.", "error")
    return redirect("/auto-trade")


@dashboard_bp.route("/auto-trade/emergency-stop", methods=["POST"])
def auto_trade_emergency_stop():
    user = _auto_trade_user()
    if not user:
        return redirect("/login")
    try:
        conn = db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO auto_trade_settings (user_id, user_email, emergency_stop)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id) DO UPDATE SET emergency_stop = 1, updated_at = CURRENT_TIMESTAMP
        """, (user["id"], user["email"]))
        c.execute("""
            UPDATE exchange_connections
            SET auto_trade_enabled = 0, status = 'paused'
            WHERE user_id = %s AND deleted_at IS NULL
        """, (user["id"],))
        c.execute("""
            UPDATE users
            SET spot_auto_trade_enabled = 0, futures_auto_trade_enabled = 0
            WHERE id = %s
        """, (user["id"],))
        conn.commit()
        conn.close()
        audit_log("auto_trade_emergency_stop", user["email"])
        flash("Emergency stop activated. Auto trade is disabled on all connected exchanges.", "success")
    except Exception as e:
        log(f"auto_trade_emergency_stop error: {e}")
        flash("Could not activate emergency stop.", "error")
    return redirect("/auto-trade")


@dashboard_bp.route("/auto-trade/connection/<int:connection_id>/<action>", methods=["POST"])
def auto_trade_connection_action(connection_id, action):
    user = _auto_trade_user()
    if not user:
        return redirect("/login")
    if action not in {"disable", "delete", "primary"}:
        return "Invalid action", 400
    try:
        conn = db()
        c = conn.cursor()
        if action == "disable":
            c.execute("""
                UPDATE exchange_connections
                SET auto_trade_enabled = 0, status = 'disabled'
                WHERE id = %s AND user_id = %s
            """, (connection_id, user["id"]))
            flash("Connection disabled.", "success")
        elif action == "delete":
            c.execute("""
                UPDATE exchange_connections
                SET auto_trade_enabled = 0, status = 'deleted', deleted_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
            """, (connection_id, user["id"]))
            flash("Connection removed.", "success")
        elif action == "primary":
            c.execute("UPDATE exchange_connections SET primary_for_futures = 0 WHERE user_id = %s", (user["id"],))
            c.execute("""
                UPDATE exchange_connections
                SET primary_for_futures = 1
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            """, (connection_id, user["id"]))
            flash("Primary futures exchange updated.", "success")
        conn.commit()
        conn.close()
        audit_log(f"auto_trade_connection_{action}", user["email"], f"connection_id={connection_id}")
    except Exception as e:
        log(f"auto_trade_connection_action error: {e}")
        flash("Could not update connection.", "error")
    return redirect("/auto-trade")


SAAS_FEATURE_NAV = [
    ("Rules Center", "/rules", "Beta"),
    ("Demo Rules", "/demo-rules", "Coming Soon"),
    ("AI Optimizations", "/ai-optimizations", "Beta"),
    ("Strategy Templates", "/templates", "Available"),
    ("Connected Exchanges", "/exchanges", "Beta"),
    ("Leverage Trading", "/leverage", "Available"),
    ("Notifications", "/notifications", "Beta"),
    ("Indicators", "/indicators", "Available"),
    ("Conditions", "/conditions", "Available"),
    ("Executions", "/executions", "Beta"),
    ("Marketplace", "/marketplace", "Coming Soon"),
    ("Academy", "/academy", "Available"),
    ("TradingView", "/tradingview", "Available"),
    ("Execution Speed", "/execution-speed", "Beta"),
    ("DeFi", "/defi", "Coming Soon"),
    ("Pricing", "/pricing", "Available"),
]


STRATEGY_TEMPLATE_CARDS = [
    {"title": "Conservative AI Signals", "status": "Available", "description": "Lower-frequency signal presentation for users who prefer strict risk controls and cleaner setups."},
    {"title": "Balanced AI Signals", "status": "Available", "description": "A balanced preset description for trend, confirmation, and risk-managed Telegram signals."},
    {"title": "Aggressive Momentum", "status": "Beta", "description": "Momentum-focused concept for users who understand higher volatility. Presentation only; engine logic is unchanged."},
    {"title": "Trend Following", "status": "Available", "description": "Explains the existing trend-confirmation style with EMA, MTF, and market structure context."},
    {"title": "Breakout Hunter", "status": "Beta", "description": "Describes confirmed breakout tracking with volume and safety filters. No user-editable automation yet."},
    {"title": "Range Protection", "status": "Available", "description": "Highlights range caution, no-trade behavior, and support/resistance validation."},
    {"title": "Smart Money Sweep", "status": "Beta", "description": "Educational template around liquidity sweep and structure confirmation already described by Nexora."},
]


PLAN_FEATURE_ROWS = [
    ("Free Trial", "2 signals", "UI preview", "0", "Available", "No", "Market data only", "Basic", "Academy preview", "Community"),
    ("Basic", "Limited monthly", "Paper rules UI", "Low", "Available", "No", "Bybit display / Binance data", "Core", "Available", "Standard"),
    ("Pro", "Higher monthly", "Paper rules UI", "Medium", "Available", "Manual tools", "Bybit display / Binance data", "Advanced", "Available", "Priority"),
    ("Elite", "Premium access", "Paper rules UI", "Higher", "Available", "Eligible", "Bybit display / Binance data", "Advanced", "Available", "VIP"),
    ("Pro 2 Years", "Highest access", "Paper rules UI", "Highest", "Available", "Eligible", "Bybit display / Binance data", "Advanced", "Available", "VIP"),
]


def _feature_badge(status):
    status = str(status or "Coming Soon").strip()
    if status not in {"Available", "Beta", "Coming Soon"}:
        return "Coming Soon"
    return status


def _product_feature_definitions(user=None):
    telegram_connected = bool(user and user.get("chat_id"))
    auto_trade_enabled = bool(user and (int(user.get("spot_auto_trade_enabled") or 0) == 1 or int(user.get("futures_auto_trade_enabled") or 0) == 1))
    return {
        "rules": {
            "title": "Rules Center",
            "eyebrow": "Coinrule-style Rules",
            "status": "Beta",
            "summary": "A presentation layer for live and demo trading rules. It does not edit the live Signal Engine yet.",
            "cards": [
                ("Live Rules", "UI only", "Coming Soon", "Live rule creation is intentionally disabled until a dedicated backend is added."),
                ("Demo Rules", "Presentation", "Beta", "Paper rule concepts are shown without sending orders."),
                ("Rule Status", "Enabled / Disabled", "Beta", "Status badges are product presentation only when no rule backend exists."),
                ("Risk Mode", "Conservative", "Available", "Risk language maps to existing Nexora safety positioning."),
            ],
            "table": {
                "headers": ["Rule", "Pair", "Timeframe", "Risk Mode", "Status"],
                "rows": [
                    ["Conservative AI Signals", "BTC/ETH majors", "15m / 1h", "Conservative", "UI only"],
                    ["Breakout Hunter", "High-liquidity pairs", "15m", "Balanced", "Coming Soon"],
                    ["Range Protection", "Major pairs", "15m", "Defensive", "UI only"],
                ],
            },
        },
        "demo-rules": {
            "title": "Demo / Paper Rules",
            "eyebrow": "Paper Trading",
            "status": "Coming Soon",
            "summary": "A safe paper-mode dashboard concept. It never executes trades and never changes the real bot.",
            "cards": [
                ("Virtual Balance", "Not connected yet", "Coming Soon", "Requires a future paper ledger backend."),
                ("Demo Signals", "Read-only preview", "Beta", "Demo concepts can be displayed without execution."),
                ("TP/SL Simulation", "Visual only", "Coming Soon", "No simulated fills are written to production tables."),
                ("Paper Mode", "Disabled", "Coming Soon", "Clearly marked as not live execution."),
            ],
        },
        "ai-optimizations": {
            "title": "AI Optimizations",
            "eyebrow": "Strategy Intelligence",
            "status": "Beta",
            "summary": "Shows verified learning and optimization context when trade history exists; otherwise uses an honest empty state.",
            "cards": [],
        },
        "templates": {
            "title": "Strategy Templates",
            "eyebrow": "SaaS Templates",
            "status": "Available",
            "summary": "Professional preset descriptions for buyers and users. Selecting templates does not modify the live Signal Engine.",
            "cards": [(item["title"], "Description only", item["status"], item["description"]) for item in STRATEGY_TEMPLATE_CARDS],
        },
        "exchanges": {
            "title": "Connected Exchanges",
            "eyebrow": "Exchange Layer",
            "status": "Beta",
            "summary": "Read-only connectivity presentation. No new exchange execution backend is added.",
            "cards": [
                ("Bybit", "Connected" if auto_trade_enabled else "Not connected yet", "Beta", "Used for eligible auto-trade users when API keys are configured."),
                ("Binance Market Data", "Market data source", "Available", "Used as a public market-data source/fallback where available."),
                ("OKX", "Placeholder", "Coming Soon", "Displayed as a future exchange option only."),
                ("KuCoin", "Market data / placeholder", "Beta", "Can be used as market-data fallback where supported; no new execution added."),
            ],
        },
        "leverage": {
            "title": "Leverage Trading",
            "eyebrow": "Futures Safety",
            "status": "Available",
            "summary": "Explains futures support and risk controls without changing leverage execution.",
            "cards": [
                ("Futures Supported", "Yes", "Available", "Futures signal presentation exists for eligible plans."),
                ("Max Leverage Display", "Config-dependent", "Beta", "Shown as product information, not an execution change."),
                ("Safety Guards", "Entry freshness + SL", "Available", "Existing safeguards are described without modifying them."),
                ("Risk Warning", "Always visible", "Available", "Crypto leverage trading is risky and not financial advice."),
            ],
        },
        "notifications": {
            "title": "Telegram + Text Notifications",
            "eyebrow": "Delivery Center",
            "status": "Beta",
            "summary": "Shows notification channels and delivery status. SMS remains Coming Soon and has no backend here.",
            "cards": [
                ("Telegram", "Connected" if telegram_connected else "Not linked", "Available", "Uses the existing Telegram linking flow."),
                ("Signal Delivery", "Active when bot is linked", "Available", "Existing Telegram delivery is unchanged."),
                ("Outcome Delivery", "Tracked when enabled", "Beta", "Uses existing signal outcome tracking when available."),
                ("Text / SMS", "Coming Soon", "Coming Soon", "No SMS backend is added."),
            ],
        },
        "indicators": {
            "title": "Advanced Indicators",
            "eyebrow": "AI Inputs",
            "status": "Available",
            "summary": "Educational overview of the analysis concepts Nexora uses or presents in its signal methodology.",
            "cards": [
                ("EMA", "Trend structure", "Available", "Used to describe trend alignment."),
                ("RSI", "Momentum quality", "Available", "Used as a momentum context indicator."),
                ("ATR", "Volatility filter", "Available", "Helps explain low/high volatility rejection."),
                ("Volume", "Confirmation", "Available", "Supports liquidity and breakout quality checks."),
                ("Support / Resistance", "Targets and risk", "Available", "Used to explain safer entries and exits."),
                ("Market Structure", "BOS / CHOCH", "Beta", "Displayed as professional analysis language."),
                ("Liquidity Sweep", "Smart money context", "Beta", "Used as an educational concept."),
                ("FVG", "Entry context", "Beta", "Presented as part of advanced methodology."),
                ("MTF Confirmation", "4H / 1H / 15M / 5M", "Available", "Explains multi-timeframe decision quality."),
            ],
        },
        "conditions": {
            "title": "Conditions & Operators",
            "eyebrow": "Rule Logic UI",
            "status": "Available",
            "summary": "Read-only condition explanations. Users cannot edit the production Signal Engine from this page.",
            "cards": [
                ("Trend Condition", "Direction quality", "Available", "Explains trend alignment requirements."),
                ("Volume Condition", "Liquidity check", "Available", "Explains why thin markets can be skipped."),
                ("Volatility Condition", "ATR band", "Available", "Explains no-trade behavior during poor volatility."),
                ("MTF Condition", "Higher timeframe agreement", "Available", "Explains why conflict blocks signals."),
                ("Risk / Reward", "Minimum quality", "Available", "Explains risk/reward filtering."),
                ("Entry Freshness", "Chase protection", "Available", "Explains stale-entry protection."),
            ],
        },
        "executions": {
            "title": "Executions",
            "eyebrow": "Delivery & Safety Logs",
            "status": "Beta",
            "summary": "Read-only execution overview using available trade/log data. It does not send Telegram messages or orders.",
            "cards": [],
        },
        "marketplace": {
            "title": "Marketplace Copy Trading",
            "eyebrow": "Future Marketplace",
            "status": "Coming Soon",
            "summary": "A polished Coming Soon page for AI templates marketplace, verified strategies, and future copy trading.",
            "cards": [
                ("AI Templates Marketplace", "Planned", "Coming Soon", "No marketplace backend is active."),
                ("Copy Top Strategies", "Planned", "Coming Soon", "No copy-trading execution is added."),
                ("Verified Performance", "Proof-first", "Coming Soon", "Future marketplace should rely on verified performance only."),
            ],
        },
        "academy": {
            "title": "Training / Academy",
            "eyebrow": "User Education",
            "status": "Available",
            "summary": "Educational hub that helps users understand Nexora, risk, Telegram setup, paper trading, and auto-trade safety.",
            "cards": [
                ("How Nexora AI Works", "Guide", "Available", "Explains AI-assisted analysis without profit guarantees."),
                ("Risk Management", "Guide", "Available", "Teaches SL, RR, position sizing, and no-trade discipline."),
                ("Reading Signals", "Guide", "Available", "Explains pair, direction, entry, targets, SL, confidence, and RR."),
                ("Paper Trading", "Guide", "Available", "Encourages testing before real execution."),
                ("Telegram Setup", "Guide", "Available", "Points users to the existing bot-link flow."),
                ("Auto Trade Safety", "Guide", "Available", "Explains API keys, Bybit readiness, and safety checks."),
            ],
        },
        "tradingview": {
            "title": "TradingView Integration",
            "eyebrow": "Chart Confirmation",
            "status": "Available",
            "summary": "Explains how the live chart supports review and confirmation. The landing TradingView widget is not duplicated here.",
            "cards": [
                ("Live Chart", "Landing terminal", "Available", "The main chart remains on the landing page."),
                ("Trend Review", "Manual confirmation", "Available", "Users can compare signals against visible market structure."),
                ("Signal Confirmation", "Education", "Available", "Encourages confirmation without changing signal delivery."),
            ],
        },
        "execution-speed": {
            "title": "Dedicated Server / Ultra Fast Execution",
            "eyebrow": "Infrastructure",
            "status": "Beta",
            "summary": "Explains scanning, queue monitoring, and safety positioning without making unverified speed guarantees.",
            "cards": [
                ("Fast Scanning", "Optimized jobs", "Beta", "Scanning speed depends on data sources and hosting conditions."),
                ("Railway Deployment", "Production hosting", "Available", "Current deployment model can be described to buyers."),
                ("Queue Monitor", "Operational view", "Beta", "Read-only queue style presentation."),
                ("Execution Safety", "Fill/deviation guards", "Available", "Safety is emphasized over chasing speed."),
            ],
        },
        "defi": {
            "title": "DeFi Trading Onchain",
            "eyebrow": "Future Onchain",
            "status": "Coming Soon",
            "summary": "A safe Coming Soon page. No onchain trading, wallet signing, or DeFi backend is added.",
            "cards": [
                ("Onchain Signals", "Planned", "Coming Soon", "No DeFi execution exists in this release."),
                ("Wallet Safety", "Research", "Coming Soon", "No wallet permissions are requested."),
                ("DEX Routing", "Planned", "Coming Soon", "No smart contract integration is added."),
            ],
        },
        "pricing": {
            "title": "Pricing",
            "eyebrow": "Plan Comparison",
            "status": "Available",
            "summary": "A SaaS-style plan feature comparison using clear Available / Beta / Coming Soon labels.",
            "cards": [],
            "pricing": True,
        },
    }


def _feature_extra_data(page_key, user):
    rows, source = _load_marketing_signals(str(user.get("chat_id") or "").strip(), 50) if user and user.get("chat_id") else ([], "not_connected")
    performance = _build_performance_snapshot(rows)
    cards = []
    table = None
    if page_key == "ai-optimizations":
        cards = [
            ("AI Optimization Credits", "Plan-based display", "Beta", "Credits are presented only; no billing or backend counter is added."),
            ("Best Strategy", performance["best_strategy"], "Available" if performance["has_verified_history"] else "Beta", "Uses tracked history when available."),
            ("Worst Strategy", "Not enough data yet", "Beta", "Requires more verified closed trades."),
            ("Learning Score", "Not enough data yet" if not performance["has_verified_history"] else f"{performance['win_rate']}%", "Beta", "Derived from verified outcomes only when present."),
            ("Last Optimization", "Not enough data yet", "Beta", "No fake optimization timestamp is shown."),
        ]
    elif page_key == "executions":
        cards = [
            ("Telegram Sends", len(rows), "Beta", "Uses tracked signals when available."),
            ("Auto Trade Attempts", "Not enough data yet", "Beta", "Shown only if logs are available."),
            ("Blocked Executions", "Not enough data yet", "Beta", "Safety rejections appear when logs expose them."),
            ("Fill Price Warnings", "Not enough data yet", "Beta", "Fill warning logs can be reviewed by admins when recorded."),
        ]
        table = {
            "headers": ["Pair", "Direction", "Status", "Confidence", "Time"],
            "rows": [[r.get("pair") or "-", r.get("direction") or "-", r.get("status") or "Tracked", r.get("confidence") or "N/A", r.get("sent_at") or "-"] for r in rows[:12]],
        }
    return cards, table, rows, source, performance


def _render_saas_feature(page_key):
    user = _safe_current_user_snapshot()
    if not user:
        return redirect("/login")
    pages = _product_feature_definitions(user)
    page = pages.get(page_key)
    if not page:
        return redirect("/rules")
    extra_cards, extra_table, signals, source, performance = _feature_extra_data(page_key, user)
    page = dict(page)
    if extra_cards:
        page["cards"] = extra_cards
    if extra_table:
        page["table"] = extra_table
    return render_template(
        "saas_feature_page.html",
        page_key=page_key,
        page=page,
        nav=SAAS_FEATURE_NAV,
        user=user,
        source=source,
        performance=performance,
        signals=signals,
        plan_rows=PLAN_FEATURE_ROWS,
    )


@dashboard_bp.route("/rules")
def rules_center_page():
    return _render_saas_feature("rules")


@dashboard_bp.route("/demo-rules")
def demo_rules_page():
    return _render_saas_feature("demo-rules")


@dashboard_bp.route("/ai-optimizations")
def ai_optimizations_page():
    return _render_saas_feature("ai-optimizations")


@dashboard_bp.route("/templates")
def strategy_templates_page():
    return _render_saas_feature("templates")


@dashboard_bp.route("/exchanges")
def connected_exchanges_page():
    return _render_saas_feature("exchanges")


@dashboard_bp.route("/leverage")
def leverage_page():
    return _render_saas_feature("leverage")


@dashboard_bp.route("/notifications")
def notifications_page():
    return _render_saas_feature("notifications")


@dashboard_bp.route("/indicators")
def indicators_page():
    return _render_saas_feature("indicators")


@dashboard_bp.route("/conditions")
def conditions_page():
    return _render_saas_feature("conditions")


@dashboard_bp.route("/executions")
def executions_page():
    return _render_saas_feature("executions")


@dashboard_bp.route("/marketplace")
def marketplace_page():
    return _render_saas_feature("marketplace")


@dashboard_bp.route("/academy")
def academy_page():
    return _render_saas_feature("academy")


@dashboard_bp.route("/tradingview")
def tradingview_page():
    return _render_saas_feature("tradingview")


@dashboard_bp.route("/execution-speed")
def execution_speed_page():
    return _render_saas_feature("execution-speed")


@dashboard_bp.route("/defi")
def defi_page():
    return _render_saas_feature("defi")


@dashboard_bp.route("/pricing")
def pricing_page():
    return _render_saas_feature("pricing")


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


@admin_bp.route("/admin/signal-supply")
def admin_signal_supply_page():
    if not session.get("user") or not is_current_admin():
        return "غير مصرح", 403
    from market_analyzer import get_signal_scan_diagnostics
    try:
        from forex_analyzer import get_forex_scan_summary, forex_auto_trade_status
    except Exception:
        get_forex_scan_summary = None
        forex_auto_trade_status = None
    diagnostics = get_signal_scan_diagnostics()
    forex_summary = get_forex_scan_summary() if get_forex_scan_summary else {}
    rejection_codes = diagnostics.get("rejections_by_code") or {}
    rows = [
        ("Market scans", diagnostics.get("scanned", 0)),
        ("Qualified A+", diagnostics.get("qualified_a_plus", 0)),
        ("Qualified A", diagnostics.get("qualified_a", 0)),
        ("Qualified B+", diagnostics.get("qualified_b_plus", 0)),
        ("Watchlist", diagnostics.get("watchlist", 0)),
        ("Rejected low volatility", diagnostics.get("rejected_low_volatility", 0)),
        ("Rejected MTF", diagnostics.get("rejected_mtf", 0)),
        ("Rejected liquidity", diagnostics.get("rejected_liquidity", 0)),
        ("Rejected fake breakout", diagnostics.get("rejected_fake_breakout", 0)),
        ("Rejected quality", diagnostics.get("rejected_quality", 0)),
        ("Rejected entry", diagnostics.get("rejected_entry", 0)),
        ("Final signals", diagnostics.get("final_signals", 0)),
    ]
    forex_rows = [
        ("Forex symbols scanned", forex_summary.get("symbols_scanned", 0)),
        ("Forex timeframes scanned", forex_summary.get("timeframes_scanned", 0)),
        ("Forex data failures", forex_summary.get("data_failures", 0)),
        ("Forex rejected volatility", forex_summary.get("rejected_volatility", 0)),
        ("Forex rejected spread", forex_summary.get("rejected_spread", 0)),
        ("Forex rejected news", forex_summary.get("rejected_news", 0)),
        ("Forex rejected quality", forex_summary.get("rejected_quality", 0)),
        ("Forex passed candidates", forex_summary.get("passed_candidates", 0)),
        ("Forex final signals", forex_summary.get("final_signals", 0)),
        ("Forex deliveries", forex_summary.get("deliveries", 0)),
    ]
    code_rows = sorted(rejection_codes.items(), key=lambda item: int(item[1] or 0), reverse=True)
    dominant = sorted(
        [(label, value) for label, value in rows if str(label).startswith("Rejected")],
        key=lambda item: int(item[1] or 0),
        reverse=True,
    )
    reason = code_rows[0][0] if code_rows and int(code_rows[0][1] or 0) > 0 else (
        dominant[0][0] if dominant and int(dominant[0][1] or 0) > 0 else "No dominant rejection reason recorded yet."
    )
    forex_status = forex_auto_trade_status() if forex_auto_trade_status else "FOREX_AUTO_TRADE_DISABLED"
    return render_template_string("""
    <!doctype html><html><head><meta charset='utf-8'><title>Nexora Signal Supply</title>
    <style>body{margin:0;background:#050b12;color:#e5eefb;font-family:Inter,Arial,sans-serif}.wrap{max-width:1180px;margin:40px auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.card{background:linear-gradient(145deg,rgba(15,27,42,.94),rgba(7,14,23,.96));border:1px solid rgba(56,189,248,.18);border-radius:18px;padding:18px;box-shadow:0 20px 60px rgba(0,0,0,.35)}span{color:#94a3b8}strong{display:block;font-size:28px;margin-top:8px}.reason{border-color:rgba(250,204,21,.35)}.section{margin-top:28px}.pill{display:inline-flex;margin:5px 6px 0 0;padding:8px 10px;border:1px solid rgba(212,175,55,.3);border-radius:999px;background:rgba(212,175,55,.08);color:#fde68a}</style>
    </head><body><main class='wrap'><h1>Nexora Signal Supply Diagnostics</h1><p>Admin-only readout for qualified opportunities, Free Earn supply, Forex supply, and rejection pressure.</p>
    <h2>Crypto Engine</h2>
    <section class='grid'>{% for label,value in rows %}<div class='card'><span>{{ label }}</span><strong>{{ value }}</strong></div>{% endfor %}</section>
    <div class='card reason' style='margin-top:18px'><span>Dominant rejection code</span><strong style='font-size:20px'>{{ reason }}</strong>{% for code,value in code_rows %}<span class='pill'>{{ code }}: {{ value }}</span>{% endfor %}</div>
    <h2 class='section'>Forex Engine</h2>
    <section class='grid'>{% for label,value in forex_rows %}<div class='card'><span>{{ label }}</span><strong>{{ value }}</strong></div>{% endfor %}</section>
    <div class='card reason' style='margin-top:18px'><span>Forex auto trade</span><strong style='font-size:20px'>{{ forex_status }}</strong></div>
    <p><a style='color:#22d3ee' href='/admin'>Back to Admin</a></p></main></body></html>
    """, rows=rows, forex_rows=forex_rows, code_rows=code_rows, reason=reason, forex_status=forex_status)


@admin_bp.route("/admin/subscriptions")
def admin_subscriptions_page():
    if not admin_required():
        return "Forbidden", 403
    rows = []
    try:
        conn = db()
        ensure_user_subscriptions_table(conn)
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT s.id, s.product_code, s.display_name, s.market_type, s.status, s.is_paid,
                   s.starts_at, s.expires_at, s.payment_provider, s.payment_reference,
                   u.email, u.chat_id
            FROM user_subscriptions s
            LEFT JOIN users u ON u.id = s.user_id
            ORDER BY s.updated_at DESC, s.id DESC
            LIMIT 100
        """)
        rows = c.fetchall() or []
        conn.close()
    except Exception as e:
        log(f"admin subscriptions unavailable: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
    return render_template_string("""
    <!doctype html><html><head><meta charset='utf-8'><title>Nexora Subscriptions</title>
    <style>body{margin:0;background:#050b12;color:#e5eefb;font-family:Inter,Arial,sans-serif}.wrap{max-width:1180px;margin:36px auto;padding:22px}.card{background:linear-gradient(145deg,rgba(15,27,42,.95),rgba(7,14,23,.98));border:1px solid rgba(212,175,55,.22);border-radius:18px;padding:18px;margin-bottom:18px;box-shadow:0 22px 70px rgba(0,0,0,.35)}input,button{border-radius:12px;border:1px solid rgba(148,163,184,.28);padding:12px;background:#08111f;color:#e5eefb}button{background:linear-gradient(135deg,#d4af37,#f7d774);color:#08111f;font-weight:800;cursor:pointer}table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid rgba(148,163,184,.12);text-align:left}th{color:#f7d774}.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:rgba(23,201,100,.14);color:#17c964}.paused{background:rgba(239,68,68,.14);color:#f87171}a{color:#38bdf8}</style>
    </head><body><main class='wrap'>
    <h1>Subscription Control</h1><p>Manual VIP ALL FOREX activation works independently from legacy crypto plans.</p>
    <section class='card'><h2>Activate / Extend VIP ALL FOREX</h2>
      <form method='post' action='/admin/subscriptions/vip-all-forex/activate' style='display:flex;gap:10px;flex-wrap:wrap;align-items:center'>
        {{ csrf_field()|safe }}
        <input name='email' placeholder='Customer email' required>
        <select name='cycle' style='border-radius:12px;border:1px solid rgba(148,163,184,.28);padding:12px;background:#08111f;color:#e5eefb'>
          <option value='monthly'>Monthly - $150 / 30 days</option>
          <option value='yearly'>Yearly - $1250 / 365 days</option>
        </select>
        <input name='days' type='number' min='1' value='' placeholder='Custom days optional'>
        <button type='submit'>Activate / Extend</button>
      </form>
    </section>
    <section class='card'><h2>Latest Subscriptions</h2>
      {% if rows %}
      <table><thead><tr><th>ID</th><th>Email</th><th>Product</th><th>Market</th><th>Status</th><th>Expires</th><th>Provider</th><th>Action</th></tr></thead><tbody>
      {% for row in rows %}
      <tr><td>{{row.id}}</td><td>{{row.email or 'N/A'}}</td><td>{{row.display_name or row.product_code}}</td><td>{{row.market_type}}</td><td><span class='badge {% if row.status != "active" %}paused{% endif %}'>{{row.status}}</span></td><td>{{row.expires_at or 'No expiry'}}</td><td>{{row.payment_provider or 'manual'}}</td><td>
        {% if row.status == 'active' %}
        <form method='post' action='/admin/subscriptions/{{row.id}}/pause'>{{ csrf_field()|safe }}<button type='submit'>Pause</button></form>
        {% else %}Paused{% endif %}
      </td></tr>
      {% endfor %}
      </tbody></table>
      {% else %}<p>No independent subscriptions yet.</p>{% endif %}
    </section>
    <p><a href='/admin'>Back to Admin</a></p></main></body></html>
    """, rows=rows)


@admin_bp.route("/admin/delivery-diagnostics")
def admin_delivery_diagnostics_page():
    if not admin_required():
        return "Forbidden", 403
    status_filter = (request.args.get("status") or "all").strip().lower()
    rows = []
    reason = ""
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT id, email, chat_id, plan, expiry, is_paid, bot_active,
                   COALESCE(spot_enabled, 1) AS spot_enabled,
                   COALESCE(futures_enabled, 1) AS futures_enabled,
                   lifetime_owner
            FROM users
            ORDER BY id DESC
            LIMIT 250
        """)
        users = c.fetchall() or []
        for user in users:
            ent = get_user_entitlements(user=dict(user), conn=conn)
            crypto = ent["crypto"]
            forex = ent["forex"]
            last_crypto = "N/A"
            last_forex = "N/A"
            try:
                c.execute("""
                    SELECT created_at
                    FROM signal_log
                    WHERE chat_id = %s AND COALESCE(product_code, '') != 'vip_all_forex'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user.get("chat_id"),))
                row = c.fetchone()
                if row:
                    last_crypto = row.get("created_at") if hasattr(row, "get") else row[0]
            except Exception:
                conn.rollback()
            try:
                c.execute("""
                    SELECT created_at
                    FROM signal_log
                    WHERE chat_id = %s AND product_code = 'vip_all_forex'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (user.get("chat_id"),))
                row = c.fetchone()
                if row:
                    last_forex = row.get("created_at") if hasattr(row, "get") else row[0]
            except Exception:
                conn.rollback()

            failure = []
            if not ent["telegram_linked"]:
                failure.append("Missing Chat")
            if not ent["telegram_active"]:
                failure.append("Blocked Bot / Paused")
            if crypto.get("expired"):
                failure.append("Crypto Expired")
            if forex.get("expired"):
                failure.append("Forex Expired")
            row = {
                "email": mask_email(user.get("email")),
                "telegram_linked": ent["telegram_linked"],
                "telegram_active": ent["telegram_active"],
                "crypto_plan": crypto.get("display_name"),
                "crypto_expiry": crypto.get("expires_at"),
                "crypto_eligible": crypto.get("can_receive_spot") or crypto.get("can_receive_futures"),
                "forex_plan": forex.get("display_name"),
                "forex_expiry": forex.get("expires_at"),
                "forex_eligible": forex.get("can_receive_signals"),
                "last_crypto": last_crypto,
                "last_forex": last_forex,
                "failure": ", ".join(failure) or "OK",
            }
            if status_filter == "missing_chat" and row["telegram_linked"]:
                continue
            if status_filter == "forex" and not row["forex_eligible"]:
                continue
            if status_filter == "crypto" and not row["crypto_eligible"]:
                continue
            rows.append(row)
        conn.close()
    except Exception as e:
        reason = str(e)
        try:
            conn.close()
        except Exception:
            pass
        log(f"admin delivery diagnostics unavailable: {e}")
    return render_template_string("""
    <!doctype html><html><head><meta charset='utf-8'><title>Nexora Delivery Diagnostics</title>
    <style>body{margin:0;background:#050b12;color:#e5eefb;font-family:Inter,Arial,sans-serif}.wrap{max-width:1280px;margin:30px auto;padding:20px}.card{background:linear-gradient(145deg,rgba(15,27,42,.95),rgba(7,14,23,.98));border:1px solid rgba(212,175,55,.22);border-radius:18px;padding:18px;box-shadow:0 22px 70px rgba(0,0,0,.35)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px;border-bottom:1px solid rgba(148,163,184,.14);text-align:left;vertical-align:top}th{color:#f7d774}.ok{color:#17c964}.bad{color:#f87171}.muted{color:#94a3b8}a{color:#38bdf8}.filters a{display:inline-block;margin:0 8px 12px 0;padding:8px 12px;border:1px solid rgba(148,163,184,.25);border-radius:999px;text-decoration:none}</style>
    </head><body><main class='wrap'><h1>Delivery Diagnostics</h1>
    <p class='muted'>Read-only view. Crypto and VIP ALL FOREX are evaluated independently from the unified entitlement service.</p>
    <div class='filters'><a href='/admin/delivery-diagnostics'>All</a><a href='/admin/delivery-diagnostics?status=crypto'>Crypto eligible</a><a href='/admin/delivery-diagnostics?status=forex'>Forex eligible</a><a href='/admin/delivery-diagnostics?status=missing_chat'>Missing chat</a><a href='/admin'>Back to Admin</a></div>
    {% if reason %}<p class='bad'>{{reason}}</p>{% endif %}
    <section class='card'><table><thead><tr><th>User</th><th>Telegram</th><th>Crypto Plan</th><th>Crypto Expiry</th><th>Crypto Eligible</th><th>Forex Plan</th><th>Forex Expiry</th><th>Forex Eligible</th><th>Last Crypto</th><th>Last Forex</th><th>Last Failure Reason</th></tr></thead><tbody>
    {% for row in rows %}
    <tr><td>{{row.email}}</td><td>{{'Linked' if row.telegram_linked else 'Missing Chat'}} / {{'Active' if row.telegram_active else 'Paused'}}</td><td>{{row.crypto_plan}}</td><td>{{row.crypto_expiry}}</td><td class='{{"ok" if row.crypto_eligible else "bad"}}'>{{row.crypto_eligible}}</td><td>{{row.forex_plan}}</td><td>{{row.forex_expiry}}</td><td class='{{"ok" if row.forex_eligible else "bad"}}'>{{row.forex_eligible}}</td><td>{{row.last_crypto}}</td><td>{{row.last_forex}}</td><td>{{row.failure}}</td></tr>
    {% endfor %}
    </tbody></table></section></main></body></html>
    """, rows=rows, reason=reason)


@admin_bp.route("/admin/subscriptions/vip-all-forex/activate", methods=["POST"])
def admin_activate_vip_all_forex():
    if not admin_required():
        return "Forbidden", 403
    email = (request.form.get("email") or "").strip().lower()
    cycle = (request.form.get("cycle") or "monthly").strip().lower()
    custom_days = (request.form.get("days") or "").strip()
    if custom_days:
        days = sanitize_int(custom_days, 30, min_value=1, max_value=3650)
        payment_label = "manual_admin_custom"
    elif cycle == "yearly":
        days = get_subscription_duration_days(VIP_ALL_FOREX_YEARLY_CODE)
        payment_label = "manual_admin_yearly"
    else:
        days = get_subscription_duration_days(VIP_ALL_FOREX_CODE)
        payment_label = "manual_admin_monthly"
    try:
        conn = db()
        c = conn.cursor()
        ensure_user_subscriptions_table(conn)
        c.execute("SELECT id FROM users WHERE LOWER(email) = %s LIMIT 1", (email,))
        user = c.fetchone()
        if not user:
            conn.close()
            flash("User not found.")
            return redirect("/admin/subscriptions")
        c.execute("""
            SELECT expires_at
            FROM user_subscriptions
            WHERE user_id = %s AND product_code = %s AND status = 'active'
            ORDER BY expires_at DESC NULLS LAST, id DESC
            LIMIT 1
        """, (user[0], VIP_ALL_FOREX_CODE))
        existing = c.fetchone()
        previous_expiry = existing[0] if existing else None
        new_expiry, _ = calculate_subscription_expiry(previous_expiry, days=days)
        activate_vip_all_forex(
            user_id=user[0],
            expires_at=new_expiry,
            payment_provider=payment_label,
            payment_reference=f"admin:{datetime.utcnow().isoformat()}",
            conn=conn,
        )
        conn.commit()
        conn.close()
        flash("VIP ALL FOREX activated.")
    except Exception as e:
        log(f"admin vip_all_forex activation error: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        flash("Activation failed.")
    return redirect("/admin/subscriptions")


@admin_bp.route("/admin/subscriptions/<int:subscription_id>/pause", methods=["POST"])
def admin_pause_subscription(subscription_id):
    if not admin_required():
        return "Forbidden", 403
    try:
        conn = db()
        ensure_user_subscriptions_table(conn)
        c = conn.cursor()
        c.execute("""
            UPDATE user_subscriptions
            SET status = 'paused', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (subscription_id,))
        conn.commit()
        conn.close()
        flash("Subscription paused.")
    except Exception as e:
        log(f"admin subscription pause error: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        flash("Pause failed.")
    return redirect("/admin/subscriptions")


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


@admin_bp.route("/admin/ai-monitor")
def admin_ai_monitor_page():
    if not session.get("user"):
        return redirect("/login")
    if not is_current_admin():
        return "Forbidden", 403

    rows, source = _load_marketing_signals(None, 50)
    performance = _build_performance_snapshot(rows)
    monitor = _marketing_admin_metrics()
    return render_template(
        "admin_ai_monitor.html",
        source=source,
        monitor=monitor,
        performance=performance,
        recent_signals=rows[:20],
    )



@admin_bp.route("/admin/sale-readiness")
def admin_sale_readiness():
    admin_guard = require_admin()
    if admin_guard:
        return admin_guard
    metrics = {
        "total_signals_sent": 0,
        "open_trades": 0,
        "closed_trades": 0,
        "wins": 0,
        "losses": 0,
        "pending_outcomes": 0,
        "free_earn_locks": 0,
        "ads_completed": 0,
        "paid_deliveries": 0,
        "latest_rejection_reasons": [],
        "latest_delivered_signals": [],
    }
    conn = None
    try:
        conn = db()
        c = conn.cursor()
        metrics["total_signals_sent"] = int(safe_scalar("SELECT COUNT(*) FROM signal_log", default=0) or 0)
        metrics["open_trades"] = int(safe_scalar("SELECT COUNT(*) FROM signal_log WHERE status IN ('SENT','OPEN')", default=0) or 0)
        metrics["closed_trades"] = int(safe_scalar("SELECT COUNT(*) FROM signal_log WHERE status = 'CLOSED' OR outcome IS NOT NULL", default=0) or 0)
        metrics["wins"] = int(safe_scalar("SELECT COUNT(*) FROM signal_log WHERE COALESCE(outcome,'') IN ('TP1_HIT','TP2_HIT','TP3_HIT','TP_HIT') OR COALESCE(pnl_percent,0) > 0", default=0) or 0)
        metrics["losses"] = int(safe_scalar("SELECT COUNT(*) FROM signal_log WHERE COALESCE(outcome,'') IN ('SL_HIT') OR COALESCE(pnl_percent,0) < 0", default=0) or 0)
        metrics["pending_outcomes"] = metrics["open_trades"]
        metrics["free_earn_locks"] = int(safe_scalar("SELECT COUNT(*) FROM free_signal_unlocks", default=0) or 0)
        metrics["ads_completed"] = int(safe_scalar("SELECT COUNT(*) FROM free_signal_unlocks WHERE COALESCE(ad_rewarded,0)=1", default=0) or 0)
        metrics["paid_deliveries"] = int(safe_scalar("SELECT COUNT(*) FROM signal_log WHERE plan <> 'trial'", default=0) or 0)
        c.execute("""
            SELECT message, created_at
            FROM bot_logs
            WHERE message ILIKE %s OR message ILIKE %s OR message ILIKE %s
            ORDER BY created_at DESC
            LIMIT 8
        """, ("%REJECT%", "%NO_TRADE%", "%BLOCKED%"))
        metrics["latest_rejection_reasons"] = c.fetchall()
        c.execute("""
            SELECT chat_id, pair, direction, plan, sent_at
            FROM signal_log
            ORDER BY sent_at DESC
            LIMIT 8
        """)
        metrics["latest_delivered_signals"] = c.fetchall()
    except Exception as exc:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        log(f"admin sale readiness metrics unavailable: {exc}")
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return render_template_string("""
    <!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Nexora Sale Readiness</title>
    <style>body{margin:0;background:#050b12;color:#e5eefb;font-family:Inter,Arial,sans-serif}.wrap{max-width:1180px;margin:36px auto;padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}.card{background:linear-gradient(145deg,rgba(15,27,42,.94),rgba(7,14,23,.96));border:1px solid rgba(56,189,248,.18);border-radius:18px;padding:18px;box-shadow:0 20px 60px rgba(0,0,0,.35)}span{color:#94a3b8}strong{display:block;font-size:30px;margin-top:8px}.table{width:100%;border-collapse:collapse;margin-top:14px}.table td,.table th{padding:10px;border-bottom:1px solid rgba(148,163,184,.16);text-align:left}.top{display:flex;justify-content:space-between;gap:12px;align-items:center}.btn{color:#03110d;background:#20d68a;border-radius:12px;padding:10px 14px;text-decoration:none;font-weight:800}</style>
    </head><body><div class='wrap'><div class='top'><div><h1>Sale Readiness Monitor</h1><p>Read-only owner diagnostics from real tracked data.</p></div><a class='btn' href='/admin'>Back to Admin</a></div>
    <div class='grid'>{% for key,value in metrics.items() if key not in ['latest_rejection_reasons','latest_delivered_signals'] %}<div class='card'><span>{{ key.replace('_',' ')|title }}</span><strong>{{ value }}</strong></div>{% endfor %}</div>
    <div class='card' style='margin-top:18px'><h2>Latest Delivered Signals</h2><table class='table'><tr><th>Chat</th><th>Pair</th><th>Direction</th><th>Plan</th><th>Sent</th></tr>{% for row in metrics.latest_delivered_signals %}<tr><td>{{ row.chat_id }}</td><td>{{ row.pair }}</td><td>{{ row.direction }}</td><td>{{ row.plan }}</td><td>{{ row.sent_at }}</td></tr>{% else %}<tr><td colspan='5'>Not enough delivered signal history yet.</td></tr>{% endfor %}</table></div>
    <div class='card' style='margin-top:18px'><h2>Latest Rejection / Block Reasons</h2><table class='table'><tr><th>Message</th><th>Time</th></tr>{% for row in metrics.latest_rejection_reasons %}<tr><td>{{ row.message }}</td><td>{{ row.created_at }}</td></tr>{% else %}<tr><td colspan='2'>No recent rejection logs available.</td></tr>{% endfor %}</table></div>
    </div></body></html>
    """, metrics=metrics)


@admin_bp.route("/admin/production-readiness")
def admin_production_readiness():
    admin_guard = require_admin()
    if admin_guard:
        return admin_guard
    try:
        from forex_analyzer import forex_readiness_status
        status = forex_readiness_status()
    except Exception as exc:
        status = {
            "ready": False,
            "checks": {},
            "provider": {"provider": "unavailable", "configured": False, "reason": str(exc)},
            "provider_health": {},
            "news": {},
            "summary": {},
            "supported_symbols": [],
            "unsupported_symbols": [],
            "last_candidate": None,
            "last_rejected_reason": str(exc),
            "auto_trade_status": "FOREX_AUTO_TRADE_DISABLED",
        }
        log(f"admin production readiness unavailable: {exc}")
    return render_template_string("""
    <!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Forex Production Readiness | Nexora Admin</title>
    <style>
    body{margin:0;background:#050b12;color:#e5eefb;font-family:Inter,Arial,sans-serif}.wrap{max-width:1180px;margin:36px auto;padding:24px}
    .top{display:flex;justify-content:space-between;gap:12px;align-items:center}.btn{color:#03110d;background:#d4af37;border-radius:12px;padding:10px 14px;text-decoration:none;font-weight:800}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.card{background:linear-gradient(145deg,rgba(15,27,42,.94),rgba(7,14,23,.96));border:1px solid rgba(212,175,55,.22);border-radius:18px;padding:18px;box-shadow:0 20px 60px rgba(0,0,0,.35)}
    .ok{color:#17c964}.bad{color:#ff6b6b}.muted{color:#94a3b8}.table{width:100%;border-collapse:collapse;margin-top:14px}.table td,.table th{padding:10px;border-bottom:1px solid rgba(148,163,184,.16);text-align:left;vertical-align:top}
    code{color:#00c2ff;word-break:break-word}
    </style></head><body><div class='wrap'>
    <div class='top'><div><h1>Forex Production Readiness</h1><p class='muted'>Read-only multi-provider monitor. Primary market data is Twelve Data, OANDA is optional, and Forex Auto Trade remains disabled.</p></div><a class='btn' href='/admin'>Back to Admin</a></div>
    <div class='grid'>
      <div class='card'><span class='muted'>Overall</span><h2 class='{{ "ok" if status.production_ready or status.shadow_ready else "bad" }}'>{{ status.readiness_level }}</h2><p>Production delivery requires fresh candles, real bid/ask spread, Trading Economics news, Telegram health, and subscription delivery checks.</p></div>
      <div class='card'><span class='muted'>Primary Provider</span><h2>Twelve Data</h2><p>Selected: <strong>{{ status.selected_provider|default(status.provider.provider) }}</strong></p><p>Configured: <strong class='{{ "ok" if status.provider.configured else "bad" }}'>{{ status.provider.configured }}</strong></p></div>
      <div class='card'><span class='muted'>Secondary Provider</span><h2>OANDA <small class='muted'>(optional)</small></h2><p>Used only when REST v20 credentials are available or as fallback/enhancement.</p></div>
      <div class='card'><span class='muted'>News</span><h2>Trading Economics</h2><p>Configured: <strong class='{{ "ok" if status.news.configured else "bad" }}'>{{ status.news.configured }}</strong></p><p>Required: {{ status.news.required }}</p></div>
      <div class='card'><span class='muted'>Candle Provider Healthy</span><h2 class='{{ "ok" if status.checks.candle_provider_healthy else "bad" }}'>{{ status.checks.candle_provider_healthy }}</h2><p>Candle provider: {{ status.selected_provider }}</p><p>Fresh candles: {{ status.checks.fresh_candles }}</p></div>
      <div class='card'><span class='muted'>Pricing Provider Healthy</span><h2 class='{{ "ok" if status.checks.pricing_provider_healthy else "bad" }}'>{{ status.checks.pricing_provider_healthy }}</h2><p>Pricing provider: {{ status.pricing_provider }}</p><p>Real Bid/Ask available: {{ status.checks.real_bid_ask_available }}</p></div>
      <div class='card'><span class='muted'>Forex Delivery Allowed</span><h2 class='{{ "ok" if status.forex_delivery_allowed else "bad" }}'>{{ status.forex_delivery_allowed }}</h2><p>{{ status.delivery_block_reason or "Allowed by current readiness settings." }}</p></div>
      <div class='card'><span class='muted'>Mode</span><h2>{{ "Shadow" if status.checks.shadow_mode_enabled else "Production" }}</h2><p>Forex production: {{ status.checks.forex_production_mode }}</p><p>Auto trade: {{ status.auto_trade_status }}</p></div>
    </div>
    <div class='card' style='margin-top:18px'><h2>Checks</h2><table class='table'>{% for key,value in status.checks.items() %}<tr><td>{{ key.replace('_',' ')|title }}</td><td class='{{ "ok" if value else "bad" }}'>{{ value }}</td></tr>{% endfor %}</table></div>
    <div class='grid' style='margin-top:18px'>
      <div class='card'><h2>Supported Forex Symbols</h2><p>{{ status.supported_symbols|join(", ") }}</p></div>
      <div class='card'><h2>Unsupported / Disabled Until Verified</h2><p>{{ status.unsupported_symbols|join(", ") }}</p><p class='muted'>No fallback fake prices are used for unsupported assets.</p></div>
    </div>
    <div class='card' style='margin-top:18px'><h2>Latest Diagnostics</h2><table class='table'>
      <tr><th>Provider Health</th><td><code>{{ status.provider_health }}</code></td></tr>
      <tr><th>Scan Summary</th><td><code>{{ status.summary }}</code></td></tr>
      <tr><th>Last Generated Forex Candidate</th><td><code>{{ status.last_candidate or "None" }}</code></td></tr>
      <tr><th>Last Rejected Reason</th><td><code>{{ status.last_rejected_reason or "None" }}</code></td></tr>
    </table></div>
    </div></body></html>
    """, status=status)


@admin_bp.route("/admin/product-features")
def admin_product_features_page():
    if not session.get("user"):
        return redirect("/login")
    if not is_current_admin():
        return "Forbidden", 403
    pages = _product_feature_definitions({})
    features = []
    for label, href, nav_status in SAAS_FEATURE_NAV:
        key = href.strip("/").replace("/", "-") or "rules"
        page = pages.get(key, {})
        features.append({
            "label": label,
            "href": href,
            "status": _feature_badge(page.get("status") or nav_status),
            "summary": page.get("summary") or "Product feature presentation page.",
        })
    return render_template("admin_product_features.html", features=features)


@admin_bp.route("/admin/auto-trade-monitor")
def admin_auto_trade_monitor_page():
    if not session.get("user"):
        return redirect("/login")
    if not is_current_admin():
        return "Forbidden", 403
    metrics = {
        "connections": 0,
        "enabled_connections": 0,
        "executed": 0,
        "skipped": 0,
        "rejected": 0,
        "errors": 0,
    }
    rows = []
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT COUNT(*) AS count FROM exchange_connections WHERE deleted_at IS NULL")
        metrics["connections"] = int((c.fetchone() or {}).get("count") or 0)
        c.execute("SELECT COUNT(*) AS count FROM exchange_connections WHERE deleted_at IS NULL AND COALESCE(auto_trade_enabled, 0) = 1")
        metrics["enabled_connections"] = int((c.fetchone() or {}).get("count") or 0)
        c.execute("""
            SELECT status, COUNT(*) AS count
            FROM execution_log
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY status
        """)
        for row in c.fetchall():
            key = str(row.get("status") or "").lower()
            if key in metrics:
                metrics[key] = int(row.get("count") or 0)
        c.execute("""
            SELECT user_email, exchange, symbol, direction, trade_type, status, reason, created_at
            FROM execution_log
            ORDER BY created_at DESC
            LIMIT 80
        """)
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
    except Exception as e:
        log(f"admin_auto_trade_monitor unavailable: {e}")
    return render_template("admin_auto_trade_monitor.html", metrics=metrics, rows=rows)


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
        return "❌ تعذر تحديث حالة البوت حاليًا.", 500


# ================= CREATE PAYMENT =================
@payments_bp.route("/create-payment", methods=["GET", "POST"])
def create_payment():
    if not session.get("user"):
        return redirect("/login")

    if request.method != "POST":
        requested_plan = (request.args.get("plan") or "").strip().lower()
        log(f"CREATE_PAYMENT_GET_BLOCKED plan={requested_plan or 'missing'}")
        return redirect("/payments")

    plan = request.form.get("plan", "basic").strip().lower()
    coupon_code = normalize_coupon_code(request.form.get("coupon", ""))

    if is_vip_all_forex_payment_code(plan) and float(PLAN_PRICES.get(plan) or 0) <= 0:
        return "VIP ALL FOREX price is not configured yet. Please contact support or use manual payment."

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

        c.execute("""
            SELECT invoice_url
            FROM payment_invoices
            WHERE chat_id = %s
              AND plan = %s
              AND amount = %s
              AND COALESCE(coupon_code, '') = COALESCE(%s, '')
              AND status IN ('created', 'waiting', 'confirming', 'pending')
              AND invoice_url IS NOT NULL
              AND created_at >= NOW() - INTERVAL '30 minutes'
            ORDER BY created_at DESC
            LIMIT 1
        """, (chat_id, plan, amount, coupon_code or None))
        recent_invoice = c.fetchone()
        if recent_invoice and recent_invoice[0]:
            conn.close()
            log(f"NOWPAYMENTS_REUSE_PENDING_INVOICE plan={plan} chat_id_present=True")
            return redirect(recent_invoice[0])

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

        log(f"NOWPAYMENTS_CREATE_RESPONSE ok={bool(data.get('invoice_url'))} status={r.status_code} invoice_id_present={bool(data.get('id') or data.get('invoice_id'))}")

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
        return "Request could not be completed", 500


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
        return "❌ Request could not be completed", 500


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
        return "❌ Request could not be completed", 500



@admin_bp.route("/admin/referral-debug")
def admin_referral_debug():
    if not session.get("user"):
        return redirect("/login")
    if not admin_required():
        return "Admin access required.", 403
    rows = []
    summary = {"registered": 0, "affiliate_rows": 0, "paid": 0}
    error = None
    conn = None
    try:
        conn = db()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("""
            SELECT
                u.email,
                u.chat_id,
                u.referral_code,
                COALESCE(reg.registered_count, 0) AS registered_count,
                COALESCE(ar.affiliate_rows, 0) AS affiliate_rows,
                COALESCE(ac.paid_count, 0) AS paid_count
            FROM users u
            LEFT JOIN (
                SELECT referred_by, COUNT(*) AS registered_count
                FROM users
                WHERE referred_by IS NOT NULL AND referred_by <> ''
                GROUP BY referred_by
            ) reg ON reg.referred_by = u.referral_code
            LEFT JOIN (
                SELECT referrer_chat_id, COUNT(*) AS affiliate_rows
                FROM affiliate_referrals
                GROUP BY referrer_chat_id
            ) ar ON ar.referrer_chat_id = u.chat_id
            LEFT JOIN (
                SELECT referrer_chat_id, COUNT(DISTINCT referred_chat_id) AS paid_count
                FROM affiliate_commissions
                WHERE status = 'approved'
                GROUP BY referrer_chat_id
            ) ac ON ac.referrer_chat_id = u.chat_id
            WHERE u.referral_code IS NOT NULL AND u.referral_code <> ''
            ORDER BY registered_count DESC, affiliate_rows DESC, paid_count DESC
            LIMIT 200
        """)
        rows = c.fetchall() or []
        summary["registered"] = sum(int(r.get("registered_count") or 0) for r in rows)
        summary["affiliate_rows"] = sum(int(r.get("affiliate_rows") or 0) for r in rows)
        summary["paid"] = sum(int(r.get("paid_count") or 0) for r in rows)
    except Exception as e:
        error = str(e)
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return render_template_string("""
<!doctype html>
<html><head><meta charset="utf-8"><title>Referral Debug</title>
<style>
body{font-family:Arial,sans-serif;background:#07111f;color:#e5eefb;margin:0;padding:24px}
.card{background:rgba(15,23,42,.92);border:1px solid rgba(56,189,248,.25);border-radius:16px;padding:18px;margin-bottom:18px}
table{width:100%;border-collapse:collapse;background:rgba(2,6,23,.5);border-radius:12px;overflow:hidden}
th,td{padding:10px;border-bottom:1px solid rgba(148,163,184,.18);text-align:left}
th{color:#38bdf8}.warn{color:#fbbf24}.ok{color:#22c55e}
a{color:#38bdf8}
</style></head><body>
<div class="card">
<h1>Referral Debug</h1>
<p>Registered referrals are counted from <code>users.referred_by</code>. Paid referrals are counted from approved <code>affiliate_commissions</code>.</p>
<p><a href="/admin">Back to Admin</a></p>
{% if error %}<p class="warn">Error: {{ error }}</p>{% endif %}
</div>
<div class="card">
<strong>Summary:</strong>
Registered: {{ summary.registered }} |
Affiliate rows: {{ summary.affiliate_rows }} |
Paid: {{ summary.paid }}
</div>
<table>
<thead><tr><th>Email</th><th>Referral Code</th><th>Registered</th><th>Affiliate Rows</th><th>Paid</th><th>Difference</th></tr></thead>
<tbody>
{% for row in rows %}
{% set diff = (row.registered_count or 0) - (row.affiliate_rows or 0) %}
<tr>
<td>{{ row.email }}</td>
<td>{{ row.referral_code }}</td>
<td>{{ row.registered_count }}</td>
<td>{{ row.affiliate_rows }}</td>
<td>{{ row.paid_count }}</td>
<td class="{{ 'warn' if diff else 'ok' }}">{{ diff }}{% if diff %} registered-only{% else %} aligned{% endif %}</td>
</tr>
{% endfor %}
</tbody>
</table>
</body></html>
""", rows=rows, summary=summary, error=error)

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

        def admin_table_columns(table_name):
            try:
                c.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                """, (table_name,))
                return {(row[0] if not hasattr(row, "get") else row.get("column_name")) for row in (c.fetchall() or [])}
            except Exception as column_error:
                db_rollback()
                log(f"admin columns unavailable table={table_name}: {column_error}")
                return set()

        def admin_recent_signal_rows(limit=8):
            columns = admin_table_columns("trades_log")
            required = {"chat_id", "pair", "direction", "entry", "tp", "sl", "status", "created_at"}
            if not columns or not required.issubset(columns):
                return []
            if "display_confidence" in columns:
                confidence_expr = "display_confidence AS confidence"
            elif "final_score" in columns:
                confidence_expr = "final_score AS confidence"
                log("ADMIN_CONFIDENCE_FALLBACK_USED source=trades_log.final_score")
            elif "confidence" in columns:
                confidence_expr = "confidence AS confidence"
            else:
                confidence_expr = "NULL AS confidence"
                log("ADMIN_CONFIDENCE_FALLBACK_USED source=trades_log.none")
            return safe_rows(f"""
                SELECT chat_id, pair, direction, entry, tp, sl, {confidence_expr}, status, created_at
                FROM trades_log
                ORDER BY created_at DESC
                LIMIT %s
            """, (int(limit),))

        total_users = int(safe_scalar("SELECT COUNT(*) FROM users", default=0) or 0)
        paid_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE is_paid = 1", default=0) or 0)
        linked_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE COALESCE(chat_id, '') != ''", default=0) or 0)
        active_bots = int(safe_scalar("SELECT COUNT(*) FROM users WHERE bot_active = 1", default=0) or 0)

        basic_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'basic'", default=0) or 0)
        pro_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'pro'", default=0) or 0)
        vip_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'vip'", default=0) or 0)
        pro_2y_users = int(safe_scalar("SELECT COUNT(*) FROM users WHERE plan = 'pro_2y'", default=0) or 0)
        vip_all_forex_users = int(safe_scalar("""
            SELECT COUNT(*)
            FROM user_subscriptions
            WHERE product_code = 'vip_all_forex'
              AND status = 'active'
              AND COALESCE(is_paid, 0) = 1
              AND (expires_at IS NULL OR expires_at >= NOW())
        """, default=0) or 0)
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
        active_plans_count = basic_users + pro_users + vip_users + pro_2y_users + vip_all_forex_users
        ai_score = min(99, max(50, round(62 + (signal_win_rate * 0.25) + min(signals_total, 100) * 0.08 + (8 if signals_profit > 0 else 0), 2)))
        avg_signal_pnl = round(signals_profit / signals_closed, 2) if signals_closed else 0
        telegram_delivery_rate = round((linked_users / total_users) * 100, 2) if total_users else 0
        queue_monitor = payments_pending + pending_withdrawals + signals_open

        free_earn_locked = int(safe_scalar("SELECT COUNT(*) FROM free_signal_unlocks WHERE COALESCE(unlocked, 0) = 0 AND expires_at >= NOW()", default=0) or 0)
        free_earn_unlocks = int(safe_scalar("SELECT COUNT(*) FROM free_signal_unlocks WHERE COALESCE(unlocked, 0) = 1", default=0) or 0)
        free_earn_credits = int(safe_scalar("SELECT COALESCE(SUM(credits), 0) FROM free_signal_unlock_credits", default=0) or 0)
        free_earn_users = int(safe_scalar("SELECT COUNT(DISTINCT chat_id) FROM free_signal_unlocks", default=0) or 0)
        adsgram_rewards = int(safe_scalar("SELECT COUNT(*) FROM free_signal_unlocks WHERE reward_provider = 'adsgram'", default=0) or 0)
        adsgram_rewarded = int(safe_scalar("SELECT COUNT(*) FROM free_signal_unlocks WHERE reward_provider = 'adsgram' AND COALESCE(ad_rewarded, 0) = 1", default=0) or 0)


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
            "free_earn_locked": free_earn_locked,
            "free_earn_unlocks": free_earn_unlocks,
            "free_earn_credits": free_earn_credits,
            "free_earn_users": free_earn_users,
            "adsgram_rewards": adsgram_rewards,
            "adsgram_rewarded": adsgram_rewarded,
            "vip_all_forex_users": vip_all_forex_users,
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
        recent_admin_signals = admin_recent_signal_rows(limit=8)
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
            vip_all_forex_users=vip_all_forex_users,
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
            vip_all_forex_users=0,
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
        return "❌ Request could not be completed", 500


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
        return "❌ Request could not be completed", 500


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
        return "❌ Request could not be completed", 500


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
        return "❌ Request could not be completed", 500


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
        return "❌ Request could not be completed", 500


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


def build_telegram_user_stats(c, user, chat_id, conn=None):
    referral_code = user.get("referral_code")
    referral_metrics = _safe_referral_metrics(c, conn, chat_id, referral_code)
    stats = {
        "trades": int(user.get("trades") or 0),
        "profit": round(float(user.get("profit") or 0), 2),
        "affiliate_balance": round(float(user.get("affiliate_balance") or 0), 2),
        "total_referrals": referral_metrics["registered_referrals_count"],
        "registered_referrals": referral_metrics["registered_referrals_count"],
        "active_referrals": referral_metrics["active_registered_referrals"],
        "paid_referrals": referral_metrics["paid_referrals_count"],
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
    expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET") or ""
    allow_insecure_dev = (os.environ.get("TELEGRAM_WEBHOOK_ALLOW_INSECURE_DEV") or "").strip().lower() in {"1", "true", "yes"}
    if not expected_secret and not allow_insecure_dev:
        TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_at"] = datetime.utcnow().isoformat()
        TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_reason"] = "missing_secret"
        log("TELEGRAM_WEBHOOK_REJECTED reason=missing_secret")
        return "webhook unavailable", 503
    if expected_secret and (len(expected_secret) > 256 or any(ch.isspace() for ch in expected_secret)):
        TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_at"] = datetime.utcnow().isoformat()
        TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_reason"] = "invalid_secret_config"
        log("TELEGRAM_WEBHOOK_REJECTED reason=invalid_secret_config")
        return "webhook unavailable", 503
    if expected_secret:
        received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""
        if not received_secret or not hmac.compare_digest(received_secret, expected_secret):
            TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_at"] = datetime.utcnow().isoformat()
            TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_reason"] = "invalid_secret"
            log("TELEGRAM_WEBHOOK_REJECTED reason=invalid_secret")
            return "forbidden", 403
    try:
        data = request.get_json(silent=True) or {}

        message = data.get("message", {}) or {}
        callback_query = data.get("callback_query", {}) or {}
        callback_message = (callback_query.get("message") or {}) if callback_query else {}
        chat = message.get("chat", {}) or callback_message.get("chat", {}) or {}
        text = (message.get("text") or "").strip()
        callback_data = (callback_query.get("data") or "").strip()
        tg_from = message.get("from") or callback_query.get("from") or {}
        telegram_lang = "ar" if str(tg_from.get("language_code") or "").lower().startswith("ar") else "en"
        chat_id = str(chat.get("id") or "").strip()

        if not chat_id:
            log("TELEGRAM_WEBHOOK_NO_CHAT update_type=message")
            return "ok", 200

        command = text.split(maxsplit=1)[0].lower() if text else ""
        update_type = "callback_query" if callback_query else ("message" if message else "unknown")
        TELEGRAM_WEBHOOK_RUNTIME_STATE["last_accepted_update_at"] = datetime.utcnow().isoformat()
        TELEGRAM_WEBHOOK_RUNTIME_STATE["last_rejected_reason"] = None
        log(f"TELEGRAM_UPDATE_ACCEPTED chat_ref={mask_chat_ref(chat_id)} update_type={update_type}")

        if callback_query:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": callback_query.get("id")},
                    timeout=5,
                )
            except Exception as callback_ack_error:
                log(f"telegram callback ack skipped: {callback_ack_error}")

        if callback_data.startswith("menu:") or callback_data.startswith("plans:"):
            try:
                view = callback_data.split(":", 1)[1] or "all"
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                if view == "home":
                    text_out, markup = main_menu_payload(tg_user, chat_id=chat_id, lang=telegram_lang)
                else:
                    text_out, markup = telegram_plans_payload(tg_user, chat_id=chat_id, lang=telegram_lang, view=view)
                send(chat_id, text_out, reply_markup=markup)
                conn.close()
            except Exception as e:
                log(f"telegram menu callback error: {e}")
                send(chat_id, "NEXORA\n\nMenu is temporarily unavailable. Please open your dashboard.")
            return "ok", 200


        if command in ["/help", "/commands"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                text_out, markup = telegram_plans_payload(tg_user, chat_id=chat_id, lang=telegram_lang, view="help")
                send(chat_id, text_out, reply_markup=markup)
                conn.close()
            except Exception as e:
                log(f"telegram help error: {e}")
                send(chat_id, command_menu(False))
            return "ok", 200

        if command in ["/plans", "/pricing", "/subscribe"] or (command not in ["/subscription", "/status", "/check_subscription"] and should_show_plans_for_text(text)):
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                text_out, markup = telegram_plans_payload(tg_user, chat_id=chat_id, lang=telegram_lang, view="all")
                send(chat_id, text_out, reply_markup=markup)
                conn.close()
            except Exception as e:
                log(f"telegram plans error: {e}")
                send(chat_id, "NEXORA PLANS\n\nPlan information is temporarily unavailable. Please open your dashboard or pricing page.")
            return "ok", 200

        if command in ["/subscription", "/status", "/check_subscription"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                text_out, markup = telegram_plans_payload(tg_user, chat_id=chat_id, lang=telegram_lang, view="account")
                send(chat_id, text_out, reply_markup=markup)
                conn.close()
            except Exception as e:
                log(f"telegram subscription error: {e}")
                send(chat_id, "NEXORA STATUS\n\nSubscription status is temporarily unavailable. Please try again shortly or open your dashboard.")
            return "ok", 200

        if command in ["/stats", "/statistics"]:
            try:
                conn = db()
                c = conn.cursor()
                tg_user = get_telegram_user(c, chat_id)
                if not tg_user:
                    send(chat_id, "لا يوجد حساب مربوط بهذا Telegram. استخدم /start أولاً.")
                else:
                    stats = build_telegram_user_stats(c, tg_user, chat_id, conn)
                    send(chat_id, user_statistics_message(stats))
                conn.close()
            except Exception as e:
                log(f"telegram stats error: {e}")
                send(chat_id, "NEXORA STATS\n\nAccount statistics are temporarily unavailable. Please try again shortly.")
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
                    log(f"TELEGRAM_LINK_TOKEN_ERROR chat_ref={mask_chat_ref(chat_id)} error={link_err}")
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

                    user_payload = {
                        "id": user_id,
                        "email": email,
                        "chat_id": chat_id,
                        "plan": current_plan,
                        "expiry": expiry,
                        "is_paid": 1 if is_paid else 0,
                        "trades": trades,
                        "bot_active": 1,
                        "spot_enabled": 1,
                        "futures_enabled": 1,
                        "lifetime_owner": lifetime_owner,
                        "is_admin": is_admin_flag,
                    }
                    menu_text, menu_markup = main_menu_payload(user_payload, chat_id=chat_id, lang=telegram_lang)
                    send(chat_id, menu_text, reply_markup=menu_markup)

                else:
                    register_link = f"{current_base_url()}/register?chat_id={chat_id}"

                    menu_text, menu_markup = main_menu_payload(None, chat_id=chat_id, lang=telegram_lang)
                    send(chat_id, menu_text, reply_markup=menu_markup)

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
                    send(chat_id, f"""This email was not found on the website.

Create your account from the secure link:
{register_link}
""")
                    return "ok", 200

                login_link = f"{current_base_url()}/login?chat_id={chat_id}"
                send(chat_id, f"""For account safety, Telegram is not linked by typing an email only.

Open the secure link and login with your password to link Telegram:
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

                if not referral_code:
                    referral_code = ensure_user_has_referral_code(chat_id, conn)

                metrics = _safe_referral_metrics(c, conn, chat_id, referral_code)
                registered = metrics["registered_referrals_count"]
                active = metrics["active_registered_referrals"]
                paid = metrics["paid_referrals_count"]
                aff_link = telegram_referral_link(referral_code)

                log(
                    f"AFFILIATE_STATS_VIEW chat_ref={mask_chat_ref(chat_id)} "
                    f"registered={registered} active={active} paid={paid} balance={round(balance, 2)}"
                )

                send(chat_id, f"""━━━━━━━━━━━━━━━━━━
🤝 NEXORA AFFILIATE CENTER
━━━━━━━━━━━━━━━━━━

🔗 Your referral link:
{aff_link}

📊 Referral Overview
👥 Registered referrals: {registered}
🟢 Active referrals: {active}
💎 Paid referrals: {paid}
💰 Commission balance: ${round(balance, 2)}

Commissions are credited only when an eligible referred user completes a qualifying payment.

💳 Withdrawals are managed from your dashboard.
Minimum withdrawal: $25
Maximum withdrawal: $300

⚠️ Referral registrations and paid commissions are tracked separately.""")

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
    value = os.environ.get("NOWPAYMENTS_IPN_SECRET", "").strip()
    return value, "NOWPAYMENTS_IPN_SECRET" if value else None


def safe_payment_payload_for_audit(data):
    data = data or {}
    safe_keys = (
        "payment_id",
        "invoice_id",
        "id",
        "order_id",
        "order_description",
        "payment_status",
        "price_amount",
        "price_currency",
        "pay_currency",
        "actually_paid",
    )
    return json.dumps({key: data.get(key) for key in safe_keys if key in data}, ensure_ascii=False, sort_keys=True)


@payments_bp.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    raw_body = request.get_data(cache=True) or b""
    data = request.get_json(silent=True) or {}
    raw_payload = safe_payment_payload_for_audit(data)

    try:
        signature = request.headers.get("x-nowpayments-sig", "").strip()
        ipn_secret, ipn_env_name = get_nowpayments_ipn_secret()
        canonical_hash, canonical_len = webhook_payload_fingerprint(data)
        log(
            "NOWPAYMENTS_IPN_CHECK "
            f"signature_present={bool(signature)} "
            f"signature_len={len(signature)} "
            f"ipn_secret_configured={bool(ipn_secret)} "
            f"ipn_secret_len={len(ipn_secret)} "
            f"env={ipn_env_name or 'missing'} "
            f"json_valid={bool(data)} "
            f"raw_len={len(raw_body)} "
            f"canonical_sha256={canonical_hash} "
            f"canonical_len={canonical_len}"
        )
        valid_signature, generated_sig = validate_nowpayments_signature(data, signature, ipn_secret)

        if not valid_signature:
            if not signature:
                log("NOWPAYMENTS_IPN_REJECTED reason=missing_signature ipn_secret_configured=%s" % bool(ipn_secret))
            elif not ipn_secret:
                log("NOWPAYMENTS_IPN_REJECTED reason=missing_ipn_secret supported_env=NOWPAYMENTS_IPN_SECRET")
            else:
                log(f"NOWPAYMENTS_IPN_REJECTED reason=invalid_signature ipn_secret_configured=True signature_len={len(signature)} canonical_sha256={canonical_hash}")
            try:
                conn = db()
                c = conn.cursor()
                c.execute("""
                    INSERT INTO failed_payments (payment_id, invoice_id, order_id, plan, payment_status, reason, raw_payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(data.get("payment_id") or ""),
                    str(data.get("invoice_id") or ""),
                    "",
                    str(data.get("order_description") or ""),
                    str(data.get("payment_status") or "signature_error"),
                    "invalid_signature",
                    safe_payment_payload_for_audit(data),
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
        log(f"NOWPAYMENTS_IPN_ACCEPTED status={payment_status} payment_id_present={bool(payment_id)} invoice_id_present={bool(invoice_id)} plan={plan}")

        if plan not in PLAN_PRICES:
            log(f"❌ Invalid payment plan ignored: {plan}")
            return "invalid plan", 400

        if not chat_id:
            return "missing order_id", 400

        if not payment_id:
            return "missing payment_id", 400

        conn = db()
        c = conn.cursor()
        # Serialize callbacks for the same provider payment to prevent double activation.
        c.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (payment_id,))

        c.execute("""
            SELECT id, amount, original_amount, discount_amount, coupon_code, invoice_url, status,
                   chat_id, plan, currency
            FROM payment_invoices
            WHERE invoice_id = %s AND %s <> ''
            ORDER BY created_at DESC
            LIMIT 1
            FOR UPDATE
        """, (invoice_id, invoice_id))
        invoice = c.fetchone()
        if not invoice:
            c.execute("""
                INSERT INTO failed_payments (payment_id, invoice_id, order_id, plan, payment_status, reason, raw_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (payment_id, invoice_id, chat_id, plan, payment_status, "invoice_not_found", raw_payload))
            conn.commit()
            conn.close()
            log(f"NOWPAYMENTS_REJECTED reason=invoice_not_found invoice_id={invoice_id}")
            return "invoice not found", 409

        invoice_row_id = invoice[0]
        coupon_code = invoice[4]
        invoice_url = invoice[5]
        invoice_chat_id = str(invoice[7] or "").strip()
        invoice_plan = str(invoice[8] or "").strip().lower()
        expected_currency = str(invoice[9] or "usd").strip().lower()

        if invoice_chat_id != chat_id or invoice_plan != plan:
            c.execute("""
                INSERT INTO failed_payments (payment_id, invoice_id, order_id, plan, payment_status, reason, raw_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (payment_id, invoice_id, chat_id, plan, payment_status, "invoice_identity_mismatch", raw_payload))
            conn.commit()
            conn.close()
            log("NOWPAYMENTS_REJECTED reason=invoice_identity_mismatch")
            return "invoice mismatch", 409

        bucket = payment_status_bucket(payment_status)
        expected_amount = Decimal(str(invoice[1]))
        try:
            provider_amount = Decimal(str(data.get("price_amount")))
        except (InvalidOperation, TypeError):
            provider_amount = Decimal("-1")
        tolerance = Decimal(str(os.environ.get("PAYMENT_AMOUNT_TOLERANCE", "0.01")))
        provider_currency = str(data.get("price_currency") or "").strip().lower()
        mismatch_reason = None
        if bucket == "success" and provider_currency != expected_currency:
            mismatch_reason = "currency_mismatch"
        elif bucket == "success" and provider_amount < 0:
            mismatch_reason = "missing_price_amount"
        elif bucket == "success" and provider_amount < (expected_amount - tolerance):
            mismatch_reason = "amount_underpaid"
        elif bucket == "success" and provider_amount > (expected_amount + tolerance):
            mismatch_reason = "amount_mismatch"

        if mismatch_reason:
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
                mismatch_reason,
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
                """, (payment_id, mismatch_reason, raw_payload, invoice_row_id))
            conn.commit()
            conn.close()
            log(f"NOWPAYMENTS_AMOUNT_REJECTED reason={mismatch_reason} expected={expected_amount} provider={provider_amount}")
            return "amount mismatch", 400

        paid_amount = float(provider_amount if provider_amount >= 0 else expected_amount)

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

        c.execute("""
            SELECT id, email, referred_by, expiry, lifetime_owner
            FROM users
            WHERE chat_id = %s
            LIMIT 1
            FOR UPDATE
        """, (chat_id,))
        buyer = c.fetchone()
        if not buyer:
            c.execute("""
                INSERT INTO failed_payments (payment_id, invoice_id, order_id, plan, payment_status, reason, raw_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (payment_id, invoice_id, chat_id, plan, payment_status, "buyer_not_found", raw_payload))
            c.execute("""
                UPDATE payment_invoices
                SET payment_id = %s, status = 'manual_review', raw_response = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (payment_id, raw_payload, invoice_row_id))
            conn.commit()
            conn.close()
            log("NOWPAYMENTS_REVIEW reason=buyer_not_found")
            return "buyer not found", 409

        c.execute("""
            INSERT INTO processed_payments (
                payment_id, order_id, payment_status, plan, amount, currency, invoice_id, invoice_url, raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (payment_id, chat_id, payment_status, plan, paid_amount, expected_currency, invoice_id, invoice_url, raw_payload))
        previous_expiry = buyer[3] if buyer else None
        if is_vip_all_forex_payment_code(plan) and buyer:
            ensure_user_subscriptions_table(conn)
            c.execute("""
                SELECT expires_at
                FROM user_subscriptions
                WHERE user_id = %s
                  AND product_code = %s
                  AND status = 'active'
                ORDER BY expires_at DESC NULLS LAST, id DESC
                LIMIT 1
            """, (buyer[0], VIP_ALL_FOREX_CODE))
            forex_existing = c.fetchone()
            previous_expiry = forex_existing[0] if forex_existing else None
            new_expiry, is_renewal = calculate_subscription_expiry(
                previous_expiry,
                days=get_subscription_duration_days(plan),
            )
            activate_vip_all_forex(
                user_id=buyer[0],
                expires_at=new_expiry,
                payment_provider="NOWPayments",
                payment_reference=payment_id,
                conn=conn,
            )
            c.execute("""
                UPDATE users
                SET bot_active = 1
                WHERE chat_id = %s
            """, (chat_id,))
        else:
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
            buyer[1] if buyer else None,
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
            buyer_email = buyer[1]
            referred_by = buyer[2]

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

        log(f"PAYMENT_ACTIVATED chat_ref={mask_chat_ref(chat_id)} plan={plan} payment_id_present={bool(payment_id)} expiry={new_expiry}")

    except Exception as e:
        log(f"❌ Webhook Error: {e}")

    return "OK"
