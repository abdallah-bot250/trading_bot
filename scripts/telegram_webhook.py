"""Inspect or update the Telegram webhook for this deployment.

Usage:
  python scripts/telegram_webhook.py status
  python scripts/telegram_webhook.py set
  python scripts/telegram_webhook.py delete
"""

import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is missing")
    return value


def telegram(method, **params):
    token = required_env("TELEGRAM_TOKEN")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/{method}",
        json=params or None,
        timeout=15,
    )
    try:
        payload = response.json()
    except ValueError:
        raise SystemExit(f"Telegram returned non-JSON response: {response.text}")

    if response.status_code != 200 or not payload.get("ok"):
        safe_payload = dict(payload)
        if "description" in safe_payload:
            safe_payload["description"] = str(safe_payload["description"])[:300]
        raise SystemExit(f"Telegram {method} failed: {safe_payload}")

    return payload


def base_url():
    value = os.environ.get("CANONICAL_DOMAIN") or os.environ.get("BASE_URL")
    value = str(value or "").strip().rstrip("/")
    if not value or value in {"https://yourdomain.com", "http://localhost"}:
        raise SystemExit("BASE_URL or CANONICAL_DOMAIN must be your final public HTTPS domain")
    if not value.startswith("https://"):
        raise SystemExit("Telegram webhooks require a public https:// domain")
    return value


def status():
    payload = telegram("getWebhookInfo")
    result = payload.get("result") or {}
    expected = f"{base_url()}/webhook"
    print("TELEGRAM_WEBHOOK_INFO")
    print(f"url={result.get('url') or '(not set)'}")
    print(f"expected_url={expected}")
    print(f"matches_expected={(result.get('url') or '').rstrip('/') == expected.rstrip('/')}")
    print(f"pending_update_count={result.get('pending_update_count', 0)}")
    print(f"last_error_date={result.get('last_error_date') or ''}")
    print(f"last_error_message={result.get('last_error_message') or ''}")
    print(f"max_connections={result.get('max_connections') or ''}")
    print(f"allowed_updates={','.join(result.get('allowed_updates') or [])}")
    print(f"secret_configured={bool(os.environ.get('TELEGRAM_WEBHOOK_SECRET', '').strip())}")


def set_webhook():
    url = f"{base_url()}/webhook"
    secret = required_env("TELEGRAM_WEBHOOK_SECRET")
    if len(secret) > 256 or any(ch.isspace() for ch in secret):
        raise SystemExit("TELEGRAM_WEBHOOK_SECRET must be 1-256 chars and must not contain whitespace")
    telegram("setWebhook", url=url, secret_token=secret, drop_pending_updates=False)
    print(f"Webhook set to {url} with secret_token configured=true")


def delete_webhook():
    telegram("deleteWebhook", drop_pending_updates=False)
    print("Webhook deleted")


def main():
    command = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if command == "status":
        status()
    elif command == "set":
        set_webhook()
    elif command == "delete":
        delete_webhook()
    else:
        raise SystemExit("Usage: python scripts/telegram_webhook.py [status|set|delete]")


if __name__ == "__main__":
    main()
