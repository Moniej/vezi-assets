# FSI Expansion — Owner Decision Package

*2026-08-03. This is a synthesis document, not a new audit — it performs
no new measurement. It converts four prior read-only audits
(`FSI_COVERAGE_EXPANSION_DECISION_AUDIT_2026-08-03.md`,
`FSI_DEPTH_SCOPING_AUDIT_2026-08-03.md`,
`FSI_TEMPLATE_EXTRACTION_PILOT_2026-08-03.md`,
`FSI_TIME_AND_MOTION_STUDY_2026-08-03.md`) into a single set of answers
to four owner questions. Where the four source documents disagree in
emphasis or where evidence is genuinely thin, that is stated directly
rather than smoothed over.*

---

## The four answers, upfront

1. **Should FSI expansion proceed? Partially, yes — but not in the form every
   phase to date (1, 2, 13) has actually used.** Proceed with a narrow,
   depth-first, quality-gated pilot. Do not fund a large breadth-first
   labor commitment.
2. **First milestone: a ~15-25 ticker set with full three-statement
   depth** (income statement + balance sheet + cash flow, confirmed by
   hand, not by keyword presence), drawn from the 21-ticker
   full-signal group already identified — not a ticker-count milestone
   like "20 tickers" measured on revenue/net_profit alone.
3. **Build first (in this order): (a) one real, human-timed trial to
   finally produce the missing cost number; (b) the ticker-attribution
   fix for the null-ticker documents (CAVERTON and similar); (c) a
   small hand-verification pilot of the tabular `results_notice`
   format on 3-5 tickers; (d) the `pbt`/`eps` schema addition.** All
   four are cheap, all four are prerequisites to any larger commitment,
   none of them is itself "FSI expansion."
4. **Do not build yet: a production deterministic parser, an
   OCR/vendor pipeline, or a breadth-only extraction push to the
   remaining 40 candidate tickers.** All three are real future options,
   none is evidenced as the right next spend.

---

## 1. Should FSI expansion proceed?

**The evidence does not support the default assumption** ("more hand
extraction, same method as Phases 1/2/13") **as the highest-return next
investment.** Three independent findings converge on this, each from a
different document in the series:

- **Ticker breadth and field depth have moved almost independently.**
  The joint assets+liabilities+equity ticker count has been stuck at
  exactly **5** since Phase 2 (2026-08-01) — unmoved through 25
  subsequent phases and Phase 13's own 5-ticker breadth expansion.
  Repeating that pattern a fourth time would very likely raise ticker
  count without raising depth again. *(Coverage Expansion Audit, §6/§8)*
- **Even a maximal hand-extraction push has a hard ceiling.** All 50
  already-scoped, already-archived candidate tickers, fully extracted,
  cap IRU coverage at **44/100 (44%)** — not 50%, not the full
  universe. Going further requires a separate OCR/vendor decision,
  open since 2026-07-16 and untouched by any of these four audits.
  *(Coverage Expansion Audit, §2.1)*
- **No per-ticker or per-filing cost figure has ever existed on this
  platform**, across three completed extraction phases. The
  time-and-motion study finally produced one real data point
  (220.9 seconds, one filing, one AI agent) — but it is n=1, measured
  on an AI agent rather than a human, and its own Quant Research
  Director review states directly that no resource-allocation decision
  should be built on it. **The actual cost of the option being
  considered is still not known.** *(Time-and-Motion Study, throughout)*

**Against that**, real, positive evidence did emerge across the depth
and template audits that was not available when the Coverage Expansion
Audit made its "Unknown" call on 40-ticker depth:

- **21 of the 40 remaining candidate tickers show full three-statement
  section signal** (income statement + balance sheet + cash flow all
  detected), and the other 19 show partial signal — none is a
  confirmed dead end. *(Depth Scoping Audit, §2.2)*
- **A genuinely new, never-attempted extraction method has real
  structural support**: 112 of 244 `results_notice` documents (19
  tickers) contain a repeating, tabular label-value-value-%change
  block — directly answering the "has a hybrid deterministic +
  human-verification approach ever been evaluated?" question the
  Coverage Expansion Audit's own Software Architect review flagged as
  unanswered. UBA's own filing, hand-verified, confirmed this block
  contains Gross earnings, PBT, PAT, EPS, Total assets, and
  Shareholders' funds together. *(Depth Scoping Audit §6.2; Template
  Pilot; Time-and-Motion Study)*
