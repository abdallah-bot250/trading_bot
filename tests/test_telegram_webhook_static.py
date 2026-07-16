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
    assert 'os.environ.get("TELEGRAM_WEBHOOK_SECRET") or ""' in routes
    assert 'request.headers.get("X-Telegram-Bot-Api-Secret-Token") or ""' in routes
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
    assert "last_accepted_update_at" in routes
    assert "chat_ref=" in routes
    assert "X-Telegram-Bot-Api-Secret-Token" in routes


def test_telegram_webhook_script_can_reset_with_current_env():
    script = read("scripts/telegram_webhook.py")
    assert "def reset_webhook" in script
    assert "deleteWebhook" in script
    assert "setWebhook" in script
    assert "getWebhookInfo" in script
    assert "TELEGRAM_WEBHOOK_TEST_CHAT_ID" in script
    assert "secret_sha256_prefix" in script
