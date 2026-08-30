# Alpha Opportunity Audit — 2026-08-12

Infrastructure phase frozen (`a877d62`, `69bb4a5`). No code changed by this
document. No Alpha Engine file touched or read for modification purposes.
Grounded directly against `data/ngx.sqlite` (queried live, 2026-08-12) and
every prior research document under `docs/` — this audit does not
re-derive what has already been rigorously tested; it synthesizes it and
identifies what is genuinely still open.

---

## 1. Executive conclusion

**There is no new hypothesis worth registering today.** This is not a
failure of this audit — it is the honest output of one, and it agrees with
~40 prior research documents (`H-001` through `H-019` on the formal ledger,
plus Stages 16–28 of unregistered discovery work) that already tested
nearly every economically plausible angle this dataset supports: price
momentum at three horizons, low-volatility, liquidity, dividend
payer-status, oil lead-lag, MPC-window timing, catalyst-driven sector
rotation, size, five size-interaction decompositions, five information-type
discovery tracks (earnings/PEAD, regulatory events, corporate actions,
information-diffusion speed, event×microstructure interaction), a
delisting-watchlist distress channel, a regulatory state-transition
channel, an illiquidity/staleness mechanism, and an insider-dealing
disclosure-lag mechanism that survived three consecutive adversarial
rounds before a completeness fix reversed it. One factor is confirmed
(Size, H-011) and is capacity-dead at real fund scale (~₦694k median
tradeable leg). Everything else is rejected, or stuck at CONDITIONAL GO
pending data that does not yet exist, or waiting on a calendar date.

Two genuinely live paths exist, and this audit's job is to name them
precisely rather than manufacture a third:

1. **Wait, don't build**: the 2026-08-17 NGX volume-threshold reform
   (Stage 28) is the single structurally cleanest candidate this entire
   program has found — a mechanical, rule-level distortion, not a
   behavioral story — and it is *already* frozen as a pre-registered
   difference-in-differences protocol (Stage 28B), operationally
   readiness-checked (Stage 28D/28E). It cannot be tested until
   `equity_prices` extends past the reform date plus a ~40-session
   post-window — realistically mid-to-late October 2026. Nothing to code
   now.
2. **Invest, don't guess**: twelve statement-based factor families (Value,
   Quality, Growth, Profitability, Piotroski Financial-Strength, Asset
   Growth, Earnings Quality, Cash-Flow Quality, Accruals, Asset Turnover,
   and the composite/interaction factors built from them) are all
   `Data-Blocked` on the identical root cause — real financial-statement
   extraction currently covers only **10 tickers** in production (verified
   below, correcting a stale 26-ticker/351-conclusion figure from an
   in-progress reliability-verification test that was never applied to
   the live database). Expanding this coverage is a labor/extraction
   investment, not a new infrastructure subsystem, and it unlocks all
   twelve at once rather than one at a time — exactly the kind of
   "coverage-closing work outranks new consumer features" priority the
   Fund Alpha Charter already states.

Everything else documented below exists to substantiate that conclusion,
not to talk the reader into a different one.

---

## 2. What information the OS currently possesses

Verified by direct query against the live database, 2026-08-12:

| Dimension | Coverage | Depth |
|---|---|---|
| Equity OHLCV | 323 tickers, 678,800 rows | 2014-06-30 → 2026-08-07 |
| Index levels | 5+ sector/broad indices, 47,031 rows | 2012-01-30 → 2026-08-07 |
| Index membership (structured) | 12 rows across 5 indices | Thin — not a usable PIT membership source by itself |
| `securities.sector_ngx` | 137 of 323 (42.4%) populated | 186 NULL |
| `securities.delisting_date` | **0 of 323 populated** | See §3 — a real gap, not a clean zero |
| Corporate actions | 185 dividend rows / 63 tickers, 1 rights issue | 2014-07-11 → 2026-07-16; **no bonus/split/merger/delisting rows exist at all** despite schema supporting 14 types |
| Documents (filings/news) | 11,589 total; 210 tickers have ≥1 document | 2014 → 2026 |
| Extracted facts | 495 rows | Dividend-heavy (161); financial-statement line items only for a 10–26-ticker subset depending on fact_type |
| **Financial reasoning conclusions (production)** | **267 rows, 10 tickers** | period_end 2020-09-30 → 2025-12-31 |
| Events | 184 rows | 78% macro (`mpc_decision`); company-specific types (management_change, capital_raise, ownership_change) each in single digits |
| Entity relationships | 22 rows | Mostly `affects_order_N` (peer-propagation labels, not semantic) and `renamed_from`; not a competitor/supplier graph |
| News (extracted) | 27 Nairametrics/MarketForces articles, native-extracted, 25 facts derived | Separate 27-article `stage10c` pilot batch entirely unextracted |
| Insider-dealing disclosures | 163 filings piloted (Stage 22–27) | Extraction feasible, adversarially tested, ultimately NO-GO (§5) |

