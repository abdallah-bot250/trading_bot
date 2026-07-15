from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def test_telegram_webhook_requires_secret_header():
    routes = read("trader_app/blueprints/routes.py")
    assert '@telegram_bp.route("/webhook", methods=["POST"])' in routes
    assert "TELEGRAM_WEBHOOK_SECRET" in routes
    assert "X-Telegram-Bot-Api-Secret-Token" in routes
    assert "hmac.compare_digest" in routes
    assert "TELEGRAM_WEBHOOK_REJECTED reason=invalid_secret" in routes


def test_telegram_webhook_is_exempt_from_csrf_and_redirects():
    runtime = read("trader_app/services/runtime.py")
    assert '"telegram.webhook"' in runtime
    assert '"/webhook"' in runtime
    assert '"/payment-webhook"' in runtime


def test_telegram_webhook_has_safe_startup_and_accept_logs():
    init = read("trader_app/__init__.py")
    routes = read("trader_app/blueprints/routes.py")
    assert "TELEGRAM_WEBHOOK_CONFIGURED" in init
    assert "TELEGRAM_UPDATE_ACCEPTED" in routes
    assert "chat_ref=" in routes
    assert "X-Telegram-Bot-Api-Secret-Token" in routes
