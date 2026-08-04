# Wave 6 Strategic Research Plan

*2026-08-04. Decision document only — no implementation, no schema
changes, no database writes, no extraction, no hypothesis registration.
Written at the close of the technical-factor research wave (H-001
through H-017, 17 hypotheses, 1 confirmed). Every claim below is tagged
**[Verified — empirical]** (measured directly this session or a prior
audited session), **[Verified — literature]** (external academic/
institutional citation), **[Verified — registry]** (from
`data/registry.sqlite` or platform documentation), or **[Assumption/
Estimate]** (explicitly not backed by direct evidence). Where a
candidate dataset has no dedicated prior audit, that absence is stated
directly rather than papered over with an invented ranking.*

---

## Answers, upfront (the seven required questions)

1. **Has the current dataset reached its research ceiling? Partially,
   and asymmetrically.** The technical/price-volume-derived side (the
   information the platform has had since day one) is genuinely close
   to exhausted — nearly every well-motivated, zero-new-data idea has
   been tried across 17 hypotheses. The fundamentals side has **not**
   reached a ceiling — it was never able to start. 11 of 16 named
   candidate factor families have never been tested even once, not
   because they failed, but because the data to test them was never
   available at adequate breadth.
2. **Should technical-factor discovery pause? Yes, largely — with two
   narrow, already-identified exceptions** (a PEAD membership-only
   retest, and a data-availability recheck on the dormant H-002). Beyond
   those two, no further zero-new-data technical hypothesis is
   evidenced as worth pursuing next.
3. **What should the platform acquire next?** Per the evidence in W6-2
   and W6-5, the highest-value, already-scoped, zero-new-data-cost
   action is a **targeted, depth-first FSI extraction pilot** (already
   recommended by the FSI Owner Decision Package, still not executed)
   — not a new external dataset acquisition. The highest-value NEW
   acquisition, if the FSI pilot's own ceiling proves too low, is
   **NGX X-Compliance free-float data**.
4. **What research capability will each unlock?** FSI depth: the
   entire fundamentals half of standard factor taxonomy (Value,
   Quality, Growth, Profitability, Investment, Financial Strength — 6
   of the 11 blocked families at once). Free-float: resolves H-011's
   own disclosed construct-validity gap and matches institutional
   frontier-index practice, but unlocks fewer new questions than FSI
   depth.
5. **What should Wave 6 become?** Not another hypothesis wave — an
   **information-acquisition and methodology-closure program**,
   structured as milestones (W6-4) rather than sequential phases, with
   explicit stopping conditions rather than an assumed march through a
   fixed backlog.
6. **What should explicitly not be pursued yet?** A third or fourth
   round of technical-factor variants (momentum/volatility variants are
   exhausted); the exotic frontier-native data sources (NEITI, GDELT,
   nightlights) before the FSI/free-float decisions land; any large,
   unbounded FSI labor commitment before the already-recommended small
   pilot reports back; portfolio construction (architecturally gated,
   correctly, behind ≥2 validated independent factors).
7. **Single highest-return investment for increasing the probability of
   a second independent alpha source: the FSI depth-first pilot**
   (timed trial → ticker-attribution fix → tabular-format
   hand-verification → schema addition), already fully specified in
   `docs/FSI_OWNER_DECISION_PACKAGE_2026-08-03.md` and not yet executed.
   It is cheaper, faster, and touches more blocked factor families than
   any new external acquisition — the platform's own highest-leverage
   unexecuted decision, not a new one this document invents.

---

## Phase W6-1 — Information Ceiling Audit

### 1.1 The complete failure/success attribution matrix

