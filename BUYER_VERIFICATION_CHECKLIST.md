# Buyer Verification Checklist

## Website
- [ ] Landing page loads.
- [ ] Register works.
- [ ] Login works.
- [ ] Dashboard opens.
- [ ] Dashboard shows N/A for unavailable real metrics, not fake ROI/win-rate values.
- [ ] Payment pages open.
- [ ] Manual payment page opens.

## Telegram
- [ ] Bot `/start` works.
- [ ] Website account links to Telegram.
- [ ] Free user receives configured free lifetime signals only.
- [ ] Free Earn locked signal opens unlock page.
- [ ] AdsGram reward callback unlocks only mapped tokens.
- [ ] Paid user receives eligible signals directly.

## Admin
- [ ] Admin dashboard opens.
- [ ] `/admin/sale-readiness` opens for admin.
- [ ] Product feature monitor opens.
- [ ] Pro 2Y constraint repair button is visible if needed.

## Trading Proof
- [ ] Signal logs are recorded after successful Telegram send.
- [ ] Closed outcomes use live market data.
- [ ] No profit guarantee appears in sales docs.

## Security
- [ ] All secrets rotated.
- [ ] Railway variables match `ENVIRONMENT_VARIABLES.md`.
- [ ] Production `.env` is not included in the sale package.
