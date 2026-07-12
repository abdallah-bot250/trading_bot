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