| H-ID | Verdict | Primary attributable cause | Secondary cause | Evidence |
|---|---|---|---|---|
| H-001 | Rejected | **Insufficient cross-sectional breadth** (sector-level, ~13 sectors — a structural ceiling, not a data gap) | Transaction costs | Placebo failure both variants; single-regime concentration 100% |
| H-002 | Untested (dormant) | N/A — not a failure | Originally data-blocked; possibly now unblocked (unverified) | Never run |
| H-003 | Rejected | **Insufficient information** — the OOS window never actually tested the hypothesis (ASI fallback held throughout) | Statistical power | Placebo p=0.198, directionally better than random but inconclusive |
| H-004 | Rejected | **Statistical power** (near-miss, placebo p=0.079) | Transaction costs (final-OOS reversal) | 0/8 cells BH-significant |
| H-005 | Rejected | **Genuine market inefficiency not existing** — gross excess ≈0, cost drag ~40%/yr on nothing | — | Placebo p=1.00, worse than every one of 100 shuffles |
| H-006 | Rejected (nuanced) | **Methodological limitation** — the underlying gross PEAD reaction IS real; the RANKED-selection construction carries no information | — | Explicit successor design (membership-only) flagged, never registered |
| H-007 | Rejected | **Transaction costs** (real, modest gross effect +2.2%/yr eliminated by turnover) | — | Adequate breadth and power; cost-driven failure specifically |
| H-008 | Rejected | **Genuine market inefficiency not existing** — wrong-signed, Holm-significant across all 3 regimes | — | NGX's regime history (violent transitions) structurally rewards risk-taking, not the calm-compounding backdrop the mechanism needs |
| H-009 | Rejected | **Statistical power** (explicitly self-diagnosed: "only ~9 independent decisions... a power problem, not a sign problem") | — | Sign flipped as predicted by the cost-fix; too few annual decisions to clear placebo |
| H-010 | Rejected | **Statistical power** (same root cause as H-009) | Methodological limitation (pooling degraded rather than fixed the near-miss; likely a calendar-alignment artifact) | Pooling didn't increase evidence of skill |
| H-011 | **Confirmed** | **Genuine market inefficiency** (capacity/illiquidity-friction compensation) | Capacity constraint on deployment (small-AUM, illiquid-name-driven) | Per its own capacity report; see also H-013/015 below |
| H-012 | Rejected | **Genuine market inefficiency not existing** (confirms H-008; regime-gating does not rescue it — MORE decisively wrong-signed than the unconditional test) | — | Placebo p=0.970 |
| H-013 | Rejected (diagnostic, not a factor failure) | N/A — successful forensic finding: explains H-011's own mechanism (concentrated in the liquid half, not the illiquid half) | — | Real Sharpe 2.272 (liquid) vs. 0.574 (illiquid, below its own placebo mean) |
| H-014 | Rejected (diagnostic, ambiguous) | **Statistical power at the sub-bucket level** (halving the universe roughly halves breadth too) | — | High-momentum bucket passes placebo but fails HAC/iid |
| H-015 | Rejected (diagnostic, not a factor failure) | N/A — successful forensic finding: concentrated in the low-volatility half | — | Real Sharpe 1.835 (low-vol) vs. 1.216, placebo-failing (high-vol) |
| H-016 | Rejected | **Insufficient information / possible wrong proxy** (re-classified by the Frontier Methodology Audit — ADTV/turnover is the proxy family Bekaert-Harvey-Lundblad 2007 found non-predictive in EM; the zero-return/LOT proxy that paper found predictive was never tested) | Genuine absence remains a live alternative explanation, not ruled out | Placebo p=0.168 (illiquid), p=1.000 (liquid) |
| H-017 | Rejected | **Ambiguous between genuine absence and insufficient information** — payer-STATUS carries no information at whole-IRU breadth; whether payer-status is simply the wrong granularity (yield MAGNITUDE, structurally unmeasurable on this platform) remains open by the hypothesis's own pre-declared limitation (L1) | — | Gross excess ≈0%, placebo p=0.366, DSR below the pool's own chance benchmark |

### 1.2 What this matrix actually shows, synthesized

**No hypothesis on this platform has ever failed because of insufficient
field DEPTH.** This is the single most important, and previously
under-stated, finding of this audit. Every one of the 17 hypotheses
tested a technical, price/volume-derived characteristic — the one
information layer the platform has had continuously since its first
data acquisition. **Not one of the 11 fundamentals-dependent factor
families (Value, Quality, Growth, Profitability, Investment, Financial
Strength, Cash Flow Quality, Accruals, Asset Turnover, Gross
Profitability, Earnings Quality) has ever been tested and failed — they
have never been tested at all**, per
`docs/FACTOR_CANDIDATE_REGISTRY.md` and the FSI audit series
[Verified — registry].

