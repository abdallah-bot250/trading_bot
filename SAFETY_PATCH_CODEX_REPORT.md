# Nexora Safety Patch Report — 2026-07-04

This patch was applied to the user's latest uploaded project: `nexora_trading_bot_backup_current_20260704_170005.zip`.

## Files changed

- `auto_sender.py`
- `trader_app/config.py`
- `trader_app/blueprints/routes.py`
- `tests/test_safety_autotrade.py`
- `SAFETY_PATCH_CODEX_REPORT.md`

## What changed

### 1. Spot auto-trading is disabled by default

Spot signals still work. Spot auto-execution is blocked unless `ENABLE_SPOT_AUTO_TRADE=true` is explicitly set.

Reason: current Spot execution does not create a guaranteed OCO/bracket exit. Marketing can mention Spot signals, but not safe fully automated Spot trading yet.

### 2. Position size now uses real stop-loss risk

Old logic used risk capital as notional size:

```python
amount = (balance * risk_percent) / entry_price
```

New logic uses actual SL distance:

```python
risk_usdt = balance * risk_percent
loss_per_unit = abs(entry - stop_loss)
amount = risk_usdt / loss_per_unit
```

It also caps the order notional using `MAX_AUTO_TRADE_NOTIONAL_PERCENT` defaulting to `0.95`.

### 3. Emergency close added

If an order is submitted but protection/fill validation fails, the bot attempts an immediate opposite market close.

For Futures, close orders use `reduceOnly=True`.

### 4. Unprotected trades are not recorded as OPEN

If TP/SL protection fails, the trade is rejected, emergency close is attempted, and the DB does not insert the trade as `OPEN`.

### 5. Production SECRET_KEY hardening

In production, startup fails if `SECRET_KEY` is missing or uses weak defaults like:

- `secret`
- `change_this_secret_key`
- `your_secret_key`

Development still gets a dev-only fallback.

### 6. Dashboard save-settings safety

Even if the Spot auto-trade checkbox is posted, it is forced OFF unless `ENABLE_SPOT_AUTO_TRADE=true` exists in env.

## Env vars added

```env
ENABLE_SPOT_AUTO_TRADE=false
MAX_AUTO_TRADE_NOTIONAL_PERCENT=0.95
```

## Tests added

`tests/test_safety_autotrade.py` covers:

- stop-loss-based sizing
- missing/invalid SL rejection
- emergency futures close uses opposite side and `reduceOnly=True`

## Remaining work before marketing as full auto-trading platform

- Implement real Spot OCO/bracket support before enabling Spot auto-trading.
- Add exchange reconciliation job.
- Verify Bybit TP/SL attachment behavior in live/testnet.
- Add full backtesting and paper trading before comparing directly to Cryptohopper.
