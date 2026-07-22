# Equity Data Diagnostics — 2026-07-21

Scope: 320,159 rows / 308 tickers (conf >= 0.9).

| check | findings | tickers affected |
|---|---|---|
| unexplained_jump (session-adjacent >12%, unaccounted) | 116 | 15 |
| stale_price (>=20 identical closes) | 1481 | 185 |
| volume/value contradictions | 0 | 0 |
| implausible_volume (> 1e12 shares, glued-token signature) | 0 | 0 |
| vwap_inconsistent (value/volume outside [0.25, 4]x close) | 469 | 192 |

Jump scan uses the NGX ±10% daily band: moves beyond 12% between CONSECUTIVE
MARKET SESSIONS are impossible without an official re-basing or a data error.
Candidate >12% moves this run resolved as:
- spanning a verified market day our panel lacks (legal 2+ session
  compound; index-verified calendar): 166
- certified by NGX's own Gainers/Losers report as within-band off an
  officially adjusted base (138,001 mover rows): 217
- closure-of-register (1,044 events) or earnings filing
  (10,690) within ±3bd: 2
- UNEXPLAINED (logged, gate input): 116
