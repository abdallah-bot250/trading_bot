# Final Forex Release Blockers Report

Date: 2026-07-16

## Scope

This release-blocker pass only hardens the Forex provider/readiness layer.

Not changed:

- Crypto Signal Logic
- Crypto Entry/TP/SL calculations
- Payments
- Plan pricing
- Telegram paid signal formatting
- AdsGram / Free Earn security

## Blockers Fixed

### 1. Twelve Data API Consumption

Twelve Data Basic-style limits are now protected by a central Forex request budget.

Added controls:

- `FOREX_TWELVEDATA_REQUESTS_PER_MINUTE`
- `FOREX_TWELVEDATA_REQUESTS_PER_DAY`
- `FOREX_TWELVEDATA_DAILY_RESERVE`
- `FOREX_SYMBOLS_PER_CYCLE`
- `FOREX_SYMBOL_ROTATION_SECONDS`
- `FOREX_CACHE_SECONDS_4H`
- `FOREX_CACHE_SECONDS_1H`
- `FOREX_CACHE_SECONDS_30M`
- `FOREX_CACHE_SECONDS_15M`
- `FOREX_CACHE_SECONDS_5M`

The scanner no longer requests all symbols and all timeframes every cycle. It rotates symbols and uses longer cache windows for higher timeframes.

Budget diagnostics report:

- `requests_used`
- `requests_remaining_estimate`
- `symbols_deferred`
- `rate_limit_hits`

Rate-limit or budget exhaustion is treated as temporary, not a permanent symbol failure.

### 2. Real Spread Is Required by Default

`FOREX_REQUIRE_REAL_SPREAD` now defaults to `true`.

If:

- `FOREX_PRODUCTION_MODE=true`
- `FOREX_REQUIRE_REAL_SPREAD=false`

Forex delivery is blocked with:

`UNSAFE_PRODUCTION_CONFIGURATION`

No paid Forex signal is allowed without:

- real bid
- real ask
- real spread
- fresh pricing timestamp

No spread is estimated from candles, ATR, high/low, or any synthetic formula.

### 3. Forex Readiness States

Readiness now uses explicit states:

- `SHADOW_READY`
- `PRODUCTION_READY`
- `NOT_READY`

Shadow readiness means real candles can be evaluated, but no customer delivery is allowed.

Production readiness requires:

- production mode enabled
- shadow mode disabled
- candle provider configured
- fresh candle success
- real bid/ask pricing success
- real spread required
- Trading Economics configured and fresh
- Telegram configuration present
- subscription delivery checks healthy

Pricing provider health is not based on credentials alone. It requires a successful real quote.

### 4. News Provider Fails Closed

Trading Economics remains the only official news provider.

When news credentials are missing and `FOREX_REQUIRE_NEWS_CALENDAR=true`, the system reports:

`NEWS_PROVIDER_NOT_CONFIGURED`

No scraping or fake news provider was added.

### 5. Expired Forex Entitlement Display

Telegram/dashboard display can now show the latest Forex subscription even if expired.

Expired subscriptions are display-only and do not grant delivery entitlement.

Signal delivery still uses active paid subscriptions only.

### 6. Pytest Clean Release

`pytest.ini` now includes:

`pythonpath = .`

This allows clean imports from the repository root.

### 7. Provider Documentation

Finnhub is not advertised as an active candle fallback because OHLC is not enabled in the current implementation.

Oil/indices are not shown as verified unless explicitly enabled with:

`FOREX_ENABLE_UNVERIFIED_CFD_SYMBOLS=true`

By default, verified Twelve Data symbols include Forex majors and metals only.

## Railway Variables

Minimum for shadow candles:

- `FOREX_SIGNAL_ENGINE_ENABLED=true`
- `FOREX_DATA_PROVIDER=twelvedata`
- `TWELVEDATA_API_KEY=...`
- `FOREX_SHADOW_MODE=true`
- `FOREX_PRODUCTION_MODE=false`

Minimum for production Forex delivery:

- `FOREX_PRODUCTION_MODE=true`
- `FOREX_SHADOW_MODE=false`
- `FOREX_REQUIRE_REAL_SPREAD=true`
- `OANDA_API_TOKEN=...` or another future real bid/ask provider
- `OANDA_ACCOUNT_ID=...`
- `TRADING_ECONOMICS_API_KEY=...`
- `TRADING_ECONOMICS_API_SECRET=...`
- `TELEGRAM_TOKEN=...`
- `BASE_URL=https://nexoratrader.net`

Budget controls:

- `FOREX_TWELVEDATA_REQUESTS_PER_MINUTE=8`
- `FOREX_TWELVEDATA_REQUESTS_PER_DAY=800`
- `FOREX_TWELVEDATA_DAILY_RESERVE=25`
- `FOREX_SYMBOLS_PER_CYCLE=2`
- `FOREX_SYMBOL_ROTATION_SECONDS=300`

## Migration

No destructive migration is required.

The subscription helper uses the existing `user_subscriptions` table and its safe `CREATE TABLE IF NOT EXISTS` / additive-column behavior.

## Security Impact

Positive:

- No fake Forex delivery without real spread.
- No pricing provider marked healthy without a fresh successful quote.
- No news bypass in production.
- No secrets logged or exposed.

## Production Recommendation

Forex can run in shadow mode with Twelve Data candles.

Do not enable production Forex delivery until a real bid/ask provider and Trading Economics credentials are configured and `/admin/production-readiness` reports `PRODUCTION_READY`.
