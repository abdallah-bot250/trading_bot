import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from market_analyzer import evaluate_mtf_alignment, b_plus_mtf_path_context


def mtf(major, confirm, setup, trigger):
    return {
        "major": major,
        "confirm": confirm,
        "frames": {
            "30m": {"direction": setup},
            "15m": {"direction": trigger},
        },
    }

cases = [
    ("short_soft", mtf("BEAR", "RANGE", "BEAR", "BEAR"), "SHORT", "SOFT_ALIGNMENT", True),
    ("long_soft", mtf("BULL", "RANGE", "BULL", "RANGE"), "LONG", "SOFT_ALIGNMENT", True),
    ("hard_conflict", mtf("BULL", "BEAR", "BEAR", "BEAR"), "LONG", "HARD_CONFLICT", False),
    ("strict_long", mtf("BULL", "BULL", "BULL", "BULL"), "LONG", "STRICT_ALIGNMENT", True),
    ("range_anchor_ok", mtf("RANGE", "BEAR", "BEAR", "BEAR"), "SHORT", "RANGE_ANCHOR", True),
    ("range_anchor_missing_trigger", mtf("RANGE", "BEAR", "BEAR", "RANGE"), "SHORT", "RANGE_ANCHOR", False),
]

for name, context, direction, expected_class, expected_ok in cases:
    result = evaluate_mtf_alignment(context, direction)
    assert result["classification"] == expected_class, (name, result)
    assert bool(result["ok"]) is expected_ok, (name, result)

soft = b_plus_mtf_path_context(mtf("BEAR", "RANGE", "BEAR", "BEAR"), "SHORT")
assert soft["ok"] and soft["state"] == "B_PLUS_MTF_CONFIRMED"
strict = b_plus_mtf_path_context(mtf("BEAR", "BEAR", "BEAR", "BEAR"), "SHORT")
assert not strict["ok"]
print("diagnose_b_plus_mtf_early_gate_fix: OK")
