# Manual Payment Page Polish

## What changed

- Rebuilt `templates/manual_payment.html` as a premium payment desk.
- Added separate professional cards for Binance, ADCB Bank, and InstaPay.
- Added copy buttons for wallet, bank details, and InstaPay handle.
- Added plan summary with current price, crossed original price, discount percent, and limited-time offer badge.
- Added proof submission section and safety/trust section.
- Kept manual activation behavior: manual payment does not auto-activate subscriptions.
- Kept all routes, payment logic, and admin flow unchanged.

## Files changed

- `templates/manual_payment.html`
- `trader_app/blueprints/routes.py`

## Notes

The page uses local CSS and existing project assets. It does not require external APIs or new dependencies.
