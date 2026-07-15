# Nexora Forex Engine and Signal Supply Report

## Scope

This phase adds a real Forex analysis layer without changing the existing crypto signal engine, payment flow, Telegram linking, Free Earn, AdsGram, authentication, or auto-trade execution.

## What Existed Before

The production code already contained:

- `vip_all_forex` subscription identifiers and pricing.
- Forex delivery routing markers in `auto_sender.py`.
- Diagnostic scripts proving subscription and product routing.

What was missing:

- No real Forex market data provider.
- No independent Forex analyzer.
- No Forex OHLCV validation.
- No Forex scan summary.
- No proof that Forex users would receive actual Forex signals only when market data and analysis are valid.

## What Was Added

### Forex Market Data

New file:

- `trader_app/services/forex_market_data.py`

It supports:

- Provider abstraction with `FOREX_DATA_PROVIDER=twelvedata`.
- API key from `FOREX_DATA_API_KEY`.
- Safe retries and timeout handling.
- In-memory caching.
- Candle stale-data rejection.
- Forex, metals, oil, and index symbol normalization.
- No hardcoded provider secret.
- No fake candles when the provider/API key is missing.

### Forex Analyzer

New file:

- `forex_analyzer.py`

It supports:

- Forex-only signal building.
- 4H and 1H trend confirmation.
- 15M/5M entry timeframe evaluation.
- EMA, RSI, MACD, ATR, support/resistance, volatility, spread, and news blackout checks.
- `FOREX_SCAN_SUMMARY`.
- Forex signals marked with `market_type=forex`.
- `auto_trade_allowed=False`.

Forex auto-trade remains disabled by design.

### Auto Sender Integration

Updated:

- `auto_sender.py`

Changes:

- Crypto signal fetching remains unchanged.
- Forex signals are fetched in the same sending cycle through the independent Forex analyzer.
- Crypto and Forex signals are combined only after each engine finishes independently.
- Forex signals are delivered only to users with active `vip_all_forex`.
- Forex signals do not trigger crypto trade-type recording.
- Forex auto-trade is skipped with `FOREX_AUTO_TRADE_DISABLED`.
- Added `CRYPTO_SCAN_SUMMARY`, `FOREX_SCAN_SUMMARY`, and `DELIVERY_SUMMARY`.

### Crypto Diagnostics

Updated:

- `market_analyzer.py`

Changes:

- Added fixed rejection reason codes:
  - `LOW_VOLATILITY`
  - `MTF_CONFLICT`
  - `LOW_LIQUIDITY`
  - `FAKE_BREAKOUT`
  - `INVALID_ENTRY`
  - `LOW_RR`
  - `LOW_FINAL_SCORE`
  - `AI_REJECTED`
  - `DUPLICATE`
  - `COOLDOWN`
  - `STALE_DATA`
  - `DATA_SOURCE_FAILURE`
  - `OTHER`
- Each rejection records one primary code.
- Added `SIGNAL_QUALITY_PROFILE=conservative|balanced|strict`.
- Default is `conservative`, preserving existing production thresholds.
- `MAX_DYNAMIC_SYMBOLS=120` and `SINGLE_SYMBOL_MODE=false` remain the default behavior.

### Admin Diagnostics

Updated:

- `trader_app/blueprints/routes.py`

Changes:

- `/admin/signal-supply` now displays:
  - Crypto diagnostics.
  - Rejection reason code counters.
  - Forex diagnostics.
  - Forex auto-trade status.

## New Environment Variables

Add to Railway only if Forex data should run:

```env
FOREX_SIGNAL_ENGINE_ENABLED=true
FOREX_DATA_PROVIDER=twelvedata
FOREX_DATA_API_KEY=your_forex_data_api_key
FOREX_REQUEST_TIMEOUT_SECONDS=8
FOREX_REQUEST_RETRIES=2
FOREX_CACHE_SECONDS=180
FOREX_MAX_CANDLE_STALE_SECONDS=1800
FOREX_MIN_RISK_REWARD=1.5
FOREX_MIN_CONFIDENCE=72
FOREX_MAX_SPREAD_PIPS=2.5
FOREX_MAX_SIGNALS_PER_CYCLE=2
FOREX_NEWS_BLACKOUT_ENABLED=true
FOREX_NEWS_BLACKOUT_ACTIVE=false
FOREX_AUTO_TRADE_ENABLED=false
SIGNAL_QUALITY_PROFILE=conservative
```

## Safety Notes

- No crypto strategy was rewritten.
- No Entry/TP/SL crypto formula was changed.
- No payment logic was touched.
- No Telegram linking logic was touched.
- No AdsGram or Free Earn security was touched.
- Forex auto-trade is still disabled.
- No fake customer or production signal data was added.

## Validation

New diagnostic:

- `scripts/diagnose_forex_engine_and_signal_supply.py`

It verifies:

- Forex data does not produce fake candles without an API key.
- Forex symbol normalization and pip sizes.
- Forex analyzer can build a correctly shaped Forex signal from deterministic fixture candles.
- Forex routing requires `vip_all_forex`.
- `vip_all_forex` does not automatically grant crypto delivery.
- Crypto rejection code counters work.
- Default crypto quality profile remains conservative.

## Why Crypto May Still Show No Signals

This phase does not relax the crypto strategy, Entry/TP/SL formulas, or hard safety filters. If production logs still show no crypto signals, the admin diagnostics now identify the dominant rejection code, such as `LOW_VOLATILITY`, `MTF_CONFLICT`, `LOW_LIQUIDITY`, `FAKE_BREAKOUT`, `INVALID_ENTRY`, or `LOW_FINAL_SCORE`.

That means no-signal periods remain possible by design when the market does not pass the existing quality gates.

## Test Results

Executed locally on July 15, 2026:

- `python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py forex_analyzer.py trader_app\services\forex_market_data.py` passed.
- `python -m compileall -q trader_app` passed.
- `python .\scripts\diagnose_forex_engine_and_signal_supply.py` passed with `FOREX_ENGINE_AND_SIGNAL_SUPPLY_OK`.
- `python .\scripts\smoke_routes.py` passed with `OK: 24 routes passed`.
- `pytest -q` passed with `11 passed, 1 warning`.
- `git diff --check` passed. Git only reported CRLF normalization warnings for existing working-copy behavior.

## Parts Not Yet Production Ready

- Forex data requires a real provider key in `FOREX_DATA_API_KEY`.
- Forex auto-trade is intentionally disabled.
- `FOREX_NEWS_BLACKOUT_ACTIVE` is a safe manual/runtime switch, not a live economic-calendar integration.
- Non-Bybit auto-trade execution remains outside this phase.
