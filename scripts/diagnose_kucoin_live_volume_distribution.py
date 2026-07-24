import importlib.util
import json
import os
import sys
import types
from urllib.request import Request, urlopen


os.environ.setdefault("MAX_DYNAMIC_SYMBOLS", "120")
os.environ.setdefault("MIN_DYNAMIC_QUOTE_VOLUME", "5000000")
os.environ["DYNAMIC_SYMBOLS_TTL_SECONDS"] = "0"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if importlib.util.find_spec("requests") is None:
    sys.modules["requests"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)

import market_analyzer as ma  # noqa: E402


def fetch_json(url):
    snapshot_path = os.environ.get("KUCOIN_LIVE_SNAPSHOT_JSON", "").strip()
    if snapshot_path:
        with open(snapshot_path, "r", encoding="utf-8") as handle:
            return json.load(handle), 200
    request = Request(url, headers={"User-Agent": "NexoraDiagnostics/1.0"})
    with urlopen(request, timeout=25) as response:
        payload = response.read().decode("utf-8", "replace")
        return json.loads(payload), response.status


def fake_kucoin_only(url, timeout=12):
    if "kucoin.com" in url:
        return fetch_json(url)
    return None, 451


def main():
    original = ma._safe_market_json
    try:
        ma._reset_symbol_universe_stats()
        ma.DYNAMIC_SYMBOL_CACHE.clear()
        ma.DYNAMIC_SYMBOL_CACHE.update({"time": 0, "symbols": None})
        ma._safe_market_json = fake_kucoin_only
        selected = ma.get_scan_symbols(force_refresh=True)
    finally:
        ma._safe_market_json = original

    stats = ma.SYMBOL_UNIVERSE_FILTER_STATS
    print(
        "KUCOIN_LIVE_VOLUME_DIAGNOSTIC_OK "
        f"final_count={len(selected)} "
        f"above_5m={stats.get('kucoin_symbols_above_volume', 0)} "
        f"distribution={json.dumps(stats.get('kucoin_volume_distribution', {}), sort_keys=True)} "
        f"top30={json.dumps(stats.get('kucoin_top_quote_turnover', []), sort_keys=True)} "
        f"invalid_examples={json.dumps(stats.get('kucoin_invalid_volume_examples', []), sort_keys=True)} "
        f"below_min_examples={json.dumps(stats.get('kucoin_below_min_quote_volume_examples', []), sort_keys=True)} "
        f"missing_examples={json.dumps(stats.get('kucoin_missing_ticker_data_examples', []), sort_keys=True)}"
    )


if __name__ == "__main__":
    main()
