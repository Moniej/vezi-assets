# DOL EPS/P.E. Extraction — Status: NOT VALIDATED, deprioritized

*2026-07-22. Approved engineering task ("EPS parser"). Reporting an honest
negative result rather than pushing a low-confidence extraction into the
reference data.*

## What was attempted

The DOL's trailing numeric region (Interim/Final paid, EPS, P.E. columns)
is heavily crowded — the same class of problem the validated ex-div and
DOL-close parsers solved via draw-order/format-aware extraction. Two
approaches were tried, both using the cross-check EPS x P.E. ~= Close
(close taken from the already-validated equity_prices panel, not
re-derived) as the pass/fail arbiter:

1. **Naive "last two numeric tokens in the row"**: worked cleanly on a
   hand-picked sample (GTCO, ZENITHBANK, GUARANTY across 2019/2022/2023 —
   all near-exact matches), but at 80-day scale (6,003 extracted rows)
   passed only **58.5%** — high-price names (DANGCEM, NESTLE, MTNN,
   SEPLAT) systematically have blank EPS/P.E. fields on many days, and the
   naive rule silently grabbed an earlier column (52-week high/low, or a
   repeated price field) instead of returning nothing.
2. **Header-calibrated banding** (locate the 'P.E.' header token per page,
   require the EPS/P.E. candidates to sit in tight x-bands relative to
   it): pass rate **dropped to 34.3%** and produced a NEW failure mode
   (implausibly tiny eps/pe pairs on low-price names like CHAMPION,
   GUINEAINS) — the column geometry apparently drifts by era/section more
   than a single set of tolerances can cover.

## Decision

Neither approach clears the pre-declared bar (95% pass on ≥500 rows;
`reports/eps_pe_validation.md` holds both runs). Per platform rule
(unknown stays unknown, never fabricate), **no EPS/P.E. data was written
to any reference file.** `src/ngxrot/dol_eps_parser.py` is kept in the
tree as a validated-negative starting point (both heuristics, the
plausibility gates, and the exact reasoning are documented in its
docstring) — a real fix needs per-format-era column calibration (the
layout visibly shifted at least once, ~2015→2019, matching what the
pricelist/DOL-close parsers already had to handle) rather than one
universal rule, which is more engineering than this session's remaining
budget supports responsibly.

## Also found, same investigation (dividend cash amounts)

The "Div/Sc/Price/Date" fields near the row's middle were probed against
the known-good GTCO FY2023 anchor (verified primary-source: ₦2.70 paid).
A positional read of that region returned ₦0.50 — which is GTCO's PAR
VALUE, not its dividend (a column bleed, not a real read) — and the "Div"
slot itself sometimes contains a non-numeric 'X' (ex-dividend marker) on
the actual closure date rather than an amount. **This region is not a
reliable source for dividend cash amounts.** The corp-actions PDF
pipeline (`scripts/build_corp_actions_db.py`, 87 DPS values already
extracted from primary-source text) remains the correct source; this
investigation does not change that and did not attempt a "dividend amount
parser" bulk run for the same reason.

## Recommendation

Deprioritize both the "dividend amount parser" and "EPS parser" backlog
items below the Size/market-cap layer (which validated cleanly — see
`reports/market_cap_validation.md`) and below the H-006/H-007 successor
designs identified in the Factor Registry. If revisited, scope as its own
session: identify format eras precisely (probe header x-positions on a
stratified sample across 2014-2026 first), calibrate per era, and only
then attempt bulk extraction.
