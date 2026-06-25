# Launch Checklist

Date: 2026-06-23

## Deployment

- Dockerfile added for production container builds.
- Docker Compose added for web, worker, Postgres, and Nginx.
- Nginx config added with gzip, static caching, proxy headers, and health route support.
- Gunicorn config added and shared by Railway `Procfile` and Docker.
- `/health` verified locally.

## Final Polish Review

Automated checks performed:

- Python compile check passed for app, Gunicorn config, app factory, config, performance service, and routes.
- Public route smoke test returned 200 for:
  - `/`
  - `/proof`
  - `/bot-check`
  - `/privacy-policy`
  - `/terms`
  - `/refund-policy`
  - `/risk-disclaimer`
  - `/cookie-policy`
  - `/contact`
  - `/about`
  - `/support`
  - `/docs`
  - `/health`
- Internal template link scan found 0 missing internal links.
- Route map currently exposes 47 routes.
- Static cache headers verified for `/static/premium.css`.
- Public cache headers verified for `/` and `/privacy-policy`.

## Production Notes

- Docker was not installed on the local machine, so `docker compose config` could not be executed here.
- Browser screenshot automation was unavailable in this Codex session because the local browser plugin was missing its runtime script.
- Visual responsive QA should still be performed manually or with Playwright on a machine that has browser automation available.

## Must-Verify Before Public Launch

- Railway variables are filled with production values.
- `BASE_URL` matches the final custom domain.
- Telegram webhook points to `https://nexoratrader.net/webhook`.
- NOWPayments IPN callback points to `https://nexoratrader.net/payment-webhook`.
- Admin account is created and matches `ADMIN_EMAIL`.
- Manual payment wallet and support link are real production values.
- Test one Starter, Pro, and Elite activation flow.
- Test one failed/pending payment webhook event in a staging environment.
- Test Telegram `/start`, `/subscription`, `/stats`, and admin broadcast commands.
- Review all pages on mobile widths: 390px, 768px, 1440px.
