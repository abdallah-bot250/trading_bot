"""Lightweight base adapter contract for future exchange-specific classes."""


class ExchangeAdapter:
    exchange_key = ""

    def __init__(self, exchange):
        self.exchange = exchange

    def test_connection(self):
        raise NotImplementedError

    def fetch_balances(self):
        raise NotImplementedError

    def validate_permissions(self):
        raise NotImplementedError

    def normalize_symbol(self, symbol, trade_type="futures"):
        return symbol

    def set_leverage(self, symbol, leverage):
        return None

    def place_order(self, *args, **kwargs):
        raise NotImplementedError

    def attach_protection(self, *args, **kwargs):
        raise NotImplementedError

    def close_position(self, *args, **kwargs):
        raise NotImplementedError

    def fetch_open_positions(self):
        return []

    def fetch_order_status(self, order_id):
        return None

