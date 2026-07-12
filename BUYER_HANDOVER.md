# Buyer Handover

## Handover Steps
1. Transfer GitHub repository or provide ZIP source package.
2. Transfer domain/DNS or point buyer domain to Railway.
3. Rotate all secrets in Railway Variables.
4. Transfer Telegram bot ownership or create a new bot and update `TELEGRAM_TOKEN` and `BOT_LINK`.
5. Configure NOWPayments and IPN secret.
6. Configure AdsGram reward URL.
7. Review `/auto-trade` and `/admin/auto-trade-monitor`.
8. Add buyer-owned exchange API keys with withdrawal permissions disabled.
9. Run diagnostics and smoke routes.
10. Test register, login, payment, Telegram linking, Free Earn unlock, dashboard metrics, and auto-trade safety checks.

## Secret Rotation
- Generate new `SECRET_KEY`.
- Generate new `FERNET_KEY`.
- Replace Telegram token if bot ownership changes.
- Rotate NOWPayments API/IPN secrets.
- Rotate database password.
- Remove seller accounts unless buyer explicitly keeps them.
- Revoke and recreate all exchange API keys after transfer. API keys should be futures-only where possible, IP-restricted where possible, and never include withdrawal permission.

## Auto Trade Handover
- Bybit futures is the primary production-ready execution path.
- Binance, OKX, Bitget, KuCoin, Gate.io, and MEXC are presented through the connection layer for testing/monitoring until execution protection is fully verified per exchange.
- Spot auto trade remains disabled by default because spot execution requires safe OCO/bracket protection.
- The buyer should activate `Emergency Stop` before rotating exchange keys, then re-enable only after test connection passes.

## Disclaimer
The product contains trading automation and signal delivery code. The buyer must test with their own accounts and accepts market risk.
