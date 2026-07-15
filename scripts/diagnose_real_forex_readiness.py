"""Static/runtime-safe readiness check. Does not place trades or fabricate data."""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


market = load("forex_market_data_diag", ROOT / "trader_app/services/forex_market_data.py")
news = load("forex_news_diag", ROOT / "trader_app/services/forex_news.py")

market_status = market.provider_configuration_status()
news_status = news.configuration_status()
assert len(market.FOREX_SYMBOLS) >= 16
assert "EURUSD" in market.FOREX_SYMBOLS and "XAUUSD" in market.FOREX_SYMBOLS
assert market.pip_size("EURUSD") == 0.0001
assert market.pip_size("USDJPY") == 0.01
assert market.pip_size("US30") == 1.0
assert news.currencies_for_symbol("EURUSD") == ["EUR", "USD"]
assert news.currencies_for_symbol("XAUUSD") == ["USD"]
print(
    "REAL_FOREX_READINESS_OK "
    f"market_provider={market_status['provider']} market_configured={str(market_status['configured']).lower()} "
    f"news_provider={news_status['provider']} news_configured={str(news_status['configured']).lower()} "
    f"real_spread_required={os.environ.get('FOREX_REQUIRE_REAL_SPREAD', 'true')} "
    f"news_required={str(news_status['required']).lower()}"
)
