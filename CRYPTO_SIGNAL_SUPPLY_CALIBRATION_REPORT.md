# CRYPTO_SIGNAL_SUPPLY_CALIBRATION_V1

## Goal

Restore logical crypto signal supply for qualified B+ opportunities without weakening A/A+ rules or disabling safety filters.

## Production Symptom

Recent production scan showed:

- 168 attempts
- 0 candidates
- 44 MTF rejects
- 44 entry rejects
- 28 liquidity rejects
- 0 final signals

This indicated over-filtering between playbook confirmation and candidate creation.

## Changes Made

### 1. Separate B+ MTF Path

A/A+ behavior remains strict:

- 4H and 1H must align in the same direction.

B+ can now pass only when:

- 4H BULL + 1H RANGE for LONG.
- 4H BEAR + 1H RANGE for SHORT.
- 4H RANGE + 1H directional with matching setup direction.
- 30m setup agrees with the trade direction.
- 15m trigger is not against the trade direction.
- No hard 4H/1H conflict exists.

Hard conflicts still reject.

Final review lock:

- Soft MTF candidates are tagged with `mtf_path=soft_alignment`.
- Soft MTF candidates are tagged with `mtf_soft_conflict=true`.
- Soft MTF candidates are forced to `quality_tier=B_PLUS`.
- Soft MTF candidates cannot be promoted to A/A+ by score alone.
- A/A+ remains reserved for the strict MTF path.
- Soft MTF scoring receives `SOFT_MTF_ALIGNMENT_PENALTY`.

### 2. Entry Confirmation Window

Entry confirmation now checks the last 3 closed candles instead of only the latest candle.

Allowed recent confirmations:

- Retest
- Pullback
- Liquidity sweep
- Rejection wick
- Support/resistance bounce
- FVG/order-block style imbalance only when structurally confirmed

The signal stores:

- `entry_confirmation_age_candles`

Open candles are excluded.

Final review lock:

- Only ages `0`, `1`, or `2` are accepted.
- Age `3+` is rejected as `ENTRY_STALE`.
- A late-entry guard runs after confirmation and rejects chase entries as `LATE_ENTRY`.

### 3. Liquidity Diagnostics

Volume checks now use:

- Last closed candle volume.
- Previous 20 closed candles average.
- Quote volume when available.

Diagnostics added:

- `current_closed_volume`
- `average_volume_20`
- `volume_ratio`
- `data_source`
- `candle_closed`

No liquidity threshold was lowered.

Final review lock:

- Missing or zero volume fails closed as `THIN`.
- Open candle volume is excluded from `current_closed_volume`.
- `average_volume_20` uses the 20 closed candles before `current_closed_volume`.

### 4. Pipeline Counters

Added counters:

- `playbooks_selected`
- `setups_confirmed`
- `entry_confirmations_passed`
- `candidates_built`
- `finalized_candidates`
- `final_signals`

Added rejection counters:

- `mtf_hard_conflict`
- `mtf_soft_conflict`
- `entry_missing`
- `entry_stale`
- `liquidity_invalid`
- `quality_score`
- `late_entry`
- `risk_reward`

### 5. 24h Supply Safety Guard

The engine records a 24h supply summary and logs:

- `SIGNAL_SUPPLY_24H`
- `SIGNAL_SUPPLY_CRITICAL_OVERFILTERING`

when scans are high and candidates remain zero.

This guard never forces a trade.

## Before / After Scenarios

| Scenario | Before | After |
| --- | --- | --- |
| 4H BULL + 1H RANGE + valid 30m/15m LONG | Often rejected as MTF conflict | Allowed only as B+ |
| 4H BEAR + 1H RANGE + valid trigger | Often rejected as MTF conflict | Allowed only as B+ |
| 4H BULL + 1H BEAR | Rejected | Still rejected |
| Retest 2 closed candles ago | Often rejected as missing entry | Accepted with age logged |
| Open candle low volume | Could distort liquidity | Excluded from liquidity baseline |
| Soft MTF with high score | Could risk over-ranking | Forced B+ with SOFT_MTF_ALIGNMENT_PENALTY |
| Retest age 3+ | Could be stale | Rejected as ENTRY_STALE |
| Price chased after retest | Could enter too late | Rejected as LATE_ENTRY |

## Safety Impact

No changes were made to:

- Payment flow
- Telegram delivery flow
- Subscriptions
- A/A+ strict logic
- Hard MTF conflicts
- Fake breakout rejection
- Low liquidity rejection
- Late-entry rejection
- RR minimum

## New Diagnostic

`scripts/diagnose_crypto_signal_supply_calibration_v1.py`

Expected success output:

`CRYPTO_SIGNAL_SUPPLY_CALIBRATION_DIAGNOSTICS_OK`
