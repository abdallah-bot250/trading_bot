# Deployment Guide

## Recommended Stack
- Railway web service
- Railway worker service
- PostgreSQL
- Custom domain with HTTPS

## Commands
- Web: `gunicorn -c gunicorn.conf.py app:app`
- Worker: `python auto_sender.py`

## Required Checks
- `/health` returns OK
- `/webhook` is excluded from canonical redirects
- `/payment-webhook` accepts signed NOWPayments IPN only
- `python scripts/smoke_routes.py` passes
- `python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py` passes

## Telegram Webhook
Set webhook to:
`https://YOUR_DOMAIN/webhook`

## AdsGram Reward URL
Use:
`https://YOUR_DOMAIN/adsgram/reward?user_id=[userId]`
