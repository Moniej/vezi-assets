# Stage 28D — Operational Fixes Applied, Re-Validated

**Date:** 2026-08-09. No post-2026-08-17 data used, inspected, or referenced anywhere in this document
(confirmed programmatically: 0 rows exist at or after that date after the refresh below). No hypothesis
registered, no backtest, no DiD, no economic gate, no return interpretation. The frozen experimental
design (Stage 28B) is **not** altered in substance — two ambiguities are closed via dated amendments
(exactly as the deviation protocol requires), and one additional operational clarification was added
after a new finding surfaced. Scripts: `scripts/stage28d_postfix_validation.py`. Raw output:
`data/staging/stage28d/`.

---

## The four fixes, as applied

### Fix 1 — treatment-classification rule made explicit

**Applied.** Stage 28B §1 now carries **Amendment 1**: a ticker with no `equity_prices` row on the exact
reference session is classified **ineligible** — excluded from treated, mid-band, and control alike, not
defaulted into any group via an unbounded look-back. This is the reading Stage 28C's evidence favored;
it is now the only reading in force.

### Fix 2 — first-`equity_prices`-row promoted to primary listing-date proxy

**Applied.** Stage 28B §2 now carries **Amendment 2**. `securities.listing_date` remains confirmed
0/321-populated (unchanged, unusable) — the fallback already named in the original frozen text is now the
sole rule, not a nominal alternative that never resolved. Verified working on real data: 4 tickers
(ABBEYBANK, AVACAP, CMFC, HBMNG) are correctly caught as newly-listed within the rehearsal pre-period,
where the old `listing_date`-based check silently found zero (a false negative, not a true "no new
listings" result).

### Fix 3 — frozen rules otherwise preserved exactly

**Confirmed, not re-tuned.** The zero-return definition (strict equality), suspension handling
(absence-not-imputation), the ≥30/40-session minimum, the DiD model, the clustering/permutation method,
both placebo-window constructions, and the dose-response check are all unchanged from Stage 28B's original
text. Nothing here was loosened or tightened in response to how the validation numbers looked.

### Fix 4 — market-data freshness

**Applied, with a DB write, reported here as required.** Ran the platform's own existing, idempotent daily
pipeline (`daily_update.py` → `parse_pricelists.py` → `ingest_pricelists.py`) — not a new acquisition
mechanism, the same one used throughout this project. Result:

| | Before | After |
|---|---|---|
| `equity_prices` latest `trade_date` | 2026-07-21 | **2026-08-07** |
| Gap to reform effective date (2026-08-17) | 27 days | 10 days |
| Gap to "today" (2026-08-09) | 19 days stale | feed is current (2 days ahead of "today" is impossible; the 2026-08-07 close reflects the most recent session available from NGX as of this run) |
| `equity_prices` row count | 353,043 | 656,152 (raw) |

**Confirmed zero rows at or after 2026-08-17** — the refresh pulled real, dated, pre-reform data only; no
post-reform observation was introduced or inspected. The row-count jump is larger than the ~19-day gap
alone would suggest because the ingestion pipeline's own validated backlog (previously-harvested but
not-yet-ingested archive files, some reaching back to 2014) was cleared in the same run — a legitimate,
gated (V1–V3 validation battery, including a same-day PDF-vs-REST cross-check that matched 100% on
2026-08-07) append to existing, established infrastructure, not a new or ad hoc write path.

## An unplanned but necessary fifth finding: `equity_prices` duplication

Re-running the session-presence check after the refresh produced session counts exceeding the 40-session
window size (65-67), which should be structurally impossible. Investigation found `equity_prices` carries
**multiple source rows per (ticker, trade_date)** by design — 301,459 duplicate pairs platform-wide,
**296,586 of them already present before today's refresh** (confirmed pre-existing, not introduced by Fix
4). 301,405 of those pairs are byte-identical across sources (no value corruption); a small residual **54
pairs genuinely conflict** between sources. The platform's own established `backtest_xs.load_panel()`
already resolves this via `drop_duplicates(subset=["ticker","trade_date"], keep="last")` — this stage
adopts the identical rule, logged as **Amendment 3** in Stage 28B: an operational clarification of how to
correctly read the existing table (previous-close comparisons must run on the de-duplicated series), not a
change to the zero-return definition itself. This is disclosed as a **pre-existing, session-wide
limitation** that likely affected the raw row-level queries in Stages 21, 23, 24, 26, and 27 as well
(none of them deduplicated before computing zero-return frequency) — flagged here for the record; fixing
those retroactively is out of scope for this instruction and not attempted.

---

## Post-fix eligible counts (corrected rule + de-duplicated data, rehearsal reference = 2026-08-07)

