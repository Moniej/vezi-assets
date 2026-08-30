# Investment Committee Review — NGX Rotation as an Investment Firm — 2026-08-12

Evaluated as an investment-management business, not a technology project.
Grounded in this project's own verified records (production database,
regression suites, live experiments through 2026-08-12). Where a
capability the rubric asks about simply does not exist yet, that is
stated plainly as **NOT YET BUILT**, not inferred or estimated — the most
important finding of this review is how much of the "firm" layer (as
opposed to the "research" layer) falls into that category.

---

## 1. Investment Firm Architecture

### Layer 1 — Investment Intelligence Infrastructure

**Built and verified**: market data (323 securities, 2014–2026 daily
OHLCV), corporate actions (185 real dividend rows), documents/filings
(11,589 documents, 210 tickers), extracted financial facts (495,
267 production conclusions across 10 tickers), point-in-time integrity
(capture-vintage gating, independently verified against real look-ahead
leakage), evidence/provenance tracking (every fact traces to a quoted
source), automated ingestion with idempotency and concurrency protection.

**Not built / thin**: macro data (limited to MPC-decision events, no
broad macro time-series), management/ownership information (structurally
zero coverage per the platform's own prior self-assessment), alternative
datasets (none), systematic data-quality monitoring beyond what this
session's own audits manually found (a numeric-transcription bug, a
matching-logic bug — found by deliberate investigation, not by an
automated quality-monitoring system that watches for these on its own).

