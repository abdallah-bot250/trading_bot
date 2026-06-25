"""Inspect or update the Telegram webhook for Nexora.

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

DEFAULT_BASE_URL = "https://nexoratrader.net"


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is missing")
    return value


def public_base_url():
    value = os.environ.get("CANONICAL_DOMAIN") or os.environ.get("BASE_URL") or DEFAULT_BASE_URL
    value = str(value).strip().rstrip("/")
    if not value.startswith("https://"):
        raise SystemExit("Telegram webhooks require a public https:// domain")
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
        raise SystemExit(f"Telegram {method} failed: {payload}")

    return payload


def status():
    payload = telegram("getWebhookInfo")
    result = payload.get("result") or {}
    expected = f"{public_base_url()}/webhook"
    print(f"Current webhook: {result.get('url') or '(not set)'}")
    print(f"Expected webhook: {expected}")
    print(f"Matches expected: {(result.get('url') or '').rstrip('/') == expected.rstrip('/')}")
    print(f"Pending updates: {result.get('pending_update_count', 0)}")
    if result.get("last_error_message"):
        print(f"Last error: {result.get('last_error_message')}")


def set_webhook():
    url = f"{public_base_url()}/webhook"
    telegram("setWebhook", url=url, drop_pending_updates=False)
    print(f"Webhook set to {url}")


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
