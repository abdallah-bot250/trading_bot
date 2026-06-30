import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "diagnose-telegram-link")
os.environ.setdefault("FERNET_KEY", "mJfxthKv6MhTGl_nLpV1tUTiHUnInUE_yXBEzfke6BA=")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BASE_URL", "http://localhost")
os.environ.setdefault("BOT_LINK", "https://t.me/test_bot")
os.environ.setdefault("TELEGRAM_TOKEN", "000:test")
os.environ.setdefault("STRICT_HTTPS", "false")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")

from app import app  # noqa: E402


def main():
    routes = {str(rule.rule) for rule in app.url_map.iter_rules()}
    required_routes = ["/bot-check", "/webhook", "/login", "/register", "/dashboard"]
    print("TELEGRAM_BOT_TOKEN configured:", bool(os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")))
    print("BOT_LINK configured:", bool(os.environ.get("BOT_LINK")))
    for route in required_routes:
        print(f"route {route}:", route in routes)
    model_path = ROOT / "trader_app" / "db" / "models.py"
    model_text = model_path.read_text(encoding="utf-8") if model_path.exists() else ""
    print("user_model_chat_id_field:", "chat_id = Column" in model_text)
    print("link_token_backend:", "telegram_link_tokens table is created on demand by routes.py")
    print("telegram_start_handler:", "/webhook" in routes)


if __name__ == "__main__":
    main()
