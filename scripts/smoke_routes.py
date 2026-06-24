import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "smoke-test-secret")
os.environ.setdefault("FERNET_KEY", "mJfxthKv6MhTGl_nLpV1tUTiHUnInUE_yXBEzfke6BA=")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BASE_URL", "http://localhost")
os.environ.setdefault("BOT_LINK", "https://t.me/test_bot")
os.environ.setdefault("TELEGRAM_TOKEN", "000:test")
os.environ.setdefault("STRICT_HTTPS", "false")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("RATELIMIT_STORAGE_URI", "memory://")

from app import app  # noqa: E402


ROUTES = {
    "/": {200},
    "/set-language/en": {302},
    "/set-language/ar": {302},
    "/health": {200},
    "/register": {200},
    "/login": {200},
    "/dashboard": {302},
    "/proof": {200},
    "/bot-check": {200},
    "/manual": {200, 302},
    "/manual-payment/basic": {200, 302},
    "/manual-payment/pro": {200, 302},
    "/manual-payment/vip": {200, 302},
    "/invoice-history": {200, 302},
    "/privacy-policy": {200},
    "/terms": {200},
    "/refund-policy": {200},
    "/risk-disclaimer": {200},
    "/cookie-policy": {200},
    "/contact": {200},
    "/about": {200},
    "/support": {200},
    "/docs": {200},
    "/admin": {302},
}


def main():
    failures = []
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.test_client() as client:
        for route, expected in ROUTES.items():
            response = client.get(route, follow_redirects=False)
            if response.status_code not in expected:
                failures.append(f"{route}: got {response.status_code}, expected {sorted(expected)}")

    if failures:
        print("Smoke route failures:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(f"OK: {len(ROUTES)} routes passed")


if __name__ == "__main__":
    main()
