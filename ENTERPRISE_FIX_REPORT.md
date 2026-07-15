# Nexora Enterprise Fix Report

Date: 2026-07-14

## Scope

This pass applied the enterprise hardening package on top of the current production project without changing the signal engine, entry/TP/SL logic, AdsGram/Free Earn logic, auto-trade execution, payment pricing, or Telegram signal formatting.

## Changes Applied

### 1. VIP ALL FOREX UI Cleanup

- Landing and dashboard plan UI now show only two direct payment actions for VIP ALL FOREX:
  - Monthly
  - Yearly
- Duplicate visible manual payment buttons were removed from the public UI.
- Manual payment backend routes were preserved.

Files:

- `templates/landing.html`
- `templates/dashboard.html`

### 2. Telegram Webhook Security

- `/webhook` now requires `TELEGRAM_WEBHOOK_SECRET` unless explicitly allowed for local development with `TELEGRAM_WEBHOOK_ALLOW_INSECURE_DEV=true`.
- Incoming Telegram updates must include `X-Telegram-Bot-Api-Secret-Token`.
- Missing secret returns `503`.
- Invalid or missing Telegram header returns `403`.
- Webhook logs no longer print raw Telegram message text or raw `chat_id`.
- Logs use command type and a short SHA-256 chat fingerprint.
- `scripts/telegram_webhook.py` now registers the webhook with `secret_token`.

Files:

- `trader_app/blueprints/routes.py`
- `scripts/telegram_webhook.py`
- `.env.example`

Required production environment:

```env
TELEGRAM_WEBHOOK_SECRET=replace_with_64_char_random_secret
TELEGRAM_WEBHOOK_ALLOW_INSECURE_DEV=false
```

After setting the secret in Railway, re-register the webhook:

```bash
python scripts/telegram_webhook.py set
```

### 3. NOWPayments Webhook Hardening

- NOWPayments processing no longer falls back to matching by `chat_id + plan`.
- Payment activation now requires a matching invoice.
- Invoice identity checks include plan, chat/user context, payment ID, currency, and amount tolerance.
- Amount checks use `Decimal`.
- `PAYMENT_AMOUNT_TOLERANCE=0.01` is documented in `.env.example`.
- Unknown/mismatched payments are sent to failed/manual-review paths.
- Buyer lookup happens before processed-payment insertion.
- Payment processing uses PostgreSQL transaction locking with advisory lock and `FOR UPDATE`.
- Duplicate payment callbacks are handled idempotently.
- Sensitive payload details are not printed in logs.

Files:

- `trader_app/blueprints/routes.py`
- `.env.example`

### 4. Auth / Session Hardening

- Login and register flows call `session.clear()` before creating a new logged-in session.
- Session is explicitly marked permanent after login/register.
- Login failure messaging is generic to avoid account enumeration.
- Registration password minimum is 10 characters.
- Reset password minimum is also 10 characters for consistency.

File:

- `trader_app/blueprints/routes.py`

### 5. App Security Headers

- Flask-Talisman CSP is enabled instead of disabling CSP.
- CSP allows required Nexora production integrations:
  - TikTok Pixel
  - TradingView
  - Telegram
  - AdsGram
  - CDN/static assets already used by the site
- `frame-ancestors` remains locked down.
- `form-action` remains restricted to self.

File:

- `trader_app/__init__.py`

### 6. Rate Limiter Configuration

- Limiter now uses app configuration instead of a hardcoded in-memory backend.
- Production should set Redis-backed rate limit storage.

Required production recommendation:

```env
RATELIMIT_STORAGE_URI=redis://...
```

File:

- `trader_app/extensions.py`

### 7. Enterprise Static Tests

Added static regression tests covering:

- VIP ALL FOREX visible buttons.
- Telegram webhook secret enforcement.
- Telegram log privacy.
- NOWPayments invoice-only validation.
- NOWPayments no `chat_id + plan` fallback.
- Login/register session clearing.
- Generic login failure messaging.

Files:

- `pytest.ini`
- `tests/test_enterprise_security_static.py`

## Tests Run

```bash
python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py
```

Result: PASS

```bash
python -m compileall -q .
```

Result: PASS

```bash
python scripts/smoke_routes.py
```

Result: PASS - 24 routes passed

Notes:

- Local warnings appeared because optional packages are not installed in this local environment:
  - `flask_limiter`
  - `flask_compress`
  - `flask_talisman`
- These are environment/package warnings, not syntax failures.

```bash
python -m pytest -q
```

Result: PASS - 7 passed

```bash
git diff --check
```

Result: PASS

## Database Impact

- No migration was added.
- No destructive schema operation was added.
- NOWPayments hardening relies on existing invoice/payment tables and PostgreSQL transaction locks.

## Security Impact

Improved:

- Telegram webhook spoofing protection.
- Telegram log privacy.
- NOWPayments invoice/payment validation.
- Session fixation resistance.
- Account enumeration resistance.
- Browser security headers.
- Configurable production rate limiter backend.

Still required before production push/deploy:

- Set `TELEGRAM_WEBHOOK_SECRET` in Railway.
- Re-register Telegram webhook with the same secret.
- Set Redis-backed `RATELIMIT_STORAGE_URI` in production if Flask-Limiter is installed.
- Confirm Railway has required optional security packages installed from `requirements.txt`.

## What Was Not Changed

- Signal Engine: NO
- Entry/TP/SL logic: NO
- Auto Trade execution: NO
- AdsGram / Free Earn: NO
- Payments pricing/plans: NO
- Login/Register route names: NO
- Telegram paid signal formatting: NO
- Database schema migrations: NO

## Suggested Git Commands

```bash
git add .env.example scripts/telegram_webhook.py templates/dashboard.html templates/landing.html trader_app/__init__.py trader_app/blueprints/routes.py trader_app/extensions.py pytest.ini tests/test_enterprise_security_static.py ENTERPRISE_FIX_REPORT.md
git commit -m "Apply enterprise security hardening"
git push
```

