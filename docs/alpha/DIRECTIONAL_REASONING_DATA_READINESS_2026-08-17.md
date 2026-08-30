# Directional Reasoning — Data Readiness & Shadow-Alpha Program

*2026-08-17. Follow-up to `DIRECTIONAL_REASONING_REPAIR_AND_VALIDATION_2026-08-17.md` (Decision B).
This pass is a data-readiness audit, not further model-tuning: determines whether the two named
prerequisites (valuation data for H-011's sleeve; a larger genuine-contradiction sample) can actually
be acquired from EXISTING infrastructure before any V3 work is authorized. New code:
`build_filing_context()` added to `src/ngxrot/fre/directional_reasoning_v2.py` (Phase 5 only — no new
module). No schema change, no write path, no new LLM calls, no ingestion pipeline built.*

---

## 1. Current data coverage (Phase 0 — freeze)

| Check | Result |
|---|---|
| git HEAD | `c541e14` |
| Protected Alpha Engine files | Zero diff, confirmed before and after (`alpha_engine.py`, `engine_full.py`, `runner.py`, `registry.py`) |
| `REASONING_WEIGHT` | `0.0`, confirmed by direct import — unchanged |
| Broker/execution path | None exists anywhere on the platform (confirmed prior pass, re-verified: zero hits) |
| Production DB backup | Taken before any exploration: `data/backups/ngx_backup_2026-08-17_pre_data_readiness.sqlite` (154MB) |
| `extracted_facts` | 495 rows (321 financial-statement-shaped) |
| `financial_reasoning_conclusions` | 403 rows |
| `investment_implications` | 48 rows |
| H-011 ticker universe (current live basket) | 20 tickers, unchanged from `docs/fre_runs/engine_status_2026-08-17.txt` |
| H-011 sleeve tickers with ANY reasoning-layer coverage | 10 of 20 (MCNICHOLS, UNIVINSURE, CILEASING, CAVERTON, NCR, VERITASKAP, PRESTIGE, CUTIX, LASACO, REDSTAREX) |

No mutation performed. All queries below are read-only against the real production DB.

---

## 2. Valuation coverage by H-011 ticker (Phase 1–2)

**Reused, not rebuilt**: `valuation_engine.py` already sources shares-outstanding from
`data/reference/market_cap_panel.csv` (the same file `backtest_xs.py`/H-011 itself uses for sizing) via
`_shares_outstanding_millions()`. This was not obvious from the prior pass's framing ("no shares-
outstanding data exists") — that claim was **too broad**. Re-checked directly: all 10 sleeve tickers
**are** present in this panel, with genuinely PIT-varying `implied_shares_m` — confirmed by finding a
real corporate action (LASACO's share count jumps from ~1,834M to ~11,084M around 2025-01-23, exactly
matching the ₦18.47bn rights issue the reasoning layer's own bullish implication referenced). This is
real, historical, point-in-time data, not a static current snapshot silently back-filled.

| ticker | shares_outstanding | price | market_cap | P/E | P/B | dividend_yield | status |
|---|---|---|---|---|---|---|---|
| LASACO | AVAILABLE (11,083.6M) | AVAILABLE | **AVAILABLE** (₦21.9bn) | PARTIAL — own EPS computable (FY-tagged NGN net_profit+equity exist), but 0 comparable `insurance`-type peers have a computable P/E → `NOT_COMPUTABLE` at the ratio step | same as P/E | MISSING (no dividend fact) | **PARTIAL** |
| PRESTIGE | AVAILABLE (13,252.6M) | AVAILABLE | **AVAILABLE** (₦18.7bn) | MISSING — net_profit/revenue facts exist but `period_start`/`period_end`/`period_type` are **all NULL** | MISSING — no `equity` fact at all | MISSING | **PARTIAL** |
| CILEASING | AVAILABLE (2,948.6M) | AVAILABLE | **AVAILABLE** (₦16.5bn) | MISSING — same NULL-period issue | MISSING — no `equity` fact | **AVAILABLE** (₦0.20/share, 3.6% yield) | **PARTIAL** |
| REDSTAREX | AVAILABLE (954.4M) | AVAILABLE | **AVAILABLE** (₦17.2bn) | MISSING — same NULL-period issue | MISSING | MISSING | **PARTIAL** |
| VERITASKAP | AVAILABLE (13,866.7M) | AVAILABLE | **AVAILABLE** (₦18.6bn) | MISSING — NULL-period issue | MISSING — `equity` facts exist (2019/2020) but `currency=NULL`, not `'NGN'` — excluded by the adapter's own currency-exactness rule | MISSING | **PARTIAL** |
| CAVERTON | AVAILABLE (3,350.5M) | AVAILABLE | **AVAILABLE** (₦18.4bn) | MISSING — NULL-period issue | MISSING | MISSING | **PARTIAL** |
| CUTIX | AVAILABLE (7,045.3M) | AVAILABLE | **AVAILABLE** (₦18.3bn) | MISSING — NULL-period issue | MISSING | MISSING | **PARTIAL** |
| NCR | AVAILABLE (108.0M) | AVAILABLE | **AVAILABLE** (₦17.4bn) | MISSING — NULL-period issue | MISSING | MISSING | **PARTIAL** |
| MCNICHOLS | AVAILABLE (326.7M) | AVAILABLE | **AVAILABLE** (₦1.8bn) | MISSING — NULL-period issue | MISSING | **AVAILABLE** (₦0.06/share, 1.1% yield) | **PARTIAL** |
| UNIVINSURE | AVAILABLE (16,000.0M) | AVAILABLE | **AVAILABLE** (₦13.4bn) | MISSING — NULL-period issue | MISSING | MISSING | **PARTIAL** |

**PIT integrity, verified not assumed**: every value above was computed with `as_of` pinned to the real
filing/anchor date, using the same `_shares_outstanding_millions()`/`_latest_price()` PIT-lookback logic
`valuation_engine.py` already enforces (latest panel row on or before `as_of`, never a current value
silently reused for a historical date). Re-run at both a historical anchor date and today (2026-08-17)
for confirmation — the MISSING classifications above are genuinely structural (absent period metadata,
absent currency tag, absent peer coverage), not date-dependent gaps that would resolve on a different
`as_of`.

**EV/EBITDA: MISSING, permanently, platform-wide.** No `total_debt`/`cash_and_equivalents` fact_type has
ever been extracted anywhere on this platform (re-confirmed against the live `fact_type` distribution).
This is unchanged from the prior audit and is not something this pass could reuse its way around — it
requires new extraction work, out of scope for a data-readiness pass per the guardrail against
fabricating inputs.

**Bottom line, corrected from the prior pass**: `market_cap` is genuinely **AVAILABLE for 10/10** sleeve
tickers (a real capability, previously understated) and `dividend_yield` is **AVAILABLE for 2/10**
(CILEASING, MCNICHOLS — the only two with a recorded dividend fact). Full P/E and P/B remain blocked for
9/10 tickers by one specific, named, fixable defect: **`period_start`/`period_end`/`period_type` are
NULL on the underlying `revenue`/`net_profit` facts** — not a source-data absence. LASACO is the
exception (properly period-tagged) but is blocked one step later by **peer-group sparsity** (zero other
`insurance`-classified tickers have a computable P/E to compare against).

---

## 3. Expectations coverage (Phase 3)

**NONE.** Re-verified directly against the live schema: zero tables matching
analyst/estimate/consensus/expectation naming (same result as the prior pass). Also checked
`events.event_type` for anything guidance-adjacent: the full, real value list is `mpc_decision`,
`fx_regime_change`, `dividend_directive`, `insurance_recapitalisation`, `banking_directive`,
`naicom_directive`, `regulatory_action`, `fx_policy`, `energy_policy`, `management_change`,
`fuel_subsidy_change`, `recapitalisation_directive`, `ownership_change`, `resumption`,
`corporate_restructuring`, `capital_raise`, `merger` — no `FORMAL_CONSENSUS`, `COMPANY_GUIDANCE`, or
`HISTORICAL_EXPECTATION` source exists anywhere. Classification: **`EXPECTATIONS_UNAVAILABLE`**,
platform-wide, unchanged from the prior audit. Not compensated for by guessing, per guardrail.

---

## 4. Multi-fact filing coverage & the real root cause (Phase 4)

Audited why the contradiction engine has only seen n=1 real case. The answer is **not** scarcity of
genuine multi-factor filings:

| | count |
|---|---|
| documents with 2+ distinct financial-statement fact types (genuine multi-fact filings) | **50** |
| of those, documents where 2+ implications were actually generated | **11** |
| total eligible financial-statement facts | 321 |
| total implications ever generated | 48 |
| **implication-generation coverage rate** | **15%** (48 / 321) |

**The binding constraint is implication-generation coverage, not fact scarcity or a reasoning-quality
defect.** 39 of the 50 real multi-fact filings never had a second implication generated from their own
second/third fact at all — the reasoning layer simply hasn't been run on 85% of eligible facts yet. This
directly matches the prior report's separately-observed finding (§4c there) that the layer reasons
fact-by-fact with no filing-level synthesis — that architectural gap and this coverage gap are the same
underlying cause viewed from two angles.

---

## 5. Filing-context architecture (Phase 5)

Added `build_filing_context(con, doc_id, contradiction_index)` to the existing
`directional_reasoning_v2.py` module (no new file, no schema change). Produces the specified
`FilingContext` object: `facts[]`, `implication_ids[]`, `positive_factors[]`/`negative_factors[]` (real,
not invented — split by each fact's own already-generated implication direction), `valuation_context`
(real P/E/P/B point estimate when computable, else the literal string `"unavailable"`),
`expectation_context` (always `"unavailable"`, per §3), and `conflicts[]` from the existing
contradiction engine.

Verified against the VERITASKAP worked example: `positive_factors=('revenue',)`,
`negative_factors=('net_profit',)`, `conflicts=(39, 40)` — matches §3 of the prior report exactly. 4 new
regression checks added; **23/23 total pass** in `scripts/fre/test_directional_reasoning_v2.py`.

This is a genuine, tested, reusable building block for a future V3 — but per Phase 7's own instruction,
**it is not wired into anything**; it exists as a queryable data structure, not an active pipeline.

---

## 6. Contradiction sample size (Phase 6)

**Target was 25 minimum, 50+ preferred. Actual: reported honestly, not manufactured.**

- **Same-filing opposing directional implications (the exact Phase 2 definition): still n=1**
  (VERITASKAP). No new LLM calls were made to inflate this — per guardrail 10, that would be
  manufacturing contradictions, not discovering them.
- **A second, legitimate, deterministic conflict signal was checked**: reused
  `financial_health_flags.py`'s own three existing rules (`leverage_increasing`,
  `cash_flow_earnings_divergence`, `margin_compression`), applied PIT-correctly
  (`period_end <= anchor_date`, the same fix from the prior pass) against all 37 directional
  implications currently in the database. Result:

  | classification | n |
  |---|---|
  | `MATERIAL_CONFLICT` (bullish call, a real PIT-available warning flag fired) | **6** — UCAP, LASACO, NASCON ×4 |
  | flags align / bearish-with-no-flag | 0 |
  | `INSUFFICIENT` (no PIT-available health-flag data at all for that ticker/date) | **31** |

  31 of 37 (84%) have **no PIT-available `financial_reasoning_conclusions` at their decision date at
  all** — the same 15%-coverage story as §4, one layer down: even where an implication exists, the
  *conclusion*-level infrastructure (trend/ratio computations) usually hasn't been run early enough to
  cross-check it.

**Total distinct, real, non-overlapping conflict signals found across both methods: 7** (1 same-filing +
6 flag-based). **Well short of the 25-case minimum.**

**→ Phase 6 result: `INSUFFICIENT_DATA`**, reported plainly. The 50 real multi-fact filings (§4) are the
addressable ceiling if implication-generation and conclusion-generation coverage were both completed —
but completing that coverage is out of scope for this pass (it would mean running the actual reasoning
pipeline more, which Phase 4's own instruction explicitly excludes: "do not simply increase the number
of LLM calls").

---

## 7. Reasoning V3 design review (Phase 7)

**V3 is NOT implemented in this pass**, per the explicit instruction to only build it if the audit shows
the information ceiling is actually lifted. It is not, on two of V3's three new inputs:

| V3 stage | ceiling status vs. V2 |
|---|---|
| Filing context | **Genuinely lifted** — `build_filing_context()` (§5) is real, tested, working infrastructure that did not exist before this pass |
| Materiality | Unchanged — still reuses the LLM's own `magnitude` field (§5 of the prior report), no new source found |
| Valuation | **Partially lifted** — `market_cap` (10/10) and `dividend_yield` (2/10) are now genuinely, broadly usable, a real improvement on the prior "permanently unavailable" framing. Full P/E/P/B remain blocked for 9/10 sleeve tickers by a **named, specific, fixable** gap (missing period metadata), not a structural absence — this is different from EV/EBITDA, which is a genuine structural absence |
| Expectations | **Unchanged, still zero** — no viable existing source found anywhere on the platform (§3) |
| Conflict detection | Real and working (§6), but the evidence base behind it is still n=7, far short of 25 |

**Conclusion: do not build V3 yet.** The honest reading of this audit is that the ceiling moved
meaningfully on valuation (market cap, dividend yield — real, new capability) and the root cause of the
thin contradiction sample is now understood precisely (implication/conclusion generation coverage, not
a hard data wall) — but expectations remain a genuine dead end with no path forward from existing data,
and the contradiction sample is still 18x below its stated minimum. Building V3's full staged pipeline
now would formalize stages (valuation, expectations) that still resolve to `NOT_COMPUTABLE`/
`insufficient_evidence` for the overwhelming majority of the sleeve — the same outcome the prior pass's
shadow test already demonstrated adds no discriminating power (`DIRECTIONAL_WEAK` for 19/21 cases).

---

## 8. Shadow-alpha dataset readiness (Phase 8–9)

Built the real shadow dataset — H-011 sleeve tickers × reasoning implications × realized outcomes.
**REASONING_WEIGHT stayed 0.0 throughout; H-011's score, ranking, and portfolio construction were never
touched (confirmed §1).**

- 29 of 48 implications sit on H-011 sleeve tickers; 10 of 20 sleeve tickers have any reasoning coverage
  at all.
- 18 of those 29 are directionally scoreable (confirmed/contradicted).
- Deduplicated to unique ticker-events (several rows share one filing/window and are not independent
  observations): **8 unique events** — 5 where reasoning agreed with H-011's implicit long stance
  (bullish), 2 where it disagreed (bearish), 1 genuinely `CONFLICTED` (VERITASKAP).

**Phase 9 result, stated as descriptively as the sample allows and no further**: the 2 disagreement
events (CAVERTON +1.22%, CUTIX -6.45%, mean ≈ -2.6%) averaged a less-negative return than the 5
agreement events (LASACO -11.26%, PRESTIGE -6.00%, MCNICHOLS +8.45%, CILEASING -2.86%, REDSTAREX -8.64%,
mean ≈ -4.06%). **This is not evidence of anything** — n=2 vs n=5 is pure noise, not a hit-rate, not a
confidence interval, not a claim. It is reported only because the task asked whether disagreement
"produces no useful distinction," and the honest answer at this sample size is: **there is no sample
size at which this question could currently be answered**, not that the answer is negative.

---

## 9. Out-of-sample firewall (Phase 10)

**`INSUFFICIENT DATA`, explicit, not worked around.** 8 unique ticker-events cannot be split into
design/validation/holdout in any way that produces a meaningful test — any split either has zero
disagreement events in one bucket (nothing to validate) or is dominated by a single observation. No
confidence interval is reported. No statistical claim is made from §8.

---

## 10. Exact remaining blockers

1. **Missing period metadata on 8 of 10 sleeve tickers' `revenue`/`net_profit` facts** — `period_start`/
   `period_end`/`period_type` are `NULL`. This is an **extraction-completeness fix on data already in
   hand**, not new ingestion — the single highest-leverage, most concretely-fixable item found in this
   audit. Fixing it would make P/E potentially computable for up to 8 more tickers (subject to §2's
   separate peer-sparsity issue for some sectors).
2. **VERITASKAP's `equity` facts carry `currency=NULL` instead of `'NGN'`** — a one-ticker data-quality
   bug, same fix category as (1).
3. **Zero comparable peers with computable P/E for LASACO's `insurance` company-type bucket** — a
   coverage-breadth issue, not fixable by touching LASACO's own data.
4. **No `total_debt`/`cash_and_equivalents` fact_type has ever been extracted anywhere** — permanent,
   structural, EV/EBITDA stays `NOT_COMPUTABLE` platform-wide until a new extraction target is added.
5. **No earnings-expectations dataset exists, and none was found reachable from existing data** — the
   one blocker with genuinely no partial-progress path from this audit.
6. **Implication/conclusion-generation coverage is 15% / 16%** of eligible facts respectively — the
   root cause of the thin contradiction sample (§4, §6). Closing this requires running the existing
   reasoning/conclusion pipelines further, which is out of this pass's explicit scope (guardrail 10).

---

## 11. Recommendation

## **B — KEEP EXPERIMENTAL** (unchanged from the prior pass, sharpened by this audit)

Not upgraded to A: §8/§9 show zero measurable incremental value at the only sample size currently
achievable (n=8 unique events) — there is nothing to promote on.

Not downgraded to C: this audit found **real, usable progress** the prior pass didn't have — market cap
and dividend yield are genuinely computable platform-wide for the H-011 sleeve (not "permanently
unavailable" as previously framed), the root cause of the thin contradiction sample is now precisely
identified (coverage, not a hard data wall) and comes with a named, fixable defect (NULL period
metadata) rather than an unfixable one. Killing the module now would discard a correctly-scoped,
partially-de-risked line of work.

Not `D` outright either: `D` applies cleanly to the specific §9/§10 incremental-value question (genuinely
insufficient data, honestly reported), but the broader data-readiness question this task asked has real,
non-null answers throughout §2–§7 — this is not "we don't know," it is "we know precisely what's missing
and some of it is addressable."

**`REASONING_WEIGHT` stays `0.0`** — unchanged, no future authorization implied by this document.

## Exact next authorized action

Two concretely scoped, low-risk data-quality fixes — **not new ingestion, not V3, not more LLM
reasoning calls** — before this question is reopened again:

1. Backfill `period_start`/`period_end`/`period_type` on the 8 sleeve tickers' existing `revenue`/
   `net_profit`/`equity` facts (data already extracted, metadata gap only) and fix VERITASKAP's
   `currency=NULL` rows. Re-run §2's valuation table after — if P/E/P/B become computable for even 3–4
   more sleeve tickers, that changes §7's ceiling assessment materially.
2. **Do not** attempt to acquire an earnings-expectations dataset — no viable existing or reachable
   source was found in this audit; that gap needs a genuinely new data-acquisition decision, out of
   scope for a "reuse existing infrastructure" pass, and should go through this platform's normal
   dataset-acquisition process (`docs/DATA_ACQUISITION_PLAN.md`) if ever pursued, not be improvised here.

No paper-shadow execution, no H-011 change, no V3 build is authorized by this document.
