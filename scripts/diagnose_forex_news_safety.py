import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("FERNET_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")

from trader_app.services import forex_news


def main():
    status = forex_news.configuration_status()
    print("FOREX_NEWS_STATUS", status)
    assert status.get("required") is not None
    if not status.get("configured"):
        assert status.get("reason") == "NO_TRUSTED_NEWS_PROVIDER"
        decision = forex_news.news_decision("EURUSD")
        assert decision.blocked is True
        assert decision.reason == "NO_TRUSTED_NEWS_PROVIDER"
    else:
        assert status.get("provider") in {"tradingeconomics", "finnhub", "financialmodelingprep"}
    print("FOREX_NEWS_SAFETY_OK")


if __name__ == "__main__":
    main()
