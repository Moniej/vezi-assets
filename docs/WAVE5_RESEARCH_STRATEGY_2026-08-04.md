# Wave 5 Research Strategy — Program-Level Review

*2026-08-04. Strategic review only — no implementation, no code, no
database writes, no new hypothesis registration, no H-017
pre-registration. Every factual claim below is sourced from the
platform's own registry (`data/registry.sqlite`), `docs/FACTOR_REGISTRY.md`,
`docs/FACTOR_CANDIDATE_REGISTRY.md`, `docs/LESSONS_LEARNED_FROM_WAVES_1_AND_2.md`,
`docs/PLATFORM_ARCHITECTURE.md`, `docs/WAVE_3_RESEARCH_DIRECTIONS.md`,
`docs/WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`,
`docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`,
`docs/INSTITUTIONAL_AUDIT_WAVE2_2026-08-02.md`,
`docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`, `docs/LIM_ARCHITECTURE.md`,
and the four-document FSI audit series culminating in
`docs/FSI_OWNER_DECISION_PACKAGE_2026-08-03.md`. The question this
document answers is not "what hypothesis is next" but "is the research
program itself asking the highest-value questions."*

---

## 1. Research Program Audit

### 1.1 Every hypothesis, evaluated

| H-ID | Objective | Outcome | What was learned | Eliminated a class? | Opened a direction? | Remaining uncertainty |
|---|---|---|---|---|---|---|
| H-001 | Sector-level 3-6M price momentum beats NGX ASI after costs | Rejected | Placebo failure both variants; 0/20 cells survive correction; 100% concentrated in one 2023-24 regime | Sector-level price momentum, in this exact form | Yes — motivated H-002 (total-return) and H-003 (direct catalyst test) | H-002 (dividend-adjusted variant) never resolved |
| H-002 | Dividend-adjusted total-return sector momentum beats NGX ASI | **Untested — blocked on dividend dataset** | N/A | No | No | Genuinely open. A dividend/ex-date dataset now exists (`exdiv_closure_calendar.csv`, used by H-016/H-017) — whether this actually unblocks H-002 has never been re-checked |
| H-003 | Catalyst/event-driven sector rotation beats NGX ASI | Rejected | Placebo p=0.198 (better than random, not significant); OOS uninformative (ASI fallback held throughout) | Direct-catalyst framing of the sector-dispersion thesis | Partially — confirms the underlying sector-dispersion premise isn't obviously false, just unconfirmed here | OOS window never actually tested the hypothesis (fallback triggered) — a genuine "untested, not falsified" residue |
| H-004 | Lagged Brent crude moves predict NGX Oil & Gas sector returns | Rejected | Placebo p=0.079 (near-miss); 0/8 cells BH-significant; final-OOS excess -11.9% vs dev +6.6% | Oil-to-equity lead-lag, at this lag structure | No | Whether a different lag window would clear placebo was never tested — closed by resource priority, not by exhaustive search |
| H-005 | NGX sector returns show exploitable patterns around CBN MPC dates | Rejected | Every rejection trigger fired; placebo p=1.00 (worse than ALL 100 shuffles); cost drag ~40%/yr with ~zero gross excess | MPC-announcement-window timing effects | No | None material — this is the cleanest, most decisive rejection in the registry |
| H-006 | Filing-window PEAD reaction, ranked top-tercile, beats EW-IRU | Rejected | Gross PEAD reaction is real and large, but ranking within the event cohort carries no information — only event *membership* might; 20-slot book turnover far costlier than estimated | Ranked/top-tercile PEAD selection | **Yes — explicitly named a new, untested design**: membership-only (any-event, unranked) PEAD, never registered as its own ID | Whether membership-only PEAD would clear placebo is completely open |
| H-007 | Cross-sectional 12-1 momentum, per-stock, beats EW-IRU | Rejected | Selection indistinguishable from persistence-preserving random relabelings despite adequate per-stock breadth; gross excess +2.2%/yr | Per-stock 12-1 momentum at quarterly cadence | Partially — motivated the cost-vs-power redesign line (H-009) | None material |
| H-008 | Long the lowest-volatility IRU quintile beats EW-IRU | Rejected | Robustly *wrong-signed* (Holm-significant against), across all 3 regimes including OOS | Unconditional low-volatility anomaly on NGX in this sample window | Yes — motivated the regime-gated retest (H-012) | Whether a genuinely calm multi-year regime (never observed 2016-2026) would behave differently is untestable with current history |
| H-009 | Same signal as H-007, annual/semiannual cadence (turnover fix) | Rejected | Sign flipped as predicted by H-007's post-mortem — turnover WAS the problem — but only ~9 independent annual decisions exist; underpowered, not wrong-signed | Confirms cost-drag diagnosis; demonstrates a genuine power ceiling from the cadence fix itself | Yes — directly motivated H-010's cohort-pooling attempt | Whether momentum is directionally real but permanently untestable at adequate power on NGX's short history remains open |
| H-010 | Pooled overlapping-cohort 12-1 momentum (4 staggered cohorts) | Rejected | Pooling degraded rather than improved the placebo result; H-009's near-miss is now diagnosed as likely a calendar-alignment artifact of one specific formation date, not genuine skill | Cohort-pooling as a power-fix for this specific signal | No | Whether a non-overlapping, differently-designed power fix exists was not tried — the family was retired instead |
| H-011 | Long smallest-cap IRU quintile beats EW-IRU | **Confirmed** — first validated factor | Real effect, but concentrated in illiquid, capacity-constrained names (LASACO, MULTIVERSE, NCR); full-issue (not float-adjusted) cap is a disclosed construct-validity gap | No | **Yes — the platform's central open thread**: motivated the entire Phase R2 interaction-forensics program (H-013/014/015) and H-016 | Whether the effect survives on a float-adjusted cap (data not yet acquired) is unresolved |
| H-012 | Low-vol, gated to macro-stable formation dates only | Rejected | Regime gate does not rescue H-008 — the STABLE-classified subset is *more* significantly wrong-signed (t=-4.02) than the unconditional test | Regime-conditional rescue of low-volatility specifically | No | Whether regime-conditioning helps *any* other family (untested elsewhere) is open |
| H-013 | Does Size survive a double sort against Liquidity? | Rejected (forensic, not standalone) | Explained away — Size premium is concentrated in the LIQUID half of small caps, opposite of the a priori illiquidity-compensation concern | Illiquidity-compensation as the mechanism behind H-011 | Yes — reframes H-011's true economic story | What *does* explain the liquid-small-cap concentration, if not illiquidity compensation, is unresolved |
| H-014 | Does Size survive a double sort against Momentum? | Rejected (forensic) — **partially explained** | High-momentum bucket passes placebo (p=0.0297) but fails HAC/iid; low-momentum bucket is comprehensively strong (2/4 Holm, 3/4 BH significant) | Not a full elimination — genuinely ambiguous result, disclosed as such | Yes — the only interaction result that isn't a clean "explained away" | Whether Size is a momentum-conditional effect is not resolved either way |
| H-015 | Does Size survive a double sort against Volatility? | Rejected (forensic) | Explained away — concentrated in the LOW-volatility half of small caps | Volatility as an alternative Size mechanism | Yes — combined with H-013, the emerging picture is a liquid + low-vol small-cap effect, not a pure Size effect | The compound nature of this effect (liquid ∩ low-vol ∩ momentum-ambiguous small caps) has never been tested as its own explicit joint sort |
| H-016 | Does whole-universe ADTV liquidity carry a premium, either direction, independent of Size? | Rejected in full (both legs) | Neither illiquid nor liquid direction clears any confirmation criterion; Leg B (liquid) rejected more decisively (placebo p=1.00) | Standalone liquidity premium, in either direction, at whole-universe breadth | No | Reconciled explicitly with H-013: liquidity matters *within* Size, not on its own — a genuinely resolved, non-contradictory finding |

