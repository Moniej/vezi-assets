# Stage 28E — Data-Integrity Audit: `equity_prices` Duplicate/Conflicting Rows

**Date:** 2026-08-09. Data-integrity audit only. No post-2026-08-17 data used (confirmed: latest
`trade_date` after correction is 2026-08-07). No DiD run, no hypothesis registered, no backtest. The
frozen Stage 28B treatment/control definitions, outcome definition, windows, DiD estimator, placebo
tests, and kill criteria are **unchanged** — this stage adds one further logged amendment strictly to
*how the underlying table is read*, not to any threshold or design choice. Scripts:
`scripts/stage28e_conflict_resolution.py`. Raw output: `data/staging/stage28e/`,
`data/staging/stage28e_conflicts_full.csv`.

---

## 1–3. The 54 conflicting pairs — full audit

Every one of the 54 conflicting `(ticker, trade_date)` pairs was pulled with all fields
(`open, high, low, close, volume, value_traded, deals, source_id, confidence, as_of_date, inserted_at`).
Programmatic verification across all 54 groups:

- **OHLC unanimous in 54/54 groups** — `open`, `high`, `low`, and critically **`close`** are byte-identical
  across every duplicate row in every conflicting group, with zero exceptions.
- **The conflict is confined entirely to `volume`/`value_traded`/`deals`.**

**Root cause identified, not guessed**: in every group, the "conflicting" rows split into two patterns:

- One or two rows with `volume` inflated by roughly **11 orders of magnitude** (e.g. ACCESSCORP
  2025-02-05: `volume=4.732180×10^19`) and `value_traded = NULL` — a known parser defect. This matches
  `ingest_pricelists.py`'s own documented history: "v1 = original word-position parse; **v2 adds glued
  VOLUME/VALUE token repair**" — i.e. v2 was written specifically to fix this exact class of bug.
- One row (always exactly one, in all 54 groups) with a **sane** `volume` (matching realistic NGX daily
  turnover) and a populated, internally-consistent `value_traded`.

