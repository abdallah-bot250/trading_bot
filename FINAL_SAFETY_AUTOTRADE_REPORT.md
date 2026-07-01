# Nexora Final Safety + Auto Trade Patch

## Scope
This patch keeps the adaptive signal engine intact and adds execution safety + Bybit-ready auto trading support.

## What changed
- Default auto-trade exchange is now `bybit` via `AUTO_TRADE_EXCHANGE`.
- Added Bybit symbol normalization for USDT-margined futures, e.g. `BTCUSDT` -> `BTC/USDT:USDT`.
- Added Bybit market order submission with TP/SL params for futures.
- Preserved Binance/BinanceUS/KuCoin compatibility via `AUTO_TRADE_EXCHANGE`.
- Added stale/chased-entry rejection before Telegram sending and before auto execution.
- Signals are rejected if price already hit TP/SL or moved too far from entry.
- Market analysis uses closed candles only to reduce repainting/stale entries.
- Auto trade respects user Spot/Futures Auto Trading toggles.
- Dashboard copy now explains Bybit-ready auto trading and API safety.
- Landing page plan copy now mentions Bybit-ready auto trading controls for eligible plans.
- Fixed dashboard chart serialization issue from previous patch.

## Recommended Railway/Render variables
```
AUTO_TRADE_EXCHANGE=bybit
SIGNAL_DEBUG_LOGS=false
MAX_ENTRY_DEVIATION_PERCENT=0.35
ENTRY_CHASE_TOLERANCE_PERCENT=0.18
MAX_DYNAMIC_SYMBOLS=40
```

## Safety note
Use Bybit API keys with trading permission only. Keep withdrawal permission disabled.

## Tests run in this environment
- `python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py` passed.
- `python scripts/diagnose_adaptive_engine.py` passed.
- `scripts/smoke_routes.py` could not run here because Flask is not installed in the sandbox environment.