- **11 of 16 named factor families share this single blocker** —
  meaning if the depth ceiling genuinely moves, the research payoff is
  the highest-leverage single unlock available anywhere on the current
  roadmap. *(Coverage Expansion Audit, §1.5, §6)*

**Net judgment**: the *reason* to keep investing in FSI is stronger
and more concrete than it was three documents ago (a real extraction
method candidate now exists, not just a hope). The *reason* to keep
the investment narrow is also stronger (the joint-depth trap is now
confirmed to have actually happened once already, not just a risk).
Both point to the same shape of decision: **proceed, but small,
targeted, and depth-first — not a repeat of the breadth-first pattern.**

---

## 2. If yes, what is the first milestone?

**Not a ticker-count number in isolation.** The series' own repeated
finding is that ticker count without joint-field depth doesn't unlock
anything beyond a crude Growth-style test. The milestone that actually
matters:

> **A ~15-25 ticker set with confirmed (hand-verified, not
> keyword-detected) income statement + balance sheet + cash flow
> depth**, drawn primarily from the 21-ticker full-signal group
> (`ABCTRANS, ACCESSCORP, AIICO, AIRTELAFRI, ARADEL, CHELLARAM,
> ELLAHLAKES, ETI, FIDELITYBK, FTNCOCOA, GEREGU, LASACO, MECURE, NB,
> NIDF, NOTORE, PZ, UACN, UNILEVER, VERITASKAP, VFDGROUP`) plus
> whichever of the existing 10 tickers can be brought to full depth.

Why this range and not another:

- It is anchored to the platform's own reasoned (not derived) breadth
  floor — the 20-35 name range associated with avoiding the platform's
  own most common historical failure mode (breadth-ceiling rejections,
  5 of 13 to date). *(Coverage Expansion Audit, §7 — explicitly labeled
  a heuristic, not a power calculation, and the Skeptical
  Statistician's review insists it not be treated as one.)*
- It is bounded by real evidence, not aspiration: 21 tickers show full
  signal today; reaching 25 means a small number of the 19 partial-signal
  tickers would also need to convert on hand inspection.
- Explicitly **not** the 44-ticker breadth ceiling — that number
  answers "how far could revenue/net_profit-only extraction go," not
  "how far could full-depth extraction go," and conflating the two is
  exactly the mistake both prior audits warn against.

**This milestone should not be committed to as a labor budget yet.**
Per §3 below, the correct first action is a pilot, not the milestone
extraction itself.

---

## 3. What should be built first?

In dependency order — each item is cheap, each is a genuine
prerequisite, and none is itself the FSI expansion decision:

### 3.1 One real, human-timed trial (highest priority)
The single most repeated, most explicitly unresolved finding across
all four documents: **no one has ever timed a human doing this.** The
time-and-motion study's own closing line names this as "the single
concrete, outstanding, not-yet-executed next step this entire document
series has been pointing toward... three documents ago." Every cost
figure in every prior audit is either absent or explicitly an AI
proxy that its own authors say should not be used for resource
planning. This is the cheapest possible action (one person, one
filing, a stopwatch — UBA doc 7793 is already the pre-scoped
candidate) and it is the input every other decision in this package
is currently missing.

### 3.2 Ticker-attribution fix (cheap, zero-extraction-labor recovery)
319 native-text documents platform-wide have `ticker IS NULL`; 30 of
those pass the strict candidate filter; at least one confirmed case
(CAVERTON, a real tracked security whose name appears in its own
document text) is a pure data-quality bug, not a content gap. **Before
fixing in bulk**, per the Data Engineering Lead's own correction to
the first audit's "cheap to fix" overstatement: check whether the 319
nulls share a common ingestion batch (bulk-fixable) or are scattered,
individually-caused failures (not cheap). That triage itself is cheap
and should happen first.

### 3.3 Tabular `results_notice` hand-verification pilot (3-5 tickers)
The most promising new finding of the whole series (§6.2 of the Depth
Scoping Audit) is unverified beyond one document (UBA). Per the Quant
Research Director's review of that finding: row count identifies
*where* a tabular structure exists, not *what* is in it. Before any
parser is built, hand-read 3-5 of the 19 tabular-format candidates
(strongest by row count: LASACO, GEREGU, AIRTELAFRI, ETI — none
currently in the 10-ticker extracted set) to confirm the key metrics
(revenue, PAT, total assets, not just numeric-looking rows) are
actually present and consistently positioned.

### 3.4 `pbt` and `eps` fact_type addition (pure schema change)
Both are universal, cleanly cross-validated headline metrics in every
filing sampled across all four audits, and neither has anywhere to be
stored. This is additive schema work only (no extraction, no new
methodology) — cheapest, most mechanical item in this list, but still
requires its own separate authorization since it was explicitly
out-of-scope for every audit that surfaced it.

None of these four items requires resolving the FSI expansion decision
first — they are useful regardless of which larger option (Option B/C/D
from the Coverage Expansion Audit) is eventually chosen, and 3.1
specifically produces the input needed to actually choose between them.

---

## 4. What should explicitly not be built yet

- **A production deterministic/template parser for financial
  statements.** The Template Pilot's own decision is narrower than
  this: "justified only as a targeted, quality-gated pilot on a
  confirmed-clean subset, not a general-purpose parser assumed to work
  archive-wide." Even the "cleanest" company found (UBA) turned out,
  on complete reading, to have a corrupted section — the quality gate
  must exist and run *before* any parser is written, not be assumed
  unnecessary.
- **A breadth-only extraction push to the remaining 40 candidate
  tickers, at Phase 13's narrow revenue/net_profit/ebit/ebitda scope.**
  This is now the pattern **two separate audits** have identified as
  the platform's own documented non-result (ticker count rising, joint
  depth staying flat). Repeating it a third time without first
  re-scoping toward depth would spend real labor against a known risk.