**Provenance**: the corrupted rows appear both under `source_id=11` (`ngx_pricelist_v1`, first inserted
2026-07-17) *and* under `source_id=18` (`ngx_pricelist_v2`, inserted 2026-08-09 — today's Fix 4 run). The
correct row, in every case, was inserted **2026-07-21** under `source_id=11`. This means: v2's fix did not
actually re-parse these specific dates today — `parse_pricelists.py`'s own documented behavior ("staging
is version-blind... old dates are already in the DB and skipped") caused today's run to re-ingest an
**already-corrupted cached parse** rather than genuinely re-deriving it, reproducing the original v1 bug
under a new `source_id` label. The correct value came from an independent, apparently one-off, re-harvest
on 2026-07-21 that happened to get it right (`value_traded` populated, plausible magnitude) but never
overwrote the original bad row, because ingestion is append-only by design.

**Classification**: this is **duplicate ingestion of a known, partially-fixed parser defect**, not a
genuine conflicting source observation, not a legitimate revision series, and not random noise. It is a
gap in how the v1→v2 parser fix actually gets applied to already-staged historical files, disclosed here
as a finding for the data-engineering backlog, not fixed at that level in this audit.

## 4. Do any of the 54 dates touch the frozen protocol's live surfaces?

| Surface | Affected? |
|---|---|
| 2026-08-17 treatment assignment (bucket membership) | **No** — assignment depends solely on `close`, which is unanimous in all 54 groups |
| Pre-period zero-return measure (§2's primary outcome) | **No** — same reason; the outcome is defined purely on `close` |
| Eventual 40-session post-period | Not yet reachable (no post-reform data exists); the same immunity will hold once it is, since the outcome remains close-only |
| ≥30/40 minimum-observation requirement | **No** — session presence is counted by row existence per `(ticker, trade_date)`, unaffected by which duplicate's volume field is chosen |
| **Volume-dependent secondary measures** (genuine-trade vs. missing split; the deferred §4 economic/liquidity gate) | **Yes, materially, for 3 dates**: `ARADEL 2026-06-15`, `ARADEL 2026-06-30`, `SEPLAT 2026-07-16` all fall inside the rehearsal 40-session pre-period window for the treated group. Without the fix in §6 below, a naive `keep='last'`-by-`source_id` rule would have silently selected the *corrupted* ~10^19-magnitude volume for these three treated-ticker sessions. |

**Conclusion: the frozen protocol's primary DiD is fully immune to this issue.** It exists entirely in a
field the primary outcome never reads. It does, however, directly threaten the *already-planned but
deferred* §4 economic gate, which explicitly depends on volume/ADTV — worth having caught now rather than
when that stage actually runs.

## 5–7. Resolution rule — deterministic, not outcome-chosen

1. **OHLC fields**: any deterministic tie-break is safe (100% agreement) — `keep='last'` by
   `(ticker, trade_date, source_id)` retained, unchanged from Amendment 3.
2. **Volume/value_traded/deals**: **prefer the row(s) with a non-null `value_traded`.** If exactly one
   distinct non-null `value_traded` value exists among a group's rows (whether carried by one row or
   several agreeing rows), that value is used — confirmed to resolve all 54 conflicting groups cleanly and
   uniquely, with zero remaining ambiguity. If a group has **multiple distinct** non-null `value_traded`
   values (genuine, unresolvable disagreement), the observation is marked **AMBIGUOUS** and excluded
   (`volume`/`value_traded`/`deals` set to null) rather than guessed. **This case occurred 0 times** across
   the full table. If **no** row in a group has a non-null `value_traded` at all, the observation is marked
   **UNRESOLVED** (fallback to whatever `volume` value exists, explicitly flagged, not silently trusted) —
   this occurred for **18,700 ticker-date rows** platform-wide, a distinct and separate, pre-existing data
   gap (dates where no source ever captured `value_traded`), not part of the 54-conflict issue and not
   fabricated here.

This rule was derived from the data's own internal completeness pattern (which row has the
information the outcome needs), not from which choice produces a more favorable result — no return, no
DiD, no zero-return frequency was computed before this rule was fixed.

## 8. Did the existing Stage 21/28B/28D code already handle this deterministically?

**No, not correctly, until this stage.** Stage 21's original scripts and Stage 28D's Amendment 3
(`drop_duplicates(subset=["ticker","trade_date"], keep="last")`, sorted by `source_id`) would have — for
these specific 54 groups — **silently kept the corrupted volume row** whenever `source_id=18` (today's
re-ingest) was the highest `source_id` present, since `keep='last'` under that sort order picks the
highest `source_id`, not the most complete row. This is corrected here (§6) via a value-completeness rule
instead of a source-id ordinal rule. `backtest_xs.load_panel()`, the platform's core, long-used canonical
panel function, uses the same naive `keep='last'` convention — **this is a real, disclosed latent
limitation of that shared function too**, surfaced by this audit, not fixed here (out of scope — it
affects the `close`-only read path not at all, given OHLC's 100% agreement, so no prior backtest result
that only used `close` is affected by it; anything that used `volume`/`value_traded` from `load_panel()`'s
output should be re-checked separately, not attempted in this audit).

## 320 vs. 321 ticker-count discrepancy — explained