### 1.2 Program-level evaluation (not a per-hypothesis summary)

**Hit rate: 1 confirmed of 16 registered (6.25%), 1 permanently dormant
(H-002), 14 rejected.** A low hit rate is not itself a red flag for a
disciplined program — placebo-first, pre-registered research *should*
reject most ideas, and the registry's own rejection quality (specific,
falsifiable, diagnosed causes rather than vague "didn't work") is
genuinely strong. The more important question is not the hit rate but
whether the *sequence* of hypotheses was well-chosen.

**The program over-invested in one family before the cost-drag lesson
generalized.** Five of the first nine hypotheses (H-001, H-003, H-005,
H-006, H-007) were killed primarily by transaction costs
(`LESSONS_LEARNED...md`'s own count). A sixth and seventh (H-004, H-009)
lived or died on the same margin. That is 7 of the first 10 hypotheses
substantially shaped by one recurring mechanism. The program did adapt
(H-009's turnover-budgeted redesign, H-010's pooling attempt) — but
both adaptations were still momentum-family variants. **Six hypotheses
in total (H-001, H-003 partially, H-004 partially, H-007, H-009, H-010)
tested some form of momentum or a momentum-adjacent catalyst**, and all
six failed. This is a legitimate, well-evidenced elimination — but it
also means over a third of the registry's total hypothesis budget went
to one family, using up research cycles that a faster generalization of
the cost-drag lesson might have redirected sooner toward Size or
Liquidity.

**The platform's one confirmed factor is not what it initially looked
like.** H-011 was registered and confirmed as "Size." Phase R2's own
forensic work (H-013/014/015) subsequently showed this effect is
concentrated in the liquid, low-volatility half of small caps, and is
ambiguous (not cleanly independent) with respect to momentum. **The
platform's factor registry currently labels this "Size — confirmed,"
which is a defensible summary but not a precise one** — see the
Academic Asset Pricing Researcher's critique in the adversarial review
below, which challenges this labeling directly.

**A real, disclosed methodological inconsistency exists across the
registry's own history.** HAC (Newey-West) and Deflated Sharpe Ratio
were only standardized platform-wide via METH-001 on 2026-08-02 — after
H-001 through H-012 were already resolved. Those twelve hypotheses were
evaluated under the pre-hardening statistical stack (Holm/BH and
placebo existed from Wave 1, but not HAC or DSR). **None of the twelve
pre-METH-001 rejections has been retroactively re-evaluated under the
current statistical standard.** For rejections this is low-risk (a
rejection that holds under a weaker standard almost certainly holds
under a stronger one), but it does mean the registry's internal
statistical rigor is not uniform across its own history — worth
disclosing plainly rather than leaving implicit.

**The most methodologically valuable moment in the whole registry is
the H-009→H-010 diagnosis**, not any single confirm/reject verdict: the
platform caught its own near-significant result (H-009, placebo
p=0.069) and correctly diagnosed it as a probable calendar-alignment
artifact rather than accepting it or blindly rerunning the same design
hoping for a different draw. That is a genuinely institutional-grade
catch, and it is the single clearest piece of evidence that this
program's discipline exceeds what its raw hit-rate would suggest.

---

## 2. Research Coverage

| Category | Status | Evidence |
|---|---|---|
| **Size** | **Completed** (confirmed, but compound — see §1.2) | H-011 confirmed; H-013/014/015 decompose it |
| **Momentum** | **Completed / eliminated** | H-001, H-003 (partial), H-004 (partial), H-007, H-009, H-010 — six tests, robust rejection across sector/per-stock/pooled/turnover-budgeted designs |
| **Volatility (low-vol)** | **Completed / eliminated** | H-008 (unconditional), H-012 (regime-gated) — both wrong-signed, not merely null |
| **Liquidity** | **Completed / eliminated as standalone; confirmed as a modifier of Size** | H-016 (standalone, both directions, rejected); H-013 (as Size interaction, explains Size's concentration) |
| **Dividend** | **Partially explored** | H-002 dormant/untested (total-return momentum, blocking dataset possibly resolved but never re-checked); H-017 (payer-status) fully designed, never registered; dividend *yield/magnitude* blocked by DOL EPS/P.E. parser's two documented failures |
| **Value** | **Not yet started — blocked by data** | Requires net_profit+equity jointly; FSI ceiling (9/100 IRU members with any fact) |
| **Quality** | **Not yet started — blocked by data** | Same FSI ceiling |
| **Growth** | **Not yet started — blocked by data**, and additionally by an unverified multi-period-per-ticker gap | FSI ceiling; multi-period depth per ticker never separately audited |
| **Profitability** | **Not yet started — blocked by data, worse than most** | No `gross_profit` fact_type exists anywhere on the platform — this family has never even had an extraction target defined, let alone data |
| **Investment (asset growth)** | **Not yet started — blocked by data** | Requires assets, multi-period; same FSI ceiling |
| **Financial Strength (Piotroski-style)** | **Not yet started — blocked by data** | Requires assets+liabilities+equity jointly — stuck at 5 tickers since Phase 2, unmoved through 25 subsequent phases |
| **Composite factors** | **Blocked — architecturally gated** | Requires ≥2 validated independent factors; only 1 exists, and per §1.2 it is itself a compound, non-independent effect |
| **Regime conditioning** | **Partially explored, narrowly** | Only tested once, as a gate on low-volatility (H-012) — failed to rescue it. Never tested as a gate on Size, on any macro variable beyond the MPC-event rule, or via a continuous (non-binary) regime variable |
| **Interaction effects** | **Partially explored, narrowly** | Only Size × {Liquidity, Momentum, Volatility} has been tested (Phase R2). No interaction has been tested among any rejected factor, and no three-way joint sort (e.g., liquid ∩ low-vol ∩ small) has been run despite H-013/H-015 jointly implying one might be informative |
| **Event-driven (PEAD/catalyst/macro-window)** | **Explored, mostly eliminated, one open thread** | H-003, H-004, H-005 eliminated; H-006 (PEAD) found a real gross effect with an explicitly named, never-registered successor design (membership-only) |

**The single clearest coverage fact**: 11 of the platform's own 16
named candidate factor families in `FACTOR_CANDIDATE_REGISTRY.md` share
one root blocker — FSI fundamental-data depth. Every technical
(price/volume/liquidity-derived) factor family reachable with current
data has now been tested at least once. **The technical-factor research
space, as currently scoped, is close to exhausted** — not because every
conceivable technical idea has been tried, but because the ones with
clear theoretical motivation and no new data requirement (Momentum,
Volatility, Liquidity, Size, and Size's interactions) all have been,
and the next entrant (Dividend) is the last one on the list that
doesn't require new data.

---

## 3. Frontier Market Research Audit

**The platform's own Wave 2 institutional audit already reached the
sharpest version of this verdict, and nothing since has changed it**:
*"hybrid, and the hybrid is uneven — frontier-market adaptations in the
DATA layer, developed-market-academic technique in the STATISTICAL
layer, with no emerging/frontier-specific statistical adjustments at
all."* (`INSTITUTIONAL_AUDIT_WAVE2_2026-08-02.md`)

**Where the platform is genuinely applying known global factor
research, unmodified**: the entire statistical apparatus — Sharpe
ratios, HAC/Newey-West standard errors, Holm/Benjamini-Hochberg
multiple-testing correction, Deflated Sharpe Ratio, placebo-permutation
testing, portfolio-sort methodology — is the standard developed-market
academic finance toolkit (AQR/Fama-French/López de Prado-style), applied
without modification to NGX data. **No non-synchronous-trading
(Scholes-Williams-style) correction has ever been implemented**, despite
NGX's documented thin-trading characteristics being explicitly named as
a confound in multiple pre-registrations (most explicitly H-016's own
"frontier confounds" section). This is a real, disclosed, and — as of
this document — still entirely unaddressed methodological gap: the
platform's econometrics have not yet been adapted for frontier
microstructure at all, even though multiple pre-registrations
*acknowledge* the confound exists.

**Where the platform is adapting emerging-market techniques**: the
Size hypothesis (H-011) was motivated by a capacity/illiquidity-friction
compensation rationale common in emerging-market small-cap research, not
a pure developed-market CAPM-extension story. The event-driven family
(H-003/H-005/H-006) targeted NGX-specific catalysts (CBN MPC decisions,
recapitalisation directives) rather than generic developed-market
event types.

**Where the platform has begun genuinely frontier-specific idea
generation, though none has been tested yet**: H-016's own
pre-registration explicitly frames itself as "a frontier-market
technique with a genuinely Nigeria-specific empirical question layered
on top" — leaving the illiquidity-premium *direction* open rather than
assuming the developed-market sign, which is the right frontier-market
posture even though the result was null in both directions. More
concretely, `FREE_DATA_SOURCE_AUDIT_2026-08-02.md` identifies several
data sources with **no developed-market analogue at all**: most notably
**NEITI** (Nigeria Extractive Industries Transparency Initiative)
revenue-audit-divergence data, described in the audit itself as having
"no developed-market analogue at all" — a genuinely frontier/extractive-
economy-native signal. **NGX X-Compliance** free-float reporting (a
governance/disclosure-deficiency signal tied to NGX's own thin-liquidity
market structure) and **FMDQ NAFEX** FX-fixing data (which exists
specifically because of Nigeria's historically fragmented FX market
structure) are similarly frontier-native in a way no simple "apply a
known DM factor to NGX data" exercise could produce. **None of these
three has been acquired or tested.**

**Verdict**: the platform is still substantially in the "developed-market
technique applied to frontier-market data" phase. The data layer has
started reaching for genuinely frontier-native inputs (NEITI, X-Compliance,
NAFEX), and H-016's bidirectional framing shows the right instinct at
the hypothesis-design level — but two things are missing before "genuinely
frontier-specific alpha research platform" is an earned description
rather than an aspiration: (1) the statistical layer has never been
adapted for frontier microstructure, and (2) not one of the frontier-native
data sources identified has actually been acquired or turned into a
tested hypothesis yet. The FSI-related discovery that a real share of
NGX filings are legally "abridged" and simply omit cash-flow statements
is itself a frontier-market-specific disclosure-regime fact — and it has
not yet been turned into a research question of its own (e.g., does
disclosure completeness itself carry information), which is a missed
opportunity worth naming even though it wasn't on the original taxonomy list.

---

## 4. Alpha Opportunity Map

| Opportunity | Category | Basis |
|---|---|---|
| H-017 (Dividend payer-status) | **Immediately testable** | Fully designed in `WAVE_4_RESEARCH_DIRECTIONS_2026-08-03.md`; zero new data acquisition |
| H-002 revival check (total-return momentum) | **Immediately testable** (pending a cheap re-check) | The dataset it was blocked on (dividend/ex-date data) may now exist per H-016/H-017's own `exdiv_closure_calendar.csv` use — a five-minute data-availability check, not new research, would resolve whether this is still blocked |
| PEAD membership-only design (H-006 successor) | **Immediately testable** | Explicitly named by H-006's own conclusion; same event dataset (8,685 PIT filings), no new acquisition |
| Non-synchronous-trading statistical correction | **Blocked by research** (methodology design, not data) | Named as absent in Wave 2 audit; no design work has been done; this is prerequisite groundwork, not itself a hypothesis |
| Survivorship-bias audit on IRU construction | **Blocked by research** (methodology, not data) | Flagged "unverified" in Wave 2 audit, never actually run; a foundational check, cheap relative to its importance |
| Value / Quality / Financial Strength / Cash Flow Quality / Accruals | **Blocked by data** | FSI 9-10-ticker ceiling; addressed by the FSI Owner Decision Package's depth-first pilot recommendation, not yet executed |
| Free-float-adjusted Size retest | **Blocked by data** | NGX X-Compliance not acquired; directly addresses H-011's own disclosed full-issue-cap construct-validity gap |
| FX-regime conditioning (any factor) | **Blocked by data** | FMDQ NAFEX not acquired |
| NEITI revenue-integrity signal | **Blocked by data** | Not acquired; extractive-sector-only scope, multi-year publication lag |
| Dividend magnitude/yield factors | **Blocked by engineering** | DOL EPS/P.E. parser has failed twice (58.5%, then 34.3% pass rate); no per-format-era calibration attempt has been made |
| Deterministic tabular-block FSI extraction | **Blocked by engineering** | Real structural candidate identified (112 `results_notice` documents, 19 tickers) but unpiloted; FSI Owner Decision Package names this as the next concrete build item |
| OCR/vendor pipeline (184 additional tickers) | **Blocked by owner decision** | Open since 2026-07-16, unresolved across every subsequent audit |
| Corporate-action event drift (Wave 3's C3) | **Blocked by research** | Explicitly deferred pending its own classification-pipeline validation pass |
| Composite factor construction | **Blocked by research + architecture** | Requires ≥2 validated *independent* factors; only 1 exists and it is not cleanly independent of Liquidity/Volatility (§1.2) |
| Regime-conditioning beyond low-vol | **Blocked by research** | Only one family has ever been tested this way; no generalized regime-conditioning methodology exists yet |
| Three-way small-cap joint sort (liquid ∩ low-vol ∩ small) | **Blocked by research** | Implied but never tested by H-013+H-015's joint pattern |
| Media-attention / analyst-neglect factor (GDELT, Google Trends) | **Blocked by data + research** | Sources not acquired; underlying construct ("low analyst coverage amplifies effects") never formally specified as a testable hypothesis |
| Portfolio construction / risk / execution layers | **Blocked by architecture (by design)** | Explicitly gated behind ≥2 validated independent factors, a deliberate platform guardrail, not an oversight |
| LIM local-model cutover | **Blocked by owner decision** | Nine-phase gated roadmap, design-only, no phase yet approved |

No ranking by expected return is given, per instruction — the map above
groups strictly by blocker type.

---

## 5. Competitive Position

*Assessed as if a professional quantitative hedge fund reviewed the
platform today.*

**Strongest capabilities, with evidence**:
- **Placebo-first, pre-registered discipline** applied without exception
  across all 16 hypotheses — a real institutional practice, not a
  cosmetic one, since it is what actually killed H-005 (p=1.00, worse
  than every one of 100 random shuffles) and correctly withheld
  confidence from H-009's near-miss.
- **Forensic decomposition of its own confirmed factor** (H-013/014/015)
  — few backtesting operations at any scale subject a *validated* result
  to adversarial double-sort testing against its own most likely
  confounds. This is genuinely rare and would read as a mark of
  seriousness to any reviewer.
- **The H-009→H-010 self-correction** — catching a near-significant
  result and correctly diagnosing it as a calendar-alignment artifact,
  rather than either accepting it or p-hacking a rerun.
- **Negative-result preservation**: 14 of 16 hypotheses are rejected and
  none has been deleted, reworded, or quietly dropped — the registry's
  `frozen` state-machine discipline is a real safeguard against exactly
  the kind of survivorship bias that plagues most informal backtesting.
- **Economic Capacity Validation** (introduced for H-016) — explicitly
  asking "at what AUM does this signal stop being deployable" is a
  fund-relevant question most academic-style backtests never ask.
- **A working self-audit habit**: the Wave 2 institutional audit's own
  "hybrid, uneven" self-assessment, and this document's own Academic
  Asset Pricing Researcher critique below, show the platform is capable
  of identifying its own overclaims rather than needing an external
  reviewer to catch them first.

**Weakest capabilities, with evidence**:
- **One confirmed factor, and it is not independently deployable.**
  H-011's own capacity report shows its return concentrated in illiquid,
  low-float names (LASACO, MULTIVERSE, NCR) — real, but small-AUM by
  construction. A fund reviewer would ask directly what dollar capacity
  this actually represents, and the honest answer, per the platform's
  own H-011 capacity finding, is "not much."
- **Single market, ~10-14 years of history, ~100-name investable
  universe.** This is simply small by any institutional standard, and
  no roadmap item changes that fact — it changes what can be tested
  within it.
- **No survivorship-bias audit has ever been run on the IRU's own
  construction** — flagged as an open, unverified risk in the Wave 2
  audit and still unresolved. This is normally one of the first checks
  an institutional shop performs, not a later-wave nicety.
- **No frontier-market econometric adaptation exists** despite frontier
  data and explicitly acknowledged frontier confounds (§3) — a fund
  reviewer versed in emerging/frontier-market quant research would
  notice this gap immediately.
- **Fundamental data coverage is close to nonexistent** — 9% of the
  IRU has any financial-statement fact at all, meaning Value, Quality,
  Growth, Profitability, Investment, and Financial Strength — six of
  the most standard factor families in all of equity research — have
  never been tested even once.
- **Zero portfolio construction, risk, or execution capability**,
  though this is a deliberate, disclosed architectural gate rather than
  an oversight — still, it means the platform today cannot produce
  anything a PM could actually allocate to.

**What would impress a hedge fund reviewer**: the pre-registration
discipline, the H-013/014/015 forensic work, and the fact that the
platform's own documentation already contains an honest "we haven't
adapted our statistics for frontier microstructure yet" admission
(Wave 2 audit) before any external reviewer had to point it out.

**What they would immediately challenge**: the capacity/deployability
of the one confirmed factor; the absence of a survivorship-bias check;
why six of sixteen hypotheses went to one family (momentum) before the
cost-drag lesson generalized; and why the platform calls itself
frontier-market research while running purely developed-market
statistics.

**What they would build next**: exactly what §4's "immediately
testable" and "blocked by research" rows already identify — the
survivorship audit and the non-synchronous-trading correction, both
cheap and foundational, before committing further capital-intensive
effort (FSI expansion, new data acquisition) to a research program
whose statistical foundation hasn't been frontier-adapted yet.

---

## 6. Five-Year Research Roadmap

```
Wave 5 (near-term, ~2-3 months)
├── H-017 pre-registration + test (Dividend payer-status) — ready today
├── H-002 data-availability re-check (5-minute lookup, not new research)
├── PEAD membership-only design (H-006 successor) — scoping + pre-registration
├── Survivorship-bias audit on IRU construction — methodology, no new data
├── Non-synchronous-trading econometric correction — DESIGN + validation
│   (this is the platform's sharpest self-identified gap; see §3 and
│   the Frontier Market Specialist critique in §7)
└── FSI depth-first pilot (per Owner Decision Package): timed human
    trial → ticker-attribution fix → tabular-format hand-verification
    pilot → pbt/eps schema addition
        │
        ▼
Wave 6 (mid-term, ~6-12 months) — GATED on Wave 5 outputs
├── IF FSI pilot succeeds (≥15-25 tickers, confirmed 3-statement depth):
│   Value / Quality / Financial Strength — first-ever fundamentals-based
│   factor tests on this platform
├── IF free-float data (NGX X-Compliance) is acquired:
│   Size retest with float-adjusted cap — resolves H-011's own disclosed
│   construct-validity gap
├── Composite factor construction — ONLY IF a second, genuinely
│   independent factor confirms (architecturally gated; not guaranteed
│   by this roadmap)
├── Regime-conditioning generalized beyond low-vol, informed by the
│   Wave-5 thin-trading correction
└── FALLBACK, if FSI pilot / free-float acquisition remain unapproved
    past a 3-month checkpoint: proceed with the Size-registry
    relabeling (§1.2, §7) and deepen the thin-trading correction
    instead of stalling
        │
        ▼
Wave 7 (longer-term, 12+ months) — GATED on Wave 6 producing real
fundamentals coverage AND the Wave-5 econometric correction being live
├── Genuinely frontier-native factor exploration: NEITI revenue-
│   integrity divergence, NGX X-Compliance governance/free-float-
│   deficiency signal, FMDQ NAFEX FX-regime conditioning — run through
│   the NOW frontier-adapted statistical pipeline, not the DM-standard
│   one used through Wave 6
├── Media-attention / analyst-neglect factor family (GDELT, Google
│   Trends) as a genuinely frontier-specific "information diffusion"
│   construct — not a DM replication
├── Portfolio construction / risk engine activation — hard-gated on
│   ≥2 validated independent factors, per existing architecture
└── LIM local-model shadow-mode A/B evaluation — per its own
    nine-phase, owner-gated roadmap, independent of the above
```

**Explicit dependency logic**: Wave 6's fundamentals work depends on
Wave 5's FSI pilot outcome, not on optimism about it — if the pilot is
negative or ambiguous, Wave 6 defaults to methodology-deepening work
instead of stalling. Wave 7's frontier-native data work is deliberately
sequenced *after*, not alongside, the thin-trading econometric
correction — running novel frontier data through uncorrected
developed-market statistics would risk producing a null result
indistinguishable from every prior rejection, wasting the platform's
first genuinely frontier-native research opportunity on a
still-unadapted statistical foundation.

---

## 7. Owner Decision

**If I were the Research Director of this project today, I would invest
the next 12 months in two sequential priorities, not a portfolio of
parallel bets:**

**Months 1-3: close the platform's own disclosed methodological debt.**
The survivorship-bias audit and the non-synchronous-trading correction
are both cheap, use no new data, and directly address the two gaps this
platform's own Wave 2 audit already identified as its sharpest
weaknesses. H-017 and the H-002 re-check are free closures that should
happen in parallel, not because they are high-value but because they
are zero-cost and currently just sitting open. **I would not invest
further in momentum-family variants or low-volatility variants** — six
and two tests respectively, both robustly and (for low-vol) wrong-signedly
eliminated; any further variant would be spending research cycles
against a well-established negative prior.

**Months 4-12: FSI depth, conditional on the Wave-5 pilot.** Eleven of
sixteen named factor families share exactly one blocker. If the
depth-first pilot the FSI Owner Decision Package already recommends
succeeds even partially, testing Value/Quality/Financial Strength for
the first time is the single highest-leverage investment available on
the entire roadmap — nothing else unlocks this many blocked questions
at once. If the pilot fails or stalls on an owner decision, the
fallback (methodology-deepening, Size-registry relabeling) is real
work, not idle waiting.

**I would explicitly not chase the frontier-native data sources (NEITI,
NAFEX, X-Compliance, GDELT) yet**, despite their genuine appeal as this
platform's most distinctively frontier-market opportunity. They are
appealing *because* they're unexploited by anyone, but pursuing them
before the statistical foundation is frontier-adapted (§3) risks
wasting a first-mover data advantage on a still-developed-market
statistical pipeline that would produce an uninterpretable result. They
belong in Wave 7, not Wave 5 or 6, and this is the clearest place this
recommendation departs from what might look like the "exciting" choice.

---

## Institutional Adversarial Review

*Five reviewers, each required to find a real weakness in this roadmap
and try to invalidate it; each answered directly, not deflected.*

### Quant Research Director

**Criticism**: "Wave 6's gate on 'FSI pilot success' is soft. What
counts as success — all 15-25 tickers converting cleanly, or some
smaller number? You have no explicit go/no-go threshold, which means
this roadmap could drift into a half-successful pilot being read as
justification for full commitment, exactly the kind of scope creep the
FSI audit series spent four documents trying to prevent."

**Response**: Correct, and this should be tightened rather than left
implicit. The threshold is already stated precisely in the FSI Owner
Decision Package's own milestone definition (§2 of that document): a
**~15-25 ticker set with confirmed, hand-verified three-statement
depth** — not keyword-detected, not partial. Wave 6 should treat
anything materially short of that range (say, under 10 tickers
converting) as a negative pilot result triggering the stated fallback,
not as a smaller-but-still-justified commitment. This threshold is
added here explicitly so it cannot be softened later.

### Academic Asset Pricing Researcher

**Criticism**: "You call H-011 'the platform's first confirmed factor,'
but your own §1.2 admits H-013/014/015 show it's concentrated in liquid,
low-volatility small caps and ambiguous with respect to momentum. By
any real academic standard, what you have is not a validated 'Size
factor' — it's an unlabeled composite effect that happens to load on
three characteristics at once. Continuing to call this 'Size — confirmed'
in the factor registry overstates what has actually been shown, and any
future reader (including a future Composite Factors attempt in Wave 6)
could be misled into treating it as an independent factor when it
demonstrably is not."

**Response**: This is accepted without qualification — it is the single
most important correction in this entire review. The registry's current
label is a defensible shorthand but not an accurate one. **The correct
description, going forward, is: "a small-cap effect concentrated in
liquid, low-volatility names, with an unresolved (partially explained)
relationship to momentum" — not "Size factor" unqualified.** This has
two concrete consequences for the roadmap: (1) `docs/FACTOR_REGISTRY.md`'s
own H-011 entry should be revised to this more precise language — a
documentation correction, not new research, and explicitly not
prohibited by this task's no-implementation scope; (2) Wave 6's
Composite Factor gate ("≥2 validated independent factors") is now
understood to require the SECOND factor to be tested for independence
from Liquidity/Volatility as rigorously as H-011 itself was — the same
forensic standard, not a lighter one, applies to whatever confirms next.

### Frontier Market Specialist

**Criticism**: "Your Wave 7 'frontier-native' ideas — NEITI, NAFEX,
X-Compliance, GDELT — are all novel DATA. But nothing in this roadmap
actually changes the STATISTICAL pipeline those data sources would run
through. You've correctly identified, via your own Wave 2 audit, that
the platform has zero frontier-specific econometric adjustment — but in
this roadmap that fix is a single bullet buried in Wave 5, not a named,
verified, gating deliverable. If Wave 7 runs NEITI data through the same
unmodified Sharpe/HAC/placebo pipeline used for H-001 through H-016, you
haven't built a frontier-market research platform — you've just found
more frontier data to feed a developed-market pipeline, which is exactly
the failure mode this whole audit was supposed to catch."

**Response**: Accepted, and the roadmap is revised to reflect it
directly rather than defending the original framing. **The
non-synchronous-trading / thin-trading econometric correction is
elevated from a Wave-5 side item to an explicit, named, verified
prerequisite that must be complete and validated before any Wave-7
frontier-native hypothesis (NEITI, NAFEX, X-Compliance) is
pre-registered** — not merely attempted in parallel. The risk the
reviewer names is real and specific: a frontier-native dataset run
through uncorrected developed-market statistics could produce a false
negative (a real effect obscured by uncorrected microstructure noise)
that would look identical to every one of the fourteen honest
rejections already in the registry, and the platform would have no way
to distinguish "genuinely null" from "obscured by the wrong
statistical tool" without this correction in place first. This is now
stated as a hard sequencing rule in §6, not a preference.

### Portfolio Manager

**Criticism**: "You have one confirmed factor — which your own Academic
reviewer just admitted isn't cleanly independent of anything — it's
small-AUM, illiquid-name-driven, and every wave in this roadmap defers
portfolio construction further out. At what point does this platform
actually produce something I can allocate capital to? Twelve months
from now, following exactly this roadmap, will I still have zero
investable strategies?"

**Response**: The honest answer is **yes, most likely** — twelve months
from now, following this roadmap, the platform will likely still have
zero deployable strategies, unless Wave 6 produces a second, genuinely
independent confirmed factor, which is not guaranteed by anything in
this document. This should be stated plainly rather than softened: the
architectural gate (≥2 validated independent factors before portfolio
construction activates) is a deliberate risk-management guardrail, and
this roadmap does not recommend relaxing it — doing so would mean
deploying capital against H-011 alone, a factor whose own capacity
report shows concentration in illiquid, low-float names, which the
platform's own H-011 documentation already treats as a reason for
caution, not confidence. **The tradeoff is real and is disclosed here
explicitly**: this roadmap prioritizes not deploying a fragile,
single-factor, capacity-constrained strategy over hitting a
twelve-month capital-deployment target. A PM who needs an allocatable
strategy on a fixed timeline should treat that as a real constraint on
this roadmap, not an assumption this document is hiding.

### Data Engineering Lead

**Criticism**: "Wave 6 gates on 'free-float data acquisition' and 'FSI
pilot success' — both of which require owner decisions that have
already been sitting unresolved for weeks (the OCR/vendor decision
since 2026-07-16, X-Compliance acquisition never actioned at all). This
roadmap implicitly assumes those stalled decisions get made, without
addressing why they've stalled or what happens if they don't. A
roadmap that silently depends on someone else's unresolved decision
isn't really a roadmap — it's a wish."

**Response**: Fair, and already partially addressed in §6's fallback
clause, but it deserves to be stated as its own explicit risk rather
than a footnote. **Wave 6 now carries a named contingency**: if the FSI
depth pilot or the free-float acquisition decision remains unapproved
past a 3-month checkpoint from the start of Wave 5, Wave 6's default
content becomes the Size-registry relabeling (per the Academic
reviewer's critique) and continued deepening of the thin-trading
econometric correction (per the Frontier Market Specialist's critique)
— both of which require no owner decision beyond what this document
itself recommends. This does not solve the underlying problem (owner
decisions stalling), but it ensures the roadmap has real, useful,
non-idle content regardless of whether those decisions land in time.

---

## Final Recommendation, After Review

The five critiques converge on one adjustment worth stating plainly:
**this roadmap's near-term (Wave 5) methodological work — the
survivorship audit, the thin-trading correction, and the Size-registry
relabeling — is more load-bearing than it first appears.** It is not
housekeeping ahead of the "real" research; it is a prerequisite for
being able to trust the answer to *any* subsequent question, including
whether the FSI pilot's eventual results (Wave 6) or any frontier-native
finding (Wave 7) are genuine. The recommendation in §7 stands, with the
five revisions above incorporated: an explicit FSI-pilot go/no-go
threshold, a corrected (not overclaiming) description of what H-011
actually showed, a hard sequencing rule putting the thin-trading
correction before any frontier-native hypothesis, an honestly disclosed
"likely still zero deployable strategies in 12 months" risk, and a
named fallback for Wave 6 if owner decisions continue to stall.
