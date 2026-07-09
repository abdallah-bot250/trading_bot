# Buyer Handover

## Handover Steps
1. Transfer GitHub repository or provide ZIP source package.
2. Transfer domain/DNS or point buyer domain to Railway.
3. Rotate all secrets in Railway Variables.
4. Transfer Telegram bot ownership or create a new bot and update `TELEGRAM_TOKEN` and `BOT_LINK`.
5. Configure NOWPayments and IPN secret.
6. Configure AdsGram reward URL.
7. Run diagnostics and smoke routes.
8. Test register, login, payment, Telegram linking, Free Earn unlock, and dashboard metrics.

## Secret Rotation
- Generate new `SECRET_KEY`.
- Generate new `FERNET_KEY`.
- Replace Telegram token if bot ownership changes.
- Rotate NOWPayments API/IPN secrets.
- Rotate database password.
- Remove seller accounts unless buyer explicitly keeps them.

## Disclaimer
The product contains trading automation and signal delivery code. The buyer must test with their own accounts and accepts market risk.
