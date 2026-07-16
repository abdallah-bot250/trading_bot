# Telegram Incoming Webhook Fix Report

Date: 2026-07-15

## Scope

Focus: incoming Telegram updates only.

No changes were made to:

- Signal Engine
- Entry / TP / SL
- Payments
- Login / Register
- AdsGram / Free Earn
- Telegram outbound signal formatting

## What Was Reviewed

- `/webhook` route in `trader_app/blueprints/routes.py`
- Blueprint registration in `trader_app/__init__.py`
- CSRF exclusions in `trader_app/services/runtime.py`
- Existing Telegram webhook management script in `scripts/telegram_webhook.py`

## Findings

### Route

`/webhook` is registered on `telegram_bp` and accepts `POST`.

### CSRF / Login

`/webhook` is already exempt from CSRF and does not require login.

### Legacy Redirect

`/webhook` is already excluded from canonical/legacy-domain redirects.

### Security

The webhook requires:

```text
X-Telegram-Bot-Api-Secret-Token
```

and compares it with `TELEGRAM_WEBHOOK_SECRET` using:

```python
hmac.compare_digest(...)
```

No fallback without secret was added.

## Fixes Applied

### 0. Exact Secret Comparison

`/webhook` now compares the incoming Telegram header exactly against the raw `TELEGRAM_WEBHOOK_SECRET` environment value:

```text
X-Telegram-Bot-Api-Secret-Token
```

No header trimming or secret trimming is used during the actual comparison. If the Railway secret contains whitespace or is longer than Telegram allows, the server reports:

```text
TELEGRAM_WEBHOOK_REJECTED reason=invalid_secret_config
```

### 1. Startup Diagnostic

Added safe startup log:

```text
TELEGRAM_WEBHOOK_CONFIGURED route=true secret_configured=true
```

This confirms after deploy that Flask registered the route and the secret exists.

### 2. Safe Incoming Update Log

Incoming accepted updates now log:

```text
TELEGRAM_UPDATE_ACCEPTED chat_ref=... update_type=message
```

No message text and no raw `chat_id` are logged.

### 3. Safer Missing Chat Log

Missing chat updates now log:

```text
TELEGRAM_WEBHOOK_NO_CHAT update_type=message
```

### 4. Safer Webhook Management Script

Updated `scripts/telegram_webhook.py`:

- `status` prints safe `getWebhookInfo` fields:
  - url
  - pending_update_count
  - last_error_date
  - last_error_message
  - max_connections
  - allowed_updates
  - secret_configured
- `set` uses `TELEGRAM_WEBHOOK_SECRET`.
- It rejects webhook secrets containing whitespace or over Telegram's length limit.
- It never prints the bot token or webhook secret.
- `reset` now performs the full repair flow:
  - delete old webhook
  - set webhook to `BASE_URL/webhook`
  - register `secret_token` from the current environment
  - verify `getWebhookInfo`
  - optionally POST a synthetic `/start` update to the webhook when `TELEGRAM_WEBHOOK_TEST_CHAT_ID` is configured

### 5. Diagnostics Added

Added:

```text
scripts/diagnose_telegram_webhook.py
tests/test_telegram_webhook_static.py
```

The diagnostic confirms:

- `/webhook` exists.
- secret header is required.
- `hmac.compare_digest` is used.
- CSRF/redirect exemptions exist.
- safe accepted-update logging exists.

If Flask is installed, the diagnostic uses Flask test client to verify:

- no secret -> 403
- wrong secret -> 403
- correct secret -> 200

In the current local sandbox, Flask is unavailable, so it ran static checks successfully.

## Required Railway Commands

Run these in Railway shell or any environment containing the real variables:

```bash
python scripts/telegram_webhook.py status
```

If the URL or secret is wrong:

```bash
python scripts/telegram_webhook.py set
python scripts/telegram_webhook.py status
```

Expected webhook URL:

```text
https://nexoratrader.net/webhook
```

Required Railway variables:

```text
TELEGRAM_TOKEN
TELEGRAM_WEBHOOK_SECRET
BASE_URL=https://nexoratrader.net
TELEGRAM_WEBHOOK_TEST_CHAT_ID=optional_private_chat_id_for_start_test
```

or:

```text
CANONICAL_DOMAIN=https://nexoratrader.net
```

One-command repair after changing `TELEGRAM_WEBHOOK_SECRET`:

```bash
python scripts/telegram_webhook.py reset
```

This is the command to use whenever Railway `TELEGRAM_WEBHOOK_SECRET` changes.

## Tests Run

Passed:

```text
python -m py_compile app.py trader_app/__init__.py trader_app/blueprints/routes.py scripts/telegram_webhook.py scripts/diagnose_telegram_webhook.py tests/test_telegram_webhook_static.py
python scripts/diagnose_telegram_webhook.py
git diff --check
```

Local environment limitations:

```text
python scripts/smoke_routes.py
```

failed because local venv does not have Flask:

```text
ModuleNotFoundError: No module named 'flask'
```

```text
python -m pytest -q tests/test_telegram_webhook_static.py
```

failed because local venv does not have pytest:

```text
No module named pytest
```

## Final Notes

I could not directly read Railway production logs or call Telegram `getWebhookInfo` with the real token from this local environment because the real Railway secrets are not available here. The updated script is ready to run safely inside Railway or from a correctly configured shell.
