# Post-Mortem Research Report — H-001 (NGX Sector Price Momentum)

**Status: REJECTED as tested, FROZEN 2026-07-15.** No parameter tuning,
alternative lookbacks, or minor variations may be run under this hypothesis
ID; the freeze is enforced by SQL triggers in the research ledger. Successor
work begins at H-002 / H-003 with new experiment IDs and fresh out-of-sample
windows.

**Purpose of this document:** make it impossible for a researcher six months
from now to unknowingly repeat this cycle. If you are considering an NGX
momentum test, read §8 first — it states precisely what has been ruled out,
what is unanswered, and what was never tested.

All figures trace to the immutable experiment registry
(`data/registry.sqlite`, 111 experiments, 62 on evidence-grade data) and the
companion reports: `reproducibility_H-001.md`,
`data_completeness_2026-07-15.md`, `IC_memo_H-001_*`.

---

## 1. The hypothesis, and why it was considered plausible

**H-001:** Cross-sectional 3–6 month price momentum across NGX sector
indices, expressed as a long-only top-N rotation, outperforms the NGX
All-Share Index after realistic transaction costs and liquidity constraints,
out of sample.

**Plausibility case (as formulated at project start):** Nigerian equities
show large, persistent dispersion between sector indices (one sector up
~97% YTD while another is down ~6% in the same period). This dispersion
appeared linked to identifiable, slow-moving catalysts — bank
recapitalisation cycles, regulatory directives, commodity trends,
dividend/earnings calendars — in a market with thin analyst coverage, where
mispricing should persist longer than in developed markets. If catalysts
reprice sectors slowly, trailing relative strength should predict continued
relative strength.

**The flaw in that reasoning, visible only in hindsight (§4):** dispersion
being real and catalyst-driven does not imply that *trailing price ranks*
capture it. The premise may survive; the proxy did not.

## 2. Methodological safeguards that prevented false discoveries

Each of these, at some point in the cycle, blocked a conclusion that would
otherwise have been wrong:

1. **Bitemporal point-in-time database** — every read takes a simulation
   date and a capture vintage; restatements append rather than overwrite.
   Three lookahead traps (restated value, late-announced membership, future
   event) are demonstrated blocked in `scripts/phase1_smoke_test.py`.
2. **Announcement-date discipline** — membership changes and events are
   usable only from the date they were public, not their effective date.
3. **Survivorship controls** — delisted securities are never deleted;
   undocumented membership history is excluded, never backfilled from
   current lists.
4. **Staging validation before ingestion** — real data entered the research
   DB only after duplicate/jump/gap/coverage checks and anchor
   cross-reference against independently sourced values. 184 rows (including
   an entire month across five indices) were dropped rather than explained
   away.
5. **Confidence scoring with a hard override** — synthetic development data
   carries confidence 0.0 and can never produce a conclusion; every
   experiment records the minimum confidence of the data it touched.
6. **Programmatic holdout enforcement** — development-stage runs are
   *refused* (not clamped) if they touch dates past the holdout start; the
   2025–26 window stayed untouched until the final_oos runs.
7. **Immutable experiment registry** — 111 experiments, UPDATE/DELETE
   blocked by SQL triggers; every run stores its full resolved config, code
   fingerprint, seeds, metrics, and validation flags.
8. **Config-driven research** — no parameter in source code; the real-data
   rerun changed only provider configuration, verified by comparing configs.
9. **Pre-registration of data-forced choices** — the two real-data universe
   variants (V1/V2) were declared from the completeness report *before* any
   real backtest ran, closing the door on universe-shopping.
10. **Parameter stability maps** — performance reported across the full
    lookback × top-N × frequency grid, not at the best cell.
11. **Multiple-testing correction** — Holm and Benjamini–Hochberg applied
    across all 20 cells per variant.
12. **Placebo testing** — 100 seeded shuffled-sector-label strategies per
    variant; this is what killed H-001, by showing the "alpha" was market
    exposure, not selection.
13. **Seed registry** — every stochastic component records algorithm, seed,
    iterations; same config reruns produced bit-identical metrics.
