# Stage 24 — Insider-Dealing Adversarial Diagnostic

**Date:** 2026-08-09
**Status:** Mechanism-discovery diagnostic only. No hypothesis, no factor, no H-024, no backtest, no
alpha claimed. Script: `scripts/stage24_insider_dealing_diagnostic.py`. Raw output preserved at
`data/staging/stage24/` (`all_filings_classified.csv`, `aggregated_events.csv`, `event_returns.csv`,
`event_returns_with_mcap.csv`). All parameters (aggregation window, PIT boundary, horizons, benchmark,
cost model, size control) were frozen in the script's own docstring **before** any return was examined.

**Question:** does publicly disclosed insider dealing contain incremental, persistent, tradeable
information on NGX after controlling for H-011 and realistic execution costs?

---

## 1–2. Extraction, classification, null-ticker resolution

163 filings → 83 genuine PURCHASE + 26 genuine SALE + 6 vesting (excluded) + 48 unusable (unchanged from
Stage 23 — the 40 scanned-image PDFs remain blocked on the same pending OCR decision, not resolved here).

**Null-ticker resolution: 15/15 resolved**, improving on Stage 23's 0/15. Method: a self-referential
issuer-name whitelist built *only* from rows in this same corpus that already carry a correct ticker (14
filings' stated issuer "Nigerian Breweries Plc" exact-matched against other corpus rows already ticked
`NB`; 1 filing's "Airtel Africa Plc" matched against rows already ticked `AIRTELAFRI`). No external
knowledge or fuzzy filename matching was used — this is deterministic, disclosed, and auditable
(`all_filings_classified.csv` carries the method for every row).

## 3. Concentration (raw filings, ticker-resolved corpus, n=109)

UCAP 35, NB 16, INITSPLC 14, FCMB 9, SEPLAT 8, UBA 8, AIRTELAFRI 6, plus 6 smaller tickers. Shares field
usable: 78/109 (72%); consideration (value) usable: 71/109 (65%).

## 4+6. PURCHASE/SALE split and event aggregation

83 PURCHASE / 26 SALE raw filings **collapse to 67 events** (53 PURCHASE / 14 SALE) once aggregated by
(insider × ticker × direction × calendar month) — confirming Stage 23's concentration finding was real:
a meaningful fraction of raw filings were repeated disclosures from the same insider in the same month,
not independent observations. Post-aggregation: 14 unique tickers, 53 unique insiders, top-3 tickers
(UCAP/UBA/SEPLAT for PURCHASE) = 56.7% of all events, top-5 = 73.1%. **This concentration is the single
most important caveat on everything that follows** — effective breadth is closer to a handful of names
than 67 suggests.

## 5. Routine/scheme flag

Deterministic keyword scan (ESOS, share incentive/purchase plan, dividend reinvestment, scrip dividend)
found **zero** additional routine transactions among the 109 genuine filings — the vesting exclusion at
classification already captured the only routine-transaction pattern present in this corpus. Reported as
a genuine negative finding, not a failed check.

## 7–10. PIT boundary and benchmark-relative returns at frozen horizons

`eligible_from` = first `equity_prices` session strictly after `filing_date` (Stage 14's own PIT
convention, reused unmodified). Benchmark: NGXASI (`index_levels`), same choice as Stage 21C for the same
reason (EW-IRU requires portfolio-construction machinery). Horizons frozen at 5/10/20/40/60 trading
sessions (60 matches H-020's own precedent).

| Direction | k | n | Mean excess | Median excess | naive t | % positive raw |
|---|---|---|---|---|---|---|
| PURCHASE | 5 | 53 | +1.23% | +0.28% | 1.54 | 60.4% |
| PURCHASE | 10 | 53 | +1.90% | +2.13% | 2.03 | 60.4% |
| PURCHASE | 20 | 53 | **+5.74%** | **+5.15%** | 3.97 | 77.4% |
| PURCHASE | 40 | 52 | +2.80% | -0.60% | 1.47 | 67.3% |
| PURCHASE | 60 | 52 | +1.68% | +2.24% | 0.94 | 67.3% |
| SALE | 5 | 14 | -3.34% | -0.06% | -1.01 | 28.6% |
| SALE | 10 | 14 | -6.26% | -4.33% | -1.10 | 35.7% |
| SALE | 20 | 14 | -13.09% | -3.35% | -1.42 | 35.7% |
| SALE | 40 | 14 | -17.31% | -5.63% | -1.59 | 28.6% |
| SALE | 60 | 14 | -21.38% | -4.61% | -1.94 | 28.6% |

*t-stats use a naive i.i.d. assumption (same caveat as Stage 21C) and are almost certainly overstated
given shared tickers/periods across events — not treated as a rigorous significance claim.*

**PURCHASE is directionally consistent and improves with horizon up to k=20** (majority-positive at every
horizon, 77% positive at k=20 specifically), then weakens at k=40/60 (median goes negative at k=40) —
consistent with information being incorporated over roughly a month and then noise/reversal dominating,
though n=52-53 is too small to be certain this isn't just sampling variation.

**SALE is directionally consistent (negative at every horizon) but the magnitude is not reliable** — see
§12's raw-vs-aggregated sensitivity check below, which found SALE's magnitude is highly sensitive to the
aggregation choice in a way PURCHASE is not.

## 8. H-011 independence — structural and correlational

**Mechanical: none**, reconfirmed directly from `size_scores()` (`src/ngxrot/backtest_xs.py:319`) — it
consumes only `panel["mcap"]` and price-panel IRU eligibility, nothing from `documents` or any
dealing-notice field.

**Correlational:** Spearman(excess_ret, market_cap_nm) = **+0.13** at both k=10 and k=20 (n=58, both
directions pooled) — weakly *positive*, the opposite of a small-cap story. By size tercile at k=20
(both directions pooled, a coarse cut — not separated by direction due to small per-cell n): Small
-6.75%/-1.66% (mean/median), Mid +5.88%/+5.15%, Large +3.23%/-1.09% — noisy and non-monotonic, no clean
size story either way. **This is not a disguised H-011 size effect**, but the pooled-direction tercile
cut is a real limitation of this pass, not a rigorous size-neutrality proof.

## 11. Cost/capacity gate — decisive for tradability

Round-trip cost (live `cost_schedule`, unmodified): **3.79%**.

- **PURCHASE clears cost only at k=20** (mean +5.74%, median +5.15%, both above 3.79%). Every other
  horizon (5, 10, 40, 60) fails on both mean and median.
- **SALE "clears cost" at several horizons in raw magnitude — but this is moot.** The platform is
  long-only by standing structural constraint (`docs/RESEARCH_ROADMAP_2026-07.md` §1: "No shorting on
  NGX → every factor is a LONG-ONLY tilt"). A negative-direction signal cannot be converted into a trade
  on this platform regardless of its magnitude or statistical strength. SALE's cost-gate numbers are
  reported for mechanism-diagnostic completeness only, not as evidence of a tradeable effect.

**This means the entire tradability question rests on PURCHASE at k=20 specifically** — a single horizon
out of five pre-specified, which survived because it was reported honestly alongside the four that
failed, not because it was selected after the fact.

## 12. Adversarial decomposition

- **Issuer concentration (PURCHASE-only, leave-top-3-out: UCAP/UBA/SEPLAT excluded, n=53→19):**
  k=20 mean weakens from +5.74% to **+3.60%** (median +5.15%→+4.76%) — still positive and still close to
  the cost floor, but the mean now falls *below* the 3.79% round-trip cost. k=10 weakens much more
  (mean +1.90%→+0.54%, median flips to -2.31%). **The effect is real but not fully independent of the
  top-3 tickers — roughly a third of its k=20 magnitude and most of its k=10 signal comes from
  UCAP/UBA/SEPLAT specifically.** (An initial pooled-direction version of this check showed an apparent
  full sign reversal — that was a direction-mixing artifact of combining PURCHASE and SALE before
  filtering; the corrected, direction-matched check above is the one that should be trusted.)
- **Extreme-observation sensitivity (PURCHASE, k=20, winsorized at 5%/95%):** mean +5.74% → **+5.28%**
  winsorized — a modest change. The single largest observation (+38.8%, SEPLAT/Udoma Udo Udoma,
  2024-09-27) and smallest (-14.8%) do not dominate the result; PURCHASE is *not* primarily a 1-2-outlier
  artifact.
- **Repeated-filing sensitivity (raw, non-aggregated vs. aggregated events):** PURCHASE is **robust** —
  raw (n=83) k=20 mean +6.35%/median +5.55% vs. aggregated (n=53) +5.74%/+5.15%, materially unchanged.
  **SALE is not robust** — raw (n=26) k=20 mean **-26.77%**/median **-40.41%** vs. aggregated (n=14)
  -13.09%/-3.35%, roughly a 2-4x difference. Repeated same-insider filings were inflating the raw SALE
  magnitude considerably; the aggregated figure is the defensible one, and even that carries a large
  mean/median gap (skew), consistent with a thin, outlier-sensitive sample (n=14).
- **Purchase/sale imbalance:** already separated throughout (§7-11) — not pooled anywhere a conclusion is
  drawn, except the one coarse independence tercile cut in §8, disclosed as a limitation there.
- **Stale-price / illiquidity cross-check (against Stage 21's own zero-return-frequency measure):**
  most corpus tickers are low-staleness (UBA 0.16, UCAP 0.18, FCMB 0.24 — liquid), but **SEPLAT (0.77)
  and AIRTELAFRI (0.92) are themselves high-staleness names** by the exact metric Stage 21 used before
  that mechanism was killed on cost grounds in Stage 21C. SEPLAT contributes the single largest positive
  PURCHASE observation (+38.8% at k=20). **This is a real, unresolved contamination risk**: part of the
  PURCHASE effect could be re-deriving the same mechanical stale-price pattern already found
  insufficient (and killed) in the illiquidity track, not a genuinely distinct insider-information effect.
  Not disentangled in this pass.
- **Corporate-action overlap:** 0/67 events have a `corporate_actions` row inside their [eligible_from,
  +20 sessions] window — clean, but this check is only as strong as `corporate_actions`' own coverage,
  which Stage 20 already found thin and inconsistent with `extracted_facts` (31 rows total, dividends and
  one rights issue only). A true zero-contamination claim would need the fuller `extracted_facts`
  corporate-action history cross-checked too — not done here, a disclosed limitation.
- **Survivorship:** not re-run in this stage; Stage 23's finding stands (no missing price data for any
  resolved ticker, but `securities.delisting_date` is NULL platform-wide, so this is not positive proof
  of survival, only absence of a specific failure mode).
- **Disclosure-timing artifacts:** the PIT boundary itself (first session strictly after `filing_date`)
  is conservative and unchanged from Stage 14's own convention; no separate weekday-clustering or
  batch-disclosure-lag test was run — a disclosed gap, not a claim of a clean result.

---

## Verdict: **CONDITIONAL GO** (PURCHASE only; SALE is diagnostically informative but untradeable)

A real, majority-directional, cost-clearing-at-one-horizon effect survives for insider PURCHASE
disclosures: positive at every horizon tested, robust to aggregation choice, not primarily driven by 1-2
extreme observations, not a disguised size effect, and — after direction-matched adversarial testing —
not *entirely* dependent on three tickers, though meaningfully weakened by their removal. That is a
materially stronger, more multiply-corroborated result than any track tested in Stages 18–21C, all of
which were killed outright.

It is not a GO, for four specific, nameable reasons:
1. **Horizon fragility** — only 1 of 5 pre-specified horizons (k=20, ≈1 month) clears transaction costs;
   the effect does not persist cleanly to 40 or 60 sessions.
2. **Issuer concentration** — roughly a third of the k=20 magnitude depends on UCAP/UBA/SEPLAT; the
   ex-top-3 mean (+3.60%) falls just under the cost floor, even though the median does not.
3. **Unresolved staleness contamination** — SEPLAT and AIRTELAFRI, two material contributors, are
   themselves high-staleness names by the exact measure that produced a killed, cost-failing mechanism in
   Stage 21C. This diagnostic cannot currently separate "insiders have real information" from "some of
   this is the same stale-price artifact already found insufficient elsewhere."
4. **Small, clustered sample** — 53 events (19 ex-top-3), naive uncorrected t-stats, and the standing
   25%-of-corpus OCR gap from Stage 23 all mean statistical confidence here is modest, consistent with
   this project's own repeated "six events is not enough" discipline.

SALE shows a real, consistent negative sign — useful as *mechanism validation* (insiders selling ahead of
bad news is economically coherent and corroborates the PURCHASE finding's plausibility) — but is
structurally untradeable on this long-only platform and its magnitude is not reliable (§12), so it cannot
move the verdict toward GO on its own.

## Single most important next step

**Separate the PURCHASE effect from the staleness confound before anything else**: re-run the k=20
PURCHASE diagnostic excluding SEPLAT and AIRTELAFRI (the two confirmed high-staleness tickers) and report
whether a positive, cost-clearing effect survives on the remaining, genuinely liquid names alone. If it
does, this becomes the strongest candidate this entire mechanism-discovery program (Stages 16–24) has
produced, and the next steps would be resolving the OCR/corpus-size gap and running a proper
cluster-adjusted significance test — still diagnostics, not a hypothesis. If it does not survive that
exclusion, the effect should be treated as substantially re-deriving the already-killed illiquidity
mechanism, not a genuinely independent one, and the insider-dealing track should be downgraded to NO-GO.

### Addendum (2026-08-09, same day): the exclusion check was run

| | All PURCHASE, k=20 (n=53) | Ex-SEPLAT/AIRTELAFRI (n=44) |
|---|---|---|
| Mean excess return | +5.74% | **+6.24%** |
| Median excess return | +5.15% | **+5.59%** |
| % positive (raw) | 77.4% | **90.9%** |
| Winsorized mean (5/95%) | +5.28% | +5.85% |
| Naive t-stat | 3.97 | **4.18** |
| Clears 3.79% round-trip cost? | Yes | Yes, comfortably |

**The effect survives and strengthens on every metric once the two confirmed high-staleness tickers are
removed** — it is not a re-derivation of the killed illiquidity mechanism. The remaining 44 events
(UCAP 20, UBA 8, FCMB 5, NB 5, DANGCEM 2, FLOURMILL 2, AIICO 1, UBN 1) are all low-to-moderate staleness
names, and winsorization barely moves the mean, so this is not a 1-2-outlier artifact either. Per the
decision rule this addendum was written to resolve: **this upgrades the insider-PURCHASE-at-k≈20 track
to the strongest candidate the entire Stages 16–24 mechanism-discovery program has produced.** It remains
a diagnostic finding, not a hypothesis — the concentration caveat (UCAP alone is still 20/44 = 45% of
this subsample), the single-surviving-horizon caveat, the naive/uncorrected t-stat, and the standing
25%-of-corpus OCR gap from Stage 23 are all still open and unresolved. The next step, if authorized,
would address those specifically (larger corpus, cluster-robust inference, sub-period stability) — still
diagnostic work, not a backtest or hypothesis registration.
