from datetime import datetime, timedelta
import sys
from pathlib import Path
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from trader_app.services.user_entitlements import delivery_eligibility_for_signal, get_user_entitlements


def user(plan="trial", expiry=None, is_paid=0, subscriptions=None):
    return {
        "id": 999,
        "email": "diagnostic@example.com",
        "chat_id": "123456",
        "plan": plan,
        "expiry": expiry,
        "is_paid": is_paid,
        "spot_enabled": 1,
        "futures_enabled": 1,
        "bot_active": 1,
        "subscription_cards": subscriptions or [],
    }


def forex_sub(days=30, product_code="vip_all_forex"):
    return {
        "product_code": product_code,
        "display_name": "VIP ALL FOREX",
        "market_type": "forex",
        "status": "active",
        "is_paid": 1,
        "expires_at": datetime.utcnow() + timedelta(days=days),
    }


def main():
    future = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
    expired = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    crypto_only = user("pro", future, 1)
    ent, ok, reason = delivery_eligibility_for_signal(user=crypto_only, signal_market="crypto")
    assert ok is True, reason
    ent, ok, reason = delivery_eligibility_for_signal(user=crypto_only, signal_market="forex")
    assert ok is False and reason == "vip_all_forex_required"

    forex_only = user("trial", None, 0, [forex_sub()])
    ent, ok, reason = delivery_eligibility_for_signal(user=forex_only, signal_market="forex")
    assert ok is True, reason

    expired_crypto = user("pro", expired, 1)
    ent = get_user_entitlements(user=expired_crypto)
    assert ent["crypto"]["status"] == "expired"

    both = user("vip", future, 1, [forex_sub(product_code="vip_all_forex_yearly")])
    ent, ok_crypto, _ = delivery_eligibility_for_signal(user=both, signal_market="crypto")
    ent, ok_forex, _ = delivery_eligibility_for_signal(user=both, signal_market="forex")
    assert ok_crypto is True and ok_forex is True

    print("SUBSCRIPTION_PLAN_INTEGRITY_OK")


if __name__ == "__main__":
    main()
