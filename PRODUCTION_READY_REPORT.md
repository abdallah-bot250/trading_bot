# Production Ready Report

Nexora AI Trader is prepared for commercial handoff on `https://nexoratrader.net`.

## Hardening Completed
- Public URLs default to `https://nexoratrader.net`.
- Legacy Railway host traffic redirects to the canonical domain without touching health checks.
- Admin-only `/telegram-status` reports webhook state without exposing the token.
- `scripts/telegram_webhook.py` can inspect, set, or delete the Telegram webhook.
- Worker logs include `SIGNAL_GENERATED`, `SIGNAL_SENT`, `SIGNAL_SKIPPED`, and `TELEGRAM_SEND_FAILED`.
- Signals record `source_exchange` for Binance, Binance US, or KuCoin.
- Auto trading remains gated by active bot status, API keys, stop loss, and max trade size.
- Automatic payments activate only after successful NOWPayments webhook; manual payments remain admin-reviewed.

## Plans
Supported plans: `basic`, `pro`, `vip`, `pro_2y`.

`pro_2y` is a two-year plan priced at 999 USD with 1499 USD crossed out. No lifetime plan is sold.

## Remaining Risks
- Railway must run both `web` and `worker`.
- Telegram webhook must point to `https://nexoratrader.net/webhook`.
- NOWPayments IPN must point to `https://nexoratrader.net/payment-webhook`.
- Real payment and signal flows should be smoke-tested on production with controlled accounts.

## Added Operational Coverage

- Subscription status and remaining-days calculations are visible without schema changes.
- Admin now has safe counters for active/free/premium users, expiring/expired subscriptions, system status, and last signal time.
- Optional admin metrics continue to fail closed with empty dashboard values instead of breaking the page.

## Final Launch Checklist

- [ ] Domain connected
- [ ] Telegram webhook returns 200 OK
- [ ] Admin clicked `Repair Pro 2Y Plan Constraint` once after deploy
- [ ] Free trial tested: only 2 free signals total
- [ ] Paid plan tested: no free signal cap
- [ ] Admin dashboard tested
- [ ] Signal message tested with Support, Resistance, Risk/Reward, and Target Basis
- [ ] Trade close message tested with Pair, Direction, Entry, Exit, Close Reason, PNL, PNL %, and Duration
- [ ] Referral website link tested: `/r/<referral_code>` and `/ref/<referral_code>`

## Premium Marketing Lockdown Checklist

- Landing page has a clear paid-ads hero, free-trial CTA, proof CTA, and honest risk disclaimer.
- Pricing displays Free Trial, Basic, Pro, Elite, and Pro 2 Years without renaming production plan IDs.
- Referral traffic stays on the website first, with Telegram shown as the official secondary step.
- Dashboard shows plan, subscription status, Telegram connection, and free signal usage using existing data only.
- Admin keeps the manual Pro 2Y constraint repair button visible for one-time post-deploy use if needed.
- Before paid ads: test register, login, Telegram linking, payment, manual payment, proof page, bot check, and admin health.
- No guaranteed profit copy should be used in ads, landing pages, or sales messages.