14. **Automatic failure conditions** — rejection triggers evaluated by code,
    with signal-quality separated from scalability so a capacity limit could
    not masquerade as (or excuse) signal failure.
15. **Synthetic full-dress rehearsal** — the entire pipeline ran end-to-end
    on labeled synthetic data first, surfacing engine bugs (an ADTV index
    mismatch that silently zeroed all trades) before real data could be
    misjudged by them.

## 3. Primary reasons for rejection

On real data (investing.com, confidence 0.5), in **both** pre-registered
variants independently:

1. **Placebo failure (decisive).** The real strategy's Sharpe fell *below*
   the mean of 100 random shuffled-label strategies (V1: 0.81 vs 0.84; V2:
   1.55 vs 1.59; p = 0.55 both). Trailing price ranks selected sectors no
   better than chance.
2. **No statistical significance anywhere.** 0 of 20 parameter cells
   survived Holm or BH correction in either variant (V1 had zero significant
   cells even before correction).
3. **Single-regime alpha.** All positive excess came from the 2023–24
   devaluation repricing (100% of positive excess in V1) — one macro event,
   not a repeatable cross-sectional effect.
4. **Out-of-sample failure.** The untouched 2025–26 window: −38.6% (V1) and
   −15.4% (V2) annualized excess.
5. **Cost non-viability of the natural implementation.** Monthly rebalancing
   loses −8.1%/yr to the benchmark at retail-max brokerage before any
   question of signal quality arises.

## 4. Assumptions that turned out to be incorrect

| Assumption | Reality |
|---|---|
| Persistent sector dispersion implies exploitable *price* momentum | Dispersion is real; trailing 3–6M price ranks did not predict it (placebo p=0.55). The proxy failed, whether or not the premise holds. |
| Monthly rebalancing would be a viable base case | ~2.6× one-way annual turnover at NGX retail costs is fatal on its own; quarterly is the floor. |
| Free data would cover the 9-index universe with usable history | 5 of 9 indices have history from 2012; Consumer Goods 2018-12, Industrial 2020-02, Pension 2021-06, Premium absent. The intended universe never existed in the data. |
| A "3-regime walk-forward" gives meaningfully independent samples | The 2023-24 devaluation repriced everything at once; the regimes are one long macro story plus tails. The Phase 1 statistical-power warning proved correct. |
| Synthetic rehearsal results would resemble real behavior | The synthetic placebo passed (p=0.04); the real one failed (p=0.55). Synthetic data validates machinery only — this was by design, and the design was vindicated. |

Assumptions **still unverified** (not wrong, just unconfirmed): the retail
fee stack (all rates remain `confidence='assumed'`), the qualification-date
markdown convention, slippage/impact coefficients.

## 5. What the project taught us about the Nigerian market

*(Real-data findings only; synthetic-derived numbers are excluded.)*

- **Cost structure dominates strategy design.** The assumed retail
  round-trip is ~3.8% of trade value, ~60% of it brokerage (the one
  negotiable line). Any NGX strategy with >1.5× annual turnover needs
  institutional pricing before it needs a signal.
- **Long-only "alpha" in NGX is mostly beta.** Random sector portfolios
  earned Sharpe ~0.8–1.6 across our windows because the market itself rallied
  hugely (ASI +45.9% in 2023, +37% in 2024, strong 2025). Placebo controls
  are not optional in this market.
- **Returns are event-concentrated.** June 2023 (FX liberalization) produced
  synchronized >15% single-day sector-index moves — the staging validator
  flagged all five as anomalies. NGX repricing happens in bursts around
  policy events, which is *consistent with* the catalyst premise (H-003) and
  *inconsistent with* smooth momentum diffusion.
- **The free-data landscape is workable but bounded.** investing.com serves
  clean daily sector-index closes from 2012 (ASI verified against three
  independent year-end anchors within 0.5%); NGX's own site is current-day
  only; no free total-return series, constituent files, or corporate-action
  database exists.

## 6. Reusable infrastructure

Everything below is hypothesis-agnostic and carries forward unchanged:

- Bitemporal PIT database + schema (`schema/`, `ngxrot/db.py`)
- Data Abstraction Layer + providers (`providers/`: investing.com live;
  CSV; synthetic; NGX-web/archive stubs), staging validation (`staging.py`)
- Governance: immutable registry, hypothesis ledger with freeze
  (`registry.py`, `ledger.py`), config runner with holdout guard (`runner.py`)
- Validation suite: stability maps, Holm/BH, placebo, walk-forward,
  confidence ratings, IC memo and reproducibility report generators
  (`phase4.py`, `stats.py`, `confidence_rating.py`, `ic_report.py`)
- Diagnostics engine (7 checks, extensible) (`diagnostics.py`)
- Both engines: `backtest_lite` (index-level) and `engine_full`
  (constituent-level with ADTV caps, line-item costs, capacity
  distributions) — the latter is built and rehearsed but **awaits real
  constituent data**.
- The `events` table + catalyst filter machinery — built, PIT-correct, and
  never yet fed real events: this is H-003's starting point.

## 7. Datasets that remain unavailable

| Dataset | Blocks | Best known route |
|---|---|---|
| Constituent daily prices/volume/value | capacity, impact, full engine on real data | NGX daily price lists (X-DataPortal paid, or forward daily collection) |
| Float-adjusted weights + membership history | survivorship-proof constituent work | NGX review circulars / archives |
| Corporate actions & dividends | H-002 (total return) | NGX X-Issuer, registrars, company IR |
| Real regulatory/event calendar with announced dates | **H-003** | CBN/SEC/NGX primary sources (schema ready) |
| NGX Premium index; pre-2019 Consumer Goods; pre-2020 Industrial | full 9-index universe | none free found |
| Broker contract note | confirming the fee stack | user's broker |
| NGN T-bill series | honest Sharpe (rf currently 0%) | CBN data |

## 8. What is ruled out, what is open, what was never tested

**Evidence AGAINST (do not re-run under any guise):**
long-only top-N rotation on NGX *price* sector indices ranked by trailing
3–6M (and, via the stability map, 3, 6, 12, 3+6, 6+12 month) returns, top-2
or top-3, monthly or quarterly, at retail-to-discount brokerage, over
2012–2026 investible history. Rejected by placebo, correction, regime
concentration, and OOS failure in two pre-registered variants.

**Unanswered questions (open, but require new data before new hypotheses):**
- Does *total-return* momentum rank differently? (Banking's 8–12% dividend
  yield is invisible to price indices — H-002, blocked on dividend data.)
- What is the real capacity of any NGX sector strategy? (Blocked on
  constituent volume data; synthetic results are suggestive of severe
  insurance-sector bottlenecks but are not evidence.)
- Would the catalyst filter have changed anything? (Never evaluable: no real
  event data was ever ingested; the on/off variants were identical by
  construction.)
- All Sharpes are vs rf=0%; NGN T-bills at times paid >20%. Excess-vs-cash
  results would be materially worse — this strengthens, not weakens, the
  rejection, but the exact numbers are unknown.

**Never tested (genuinely new ground, requires new hypothesis IDs):**
- H-003: direct catalyst/event-driven rotation (**priority** — tests the
  original premise's mechanism instead of a price proxy)
- Constituent-level momentum or any stock-selection strategy
- Weekly/faster signals (note: almost certainly cost-prohibited — see §5)
- Fundamental/valuation-based sector rotation; FX-regime conditioning;
  long-short constructions (shorting NGX is practically constrained)

## 9. Rules for the next cycle

1. H-001 is frozen at the SQL level: status changes and new experiments
   under it are blocked. There is no unfreeze.
2. Successor hypotheses are registered: **H-003 (priority)** and H-002 —
   each requires its own success/failure criteria, failure-condition
   thresholds, and untouched OOS window *declared before testing begins*.
3. Both are currently **blocked on data acquisition**, not code. Build the
   real event calendar (H-003) or the dividend database (H-002) first;
   the research engine runs on either the day the data passes staging
   validation.
