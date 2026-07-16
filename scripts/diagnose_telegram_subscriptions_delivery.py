import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("BASE_URL", "https://nexoratrader.net")

from trader_app.services.telegram import (  # noqa: E402
    should_show_plans_for_text,
    subscription_message,
    telegram_plans_payload,
)
from trader_app.services.user_entitlements import (  # noqa: E402
    delivery_eligibility_for_signal,
    get_user_entitlements,
)


BAD = ["\u00c3\u0192", "\u00c3\u201a", "\u00c3\u00b0\u00c5\u00b8", "\u00c3\u017d\u00e2\u20ac\u0153", "\u00ef\u00bf\u00bd"]


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def assert_clean(text):
    for marker in BAD:
        assert_true(marker not in text, f"Mojibake marker found: {marker}")


def main():
    crypto_user = {
        "id": 1,
        "chat_id": "111",
        "plan": "pro",
        "expiry": "2099-12-31",
        "is_paid": 1,
        "spot_enabled": 1,
        "futures_enabled": 1,
        "bot_active": 1,
    }
    forex_user = {
        "id": 2,
        "chat_id": "222",
        "plan": "trial",
        "expiry": None,
        "is_paid": 0,
        "bot_active": 1,
    }
    both_user = {
        "id": 3,
        "chat_id": "333",
        "plan": "pro_2y",
        "expiry": "2099-12-31",
        "is_paid": 1,
        "spot_enabled": 1,
        "futures_enabled": 1,
        "bot_active": 1,
    }
    expired_user = {
        "id": 4,
        "chat_id": "444",
        "plan": "basic",
        "expiry": "2020-01-01",
        "is_paid": 1,
        "bot_active": 1,
    }

    # Injected subscription rows avoid database dependency for message rendering.
    forex_user["subscription_cards"] = [
        {"product_code": "vip_all_forex", "display_name": "VIP ALL FOREX", "market_type": "forex", "expires_at": "2099-12-31"}
    ]
    both_user["subscription_cards"] = [
        {"product_code": "pro_2y", "display_name": "Pro 2 Years", "market_type": "crypto", "expires_at": "2099-12-31"},
        {"product_code": "vip_all_forex", "display_name": "VIP ALL FOREX", "market_type": "forex", "expires_at": "2099-12-31"},
    ]

    plans_en, markup = telegram_plans_payload(both_user, chat_id="333", lang="en", view="all")
    plans_ar, _ = telegram_plans_payload(both_user, chat_id="333", lang="ar", view="all")
    assert_clean(plans_en)
    assert_clean(plans_ar)
    assert_true("VIP ALL FOREX" in plans_en, "Forex plan must appear in /plans")
    assert_true("Your active subscriptions" in plans_en, "/plans must include active subscriptions")
    assert_true("اشتراكاتك الحالية" in plans_ar, "Arabic active subscriptions section missing")

    buttons = [button for row in markup["inline_keyboard"] for button in row]
    urls = [button.get("url", "") for button in buttons if button.get("url")]
    assert_true(any("/manual-payment/basic" in url for url in urls), "Basic checkout URL missing")
    assert_true(any("/manual-payment/vip_all_forex_yearly" in url for url in urls), "Forex yearly checkout URL missing")
    assert_true(all("TELEGRAM" not in url.upper() and "TOKEN" not in url.upper() for url in urls), "Secret leaked in Telegram URL")

    crypto_text = subscription_message(crypto_user, lang="en")
    forex_text = subscription_message(forex_user, lang="en")
    both_text = subscription_message(both_user, lang="en")
    expired_text = subscription_message(expired_user, lang="en")
    assert_clean(crypto_text + forex_text + both_text + expired_text)
    assert_true("Crypto Subscription" in both_text and "VIP ALL FOREX Subscription" in both_text, "Both sections must be independent")
    assert_true("Plan: Pro" in crypto_text, "Crypto-only user must show crypto plan")
    assert_true("Plan: VIP ALL FOREX" in forex_text, "Forex-only user must show forex plan")
    assert_true("Status: Expired" in expired_text, "Expired crypto user must show expired state")

    unlinked_text, unlinked_markup = telegram_plans_payload(None, chat_id="999", lang="en", view="all")
    assert_true("Not linked" in unlinked_text, "Unlinked state must be clear")
    assert_true(any("/login?chat_id=999" in button.get("url", "") for row in unlinked_markup["inline_keyboard"] for button in row), "Reconnect URL missing")

    assert_true(should_show_plans_for_text("/plans"), "/plans keyword missing")
    assert_true(should_show_plans_for_text("الخطط"), "Arabic plans keyword missing")
    assert_true(should_show_plans_for_text("Forex"), "Forex keyword missing")

    ent = get_user_entitlements(user=both_user)
    assert_true(ent["crypto"]["plan_code"] == "pro_2y", "Crypto entitlement mismatch")
    # This call may not see injected subscription cards because production source is DB.
    # Message rendering covers injected cards; delivery checks use DB in production.
    _, crypto_allowed, crypto_reason = delivery_eligibility_for_signal(user=crypto_user, signal_market="crypto")
    assert_true(crypto_allowed and crypto_reason == "eligible", "Crypto delivery eligibility failed")

    print("TELEGRAM_SUBSCRIPTIONS_DELIVERY_OK")


if __name__ == "__main__":
    main()
