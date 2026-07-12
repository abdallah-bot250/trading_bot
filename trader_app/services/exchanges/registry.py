"""Central exchange capability registry.

The registry is intentionally conservative. Only Bybit futures is marked as
production-ready for auto execution until real protection-order testing proves
other venues safe.
"""

EXCHANGE_CAPABILITIES = {
    "bybit": {
        "name": "Bybit",
        "spot": True,
        "futures": True,
        "passphrase": False,
        "sandbox": True,
        "native_tp_sl": True,
        "oco": False,
        "auto_trade_futures": True,
        "auto_trade_spot": False,
        "recommended": True,
        "production_ready": True,
        "symbol_note": "USDT perpetuals use CCXT format like BTC/USDT:USDT.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "binance": {
        "name": "Binance",
        "spot": True,
        "futures": True,
        "passphrase": False,
        "sandbox": True,
        "native_tp_sl": True,
        "oco": True,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "symbol_note": "Futures protection requires exchange-specific validation.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "okx": {
        "name": "OKX",
        "spot": True,
        "futures": True,
        "passphrase": True,
        "sandbox": True,
        "native_tp_sl": True,
        "oco": True,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "symbol_note": "Requires API passphrase.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "bitget": {
        "name": "Bitget",
        "spot": True,
        "futures": True,
        "passphrase": True,
        "sandbox": True,
        "native_tp_sl": True,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "symbol_note": "Requires API passphrase on most accounts.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "kucoin": {
        "name": "KuCoin",
        "spot": True,
        "futures": True,
        "passphrase": True,
        "sandbox": True,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "symbol_note": "Passphrase required. Auto execution remains beta.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "gateio": {
        "name": "Gate.io",
        "spot": True,
        "futures": True,
        "passphrase": False,
        "sandbox": False,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "symbol_note": "Requires exchange-specific execution testing.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "mexc": {
        "name": "MEXC",
        "spot": True,
        "futures": True,
        "passphrase": False,
        "sandbox": False,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "symbol_note": "Futures execution must be validated before enabling.",
        "permissions": ["Read", "Trade", "No withdrawals"],
    },
    "bingx": {
        "name": "BingX",
        "spot": True,
        "futures": True,
        "passphrase": False,
        "sandbox": False,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "read_test_only": True,
        "symbol_note": "Secondary read/test support only.",
        "permissions": ["Read only recommended"],
    },
    "htx": {
        "name": "HTX",
        "spot": True,
        "futures": True,
        "passphrase": False,
        "sandbox": False,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "read_test_only": True,
        "symbol_note": "Secondary read/test support only.",
        "permissions": ["Read only recommended"],
    },
    "kraken": {
        "name": "Kraken",
        "spot": True,
        "futures": False,
        "passphrase": False,
        "sandbox": False,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "read_test_only": True,
        "symbol_note": "Secondary read/test support only.",
        "permissions": ["Read only recommended"],
    },
    "coinbaseadvanced": {
        "name": "Coinbase Advanced",
        "spot": True,
        "futures": False,
        "passphrase": False,
        "sandbox": False,
        "native_tp_sl": False,
        "oco": False,
        "auto_trade_futures": False,
        "auto_trade_spot": False,
        "recommended": False,
        "production_ready": False,
        "read_test_only": True,
        "symbol_note": "Secondary read/test support only.",
        "permissions": ["Read only recommended"],
    },
}


def normalize_exchange_key(value):
    key = str(value or "").strip().lower().replace("-", "").replace("_", "")
    aliases = {
        "gate": "gateio",
        "gateio": "gateio",
        "coinbase": "coinbaseadvanced",
        "coinbaseadvanced": "coinbaseadvanced",
        "binanceus": "binanceus",
        "binance_us": "binanceus",
    }
    return aliases.get(key, key)


def get_exchange_capability(exchange):
    return EXCHANGE_CAPABILITIES.get(normalize_exchange_key(exchange))


def supported_exchange_options():
    return [
        {"key": key, **value}
        for key, value in EXCHANGE_CAPABILITIES.items()
    ]


def exchange_requires_passphrase(exchange):
    capability = get_exchange_capability(exchange) or {}
    return bool(capability.get("passphrase"))


def exchange_mode_status(exchange, mode):
    capability = get_exchange_capability(exchange) or {}
    if mode == "futures":
        return bool(capability.get("futures")), bool(capability.get("auto_trade_futures"))
    return bool(capability.get("spot")), bool(capability.get("auto_trade_spot"))

