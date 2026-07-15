# Post Deploy Signal Supply Fix Report

Date: 2026-07-15

## Scope

This fix targets production signal supply diagnostics after commit `3bc1faa`.

No changes were made to:

- Entry / TP / SL formulas
- Trading strategy thresholds
- Payment flow
- Login / Register
- Telegram paid signal formatting
- AdsGram / Free Earn reward security
- Auto-trade execution logic

## 1. Dynamic Crypto Universe

### Problem

Production logs showed:

```text
DYNAMIC_SYMBOLS_SELECTED count=1
```

while Binance US `exchangeInfo` had many valid symbols but ticker/volume data returned only one match.

### Fix

- Added `MIN_DYNAMIC_SYMBOLS=20`.
- `get_scan_symbols()` now keeps valid symbols from `exchangeInfo` even when ticker/quote-volume data is incomplete.
- Valid exchange-info symbols are ranked conservatively:
  - high-volume matched symbols first
  - then approved supported symbols from exchange info
  - no unavailable Binance US symbols are invented
- If the final count is below `MIN_DYNAMIC_SYMBOLS`, supported fallback symbols are merged without duplicates.
- Added structured log fields:
  - `exchange_info_count`
  - `ticker_count`
  - `matched_count`
  - `fallback_added_count`
  - `final_count`

### Diagnostic

`scripts/diagnose_forex_engine_and_signal_supply.py` verifies:

- Binance global failure + Binance US exchangeInfo=28 + ticker=1 returns at least 20 valid scan symbols.

## 2. Forex Provider Diagnostics

### Problem

Production logs showed repeated failures:

```text
FOREX_SCAN_SUMMARY symbols_scanned=16 timeframes_scanned=16 data_failures=16
```

without a clear reason.

### Fix

- Added structured Forex failure codes:
  - `PROVIDER_NOT_CONFIGURED`
  - `API_KEY_MISSING`
  - `AUTH_FAILED`
  - `RATE_LIMITED`
  - `SYMBOL_NOT_SUPPORTED`
  - `TIMEFRAME_NOT_SUPPORTED`
  - `TIMEOUT`
  - `HTTP_ERROR`
  - `EMPTY_CANDLES`
  - `STALE_DATA`
  - `PARSE_ERROR`
- Added `provider_configuration_status()`.
- If Forex provider is not configured, Forex scanning is disabled cleanly instead of producing noisy per-symbol failures.
- Logs now include provider and reason only, never secrets or response bodies.
- Added startup/scan log:

```text
FOREX_PROVIDER_STATUS provider=... configured=true/false reason=...
```

- `FOREX_SCAN_SUMMARY` now separates:
  - `symbols_requested`
  - `symbols_with_data`
  - `requests_failed`
  - `failure_reasons`
  - `disabled`
  - `disabled_reason`

### Diagnostic

Added:

- `scripts/diagnose_forex_provider_probe.py`

Expected output when API key is not configured:

```text
FOREX_PROVIDER_PROBE provider=twelvedata configured=false reason=API_KEY_MISSING ...
FOREX_PROVIDER_PROBE_OK
```

## 3. Rejection Counters

### Problem

Rejection counters could overlap because classification used broad substring matching.

### Fix

- Rejection classification now returns one primary reason code per attempt.
- Broad `ENTRY` matching was removed to avoid false positives.
- `FAKE_BREAKOUT`, `INVALID_ENTRY`, `LOW_LIQUIDITY`, and `MTF_CONFLICT` are classified with more precise markers.
- Added:
  - `scan_attempts`
  - `unique_symbols_scanned`
- Summary logs now include both unique symbols and attempts.

### Diagnostic

`scripts/diagnose_post_deploy_signal_supply_fix.py` verifies that:

- A rejection maps to one primary reason.
- Total rejection counters do not exceed scan attempts.

## 4. No-Signal Telegram Spam Control

### Problem

No-signal/warning messages could repeat too often and Telegram 403 users could be retried every cycle.

### Fix

- Added `NO_SIGNAL_NOTIFY_COOLDOWN_HOURS=6`.
- Added persistent `notification_state` table via safe `CREATE TABLE IF NOT EXISTS`.
- Added idempotency key per:
  - chat_id
  - plan
  - no-signal state
- No-signal messages are sent only when cooldown expires or market state changes.
- Users without `chat_id` are skipped.
- Users with `bot_active != 1` are skipped.
- Telegram 400/403 blocked/deactivated responses now mark:

```sql
users.bot_active = 0
```

without crashing the cycle.

## 5. Tests Run

Passed:

```text
python -m compileall -q trader_app
python scripts/diagnose_post_deploy_signal_supply_fix.py
python scripts/diagnose_forex_engine_and_signal_supply.py
python scripts/diagnose_forex_provider_probe.py
python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py forex_analyzer.py
git diff --check
```

Notes:

- `scripts/smoke_routes.py` could not run in the available local test venv because Flask is not installed:

```text
ModuleNotFoundError: No module named 'flask'
```

- `pytest -q` could not run because pytest is not installed:

```text
No module named pytest
```

- Attempts to install dependencies from `requirements.txt` timed out in the local sandbox. This is an environment limitation, not a code failure.

## 6. Environment Variables Added

```env
MIN_DYNAMIC_SYMBOLS=20
NO_SIGNAL_NOTIFY_COOLDOWN_HOURS=6
```

## 7. Production Safety

- No signal quality reduction was introduced.
- No random signal generation was introduced.
- Forex scan does not fake data.
- Forex auto-trade remains disabled.
- Telegram no-signal messages are not logged as trading signals.
- Telegram 403 blocked users are cooled down by deactivating bot delivery.

