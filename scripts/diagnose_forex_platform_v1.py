from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def main():
    subscriptions = read("trader_app/services/subscriptions.py")
    sender = read("auto_sender.py")

    required = [
        "can_receive_forex",
        "can_receive_metals",
        "can_receive_indices",
        "can_receive_oil",
        "can_auto_trade_forex",
        "execution_not_verified",
        "FOREX_MARKET_TYPES",
    ]
    combined = subscriptions + "\n" + sender
    missing = [item for item in required if item not in combined]
    if missing:
        raise AssertionError("missing forex platform markers: " + ", ".join(missing))

    print("FOREX_PLATFORM_V1_DIAGNOSTIC_OK")


if __name__ == "__main__":
    main()

