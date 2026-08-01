# FRE Part 10 — Dataset Strategy

*Design/inventory only. No acquisition, no scraping, no dependency
installation performed by this document. Priority language follows the
charter's explicit rule (§ below). See `docs/fre/00_fre_master_index.md`
for standing rules.*

## Objective

Enumerate every dataset the Financial Reasoning Engine will eventually
need — across all fourteen other parts of this program — with purpose,
source, labels, collection method, estimated size, quality controls,
validation approach, priority, and maturity, so acquisition work can be
sequenced deliberately rather than discovered ad hoc mid-implementation.

## Priority language rule (inherited, restated because it applies directly here)

`docs/FUND_ALPHA_CHARTER.md`: *"No hypothesis is ever described as 'likely
to validate' before testing... Priority language must cite research
efficiency only: acquisition cost, dataset reuse, and time-to-verdict."*
This document applies the identical discipline to datasets: a dataset is
never prioritized because "it will probably make the reasoning engine
better" — only because of what it unlocks (how many FRE parts / hypothesis
families it feeds), its acquisition cost, and how much existing
infrastructure it reuses.

## Maturity vocabulary (fixed, reused across every row)

`not_started` → `probed` (a scoping/feasibility check has run, no data
acquired) → `partial` (some real data acquired, coverage incomplete or
unvalidated) → `validated` (acquired, quality-checked, in production use).

## Dataset inventory