**Within the technical side, the dominant, recurring, already-well-
understood causes are transaction costs and statistical power** —
5+ of the first 9 hypotheses were shaped primarily by cost drag
(`docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`), and a further three
(H-009, H-010, H-014) were shaped primarily by too few independent
decisions in a ~10-year sample. **Neither of these two dominant causes
is fixable by acquiring new data** — cost realism is already
well-modeled (per the Frontier Methodology Audit's own assessment), and
statistical power in a short sample is fixed only by the passage of
calendar time, not by any acquisition this document could recommend.

**Two rejections have real, disclosed uncertainty about whether they
reflect genuine market behavior or a measurement artifact** — H-016
(liquidity proxy choice) and H-017 (binary vs. yield-magnitude
granularity). Both are real, honest open questions, not resolved by
this audit; both are cheap to revisit later (Section W6-3) but neither
is evidence that new EXTERNAL data is required — the LOT-style proxy
identified for H-016 is computable from data the platform already has.

**Genuine, decisive "the effect does not exist" verdicts** (H-005,
H-008, H-012) are real, well-evidenced negative findings — not
attributable to any data or methodology gap, and not worth revisiting.

### 1.3 The honest answer to "has the dataset reached its ceiling"

**For the technical/price-volume information layer: essentially yes.**
Every well-motivated, zero-new-data technical idea with a clear
economic mechanism has now been tried, across momentum (6 forms),
volatility (2 forms), liquidity (1 standalone + 3 interaction tests),
size interactions, dividend payer-status, and event-driven/macro
timing (3 forms). The only two remaining zero-new-data technical
threads are narrow: the PEAD membership-only successor (H-006) and a
five-minute data-availability recheck on dormant H-002.

**For the platform's total information set: clearly no.** An entire,
standard half of equity-factor research has never been reachable. The
ceiling that has been hit is not a ceiling on ideas — it is the
boundary of a single information layer that has now been thoroughly
mined.

---

## Phase W6-2 — Information Value Analysis

*Ranking candidate DATASETS, not factor ideas, per instruction. Rows
marked **[Audited]** draw on a completed platform audit
(`docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`, the FSI audit series, or
this session's own database queries); rows marked **[Not yet audited]**
have no dedicated evidence base on this platform and are stated as such
rather than force-ranked with invented numbers.*

| Dataset | Status | Research capability unlocked | Factor families unlocked | Architectural impact | Engineering complexity | Maintenance burden | Validation complexity | Vendor dependence | Compatibility |
|---|---|---|---|---|---|---|---|---|---|
| **Expanded FSI depth** (balance sheet + cash flow, depth-first on the already-scoped candidate pool) **[Audited]** | Not acquired; a small pilot is the FSI Owner Decision Package's own top recommendation, still not executed | Highest of any candidate — the ONLY path to the entire fundamentals half of factor research | Up to 6 of 11 blocked families (Value, Quality, Financial Strength, Cash Flow Quality, Accruals, Asset Turnover), depending on real per-filing yield (unverified until the pilot runs) | None — schema, `financial_health_flags.py`, `financial_ratios` already built and reused across every prior FSI phase | Low (reuses Phase 1/2/13's validated hand-extraction methodology) | Medium-High at scale (per-ticker/sector idiosyncrasy: bank EBIT/EBITDA gap, abridged-filing cash-flow omission, ~33% of filings) | Medium (internal same-document cross-check only, never externally validated — a disclosed, standing gap) | None — no vendor, uses already-archived NGX filings | High — directly extends the existing `extracted_facts` schema, additive only |
| **NGX X-Compliance (free-float)** **[Audited]** | Not acquired; scoped as "near-term" in the Free Data Source Audit | Resolves H-011's own disclosed full-issue-cap construct-validity gap; enables a genuine free-float-adjusted benchmark, matching institutional frontier-index practice (MSCI/S&P/FTSE all free-float-adjust even at the frontier tier) | 0 NEW families unlocked directly — improves measurement QUALITY of Size and any future factor needing float-adjusted weights, does not unlock a family that is currently at zero | Low-Medium — a new structured table, one clear source format | Low-Medium (a recurring official report, not a heterogeneous filing archive) | Medium — historical archive depth uncertain, not yet scoped | None — no vendor, official NGX report | High |
| **FMDQ NAFEX / T-bill / bond rates** **[Audited]** | Not acquired; free tier limited to current/recent rates, bulk historical unconfirmed | Independent risk-free-rate cross-check; a continuous FX-regime conditioning variable (new) | 0 directly — a conditioning/context variable, not a standalone factor family | Low | Unknown — bulk historical access unconfirmed | Low once acquired | None — official source | Medium — bulk-history access itself unresolved | High |
| **DMO bond auction data** **[Audited]** | Not acquired; no bulk API, per-auction scraping required | Term-structure depth; a genuinely NEW factor family (duration/rate-sensitivity interaction) — the only candidate here that opens a wholly new family rather than deepening an existing one | 1 new family (rate-sensitivity), a family not currently named at all in `FACTOR_CANDIDATE_REGISTRY.md` | Medium — per-auction scraping, no bulk source | Medium-High | Medium | None — official source | Medium | Medium |
| **NBS CPI/GDP** **[Audited]** | Not acquired; rebasing-break handling required | New continuous macro-regime input (inflation-regime conditioning) | 0 directly — a conditioning variable | Low | Low-Medium (rebasing breaks need handling) | Low | None — official source | Low | High |
| **NEITI (extractive-industry revenue audits)** **[Audited]** | Not acquired; multi-year publication lag | A genuinely frontier-native signal with "no developed-market analogue at all" per the Free Data Source Audit's own framing — revenue-integrity/audit-divergence | 1 narrow, sector-specific family (extractive-sector governance signal) | Low | Medium | Low (infrequent publication) | Medium — a new signal construct, no precedent to validate against | Low | Medium |
| **GDELT (media-attention/event-intensity)** **[Audited]** | Not acquired | A frontier-specific VALUE proposition (low analyst coverage rationale) on a universal source | 1 new family (media-attention/information-diffusion) | Medium | Medium-High | Medium | High — no precedent on this platform for this signal type | None (public feed) | Medium |
| **Google Trends (retail-attention proxy)** **[Audited]** | Not acquired; unofficial API | Similar rationale to GDELT, narrower | 0-1 (overlaps GDELT's information-diffusion family) | Low-Medium | Low | Low-Medium (unofficial API stability risk) | Medium | Low (unofficial API is itself a dependency risk) | Medium |
| **NOAA VIIRS nightlights** **[Audited]** | Not acquired; high engineering cost | Regional-economic-activity proxy — novel, unproven at COMPANY level (a real, disclosed weakness in the original audit) | Unclear — no company-level precedent exists anywhere to anchor an estimate | High | High | Medium | High — entirely novel construct | None (public data) | Low |
| **FAOSTAT (commodity exposure)** **[Audited]** | Not acquired | Narrow — agro-sector-only interaction factor | 0 new, narrows an existing interaction | Low | Low | Low | Low | None | Medium |
| **World Bank WDI** **[Audited]** | Not acquired | Broad macro context only, not company-level | 0 | Low | Low | Low | Low | None | High |
| **UK Companies House / LSE RNS** **[Audited]** | Not acquired | Narrow — deepens ONE existing dual-listed name (Seplat)'s FSI coverage only | 0 new families | Low | Low-Medium | Low | Low | Low | Medium |
| **CAC (Corporate Affairs Commission) filings** **[Audited]** | Not acquired; forward-only, no historical snapshots | Board-stability/governance-turnover signal | 1 narrow family (governance/board-turnover) | Medium | Medium | Medium | Medium | Low | Medium |
| **Ownership structure / beneficial ownership registers** | **[Not yet audited — genuine gap]** | Unknown — no adequate free source was even identified in the original Free Data Source Audit's own "not found" category (item B5) | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |
| **Insider transactions** | **[Not yet audited]** | Plausible signal family (insider trading is a well-documented DM/EM anomaly), but no NGX-specific source has ever been scoped on this platform | Unknown, plausibly 1 new family if a source exists | Unknown | Unknown — likely requires a new extraction target from filings not yet characterized for this purpose | Unknown | Unknown | Unknown | Unknown |
| **Corporate governance (beyond X-Compliance)** | **[Not yet audited]** | Unclear incremental value over X-Compliance + CAC combined | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |
| **Analyst coverage / initiation tracking** | **[Not yet audited]** | Used only as a qualitative RATIONALE in H-016/H-017's economic mechanisms ("thin sell-side coverage") — never scoped as an acquirable dataset in its own right | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |
| **Alternative data (broadly)** | **[Not yet audited beyond GDELT/Trends/VIIRS above]** | Covered narrowly by the three items above; no broader category has been scoped | N/A — too broad a label to rank | — | — | — | — | — | — |

**The central, load-bearing finding of this table**: **only the
expanded-FSI-depth row unlocks multiple currently-zero-coverage factor
families at once.** Every other audited candidate either (a) improves
the measurement quality of an existing, already-tested characteristic
(free-float, FX rates), (b) opens exactly one narrow new family (DMO
bonds, NEITI, GDELT, CAC), or (c) has no dedicated evidence base at all
on this platform (ownership, insider transactions, governance beyond
X-Compliance, analyst coverage). **This is not a close call between
many well-evidenced options — it is one clearly dominant option and a
long tail of narrower or unevaluated ones.**

---

## Phase W6-3 — Marginal Research Value

*Ranked by expected research RETURN, not engineering effort, per
instruction. Effort is reported alongside for context, not as the
ranking criterion.*

| Option | Expected marginal research return | Basis |
|---|---|---|
| **1. Expanding FSI depth (the already-recommended pilot)** | **Highest** | Directly addresses the single largest, most repeatedly identified blocker on the entire roadmap (11 of 16 families); already scoped to a small, cheap pilot; the only option in this list that could plausibly produce the platform's SECOND validated, independent factor family rather than a variant of the first |
| **2. Improving methodology (the two remaining Methodology Hardening items)** | **High, but narrower** | The bonus/scrip-issue adjustment and unified ranking convention are real, disclosed gaps affecting every hypothesis's precision — but neither is expected to REVERSE any existing verdict (per the Methodology Hardening document's own [Judgment]-tagged assessment); value is in reliability, not new discovery |
| **3. Adding one new external dataset (best candidate: free-float/X-Compliance)** | **Medium** | Resolves one specific, real construct-validity gap (H-011) and matches institutional practice, but per W6-2 does not unlock any currently-zero-coverage family — a quality improvement on an already-confirmed factor, not a new discovery channel |
| **4. Improving validation (survivorship — already done this session; external cross-validation of FSI facts — not done)** | **Medium, and partially already realized** | The survivorship audit (Methodology Hardening M1) already captured most of the available value here at near-zero cost; the remaining validation gap (no external cross-check of any FSI fact, ever) is real but its marginal value is hard to estimate without knowing the error rate it would find — stated as [Assumption]: likely modest, since internal same-document cross-checks have found 100% pass rates on every pilot to date |
| **5. Another technical-factor hypothesis (beyond the two narrow zero-new-data threads named in W6-1)** | **Low** | Per W6-1, the technical/price-volume information layer is close to exhausted; a further variant would very likely repeat an established negative pattern (transaction costs or statistical power) rather than discover something new |
| **6. Improving portfolio construction** | **Not applicable yet — correctly gated** | Requires ≥2 validated independent factors (currently 1, and it is not cleanly independent per its own forensic decomposition); pursuing this now would violate the platform's own standing architectural guardrail, not a research-value question at all |

**A genuinely new insight from this ranking exercise**: options 1 and 2
are not competing for the same research cycle — the FSI pilot is a
labor/data question, the methodology fixes are a small, bounded
engineering task. **Both could run in parallel without resource
conflict**, a point the milestone roadmap below (W6-4) makes explicit
rather than forcing a false sequential choice.

---

## Phase W6-5 — Opportunity Cost

**Which missing information is currently preventing the largest amount
of research?** Unambiguously, FSI depth — per the Coverage Expansion
Decision Audit, 11 of 16 named candidate factor families share this
one root blocker. No other candidate in W6-2's table blocks more than
one family. This is not a close comparison.

**Which datasets have the highest "alpha per engineering hour"?**
[Assumption/Estimate, since no realized alpha exists yet for any
fundamentals-based factor to measure against]: FSI depth is very
likely the highest, given (a) zero new data acquisition cost (the
filings already exist in the archive), (b) a validated, reused
extraction methodology (Phases 1/2/13), and (c) the largest number of
blocked families addressed per unit of labor. Free-float is the second
most plausible candidate by this same logic — also zero acquisition
COST in the sense that NGX publishes it officially, but addresses only
one, already-confirmed factor's construct validity rather than opening
new territory.

**Where are diminishing returns likely to begin?** [Assumption,
reasoned from W6-2's table]: at the exotic frontier-native sources
(NEITI, GDELT, nightlights, Google Trends) — each unlocks at most one
narrow family, each carries meaningful engineering/validation cost or
an entirely novel, unprecedented construct with no track record on
this platform, and none has been shown to unlock more than the single
family it targets. **These are not bad ideas — they are the platform's
most genuinely frontier-native opportunities per the earlier Wave 5
review — but per this analysis they belong AFTER the FSI/free-float
decisions, not before, exactly as the Frontier Methodology Audit
already concluded for a related reason (statistical adaptation should
precede novel-data adaptation).**

**The cost of NOT acquiring FSI depth, stated plainly**: every month
this pilot remains unexecuted is a month in which 11 of 16 standard
equity factor families — including Value and Quality, arguably the two
most foundational families in all of institutional equity research —
remain completely untestable on this platform, regardless of how many
more technical-factor hypotheses are run.

---

## Phase W6-4 — Wave 6 Research Roadmap (milestones, not phases)

### Milestone A — Close the two remaining Methodology Hardening items
- **Objective**: implement the bonus/scrip-issue price-adjustment
  mechanism and unify cross-sectional ranking onto the platform's own
  already-justified percentile-rank precedent (per
  `docs/METHODOLOGY_HARDENING_2026-08-04.md` Phase M4).
- **Prerequisite**: none — fully scoped, zero new data.
- **Expected research capability gained**: improved reliability of
  every future hypothesis's precision, not a new discovery channel.
- **Measurable completion criteria**: bonus-issue adjustment mechanism
  implemented and unit-tested against at least one real, verified
  historical bonus event; ranking convention unified across both
  backtest engines with a documented, deliberate decision on
  winsorization either way.
- **Dependencies**: none.
- **Stopping condition**: complete when both are shipped and disclosed
  in the platform's own limitations documentation — this is a small,
  bounded item, not an open-ended one.

### Milestone B — FSI depth-first pilot (the platform's own
already-recommended, still-unexecuted next step)
- **Objective**: execute exactly what `docs/FSI_OWNER_DECISION_PACKAGE_2026-08-03.md`
  already specifies — a real, human-timed extraction trial, the
  ticker-attribution bug fix, a small hand-verification pilot of the
  tabular `results_notice` format on 3-5 tickers, and the `pbt`/`eps`
  schema addition.
- **Prerequisite**: none beyond owner authorization for the (small,
  already-bounded) labor and schema-change items — not gated on
  Milestone A.
- **Expected research capability gained**: a real, evidence-based
  answer to whether Value/Quality/Financial Strength testing is
  achievable at the ~15-25 ticker breadth the FSI Owner Decision
  Package already identified as the target milestone.
- **Measurable completion criteria**: exactly the FSI Owner Decision
  Package's own milestone — a confirmed, hand-verified ≥15-25 ticker
  set with full three-statement depth, OR a clear negative finding
  (fewer tickers converting) that itself resolves the open question.
- **Dependencies**: none technical; one owner decision (labor
  authorization), already the single most-repeated unresolved item
  across four prior FSI audits.
- **Stopping condition**: if the pilot yields fewer than ~10 tickers
  with full depth (below even the platform's own minimum code-level
  breadth floor), STOP — do not escalate to a larger extraction
  commitment; fall back to Milestone D instead.

### Milestone C — First fundamentals-based factor test (CONDITIONAL —
only if Milestone B succeeds)
- **Objective**: pre-register and test the first Value or Quality
  hypothesis using the newly-available fundamentals depth.
