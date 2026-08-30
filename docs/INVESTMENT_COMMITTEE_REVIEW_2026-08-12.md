# Investment Committee Review — NGX Rotation Investment OS — 2026-08-12

Five-seat committee evaluation of continued founder capital allocation.
Grounded entirely in verified facts from this project's own production
database, regression suites, and live experiments run through 2026-08-12
(reliability audit `a877d62`/`69bb4a5`, Alpha Opportunity Audit, Financial
Coverage Expansion Audit, Financial Extraction Pilot, Financial Extraction
Quality Fix Report). No number below is invented; where evidence is
missing, that is stated explicitly rather than estimated.

---

## 1. VERDICT

**HOLD.** Conviction: **MEDIUM**.

Continue with a tightly bounded validation budget — complete the two
already-scoped, already-cheap next steps (finish the interrupted 5-document
extraction pilot; decide on production application of two tested-clean,
zero-risk migrations) before any expansion decision. No major new capital
commitment (a 44-ticker extraction campaign, a new alpha research track,
new infrastructure) until those resolve.

**Dissenting seats**: Quant leans toward REDIRECT — after 19 formal
hypotheses and ~25 discovery tracks, zero deployable alpha exists, and the
Quant's own mandate is to weight that fact heavily regardless of
infrastructure quality. Value/Moat leans toward FUND on the Investment OS
layer specifically (not the Alpha Engine) — argues the accumulated,
PIT-safe, reproducible research history is a compounding asset whose value
doesn't depend on Alpha Engine success. The committee's HOLD is the
believability-weighted synthesis of these two positions, not a vote — see
§5 and §10 for exactly what would move it either direction.

---

## 2. WHAT HAS ACTUALLY BEEN BUILT

### Production (operational, verified against the live database)

- Market data: 323 securities, 678,800 equity-price rows (2014–2026), index
  levels 2012–2026.
- Document archive: 11,589 documents, 210 tickers with at least one.
- `extracted_facts`: **495** rows. `financial_reasoning_conclusions`:
  **267** rows, covering **10 tickers** (AFRIPRUD, BUAFOODS, CAP, DANGCEM,
  MTNN, NASCON, NESTLE, OANDO, UBN, UCAP).
- Reliability infrastructure: automated backup/restore (verified via a
  real restore test matching row counts), idempotent document ingestion
  (`UNIQUE(local_path)`, reproduced-then-fixed), idempotent financial
  writes, WAL + busy-timeout, capture-vintage PIT gating on the
  document/entity/financial-reasoning path (a real, live-data-confirmed
  look-ahead bug found and closed — 98.8% of documents had a capture lag
  averaging ~4.6 years past their nominal filing date). Independently
  re-verified in a second pass using genuinely concurrent OS processes for
  the two concurrency claims, not simulations.
- Alpha Engine boundary: traced via `git diff` and import-graph analysis,
  not asserted — every change touching shared modules (`db.py`,
  `registry.py`) is a connection-level pragma or an additive column on a
  table Alpha never reads.

### Scratch/Test (proven to work, NOT in production)

- Point-in-time matching fix + period backfill, applied to a scratch
  copy: `financial_reasoning_conclusions` 267 → **403** (+136, 0
  duplicates). **Not applied to production** — awaiting explicit
  approval.
- `numeric_consistency_check` schema column: exists on scratch, **not**
  on production.
- 5-ticker/11-document extraction pilot (original): 10 of 11 documents
  processed before hitting the free-tier daily quota.
- Post-fix re-extraction: 1 of 5 planned documents completed live before
  quota exhausted again; the completed one (TRANSCORP FY2024) shows 6/6
  facts with correct period metadata and 6/6 passing numeric-consistency
  (including the exact figure that was previously wrong by 10×).

### Planned (specified, not yet executed)

- Complete the remaining 4 pilot documents once daily quota resets.
- Extend extraction to the 44-ticker "ready" backlog (11 tickers with ≥3
  substantive documents already identified as plausibly trend-viable; 4
  with 2; 23 with 1; 6 with zero substantive content on inspection).