**Correction to the prior handoff's figures**: the "~26 tickers / 351
conclusions" figure came from a full-universe recompute run during the
just-completed reliability-verification pass — it ran against a **scratch
copy only**, to prove the write path is idempotent (Milestone doc,
§4). It was never applied to `data/ngx.sqlite`. Production currently holds
267 conclusions for 10 tickers (`AFRIPRUD, BUAFOODS, CAP, DANGCEM, MTNN,
NASCON, NESTLE, OANDO, UBN, UCAP`), matching `FACTOR_CANDIDATE_REGISTRY.md`'s
2026-08-02/03 figure exactly — coverage has not grown since that audit.

**Research Query Layer, actual capability** (not aspirational):
`research_query.py` exposes `prices`, `cross_section`, `universe_history`,
`compare`, `metadata`, `entity_lookup`, `facts`, `events`,
`entity_relationships`, `document_context` as first-class query types.
**`financial_reasoning_conclusions` and `corporate_actions` are not
exposed through it** — both require going around the query layer to
`pit_financial_memory.as_of()` and `db.corporate_actions_asof()` directly.
Not a blocker (the underlying PIT-safe functions work, verified in the
reliability milestone), but worth stating precisely: "the Research Query
Layer already supports market and document evidence" is true, and it does
not yet mean every table is reachable through it.

---

## 3. What information is actually PIT-safe

Reusing, not re-deriving, the capture-vintage work verified in
`69bb4a5`:

- **Market data** (`equity_prices_asof`, `index_levels_asof`,
  `corporate_actions_asof`, `membership_asof`, `events_asof`): PIT-safe on
  both axes (`sim_date`/business date and `vintage`/capture date) — this
  was already correct before the reliability work and remains the
  strongest PIT foundation in the OS.
