# Nexora AI Trader Deployment Guide

This project supports Railway deployment and Docker-based production deployment.

## Production Files

- `Procfile` runs the Railway web process with Gunicorn.
- `gunicorn.conf.py` centralizes worker, timeout, thread, and logging settings.
- `Dockerfile` builds a production Python image and exposes port `8080`.
- `docker-compose.yml` runs web, worker, Postgres, and Nginx locally or on a VPS.
- `deploy/nginx.conf` serves static files with long cache headers and proxies dynamic traffic to Gunicorn.
- `/health` is the health check endpoint used by Docker and Nginx.

## Required Environment Variables

Set these in Railway, your VPS environment, or `.env`:

```env
SECRET_KEY=change_this_secret_key
FERNET_KEY=generate_a_real_fernet_key
DATABASE_URL=postgresql://...
TELEGRAM_TOKEN=...
BOT_LINK=https://t.me/your_bot_username
BASE_URL=https://your-domain.com
ADMIN_EMAIL=admin@example.com
NOWPAYMENTS_API_KEY=...
NOWPAYMENTS_IPN_SECRET=...
STRICT_HTTPS=true
SESSION_COOKIE_SECURE=true
```

Optional production tuning:

```env
WEB_CONCURRENCY=2
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=90
CACHE_STATIC_SECONDS=2592000
CACHE_PUBLIC_SECONDS=300
COMPRESS_LEVEL=6
COMPRESS_MIN_SIZE=512
```

## Railway

Railway will use `Procfile`:

```procfile
web: gunicorn -c gunicorn.conf.py app:app
worker: python auto_sender.py
```

Checklist:

- Add a Postgres database and set `DATABASE_URL`.
- Add all required environment variables.
- Set `BASE_URL` to the final Railway or custom domain URL.
- Set Telegram webhook to `https://your-domain.com/webhook`.
- Set NOWPayments IPN callback to `https://your-domain.com/payment-webhook`.
- Verify `https://your-domain.com/health` returns `{"status":"ok"}`.

## Docker Compose

For local production-like testing:

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Site: `http://localhost`
- Direct Gunicorn app: `http://localhost:8080`
- Health: `http://localhost/health`

Notes:

- Compose includes Postgres and passes `DATABASE_URL` to the web and worker containers.
- Nginx serves `/static/` directly with immutable cache headers.
- Gunicorn handles Flask routes behind Nginx.

## Nginx

The included `deploy/nginx.conf`:

- Enables gzip compression.
- Caches static files for 30 days.
- Adds basic hardening headers.
- Proxies dynamic requests to `web:8080`.
- Keeps `/health` available for uptime checks.

## Final Launch Checks

- Public pages: `/`, `/proof`, `/bot-check`, `/privacy-policy`, `/terms`, `/refund-policy`, `/risk-disclaimer`, `/cookie-policy`, `/contact`, `/about`, `/support`, `/docs`.
- Auth pages: `/register`, `/login`, password reset, email verification.
- Dashboard: plan cards, coupon input, automatic payment, manual payment, invoice history.
- Payments: `/create-payment`, `/payment-webhook`, duplicate payment handling, failed payment tracking.
- Telegram: `/webhook`, `/start`, `/subscription`, `/stats`, admin broadcast commands.
- Admin: users, payments metrics, coupons, withdrawals, affiliate, AI performance, spot/futures stats.
- Performance: static cache headers, public cache headers, no-store for dashboard/admin/invoices.
- Security: HTTPS, secure cookies, CSRF, admin protection, audit logs.
