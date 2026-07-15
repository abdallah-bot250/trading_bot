# Real Forex Production Upgrade

## Scope

This upgrade keeps crypto analysis and all payment pricing unchanged. It hardens the Forex signal path so that a production signal cannot be created from synthetic spread or an unverified news state.

## Implemented

- Added `trader_app/services/forex_news.py`.
- Added a configurable real economic-calendar adapter.
- Added real quote retrieval in `forex_market_data.py` for bid/ask spread validation.
- Removed the candle-range spread proxy from production signal acceptance.
- Added fail-closed controls:
  - `FOREX_REQUIRE_REAL_SPREAD=true`
  - `FOREX_REQUIRE_NEWS_CALENDAR=true`
- A missing, failed, stale, rate-limited, or unauthorized data/news provider blocks Forex signals rather than fabricating a setup.
- Forex signals now explain:
  - 4H and 1H trend alignment.
  - EMA pullback zone.
  - RSI and MACD confirmation.
  - Session.
  - Real bid/ask spread.
  - News-calendar decision.
  - ATR and support/resistance basis for SL/TP.
  - Risk/reward.
- Telegram formatting now identifies Forex session, spread source, provider, timestamp, and a longer reason for the trade.
- Forex auto-trading remains disabled.
- Existing Admin manual activation for `VIP ALL FOREX` remains available and independent from the user's crypto plan.

## Required Railway variables

```env
FOREX_SIGNAL_ENGINE_ENABLED=true
FOREX_DATA_PROVIDER=twelvedata
FOREX_DATA_API_KEY=<real provider key>
FOREX_REQUIRE_REAL_SPREAD=true

FOREX_REQUIRE_NEWS_CALENDAR=true
FOREX_NEWS_PROVIDER=tradingeconomics
FOREX_NEWS_API_KEY=<real calendar client key>
FOREX_NEWS_API_SECRET=<real calendar client secret>
FOREX_NEWS_LOOKAHEAD_MINUTES=45
FOREX_NEWS_LOOKBACK_MINUTES=20
FOREX_NEWS_MIN_IMPORTANCE=2

FOREX_AUTO_TRADE_ENABLED=false
```

## Production acceptance criteria

Do not sell Forex signal access until logs show:

- `FOREX_PROVIDER_STATUS ... configured=true`
- `FOREX_NEWS_PROVIDER_STATUS ... configured=true required=true`
- `symbols_with_data > 0`
- `rejected_real_spread=0` for at least some supported symbols
- No `AUTH_FAILED`, `API_KEY_MISSING`, or continuous `RATE_LIMITED`
- Telegram incoming and outgoing tests pass

A valid system is not required to produce a trade every cycle. Zero trades is expected when no setup passes trend, pullback, momentum, spread, news, freshness, and risk/reward gates.

## Verification performed

- Python syntax compilation passed for modified modules.
- Package compileall passed.
- Existing Forex/signal-supply diagnostic passed.
- Real Forex readiness diagnostic passed.

Full Flask tests require the project's installed runtime dependencies.
