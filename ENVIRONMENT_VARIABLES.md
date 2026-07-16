# Environment Variables

## Core
- `SECRET_KEY`
- `FERNET_KEY`
- `DATABASE_URL`
- `BASE_URL`
- `CANONICAL_DOMAIN`
- `ADMIN_EMAIL`

## Telegram
- `TELEGRAM_TOKEN`
- `BOT_LINK`
- `ADMIN_TELEGRAM_ID`

## Payments
- `NOWPAYMENTS_API_KEY`
- `NOWPAYMENTS_IPN_SECRET`
- `MANUAL_PAYMENT_WALLET`
- `MANUAL_PAYMENT_NETWORK`

## VIP ALL FOREX
- `VIP_ALL_FOREX_PRICE` - monthly NOWPayments price, default `150`.
- `VIP_ALL_FOREX_ORIGINAL_PRICE` - monthly crossed-out/reference price, default `299`.
- `VIP_ALL_FOREX_DAYS` - monthly subscription duration in days, default `30`.
- `VIP_ALL_FOREX_YEARLY_PRICE` - yearly NOWPayments price, default `1250`.
- `VIP_ALL_FOREX_YEARLY_ORIGINAL_PRICE` - yearly crossed-out/reference price, default `1800`.
- `VIP_ALL_FOREX_YEARLY_DAYS` - yearly subscription duration in days, default `365`.

## Forex Production Data
- `FOREX_SIGNAL_ENGINE_ENABLED` - enable the Forex signal scanner.
- `FOREX_DATA_PROVIDER` - default `twelvedata`; use `auto` for priority-based fallback or `oanda` only when REST v20 credentials are available.
- `TWELVEDATA_API_KEY` - required primary market-data key for global Forex/metal/index candle and price data.
- `FOREX_DATA_API_KEY` - legacy alias for `TWELVEDATA_API_KEY`.
- `OANDA_API_TOKEN` - optional OANDA v20 API token. Never log or expose it.
- `OANDA_ACCOUNT_ID` - optional OANDA account id. Never expose it in UI.
- `OANDA_ENVIRONMENT` - optional; `practice` first, `live` only after shadow validation.
- `OANDA_API_BASE_URL` - optional practice URL: `https://api-fxpractice.oanda.com`.
- `OANDA_STREAM_BASE_URL` - optional practice stream URL: `https://stream-fxpractice.oanda.com`.
- `FOREX_REQUIRE_REAL_SPREAD` - default `false` for shadow evaluation; set `true` before production Forex delivery. Twelve Data may not provide bid/ask, so spread is shown as `Unavailable` instead of being fabricated.
- `FOREX_REQUIRE_NEWS_CALENDAR` - keep `true`; unavailable calendar fails closed.
- `FOREX_PRODUCTION_MODE` - keep `false` until readiness passes.
- `FOREX_SHADOW_MODE` - keep `true` during practice/shadow evaluation.
- `FOREX_AUTO_TRADE_ENABLED` - keep `false`; Forex auto execution is not production-enabled.
- `FOREX_REQUIRE_DATA_RECONCILIATION` - optional strict secondary-provider price check.
- `FOREX_PRICE_DIVERGENCE_THRESHOLD_PIPS` - max OANDA vs reference divergence.
- `TRADING_ECONOMICS_API_KEY` and `TRADING_ECONOMICS_API_SECRET` - real calendar credentials.
- `FOREX_NEWS_HIGH_BEFORE_MINUTES` / `FOREX_NEWS_HIGH_AFTER_MINUTES` - high-impact news block window.
- `FOREX_NEWS_MEDIUM_BEFORE_MINUTES` / `FOREX_NEWS_MEDIUM_AFTER_MINUTES` - medium-impact news block window.

## Free Earn / AdsGram
- `FREE_EARN_MODE`
- `FREE_SIGNALS_LIFETIME`
- `LOCKED_SIGNAL_TTL_MINUTES`
- `REWARDED_AD_PROVIDER`
- `ADSGRAM_PLATFORM_ID`
- `ADSGRAM_BLOCK_ID`
- `ADSGRAM_REWARD_SECRET`
- `ADSGRAM_REQUIRE_SIGNATURE`
- `FREE_UNLOCK_DEMO_MODE`

## Signal Diagnostics
- `SIGNAL_DEBUG_LOGS`
- `STRICT_VOLATILITY_FILTER`
- `MIN_DAILY_SIGNAL_TARGET`
- `NEXORA_PROOF_MODE`
- `ENABLE_SIGNAL_TRACKING`
- `SIGNAL_TRACKING_NOTIFY`

## Multi-Exchange Auto Trade
- `AUTO_TRADE_EXCHANGE` - legacy fallback exchange, usually `bybit`.
- `ENABLE_SPOT_AUTO_TRADE` - keep `false` unless protected OCO/bracket exits are implemented and verified.
- `MAX_AUTO_TRADE_NOTIONAL_PERCENT`
- `MAX_ENTRY_DEVIATION_PERCENT`
- `ENTRY_CHASE_TOLERANCE_PERCENT`
- `MAX_TP1_PROGRESS_PERCENT`

Exchange API keys should be added by users through `/auto-trade`. Production secrets must not be stored in `.env.example`.

Never commit production `.env` values.