| Group | n tickers | Pass ≥30/40 min-obs | Median sessions present (of 40) |
|---|---|---|---|
| **TREATED (≥₦1,000)** | 9 | **7** | 39 |
| MID-BAND (₦500–999.99) | 6 | 5 | 39 |
| CONTROL (<₦500) | 124 | 116 | 39 |
| **INELIGIBLE** (no row on reference session) | 182 / 321 | — | — |

**Treated group detail** — the number that matters most for the eventual experiment:

| Ticker | Reference close | Sessions present (of 40) |
|---|---|---|
| AIRTELAFRI | ₦5,801.4 | 39 |
| ARADEL | ₦1,526.8 | 39 |
| DANGCEM | ₦1,034.0 | 39 |
| NESTLE | ₦2,750.0 | 39 |
| **NEWGOLD** | ₦104,000.0 | 23 — **fails min-obs** |
| OKOMUOIL | ₦1,418.0 | 39 |
| PRESCO | ₦2,070.0 | 39 |
| SEPLAT | ₦11,363.9 | 39 |
| **STANBICETF30** | ₦2,250.0 | 20 — **fails min-obs** |

**A genuinely new scope question, surfaced by this rehearsal, not resolved here**: NEWGOLD (a gold ETF)
and STANBICETF30 (an equity-index ETF) both clear the ≥₦1,000 price bar but are not ordinary equities —
whether the reform's rule even applies to them is unconfirmed (the "board/security-type scope caveat"
already logged as open in Stage 28B §1), and both independently fail the observation-count gate anyway.
**The clean, fully-qualifying treatment group is 7 tickers** (AIRTELAFRI, ARADEL, DANGCEM, NESTLE,
OKOMUOIL, PRESCO, SEPLAT), all with a full 39/39 session presence. This number — not 9 — should be the
working expectation for October.

## Placebo checks (re-run on corrected, de-duplicated data)

| Placebo | Treated Δ | Control Δ | Placebo DiD |
|---|---|---|---|
| 1 (2026-04-16→06-10 vs. 06-11→08-07) | +6.4pp | +8.1pp | **-1.7pp** |
| 2 (2025-12-25→2026-02-18 vs. 2026-02-19→04-15) | +1.0pp | +7.8pp | **-6.8pp** |

Smaller in magnitude than the pre-fix rehearsal (-3.0pp/-10.6pp), consistent with removing the duplicate-
row inflation, but the underlying caution stands unchanged: with a 7-9-ticker treatment group, several
percentage points of DiD noise is achievable with zero real effect. The real October result still needs
to clear this kind of noise floor, not just zero, exactly as Stage 28C found and Stage 28B §3 already
requires (exact permutation test, not a trusted asymptotic p-value).

## Pre-trend rehearsal (corrected)

| Group | First half | Second half |
|---|---|---|
| Treated (n=9) | 71.5% | 84.8% |
| Mid-band (n=6) | 80.4% | 79.8% |
| Control (n=124) | 54.3% | 51.8% |

The treated group shows a non-trivial rise within this rehearsal window alone (+13.3pp) — worth watching,
not alarming on its own (a 20-vs-20-session split of an arbitrary recent window, not the real pre-period),
but it means the real pre-trend check (Stage 28B §5) needs to be taken seriously rather than assumed to
pass by default.

---

## Does the protocol remain internally executable?

**Yes.** Every mechanical piece — outcome definition (now with the deduplication clarification), treatment
rule (now unambiguous), suspension/newly-listed handling, minimum-observation gate, DiD/clustering/
permutation machinery, placebo construction — runs cleanly end to end on real, current, pre-reform data.

## Remaining data limitations, for the record

1. **The 54 genuinely-conflicting duplicate pairs** are resolved by `keep="last"`, matching platform
   convention, but the *reason* they conflict (which source is more trustworthy) has not been
   investigated — immaterial at 0.02% of duplicate pairs, not pursued further here.
2. **ETF scope ambiguity** (NEWGOLD, STANBICETF30) — unresolved, and now concretely relevant since they
   sit in the price-level treatment band; both fail the observation gate regardless, so this doesn't block
   October, but should be settled before analysis, not during it.
3. **Board/security-type scope of the reform itself** remains unconfirmed against a primary NGX circular
   (open since Stage 28, still open here).
4. **Treatment group size is small and now precisely known**: 7 qualifying tickers. Every inferential
   method in the frozen protocol (exact permutation, cluster-robust with small-G caveats) was chosen with
   exactly this scale in mind — this is confirmation the design anticipated the real constraint correctly,
   not a new problem.

## Status

**WAIT.** 0 post-2026-08-17 trading sessions exist. No DiD was run. No hypothesis was registered. No
backtest. No parameter was tuned in response to any number produced in this document. The next action
remains calendar-driven: re-open Stage 28B once `equity_prices` contains ≥40 genuine post-2026-08-17
sessions for the 7-ticker treated group, and run §3/§5 exactly as amended.
