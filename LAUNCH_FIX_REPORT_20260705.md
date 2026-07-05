# Nexora Launch Fix Report — 2026-07-05

## Changes made
- Activated the AdsGram rewarded-video SDK on the locked-signal page.
- The unlock button now verifies the Telegram Mini App user, binds that user to the locked signal, initializes AdsGram block `37291`, and calls the rewarded ad `show()` flow.
- Preserved the existing server-side reward callback, anti-replay checks, token ownership checks, expiry checks, and stale-signal credit behavior.
- Changed `STRICT_VOLATILITY_FILTER` default to `false`. This only relaxes the LOW_VOLATILITY hard block for large-cap symbols through the existing guarded path; MTF conflict, fake breakout, low-volume chop, liquidity, quality, RR, professional entry, freshness, and plan checks remain active.
- Added launch-ready environment examples for Free Earn and AdsGram.

## Safety decision
No forced signal target was enabled. `MIN_DAILY_SIGNAL_TARGET=0` remains diagnostic-only. The system is not allowed to invent trades to hit a quota.

## Validation
- `python scripts/smoke_routes.py`: OK, 24 routes passed.
- `python -m py_compile app.py ai_model.py auto_sender.py market_analyzer.py trade_tracker.py`: OK.
- `python scripts/diagnose_adaptive_engine.py`: ADAPTIVE_DIAGNOSTICS_OK.
- Launch patch assertions: LAUNCH_PATCH_OK.

## Production environment
STRICT_VOLATILITY_FILTER=false
MIN_DAILY_SIGNAL_TARGET=0
FREE_EARN_MODE=true
FREE_SIGNALS_LIFETIME=2
LOCKED_SIGNAL_TTL_MINUTES=10
REWARDED_AD_PROVIDER=adsgram
ADSGRAM_PLATFORM_ID=35044
ADSGRAM_BLOCK_ID=37291
ADSGRAM_REQUIRE_SIGNATURE=false
FREE_UNLOCK_DEMO_MODE=false
