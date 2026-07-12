# Nexora AI Trader - Sale README

Nexora AI Trader is a production-oriented Flask + Telegram crypto signal SaaS package with subscription access, referral tracking, rewarded-ad unlocks for free users, and sale-ready buyer documentation.

## What Is Included

- Flask website with landing page, login/register, dashboard, admin panel, payments, proof, bot check, and product feature pages.
- Telegram bot onboarding, account linking, referral messaging, subscription status, admin broadcasts, and signal delivery.
- Adaptive signal pipeline with diagnostics, B+ qualified opportunity calibration, and strict no-random-trade safeguards.
- Free Earn V2: free users receive the configured lifetime free signals, then unlock eligible premium signals through AdsGram rewarded ads.
- NOWPayments automatic invoices plus manual payment support.
- Referral / affiliate tracking with website-first referral links.
- Real dashboard metrics from `signal_log` and `trades_log`; insufficient history displays honest empty states instead of fake ROI or win-rate numbers.
- Professional multi-exchange auto-trade layer with encrypted API storage, connection testing, emergency stop, risk profile settings, and execution logging. Bybit futures is production-ready; additional exchanges are available for monitored connection/testing until exchange-specific execution protection is verified.

## Not Included

- No guarantee of profit.
- No financial advice.
- No buyer-owned secrets, API keys, Telegram token, payment keys, or database credentials.
- No guaranteed ad revenue. AdsGram must be configured and approved by the buyer.

## Buyer Verification Checklist

- Open `/health`.
- Register and login with a test user.
- Link Telegram through `/bot-check` or dashboard Connect Telegram flow.
- Confirm `/webhook` returns 200/204 and Telegram receives `/start`.
- Confirm Free Earn mode creates a locked signal only after the free lifetime allowance is used.
- Confirm AdsGram reward URL is configured as `/adsgram/reward?user_id=[userId]`.
- Confirm paid users receive eligible final signals directly.
- Confirm dashboard metrics show N/A until real tracked outcomes exist.
- Confirm `/admin/sale-readiness` is accessible to admin only.
- Confirm `/auto-trade` shows the multi-exchange wizard and `/admin/auto-trade-monitor` shows execution diagnostics.
- Confirm Spot Auto Trade remains disabled unless protected exits are deliberately implemented and tested.

## Sale Notes

Pricing is intentionally not hardcoded in this document. The seller and buyer should agree on price, included accounts, handover schedule, and post-sale support separately.

## Risk Disclaimer

Crypto trading is risky. Signals are decision-support alerts, not guaranteed outcomes. Past results do not guarantee future performance.
