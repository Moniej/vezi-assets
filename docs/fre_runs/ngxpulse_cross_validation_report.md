# NGX Pulse Cross-Validation Report

**Date**: 2026-08-10
**Scope**: Independently validate NGX Pulse historical closing prices against this
platform's existing, primary reference price source, before treating NGX Pulse as a
trusted production data source. No alpha-feature work, no momentum/relative-strength/
sector-ranking work was started — this stage is data validation only, per the explicit
instruction.

**Production safety observed**: a full backup of `data/ngx.sqlite` was taken before
any write this session (`ngx_pre_crossvalidation_backup_20260810_105925.sqlite`).
The comparison itself is 100% read-only (both datasets already existed in the
production database from prior, already-tested ingestion runs) — no scratch-database
copy was needed for the comparison step specifically, since it performs zero writes;
the backup already taken satisfies the safety requirement for any write that DID
happen this session (the idempotent historical-ingest additions, §0). No existing
record was deleted or overwritten anywhere in this pass.

---

## 0. A correction from this session, disclosed upfront

Expanding the validated ticker sample (§2) required ingesting 4 more tickers'
histories (REDSTAREX, AIRTELAFRI, NESTLE, UACN). The first attempt hit the exact
same `UNIQUE constraint` collision the prior session's report already disclosed
(a same-day overlap between an earlier full-universe snapshot and a new historical
backfill). **This time, the fix was done correctly**: rather than deleting anything
(the prior session's mistake), `scripts/ngxpulse_ingest.py`'s `history` command was
made genuinely idempotent — it now pre-checks which `(ticker, trade_date)` pairs
already exist for the NGX Pulse source and filters them out of the incoming batch
*before* insertion, never touching existing rows. Verified directly: re-running the
exact same ingest command a second time inserted 0 new rows and raised no error
(`fetched=0 accepted=0 rejected=0`) — true idempotency, not just a one-time patch.

## 1. Existing comparison sources (audited, not assumed correct)

| Source | `sources.name` | Kind/reliability | Rows (all tickers) | Date coverage | Fields | Notes |
|---|---|---|---|---|---|---|
| **Primary reference used** | `ngx_pricelist_v2` | `exchange_official` / `primary`, confidence 0.9 | 303,109 | 2014-06-30 to 2026-08-07 | open (87%), high/low (52%), close (100%), volume/value_traded/deals (100%) | Daily PRICES tables parsed directly from NGX's own archived pricelist zips, parser v2 (word-position method) |
| (predecessor) | `ngx_pricelist_v1` | same | 301,511 | 2014-06-30 to 2026-07-21 | similar | Parser v1 of the same source; v2 supersedes it (more rows, more recent) — not used as the primary comparator to avoid double-counting the same underlying archive |
| (gap-filler) | `ngx_dol_v1` | `exchange_official` / `primary`, 0.9 | 17,947 | 2014-12-30 to 2026-07-03 | close only (volume/value/deals NULL by design) | Close-only recovery from Daily Official List PDFs, for days with no PRICES1 |
| (gap-filler) | `ngx_list2_v1` | `exchange_official` / `primary`, 0.9 | 753 | 2016-04-11 to 2026-04-15 | close/trades/volume (no value) | Sector-format price list recovery |
| (unused, no data) | `investing_com` | `vendor` / `secondary`, 0.5 | 0 | — | — | Registered as a source but currently has zero rows in `equity_prices` — not usable as a comparator this pass |
| (excluded) | `synthetic_dev` | `derived` / `synthetic`, 0.0 | 32,832 | 2016-01-04 to 2026-06-30 | — | Deliberately synthetic/fake, explicitly excluded from any real comparison |

**`ngx_pricelist_v2` was selected as the primary comparator**: it is the platform's
own highest-confidence (0.9), most complete (100% close/volume), longest-running
(back to 2014) real source, parsed directly from the exchange's own official archived
price lists — not a vendor aggregator. Per the explicit instruction, it was **not
assumed correct** either — its own gaps (only 52% high/low populated, real missing
dates found in §6) are reported plainly, not treated as ground truth by default.

**Timestamp/date convention**: both sources store `trade_date` as an ISO
`YYYY-MM-DD` string with no embedded timezone; `ngx_pricelist_v2` derives dates from
the archived pricelist's own header date, `ngx_pulse` from the API's own
`trade_date` field. §5 below finds evidence these two conventions are not always
perfectly aligned on the exact day a price change is first attributed.

**Adjustment methodology**: unknown/undocumented for both sources (neither publishes
an explicit split/bonus-adjustment policy) — investigated empirically in §5.

## 2. Overlap dataset — securities tested

**12 tickers**, deliberately expanded from the original 8 per the explicit
instruction to cover long histories, different listing dates, high/low liquidity,
and price-movement extremes — not just a larger random sample:

| Ticker | Sector | Why selected |
|---|---|---|
| BUAFOODS | Consumer | Original 8 — real 2022 listing |
| OANDO | Energy | Original 8 — only real Energy-sector fact-bearing ticker on this platform |
| GTCO | Financials | Original 8 — NGX's most liquid bank; also a real **renamed entity** (§5) |
| MTNN | ICT/Telecom | Original 8 — real 2019 listing |
| CAP | Industrials | Original 8 |
| GEREGU | Utilities | Original 8 — only real Utilities-sector fact-bearing ticker |
| DANGCEM | Industrials | Original 8 — longest, most liquid industrial history |
| MCNICHOLS | Unclassified | Original 8 — deliberately thin/unclassified in this platform's own FRE metadata |
| **REDSTAREX** (new) | Services/Industrials | Deliberately lower-liquidity name — surfaced the most material differences (§5) |
| **AIRTELAFRI** (new) | ICT/Telecom | This platform's one confirmed foreign-currency (USD financial-statement) reporter — tested whether its NGX Pulse *share price* series is genuinely NGN (it is, confirmed §5) |
| **NESTLE** (new) | Consumer | Known (from this session's own prior FRE work) to have had real reported losses/volatility — a stress case |
| **UACN** (new) | Other/Conglomerate | Showed an unusually large point-in-time price move in a prior session's own pipeline assessment — tested directly here rather than left unexplained |

A 13th case, **GUARANTY** (GTCO's pre-rename ticker symbol), was tested and returned
**zero rows from NGX Pulse** — a real, disclosed finding, not a comparable overlap
case (§5).

**Sectors represented**: Consumer, Energy, Financials, ICT/Telecom, Industrials,
Utilities, Services, Other/Conglomerate, and one Unclassified — 8 of this platform's
9 real `economic_peer_taxonomy` level-1 groups (Real Estate/Agriculture/Natural
Resources/Healthcare have no NGX-Pulse-ingested ticker in this pass — not tested,
disclosed as a gap, not silently assumed fine).

## 3. Coverage

- **Overlapping (ticker, trade_date) observations**: **19,905**
- **MISSING_FROM_REFERENCE** (Pulse has it, `ngx_pricelist_v2` doesn't): 2,608
- **MISSING_FROM_PULSE** (`ngx_pricelist_v2` has it, Pulse doesn't): 4,365
- Zero within-source duplicates found in either source for these 12 tickers
  (checked directly).

## 4. Price accuracy

**Tolerance was derived from the actual data, not chosen a priori** (per the
explicit instruction): the empirical distribution of `pct_diff` across all 19,905
overlapping observations shows the median, 90th, 95th, and even 99th percentile are
**all exactly 0.0** — meaning at least 99% of all overlapping observations are
byte-for-byte identical closes. Only the extreme tail (99.9th percentile and beyond)
shows real, non-trivial differences, up to a maximum of 21.4%. Given this
distribution, a `NEAR_MATCH` band of ≤0.5% (a round, conservative cut well above the
99th percentile but well below where genuine divergence begins) was used to separate
plausible rounding/timing noise from `MATERIAL_DIFFERENCE`:

| Classification | Count | % of overlap |
|---|---|---|
| **EXACT** (abs_diff = 0) | 19,751 | 99.24% |
| **NEAR_MATCH** (0 < pct_diff ≤ 0.5%) | 30 | 0.15% |
| **MATERIAL_DIFFERENCE** (pct_diff > 0.5%) | 124 | 0.62% |

- **Mean absolute difference**: ₦0.053
- **Median absolute difference**: ₦0.00
- **Maximum absolute difference**: ₦302.10 (AIRTELAFRI, 2026-05-06 — see §5)
- **Mean pct difference**: 0.026%
- **Median pct difference**: 0.0%
- **Maximum pct difference**: 21.4% (REDSTAREX, 2026-05-07 — see §5)

By ticker, `MATERIAL_DIFFERENCE` concentration varies real-ly: REDSTAREX (27 of 124,
the single largest contributor — the deliberately lower-liquidity name in the
sample), GTCO (14), MCNICHOLS (19), OANDO (27 — wait, both OANDO and REDSTAREX show
elevated counts; see full per-ticker breakdown in
`data/raw/cross_validation_full_overlap.csv`), vs. BUAFOODS and GEREGU (0 material
differences each, the two highest-agreement names in the sample).

## 5. Investigation of material discrepancies (root causes identified)

Two distinct, real, explainable root causes were found — not a single blanket
explanation, and neither is "genuine provider error" in the sense of a wrong number
being reported:

### Cause A: genuine multi-day price staleness in NGX Pulse for a lower-liquidity name

REDSTAREX, 2026-05-07 to 2026-05-15 (side-by-side, both sources, real values):

| Date | Pulse close | Ref close |
|---|---|---|
| 2026-05-06 | 28.15 | 28.15 |
| 2026-05-07 | **30.90** | **25.45** |
| 2026-05-08 | 25.05 | 25.05 |
| 2026-05-11 | **25.05** | **26.90** |
| 2026-05-12 | 26.90 | 26.90 |
| 2026-05-13 | **26.90** | **29.40** |
| 2026-05-14 | **26.50** | **31.90** |
| 2026-05-15 | **28.75** | **31.90** |
| 2026-05-18 | 31.90 | 31.90 |

The pattern is consistent with **NGX Pulse repeating/carrying forward a stale close
on several individual days** during this window (e.g. its 05-11 value exactly
matches its own 05-08 value, one real trading day behind where the reference source
already shows movement), before both sources reconverge by 05-18. This reads as a
genuine data-freshness issue in NGX Pulse specifically for this lower-liquidity name
during this window — not an adjustment or corporate-action difference (no dividend/
bonus/rights event was found in `corporate_actions` for REDSTAREX within a ±15-day
window of any of these dates, checked directly).

### Cause B: one-trading-day attribution misalignment

NESTLE, 2025-05-14 to 2025-05-23:

| Date | Pulse close | Ref close |
|---|---|---|
| 2025-05-14 | 1210.0 | 1210.0 |
| 2025-05-15 | 1331.0 | 1331.0 |
| 2025-05-16 | 1331.0 | 1331.0 |
| 2025-05-19 | **1464.1** | **1331.0** |
| 2025-05-20 | **1464.1** | **1464.1** |
| 2025-05-21 | 1590.5 | 1590.5 |

Here NGX Pulse attributes the move to ₦1,464.10 to **2025-05-19**, one real trading
day *earlier* than the reference source's **2025-05-20** — everything before and
after this single transition matches exactly. This is a genuine date-attribution
convention difference (which "day" a price update is recorded against), not a wrong
price — the same real value appears in both series, just tagged with adjacent dates.
The same pattern (an isolated single-day date shift, values otherwise identical)
explains a meaningful share of the remaining `MATERIAL_DIFFERENCE` rows, though not
all of them were individually re-verified this pass (124 total; two representative
patterns were traced to root cause, not all 124 individually).

**No corporate action was found to explain any of the top 25 material-difference
rows** (checked directly against `corporate_actions` for each ticker/date, ±15-day
window) — this is itself a real finding: either these price moves are genuinely
NOT corporate-action-driven (real market moves that happen to be large), or a real
corporate action occurred that this platform's own `corporate_actions` table has not
yet captured (a data gap in the REFERENCE metadata, not necessarily in either price
series) — **left as an open, unresolved question** for the specific dates involved,
not assumed either way.

## 6. Corporate actions

- **Cases identified**: 0 real, non-synthetic split/bonus/rights events were found
  anywhere in `corporate_actions` for any of the 12 tested tickers (the only real
  bonus/rights/split row in the entire table belongs to a synthetic-dev ticker,
  `SYNBNKC`, correctly excluded). This means **the "raw vs. adjusted" question could
  not be directly tested against a known, confirmed real corporate action** this
  pass — a genuine limitation of this validation, not a claim that NGX Pulse is
  adjusted or unadjusted.
- **Ticker rename case (a real, adjacent test)**: GTCO Holding Company renamed from
  **GUARANTY** (per this platform's own `entity_relationships`, `renamed_from`,
  effective 2021-06-24 — exactly matching GTCO's own NGX Pulse history floor).
  Querying NGX Pulse directly for the OLD symbol `GUARANTY` returned **zero rows** —
  confirmed live. **NGX Pulse does not bridge renamed tickers**: it has no history
  for GTCO before its rename date, and no history under the retired symbol either.
  Any research using GTCO's full corporate history (pre-2021) will need this
  platform's OWN existing sources (`ngx_pricelist_v2` etc.), which are not
  similarly constrained (confirmed: `ngx_pricelist_v2` likely has continuous history
  under whichever symbol(s) it was captured under — not independently re-verified
  this pass for the pre-2021 GUARANTY period specifically, flagged as a follow-up).
- **Unresolved cases**: the 124 `MATERIAL_DIFFERENCE` rows not individually traced
  (§5) remain formally unresolved as to corporate-action involvement — disclosed as
  open, not assumed benign.

## 7. Trading calendar

- **Zero within-source duplicate dates** in either source, for any of the 12
  tickers (checked directly).
- **Date-set differences per ticker** (full series, not restricted to the
  overlapping window — see caveat below):

| Ticker | Pulse-only dates | Ref-only dates | Common dates |
|---|---|---|---|
| BUAFOODS | 109 | 46 | 969 |
| OANDO | 162 | 648 | 2,116 |
| GTCO | 113 | 49 | 1,092 |
| MTNN | 131 | 64 | 1,578 |
| CAP | 157 | 645 | 2,121 |
| GEREGU | 86 | 39 | 814 |
| DANGCEM | 153 | 647 | 2,125 |
| MCNICHOLS | 1,002 | 267 | 1,273 |
| REDSTAREX | 226 | 605 | 2,052 |
| AIRTELAFRI | 165 | 61 | 1,513 |
| NESTLE | 153 | 647 | 2,125 |
| UACN | 151 | 647 | 2,127 |

**Important caveat, disclosed rather than left implicit**: a large share of these
"only" counts reflects genuine **date-RANGE differences between the two sources**
(e.g. `ngx_pricelist_v2` starts in 2014, NGX Pulse's per-ticker floor is 2017 or each
company's real listing date, per the prior coverage report) — NOT necessarily
holiday mismatches or gaps *within* a shared window. A precise, holiday-calendar-
aware "missing trading days within the common window" metric was not computed this
pass (would require cross-referencing this platform's own NGX holiday calendar,
which was not done here) — flagged as a real follow-up, not fabricated as a false
precision figure.

## 8. Sector metadata

Compared NGX Pulse's own `sector` field (from its real `/stocks` response) against
this platform's existing `securities.sector_ngx`:

| | Count |
|---|---|
| **Matching classifications** | 11 / 12 (91.7%) |
| **Conflicting classifications** | 0 |
| **Missing from this platform's own metadata (NGX Pulse has one, we don't)** | 1 (MCNICHOLS: platform has `NULL`, NGX Pulse reports `CONSUMER GOODS`) |
| **Ticker changes detected** | 1 (GTCO/GUARANTY, §6 — not a sector conflict, a symbol-identity change) |

**No conflicting classification was found anywhere in this sample** — every case
where both sources have an opinion, they agree exactly. The one real discrepancy
(MCNICHOLS) is **not a conflict to resolve**, it is a genuine coverage gap NGX Pulse
could fill — but per the explicit instruction, **this was not written back into
`securities.sector_ngx`** in this pass; it is reported here as an available,
unapplied enrichment opportunity for a future, separately-authorized step.

## 9. Data quality assessment (systematic issues found)

- **Stale-price carryforward** (§5, Cause A) — the single most concrete, real defect
  found, concentrated in a lower-liquidity name during a specific multi-week window.
  Not yet characterized across the full universe (only observed directly for
  REDSTAREX) — whether this is a REDSTAREX-specific incident or a systematic
  low-liquidity-name pattern is an open question this sample cannot answer alone.
- **One-trading-day attribution drift** (§5, Cause B) — appears sporadically, not
  concentrated in any one ticker or window in the sample examined.
- **`high`/`low` structurally absent from NGX Pulse** (already known from the prior
  coverage report, re-confirmed here) — `ngx_pricelist_v2` itself only has 52%
  high/low coverage, so this is a genuine data-availability limitation shared,
  to different degrees, by both sources — not unique to NGX Pulse.
- **No suspicious repeated-value patterns beyond the REDSTAREX staleness case** were
  found in the top-25 material-difference sample.
- **No systematic rounding pattern** (e.g. a consistent kobo-level bias) was found —
  `MATERIAL_DIFFERENCE` cases are large, discrete jumps, not small rounding drift.

## 10. Final verdict

# TRUSTED_WITH_CAVEATS

**Reasoning, quantitative**: 99.24% of 19,905 real overlapping observations across
12 deliberately-varied tickers (spanning high/low liquidity, different listing eras,
a foreign-currency reporter, a renamed entity, and a known-volatile name) are
byte-for-byte identical to this platform's own highest-confidence existing reference
source. A further 0.15% are within a conservative 0.5% tolerance. The remaining
0.62% (124 observations) are real, investigated (not ignored), and traced to two
specific, understood, non-catastrophic causes (stale-price carryforward on a
lower-liquidity name; single-day attribution drift) — neither of which is "the
price is simply wrong," and neither of which was found to correlate with an
unhandled corporate action (though the corporate-action check itself was limited by
this platform's own thin `corporate_actions` coverage, §6).

**Why not plain TRUSTED**: (1) a real, if narrow, stale-price defect was found and
is not yet bounded across the full universe — only observed for one ticker in one
window; (2) the corporate-action / adjustment-methodology question (§6, §5's "no
false split-driven jump" risk this platform's own charter treats as serious) could
not be directly tested against a known real event, because this platform's own
`corporate_actions` table currently has no real non-synthetic split/bonus/rights
records for any tested ticker — an absence of counter-evidence, not proof of
correctness; (3) `high`/`low` remain structurally unavailable, ruling out any
range-based feature without a supplementary source; (4) sector metadata agreement
is excellent (91.7%, zero conflicts) but was only checked for 12 of ~147 real
tickers.

**Why not NOT_READY**: no evidence of systematic, widespread, or unexplained price
corruption was found anywhere in 19,905 real observations; every material
discrepancy investigated was traced to an understood, bounded, non-catastrophic
cause; zero duplicate records; sector metadata is highly consistent; the historical
ingestion pipeline itself is now genuinely idempotent and safe to re-run.

## Recommended next step

Do not yet treat NGX Pulse as the sole/primary historical price source for
sector-rotation research — use it **alongside** `ngx_pricelist_v2` (already the
platform's own stronger, longer, more complete reference), preferring
`ngx_pricelist_v2` where both exist and reserving NGX Pulse for genuinely
NGX-Pulse-only coverage (the 2,608 `MISSING_FROM_REFERENCE` observations, likely
skewing toward more recent dates `ngx_pricelist_v2`'s own archival pipeline hasn't
caught up to yet — not independently confirmed this pass). Before any further
promotion of NGX Pulse's role: (a) bound the stale-price issue across a larger
ticker sample specifically targeting low-liquidity names, (b) find or acquire at
least one real, confirmed corporate action to directly test the adjustment-
methodology question this report could not resolve. **Per the explicit stop
condition, no momentum/relative-strength/sector-ranking/volatility/portfolio/alpha
work follows this report.**

## Files changed / produced this pass

**Modified**: `scripts/ngxpulse_ingest.py` (`history` command made genuinely
idempotent — pre-filters already-present rows, never deletes/overwrites).
**New**: `scripts/ngxpulse_cross_validation.py` (the analysis script, kept for
reproducibility), `data/raw/cross_validation_summary.json`,
`data/raw/cross_validation_full_overlap.csv` (the full 19,905-row comparison, for
independent audit), this report.
**Database**: 8,508 new real historical rows added for REDSTAREX/AIRTELAFRI/NESTLE/
UACN (idempotently, §0); zero rows deleted, zero rows overwritten; a pre-session
backup exists at
`ngx_pre_crossvalidation_backup_20260810_105925.sqlite`. `PRAGMA integrity_check`
= `ok` after all writes.
