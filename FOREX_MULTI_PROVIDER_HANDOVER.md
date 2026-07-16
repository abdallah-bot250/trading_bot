# Nexora Forex Multi-Provider Handover

## Architecture

Nexora Forex now uses a provider manager instead of depending on one broker/data vendor.

Main module:

- `trader_app/services/forex_provider_manager.py`

Compatibility facade:

- `trader_app/services/forex_market_data.py`

The analyzer still calls the same market-data functions, but those calls now route through the manager.

## Provider Priority

Default priority:

1. Twelve Data
2. Finnhub, optional future/secondary provider
3. OANDA REST v20, optional only
4. Future providers

If a configured provider fails, the manager attempts the next configured provider automatically.

## Railway Variables

Minimum required for Forex market data:

```env
FOREX_DATA_PROVIDER=twelvedata
TWELVEDATA_API_KEY=your_twelvedata_api_key
```

Minimum required for news safety:

```env
FOREX_REQUIRE_NEWS_CALENDAR=true
FOREX_NEWS_PROVIDER=tradingeconomics
TRADING_ECONOMICS_API_KEY=your_tradingeconomics_api_key
TRADING_ECONOMICS_API_SECRET=your_tradingeconomics_api_secret
```

Optional OANDA REST v20 enhancement:

```env
OANDA_API_TOKEN=your_oanda_api_token
OANDA_ACCOUNT_ID=your_oanda_account_id
OANDA_ENVIRONMENT=practice
```

If OANDA variables are missing, Nexora logs/diagnoses `OANDA_PROVIDER_DISABLED` and continues with Twelve Data.

## Spread Logic

Twelve Data may provide OHLC/price without executable bid/ask.

Nexora does not fabricate spread.

If bid/ask are unavailable:

```text
Spread: Unavailable
```

The signal can still be evaluated with candles, price, risk/reward, and Trading Economics news checks.

If OANDA is configured and used, it can provide bid/ask/spread and improve execution-quality diagnostics.

## Production Delivery Safety

Candles and executable pricing are separate lanes:

- `candle_provider` can be Twelve Data.
- `pricing_provider` must be a provider with real bid/ask, such as OANDA REST v20.
- `news_provider` remains Trading Economics.

In shadow mode, Nexora may build and log a Forex candidate from real Twelve Data candles even when spread is unavailable. It does not deliver that candidate to users as a paid signal.

In production, when:

```env
FOREX_REQUIRE_REAL_SPREAD=true
FOREX_PRODUCTION_MODE=true
FOREX_SHADOW_MODE=false
```

Forex delivery is blocked unless there is:

- real bid
- real ask
- real spread
- fresh pricing timestamp

If those are missing, the rejection reason is:

```text
REAL_SPREAD_UNAVAILABLE
```

No spread is estimated from high/low, ATR, candle range, or any synthetic formula.

## News Provider

Trading Economics remains responsible for:

- high-impact news
- medium-impact news
- event blackout windows

If `FOREX_REQUIRE_NEWS_CALENDAR=true` and Trading Economics is not configured, Forex signals fail closed.

## Admin Readiness

`/admin/production-readiness` now reports:

- Primary Provider: Twelve Data
- Secondary Provider: OANDA, optional
- News: Trading Economics
- Provider Healthy

It no longer treats OANDA as required.

## Files Modified

- `.env.example`
- `ENVIRONMENT_VARIABLES.md`
- `FOREX_MULTI_PROVIDER_HANDOVER.md`
- `auto_sender.py`
- `forex_analyzer.py`
- `scripts/diagnose_forex_provider_manager.py`
- `trader_app/blueprints/routes.py`
- `trader_app/services/forex_market_data.py`
- `trader_app/services/forex_provider_manager.py`

## Diagnostics

Run:

```bash
python scripts/diagnose_forex_provider_manager.py
```

Expected success marker:

```text
FOREX_PROVIDER_MANAGER_OK
```

## Test Results

Record the latest production/package test run here before handover:

- `python scripts/diagnose_forex_provider_manager.py`
- `python scripts/smoke_routes.py`
- `python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py forex_analyzer.py`
- `git diff --check`

No Crypto Engine, Telegram delivery, payment, subscription, or login logic is changed by this architecture.
