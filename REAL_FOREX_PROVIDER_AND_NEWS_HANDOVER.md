# Legacy Forex Provider And News Handover

This document is kept only for historical context from the earlier OANDA-first
implementation.

The current production design is now documented in:

- `FOREX_MULTI_PROVIDER_HANDOVER.md`

Current architecture:

- Primary candle / market analysis provider: Twelve Data.
- Optional real bid/ask pricing provider: OANDA REST v20.
- News provider: Trading Economics.
- No fake spread, bid, ask, candles, or news events are generated.

Production safety:

- Shadow mode may build theoretical Forex candidates from Twelve Data candles.
- Paid Forex delivery in production should use `FOREX_REQUIRE_REAL_SPREAD=true`.
- With real spread required, delivery is blocked unless a pricing provider
  supplies real bid, ask, spread, and a fresh pricing timestamp.

Run:

```bash
python scripts/diagnose_forex_provider_manager.py
```

Expected marker:

```text
FOREX_PROVIDER_MANAGER_OK
```
