# FSI Phase 14 — Evidence-Based Screening (Pre-registration)

*Design document, immediately followed by implementation per the owner's
continuous-execution operating mode (per-phase approval checkpoint
disabled for this track, restated 2026-08-02). Builds on
`fsi-phase13-baseline-2026-08-02` and modifies nothing in Phases 1-13 —
all thirteen remain frozen, touched only for future bug fixes.*

## 1. Architecture review

**FRE-1 through FRE-6, FSI Phase 1-13**: all frozen, unchanged. 10 real
tickers (5 original + MTNN/DANGCEM/UBN/OANDO/NESTLE from Phase 13), 298
extracted_facts, 267 financial_reasoning_conclusions (125 ratio + 112
trend + 30 flag).

**Part 9 (`docs/fre/09_portfolio_reasoning.md`, frozen since
`fre-architecture-baseline-2026-08-01`)** already designed exactly this
capability in full, under its own Tier-1/Tier-2 split: **Screening**
("descriptive filtering over already-produced research, structurally
identical to a SQL `WHERE` clause... never computes or implies an
expected return") is explicitly Tier 1 — "not gated," buildable now,
because it filters already-governed research rather than producing a new
claim. Never implemented. **Real, disclosed correction to Part 9's own
example**: its screening example cites `CompanyThesis.financial_quality`/
`.growth_quality`/`.capital_allocation_quality` fields — confirmed by
direct grep of `company_thesis.py` and `company_thesis_360.py` that NONE
of these fields exist in the actual, later-built implementation (Phase
5/8 took a more conservative design: `concern_evidence`/`supplementary_
evidence` built from fired health flags and trend directions, not a
quality-score triple). This phase screens over the REAL fields that
exist — `financial_reasoning_conclusions`' own `metric`/`conclusion_
type`/`status`/`value_text` (direction) columns via Phase 4's `pit_
financial_memory.as_of()` — not the hypothetical fields Part 9 imagined
before Phase 3-13 were built.

**Every module built in this program (Phase 3 through 13) enforces a
mechanically-tested single-ticker-scope guardrail** (`inspect.signature`:
no function accepts more than one `ticker`-named parameter). This phase
proposes the FIRST function in the entire program that legitimately
operates across ALL tickers at once — by design, not by accident, since
Part 9's own Tier 1 explicitly authorizes exactly this ("Watchlists,
Screening... buildable now"). This requires its OWN, different guardrail
(not "at most one ticker," but "never ranks/scores/sorts by value, never
accepts a numeric threshold, never outputs an aggregate statistic") —
designed in Section 5 below.

**Knowledge graph coverage for the 5 Phase-13 tickers remains empty**
(disclosed, unchanged since Phase 13) — irrelevant to this phase, since
screening operates over `financial_reasoning_conclusions`, not the graph.

## 2. Explicit evaluation of the six named categories (per the operating-mode instruction)

**Data Intelligence Expansion**: real remaining opportunity (39 of 49
scoped candidate tickers still unused; balance-sheet/cash-flow deferred
for the 5 Phase-13 tickers) — but this is MORE of the same validated
extraction work, not a new capability, and was just exercised in Phase
13. Not proposed here.

**Financial Intelligence**: Phase 3's 3 flags + 5 ratios already cover
the core "quality" dimensions (leverage, margin, cash-flow/earnings
divergence) mechanically and PIT-safely. A genuinely NEW financial-
intelligence flag (e.g. a 4th health-flag type) is possible but is
incremental extension of an already-frozen rule set, lower architectural
leverage than closing Part 9's own long-standing, fully-designed,
zero-risk gap.

**Knowledge Graph Maturity**: blocked by the same real data gaps named in
every prior review (`sector_ngx` 0/320, `index_membership` synthetic,
zero real relationships beyond 4 renames) — unchanged, not re-derived
here.

**Research Workflow**: THIS is where Screening lands. Every research
object built so far (Company Memory, Thesis, Dossier, CLI) requires
already knowing WHICH ticker to look up. With 10 tickers now (Phase 13),
this gap is more consequential than it was on 5 — a researcher has no way
to ask "which of my 10 companies currently show a leverage concern?"
without checking each one individually.

**Evaluation System**: Part 11's own framework needs an analyst-authored
gold set (strategy-narrative cases) — a genuine dependency on owner/
analyst-level input this session cannot fabricate. Real, but not
executable as a self-contained phase today without that input.

**Production Infrastructure**: explicitly excluded from this session's
own continuous-execution scope, per the standing disclosure — not
evaluated as a candidate.

## 3. The single highest-value remaining bottleneck

**Cross-ticker research retrieval.** Part 9's own architecture already
named and fully designed this exact capability over a year before FSI's
extraction/reasoning tracks existed to feed it — a rare case where the
"why" is already written and frozen, only the "build it" step remains.
With the ticker roster now at 10 (Phase 13) and growing, the value of
"find candidates without manual per-ticker lookup" grows directly with
coverage — this is the first FSI capability whose value compounds with
Phase 13's own expansion, rather than needing yet another new dataset.

## 4. Objective

Build `src/ngxrot/fre/screening.py`: two read-only functions,
`screen_by_flag(con, flag_metric, fired, as_of_date)` and
`screen_by_trend(con, metric, direction, as_of_date)`, each iterating
over every real ticker (via `financial_ratios.list_tickers()`, already
proven across Phase 3-13), calling Phase 4's `pit_financial_memory.
as_of(ticker, as_of_date)` per ticker (PIT-safe by construction, zero new
gating logic), and returning only tickers whose PIT-visible conclusions
match the given categorical criterion — in a fixed, disclosed, non-value
order (alphabetical by ticker), never sorted by magnitude.

## 5. Guardrails (the load-bearing design decision this phase makes)

To stay inside Part 9's own Tier-1 boundary and never drift toward
Tier-2 (ranking/scoring/sizing), this phase deliberately:

- **Accepts only categorical filter values** — a flag's `fired` boolean,
  or a trend's `direction` enum (`increasing`/`decreasing`/`stable`) —
  NEVER a numeric threshold on a ratio value (e.g. "margin below X%").
  A numeric-threshold screen is a real, common finance use case, but
  introduces exactly the kind of value-based cutoff that could function
  as an implicit score; excluding it entirely is the conservative choice
  consistent with "boring correctness over impressive speculation."
- **Never accepts** a `limit`/`top_n`/`sort_by`/`rank_by`/`weight`
  parameter in either function's signature — mechanically checked.
- **Always returns results in alphabetical-ticker order** — mechanically
  checked against Python's own `sorted()`, the same neutral-ordering
  discipline `render_report()` (Phase 7) already established for
  conclusions.
- **Computes no aggregate** (no count-weighted summary, no "average
  across matching tickers") — each result is an independent, individually
  evidence-linked row, never rolled up.
- **Never imports, and is never imported by,** `alpha_engine.py`,
  `runner.py`, or any portfolio-construction module — verified by the
  same mechanical import-graph check Part 9 itself names as FRE-9's own
  Tier-1 verification mechanism. This phase deliberately does NOT build
  Part 9's separate "Portfolio memory cross-reference" sub-capability
  (the one Tier-1 item that DOES read `alpha_engine.py`'s live sleeve) —
  left for a future, separately-scoped phase, keeping this phase's own
  risk surface to a single new boundary (cross-ticker read), not two.
- **The result dataclass carries no score/rank/weight field** — only the
  matched ticker, the matching conclusion's own existing fields (metric,
  status, value_text/value_numeric, confidence_tier, method,
  limitations), verified by direct dataclass introspection, the same
  check used in every prior FSI phase.

## 6. Alternatives considered

1. **Watchlist (Part 9's other Tier-1 item).** Real and also authorized,
   but requires a new persisted table (`WatchlistEntry`) and a
   stated-in-advance `entry_criteria` workflow — larger design surface,
   a write path, and a "who curates it" question this session cannot
   answer for the owner. Screening is the smaller, purely-read, zero-
   persistence Tier-1 item; a natural Phase 15 candidate once Screening
   is proven.
2. **Sector-coverage view (Part 9's third Tier-1 item).** Blocked on
   `securities.sector_ngx` (0/320 populated) — same standing gap named in
   every prior review.
3. **A new Phase 3 health-flag type (Financial Intelligence).** Rejected
   as this installment's choice — incremental extension of an
   already-mature, already-frozen rule set, versus closing a
   fully-designed, zero-new-risk architectural gap that grows in value
   with every future coverage-expansion phase.
4. **Evaluation framework operationalization (FRE-10).** Rejected — needs
   an analyst-authored gold set this session cannot fabricate without
   the owner's own domain judgment; attempting it without that input
   would risk exactly the "harness that passes everything regardless of
   quality" failure FRE-10's own roadmap entry names as its single worst
   failure mode.
5. **Extend Phase 13's coverage expansion to more tickers.** Rejected —
   legitimate future work, but more of the same validated extraction
   work just completed, not a new capability; the operating-mode
   instruction explicitly deprioritizes "more complexity/novelty" in
   favor of the highest-leverage gap, and a zero-risk, fully-pre-designed
   capability gap (this one) outranks incremental data growth.

## 7. Dependencies

`src/ngxrot/fre/financial_ratios.py`'s `list_tickers()` (proven across
Phase 3-13, now returns all 10 real tickers); `src/ngxrot/fre/pit_
financial_memory.py`'s `as_of()` (Phase 4, frozen, PIT-safe by
construction); `financial_reasoning_conclusions`' existing `metric`/
`conclusion_type`/`status`/`value_text` columns (Phase 3, frozen schema).
No schema change.

## 8. Risks

- **Screening could be misread as an implicit ranking if results were
  ever ordered by anything but ticker name** — mitigated by the
  alphabetical-order guardrail (Section 5), mechanically tested, not
  merely documented.
- **A future phase could be tempted to add a numeric-threshold filter
  parameter "just this once"** — this pre-registration's own Section 5
  explicitly forecloses that for THIS phase; any future numeric-threshold
  screen would need its own separate pre-registration and its own
  explicit risk analysis, not a quiet parameter addition here.
- **Scope-selection risk, restated as in every prior phase**: this
  document's own topic choice may not match the owner's actual intent —
  flagged explicitly, redirection expected if wrong.

## 9. Success criteria

- `screen_by_flag()` and `screen_by_trend()` correctly identify every
  real, currently-fired flag / currently-classified trend direction
  across all 10 tickers, verified against a direct SQL query of
  `financial_reasoning_conclusions` (not just internal self-consistency).
- PIT correctness: a screen run `as_of` a date before a ticker's
  qualifying conclusion was filed must NOT include that ticker — verified
  against at least 2 real filing-date boundaries (reusing Phase 4's own
  established boundary-testing pattern).
- Zero database writes. Zero LLM calls. Zero new schema.
- Mechanical guardrail tests pass: no numeric-threshold/limit/sort/rank
  parameter in either function signature; alphabetical output order;
  no score/rank/weight field in the result dataclass; no import of/by
  `alpha_engine.py` or `runner.py`.
- Full regression suite (24 test files after this phase) and Phase 5's
  validation harness both still pass.

## 10. Failure criteria

- Any screening result includes a ticker whose matching conclusion was
  not yet PIT-visible as of the given date — a look-ahead violation,
  treated with the same severity as any other PIT defect on this
  platform, stop and report immediately.
- Any accidental value-based ordering or aggregate statistic in the
  output — redesign before proceeding, not a cosmetic fix.

## 11. Implementation boundaries

**In scope**: `src/ngxrot/fre/screening.py` (two functions, as described);
a dedicated test file with the mechanical guardrail checks plus PIT/
correctness verification; full regression re-run; implementation log and
final report; commit and tag `fsi-phase14-baseline-<date>`.

**Out of scope, explicitly**: numeric-threshold screening; Watchlist
persistence; sector-coverage view; Portfolio-memory cross-reference to
`alpha_engine.py`; any modification to any of the thirteen frozen FSI
phases' own code; any valuation, ranking, scoring, alpha claim, or
recommendation.

---

*Per the owner's continuous-execution operating mode, implementation
proceeds immediately following this pre-registration.*