- **Prerequisite**: Milestone B's own completion criteria met.
- **Expected research capability gained**: the platform's first-ever
  test of a factor family outside the technical/price-volume layer —
  the highest-value single event this roadmap can produce.
- **Measurable completion criteria**: a full pre-registration,
  implementation, and Phase 4 gauntlet result (confirmed or rejected),
  exactly matching the standard methodology used for H-001 through
  H-017.
- **Dependencies**: Milestone B.
- **Stopping condition**: none beyond the hypothesis's own pre-declared
  confirmation/rejection criteria — this is a normal hypothesis test at
  that point, not a special case.

### Milestone D — Free-float acquisition (NGX X-Compliance)
- **Objective**: resolve the vendor/acquisition decision open since
  2026-07-16, and build the structured free-float table.
- **Prerequisite**: none technical; independent of Milestones A-C.
- **Expected research capability gained**: a float-adjusted Size
  retest (resolving H-011's own disclosed limitation) and a
  free-float-deficiency governance signal.
- **Measurable completion criteria**: a structured, versioned
  free-float table covering at minimum the current 100-member IRU.
- **Dependencies**: none.
- **Stopping condition**: if historical archive depth proves too
  shallow to support a PIT-safe retest across multiple regimes
  (unscoped risk per W6-2), the acquisition may still be worthwhile for
  a CURRENT-only snapshot use, but a full retest should not proceed
  until depth is confirmed.

### Milestone E — Scoping pass on the four not-yet-audited candidates
(ownership structure, insider transactions, governance beyond
X-Compliance, analyst coverage)
- **Objective**: a cheap, read-only audit (mirroring the Free Data
  Source Audit's own methodology) to determine whether any adequate
  free source exists for these four categories — currently genuinely
  unknown, not just unranked.
- **Prerequisite**: none.
- **Expected research capability gained**: converts four "unknown"
  rows in W6-2's table into either real candidates or confirmed dead
  ends — a scoping outcome, not a data acquisition itself.
- **Measurable completion criteria**: a completed audit document
  analogous to the Free Data Source Audit, covering these four
  categories specifically.
- **Dependencies**: none; can run in parallel with any other milestone.
- **Stopping condition**: complete when all four categories have a
  documented status (available/not found/partially available).

### Milestone F — Frontier-native factor exploration (NEITI, X-Compliance
governance signal, FMDQ NAFEX conditioning) — explicitly LAST
- **Objective**: the genuinely frontier-native research direction named
  in Wave 5 and reaffirmed here.
- **Prerequisite**: **Milestone D (free-float) AND the Frontier
  Methodology Audit's own thin-trading econometric correction
  (unaddressed as of this document)** — running novel frontier data
  through an unadapted statistical pipeline risks an uninterpretable
  null, exactly the risk the Frontier Methodology Audit named.
- **Expected research capability gained**: the platform's first
  genuinely frontier-native (not developed-market-technique-applied-to-
  frontier-data) hypothesis.
- **Measurable completion criteria**: a full pre-registration and test,
  same standard as every other hypothesis.
- **Dependencies**: Milestones D and the (separately tracked, still
  open) thin-trading correction.
- **Stopping condition**: do not begin until both prerequisites are
  met — this is a hard sequencing rule, not a preference, carried
  forward unchanged from the Frontier Methodology Audit.

**Dependency graph** (milestones without an arrow between them can run
concurrently):

```
Milestone A (methodology closure)  ──╮
                                      ├── independent, can run in parallel
Milestone B (FSI pilot) ─────────────┤
Milestone D (free-float) ────────────┤
Milestone E (scoping pass) ──────────╯

Milestone B ──(if successful)──> Milestone C (first fundamentals factor)

Milestone D + [thin-trading correction, tracked separately] ──> Milestone F
```

---

## Institutional Review

### Frontier Market Academic

**Criticism**: "Your W6-2 table gives NEITI and GDELT real rows with
real detail, but ranks them below FSI depth and free-float — both
developed-market-style improvements. Isn't this roadmap just delaying
the platform's most genuinely frontier-native opportunity in favor of
more conventional work, contradicting the whole thrust of the Frontier
Methodology Audit?"

**Response**: This is addressed directly, not deflected — Milestone F
explicitly preserves the frontier-native direction as a real, still-
prioritized destination, not an abandoned one. The sequencing (not the
priority) is what's being defended: per the Frontier Methodology
Audit's own conclusion (independently reached, not invented for this
document), running a genuinely novel frontier dataset through the
platform's still-unadapted statistical pipeline risks an
uninterpretable result — a false negative that would look identical to
every prior null. Free-float and the thin-trading correction are
listed as PREREQUISITES to Milestone F for that specific, evidenced
reason, not because conventional data is inherently more valuable.