- **The OCR/vendor pipeline.** The only path past the 44/100 ceiling,
  but a genuinely separate, larger, cost-bearing decision open since
  2026-07-16 with no new information from any of these four audits.
  Do not fold this decision into the FSI-depth-pilot decision — they
  have different owners, different costs, and different timelines.
- **Any large, unbounded labor allocation of any kind**, until 3.1 (the
  timed human trial) produces a real cost number. Every prior document
  in this series states this explicitly; repeating a large-scale
  extraction commitment without that number would mean spending
  against both an unmeasured cost and an unmeasured yield
  simultaneously.
- **Building on the company-self-reported ratios found in the tabular
  blocks** (Cost-to-Income, RoAE, etc., surfaced in §6.2 of the Depth
  Scoping Audit). These are the company's own computed figures, not
  independently re-derived — a disclosed, unresolved construct-validity
  question, separate from the extraction-feasibility question this
  package addresses.

---

## 5. What this package does not change

- **H-017 (Dividend Payer Status) proceeds independently of this
  decision**, per unconditional agreement across both the Coverage
  Expansion and Depth Scoping audits — it requires no FSI data and
  should not wait on any part of this package.
- **This package does not itself authorize the schema change (§3.4),
  the pilot (§3.3), or the timed trial (§3.1)** — each was explicitly
  scoped out of its originating audit's own authority and needs its
  own go-ahead, even though all three are cheap. This document
  recommends them; it does not execute them.

---

## 6. One caveat that should travel with this whole package

Per the Skeptical Portfolio Manager's review of the Depth Scoping
Audit — the sharpest, most load-bearing caveat in the entire series,
and it applies here too: **every "promising" finding cited above is a
count of textual presence or a single hand-verified example, not a
confirmed, validated, at-scale extraction result.** Nothing in this
package or its four source documents confirms that the depth-first
pilot in §3.3 will actually succeed, or that the tabular format
generalizes past the handful of documents actually read by a human.
The value of this whole line of work is narrowing *where* to look and
*roughly how promising it is* — not confirming that looking there will
pay off.
