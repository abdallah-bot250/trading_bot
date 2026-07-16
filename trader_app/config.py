import os
from datetime import timedelta


def _get_secret_key():
    secret = os.environ.get("SECRET_KEY", "").strip()
    flask_env = os.environ.get("FLASK_ENV", "").strip().lower()
    app_env = os.environ.get("APP_ENV", os.environ.get("ENV", "")).strip().lower()
    is_production = flask_env == "production" or app_env == "production"
    weak_values = {"", "secret", "change_this_secret_key", "your_secret_key"}
    if is_production and secret in weak_values:
        raise RuntimeError("SECRET_KEY must be set to a strong non-default value in production")
    return secret or "dev-only-secret-key"


class Config:
    SECRET_KEY = _get_secret_key()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() in ["1", "true", "yes"]
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get("SESSION_TIMEOUT_MINUTES", "60")))
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(days=int(os.environ.get("STATIC_CACHE_DAYS", "30")))
    COMPRESS_MIMETYPES = [
        "text/html",
        "text/css",
        "text/xml",
        "application/json",
        "application/javascript",
        "image/svg+xml",
    ]
    COMPRESS_LEVEL = int(os.environ.get("COMPRESS_LEVEL", "6"))
    COMPRESS_MIN_SIZE = int(os.environ.get("COMPRESS_MIN_SIZE", "512"))
    CACHE_STATIC_SECONDS = int(os.environ.get("CACHE_STATIC_SECONDS", str(60 * 60 * 24 * 30)))
    CACHE_PUBLIC_SECONDS = int(os.environ.get("CACHE_PUBLIC_SECONDS", "300"))

    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    BASE_URL = os.environ.get("BASE_URL", "https://yourdomain.com")
    BOT_LINK = os.environ.get("BOT_LINK", "https://t.me/your_bot_username")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PUBLIC_URL")

    NOWPAYMENTS_API_KEY = os.environ.get("NOWPAYMENTS_API_KEY", "").strip()
    NOWPAYMENTS_IPN_SECRET = (os.environ.get("NOWPAYMENTS_IPN_SECRET") or os.environ.get("NOWPAYMENTS_IPN_CALLBACK_SECRET") or os.environ.get("IPN_SECRET") or "").strip()

    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    STRICT_HTTPS = os.environ.get("STRICT_HTTPS", "true").lower() in ["1", "true", "yes"]
    PAYMENT_AMOUNT_TOLERANCE = float(os.environ.get("PAYMENT_AMOUNT_TOLERANCE", "0.01"))

    SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
    SECURITY_EMAIL_FROM = os.environ.get("SECURITY_EMAIL_FROM", SMTP_USERNAME or "no-reply@example.com").strip()
