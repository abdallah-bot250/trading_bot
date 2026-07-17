# Nexora production patch review — 2026-07-17

## Applied fixes

- Centralized crypto MTF classification into strict, soft, range-anchor, hard-conflict, and invalid states.
- Removed the legacy early strict-MTF rejection that blocked valid B+ cases such as 4H BEAR + 1H RANGE.
- Soft/range-anchor paths remain B+ only and still require 30m/15m confirmation; hard conflict remains fail-closed.
- Added a focused diagnostic for the early-gate scenarios.
- Corrected Forex capability reporting so an active Forex subscription does not claim Forex Auto Trade is available.
- Corrected Telegram subscription display so yearly VIP ALL FOREX is recognized as Forex access.
- Made Forex candle freshness timeframe-aware so healthy 1H/4H closed candles are not rejected by a fixed 30-minute stale limit.

## Safety retained

- A/A+ strict MTF behavior remains unchanged.
- Unsafe RR, low confidence, stale entries, real-spread requirements, news requirements, and shadow/production separation remain enabled.
- Forex Auto Trade remains disabled.
