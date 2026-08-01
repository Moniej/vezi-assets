# FRE Part 5 — Company Memory

*Design only. A read-only aggregation layer over existing append-only
tables (`documents`, `events`, `extracted_facts`, `investment_implications`,
Part 2's lineage edges) — no new system of record. See
`docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Give every reasoning call access to a company's **longitudinal record** —
filing history, earnings/dividend/capital-allocation pattern, management
and strategy history, and cyclical sector behaviour — as a single,
PIT-safe, queryable object, the same way `context.build_reasoning_context()`
already assembles a *point-in-time snapshot* for a single reasoning call
(Phase E). Company Memory is that context object's longitudinal
counterpart: not "what do we know right now," but "what has this company's
pattern been over time, as of a given date."

## Rationale — this closes a gap Part 3 already surfaced

Part 3's Evidence Graph worked example for "Statement of Changes in
Equity" explicitly named the missing piece: "Capital-allocation *pattern*
over multiple periods is the real signal — a single period is weak
evidence... 'How does this compare to the company's 5-year
capital-allocation pattern?'" That question has no answer today because
nothing aggregates `extracted_facts`/`events` across time into a
per-company narrative. Company Memory is the direct, purpose-built answer
to that named gap — not a speculative "nice to have."

## Design: a `CompanyMemory` object, not a new table

Following the exact precedent `context.py`'s `ReasoningContext` already
set (Phase E): a Python object assembled by **read-only queries** over
existing tables, filtered `as_of` a given date using the same PIT
discipline every quant-engine reader already uses (`db.py`'s `*_asof`
convention, latest-vintage-wins). This is a deliberate, non-negotiable
design constraint: **a memory object built without PIT filtering would
introduce look-ahead bias into every reasoning call that uses it** — the
single most consequential architectural mistake this document could make,
given how central "never fabricate, primary sources, append-only PIT" is
to this platform's charter. `CompanyMemory.as_of(ticker, date)` must refuse
to include any document/fact/event with `filing_date`/`announced_date` >
`date`, exactly like every existing PIT reader.

```
CompanyMemory:
    ticker, as_of_date
    filing_history: list[DocumentSummary]            # from `documents`, filtered by ticker
    dividend_history: list[DividendEvent]             # from existing Phase B deterministic
                                                        # extractor output — REAL data today
    corporate_action_history: list[CorporateActionEvent]  # from `events` + `extracted_facts`
    management_history: list[ExecutiveTenure]          # from Part 2's `executive_of` lineage edges
    strategy_narrative_timeline: list[NarrativeSnapshot]   # NEW derived layer, see below
    major_event_history: list[Event]                   # from `events`, unchanged
    coverage_note: str                                  # explicit disclosure of gaps, see below
```

## Component-by-component: what's real today vs. genuinely new

| Component | Status | Source |
|---|---|---|
| **Filing history** | Real today, zero new extraction — a filtered `documents` query | Phase A's 11,533 archived documents |
| **Dividend history** | Real today — the *only* component of this whole list with a validated, 100%-passing extractor already in production | Phase B's `build_extracted_facts_deterministic.py`, 141 dividend facts, `validate_extracted_facts.py` PASS |
| **Corporate action history** (buybacks, rights issues) | Partially real — the corp-actions archive itself is 97% complete (`HANDOFF.md`), but only dividend/rights/bonus fact types have a working deterministic extractor; buybacks are not yet extracted | Phase B (partial), Part 1's `corporate_action` ontology nodes for typing |
| **Management history** | Not yet populated — depends on Part 2's `executive_of` lineage edges, which depend on `management_change` fact extraction (an existing `fact_taxonomy.toml` leaf, not yet run against real filings at volume) | Part 2, dependent |
| **Strategy narrative timeline** | **Genuinely new, not a simple aggregation** — see below | New |
| **Major event history** | Real today — the existing `events` table already holds hand-curated MPC/regulatory events plus whatever AI-detected events exist post-Phase-F | `events`, unchanged |

## Strategy narrative timeline — the one genuinely new capability

"Strategy shifts" and "cyclical behaviour" are not queries over structured
facts; they require comparing **qualitative narrative text across
periods** (Part 3's "Chairman's/MD's Statement" evidence row) — e.g.,
detecting that a company's stated strategic priority moved from "capacity
expansion" in 2021 filings to "cost discipline" in 2024 filings. This is
the hardest, most speculative component in this document, and is designed
with three explicit constraints:

1. **Never auto-detected as a silent inference.** A "strategy shift"
   candidate is generated by comparing two `extracted_facts` rows sourced
   from narrative sections (already capped at lower `extraction_confidence`
   per Part 3), and is written as a `NarrativeSnapshot` with **both**
   source quotes attached (an `evidence_id` pair, not one) — the reasoning
   engine's answer to "why do you think strategy shifted" must always be
   "compare these two direct quotes," never a bare assertion.
2. **Never presented above `unvalidated_ai_interpretation` status.** This
   is squarely the softest evidence class in the whole FRE design (Part 3's
   qualitative-node caution from Part 1 applies here directly) — a strategy
   -shift claim is exactly the kind of conclusion the self-critique gate's
   `ignored_alternative_explanation` question should scrutinize hardest
   (maybe the language changed because of a new investor-relations writer,
   not a real strategic pivot).
3. **Cyclical behaviour classification reuses Part 1's ontology, not a new
   taxonomy.** "This company's revenue is cyclically sensitive to the
   construction cycle" is a `sector_ratio`/`macro` ontology claim (Part 1)
   applied longitudinally — Company Memory's job is to supply the
   multi-period evidence (revenue trend across at least one full observed
   cycle) that the ontology's `causal` edge needs to move from
   `theoretical` to `ngx_confirmed`/`ngx_mixed` `evidence_status`, not to
   invent a separate cyclicality concept.

## Coverage honesty — "10+ years" is a target, not an assumed fact

The owner's brief asks for 10+ years of filings support. **This document
does not assume that depth exists uniformly.** Real per-ticker filing depth
varies (older filings are more likely OCR-only/scanned, per Phase A's
disclosed 4,134/11,533 OCR-pending count) — `CompanyMemory.coverage_note`
is a **mandatory, explicit field** stating the actual observed depth and
gap pattern for that specific ticker (e.g., "6 years of native-text
filings, 3 additional years OCR-pending, 2 years with no archived filing
found") — never a silent assumption of full historical depth. This
directly extends `coverage_assessment.py`'s existing "10-dimension
mechanical coverage checklist" (built in the stabilization pass) with an
eleventh, longitudinal-specific dimension: **historical depth coverage**.

## Alternatives considered

1. **A dedicated `company_memory` materialized table, refreshed on a
   schedule.** Rejected for now — adds a caching-invalidation problem
   (append-only source tables mean the memory view is always
   reconstructable on demand; materializing it risks a stale view being
   read after a new document lands) that a plain, always-fresh query object
   avoids. Revisit only if query latency becomes a real, measured problem
   (not assumed) once real volume exists — flagged as a future extension,
   not built preemptively (same "no need pre-exists" discipline the
   architecture doc's §5 already applied to the graph-database question).
2. **Store strategy-shift conclusions as first-class `investment_implications`
   rows immediately.** Rejected — conflates a genuinely different evidence
   class (cross-period narrative comparison) with the single-fact
   implication schema; instead, a confirmed strategy-shift narrative
   becomes an `extracted_facts`-linked observation that *feeds into* a
   normal Step 1-14 reasoning call when relevant, not a shortcut around it.
3. **Infer cyclicality purely from price data (the quant engine already has
   sector/price time series).** Rejected as the *sole* mechanism — price
   cyclicality is a different, already-answerable question via the
   existing research engine (a legitimate hypothesis-testable claim, e.g.
   "is NGXINDU return cyclically correlated with a construction-activity
   proxy"), not a Company Memory concept; Company Memory's contribution is
   specifically the *narrative and fundamental* evidence trail, kept
   distinct from — and never presented as a substitute for — a properly
   tested quantitative hypothesis.

## Trade-offs

- PIT-correctness adds real query complexity (every component must respect
  `as_of_date`) in exchange for avoiding a categorical, charter-level
  mistake (look-ahead bias) — non-negotiable, not really a trade-off in
  practice.
- The strategy-narrative timeline is the highest-value, highest-risk
  component on this list — most useful for exactly the kind of long-horizon
  qualitative judgment an institutional analyst provides, and also the
  easiest component to get wrong in a way that sounds authoritative. This
  tension is resolved by keeping it maximally evidence-quoted and
  confidence-capped rather than by avoiding the capability altogether.

## Risks

- **Survivorship/attention bias in filing archives** — companies that later
  delisted or were suspended may have systematically thinner archived
  history, which could make Company Memory silently "explain" a company's
  eventual failure less well than a company that is still actively filing.
  Disclosed, not solved — `coverage_note` should flag unusually sparse
  recent history as a coverage gap, not silently degrade.
- **Narrative-comparison false positives** (see constraint 1-3 above) — the
  primary mitigation is structural (mandatory dual-quote evidence,
  confidence ceiling), not a promise of accuracy.

## Future extensions

- A **management track record** score (Part 7's Investment Thesis Engine
  input) — did prior stated strategy shifts, once identified, correlate
  with subsequently realized outcomes? This is itself a testable
  hypothesis once enough history accumulates, feeding the Discovery-scanner
  path exactly like any other candidate — never asserted directly.
- Cross-company strategy-narrative comparison (do sector peers describe
  similar shifts at similar times — a macro/sector transmission signal) —
  deferred until single-company narrative timelines are validated.

## Dependencies

- `documents`, Phase B's dividend extractor, `events` (all existing,
  unchanged). Part 2's lineage edges for management history. Part 1's
  ontology for cyclicality typing. `coverage_assessment.py` (existing,
  extended by one dimension). PIT discipline (`db.py`'s `*_asof`
  convention, existing, unchanged, non-negotiable).
- A working buyback extractor (not yet built — a real, disclosed, small
  gap distinct from the already-working dividend/rights/bonus extractors).
