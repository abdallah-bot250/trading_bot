import sys
import importlib.util
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class Timeout(Exception):
        pass

    class RequestException(Exception):
        pass

    requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(RequestException("network disabled in diagnostic"))
    requests_stub.exceptions = types.SimpleNamespace(Timeout=Timeout, RequestException=RequestException)
    sys.modules["requests"] = requests_stub

spec = importlib.util.spec_from_file_location(
    "forex_market_data_probe",
    ROOT / "trader_app" / "services" / "forex_market_data.py",
)
forex_market_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forex_market_data)
get_ohlcv = forex_market_data.get_ohlcv
provider_configuration_status = forex_market_data.provider_configuration_status


def main():
    status = provider_configuration_status()
    symbol = "EURUSD"
    timeframe = "15m"
    if not status.get("configured"):
        print(
            "FOREX_PROVIDER_PROBE "
            f"provider={status.get('provider')} configured=false reason={status.get('reason')} "
            "status_code= candles_count=0 latest_timestamp= stale=true"
        )
        print("FOREX_PROVIDER_PROBE_OK")
        return

    result = get_ohlcv(symbol, timeframe, outputsize=80)
    print(
        "FOREX_PROVIDER_PROBE "
        f"provider={result.provider} status_code={result.status_code or ''} "
        f"candles_count={len(result.candles or [])} latest_timestamp={result.data_timestamp or ''} "
        f"stale={bool(result.stale)} ok={bool(result.ok)} reason={result.error or 'OK'}"
    )
    print("FOREX_PROVIDER_PROBE_OK")


if __name__ == "__main__":
    main()
