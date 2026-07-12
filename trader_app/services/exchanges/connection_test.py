"""Safe server-side exchange connection tests.

This module avoids logging secrets and returns user-friendly status objects.
Network calls are best-effort; diagnostics can run without real credentials.
"""

from datetime import datetime
import time

from .registry import get_exchange_capability, normalize_exchange_key


def _ccxt_class(exchange_key):
    import ccxt

    mapping = {
        "bybit": ccxt.bybit,
        "binance": ccxt.binance,
        "okx": ccxt.okx,
        "bitget": ccxt.bitget,
        "kucoin": ccxt.kucoin,
        "gateio": ccxt.gateio,
        "mexc": ccxt.mexc,
        "bingx": getattr(ccxt, "bingx", None),
        "htx": getattr(ccxt, "htx", None),
        "kraken": ccxt.kraken,
        "coinbaseadvanced": getattr(ccxt, "coinbaseadvanced", None),
    }
    klass = mapping.get(exchange_key)
    if klass is None:
        raise ValueError(f"Exchange {exchange_key} is not supported by this build")
    return klass


def build_ccxt_exchange(exchange, api_key, api_secret, passphrase=None, mode="futures"):
    exchange_key = normalize_exchange_key(exchange)
    capability = get_exchange_capability(exchange_key)
    if not capability:
        raise ValueError("Unsupported exchange")

    klass = _ccxt_class(exchange_key)
    default_type = "swap" if mode == "futures" else "spot"
    options = {"defaultType": default_type, "adjustForTimeDifference": True}
    if exchange_key == "binance" and mode == "futures":
        options = {"defaultType": "future"}

    config = {
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": options,
    }
    if capability.get("passphrase") and passphrase:
        config["password"] = passphrase
    return klass(config)


def safe_error_message(exc):
    raw = str(exc or "")
    lowered = raw.lower()
    if "permission" in lowered:
        return "Trade permission missing or restricted."
    if "invalid" in lowered and "key" in lowered:
        return "Invalid API key."
    if "signature" in lowered or "secret" in lowered:
        return "Invalid API secret or passphrase."
    if "passphrase" in lowered or "password" in lowered:
        return "API passphrase required or invalid."
    if "ip" in lowered and "restrict" in lowered:
        return "IP restriction mismatch."
    if "timeout" in lowered or "temporarily" in lowered:
        return "Exchange temporarily unavailable."
    if "network" in lowered:
        return "Exchange network error."
    return "Connection test failed safely. Check API permissions and exchange availability."


def test_exchange_connection(exchange, api_key, api_secret, passphrase=None, mode="futures"):
    exchange_key = normalize_exchange_key(exchange)
    capability = get_exchange_capability(exchange_key)
    if not capability:
        return {"ok": False, "message": "Unsupported exchange", "exchange": exchange_key}
    if capability.get("passphrase") and not passphrase:
        return {"ok": False, "message": "Passphrase required for this exchange", "exchange": exchange_key}

    started = time.time()
    result = {
        "ok": False,
        "exchange": exchange_key,
        "exchange_name": capability.get("name", exchange_key),
        "api_valid": False,
        "exchange_reachable": False,
        "spot_enabled": bool(capability.get("spot")),
        "futures_enabled": bool(capability.get("futures")),
        "trade_permission": "Unknown",
        "withdraw_permission": "Not detectable",
        "usdt_balance": "N/A",
        "futures_balance": "N/A",
        "available_margin": "N/A",
        "position_mode": "Unknown",
        "latency_ms": None,
        "server_time_difference": "N/A",
        "rate_limit_status": "Enabled",
        "tested_at": datetime.utcnow().isoformat(),
    }
    try:
        ex = build_ccxt_exchange(exchange_key, api_key, api_secret, passphrase, mode=mode)
        ex.load_markets()
        result["exchange_reachable"] = True
        balance = ex.fetch_balance()
        result["api_valid"] = True
        result["trade_permission"] = "Enabled if API was created with trade permission"
        usdt_free = (
            balance.get("USDT", {}).get("free")
            or balance.get("free", {}).get("USDT")
            or 0
        )
        result["usdt_balance"] = round(float(usdt_free or 0), 6)
        result["futures_balance"] = result["usdt_balance"] if mode == "futures" else "N/A"
        result["available_margin"] = result["usdt_balance"]
        result["position_mode"] = "Exchange default"
        result["latency_ms"] = int((time.time() - started) * 1000)
        result["ok"] = True
        result["message"] = "Connection Successful"
        return result
    except Exception as exc:
        result["latency_ms"] = int((time.time() - started) * 1000)
        result["message"] = safe_error_message(exc)
        return result

