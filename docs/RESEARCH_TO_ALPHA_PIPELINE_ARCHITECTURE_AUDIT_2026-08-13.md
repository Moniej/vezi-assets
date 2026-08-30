# Research-to-Alpha Pipeline Architecture Audit — 2026-08-13

**Read-only.** No code, schema, config, or production data changed while
producing this. Verified at close: `extracted_facts=495`,
`financial_reasoning_conclusions=267`, 10 computed tickers — all
unchanged. `LocalLIMProvider` not touched, its quality gate not touched,
no fallback wiring added. Alpha Engine not touched.

---

## A. Existing architecture relevant to this objective

Four real, independently-built subsystems, mapped to the target diagram:

1. **Document/news extraction & reasoning graph** (`schema.sql`):
   `documents` → `extracted_facts` → `causal_chain_steps` →
   `impact_assessments` → `investment_implications` → `effect_chains` →
   `research_task_candidates`, gated by `self_critique_reviews`. Driven by
   `src/ngxrot/documents/{extract,reasoning,self_critique,prompts}.py`
   through the `LLMProvider` abstraction (Gemini live, LocalLIM gated off).
2. **Qualitative research workflow** (`registry.sql`): `research_projects`
   → `research_notes`/`research_evidence`/`research_findings` →
   `research_hypotheses` → `research_conclusions`, plus a general-purpose
   `research_query.py` layer on top of Phase-1 data infrastructure
   (identity/lineage/PIT/universe).
3. **Formal hypothesis ledger + quant testing engine**: `hypotheses` /
   `experiments` / `hypothesis_experiments` (`registry.sql`, immutable,
   frozen-on-resolution) tested by `backtest_xs.py` (cross-sectional
   sim, rank/vol/size/liquidity/payer-status scoring, capacity report,
   regime gating, interaction dimensions, **placebo statistics already
   built**) and `engine_full.py` (constituent-level, ADTV-capped,
   line-item-cost-modeled realism upgrade).
4. **Alpha Engine** (`alpha_engine.py`): reads ONLY `confirmed` hypotheses
   from the registry and emits `Recommendation`s. By its own docstring:
   *"A model is plugged in by validating it, not by editing this file."*
   This is the CIO/capital-allocation boundary, already enforced by
   construction, not just convention.
5. **Portfolio/Risk/Execution/Performance/Attribution** (`src/ngxrot/portfolio/`,
   built 2026-08-12/13, 134/134 tests passing) — consumes `alpha_engine`'s
   `Recommendation`s, paper-only, untouched by this audit.

---

## B. What already works (real, verified, not aspirational)

- **The extraction→reasoning graph is real and produces checkable output.**
  495 facts, 470 grounded, a working evidence-citation discipline, a
  working self-critique gate with 8 named failure modes
  (`self_critique_reviews.question`), immutable audit trail (`llm_calls`).
- **The quant testing engine is genuinely mature.** `backtest_xs.py`
  already has placebo tests (`placebo_stats`), regime-gating
  (`regime_gated_targets`), interaction-dimension scoring, and a
  standalone `capacity_report`. This is not a stub — 18 hypotheses have
  actually been run through it (H-001 through H-017, H-019; H-018
  apparently skipped/renumbered).
- **The CIO boundary already exists architecturally.** `alpha_engine.py`
  cannot act on anything that isn't `confirmed` in the ledger — the
  "LLM must not declare alpha" rule is enforced by the code's own data
  dependency, not by a policy someone could forget.
- **The hypothesis ledger is immutable and disciplined.** Triggers block
  editing a resolved hypothesis, require a written conclusion on
  resolve, and forbid new experiments on a frozen hypothesis. 17 of 18
  registered hypotheses are `rejected` or `untested` — this is a system
  that actually kills ideas, not one that rubber-stamps them (matches
  your "generate hundreds, kill most" instinct, at smaller scale so far).
- **Provider abstraction and portfolio layer**: confirmed already built
  in the prior two audits this session's history covers — not re-litigated
  here.

---

## C. What is genuinely missing