| Dataset | Purpose | Source | Labels / fields | Collection method | Est. size | Quality controls | Validation | Priority | Maturity |
|---|---|---|---|---|---|---|---|---|---|
| **Financial statements (structured line items)** | Unlocks Parts 1 (`income_statement`/`balance_sheet`/`cash_flow`/`sector_ratio` nodes), 5 (earnings history), 7 (Financial/Growth quality fields), 8 (every valuation method) — the single highest-leverage dataset in this entire program | NGX filings (native-text subset first), possibly a commercial data vendor as a cross-check source | Revenue, COGS, opex, EBITDA/EBIT, net profit, EPS, balance-sheet lines, CFO/CFI/CFF, per period, per ticker | Extraction from native-text filings (reuses the existing OCR-gap-aware pipeline) + optional vendor cross-check, never vendor-only (primary-source-first discipline, unchanged) | Unknown until scoped — bounded above by ~7,399 native-text documents (Phase A), likely far fewer once filtered to statement-bearing filings | Deterministic extraction where possible (reuses Phase B's pattern); grounding check (existing `grounding.py`) for any LLM-assisted extraction | Cross-check against at least one independently-sourced anchor per sector (the same "GTCO/Zenith anchor" discipline already used in Phase B/C, generalized) | **Highest** — feeds the most other FRE parts of anything on this list | `not_started` |
| **Sector classification (`securities.sector_ngx`)** | Unlocks Parts 1/2/6/9's sector-conditioned logic (currently the single most-cited blocker across this whole program) | NGX-disclosed SIC-style classifications inside filings themselves (architecture doc §4.2 already names this as a "natural early win," not a separate harvest project) | One sector label per ticker | Entity-extraction side effect of processing existing filings — no new document source needed | 320 tickers | Human-reviewable merge/classification queue (existing entity-resolution pattern) | Cross-check against NGX's own published sector groupings (a primary source, likely already accessible) | **High** — cheap (no new document source), unlocks disproportionately many downstream parts | `not_started` |
| **Shares outstanding / float-adjusted size** | Unlocks a real (not full-issue-only) market-cap panel; feeds Part 2's ownership-concentration ranking and any future Size-factor refinement | NGX filings (existing backlog item, `HANDOFF.md`) | Shares outstanding per period, free-float % where disclosed | Same filing archive, a targeted extraction pass | Bounded by existing archive | Implied-share-count stability check (same methodology already used for the existing full-issue market-cap panel) | Cross-check against the existing full-issue panel for consistency | Medium — named in the existing quant-engine backlog already, this document does not newly invent the need | `not_started` |
| **Substantial-shareholding / ownership notices** | Part 2's `major_shareholder_of` edges, Part 7's ownership-related risk flags | NGX filings (substantial-shareholding disclosure notices) | Shareholder name, percentage, ticker, effective date | New `fact_taxonomy.toml` leaf + extraction (Part 2 already specifies this) | Unknown, likely small (disclosure notices are infrequent per company) | Human-reviewed given financial sensitivity (Part 2's explicit, elevated review-bar flag) | Cross-check against a sample of independently-known major shareholders (e.g., publicly disclosed founder/institutional stakes) | Medium | `not_started` |
| **News corpus + `news_outlets` reliability registry** | Unlocks the News Understanding Engine and Part 6's cross-document News tier | New harvest (no existing archive); `news_outlets` registry is owner-judged, not harvested | Article text, publish date, outlet, ticker/entity mentions | New `NewsDocumentProvider` (architecture doc §4.1, not yet built) | Unbounded/ongoing | Per-outlet `reliability_tier` (owner-set, never AI-inferred) | Corroboration-based (Part 6's cross-document mechanism is itself the validation path — a news claim with no filing corroboration is flagged, not silently trusted) | Medium — real value but requires an owner-judgment step (the registry) that cannot be automated first | `not_started` |
| **Macro/industry reports (NBS, SEC, sector bodies)** | Feeds Part 1's macro ontology's `ngx_confirmed`/`ngx_rejected` evidence trail with primary macro narrative, not just series data | Public bodies (NBS, SEC Nigeria, sector associations) | Report text, publish date, topic | `MacroDocumentProvider` (architecture doc §4.1, "probe only" status per the 2026-07-15 acquisition plan — unchanged) | Unknown, not yet probed | Native-text extraction where available | n/a until acquired | Medium, inherited unchanged from the existing acquisition plan's own framing | `probed` |
| **Analyst research** | Part 6's Analyst Notes source type | Third-party providers, **legally gated** | Report text, rating, target (if disclosed) | `AnalystResearchProvider`, explicitly not a general harvest target | n/a | n/a until licensing resolved | n/a | **Blocked on a legal/licensing decision, not an engineering priority question** (architecture doc §13, unchanged) | `not_started`, gated |
| **Earnings call transcripts** | Part 6's Historical Filings analog for verbal disclosure | NGX issuers — **open finding: most NGX issuers do not hold transcribable analyst calls** (architecture doc §4.1, unresolved) | n/a until the availability question is answered | `TranscriptDocumentProvider`, generic/future-exchange-oriented today | n/a | n/a | n/a | Low for NGX specifically until the availability scoping task (already named, not yet done) resolves; the provider stub is built for future non-NGX exchanges | `not_started`, blocked on a scoping task |
| **Press releases (as a distinct `doc_type`)** | Part 6 flagged this as possibly-already-covered-but-unconfirmed by the existing xissuer feed | Existing archive (likely) or a new source (unconfirmed) | n/a — this is a classification/scoping task, not a new harvest, pending Part 13's gap analysis | Re-classify existing archive by `doc_type`, or scope a new provider if truly absent | n/a | n/a | n/a | Low-cost to resolve (a scoping check, not a harvest) — resolve before assuming either way | `not_started` |
| **Investor presentations (`doc_type` split)** | Same archive, currently unclassified by type at the granularity this program needs (architecture doc §4.1) | Existing xissuer archive | `doc_type` label only | A classification pass over already-archived documents — zero new harvesting | Bounded by existing archive | n/a (classification, not extraction) | Spot-check against a manually-labeled sample | Low-cost, high reuse — should be sequenced early given near-zero acquisition cost | `not_started` |
| **Ontology-edge evidence log** (Part 1) | Keeps `evidence_status` current as `docs/FACTOR_REGISTRY.md` grows | The registry itself — a **process**, not a harvested dataset | Edge ↔ hypothesis-ID mapping | Manual curation, triggered by every new hypothesis verdict (Part 12 roadmap item) | Small (one row per tested mechanism) | Owner/analyst-curated, matching the registry's own curation discipline | Cross-checked against the registry text directly (same source, no separate validation needed) | Low acquisition cost, high leverage for Part 1/4/6's macro-mode guardrails | `not_started` |
| **Strategy-narrative comparison gold set** (Part 5) | A human-reviewed evaluation set for the strategy-shift-detection capability, needed before that capability can be trusted at all (Part 11 will need this to evaluate it) | Analyst-reviewed pairs of narrative excerpts across periods, same ticker | (excerpt_A, excerpt_B, human-judged: shift/no-shift, rationale) | Human annotation, small and deliberately curated — the same "gold set used sparingly and last" philosophy `docs/LIM_ARCHITECTURE.md` §3.3 already established for LIM training | Small (tens of pairs, not hundreds) | Analyst-authored, inherently the quality control | n/a (this dataset IS the validation mechanism for Part 5's riskiest capability) | Medium — required before Part 5's strategy-narrative feature can be evaluated, not before it can be designed | `not_started` |
| **Company lineage (mergers/demergers)** | Extends the existing, owner-verified `symbol_renames.csv` (renames only) to mergers/demergers (Part 2) | Filing-derived entity extraction, human-reviewed merge queue | (entity_A, entity_B, relation_type, effective_date) | Reuses the existing entity-resolution queue mechanism, no new pipeline | Small — corporate mergers/demergers are infrequent events | Human-reviewed before any merge (existing discipline, restated) | Cross-check against NGX's own delisting/listing announcements | Low-medium | `not_started` |

## Alternatives considered

1. **Acquire everything opportunistically as each FRE part needs it,
   without a consolidated inventory.** Rejected — this is exactly the
   pattern the charter's priority hierarchy exists to prevent (level-5
   single-hypothesis-driven acquisition outranking level-2/3
   multi-candidate-feeding acquisition); a consolidated view lets the
   highest-leverage dataset (financial statements) be correctly identified
   as the priority even though no single FRE part "needs" it most urgently
   in isolation.
2. **Treat a commercial data vendor as the default source for financial
   statements, skipping primary-source extraction.** Rejected as the sole
   approach — violates the platform's standing "primary sources for dates,
   archive-first" rule; a vendor feed is acceptable as a **cross-check**,
   never as the sole source of truth, consistent with how the DOL/pricelist/
   gainers sources are already cross-verified against each other today.

## Trade-offs

- The financial-statements dataset is simultaneously the highest-leverage
  and highest-cost item on this list (likely requiring either a dedicated
  OCR investment or a vendor relationship) — sequencing it first is a real
  resource commitment, not a free win, and Part 12's roadmap must treat its
  acquisition as its own gated phase with its own review checkpoint, not an
  assumed prerequisite waved through.
- Several low-cost items (sector classification, investor-presentation
  `doc_type` split) are cheap precisely because they reuse already-archived
  data — sequencing these early is close to strictly positive-value, and
  the roadmap should not let them wait behind the expensive financial
  -statements effort merely because that item is "priority 1."

## Risks

- **OCR coverage remains the platform's oldest, still-unresolved blocker**
  (Phase A's 4,134/11,533 OCR-pending documents, an open decision since
  2026-07-16) — every text-dependent dataset on this list inherits this
  risk; this document does not resolve it, only flags that it compounds
  across nearly every row above.
- **News/analyst datasets carry real reputational and legal risk if
  reliability tiering or licensing is rushed** — both are explicitly
  owner-gated for this reason, not an oversight.
- **A financial-statements vendor relationship, if pursued, introduces a
  new third-party dependency and cost** — outside this document's scope to
  resolve, flagged for Part 14's risk assessment.

## Future extensions

- A per-dataset "hypothesis families unlocked" count, computed once the
  ontology (Part 1) and factor-family map (`HYPOTHESIS_FAMILY_MAP.md`,
  existing) are cross-referenced — would let this table's priority column
  become a real, countable metric instead of a qualitative High/Medium/Low
  label.

## Dependencies

- Every dataset row above is itself a dependency of one or more of Parts
  1-9; this document is the single place that inventory is made explicit,
  cross-referenced from each part's own "Dependencies" section rather than
  restated in full there.
- `docs/DATA_ACQUISITION_PLAN.md` and `docs/PHASE1_DATA_GAPS.md` (existing,
  quant-engine-focused) — this dataset strategy is scoped to FRE-specific
  needs and should be read alongside, not instead of, those documents for
  the platform's full acquisition picture.
