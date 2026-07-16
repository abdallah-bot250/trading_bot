# Telegram Subscriptions and Delivery Handover

## Root Cause

Telegram `/start` and `/subscription` were reading the legacy `users.plan` field for the main subscription view. VIP ALL FOREX is stored separately in `user_subscriptions`, so a user with both Crypto and VIP ALL FOREX could see only the Crypto plan in Telegram.

Some Telegram-facing strings were also stored as mojibake, so users could see broken text such as `Ã`, `Â`, or `ðŸ`.

## Fix Summary

- Added a unified entitlement service:
  - `trader_app/services/user_entitlements.py`
- Telegram messages now render Crypto and VIP ALL FOREX as independent sections.
- `auto_sender.py` uses the same entitlement service for delivery eligibility.
- Added `DELIVERY_ELIGIBILITY` logs without exposing full email or raw chat ID.
- Added a read-only admin page:
  - `/admin/delivery-diagnostics`
- Rebuilt `trader_app/services/telegram.py` with clean UTF-8 strings.

## Crypto Subscription Storage

Crypto subscription status remains backward-compatible with the existing `users` table:

- `users.plan`
- `users.expiry`
- `users.is_paid`
- `users.lifetime_owner`
- `users.spot_enabled`
- `users.futures_enabled`

The entitlement service converts those fields into:

- Crypto active / expired
- Spot eligibility
- Futures eligibility
- Auto Trade eligibility

## Forex Subscription Storage

VIP ALL FOREX is stored independently in:

- `user_subscriptions.product_code = vip_all_forex`
- `user_subscriptions.market_type = forex`
- `user_subscriptions.status`
- `user_subscriptions.is_paid`
- `user_subscriptions.starts_at`
- `user_subscriptions.expires_at`

Forex does not replace or rename the user's Crypto plan.

## Conflict Handling

Crypto and Forex are evaluated independently:

- Crypto-only users see Forex as `Not Active`.
- Forex-only users see Crypto separately.
- Users with both see both sections.
- Expired plans are shown as expired instead of hidden.

## Telegram Message Shape

### `/start`

Shows:

- Account connected successfully
- Crypto Subscription
- VIP ALL FOREX Subscription
- `/subscription`
- `/plans`
- `/stats`

### `/subscription`

Shows:

- Crypto plan, status, expiry, Spot, Futures, Auto Trade
- Forex plan, status, expiry, Forex Signals, Forex Auto Trade status
- Telegram linked status
- Free signal usage

### `/plans`

Uses the central Plan Catalog and shows:

- Crypto plans
- VIP ALL FOREX monthly/yearly
- supported assets only
- Forex Auto Trade as `Not available`
- disclaimers
- safe checkout links

## Delivery Behavior

`auto_sender.py` now calls the unified entitlement service before deciding whether a user may receive a Crypto or Forex signal.

Expected behavior:

- Crypto signal -> Crypto entitlement required.
- Forex signal -> VIP ALL FOREX entitlement required.
- User with both -> can receive both.
- Missing Telegram chat -> blocked with `missing_chat_id`.
- Expired plan -> blocked as inactive/expired.

## Admin Diagnostics

New read-only route:

`/admin/delivery-diagnostics`

Shows:

- Telegram linked
- Telegram active
- Crypto plan / expiry / eligibility
- Forex plan / expiry / eligibility
- Last Crypto delivery
- Last Forex delivery
- Failure reason

## Encoding

`trader_app/services/telegram.py` was rebuilt as clean UTF-8.

The remaining scan should be reviewed for legacy non-Telegram strings if any appear outside the Telegram layer.

## Tests

Expected commands:

```bash
python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py forex_analyzer.py
python -m compileall -q trader_app
python scripts/smoke_routes.py
python scripts/scan_mojibake.py
python scripts/diagnose_telegram_subscriptions_delivery.py
python scripts/diagnose_telegram_plans_catalog.py
pytest -q
git diff --check
```

## Migration

No required destructive migration.

The existing `user_subscriptions` table is created with `CREATE TABLE IF NOT EXISTS` by the current code path.

## Remaining Risk

If old Telegram strings exist in unrelated legacy branches, `scan_mojibake.py` may still report them. They should be cleaned progressively without changing payment, signal engine, or subscription logic.
