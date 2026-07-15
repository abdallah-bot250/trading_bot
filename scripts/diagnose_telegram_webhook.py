import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "telegram-webhook-diagnostic-secret")
os.environ.setdefault("FERNET_KEY", "mJfxthKv6MhTGl_nLpV1tUTiHUnInUE_yXBEzfke6BA=")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BASE_URL", "https://nexoratrader.net")
os.environ.setdefault("BOT_LINK", "https://t.me/test_bot")
os.environ.setdefault("TELEGRAM_TOKEN", "000:test")
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "diagnostic-secret-token"
os.environ.setdefault("STRICT_HTTPS", "false")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    try:
        from app import app
    except ModuleNotFoundError as exc:
        if exc.name != "flask":
            raise
        routes_text = (ROOT / "trader_app" / "blueprints" / "routes.py").read_text(encoding="utf-8", errors="replace")
        runtime_text = (ROOT / "trader_app" / "services" / "runtime.py").read_text(encoding="utf-8", errors="replace")
        init_text = (ROOT / "trader_app" / "__init__.py").read_text(encoding="utf-8", errors="replace")
        require('@telegram_bp.route("/webhook", methods=["POST"])' in routes_text, "webhook POST route missing")
        require("X-Telegram-Bot-Api-Secret-Token" in routes_text, "Telegram secret header check missing")
        require("hmac.compare_digest" in routes_text, "constant-time secret compare missing")
        require("TELEGRAM_WEBHOOK_REJECTED reason=invalid_secret" in routes_text, "invalid secret rejection log missing")
        require("TELEGRAM_UPDATE_ACCEPTED" in routes_text, "accepted update log missing")
        require('"/webhook"' in runtime_text and '"telegram.webhook"' in runtime_text, "CSRF/redirect webhook exemption missing")
        require("TELEGRAM_WEBHOOK_CONFIGURED" in init_text, "startup webhook diagnostic missing")
        print("TELEGRAM_WEBHOOK_DIAGNOSTIC_STATIC_OK flask_unavailable=true")
        return

    require("telegram.webhook" in app.view_functions, "telegram.webhook route is not registered")
    require("/webhook" in {rule.rule for rule in app.url_map.iter_rules()}, "/webhook URL rule is missing")

    app.config.update(TESTING=True)
    payload = {"update_id": 1001, "message": {"message_id": 1}}

    with app.test_client() as client:
        missing = client.post("/webhook", json=payload)
        require(missing.status_code == 403, f"missing secret expected 403, got {missing.status_code}")

        wrong = client.post(
            "/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )
        require(wrong.status_code == 403, f"wrong secret expected 403, got {wrong.status_code}")

        correct = client.post(
            "/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": os.environ["TELEGRAM_WEBHOOK_SECRET"]},
        )
        require(correct.status_code == 200, f"correct secret expected 200, got {correct.status_code}")

    print("TELEGRAM_WEBHOOK_DIAGNOSTIC_OK")


if __name__ == "__main__":
    main()
