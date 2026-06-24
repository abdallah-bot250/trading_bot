# Nexora Trader Production Hardening Report

This patch focuses on reliability and sale-readiness without changing the public brand or core routes.

## Fixed / improved

1. **Signal tracking**
   - Added `signal_log` table creation in the worker.
   - Every successfully delivered Telegram signal is now tracked with pair, direction, type, entry, TP, SL, confidence, plan, and status.
   - Added TP/SL outcome monitoring for sent signals, not only auto-executed trades.
   - Users can receive Telegram updates when a tracked signal hits TP or SL.

2. **Auto-trading reliability**
   - Added configurable `AUTO_TRADE_EXCHANGE` environment variable.
   - Default remains Binance for backwards compatibility.
   - Optional spot execution exchange support for `kucoin` and `binanceus` was added with clear safety errors for unsupported futures execution.
   - Auto-trading now fails safely with explicit logs when the chosen exchange cannot execute the requested trade type.

3. **Market data cleanup**
   - Removed unsupported `XAUSDT` from scanner symbols to reduce noisy KuCoin/Binance errors.
   - Binance / Binance US / KuCoin market-data fallback remains intact.

4. **Plans and subscriptions**
   - Unified the SQLAlchemy model and migration plan check constraint to support only:
     `trial`, `basic`, `pro`, `vip`, `pro_2y`.
   - Removed `lifetime` from plan constraints and upgrade scripts.
   - Kept `lifetime_owner` column only for backward compatibility with old databases; it is no longer exposed as a sellable plan.
   - Disabled the old owner lifetime upgrade endpoint by default.

5. **Admin security cleanup**
   - Admin access no longer depends on `lifetime_owner`; it requires the DB admin flag and the configured `ADMIN_EMAIL`.
   - Removed commercial UI buttons that exposed lifetime-style owner upgrades.

6. **Custom domain hardening**
   - Added legacy-domain redirect support.
   - Requests coming to `web-production-c6a34.up.railway.app` redirect to `BASE_URL` / `CANONICAL_DOMAIN`.
   - This keeps old Railway links, Telegram links, and browser bookmarks aligned with `https://nexoratrader.net` when Railway Variables are set correctly.

7. **Release hygiene**
   - Cleaned generated Python cache files from the release package.
   - The release ZIP excludes `.git`, `__pycache__`, `*.pyc`, logs, and PID files.

## Required Railway variables to review

- `BASE_URL=https://nexoratrader.net`
- `CANONICAL_DOMAIN=https://nexoratrader.net`
- `LEGACY_DOMAINS=web-production-c6a34.up.railway.app`
- `BOT_LINK=https://t.me/<your_bot_username>`
- `TELEGRAM_TOKEN=<real token>`
- `DATABASE_URL=<Railway Postgres URL>`
- `FERNET_KEY=<valid Fernet key>`
- `NOWPAYMENTS_API_KEY=<real key>`
- `NOWPAYMENTS_IPN_SECRET=<real secret>`
- Optional: `AUTO_TRADE_EXCHANGE=binance` (default), `kucoin`, or `binanceus`

## Important operational note

KuCoin fallback is for market data and optional spot auto-trading only if the user supplies KuCoin-compatible API keys and `AUTO_TRADE_EXCHANGE=kucoin` is configured. Futures auto-execution remains Binance-only in this build.

## Validation performed

- Python syntax compilation passed for all `.py` files in the package.
- Full Flask route smoke test could not be executed in this container because Flask is not installed in the execution environment.
