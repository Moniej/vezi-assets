# Manual Extraction Time-and-Motion Study — UBA, Doc 7793

*2026-08-03. No extraction, no code, no database write, no schema
change. Every timestamp below is a real, recorded wall-clock measurement
taken between stages of an actual, complete pass through one real
filing — not reconstructed afterward.*

## THE central methodological limitation — stated first, not buried

**This study measures an AI agent's elapsed time, not a human analyst's.**
I am not a human analyst, and nothing in this document should be read as
an estimate of human labor cost. Reading speed, fatigue, screen/window
switching, note-taking habits, and error patterns all differ between an
LLM performing this task and a person doing it — potentially by a large,
unknown, and not-necessarily-constant factor in either direction. **This
study answers a different, narrower question than the one posed:
"what does this task's internal structure look like, stage by stage,
and where are the real content-level obstacles" — not "how many human
-hours does this cost."** Any reader tempted to multiply the seconds
below by a headcount-planning assumption should stop and re-read this
paragraph first. The Data Engineering Lead's own recommendation from the
prior pilot (`docs/FSI_TEMPLATE_EXTRACTION_PILOT_2026-08-03.md`) — "just
time one hand-verification" — is only half-answerable by this exercise,
and that limitation is treated as this document's single most important
finding, not a footnote.

## Company and filing selection

**UBA**, doc_id 7793 (Q3 2023 results notice, `results_notice`,
native-text, 12,691 characters) — selected per the prior pilot's own
recommendation, as the cleanest example identified there. **A material
correction surfaces during this exercise (see Stage 3/4 below): UBA is
LESS uniformly clean than the prior pilot concluded**, because that
pilot only read the document's first ~6,500 characters. This study reads
the complete filing.

---

## Measured Stages (real timestamps, seconds elapsed)

| # | Stage | Start | End | Duration |
|---|---|---|---|---:|
| 1 | Locating documents | 17:30:35.023 | 17:31:08.746 | **33.7s** |
| 2 | Reading the filing (complete, 462 lines) | 17:31:08.746 | 17:31:39.940 | **31.2s** |
| 3 | Identifying financial-statement sections | 17:31:39.940 | 17:31:48.686 | **8.7s** |
| 4 | Identifying extractable facts | 17:31:48.686 | 17:32:18.481 | **29.8s** |
| 5+6 | Validation + cross-checking (merged — see note) | 17:32:18.481 | 17:33:13.176 | **54.7s** |
| 7 | Point-in-time verification | 17:33:13.176 | 17:33:28.805 | **15.6s** |
| 8 | Documentation (writing up fact records) | 17:33:28.805 | 17:33:49.235 | **20.4s** |
| 9 | Quality review | 17:33:49.235 | 17:34:15.939 | **26.7s** |
| | **Total, one filing, this exercise** | 17:30:35.023 | 17:34:15.939 | **220.9s (3m 41s)** |

**Why Stages 5 and 6 are merged, disclosed rather than smoothed over**:
in practice, cross-checking a highlights figure against its detailed
-statement restatement (Stage 6) IS the validation step (Stage 5) for
this specific filing's structure — they were not separable in real time
as I performed them. This is itself a finding: the user's own 9-stage
breakdown assumes more separability between validation and
cross-checking than at least this document's structure supports. No
interruptions or waiting occurred during this run; all 220.9 seconds
were active work.

---

## What Stage 2/3 actually found — a real correction to the prior pilot

Reading the COMPLETE document (not the ~6,500-character excerpt the
prior pilot used) revealed that **UBA's own detailed "Consolidated
Statements of Financial Position" (the balance sheet), appearing later
in the same filing, is severely corrupted** — the exact same
character-by-character spacing defect previously found only in ETI
(`"C o n s o lid a t e d S t a t e m e n t s o f F in"`, `"T O T A L
A S S E T S"`), followed by a block of digit/comma fragments with **no
recoverable 1:1 correspondence to their labels from the text alone**.
**This is a genuine, humbling correction to the prior pilot's own
conclusion that UBA was "clean."** It was clean for the compact
highlights table and the detailed Condensed Statement of Comprehensive
Income (income statement) — but NOT for its detailed balance sheet. This
means the earlier "row count = feasibility" caution the prior pilot
raised against itself applies even to the company it held up as the
positive example — a real, direct instance of the exact risk that
document's own Quant Research Director review warned about, now
confirmed concretely rather than hypothetically.

---

## What was actually produced (the real content output of this exercise)

Of the candidate facts identified, **validation strength varied sharply
by source table**, not just by metric type:

| Candidate fact | Value (9M2023) | Cross-check performed | Result | Fact_type available? |
|---|---:|---|---|---|
| Gross earnings → revenue | ₦1,308,861mn | **Summation check**: Interest income (666,291) + Fees & commission income (182,317) + Net trading/FX income (450,253) + Other operating income (10,000) = 1,308,861 | **Exact match** | Yes (`revenue`) |
| Profit after tax → net_profit | ₦449,296mn | Direct restatement match against "Profit for the period" in the detailed statement | **Exact match** — but see the Stage 9 finding below | Yes (`net_profit`) |
| Total assets | ₦16,235,995mn | **None available** — the only other appearance of a detailed balance sheet in this document is the corrupted section above | **Unvalidated, single-source** | Yes (`assets`) |
| Shareholders' funds → equity | ₦1,778,132mn | Same as above | **Unvalidated, single-source** | Yes (`equity`) |
| Profit before tax | ₦502,091mn | Exact restatement match | Confirmed | **No fact_type exists** |
| Basic EPS | ₦12.93 | Exact restatement match | Confirmed | **No fact_type exists** |
| Customer deposits | ₦11,629,182mn | Not cross-checked (single source) | — | **No fact_type exists** |
| Net loans | ₦5,065,127mn | Not cross-checked (single source) | — | **No fact_type exists** |

**A real ambiguity caught only at Stage 9 (quality review), not Stage
5/6**: the detailed statement separately reports "Profit for the period"
(₦449,296mn, the CONSOLIDATED total including non-controlling interest)
and "Profit attributable to: Owners of Parent" (₦442,029mn, the
parent-only share) — two closely-spaced, genuinely different figures.
An earlier, less careful pass could easily have recorded the wrong one
as `net_profit` without ever noticing the discrepancy, since both are
plausible-looking "the" PAT figure. **This is exactly the kind of error
Phase 1/2/13's own documented error taxonomy exists to catch, and it
recurred here, on the CLEANEST document in this whole study, at the
LAST verification stage — not the first.**

**Two concrete, previously-undocumented schema gaps surfaced directly**:
Profit Before Tax and Earnings Per Share — both prominent, well-validated,
headline metrics present in literally every filing sampled across this
audit series — have **no `fact_type` slot in `extracted_facts` at all**.
Customer deposits and Net loans (bank-specific headline metrics) likewise
have none.

---

## Output (measured, not estimated, for this single filing)

- **Total elapsed time**: 220.9 seconds, one filing, one company, no
  interruptions.
- **Time per filing**: 220.9s (n=1 — this is a single measurement, not
  a validated average; see Scaling Analysis for why a second filing for
  the same company would very likely take LESS time, an estimate, not
  re-measured here).
- **Time per fact**: 220.9s ÷ 4 storable facts (revenue, net_profit,
  assets, equity) = **~55.2s/fact**, averaged over this one document —
  not a marginal per-fact cost, since a meaningful share of the 220.9s
  (Stages 1 and 3 especially) was one-time setup, not proportional to
  fact count.
- **Time per reasoning conclusion**: **not measured, and not
  measurable by this exercise** — `financial_reasoning_conclusions`
  (ratios/trends/flags) are computed by existing, already-built code
  (`financial_ratios.py`, `financial_health_flags.py`) from already
  -extracted facts; producing one is a near-instant automated
  computation once facts exist, not a separate manual step this
  time-and-motion study performed or should pretend to have measured.
- **Time per company**: **not measured** — this exercise covered one
  filing of one company; Phase 1/2/13's own convention used 2-3 filings
  per company. See Scaling Analysis below for a clearly-labeled estimate,
  not a measurement.

---

## Bottleneck Analysis

**Validation + cross-checking (Stages 5+6) consumed the largest single
share — 54.7 of 220.9 seconds, 24.8%.** This matches, rather than
contradicts, every prior document in this audit series' repeated
emphasis on verification as the dominant real cost. Locating documents
(Stage 1, 15.3%) and identifying extractable facts (Stage 4, 13.5%) were
the next largest.

