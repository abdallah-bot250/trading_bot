# Nexora AI Trader - Sale README

Suggested selling price: 8000 USD.

## Features
- Premium landing page, pricing, dashboard, admin panel, and bot verification page.
- Telegram onboarding, subscription status, stats, affiliate links, and admin broadcasts.
- Binance, Binance US, and KuCoin market data fallback.
- Signal tracking with TP/SL outcome monitoring.
- NOWPayments automatic payment and manual payment desk.
- Affiliate commissions and withdrawal requests.

## Tech Stack
Python, Flask, Gunicorn, PostgreSQL, SQLAlchemy, Alembic, Telegram Bot API, NOWPayments, ccxt, pandas, NumPy, scikit-learn.

## Demo Checklist
- Open `https://nexoratrader.net/health`.
- Verify `/bot-check`.
- Register and login with a test account.
- Link Telegram with `/start`.
- Review dashboard, payment pages, invoice history, and admin panel.
- Confirm worker logs show signal activity.

## Known Limitations
This is not a profit guarantee. Auto trading requires user API keys and careful testing. Manual payments require admin approval.

## Buyer-Facing Operational Features

- Subscription visibility: plan status, expiry, and remaining days are shown to users.
- Admin intelligence: active users, free/premium split, expiring/expired subscriptions, revenue, signals, and service status.
- Referral visibility: referral link, referral code, copy action, total referrals, commission total, balance, and withdrawals.

## Phase 2 Buyer Notes

- Includes subscription lifecycle visibility, referral QR/code dashboard, richer admin health cards, and read-only system diagnostics.
- These additions are backward compatible and do not alter authentication, Telegram linking, payments, trading, or AI logic.

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
