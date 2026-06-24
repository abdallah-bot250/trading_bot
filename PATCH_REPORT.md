# Nexora AI Trader - Company Fix Patch

This patch fixes the production issues found after Railway deployment.

## Fixed

1. Database / Admin crash
- Rebuilt `init_db()` to be Railway-safe.
- Added missing `created_at`, `updated_at`, and `deleted_at` columns where needed.
- Prevented failed DDL from leaving PostgreSQL in `current transaction is aborted` state.
- Added safe per-statement rollback and commit.
- Updated the plan constraint to support the fourth plan.

2. Fourth plan added
- Added `Ultimate` plan.
- Price: `$199.99`.
- Added to backend pricing, labels, payment validation, dashboard pricing, admin activation, and landing pricing.

3. Automatic payments improved
- `create-payment` no longer fails if the user has not linked Telegram yet.
- Payments can be created by email and later linked to Telegram.
- Webhook resolves paid users by invoice, payment ID, chat ID, or email.
- Paid subscriptions activate even if Telegram linking happens later.
- Affiliate commission still works for resolved users.

4. Telegram signal delivery
- Preserved `/webhook`, Telegram commands, and signal sender.
- Kept Spot/Futures user preference filtering.
- Added Ultimate support to the signal plan filters.
- Enabled auto-trade mode for Elite and Ultimate when API keys and bot_active are enabled.

5. Clean production repo
- Removed `__pycache__`, `*.pyc`, logs, and pid files.
- Updated `.gitignore` to prevent them from coming back.

6. Arabic / English
- Mojibake scan passes with COUNT=0.
- Existing bilingual system remains intact.

## Important Railway notes

- You can remove or ignore `SKIP_INIT_DB=true`; the new init_db is safe and should run.
- Keep these variables set:
  - SECRET_KEY
  - FERNET_KEY
  - DATABASE_URL
  - BASE_URL
  - TELEGRAM_TOKEN
  - BOT_LINK
  - ADMIN_EMAIL
  - NOWPAYMENTS_API_KEY
  - NOWPAYMENTS_IPN_SECRET
  - WEB_CONCURRENCY=1
  - GUNICORN_THREADS=2
  - GUNICORN_TIMEOUT=120

## After deploying

Test:
- `/health`
- `/login`
- `/dashboard`
- `/admin`
- `/create-payment?plan=basic`
- `/create-payment?plan=ultimate`
- Telegram `/start`
- Telegram `/subscription`