1. **Finance-literature ingestion: does not exist at all.** Searched the
   entire codebase for "academic," "journal" (as in finance journal, not
   `portfolio/journal.py`'s decision journal), "SSRN," "arxiv,"
   "literature" — zero real hits. There is no ingestion path, no schema,
   no concept of an external research paper anywhere in this system.
2. **LLM-generated hypotheses never reach the quant testing engine —
   confirmed at zero, not "rarely."** Queried directly:
   `investment_implications.status='promoted_to_discovery_candidate'` →
   **0 rows, ever**. `research_task_candidates` → **84 open items, 0
   promoted, 0 dismissed** — this queue has never been worked, not even
   once. **All 18 hypotheses in the formal ledger (`hypotheses` table)
   are quantitative price/volume factors (Size, Liquidity, Dividend
   Payer Status, etc.) — none trace back to a document/news-derived
   `investment_implications` row.** The extraction/reasoning graph and
   the hypothesis-testing engine are two real, working, but **currently
   disconnected islands.**
3. **No structured "formal test definition" schema exists.** The
   `hypotheses` table is a lightweight ledger (description, motivation,
   status, conclusion) — no universe/signal/entry-condition/
   holding-period/benchmark columns. `research_hypotheses` (the
   qualitative-research-side table) is similarly light (statement +
   supporting/contradicting finding IDs). **The actual formal test
   parameters your example hypothesis needs (universe, entry condition,
   holding period, benchmark, validation plan, confirmation/rejection
   criteria) exist only as free-text prose in `docs/PREREG_H-*.md` files**
   (17 of them) — hand-written each time, not generated from or stored
   as structured data a script could consume to build a `backtest_xs.py`
   config automatically.
4. **Management-statement fact type and explicit Catalyst typing** —
   named in the prior audit turn, unchanged, still real gaps (the
   STANBIC qualitative-statement mistag is a live example).
5. **Sentiment is not a gap — it's a deliberate exclusion**, restated
   from the prior turn: the system prompt explicitly says *"you do not
   produce sentiment labels."* Building sentiment scoring would reverse
   a considered design decision, not fill an oversight.

---

## D. Exact gap between current Research OS and the target pipeline

Mapping your 10-stage diagram directly against verified reality:

| Stage | Status |
|---|---|
| Documents/news/company filings | 🟢 BUILT — real ingestion, real extraction |
| + Finance journals/academic research | 🔴 DOES NOT EXIST |
| → Research knowledge | 🟢 BUILT (two forms: document-derived `investment_implications`, and qualitative `research_findings`/`research_notes`) |
| → LLM Research Analyst | 🟡 PARTIAL — extracts facts/mechanisms from documents well; has never been asked to produce a testable hypothesis in the target's structured shape; has no literature input at all |
| → Structured Hypotheses | 🔴 MISSING — no schema exists for "signal + universe + entry + holding period + benchmark" as structured data |
| → Hypothesis Engine | 🟡 PARTIAL — `hypotheses`/`experiments` ledger exists and is disciplined, but nothing feeds it automatically; every entry to date is hand-authored, quant-only |
| → Formal Test Definition | 🔴 MISSING as structured data — exists only as free-text `PREREG_H-*.md` |
| → NGX Historical Test | 🟢 BUILT — `backtest_xs.py`/`engine_full.py`, genuinely mature |
| → Robustness Validation | 🟢 BUILT — placebo, regime-gating, interaction dimensions already implemented |
| → Candidate Alpha | 🟢 BUILT — the `confirmed` status gate, enforced by `alpha_engine.py`'s own read path |
| → Portfolio + Risk | 🟢 BUILT (2026-08-12/13, separate track, paper-only) |
| → Investment | ⚪ Correctly not reached — no confirmed, capacity-viable factor exists yet |

**The gap is narrow and specific, not architectural.** Everything from
"NGX Historical Test" onward is real and working. Everything before
"Structured Hypotheses" (document reasoning) is real and working. **The
break is in the middle two boxes**: nothing translates a document-derived
insight (or, per the missing literature capability, an academic finding)
into the structured, testable shape the quant engine actually consumes.

---

## E. Current finance-literature capabilities

**None.** Zero ingestion, zero schema, zero prior work. This is not a
"weak" capability — it is an absent one. Any of your listed backlog items
that specifically need literature grounding (e.g., citing the actual
academic earnings-acceleration or accruals literature, not just an NGX
company's own filing) cannot be sourced from anything currently in this
system.

---

## F. Current LLM capabilities

Real and specific, not generic:

- Reads one document at a time, produces evidence-linked facts
  (`extracted_facts`), causal chains (`causal_chain_steps`), categorized
  impact judgments (`impact_assessments`), and a rich implication record
  (`investment_implications`: direction, magnitude, duration bucket,
  bull/bear/base-case deltas, market-reaction assessment) — genuinely
  closer to "analyst" than "summarizer" for THIS narrow task.
- Self-critiques against 8 named failure modes before anything is
  trusted (`self_critique_reviews`).
- **Cannot and does not**: read academic literature (no path exists),
  produce a structured/testable hypothesis (no schema exists for one),
  or declare something alpha (architecturally blocked — `alpha_engine.py`
  only reads `confirmed` ledger entries, and nothing document-derived has
  ever reached that ledger).
- **LocalLIMProvider**: exists, correctly gated off (per the 2026-08-13
  viability audit — confidently-wrong outputs, 0% coverage of the actual
  extraction schema, currently non-functional inference environment).
  Not touched by this audit, not proposed for use here.

---

## G. Current NGX data/testing capabilities

> **ADDENDUM (2026-08-13, later same day)**: the backfill named in row 2
> below was subsequently approved by the operator and applied to
> production (backed up first, integrity + restore verified). Table
> updated to reflect the real post-apply state, not the pre-approval
> snapshot this audit originally measured.

| Metric | Value |
|---|---:|
| Extracted facts (production) | 495, spanning 74 tickers (unchanged — backfill invents nothing) |
| Facts surviving to a COMPUTED conclusion | **191 (38.6%)**, was 131 (26.5%) pre-backfill |
| Tickers with any computed ratio/trend/flag TODAY | **14**, was 10 pre-backfill |
| Target for credible cross-sectional testing (this platform's own prior derivation) | 50 |
| Tickers with ≥3 usable periods (minimum for a real trend read) | 8 (unaffected by this backfill — it completes `period_start` only, doesn't add new periods) |

**1. What data is available**: 495 raw facts across 74 tickers, but only
10-16 have enough period-complete, currency-matched, non-zero-denominator
data to produce a real ratio/trend/flag.

**2. Which securities have sufficient historical coverage**: NASCON,
DANGCEM, AFRIPRUD, UCAP, BUAFOODS, CAP, MTNN, OANDO, NESTLE, UBN (10
today). +AIRTELAFRI, DEAPCAP, GEREGU, LASACO, UACN, VERITASKAP (6 more,
pending the backfill).

**3. What factors/signals can currently be tested**: none, at a
statistically legitimate cross-sectional breadth. The computation
infrastructure for Value/Quality/Profitability/Momentum/Piotroski all
exists and works correctly on the 10-16 names it has — but 10-16 is
below the threshold this platform's own prior research (Financial
Coverage Expansion Audit §9) derived as necessary for real placebo/HAC
statistical power.

**4. What prevents proper cross-sectional testing**: breadth, exclusively
— not extraction quality (which is genuinely good where facts are
period-complete), not computation logic (which is built and correct).

**5. Whether the approved backfill should be applied**: **done.** Approved
by the operator and applied to production the same day this audit was
written, backed up first. Actual result: conclusions 267→403 (matching
the pre-tested projection exactly), computed-ticker coverage 10→**14**
(the real, `status='computed'`-filtered count — not the 16 originally
estimated, and not the 26 first misreported in conversation before being
corrected, which counted every ticker with *any* conclusion row
including unusable `insufficient_data` placeholders).

**6. Minimum coverage for credible NGX hypothesis testing**: 50 tickers ×
~5 years, per this platform's own already-derived standard (not
re-derived here) — reachable from the existing document backlog
(no new acquisition needed) at ~10-13 days of Gemini-quota-bound
extraction once the daily quota genuinely resets.

---

## H. Proposed minimum implementation

Ranked by leverage, smallest first — **none of this is authorized to
start by this audit; it is scoped for your decision**:

1. **A structured hypothesis schema** (the real, specific gap in §C.3):
   a new table (or an additive extension of `hypotheses`) with columns
   for `signal_definition`, `universe`, `entry_condition`,
   `holding_period`, `benchmark`, `validation_plan_ref` — populated
   initially by hand-translating the existing `research_task_candidates`
   backlog (84 open items, currently untouched) as a first real test of
   the pipeline, not a new document-generation feature.
2. **One connector**: a script/function that takes an
   `investment_implications` row with `action_recommendation='factor_candidate'`
   and drafts a row in the new structured-hypothesis table — closing the
   confirmed dead link in §C.2. This is the ONE piece of new code this
   audit would actually recommend, and it is small (a mapping function,
   not a new subsystem).
3. **Literature ingestion, if wanted at all, is the largest and lowest-priority
   item here** — a genuinely new capability (source acquisition, a new
   extraction schema distinct from the filing-extraction one, since a
   paper's "expected relationship"/"data requirements" fields don't map
   onto `extracted_facts`' numeric-fact shape). Given §G's coverage gap
   is the binding constraint on testing ANYTHING right now, literature
   ingestion has low near-term expected value regardless of how well it's
   built — you could feed it the entire academic factor-investing
   canon and it still couldn't be tested on NGX below 50-ticker breadth.

---

## I. Recommended execution order

1. **Approve or reject the backfill** (§G.5) — zero cost, sitting ready,
   already blocks the most tests.
2. **Resume quota-paced extraction** toward 50 tickers, using the
   existing backlog — the actual binding constraint on every downstream
   stage in the diagram.
3. **Only once coverage is real**: build the structured-hypothesis schema
   (§H.1) and the one connector (§H.2) — cheap, and pointless before
   there's enough data to test what it would produce.
4. **Literature ingestion last, and only if still wanted** after (1)-(3)
   — its value is capped by the same coverage ceiling until that's fixed.

This is the same "data breadth is the binding constraint, not
architecture" conclusion as the last two reports — restated here because
this audit's own findings (§C.2's zero-promotions discovery especially)
make it sharper, not because anything changed.

---

## J. Specific files/modules that would need modification (if H is authorized later — none touched today)

- `schema/registry.sql` — additive columns/table for structured hypothesis
  test definitions (§H.1).
- A new, small module — e.g. `src/ngxrot/documents/hypothesis_draft.py` —
  for the connector (§H.2). Would read `investment_implications`/
  `research_task_candidates`, write only to the new structured table;
  would NOT touch `extract.py`/`reasoning.py`/`alpha_engine.py`/
  `backtest_xs.py`.
- `scripts/fre/backfill_flow_fact_period_start.py --apply` — already
  built, already tested, the one item actually ready to execute today
  pending your approval (not a modification, a decision).

Nothing in `alpha_engine.py`, `engine_full.py`, `backtest_xs.py`, or the
portfolio layer needs to change for any of this — confirming your
instinct that the quant/portfolio machinery doesn't need rebuilding.

---

## K. What should explicitly NOT be built

- A new provider abstraction — exists, confirmed again.
- A new research/document schema — exists, confirmed again; only two
  narrow field-level gaps remain (management-statement type, catalyst
  type), not a new graph.
- A new portfolio layer — exists, untouched, ready.
- Sentiment scoring — would reverse a deliberate existing design
  decision; flag for an explicit yes/no from you, don't build by default.
- Literature ingestion before coverage is fixed — real capability gap,
  but building it now would be solving a problem that can't be acted on
  yet (§H.3/I.4).
- A new hypothesis-testing/backtest engine — `backtest_xs.py`/
  `engine_full.py` are already more sophisticated (placebo, regime,
  capacity, interactions) than this audit expected going in; do not
  duplicate.
- Any change to `alpha_engine.py`'s confirmed-only gate — it is already
  the exact CIO boundary you're asking for.

---

## Definitions — the five-way distinction, mapped to real objects in this codebase

| Term | What it means here | Real object |
|---|---|---|
| **Research intelligence** | Evidence-grounded understanding extracted from a document — a fact, a mechanism, a causal link | `extracted_facts`, `causal_chain_steps`, `impact_assessments`, `investment_implications` |
| **Investment hypothesis** | A claim about a repeatable relationship, stated in words, not yet formally testable | `research_hypotheses.statement`, or the `description` field of a hand-written `PREREG_H-*.md` before its formal sections are filled in |
| **Backtestable signal** | The SAME hypothesis translated into a precise, parameterized definition (universe, entry rule, holding period, benchmark) that a script can execute | **Currently only exists as prose** in `PREREG_H-*.md` §"Signal specification" — this is the missing structured layer (§C.3) |
| **Validated alpha** | A signal that has been run through `backtest_xs.py`/`engine_full.py`, survived placebo/regime/capacity checks, and is marked `confirmed` in the immutable `hypotheses` ledger | `hypotheses` where `status='confirmed'` — **exactly one exists today: H-011 (Size)** |
| **Portfolio decision** | A `confirmed` hypothesis's signal, sized and risk-checked into an actual position | `alpha_engine.Recommendation` → `portfolio/construction.py` → `portfolio/risk.py` — architecturally cannot happen without the row above existing first |

**Brutally honest summary, as requested**: this system has real,
working infrastructure at both ends of your diagram (document
understanding on one end, quant testing + portfolio construction on the
other) and a working example that the whole chain CAN close (H-011).
What it does not have is (a) the structured middle layer connecting
document-derived insight to a testable signal, which has never once been
exercised even manually, and (b) enough ticker breadth for that middle
layer to matter yet even if built today. Building (a) before fixing (b)
would produce infrastructure with nothing real to test — the same
mistake this platform's own prior audits have repeatedly caught and
corrected.
