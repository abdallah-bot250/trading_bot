import os
import sys
import types
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The CI/container running these safety unit tests may not have optional live
# exchange/database packages installed. Stub them because these tests only cover
# pure safety helpers and never call real exchanges or databases.
sys.modules.setdefault("ccxt", types.SimpleNamespace(bybit=lambda *a, **k: None, kucoin=lambda *a, **k: None, binanceus=lambda *a, **k: None, binance=lambda *a, **k: None))
sys.modules.setdefault("psycopg2", types.SimpleNamespace(connect=lambda *a, **k: None))

import auto_sender


def test_calculate_amount_uses_stop_loss_risk_and_caps_notional():
    amount = auto_sender.calculate_amount(
        usdt_balance=1000,
        risk_percent=0.01,
        entry_price=100,
        stop_loss_price=95,
    )
    assert amount == 2.0


def test_calculate_amount_rejects_missing_stop_loss():
    assert auto_sender.calculate_amount(1000, 0.01, 100, None) == 0
    assert auto_sender.calculate_amount(1000, 0.01, 100, 100) == 0


class DummyExchange:
    id = "bybit"
    def __init__(self):
        self.orders = []
    def create_order(self, symbol, type, side, amount, price=None, params=None):
        self.orders.append({
            "symbol": symbol,
            "type": type,
            "side": side,
            "amount": amount,
            "price": price,
            "params": params or {},
        })
        return {"id": "close-1"}


def test_emergency_close_futures_uses_reduce_only_opposite_side():
    ex = DummyExchange()
    ok, order = auto_sender.emergency_close_position(ex, "BTC/USDT:USDT", "buy", 0.1, "futures", "test")
    assert ok is True
    assert order["id"] == "close-1"
    assert ex.orders[0]["side"] == "sell"
    assert ex.orders[0]["params"].get("reduceOnly") is True
