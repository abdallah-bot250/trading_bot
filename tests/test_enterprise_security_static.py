from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8", errors="ignore")


def test_vip_all_forex_public_ui_has_monthly_and_yearly_only():
    landing = read("templates/landing.html")
    dashboard = read("templates/dashboard.html")

    forex_landing = landing[landing.index("VIP ALL FOREX"):]
    assert 'action="/create-payment" method="POST"' in forex_landing
    assert 'name="plan" value="vip_all_forex"' in forex_landing
    assert 'name="plan" value="vip_all_forex_yearly"' in forex_landing
    assert "/manual-payment/vip_all_forex" not in forex_landing
    assert "/manual-payment/vip_all_forex_yearly" not in forex_landing

    forex_dashboard = dashboard[dashboard.index("VIP ALL FOREX"):]
    assert 'name="plan" value="vip_all_forex"' in forex_dashboard
    assert 'name="plan" value="vip_all_forex_yearly"' in forex_dashboard
    assert "/manual-payment/vip_all_forex" not in forex_dashboard
    assert "/manual-payment/vip_all_forex_yearly" not in forex_dashboard


def test_telegram_webhook_is_secret_checked_and_not_raw_logged():
    routes = read("trader_app/blueprints/routes.py")

    assert "TELEGRAM_WEBHOOK_SECRET" in routes
    assert "X-Telegram-Bot-Api-Secret-Token" in routes
    assert "webhook unavailable" in routes
    assert "hashlib.sha256(chat_id.encode" in routes
    assert "Telegram message | chat_id=" not in routes


def test_nowpayments_requires_matching_invoice_before_processing():
    routes = read("trader_app/blueprints/routes.py")
    webhook_start = routes.index('def payment_webhook():')
    webhook = routes[webhook_start:]

    assert "pg_advisory_xact_lock" in webhook
    assert "FOR UPDATE" in webhook
    assert "invoice_not_found" in webhook
    assert "invoice_identity_mismatch" in webhook
    assert "currency_mismatch" in webhook
    assert "buyer_not_found" in webhook
    assert "INSERT INTO processed_payments" in webhook
    assert webhook.index("buyer_not_found") < webhook.index("INSERT INTO processed_payments")
    assert "OR (chat_id = %s AND plan = %s)" not in webhook


def test_login_and_register_clear_session_and_use_generic_login_failure():
    routes = read("trader_app/blueprints/routes.py")

    assert routes.count("session.clear()") >= 3
    assert "reason=unknown_email" in routes
    assert "reason=bad_password" in routes
    assert "البريد الإلكتروني أو كلمة المرور" in routes
    assert "الباسورد غير صحيح" not in routes

    login_start = routes.index('@auth_bp.route("/login"')
    login_end = routes.index('@auth_bp.route("/logout"')
    login_block = routes[login_start:login_end]
    assert "الإيميل غير موجود" not in login_block
