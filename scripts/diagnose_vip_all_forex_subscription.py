from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def assert_contains(text, needle, label):
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main():
    runtime = read("trader_app/services/runtime.py")
    routes = read("trader_app/blueprints/routes.py")
    telegram = read("trader_app/services/telegram.py")
    sender = read("auto_sender.py")
    dashboard = read("templates/dashboard.html")
    landing = read("templates/landing.html")
    subscriptions = read("trader_app/services/subscriptions.py")

    assert_contains(runtime, '"vip_all_forex"', "runtime product code")
    assert_contains(runtime, "VIP_ALL_FOREX_PRICE", "runtime price env")
    assert_contains(subscriptions, "CREATE TABLE IF NOT EXISTS user_subscriptions", "subscription table")
    assert_contains(subscriptions, "get_user_active_subscriptions", "active subscription helper")
    assert_contains(subscriptions, "get_user_market_capabilities", "market capability helper")
    assert_contains(routes, "activate_vip_all_forex", "payment/admin activation hook")
    assert_contains(routes, "if plan == VIP_ALL_FOREX_CODE", "payment branch")
    assert_contains(routes, "SET is_paid = 1,\n                    plan = %s", "legacy crypto update remains isolated")
    assert_contains(telegram, "VIP ALL FOREX", "telegram plan display")
    assert_contains(sender, "vip_all_forex_required", "delivery gate")
    assert_contains(sender, "FOREX_AUTO_TRADE_DISABLED", "forex auto trade safety")
    assert_contains(dashboard, "My Active Subscriptions", "dashboard subscription section")
    assert_contains(landing, "VIP ALL FOREX", "landing pricing card")

    print("VIP_ALL_FOREX_SUBSCRIPTION_DIAGNOSTIC_OK")


if __name__ == "__main__":
    main()