### Quant Research Director

**Criticism**: "Milestone B's stopping condition — 'fewer than ~10
tickers, fall back to Milestone D' — treats 10 as a hard breadth floor,
but your own Wave 5 document called the 20-35 range a 'reasoned
judgment, not a derived figure,' and warned specifically against
treating it as validated. Are you now treating an even lower, less-
justified number as a hard stopping rule?"

**Response**: A fair, precise catch. The 10-name floor cited here is
not the same number as Wave 5's 20-35 reasoned range — it is the
platform's own CODE-LEVEL minimum (`_eligible()`'s `len(elig) < 10`
guard, used mechanically across every `xs_*` method) below which no
test can even run, not a claim about statistical credibility. This
should be stated more precisely: **falling below 10 means the pilot
literally cannot produce a runnable test; falling between 10 and the
reasoned 20-35 floor means a test could run but would repeat the
platform's own most common historical failure mode (breadth-ceiling
rejections).** The stopping condition in Milestone B is revised to
reflect this two-tier distinction rather than treating 10 as a
sufficiency bar.

### Asset Pricing Researcher

**Criticism**: "W6-1 classifies H-016 and H-017 as having 'ambiguous'
causes — possibly genuine absence, possibly a measurement problem. But
you don't actually resolve this ambiguity anywhere in the roadmap. If
it's real and cheap to check (per your own Section W6-3), why isn't
revisiting H-016 with a LOT-style proxy an explicit milestone here,
instead of left as an unresolved footnote?"

