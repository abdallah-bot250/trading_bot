import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("BASE_URL", "https://nexoratrader.net")

from trader_app.services.plan_catalog import PLAN_CATALOG, checkout_url, public_plans_by_market
from trader_app.services.telegram import should_show_plans_for_text, subscription_message, telegram_plans_payload


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def _buttons(markup):
    return sum((row for row in markup["inline_keyboard"]), [])


def main():
    text_en, markup_en = telegram_plans_payload(None, chat_id="123", lang="en", view="all")
    text_ar, markup_ar = telegram_plans_payload(None, chat_id="123", lang="ar", view="all")
    text_forex, _ = telegram_plans_payload(None, chat_id="123", lang="en", view="forex")
    text_compare, _ = telegram_plans_payload(None, chat_id="123", lang="en", view="compare")

    assert_true("VIP ALL FOREX" in text_en, "/start or /plans must show VIP ALL FOREX")
    assert_true("Basic" in text_en and "Pro" in text_en, "Crypto plans must be visible")
    assert_true("$150" in text_en and "$1250" in text_en, "Telegram prices must match catalog defaults")
    assert_true("Forex Auto Trade: Not available" in text_forex, "Forex Auto Trade must be marked unavailable")
    assert_true("Oil" not in text_forex and "indices" not in text_forex.lower(), "Unsupported oil/indices must not be advertised as supported")
    assert_true("Trading is risky" in text_en or "do not guarantee profit" in text_en, "Disclaimer must be present")
    assert_true("Crypto covers" in text_compare and "VIP ALL FOREX" in text_compare, "Compare plans must explain Crypto vs Forex")

    hidden = [p for p in public_plans_by_market() if not p.get("publicly_visible")]
    assert_true(not hidden, "Hidden plans must not appear in public plans")

    assert_true(should_show_plans_for_text("/plans"), "/plans should trigger plans")
    assert_true(should_show_plans_for_text("/subscribe"), "/subscribe should trigger plans")
    assert_true(should_show_plans_for_text("الخطط"), "Arabic plan keyword should trigger plans")
    assert_true(should_show_plans_for_text("Forex prices"), "Forex keyword should trigger plans")
    assert_true(should_show_plans_for_text("Crypto plans"), "Crypto keyword should trigger plans")

    urls = [button.get("url", "") for button in _buttons(markup_en) if button.get("url")]
    assert_true(any("/manual-payment/basic" in url for url in urls), "Subscribe Basic must open safe payment page")
    assert_true(any("/manual-payment/pro" in url for url in urls), "Subscribe Pro must open safe payment page")
    assert_true(any("/manual-payment/vip_all_forex" in url for url in urls), "Forex monthly must open safe payment page")
    assert_true(any("/manual-payment/vip_all_forex_yearly" in url for url in urls), "Forex yearly must open safe payment page")
    assert_true(all("payment-webhook" not in url and "create_invoice" not in url for url in urls), "Buttons must not create invoices via GET")
    assert_true(all("TELEGRAM" not in url.upper() and "TOKEN" not in url.upper() for url in urls), "Buttons must not expose secrets")

    active_crypto_user = {
        "id": 1,
        "chat_id": "123",
        "plan": "pro",
        "expiry": "2026-12-31",
        "is_paid": 1,
        "subscription_cards": [],
    }
    crypto_text, _ = telegram_plans_payload(active_crypto_user, chat_id="123", lang="en", view="all")
    assert_true("Plan: Pro" in crypto_text, "Crypto user must see active crypto plan")
    assert_true("Expiry: 2026-12-31" in crypto_text, "Crypto user must see crypto expiry")
    assert_true("Status: Not Active" in crypto_text, "Crypto-only user must not be shown as Forex active")

    active_forex_user = {
        "id": 2,
        "chat_id": "456",
        "plan": "trial",
        "expiry": None,
        "is_paid": 0,
        "subscription_cards": [
            {"product_code": "vip_all_forex", "display_name": "VIP ALL FOREX", "market_type": "forex", "expires_at": "2026-08-16"}
        ],
    }
    forex_user_text, _ = telegram_plans_payload(active_forex_user, chat_id="456", lang="en", view="all")
    assert_true("Plan: Free Trial" in forex_user_text, "Forex-only user must keep crypto separate")
    assert_true("Plan: VIP ALL FOREX" in forex_user_text, "Forex user must see Forex plan")
    assert_true("Expiry: 2026-08-16" in forex_user_text, "Forex user must see Forex expiry")

    both_user = {
        "id": 3,
        "chat_id": "789",
        "plan": "pro",
        "expiry": "2026-12-31",
        "is_paid": 1,
        "subscription_cards": [
            {"product_code": "pro", "display_name": "Pro", "market_type": "crypto", "expires_at": "2026-12-31"},
            {"product_code": "vip_all_forex", "display_name": "VIP ALL FOREX", "market_type": "forex", "expires_at": "2026-08-16"},
        ],
    }
    both_text = subscription_message(both_user)
    assert_true("Crypto Subscription" in both_text and "VIP ALL FOREX Subscription" in both_text, "Both subscriptions must be shown independently")

    unlinked_text, unlinked_markup = telegram_plans_payload(None, chat_id="999", lang="en", view="all")
    assert_true("Not linked" in unlinked_text, "Unlinked user must get link-state message")
    assert_true(any("/login?chat_id=999" in button.get("url", "") for button in _buttons(unlinked_markup)), "Unlinked user must get account link URL")

    expired_user = {"id": 4, "chat_id": "000", "plan": "basic", "expiry": "2020-01-01", "is_paid": 1, "subscription_cards": []}
    expired_text = subscription_message(expired_user)
    assert_true("Expiry: 2020-01-01" in expired_text, "Expired user must still see the actual expiry")

    assert_true(PLAN_CATALOG["basic"]["billing_cycles"]["monthly"]["price"] == 25, "Catalog Basic price mismatch")
    assert_true(PLAN_CATALOG["pro"]["billing_cycles"]["monthly"]["price"] == 59.99, "Catalog Pro price mismatch")
    assert_true(PLAN_CATALOG["vip_all_forex"]["billing_cycles"]["monthly"]["price"] == 150, "Catalog monthly Forex price mismatch")
    assert_true(PLAN_CATALOG["vip_all_forex"]["billing_cycles"]["yearly"]["price"] == 1250, "Catalog yearly Forex price mismatch")
    assert_true(checkout_url("vip_all_forex", "yearly").endswith("/manual-payment/vip_all_forex_yearly"), "Yearly checkout code mismatch")

    print("TELEGRAM_PLANS_CATALOG_OK")


if __name__ == "__main__":
    main()
