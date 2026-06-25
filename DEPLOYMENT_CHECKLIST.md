# Deployment Checklist

## Railway
- Set `BASE_URL=https://nexoratrader.net`.
- Set `CANONICAL_DOMAIN=https://nexoratrader.net`.
- Set `BOT_LINK`, `TELEGRAM_TOKEN`, `SECRET_KEY`, `FERNET_KEY`, `ADMIN_EMAIL`, and `DATABASE_URL`.
- Set NOWPayments variables for automatic payments.
- Run both `web` and `worker` from the Procfile.

## Webhooks
- Telegram: `https://nexoratrader.net/webhook`.
- NOWPayments IPN: `https://nexoratrader.net/payment-webhook`.
- Check Telegram from `/telegram-status`.

## Final Tests
```bash
python scripts/smoke_routes.py
python -m py_compile app.py auto_sender.py market_analyzer.py trade_tracker.py spot_futures_engine.py
```