**Response**: A legitimate gap in the roadmap as drafted, and it should
be corrected rather than left implicit. This is added as an explicit
addendum to Milestone A (methodology closure), since it shares that
milestone's profile exactly — zero new data, small and bounded,
independent of the FSI/free-float track: **implement and test a LOT or
Amihud-style liquidity proxy (already identified as zero-new-data-cost
in the Frontier Methodology Audit's Part 3) as a supplementary,
non-hypothesis-registering robustness check on H-016's own conclusion**
— not a new hypothesis ID, but a methodology-quality check on an
existing rejected result, exactly parallel to how the survivorship
audit checked an existing architectural assumption rather than
registering as new research.

### Data Engineering Lead

**Criticism**: "Milestone E (the scoping pass on ownership/insider/
governance/analyst-coverage data) is listed as low-effort and
independent, but you have zero evidence for that — you've explicitly
labeled these four categories as 'genuinely unknown.' Isn't claiming
this is a small, parallel-runnable milestone itself an unsupported
estimate, exactly the kind of thing this document says it won't do?"

**Response**: Accepted directly. The claim that this milestone is
"cheap" is an unlabeled estimate as originally drafted, and it is
corrected here: **Milestone E's effort is itself unknown until the
scoping pass begins** — what is known is only that it mirrors a
methodology (the Free Data Source Audit's own approach) that has been
executed before at a documented, bounded cost. The milestone's own
completion criteria and stopping condition are unaffected, but its
"expected effort" framing is removed rather than asserted without
evidence.

### Portfolio Manager

**Criticism**: "Every milestone in this roadmap, including the
'highest-return' one, ends in either a research finding or a data
table — none of them produces anything I could allocate capital to.
When, under this roadmap, does the platform actually get a SECOND
deployable factor, even in principle?"

**Response**: The honest answer, stated as plainly as it was in the
Wave 5 review: **not guaranteed by this roadmap at all, and possibly
not within Wave 6.** Milestone C (the first fundamentals-based factor
test) is the earliest point at which a second candidate could emerge,
and it is explicitly conditional on Milestone B succeeding — a real,
disclosed uncertainty, not a promise. This roadmap's purpose, stated
directly in its own framing, is to increase the PROBABILITY of
eventually finding a second independent factor by fixing the
information bottleneck that has made 11 of 16 standard families
untestable — it is not a commitment to produce one on any particular
timeline, and this document does not pretend otherwise.

### Chief Investment Officer

**Criticism**: "You've spent six documents now (Wave 4, Wave 5,
Frontier Methodology Audit, Methodology Hardening, H-017, and now this)
without a single new confirmed factor since H-011 two weeks ago. At
what point is 'more information, more rigor' actually the right call
versus a sign the program should consolidate around what it already
has — one small, capacity-constrained, imperfectly-independent factor
— rather than keep expanding scope?"

