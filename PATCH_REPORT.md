# Nexora Company v3 Patch Report

## Changes applied

1. Removed public Lifetime subscription offering
   - Removed Lifetime card from pricing/dashboard/admin controls.
   - Removed Lifetime from active plan price dictionaries.
   - Kept internal `lifetime_owner` database column untouched for backward compatibility only.

2. Fixed Pro 2 Years plan
   - Plan ID remains: `pro_2y`.
   - Duration remains: 730 days / 2 years.
   - Real price: `$999`.
   - Display comparison price: `$1499`.
   - Updated dashboard and landing pricing displays.

3. Automatic payment behavior
   - NOWPayments webhook keeps automatic activation for paid invoices.
   - Manual payments remain admin-activated from `/admin` only.

4. Manual payment
   - Binance USDT TRC20 wallet, ADCB bank details, and InstaPay handle remain in manual payment page.
   - Manual payment button remains marked: `Manual Payment - No Fees`.

5. Telegram signals / exchange fallback
   - KuCoin fallback remains enabled in `auto_sender.py` when Binance/Binance US fail.
   - Auto trading plan gate now includes Elite and Pro 2 Years only.

6. Safety
   - Python cache files removed from output package.
   - Code compile check passed for core Python files.

## Notes

- Smoke route test could not be executed inside this sandbox because Flask is not installed here.
- Run on your machine or Railway after copy:
  `python scripts/smoke_routes.py`