`ingest_pricelists.py` auto-registers any newly-seen ticker symbol into `securities` via
`INSERT OR IGNORE INTO securities (ticker, name, notes) VALUES (?, ?, 'auto from ngx_pricelist ingest')`
— existing, by-design behavior, not something introduced by this session's fixes. `securities` grew from
320 (Stage 28C's snapshot, before Fix 4) to 321 (Stage 28D onward) as a direct, mechanical consequence of
Fix 4's price-feed refresh encountering a ticker not previously registered.

Of the 4 tickers flagged in Stage 28D as "newly listed" (first `equity_prices` row after the rehearsal
pre-period start): **ABBEYBANK and CMFC already existed before today** (confirmed — both appear with price
history in `market_cap_panel.csv`, a reference file that predates today's refresh). **AVACAP has zero
prior footprint anywhere** (absent from `market_cap_panel.csv`, and its first trade date, 2026-07-31,
falls strictly after the pre-fix data cutoff of 2026-07-21) — this is the best-evidenced candidate for the
genuinely new 321st entrant. **HBMNG is inconclusive** from available evidence (absent from
`market_cap_panel.csv`, but its first trade date of 2026-07-09 technically predates the old cutoff, so it
cannot be ruled out as already-registered before today). No pre-refresh snapshot of the full `securities`
table was captured, so this cannot be pinned down with full certainty — disclosed as a minor, non-blocking
limitation of this retrospective investigation, not a live risk to the protocol (all 4 candidates are
either outside the treated/control price bands or, if in them, would be governed by the same eligibility
rules as any other ticker).

## 9. Re-run of pre-reform validation, corrected data, strictly pre-2026-08-17

| | Result |
|---|---|
| Latest `trade_date` after correction | 2026-08-07 (confirmed < 2026-08-17) |
| Treated (≥₦1,000) | 9 tickers, **7 pass** the ≥30/40 gate (unchanged from Stage 28D — confirms the volume fix does not alter bucket membership or eligibility, exactly as §4 predicted) |
| Mid-band (₦500–999.99) | 6 tickers, 5 pass (unchanged) |
| Control (<₦500) | 124 tickers, 116 pass (unchanged) |
| Ineligible (no reference-session row) | 182/321 (unchanged) |

**Every count is identical to Stage 28D's.** This is the expected, confirmatory result: since bucket
assignment and the primary outcome depend only on `close`, and `close` was never in dispute, fixing the
volume-resolution rule could not and did not change treatment/control membership or eligibility. The value
of this re-run is negative-result confirmation, not a changed number.

---

## Does the October experiment remain executable?

**Yes, cleanly, and now on firmer footing than before this audit.** The primary DiD was never at risk —
its only input field is unambiguous in 100% of the audited conflicts. What this audit fixed is a latent
risk to the **deferred §4 economic gate** (which needs real volume data) and to general data trustworthiness
going into October — both addressed via a disclosed, deterministic, non-outcome-dependent rule, logged as
**Amendment 4** to Stage 28B (data-engineering clarification only; no threshold, window, estimator, or
kill-criterion touched).

## Remaining blockers / limitations, for the record

1. **18,700 rows platform-wide have no `value_traded` from any source** — a distinct, pre-existing gap,
   unresolved (correctly marked unresolved, not guessed). Relevant only to the deferred §4 gate.
2. **The v1→v2 parser-fix gap**: `parse_pricelists.py` does not re-parse already-staged historical files
   even after a parser version bump, so the underlying defect can keep resurfacing on future re-ingests of
   old dates under new source-id labels. Not fixed here (data-engineering backlog item, out of scope for
   this audit) — future ingestion runs should be aware this class of stale-cache reproduction can recur.
3. **`backtest_xs.load_panel()`'s own naive `keep='last'` convention** carries the same latent risk this
   audit found for `equity_prices`' volume fields, for any future work that reads volume through it rather
   than through this stage's corrected rule. Flagged, not patched.
4. **320-vs-321 root cause is well-evidenced but not fully certain** for one of the four candidate tickers
   (HBMNG) — disclosed, non-blocking.

## Status

**WAIT — unchanged.** 0 post-2026-08-17 trading sessions exist. No DiD was run. No hypothesis. No
backtest. No treatment threshold, window, outcome definition, estimator, placebo test, or kill criterion
was modified — only how the existing table's volume field is read, logged as Amendment 4.
