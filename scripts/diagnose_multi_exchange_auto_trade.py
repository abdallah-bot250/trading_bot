import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    registry = read("trader_app/services/exchanges/registry.py")
    runtime = read("trader_app/services/runtime.py")
    routes = read("trader_app/blueprints/routes.py")
    sender = read("auto_sender.py")
    template = read("templates/auto_trade.html")

    for exchange in ["bybit", "binance", "okx", "bitget", "kucoin", "gateio", "mexc"]:
        require(exchange in registry, f"missing exchange capability: {exchange}")

    require("auto_trade_futures" in registry, "capability registry missing futures flag")
    require("auto_trade_spot" in registry, "capability registry missing spot flag")
    require("exchange_connections" in runtime, "exchange_connections table missing")
    require("auto_trade_settings" in runtime, "auto_trade_settings table missing")
    require("execution_log" in runtime, "execution_log table missing")
    require("/auto-trade/test-connection" in routes, "connection test route missing")
    require("/auto-trade/save-connection" in routes, "save connection route missing")
    require("/admin/auto-trade-monitor" in routes, "admin auto trade monitor route missing")
    require("Emergency Stop" in template, "emergency stop UI missing")
    require("Spot Auto Trade is disabled" in routes or "Spot auto trade stays disabled" in template, "spot safety messaging missing")
    require("load_primary_auto_trade_connection" in sender, "auto sender does not load primary exchange connections")
    require("record_execution_event" in sender, "execution event logging missing")
    require("safe_decrypt_credential" in sender, "credential decrypt fallback missing")
    require("exchange_name=effective_exchange" in sender, "auto trade does not pass selected exchange to execution")
    require("passphrase=effective_passphrase" in sender, "auto trade does not pass passphrase to execution")
    require("spot_auto_disabled_or_unprotected" in sender, "spot execution guard missing")

    unsafe_secret_logs = re.findall(r"log\(f?['\"].*(api_secret|api_key|passphrase)", sender, flags=re.IGNORECASE)
    require(not unsafe_secret_logs, "possible credential logging found")

    print("MULTI_EXCHANGE_AUTO_TRADE_DIAGNOSTICS_OK")


if __name__ == "__main__":
    main()