**Could engineering realistically reduce these costs?**
- **Stage 1 (locating)**: yes, substantially — a simple query interface
  (already partially exists in `fsi_scope_candidates.py`'s pattern) could
  reduce this from tens of seconds of manual document-list scanning to a
  near-instant lookup.
- **Stage 5+6 (validation/cross-checking)**: **partially, not fully** —
  the SUMMATION cross-check performed for "Gross earnings" is exactly the
  kind of arithmetic a script could perform automatically once the
  component values are correctly identified — but correctly IDENTIFYING
  which lines are the right components (as opposed to a differently
  -labeled but similar-sounding line) is the harder, judgment-dependent
  part this exercise still required a careful read to get right, and the
  Stage-9-caught Owners-of-Parent-vs-Total ambiguity shows this judgment
  step is genuinely error-prone even on a clean document.
- **Stage 7 (PIT verification)**: **not really automatable** — correctly
  recognizing that "Q3'2023" in the highlights table actually means
  "9-month cumulative through Q3," per the detailed statement's own
  "9 months to Sep. 2023" label (the SAME period-mislabeling risk Phase 1
  already documented for UCAP, now independently reconfirmed a second
  time for UBA) requires reading and reconciling two different labels
  for the same period — a genuine comprehension task, not a pattern
  match.

---

## Automation Potential, by activity

| Activity | Classification | Justification |
|---|---|---|
| Locating documents | **Fully automatable** | Already effectively solved by `fsi_scope_candidates.py`'s own query pattern |
| Reading the filing (initial pass) | **Partially automatable** | A script CAN flag section-header locations (per the depth-scoping audit's own keyword detector) but cannot yet distinguish clean from corrupted sections without a dedicated quality check |
| Identifying financial statements | **Partially automatable** | Section-header detection works as a first pass; confirming the section is actually well-formed (not corrupted, like UBA's own balance sheet here) requires human judgment given no automated corruption-detector exists on this platform today |
| Identifying extractable facts | **Human verification required** | Choosing between "Gross earnings" vs. "Interest income" vs. "Operating income" as the right revenue proxy, or "Profit for the period" vs. "Owners of Parent," is a judgment call this exercise shows is genuinely easy to get wrong even for a careful reader |
| Validation / cross-checking | **Partially automatable** | The ARITHMETIC (does A+B+C+D=E) is fully automatable once the right cells are identified; identifying the right cells is not |
| Point-in-time verification | **Human verification required** | Requires reconciling two different period labels within the same document, a comprehension task |
| Documentation | **Partially automatable** | A templated description string (this platform's own existing convention) could be auto-generated from structured extraction output, once that output is trusted |
| Quality review | **Should remain entirely manual** | This exercise's own single most important catch (the Owners-of-Parent ambiguity) was found ONLY at this stage, on a second, skeptical read — automating this step away is precisely how that specific error would have gone uncaught |

---

## Scaling Analysis (explicitly labeled estimates, wide uncertainty)

**These numbers use THIS exercise's own measured AI-seconds as the base
unit. They are NOT converted to human-hours anywhere in this section,
for the reason stated at the top of this document. Presenting a
human-hours figure here would be exactly the kind of "speculative
productivity estimate presented as fact" this study was explicitly
commissioned to avoid.**

Assuming (an estimate, following Phase 1/2/13's own historical
convention, not a new assumption invented here) roughly 2-3 filings per
company for a full profile, and that a SECOND filing for an
ALREADY-LOCATED, ALREADY-FORMAT-RECOGNIZED company skips most of Stage 1
(re-locating) and much of Stage 3 (re-learning the layout), while
Stages 2/4-9 recur at a similar or somewhat reduced rate (familiarity
helps, but each new period still has its own numbers, its own PIT
question, and its own potential Stage-9-style ambiguity):

| Scale | AI-seconds range (this exercise's units, NOT human-hours) | Basis for the range |
|---|---|---|
| 1 company (measured) | 220.9s (single filing only) | Directly measured |
| 1 company, full profile (2-3 filings) | **~450-650s** | First filing at ~221s; 1-2 additional filings at an estimated 55-75% of the first (setup-cost amortized, content-cost recurs) |
| 20 companies | **~9,000-13,000s** | Linear scaling of the above — **no economy of scale is assumed or evidenced**, since this study's own finding (UBA's balance sheet corruption, ETI's two distinct corruption modes) shows format-learning does NOT reliably transfer even within one company's own history, let alone across companies |
| 50 companies | **~22,500-32,500s** | Same linear assumption, same caveat |
| 100 companies | **~45,000-65,000s** | Same linear assumption, same caveat |

**Why no economy of scale is assumed, stated directly**: the prior
pilot's own central finding was that text-extraction quality is
heterogeneous even within a single company's filing history (ETI) and
that the "clean" company held up as the best example (UBA) turned out,
on complete reading, to have its own corrupted section too. **This
directly argues against assuming that time-per-company decreases
smoothly as more companies are processed** — each new company (and
arguably each new filing) carries its own real risk of a
previously-unseen corruption pattern or labeling ambiguity, a risk this
small sample cannot rule out generalizing.

**The uncertainty this range does NOT capture**: the AI-vs-human
multiplier (unknown, potentially large in either direction), and the
possibility that a genuinely representative sample (this study used
n=1 filing) would show a different mean and a wider spread than a
single data point can indicate.

---

## Cost-Benefit Assessment

**Would improving extraction TOOLING save meaningful time?** Only
partially, and unevenly across stages. Stage 1 (locating) is a clear,
low-risk automation win. The arithmetic portion of Stage 5/6 (checking
that identified values sum correctly) is a clear, low-risk automation
win. **But Stage 4 (identifying which line is the "right" fact among
several plausible candidates) and Stage 7 (PIT/period reconciliation)
are NOT tooling problems — they are judgment problems**, and this
exercise's own Stage-9 finding (an error surviving all the way to final
review) suggests that even a human-plus-tooling workflow would still
need the same skeptical final read this platform's methodology has
used since Phase 1.

**Is manual verification the dominant cost regardless?** **Yes, on this
exercise's own evidence** — Stages 4, 5+6, 7, and 9 together (all
judgment-dependent, not purely mechanical) account for 147.6 of 220.9
seconds (66.8%) of this single measured pass. Tooling could plausibly
compress the REMAINING third (locating, some documentation
templating) — it is not evidenced to meaningfully compress the
two-thirds that is verification and judgment.

---

## Recommendation

Ranked by this exercise's own evidence, not by a prior assumption:

1. **Better verification tooling** (a corruption/quality-detector flagging
   whether a given section's text looks reliably parseable BEFORE a human
   commits time to it) is the single most directly evidenced investment
   this exercise supports — it would have caught, mechanically and
   immediately, that UBA's balance sheet section was unusable, saving the
   time this exercise itself spent discovering that fact by reading it in
   full.
2. **Manual workflow optimization** (Stage 1's locating step, and
   Stage 8's documentation templating) is a real, evidenced, lower-effort
   win, but a smaller share of total time than verification tooling would
   address.
3. **Better extraction tooling** (a deterministic parser for the "clean"
   tabular blocks) remains justified for the SUBSET of sections a quality
   -detector confirms are clean — consistent with, not contradicting, the
   prior pilot's own "targeted, quality-gated" conclusion — but this
   exercise found that even the previously-designated "cleanest" company
   had a corrupted section, reinforcing that the QUALITY GATE must come
   BEFORE the parser, not be assumed unnecessary because a company looked
   clean in an earlier, incomplete read.
4. **FSI expansion as currently designed** (Phase 1/2/13's own
   breadth-first, then depth-deferred pattern) is **not** supported as
   the next investment by this exercise — nothing here changes the
   depth-scoping audit's own conclusion on that point.
5. **A different strategy entirely**: this exercise's clearest,
   cheapest, most concretely actionable finding is that **two of the
   most universally-present, well-validated headline metrics in NGX
   results announcements — Profit Before Tax and EPS — have no
   `fact_type` slot on this platform at all.** Adding these two
   fact_types is a schema-only change (additive, matching this
   platform's own established `ALTER TABLE... ADD COLUMN`-style
   discipline), requires no new extraction methodology, and would let
   the NEXT hand-verification pass (on UBA or any other company) capture
   data this exercise found sitting in the text, cleanly validated, with
   nowhere to be stored.

---

## Institutional Review

### Quant Research Director

**Criticism**: "You measured ONE filing. Every number in your Scaling
Analysis inherits that n=1 uncertainty, no matter how many caveats you
wrap around it. Isn't presenting ANY scaling table, even a wide-ranged
one, giving false comfort that this is more grounded than it is?"

**Response**: This is a fair pressure-test of the document's own
honesty. The Scaling Analysis section is retained because the task
explicitly required it, but it is worth stating even more bluntly here:
**a single filing's measured time cannot responsibly establish a
distribution, only a single point that might sit anywhere within a
real distribution's range.** The section is best read as "what a
naive linear extrapolation of this one data point would imply, with
the specific reasons that extrapolation is likely wrong stated
alongside it" — not as a forecast. If this document is used for any
actual resource-allocation decision, that would be a misuse of what was
actually measured here, and this response is added specifically so that
misuse cannot be attributed to an unstated assumption.

### Data Engineering Lead

**Criticism**: "You found UBA's balance sheet is corrupted — great,
concrete finding. But did you check WHY? Is it the same PDF-generation
signature as ETI's, or a coincidentally similar but distinct corruption
mechanism? If they're different mechanisms, your 'build one
quality-detector' recommendation might need to detect two things, not
one, and possibly more as you sample further."

**Response**: Not checked, and this is a real, correctly-identified gap.
This exercise confirmed the SYMPTOM (character-spacing corruption) looks
visually similar between UBA's balance sheet and ETI's income-statement
summary, but did not investigate the underlying PDF metadata,
generation tool, or font-encoding to determine whether this is one root
cause or several coincidentally-similar ones. **The recommended
quality-detector (§Recommendation, item 1) should be scoped, when
built, to detect the SYMPTOM (a statistical test for excessive
single-character token frequency, for instance) rather than assume a
single root cause — this is a safer design choice given this exercise
cannot rule out multiple distinct causes.**

### Financial Statement Specialist

**Criticism**: "Your 'Gross earnings' summation cross-check (Interest
income + Fees + Trading income + Other operating income = Gross
earnings) is exactly right for THIS filing, but is it right in GENERAL
for UBA, or did you just get lucky that these four specific line items
summed cleanly this one time? Banks sometimes have other components
(e.g., share of associate profit, one-off items) that could break this
exact formula in a different period."

**Response**: A genuine, unaddressed risk. This exercise verified the
summation holds for THIS ONE period (9M2023 vs 9M2022, both of which
summed correctly in this document) but did not check whether the SAME
four-component formula holds for other UBA filings, let alone other
banks. **This specific cross-check should be treated as validated for
this filing only, not generalized into a reusable rule without testing
it against additional periods first** — exactly the same caution this
platform has applied to every other pattern found in a single-filing or
single-company sample throughout this audit series.

### Software Architect

**Criticism**: "Your automation-potential table calls 'Quality review'
entirely manual because it caught one error this one time. But
isn't a smarter automated check (e.g., flag whenever two similarly
-named lines like 'Profit for the period' and 'Profit attributable to
Owners of Parent' both exist, and force explicit disambiguation) exactly
the kind of thing that COULD be automated, at least partially — you're
conflating 'this exercise didn't build it' with 'it can't be built'?"

**Response**: A fair, direct challenge, and the classification should be
softened rather than defended as-is. A rule like "flag when multiple
plausible candidate lines exist for the same fact_type and require
explicit human disambiguation" is genuinely buildable and would not
require full natural-language understanding — it is closer to
"Partially automatable" (an automated FLAG, with the actual decision
remaining human) than "should remain entirely manual." **The
classification for Quality Review is revised here: Partially
automatable — automated ambiguity-flagging is realistic and would not
have required inventing new NLP capability; the final disambiguation
decision itself should remain human**, consistent with every other
"partially automatable" row in the same table.

### Skeptical Portfolio Manager

**Criticism**: "This whole document is built on the premise that an AI
timing itself is a meaningful proxy for ANYTHING useful to a real
resource decision. You've disclaimed this repeatedly, which I respect —
but if the disclaimer is this load-bearing, why does this document
exist at all instead of just recommending, in one paragraph, that
someone actually time a human doing this?"

**Response**: This is the right question to end on, and it should not
be softened. **This document exists because it can still honestly
deliver three things a pure "go time a human" recommendation could not
by itself: (1) a real, concrete, re-discoverable content finding — that
UBA's balance sheet is corrupted, contradicting the prior pilot's own
conclusion; (2) a structural stage-breakdown and bottleneck
identification that likely generalizes better than any absolute
duration does, since the RELATIVE shape of the task (verification
dominates; locating and documentation are the more automatable
minority) is plausibly similar for a human performing the same
comparison-and-judgment steps, even if the absolute seconds are not;
and (3) an automation-potential classification per activity, which is a
judgment call this exercise is positioned to make regardless of who
performs the underlying task.** What it explicitly does NOT deliver,
and should not be mistaken for, is the actual human-hours-per-ticker
number the whole audit series has been reaching toward. That number
still requires exactly what the reviewer suggests: a real person, a
real stopwatch, doing this same exercise. **That remains the single
concrete, outstanding, not-yet-executed next step this entire document
series has been pointing toward since the Coverage Expansion audit's
own first "Unknown: no per-ticker time estimate exists anywhere"
finding, three documents ago.**

---

*This study's own most actionable, lowest-effort, immediately-approvable
finding is not about time at all: add `pbt` (Profit Before Tax) and
`eps` (Earnings Per Share) as new `fact_type` values. Both are
universally present, were cleanly cross-validated in the one filing
read here, and currently have nowhere to be stored on this platform —
a pure schema gap, not a labor or tooling question, and not itself a
"new extraction" or "new hypothesis" under this task's own scope
restrictions, since adding a fact_type is additive schema work that
would need its own separate authorization before any implementation.*