- Reach a 50-ticker/5-year minimum viable research universe for
  statement-based factor testing.

### Hypothesized (thesis, not yet evidenced)

- That expanded financial-statement coverage will surface a validated,
  tradable factor (Value/Quality/Piotroski/Financial-Momentum/Cash-Flow
  families) — genuinely untested; every prior alpha-discovery track ran
  on price/liquidity/event data, never on the FSI ratio data, because
  that coverage didn't exist broadly enough until this session's fixes.
- That the accumulated Investment OS has standalone enterprise/licensing
  value independent of any Alpha Engine outcome — asserted by the
  Value/Moat seat below, not measured.

---

## 3. BULL CASE (maximum three)

**1. Seat: Value/Moat.**
**FACT**: The platform has run 19 formal hypotheses plus ~25 discovery
tracks through a consistent, pre-registered, placebo-tested,
capacity-adjusted validation gauntlet, with every result — confirmed,
rejected, or reversed — recorded with full provenance (fact/evidence IDs,
experiment IDs, ledger status).
**INFERENCE**: This body of negative-and-positive results is itself a
proprietary, hard-to-replicate asset — a competitor starting today would
need to re-run the same ~44 tests to reach the same state of knowledge
about what does and doesn't work on NGX.
**Mechanism**: research-history compounding — each future hypothesis
starts from this accumulated prior instead of from zero, lowering the
marginal cost of the *next* validated idea, whether or not any single
past idea worked.
**Economic value**: unquantified directly, but proxied by avoided
re-work — 19+25 ≈ 44 research cycles' worth of engineering/compute time
not needing to be repeated by any future team (internal or external)
working this dataset.
**Key assumption**: that NGX-specific research knowledge decays slowly
enough (regulatory regime, market structure) for this history to remain
relevant for several years, not months.

**2. Seat: Finance/Economics.**
**FACT**: Dollar cost of the entire financial-extraction pipeline to date
is $0 (free-tier Gemini API); the binding constraint is a measured
20-requests/day quota, not spend.
**INFERENCE**: The marginal cost of testing the next fundamental-factor
hypothesis is currently bounded by calendar time (~10–13 days of quota to
reach the 44-ticker backlog), not capital — a highly capital-efficient
position for information gain per ₦ spent, even though it is NOT
capital-efficient per unit of founder TIME.
**Mechanism**: real-options value — the platform can cheaply test whether
fundamentals contain exploitable signal (a class of factor never
previously testable here) before committing to a paid tier or larger
engineering investment.
**Economic value**: the option to discover a Value/Quality/Piotroski
factor costs, at current measured rates, roughly 10–13 calendar days of
waiting plus the engineering time already sunk (a fixed, mostly-sunk
cost) — cheap relative to the potential payoff of even one additional
confirmed factor.
**Key assumption**: that fundamentals contain information not already
captured by the price/liquidity/event data the 44 already-tested
hypotheses exhausted — genuinely unproven, this is the option being
bought, not a result in hand.

**3. Seat: Macro Allocator.**
**FACT**: The reliability work (backup/restore, idempotency, concurrency,
PIT gating) was independently re-verified using real concurrent OS
processes, not simulated — the infrastructure's core reliability claims
are unusually well-evidenced for a project at this stage.
**INFERENCE**: A research platform this well-instrumented (reproducible,
PIT-safe, idempotent, backed up) lowers the *execution risk* of every
future research cycle run on it, independent of whether any specific
cycle finds alpha.
**Mechanism**: infrastructure reliability reduces the probability that a
future promising result is later invalidated by a data-integrity bug
(exactly the class of error — the capture-vintage leak, the debt-to-equity
matching bug, the 10× numeric error — this session's own audits found and
fixed) — each fixed bug is one fewer false-positive or false-negative risk
in a *future* alpha test.
**Economic value**: unquantified, but the counterfactual is visible in
this project's own history — the debt-to-equity bug alone would have
silently zeroed out an entire factor family (Value/Financial-Strength) for
every future test until discovered.
**Key assumption**: that the fixes found so far represent the bulk of the
remaining integrity risk, not the first few of many — cannot be verified
without more usage.