**Committee determination**: this creates a **sophisticated research
environment**, not yet a demonstrated **informational advantage**. The
distinction matters — good data plumbing lets you test ideas cheaply; it
does not, by itself, mean the ideas are right. No evidence in this
project shows the data itself (as opposed to what's done with it) is
proprietary or unavailable to a competitor with comparable engineering
effort and free-tier LLM access.

### Layer 2 — Research & Investment Process

The honest process map, traced from this project's own artifacts:

```
Data → Extraction → Fact → Hypothesis → Backtest → Validation → REJECTED (usually)
```

This is a real, repeatable, disciplined research loop — **but it stops
before "Position."** There is no evidence anywhere in this project of:
position sizing rules, entry/exit criteria applied to real capital, a
rebalancing calendar, or a portfolio that exists outside a backtest
script. The rubric's desired chain — *Information → Signal → Thesis →
Position → Risk Management → Outcome → Learning* — is genuinely
implemented only through "Thesis" (a hypothesis, pre-registered and
tested). Nothing downstream of that has been built.

**This is not "Information → Opinion → Trade" either** — there is no
opinion-driven trading happening. It is closer to *Information →
Hypothesis → Rejection*, repeated 19+25 times, which is methodologically
sound but has not yet produced anything to size, enter, or exit.

### Layer 3 — Alpha Engine (most important layer)

Applying the required question set to the one confirmed result:

**H-011 (Size — long the smallest-cap quintile)**:
- Economic rationale: illiquidity/capacity-friction compensation — investors
  demand a premium for holding hard-to-trade names. Coherent, textbook.
- Why does it persist / why hasn't arbitrage closed it: precisely because
  it's hard to trade at scale — the same friction that creates the premium
  prevents easy arbitrage. Internally consistent.
- Backtestable without look-ahead: yes — built on the platform's own
  point-in-time universe construction (IRU), verified not to depend on
  `securities.delisting_date` (100% NULL) because it reconstructs
  membership from the trailing price tape at each historical date.
- Survives transaction costs: yes, as tested.
- Survives liquidity constraints: **this is where it fails as an
  investable strategy** — median tradeable leg is **~₦694,000**. That is
  not a small-fund constraint; it is below what almost any formal
  investment vehicle could deploy meaningfully.
- Scalable: **no.**

**Every other tested candidate** (momentum at three horizons, low-vol,
liquidity, dividend-payer-status, oil-lag, MPC-window timing,
catalyst-driven rotation, three Size-interaction decompositions,
insider-dealing disclosure lag) was rejected, reversed, or remains
negative-in-testing (H-019). The insider-dealing case is worth naming
specifically: it survived four rounds of adversarial testing before a
data-completeness fix revealed the earlier positive result was carried by
a single micro-cap outlier — a textbook illustration of exactly the "does
the backtest looking profitable actually mean alpha" trap this section
warns against, caught by the platform's own discipline, not avoided by luck.

**Committee determination**: the firm has one validated, uncapturable
edge, and a demonstrated, credible process for rejecting false ones. It
has **not yet discovered a deployable edge**, and the base rate this
process has itself revealed (1 confirmed of ~44 tested, and that one
undeployable) should set expectations for what's still untested
(fundamentals-based factors — see §3/13), not optimism.

### Layer 4 — Portfolio Management

**NOT YET BUILT.** No portfolio exists. No capital allocation across
multiple positions has been modeled or executed. No diversification,
correlation, sector-exposure, or factor-exposure management exists
outside of individual hypothesis backtests (each of which tests one
factor in isolation, not a combined book). The firm currently cannot
distinguish "finding a good investment" from "building a superior
portfolio" because it has never had to — there has never been more than
one candidate position type active at a time, and that one (Size) is
capacity-dead.

### Layer 5 — Risk Management

**NOT YET BUILT as a live capability.** What exists: capacity/cost
modeling *inside individual backtests* (a real, rigorous practice — every
tested hypothesis was checked against realistic transaction costs and
ADTV-based capacity limits before being taken seriously). What does not
exist: position limits, sector limits, a drawdown policy, a tail-risk
framework, model-risk governance, or any mechanism for surviving being
wrong, because nothing has been deployed that could be wrong yet. This is
the single most important gap for an "investment firm" evaluation
specifically — a firm is defined as much by how it survives losses as by
how it finds gains, and this dimension is currently empty.

### Layer 6 — Performance Measurement

**No live performance exists.** No CAGR, Sharpe, Sortino, drawdown,
Calmar, win rate, or information ratio can be reported because no capital
has been deployed against any strategy. Backtested statistics exist for
individual rejected/confirmed hypotheses (Sharpe, placebo p-values, HAC
significance), but these are research-validation statistics, not track
record. **Do not conflate the two** — this review will not report a
"firm performance" number because none exists.

### Layer 7 — Research-to-Capital Pipeline

This is the firm's **strongest institutional capability**, genuinely
built and evidenced. Every hypothesis's rejection is recorded with a
specific "why" (H-009: sample size, not signal; H-008: robust wrong-
direction significance; the insider-dealing reversal: outlier-driven, not
signal-driven) and feeds the next round — H-002/H-003 explicitly
generated follow-on hypotheses per the platform's own stated precedent.
Mistakes become recorded, attributed, reusable findings, not silent
dead ends. This is real organizational learning infrastructure, even
though the pipeline has not yet reached "Portfolio Implementation" or
"Live Performance" — it is proven only through "Attribution" on backtests,
not on real outcomes.

### Layer 8 — Technology as Competitive Advantage

Applying the required test — *does this improve the firm's ability to
find, validate, execute, or scale alpha* — to what's actually been built
this session:

- Capture-vintage PIT gating: **yes**, directly — it closes a real
  look-ahead leak that would have silently corrupted any historical
  research replay.
- Idempotent writes, concurrency protection, backup/restore: **indirectly
  yes** — these prevent a validated result from later being invalidated
  by a data-integrity failure, but they don't themselves find or validate
  alpha.
- The numeric-consistency check and period-extraction fix: **yes,
  directly** — a 10× numeric error would have silently corrupted a real
  hypothesis test had it gone undetected.
- Monitoring/alerting, research workspace, document evidence grounding:
  **supports validation and research speed**, not yet shown to have
  changed any investment outcome, because there is no investment outcome
  yet.

No component reviewed this session should be classified as unnecessary
complexity by this test — but the test itself cannot yet be fully applied,
because "improve the firm's ability to execute or scale alpha" has no
alpha to execute or scale against yet.

### Layer 9 — Institutional Scalability

**Cannot evaluate ₦100M/₦1B/₦10B+ readiness — the firm cannot yet
respons­ibly deploy ₦10M.** The one confirmed edge is capacity-constrained
at roughly ₦694,000 per leg. There is no governance structure, no
compliance function, no investor reporting, no fund administration, and
no track record to raise external capital against. Key-person risk is
total — every capability described in this review exists as code and
research artifacts a single founder built and understands; no evidence of
team, succession, or institutional process independent of that one
person.

### Layer 10 — Competitive Moat

**Technology moat: moderate.** The PIT/evidence/reproducibility
infrastructure and the ~44-hypothesis research history are real and would
take a competitor real time to replicate (not because the components are
individually hard — they use commodity LLMs and public data — but because
replicating the *history of what's already been ruled out* requires
re-running the same work).

**Investment moat: effectively zero**, and the rubric is explicit this is
the one that matters more. There is no proprietary edge currently being
protected — the one confirmed factor is undeployable, and undeployable
edges don't need protecting from competitors because competitors
couldn't deploy them either. A moat protects a return stream; there is no
return stream yet.

### Layer 11 — Economics of the Firm

**Entirely hypothetical — no figures exist for**: management fees,
performance fees, AUM, personnel cost, compliance cost, or fund
administration, because there are no external investors, no fund
structure, and no AUM. The only real, measured economics in this project
are research-production costs: $0 direct API spend (free tier), bound by
a measured 20-requests/day throughput ceiling. This is a research-cost
model, not a fund-economics model, and should not be presented as one.

---

## 12. Five Seats

**Seat 1 — CIO.** *Would I trust this process with serious capital?*
Not yet, and not close. The research discipline is real and would earn
trust over time, but there is currently nothing to trust capital *to* —
no portfolio, no risk framework, no deployable edge. The one confirmed
factor is a research result, not an investable strategy. **Verdict: not
investable today; the process, if it eventually produces a capacity-
viable factor, would be worth trusting incrementally, starting small.**

**Seat 2 — Quantitative Research Director.** *Is this actually an edge,
or are we fooling ourselves?* On the evidence: mostly not fooling
ourselves — the insider-dealing reversal and the disciplined rejection
rate (15 of 19) are exactly what NOT fooling yourself looks like in
practice. But the one "yes" (Size) fails the scalability test explicitly
named in this rubric's own question list, and no fundamentals-based
factor has been tested yet at all (only just became possible this
session, coverage still incomplete). **Verdict: process integrity is
high; edge inventory is currently one item, and that item doesn't
survive institutional deployment.**

**Seat 3 — Risk Officer.** *What can permanently damage the firm?*
Right now: almost nothing, because almost nothing is deployed — the
firm's risk is currently "wasted founder time," not "capital
impairment." That will change the moment any capital is deployed against
an undercapacity-tested strategy without position/drawdown limits, which
don't exist yet. **Verdict: risk management must be built BEFORE any
capital deployment, not after — currently there is no mechanism to
survive being wrong because nothing has been risked yet, but that
protection doesn't extend automatically to the moment it's needed.**

**Seat 4 — Portfolio Manager.** *Can this strategy actually be traded
with real money?* The only confirmed strategy: at ~₦694k capacity, no —
not in any way that matters to an institutional operation. Every other
tested strategy: rejected before this question was even reachable.
**Verdict: nothing in the current inventory is tradeable at institutional
size; this seat has nothing to execute yet.**

**Seat 5 — Managing Partner / Capital Allocator.** *Should we continue
allocating capital, talent, technology, and founder attention to this
firm?* The infrastructure and research-discipline layers justify
continued, bounded investment — they're cheap (near-zero dollar cost),
they compound (each hypothesis adds to reusable knowledge), and the
process just caught two real bugs before they could corrupt a future
result. But "firm" implies portfolio, risk, and economics layers that
are currently empty, and building those out prematurely (before a
capacity-viable edge exists) would be building operational overhead
around nothing. **Verdict: continue funding the research/infrastructure
layer at current (low) intensity; do NOT yet fund portfolio/risk/
compliance/fundraising infrastructure — there is nothing for it to
manage.**

---

## 13. Investment Committee Decision Framework

**A. Investment Thesis** — Why could this become a successful investment
firm? The founder has built a genuinely disciplined, low-cost, PIT-safe
research process that has already correctly identified and rejected 15 of
19 tested ideas, caught its own data-integrity bugs before they could
corrupt a result, and is about to test an entirely new factor class
(fundamentals) that the prior ~44 tests never touched because the data
didn't exist yet. If a fundamentals-based factor validates with real
capacity (unlike Size), the firm would have both a real edge and the
process discipline to size and risk-manage it properly once that
layer is built.

**B. Anti-Thesis** — Why could this fail despite the infrastructure?
Nigerian equities may simply not contain a capacity-viable systematic
edge at the scale this operation could ever test — the one confirmed
factor's own failure mode (real premium, unarbitrageable specifically
*because* it's uncapturable at scale) may be the market's general
character, not a solvable data problem. Sophisticated infrastructure
does not change a market's underlying liquidity. The firm could spend
years building an increasingly elegant research apparatus around a
capital base too thin to ever support the institutional layers (Layers
4–6, 9, 11) this review found completely empty.

**C. Current Alpha Score: 15/100** — one confirmed factor exists (real
credit for genuine, rigorous validation), but it is capacity-dead;
everything else tested is rejected or negative; the untested fundamentals
class is a real open question, not yet evidence either way.

**D. Investment Process Score: 30/100** — the research half (hypothesis
→ backtest → validation → learning) is genuinely strong; the entire
execution half (position → risk management → outcome) does not exist.

**E. Risk Management Score: 10/100** — real capacity/cost discipline
inside backtests; zero live risk-management capability (limits,
drawdown policy, tail-risk framework).

**F. Scalability Score: 10/100** — the one proven edge caps at ~₦694k;
no evidence yet either way for fundamentals-based factors; research-cost
scalability (cheap, quota-bound) is not investment scalability and
should not be conflated with it.

**G. Institutional Readiness Score: 5/100** — no governance, compliance,
reporting, fund structure, or external-capital-readiness of any kind
exists; total key-person dependency.

**H. Moat Score: 25/100** — real technology/research-history moat;
effectively zero investment moat, which the rubric itself weights higher.

**I. Overall Firm Score: 15/100** — reflects that this is, honestly,
still a research operation with unusually strong engineering and research
discipline, not yet an investment firm by this rubric's own definitions
in Layers 4–6, 9, and 11.

---

## 14. Capital Allocation Decision

**🟡 INVEST / VALIDATE — with an explicit, narrow scope.**

Not INVEST/SCALE: there is no durable, capacity-viable edge to scale.
Not STOP: the process has produced real, credible negative *and*
positive results cheaply, and one genuinely new, untested factor class is
about to become testable for the first time.
Not (yet) HOLD/RESTRUCTURE at the research layer specifically — though
see the explicit split below, because at the *firm* layer (Layers 4–6, 9,
11) the honest classification is closer to "does not exist to
restructure" than "weak thesis to redirect."

**The exact experiments required, in order** (matches this project's own
already-scoped next steps): (1) complete the interrupted 5-document
extraction-quality pilot once the daily API quota resets; (2) if quality
holds, extend fundamental-statement coverage to a defensible ~50-ticker/
5-year research universe; (3) run ONE pre-registered fundamentals-based
hypothesis (e.g. Piotroski or Profitability) through the exact same
validation gauntlet that correctly killed 15 of 19 prior candidates — no
shortcuts, no relaxed bar because it's a "new" data type.

**Do not build Layers 4, 5, 6, 9, or 11** (portfolio construction, live
risk management, performance reporting, institutional scaling,
fund economics) **until step 3 produces a capacity-viable confirmed
factor.** Building them earlier is building firm infrastructure around a
firm that doesn't have an edge to operate yet.

---

## 15. Mandatory Final Question

**If this firm did not exist today, and we were shown everything we now
know, would we invest our own capital to build it from scratch?**

Not to build the *firm* as currently scoped — no, not at the "firm"
layer; there is no edge to found a firm on yet, and funding governance/
compliance/fundraising infrastructure today would be pure overhead.
**Yes, to fund the next research cycle specifically** — it is cheap
(near-zero dollar cost, bounded calendar time), has a clear, falsifiable
next test, and the team (one founder) has demonstrated the discipline to
kill its own bad ideas rather than nurse them. That is a fundable
research bet, not yet a fundable firm.

**What single capability would create the largest increase in the
probability this becomes a billion-naira-plus operation?**
A **capacity-viable confirmed factor** — full stop. Not more
infrastructure, not more data coverage, not portfolio-management tooling.
Every institutional layer this review scored near zero (Portfolio,
Risk, Scalability, Institutional Readiness, Moat) is downstream of having
something real to manage — none of them can be meaningfully built in a
vacuum, and all of them become tractable the moment one exists. This is
the single highest-leverage unknown in the entire operation.

**What should the founder stop doing immediately?**
Stop building any firm-level infrastructure (compliance frameworks,
investor reporting, portfolio-management tooling, fundraising
preparation) — there is nothing yet for any of it to manage, and every
hour spent there is an hour not spent resolving the one real open
question.

**What should the founder start doing immediately?**
Start explicitly separating "research operation" from "investment firm"
in both language and resource allocation — stop describing pre-portfolio,
pre-track-record work in firm terms (AUM, fees, institutional scale) that
imply a maturity stage not yet reached, since that framing risks
distorting the next decisions (as this very pivot in framing already
shows it can).

**What should receive the overwhelming majority of capital and attention
for the next 90 days?**
The three-step experiment above (§14) — completing extraction validation,
reaching real fundamentals coverage, and running one properly-gated
fundamentals hypothesis. Nothing else in this review's 15 sections should
receive material founder attention until that sequence resolves, because
nothing else can be honestly evaluated until it does.

---

*Prepared from this project's own verified records. No agent, hypothesis,
portfolio, or infrastructure component was modified in the preparation of
this review.*