- **Documents, extracted facts, entity relationships**: PIT-safe **only
  when the caller explicitly passes `vintage`** to `retrieve_documents`/
  `find_facts`/`find_entity_relationships`/`pit_financial_memory.as_of` —
  none of these thread `vintage` by default, and `research_query.py`,
  `build_reasoning_context`, and every hypothesis-testing script written
  before 2026-08-12 predate this parameter entirely. **Any backtest built
  on document/fact/entity data before today must be re-audited for
  capture-vintage leakage** if it used a historical `as_of` date — this
  was a real, live-data-confirmed bug (98.8% of documents have a capture
  lag over 30 days, avg ~4.6 years) closed only in the just-frozen
  milestone. H-001–H-019 never touched document/fact data for their core
  signals (price/index-based), so they are unaffected; H-019 (news
  events) and the Stage 18/19/22–27 discovery work **did** use
  document-derived dates and should be treated as unverified against this
  specific axis unless independently re-checked — flagged here, not
  re-audited (out of this document's scope).
- **`securities.delisting_date` is 100% NULL** and no `corporate_actions`
  row of type delisting/merger/bonus/split exists. This is a genuine,
  previously-unflagged **survivorship-bias risk**: any cross-sectional
  backtest that queries `securities` for "the universe" without going
  through a real point-in-time membership source (`index_membership`,
  itself only 12 rows) risks silently using today's surviving-name list
  as if it were historically available. Every hypothesis on the formal
  ledger constructs its universe from the IRU (`universe.py`) rather than
  raw `securities`, which is the correct pattern — but this gap means any
  *new* candidate must be built the same disciplined way, not assumed
  safe because `securities` exists.
- **Dividend `markdown_date = NULL`** (155 real rows): confirmed inert to
  `engine_full.py`'s total-return overlay, both by direct code trace and
  by the regression test `test_corporate_actions_dividend_load.py`. Any
  dividend-based *research* signal (as opposed to Alpha Engine input)
  should use `declared_date` (populated on all 186 rows), never
  `markdown_date` (populated on only 31) — a signal built on the sparser
  field would silently narrow to that one-sixth of the data.
- **Financial reasoning conclusions**: PIT-safe on `filing_date`
  (`pit_financial_memory.py`, always was) and now also on capture vintage
  (this milestone) — but this safety is irrelevant at 10-ticker breadth;
  see §9.

---

## 4–7. Candidate sources of edge, hypotheses, data requirements, economic rationale

Presented together because, at this stage of the platform's research
history, the honest unit of analysis is "what has already been concluded
about this candidate," not a fresh derivation. Ranked HIGH/MEDIUM/LOW/
BLOCKED per §10's criteria.

### Already closed — do not retest without new evidence

| Candidate | Prior verdict | Why closed |
|---|---|---|
| Cross-sectional price momentum (sector, 3-6M) | H-001 REJECTED | Placebo failure in both variants |
| Total-return sector momentum | H-002 abandoned, untested | Needs formal retirement, not a candidate |
| Catalyst/event-driven sector rotation | H-003 REJECTED | p=0.198, close but below threshold |
| Oil-Brent → Oil&Gas sector lead-lag | H-004 REJECTED | p=0.079, close but below threshold |
| MPC announcement-window effects | H-005 REJECTED | Every rejection trigger fired |
| PEAD via filing-window reaction | H-006 REJECTED | Reaction exists in gross terms; ranking carries no information (only event *membership* might — see H-A below) |
| Per-stock 12-1 momentum (quarterly) | H-007 REJECTED | Fails retail costs |
| Low-volatility tilt | H-008 REJECTED | Robustly underperformed, wrong-direction significant |
| Turnover-budgeted 12-1 momentum (annual) | H-009 REJECTED | Sign flipped as predicted, but only ~9 independent decisions — sample-size-bound, not signal-bound |
| Pooled overlapping-cohort momentum | H-010 REJECTED | Pooling degraded the placebo result |
| Regime-conditional low-vol gate | H-012 REJECTED | Gate doesn't rescue H-008 |
| Size × Liquidity/Momentum/Volatility interactions | H-013/014/015 REJECTED | Size does not survive independently of Liquidity; partially explained by Momentum; independent of Volatility |
| Liquidity (ADTV) factor, either direction | H-016 REJECTED IN FULL | Cost drag eliminates gross premium |
| Dividend payer-status (binary) | H-017 REJECTED | Gross excess ≈0 |
| News-derived GMC/CIR discrete events | H-019 TESTING, currently negative | 2 realized trades, both losses, worse than benchmark |
| Earnings surprise / news-PEAD | Stage 16 H-A, Stage 18 §12: NO-GO | Same economic claim as H-006 on a different channel; 0/20 names have ≥2 comparable-period observations; unresolved audited-vs-reported figure-integrity risk |
| Corporate-action economic-impact (capital_raise class) | Stage 16 H-C: NO-GO | Redundant with primary filings — same objection that excluded it from H-019 |
| Information-diffusion speed (cross-outlet lag) | Stage 16 H-D: NO-GO | Zero matched cross-outlet pairs exist; not a coverage gap, a research-design gap |
| Regulatory state-transition (suspension-lift) | Stage 19 CONDITIONAL → Stage 19B **KILL** | Frozen diagnostic ran, persistence did not survive |
| NGX-specific PEAD (re-scoped) | Stage 18 §12: NO-GO, reconfirmed | Same coverage blocker as H-A |
| Illiquidity/staleness → forward returns | Stage 20/21 CONDITIONAL → Stage 21C **NO-GO** | Drift-only, market-relative test fails at all four horizons |
| Insider-dealing disclosure lag (PURCHASE) | Stage 22–26 CONDITIONAL GO (×4 rounds) → Stage 27 **NO-GO** | Survived concentration, clustering, and interim completeness checks; final corpus-completeness fix revealed the effect was carried by one micro-cap outlier and fails exact small-sample inference |
| Value / Quality / Growth / Profitability / Piotroski F-Score / Asset Growth / Earnings Quality / Cash-Flow Quality / Accruals / Asset Turnover (all statement-based) | `FACTOR_CANDIDATE_REGISTRY.md`: **Data-Blocked** | 10-ticket ceiling on every non-dividend fact type — see §9 |
| Any composite or interaction factor requiring ≥2 validated components | `FACTOR_CANDIDATE_REGISTRY.md` D1/D2: blocked | Only H-011 is confirmed; a composite today combines one proven signal with unproven ones |

### Still open, at various stages of readiness

| Candidate | Status | Rank | Why |
|---|---|---|---|
| **2026-08-17 volume-threshold reform (DiD)** | Frozen protocol, waiting on data | **HIGH** — but not actionable until October 2026 | Mechanical, rule-level distortion (exchange's own price-band system), not a behavioral story — structurally the cleanest mechanism the entire program has found (Stage 28 §5). Treatment/control groups, metric, and falsification rule are pre-specified (Stage 28B), so there is zero hindsight risk once data arrives. Operational readiness (duplicate-price audit, data-integrity fixes) already done (28D/28E). |
| **Delisting-watchlist distress mispricing** | CONDITIONAL GO, materially downgraded | MEDIUM | First-party, structured, no FSI needed, PIT-clean by construction — but the flagship case (DEAPCAP) does not survive adversarial scrutiny (its price action is dominated by an unrelated earlier catalyst), leaving only 6-7 genuinely independent underlying situations. Resumption events (2 of them) are "genuinely novel, clean, and interesting" but too few to test alone. Needs a new, bounded extraction pass against NGX's own watchlist (external data acquisition, not built) before it is testable at all. |
| **Regulatory event × liquidity/attention** (general, beyond suspension-lift specifically) | CONDITIONAL, structurally strongest of Stage 16's five tracks | MEDIUM | PIT-clean, explicitly independent of H-011/H-019, well-defined next step — but blocked entirely on volume (2 independent events in the current corpus). |
| **Financial-statement factor family (Value/Quality/Profitability/Piotroski etc.)** | Data-Blocked | **HIGH priority to unblock, not currently testable** | Twelve literature-grounded, economically well-motivated candidates share one root cause (10-ticker extraction ceiling) — the single highest-leverage coverage investment on the platform, because closing it unlocks all twelve simultaneously rather than one at a time. |
| Free-float-rule-tightening exposure | CONDITIONAL, rule not yet adopted | LOW | Requires new data (per-company shareholding structure) not currently ingested anywhere; genuinely ex-ante-knowable in principle but the rule itself may never be adopted. |
| Recapitalisation dilution-magnitude (post-hoc, within-sector relative) | NO-GO on the macro framing; dilution-magnitude reframing untested | LOW | The "recap happened, buy the sector" version is dead (window closed, fully priced); the relative dilution-magnitude reframing is a real, untested idea but needs new NAICOM/CBN compliance-data acquisition. |
| PenCom-flow / H-011 interaction | Flagged as a risk, not an opportunity | LOW / risk-only | Plausibly an *anti-correlated* structural headwind for H-011's small-cap universe (pension mandates likely concentrate in large/liquid names) — worth confirming as a risk check, not pursuing as a signal. |
| Index-inclusion effect (imported from MSCI/US literature) | Explicitly rejected as an import | BLOCKED | NGX-specific passive-AUM tracking has never been verified; importing foreign-market evidence without that verification is exactly the mistake the program's own rules prohibit. |
| Insider-dealing SALE-side | Diagnostically informative, untradeable | BLOCKED | Stage 24: informative as a mechanism signal but cannot be traded on directly. |

---

## 8. Leakage / bias risks (platform-wide, not candidate-specific)

1. **Survivorship bias via `securities`** — §3. Real, previously unflagged by this exact name, though every *tested* hypothesis avoided it correctly via `universe.py`'s IRU construction.
2. **Capture-vintage leakage on document/fact/entity data for any pre-2026-08-12 research** — §3. The infrastructure fix is real and verified; whether every *prior* piece of discovery work (Stage 18, 19, 22–27) that touched document dates would survive re-auditing under it is unconfirmed. Not re-run here.
3. **PEAD-family figure-integrity risk** — unaudited/interim news-reported financial figures carry an unresolved audited-vs-reported risk (Stage 12 §12F/12H) — this specifically killed H-A and is why earnings content was excluded from H-019's scope entirely, not an oversight.
4. **Corporate-action redundancy** — capital_raise-type events sourced from news are largely a slower, less complete version of what a completed primary-filing extraction would show directly (Stage 16 §11H/13F) — a "novel to the database" fact is not the same as "novel to the market."
5. **Small-sample / extreme-observation fragility** — the single most common reason a CONDITIONAL GO in this program's own history flipped to NO-GO (H-009 momentum, H-013–015 Size interactions, Stage 21C illiquidity, Stage 27 insider-dealing) was a result driven by too few independent decisions or one outlier ticker (MCNICHOLS, UCAP). Any future candidate inherits this risk by default at NGX's scale and must be pre-registered with an explicit outlier-removal / small-G exact-inference check, not added after seeing results.
6. **Capacity/execution reality** — H-011 is confirmed but capacity-dead (~₦694k median tradeable leg). Every candidate touching the same small/illiquid names (H-011's universe, most of the news/regulatory/delisting/insider tracks) inherits this constraint by default and must be capacity-assessed *before* being taken seriously, per Stage 17 §9's own explicit lesson.

---

## 9. Backtest feasibility

**Nothing on the "still open" list is backtest-ready today** except the
frozen, data-waiting volume-threshold DiD (which is a diagnostic, not a
backtest, and explicitly not to be escalated to one until its own
falsification rule is evaluated).

The financial-statement factor family is the one candidate group where
feasibility is a **pure coverage number**, not a research-design problem:
`FACTOR_CANDIDATE_REGISTRY.md`'s own standard — "10 tickers is roughly a
tenth of the 100-name IRU bar every tested hypothesis has used... a
fundamentally underpowered, non-comparable design" — still holds exactly
today, unchanged since 2026-08-02/03. Expanding this coverage (extraction
labor over already-archived filings, not new data acquisition, not new
infrastructure) is the single action that would convert the largest
number of BLOCKED candidates into testable ones.

---

## 10. Ranking of opportunities

**HIGH**
- 2026-08-17 volume-threshold reform DiD — frozen, waiting on data, zero design risk remaining. Not actionable until ~October 2026.
- FSI financial-statement coverage expansion (infrastructure-adjacent, not a hypothesis itself) — unlocks 12 BLOCKED candidates simultaneously. Highest-leverage single investment on the platform right now.

**MEDIUM**
- Delisting-watchlist distress mispricing — real mechanism, PIT-clean, but thin (6-7 independent situations) and its flagship case failed adversarial review. Needs bounded external data acquisition before any test.
- Regulatory event × liquidity/attention (general) — structurally the strongest of the five Stage-16 tracks, blocked purely on volume (2 events).

**LOW**
- Free-float exposure watchlist — real, ex-ante, but needs unbuilt shareholding-structure data.
- Recap dilution-magnitude (relative reframing) — untested idea, needs unbuilt compliance data.
- PenCom-flow interaction — risk-check only, not an opportunity.

**BLOCKED**
- Every statement-based factor individually (Value, Quality, Growth, Profitability, Piotroski, Asset Growth, Earnings Quality, Cash-Flow Quality, Accruals, Asset Turnover) — same root cause as the HIGH-ranked coverage investment above.
- Any composite/interaction factor (needs ≥2 validated components; only 1 exists, and it's capacity-dead).
- NGX-PEAD in any form (earnings-surprise or news-channel) — coverage- and PIT-blocked simultaneously.
- Index-inclusion effect — unverified foreign-literature import.
- Insider-dealing SALE-side — untradeable by construction.
- Information-diffusion speed — no matched cross-outlet data exists, and none is close to existing.

---

## 11. Recommended first hypothesis

**None, registered today.** Registering a hypothesis now, from this
dataset, without either the reform-date data or expanded fundamental
coverage, would mean re-testing something already rejected, testing a
statement-based factor at a sample size the platform's own standing
discipline already calls "a methodology error, not a legitimate research
step," or manufacturing a combination hypothesis whose price/liquidity/
momentum/low-vol legs are individually dead — exactly the anti-overfitting
violation this audit was asked to guard against.

The two legitimate next actions are not hypotheses, they are the
prerequisites to having one:

1. **Monitor, don't act**: once `equity_prices` extends past 2026-08-17
   plus ~40 sessions, run Stage 28B's frozen DiD protocol exactly as
   written. If it clears its own pre-stated falsification rule, *that*
   triggers hypothesis registration and the full validation gauntlet
   (§13) — not before.
2. **If coverage-expansion capacity is authorized separately**: extend
   FSI financial-statement extraction beyond the current 10 tickers.
   This is the single highest-leverage lever on the platform because it
   is shared infrastructure for twelve otherwise-independent candidates,
   not a bet on any one of them. The right target breadth is the same
   ~100-name IRU bar every tested hypothesis on this platform already
   uses, not an arbitrary larger number.

---

## 12. What must NOT be built yet

- No new backtest, hypothesis registration, or `configs/hNNN_*.toml` file.
- No statement-based factor test at anything less than IRU-comparable
  breadth (~100 names) — testing at 10 is a pre-declared methodology
  error on this platform, not a judgment call to relitigate.
- No combination/composite hypothesis — only one component (Size) is
  validated, and it is capacity-dead; a composite today is speculation
  wearing a composite's clothing (`FACTOR_CANDIDATE_REGISTRY.md` D1).
- No re-registration of any REJECTED/NO-GO hypothesis above without
  genuinely new evidence, per the platform's own explicit rule: an
  economically identical claim on a different data channel is the same
  hypothesis, not a new one (this killed both H-A/Stage-16 and the
  Stage-18 PEAD reframing).
- No `alpha_engine.py`, `engine_full.py`, `runner.py`, or hypothesis
  registry changes.
- No new infrastructure subsystem, external data acquisition pipeline, or
  scraper — even for the MEDIUM-ranked candidates (delisting watchlist,
  free-float exposure) — without a separate, explicit authorization
  naming that specific acquisition, consistent with every prior stage
  gate on this platform.
- No premature escalation of the volume-threshold DiD before its own
  data-availability condition and pre-registered falsification rule are
  both met.

---

## 13. Proposed validation protocol

Not a new proposal — this audit's job is to confirm the platform's
existing gauntlet remains the correct one, since every candidate above
that reached a real verdict did so by clearing or failing it:

1. **Pre-registration before data inspection** (`docs/PREREG_H-NNN.md`) —
   universe, formation rule, holding period, rebalance cadence, benchmark,
   cost assumption, and rejection triggers fixed in writing before any
   return is computed. Every hypothesis on the ledger followed this; the
   two cases where a result changed after the fact (H-009→sample-size
   diagnosis, Stage 27's completeness reversal) were pre-declared
   diagnostic follow-ups, not silent re-runs.
2. **Placebo test**: real Sharpe/return vs. a distribution of
   shuffled-label or randomly-timed variants (100 seeds, the standing
   convention) — the single most decisive gate in this program's history;
   it killed H-001, H-005, and flagged H-004/H-003 as directionally
   suggestive but insufficient.
3. **Parametric + HAC-robust significance**, not iid p-values alone —
   several candidates (H-013, H-021C-adjacent work) passed one and failed
   the other; both are required.
4. **Small-sample / exact inference and extreme-observation removal**
   whenever independent-decision count is low (<~20) — this is not
   optional given NGX's scale; it is what caught H-009's true binding
   constraint and Stage 27's insider-dealing outlier.
5. **Stability grid / multiple-regime check** — H-008's low-vol result
   held across all three regimes including OOS, which is *why* its
   rejection is trusted; a result that only holds in one regime is
   treated as fragile by default.
6. **Independence check against every already-validated or in-testing
   factor** (H-011, H-019) — mandatory before registration, not an
   afterthought; this is what caught H-013–015 (Size) and flagged every
   Stage-16/17/20 candidate's overlap risk explicitly.
7. **Capacity and realistic transaction-cost modeling** — using the
   platform's own `cost_schedule`/ADTV-cap machinery, not a generic
   assumption; this is what made H-011's confirmation honest (capacity-
   constrained, stated plainly) rather than overstated.
8. **Out-of-sample / walk-forward** as the final gate, not the first —
   every REJECTED verdict above was reached using development-window
   evidence or full-sample diagnostics *before* any OOS claim was made;
   OOS is reserved for a candidate that has already survived 1–7.

This protocol is expensive by design. Given that ~19 formal hypotheses and
~25 additional discovery tracks have been run through it and only one
survived — capacity-dead — the platform's revealed base rate for "an
idea that sounds plausible actually validates" is roughly 1-in-40. That is
the correct prior for whatever comes out of §9's coverage-expansion
investment or the October 2026 volume-threshold diagnostic, and it is the
reason this audit does not manufacture a 40th candidate today merely to
have something to report.