---

## 4. BEAR CASE (ranked by probability × severity)

| # | Failure mode | Probability | Severity | Why |
|---|---|---|---|---|
| 1 | **No scalable alpha ever emerges** | **HIGH** | **HIGH** | FACT: 19/19 formal hypotheses are confirmed-but-capacity-dead (1), rejected (15), abandoned (1), or negative-in-testing (1). Zero are both confirmed and deployable. INFERENCE: NGX's own structure (thin liquidity, small float, ~150-name real universe) may make classical cross-sectional equity factors structurally uncapturable here, not merely undiscovered — a base-rate argument, not proof. |
| 2 | **Limited NGX market capacity caps any future win** | **HIGH** | **MEDIUM-HIGH** | FACT: the one confirmed factor (Size) has a ~₦694k median tradeable leg — below what almost any real fund could deploy meaningfully. INFERENCE: any *future* small-cap-adjacent factor likely inherits a similar capacity ceiling, since NGX's total addressable liquidity, not the model, is the constraint. |
| 3 | **Founder opportunity cost** | MEDIUM | HIGH | QUESTION: no explicit accounting of founder hours spent to date vs. alternative ventures exists in this project's own records — cannot be quantified from available evidence, must be estimated by the founder directly. Flagged as the single largest unquantified risk in this review. |
| 4 | **Financial-extraction throughput never scales cheaply** | MEDIUM | MEDIUM | FACT: 20 requests/day free tier measured directly; ~304-document backlog implies ~30 days sequential, or a paid tier (untested cost) to go faster. INFERENCE: even a working extraction pipeline may take a calendar quarter to reach broad coverage on the current tier. |
| 5 | **Data quality / extraction errors recur** | MEDIUM | MEDIUM-HIGH | FACT: one confirmed 10× numeric error and one confirmed structural matching bug (debt-to-equity) were found and fixed THIS SESSION, on a very small sample (11 documents). INFERENCE: at 191-ticker scale, the base rate for undiscovered defects of similar severity is unknown and could be materially higher than the 1-in-11-documents rate observed so far, which is itself too small a sample to trust as a real error rate. |
| 6 | **Survivorship bias in future universe construction** | MEDIUM | MEDIUM | FACT: `securities.delisting_date` is 100% NULL platform-wide; separately verified that the IRU machinery does NOT depend on this field and is PIT-correct by construction. INFERENCE: risk is present only for future code that bypasses the IRU and queries `securities` directly — a discipline risk, not a current data risk. |
| 7 | **Overfitting / data snooping across ~44 tests** | MEDIUM | MEDIUM | FACT: every hypothesis used placebo tests, HAC-robust significance, and multiple-testing-aware review per the platform's own stated gauntlet. INFERENCE: with ~44 independent tests run, some false-positive risk exists structurally even with correction — the ONE confirmed factor (Size) should itself be viewed with this in mind, not treated as certain. |
| 8 | **Infrastructure becomes an end in itself** | MEDIUM | MEDIUM | FACT: this session alone produced 4 audit/report documents and multiple rounds of fixes before a single new alpha hypothesis was tested. INFERENCE: real engineering discipline is visible (measure-before-build, scratch-before-production, no speculative infrastructure) — the risk is process, not evidence of current drift, but worth naming as the platform's own stated failure mode to guard against. |
| 9 | **Commodity replication** | LOW-MEDIUM | MEDIUM | INFERENCE: the extraction pipeline (LLM + structured facts + PIT gating) uses commodity components (Gemini free tier, standard SQL) — a well-resourced competitor could plausibly replicate the infrastructure layer in weeks. The accumulated *research history* (§3 bull case #1) is the harder-to-replicate part, not the code. |
| 10 | **LLM/API cost dependency at scale** | LOW | LOW-MEDIUM | FACT: currently $0 (free tier). QUESTION: no paid-tier cost has been measured; if free-tier throughput proves insufficient, real cost is currently unknown, not merely unfavorable. |
| 11 | **Excessive human review requirement** | LOW | LOW | FACT: the numeric-consistency check explicitly flags-for-review rather than auto-correcting, by design — review burden scales with flag rate, which on the one measured batch (11 documents) was 1 flag, i.e. ~9%. Too small a sample to project confidently. |

---

## 5. EACH SEAT'S VIEW

**Macro Allocator**: The infrastructure is real, well-verified option
value — the question is not whether to keep it (sunk, working, cheap to
maintain) but whether to fund its *next* expansion. Given zero proven
alpha and a real, quantified quota-bound throughput ceiling, the
highest-expected-value action is the cheap, already-scoped validation
step (§8), not a capital commitment to full-scale extraction. **View:
HOLD, tightly bounded.**

**Value/Moat**: The accumulated, provenance-tracked research history
(44 tested hypotheses/tracks) and the now-corrected financial-extraction
contract are durable, compounding assets independent of Alpha Engine
outcomes. A competitor with commodity LLMs and public data could
replicate the *code* but not the *history* without repeating the same
work. Continued modest investment in the Investment OS/FRE layers is
justified on infrastructure-option grounds alone. **View: lean FUND on
Investment OS/FRE specifically; HOLD on Alpha Engine.**

**Risk & Cycle Strategist**: The project's own discipline (scratch-first,
measure-before-scale, explicit kill lists, real concurrent-process
verification) is the strongest evidence against reckless continuation —
but that same discipline means the honest current state is "promising,
unproven, throughput-constrained." The single largest unhedged risk in
this review is unquantified founder opportunity cost (bear case #3) —
not resolvable from this project's own data. **View: HOLD, and treat the
opportunity-cost question as the actual gating question, not a footnote.**

**Quant** (veto authority on alpha claims): **THE EVIDENCE FOR ALPHA IS
CURRENTLY INSUFFICIENT.** 19 formal hypotheses, ~25 additional tracks, one
confirmed factor that is capacity-dead at ~₦694k. No claim of infrastructure
quality, financial-intelligence sophistication, or research-history value
changes this. Financial-statement coverage expansion is a *prerequisite*
to testing five more factor families, not evidence any of them will
validate — the platform's own revealed base rate (1 confirmed of ~44
tested) should set the prior for those five, not optimism about better
data. **View: no capital increase justified by alpha evidence; any
continued funding must be justified on infrastructure-option grounds
(Value/Moat's argument) or not at all.**

**Finance & Economics**: Engineering ROI on this session's work is
high — real bugs found and fixed at effectively zero marginal dollar
cost. Investment ROI is currently **zero and unmeasurable** — no capital
has been deployed against any validated signal. Potential
enterprise/software ROI (licensing the OS/FRE layer) is a **hypothesized**
category with no evidence gathered either way in this review. These three
ROI types must not be conflated when deciding the next allocation.
**View: fund the Investment ROI path only to the extent it cheaply
resolves uncertainty (§8); do not let Engineering ROI success imply
Investment ROI justification.**

---

## 6. CAPITAL ALLOCATION — next 100 units of founder time/capital

| Allocation | % | Why this beats the next-best alternative |
|---|--:|---|
| Financial extraction (finish pilot, decide on production migration) | **25** | Lowest-cost, highest-information-value action available right now — already-built, already-tested-on-scratch, blocked only on quota time, not capital. Directly unlocks or kills the next factor-testing phase. |
| Alpha validation (only the two genuinely open, zero/low-cost threads: the Aug-17 volume-threshold DiD once its data window arrives; a first pass on 1-2 fundamentals-based hypotheses once 50-ticker coverage is real) | **20** | The volume-threshold candidate is pre-registered and free but literally cannot be pulled forward in time — allocate calendar-watching time, not engineering time, now. Fundamentals-based hypotheses are the one genuinely untested factor class; low cost to attempt once coverage exists. |
| Infrastructure maintenance (none planned beyond what's needed to support the above) | **10** | Reliability work just passed independent re-verification — further infrastructure investment has a demonstrated LOW marginal return right now (§7's "what to stop"). Reserve only enough to not regress. |
| Data acquisition (the 49-ticker zero-document gap, external sources) | **5** | Explicitly NOT needed to reach the 50-ticker target (already-archived documents suffice) — allocate minimally, defer the bulk of this decision. |
| Opportunity-cost review (founder time accounting vs. alternative ventures) | **15** | Bear case #3 is the single largest unquantified risk in this entire review — cannot be resolved by more engineering, only by the founder's own accounting. Allocate real time to answering it before the next HOLD→FUND decision (§10). |
| Other / reserve (unallocated, held for whichever of the above resolves first) | **25** | Deliberately unallocated — the two Gate-1 actions (§8) will determine, within ~2 weeks, whether the next 100 units should skew toward "scale FRE" or "redirect toward opportunity cost review" — locking in more than 75% now would pre-empt that decision. |

Derivation logic: allocations favor **reversible, low-cost, high-information**
actions (extraction pilot completion, opportunity-cost accounting) over
**expensive, hard-to-reverse** ones (full 44-ticker extraction campaign,
new infrastructure, new alpha-research hires/tools) — consistent with the
committee's HOLD verdict. Nothing is allocated to net-new infrastructure
or net-new alpha hypothesis generation, per §7.

---

## 7. WHAT TO STOP DOING

- **Stop building new infrastructure subsystems.** The reliability layer
  passed independent re-verification this session using real concurrent
  processes — there is no identified defect that justifies further
  infrastructure engineering right now. (Explicit standing instruction in
  this project's own records; reaffirmed here on the evidence.)
- **Stop registering new alpha hypotheses for their own sake.** The
  platform's own ledger already shows registering-to-stay-busy produces
  rejections, not edge — 15 of 19 formal hypotheses were rejected, several
  were economically identical restatements of earlier rejected claims
  (explicitly named and killed as such in the project's own prior audits).
- **Stop treating scratch-copy results as progress.** 403 conclusions
  exist only on a scratch copy; production is still 267. This distinction
  was blurred once already in this project's own history (the prior
  session's handoff cited the scratch figure as current state) — continued
  vigilance warranted.
- **Stop expanding document acquisition before extraction throughput is
  validated.** 191 tickers already have unextracted native-text documents
  — acquiring more before finishing extraction validation would be pure
  activity, not information gain.
- Documentation/reporting itself (four substantial audit documents this
  session) has now reached the point of **negative marginal ROI** if
  continued at the same rate without new decision-relevant action between
  reports — this review should be the last document produced before the
  Gate-1 actions in §8 actually execute.

---

## 8. NEXT 30 / 60 / 90 DAYS

**0–2 weeks (Gate 1 — already scoped, blocking everything else):**
- **Action**: Complete the remaining 4 documents of the extraction pilot
  when daily quota resets; then, if quality holds, seek explicit approval
  for the two tested-clean production migrations (period backfill;
  numeric-consistency schema column).
- **Uncertainty removed**: whether the fix generalizes beyond the one
  document already verified, and whether self-critique behaves correctly
  against period-complete, consistency-checked facts (unverified so far).
- **Decision unlocked**: whether to proceed to the 44-ticker backlog at
  all.
- **Success metric**: ≥80% of the remaining 4 documents produce
  period-complete facts with no numeric-consistency flags requiring
  investigation (i.e., flags that on inspection turn out to be real
  errors, not false positives).
- **Failure metric**: repeated period-metadata gaps, or ≥1 additional
  confirmed numeric error not caught by the consistency check.
- **Capital required**: ~4 more days of free-tier quota (~$0), a few
  hours of founder review time.

**2–6 weeks (Gate 2 — conditional on Gate 1):**
- **Action**: If Gate 1 succeeds, extend extraction to the 11-ticker
  "already ≥3 substantive documents" tier first (cheapest path to
  additional trend-viable coverage), re-measuring factor-family sample
  sizes after each batch rather than committing to the full 44 upfront.
- **Uncertainty removed**: real achievable ticker count and period depth
  at the 50-ticker/5-year target, replacing the current estimate with
  measured data.
- **Decision unlocked**: whether 50×5yr is actually reachable from
  already-archived documents, or whether the 49-ticker acquisition gap
  must be addressed after all.
- **Success/failure metric**: coverage measured directly against the
  §3-of-the-coverage-audit statistical rationale (≥50 tickers, ≥5 years,
  ≥3 periods each for trend-dependent factors).
- **Capital required**: ~10–13 days of quota-bound extraction, $0.

**6–12 weeks (Gate 3, and the parallel Alpha thread):**
- **Action**: Once (and only once) 50×5yr-equivalent coverage is real,
  run ONE pre-registered fundamentals-based hypothesis (e.g. Piotroski or
  Profitability) through the full existing validation gauntlet — the same
  gauntlet, not a shortcut. In parallel, monitor (not build) for the
  Aug-17 volume-threshold reform's data window to open (~mid-to-late
  October 2026) and run its own pre-frozen diagnostic then.
- **Uncertainty removed**: whether fundamentals contain any exploitable
  cross-sectional signal on NGX at all — the one factor class never
  tested in ~44 prior attempts.
- **Decision unlocked**: whether the Investment OS/FRE investment has
  produced a second data point toward Alpha, or reinforces the Quant
  seat's current "insufficient evidence" verdict.
- **Success metric**: a hypothesis that clears placebo + HAC + capacity
  gates (matching H-011's own bar).
- **Failure metric**: rejection matching the pattern of 15 of the prior
  19 hypotheses — expected, not catastrophic, but should trigger the
  HOLD→REDIRECT evidence check in §10 if it makes 2 of 2 new fundamentals
  tests both fail.
- **Capital required**: engineering/founder time for one hypothesis
  cycle (order of magnitude comparable to a prior single hypothesis on
  this platform, not separately estimated here — no reliable per-hypothesis
  time figure exists in this project's own records).

---

## 9. KILL / REDIRECT CRITERIA

| Metric | Threshold | Why it matters | How derived | Decision triggered |
|---|---|---|---|---|
| Extraction period-completeness rate | < 80% of newly extracted flow facts have valid period_start/end after Fix 1 | Below this, the deterministic pipeline still can't consume most new facts — the core defect this session fixed would not actually be fixed at scale | 80% chosen as "clearly better than the observed 0% pre-fix, with margin for real document messiness" — not arbitrary, but a judgment call pending a larger sample | STOP further extraction; return to prompt/validation engineering |
| Numeric-consistency flag rate on real data | > 15% of facts flagged | The check is designed to catch rare, severe errors (round-factor mistakes); a high flag rate would mean either the model's numeric accuracy is worse than believed, or the check is mis-calibrated (false positives) | 15% is roughly the ceiling before "review queue" stops being a queue and becomes the dominant workflow, defeating the purpose of automation | MODIFY: investigate whether flags are real errors or false positives before scaling either way |
| Cost/throughput per usable 5-year ticker | Free-tier throughput proves insufficient AND a paid-tier cost estimate exceeds what founder is willing to commit (founder-specified, not set here) | This is fundamentally a founder capital-allocation decision, not an engineering one | No default derivable from project data — must be set by the founder directly | REDIRECT extraction effort to a slower, free cadence rather than scale spend |
| Independent alpha tests on new fundamentals-based hypotheses | 0 of the next 3 tested clear even the placebo gate | Matches the platform's own revealed base rate (~1 confirmed of ~44) — 3 more consecutive clean rejections would be consistent with "fundamentals don't help either," not just bad luck | Derived from the existing ledger's own base rate, not invented | Move Quant seat's verdict from "insufficient evidence" to "evidence against" — triggers HOLD→REDIRECT review |
| Founder time consumed by infrastructure/reporting vs. decision-relevant action | No further audit/report is produced without a preceding NEW decision-relevant action (per §7) | Directly enforces the "reward information gain, not activity" principle this review itself was asked to apply | Self-referential: this review is intended to be the checkpoint | Any violation triggers an explicit HOLD→REDIRECT conversation about process, not content |

---

## 10. WHAT WOULD CHANGE THE COMMITTEE'S MIND

**HOLD → FUND**: A pre-registered fundamentals-based hypothesis (Value,
Quality, Piotroski, Financial Momentum, or Cash-Flow) clears the full
existing validation gauntlet (placebo p<0.05, HAC-robust significance,
stability across regimes, capacity-adjusted tradeable size materially
above H-011's ~₦694k ceiling) on the 50-ticker/5-year universe once
built. This is the single piece of evidence that would justify materially
increasing allocation — nothing short of an actual confirmed, capacity-
viable factor should move this seat's verdict.

**FUND → HOLD** (i.e., what would stop a future expansion once funded):
A confirmed factor's capacity, on real measurement, turns out to be
similarly capped to H-011's ~₦694k — repeating the pattern rather than
breaking it.

**HOLD → REDIRECT**: Either (a) three consecutive fundamentals-based
hypotheses fail to clear placebo (matching kill-criterion #4 above), which
would suggest the Investment OS/FRE's real value is as research
infrastructure rather than an alpha pipeline — at which point founder
capital should explicitly re-target FRE/OS output toward a different
consumer (e.g., a research/analysis product, not a trading strategy); or
(b) the founder's own opportunity-cost accounting (§6, 15% allocation)
concludes a specific alternative venture has demonstrably higher expected
value for the same time commitment.

**HOLD → KILL**: Evidence that (a) extraction cannot be made reliable even
after this session's fixes (repeated, varied data-quality failures beyond
what's already found), AND (b) no fundamentals-based hypothesis clears
placebo after a genuine attempt, AND (c) the founder's own opportunity-
cost review independently concludes the project is below the best
alternative. All three, not any one — a single negative result (e.g. one
more rejected hypothesis) is expected, priced-in evidence, not kill
evidence, per the platform's own revealed base rate.

---

## ECONOMIC LAYER SEPARATION

| Layer | Current Evidence | Confidence | Economic Status |
|---|---|---|---|
| Investment OS | Independently re-verified reliability (real concurrent-process tests); real, closed capture-vintage and matching-logic bugs found and fixed; backup/restore proven | HIGH | **PROMISING** (infrastructure-option value argued by Value/Moat seat, not independently measured as economically attractive) |
| FRE / Financial Intelligence | One confirmed, traced, fixed 10× numeric bug; one confirmed, traced, fixed structural matching bug (debt-to-equity never computed platform-wide); 1 of 5 planned pilot documents verified post-fix; throughput measured at 20 req/day | MEDIUM | **UNPROVEN → PROMISING**, pilot incomplete |
| Alpha Engine | 19 formal hypotheses + ~25 discovery tracks; 1 confirmed but capacity-dead (~₦694k); 15 rejected; 1 negative-in-testing; 1 abandoned | HIGH (on the negative finding itself) | **UNPROVEN**, trending toward evidence-against for classical factors specifically; fundamentals-based factors remain genuinely untested |

A PROMISING Investment OS does not imply a PROMISING FRE. A PROMISING FRE
does not imply any Alpha Engine outcome. Each layer's status stands on its
own evidence, per the committee's operating rules.

---

*Prepared from this project's own verified records. No agent, hypothesis,
or infrastructure component was modified in the preparation of this
review. Alpha Engine, hypothesis registry, and Research Workspace/Query
architecture: not touched.*