**Response**: This is the most senior-level, hardest challenge in this
review, and it deserves a direct answer rather than a defense of
activity. The honest case for continuing rather than consolidating is
narrow and specific, not a general appeal to "more research is always
good": **11 of 16 standard factor families have literally never been
tested on this platform, for a data reason that is now well-diagnosed
and has a small, cheap, already-scoped fix (Milestone B) sitting
unexecuted.** Consolidating around H-011 alone, without first checking
whether that fix works, would mean permanently accepting a
single-factor, capacity-constrained platform without ever having asked
its most standard, most foundational research questions (Value,
Quality) even once. If Milestone B is run and fails to produce usable
depth, the CIO's implied recommendation — stop expanding scope, work
with what exists — becomes the right call, and this document's own
Milestone B stopping condition already says so explicitly. The
disagreement, if there is one, is about whether to run one more small,
cheap, already-scoped check before making that call — not about
whether unlimited further expansion is warranted, which this document
does not argue for.

---

## Revisions made in response to the review

- Milestone A's scope is expanded to explicitly include a LOT/Amihud
  liquidity-proxy robustness check on H-016 (Asset Pricing Researcher).
- Milestone B's stopping condition now distinguishes the code-level
  10-name floor (below which no test can run) from the reasoned 20-35
  breadth range (below which a test can run but would repeat the
  platform's most common historical failure mode) (Quant Research
  Director).
- Milestone E's "low effort" framing is removed and replaced with an
  honest "effort unknown until scoped" (Data Engineering Lead).
- Milestone F's sequencing rationale (why frontier-native work waits) is
  stated more explicitly as evidence-based, not a value judgment
  against frontier-native research (Frontier Market Academic).
- The Portfolio Manager and Chief Investment Officer critiques are both
  answered with an explicit, undefended admission that this roadmap
  does not guarantee a second deployable factor within Wave 6 — stated
  in the executive answers at the top of this document as well, not
  only in the review section.

---

## What this document does not do

It does not register H-018 or any new hypothesis. It does not
implement any extraction, schema change, or new signal. It does not
assume FSI expansion is automatically first — Milestone B earned that
position through W6-1 through W6-5's evidence, and the roadmap
explicitly names the condition under which it would be deprioritized
(Milestone B's own stopping condition, falling back to Milestone D).
