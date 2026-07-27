# Fund Alpha — Reasoning Engine Specification

*2026-07-22, revision 2 (adds the mandatory self-critique gate, §12).
Design document only — no code written against it, no LLM call made. This
is the detailed operating specification for the "reasoning" step that
`docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md`'s §4.5 described abstractly
(Financial / News / Macroeconomic / Industry Reasoning Engines, sharing
one schema). It supersedes §4.5's `reasoning` and `investment_implications`
DDL sketches with a richer schema — those tables held zero rows as of this
writing (Phase A only populated `documents`/`entities`/`entity_mentions`),
so this is a revision, not a migration. Everything in §11 of the
architecture doc (the governance recap) still applies unchanged; this
document adds mechanism, not new authority. No document has been analyzed
yet — this is the contract the reasoning engines must fill in once Phase D
starts, not a completed analysis.*

## 0. What this document is for

The owner's directive frames the reasoning engine as an institutional
analyst, not a summarizer: every document must be pushed through a fixed
13-step reasoning chain that terminates in a specific question — *does
this change the expected future value of this company?* — never in a bare
sentiment label. A 14th step, added by owner follow-up, requires the
engine to challenge its own conclusion before anything counts as usable —
the same way an investment committee challenges an analyst's thesis before
acting, rather than trusting the analyst's first draft (§12). This
document turns that mandate into: (a) a fixed process every reasoning
engine call must execute, in order; (b) a storage schema that can hold the
OUTPUT of that process without collapsing it back into a summary; (c) a
set of MECHANICAL checks (not just instructions to a model) that enforce
"never say X without explaining why."

**Restated governance boundary (unchanged from the architecture doc,
repeated here because this document's richer outputs — "Hypotheses
Created," "Portfolio Implications" — are exactly the kind of output that
could be misread as authoritative if this weren't restated):** nothing
this engine produces is a validated factor or a portfolio action.
"Hypotheses Created" means a row lands in the Discovery-candidate queue
(`discovery_feed.py`, unchanged); it becomes H-012+ only after
pre-registration and the full gauntlet. "Portfolio Implications" means a
labeled research note; Portfolio Construction remains GATED behind ≥2
validated independent factors, exactly as today.

## 1. The 14-step reasoning chain (mandatory process, in order)

Every document, of every type, executes all 14 steps. A reasoning engine
that skips a step (e.g., states duration without magnitude, or skips the
self-critique gate before a row is treated as usable) has produced an
incomplete record, not a valid one — enforced by the schema in §3 (most
fields are `NOT NULL`) and, for step 14, by a status that blocks
downstream consumption until the gate passes (§12).

| Step | Question | Where it's stored |
|---|---|---|
| 1. Identify | company, sector, exchange, country, doc type, publication time, event date | `documents` (extended, §2) |
| 2. Extract facts | every material fact, using the fact taxonomy (§4) — nothing important ignored | `extracted_facts` |
| 3. Recursive "why" | keep asking why until reaching the economic reason (factory → production → sales → revenue → earnings → intrinsic value) | `causal_chain_steps` |
| 4. Impact by category | 14 fixed categories (§5), each positive/negative/neutral/mixed/unknown + explanation | `impact_assessments` |
| 5. Duration | Very Short / Short / Medium / Long / Structural / Permanent | `investment_implications.duration_bucket` |
| 6. Magnitude | Tiny / Small / Medium / Large / Transformational | `investment_implications.magnitude` |
| 7. Confidence | 0-100% + an explicit uncertainty explanation (never a bare number) | `investment_implications.confidence` + `confidence_rationale` (NOT NULL) |
| 8. Causal chain (full) | the complete arrow-chain from fact to intrinsic value | `causal_chain_steps` (same table as step 3 — step 3 is this chain's construction, step 8 is stating it complete) |
| 9. Thesis/valuation deltas | bull case, bear case, base case, intrinsic value, expected earnings, target multiple, risk profile, portfolio sizing | `investment_implications` (extended fields, §3) |
| 10. Action classification | No Action / Watchlist / Research Task / Model Update / Valuation Update / Factor Candidate / Immediate Review | `investment_implications.action_recommendation` |
| 11. Cross-reference | has this happened before, how often, what happened, does it strengthen/weaken prior evidence | `investment_implications.corroborates_implication_id` + reuse of existing event-study machinery (§7) |
| 12. Consistency check | contradiction detection, reliability comparison, **version don't overwrite** | `investment_implications.contradicts_implication_id` + `consistency_note`, append-only (§8) |
| 13. Structured output | the full record assembled from steps 1-12 | one `investment_implications` row + its linked `impact_assessments`/`causal_chain_steps`/`effect_chains`/`research_task_candidates` rows |
| 14. Self-critique gate | challenge the step-13 draft before it counts as usable — unevidenced inference? correlation vs. causation? ignored alternative? single-document overreaction? contradicts prior evidence? enough information? what would raise confidence? is this just noise? | `self_critique_reviews` (§12); a failing gate blocks the implication's `status` from progressing |

## 2. Step 1 — Identification (extends `documents`)

Additive columns on the existing `documents` table (Phase A already
populated 11,533 rows without these — additive `ALTER TABLE ADD COLUMN`,
same pattern as every prior migration in `db.py`):

```sql
ALTER TABLE documents ADD COLUMN sector TEXT;              -- securities.sector_ngx once populated
ALTER TABLE documents ADD COLUMN exchange TEXT DEFAULT 'NGX';
ALTER TABLE documents ADD COLUMN country TEXT DEFAULT 'NG';
ALTER TABLE documents ADD COLUMN event_date TEXT;          -- when the underlying event HAPPENED,
                                                            -- distinct from filing_date (when disclosed)
ALTER TABLE documents ADD COLUMN news_classification TEXT  -- populated for source_type='news' only
    CHECK (news_classification IN ('noise','narrative','catalyst','fundamental_change',
        'structural_change','temporary_shock','liquidity_event','sentiment_event',
        'information_event','macro_event','micro_event','false_signal',
        'market_overreaction','market_underreaction','unknown'));
```

`exchange`/`country` default to NGX/NG today but exist precisely so a
future non-NGX `DocumentProvider` (§10 of the architecture doc) needs no
schema change — this is the Module 12 (multi-exchange) requirement
satisfied at the identification step, the earliest possible point.

## 3. Steps 2-13 — the full schema

```sql
-- Step 2: every material fact, one row per fact, using the taxonomy in §4.
CREATE TABLE IF NOT EXISTS extracted_facts (
    fact_id               INTEGER PRIMARY KEY,
    doc_id                INTEGER NOT NULL REFERENCES documents(doc_id),
    fact_type             TEXT NOT NULL,       -- configs/fact_taxonomy.toml leaf
    description           TEXT NOT NULL,
    evidence_id           INTEGER REFERENCES evidence(evidence_id),
    extraction_confidence REAL NOT NULL CHECK (extraction_confidence BETWEEN 0.0 AND 1.0),
    model_id              TEXT,
    prompt_version        TEXT,
    grounding_check        TEXT NOT NULL DEFAULT 'not_run'
                             CHECK (grounding_check IN ('not_run','passed','failed','overridden')),
    extracted_at          TEXT NOT NULL
);

-- Steps 3 + 8: the recursive "why" chain AND the full causal chain are the
-- SAME artifact (a chain construction, seen at two points in the process).
-- One row per link; step_order 0 is the raw fact, increasing order = each
-- successive "why". evidence_id is often NULL past step 0 — later links
-- are economic INFERENCE, not new quotes, and must say so via inferred=1.
CREATE TABLE IF NOT EXISTS causal_chain_steps (
    chain_id      INTEGER PRIMARY KEY,
    fact_id       INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    step_order    INTEGER NOT NULL,
    statement     TEXT NOT NULL,               -- e.g. "Higher production capacity"
    inferred      INTEGER NOT NULL DEFAULT 0,   -- 0 = directly evidenced, 1 = economic inference
    evidence_id   INTEGER REFERENCES evidence(evidence_id),
    UNIQUE (fact_id, step_order)
);

-- Step 4: impact on each of the 14 fixed categories (§5), one row each —
-- a category with no basis to assess is 'unknown', never omitted, since
-- the owner's rule is EVERY category gets a verdict, explicitly.
CREATE TABLE IF NOT EXISTS impact_assessments (
    assessment_id  INTEGER PRIMARY KEY,
    fact_id        INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    category       TEXT NOT NULL CHECK (category IN
                     ('revenue','margins','cash_flow','capital_allocation','balance_sheet',
                      'growth','competitive_advantage','execution_risk','regulatory_risk',
                      'liquidity','valuation','market_expectations','long_term_moat')),
    direction      TEXT NOT NULL CHECK (direction IN
                     ('positive','negative','neutral','mixed','unknown')),
    explanation    TEXT NOT NULL,               -- the mandatory "explain WHY", never omitted
    evidence_id    INTEGER REFERENCES evidence(evidence_id),
    UNIQUE (fact_id, category)
);

-- Steps 5-13 terminal synthesis. One row per (fact, ticker) — a single
-- fact can imply consequences for more than one ticker (peers via §6/
-- Industry Reasoning), each gets its own row.
CREATE TABLE IF NOT EXISTS investment_implications (
    implication_id            INTEGER PRIMARY KEY,
    fact_id                   INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    ticker                    TEXT REFERENCES securities(ticker),
    index_code                TEXT REFERENCES indices(index_code),

    -- Step 5
    duration_bucket           TEXT NOT NULL CHECK (duration_bucket IN
                                ('very_short','short','medium','long','structural','permanent')),
    -- Step 6
    magnitude                 TEXT NOT NULL CHECK (magnitude IN
                                ('tiny','small','medium','large','transformational')),
    -- Step 7
    confidence                REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    confidence_rationale      TEXT NOT NULL,     -- MUST explain the uncertainty, not just state a number

    -- Step 9
    bull_case_delta           TEXT,              -- how this changes the bull case, if it does
    bear_case_delta           TEXT,
    base_case_delta           TEXT,
    intrinsic_value_direction TEXT CHECK (intrinsic_value_direction IN
                                ('increase','decrease','unclear')),
    intrinsic_value_reasoning TEXT,               -- HOW, never a bare direction (owner's explicit rule)
    expected_earnings_direction TEXT CHECK (expected_earnings_direction IN
                                ('increase','decrease','unclear')),
    target_multiple_direction TEXT CHECK (target_multiple_direction IN
                                ('increase','decrease','unclear','not_assessed')),
    risk_profile_direction    TEXT CHECK (risk_profile_direction IN
                                ('increase','decrease','unclear','not_assessed')),
    portfolio_sizing_note     TEXT,               -- QUALITATIVE ONLY — Portfolio Construction is
                                                   -- GATED; this is never an actual position size

    -- Step 10
    action_recommendation     TEXT NOT NULL CHECK (action_recommendation IN
                                ('no_action','watchlist','research_task','model_update',
                                 'valuation_update','factor_candidate','immediate_review')),

    -- Step 11-12: cross-reference and consistency (§8)
    corroborates_implication_id INTEGER REFERENCES investment_implications(implication_id),
    contradicts_implication_id  INTEGER REFERENCES investment_implications(implication_id),
    consistency_note             TEXT,            -- required if either FK above is set

    -- market reaction framing (owner's "underreacting or overreacting" question)
    market_reaction_assessment TEXT CHECK (market_reaction_assessment IN
                                ('underreacting','overreacting','fairly_priced','unclear')),
    market_reaction_reasoning  TEXT,

    status                     TEXT NOT NULL DEFAULT 'draft_pending_self_critique'
                                 CHECK (status IN ('draft_pending_self_critique',
                                                    'blocked_by_self_critique',
                                                    'unvalidated_ai_interpretation','under_review',
                                                    'promoted_to_discovery_candidate','rejected_by_review')),
    propagated_from_implication_id INTEGER REFERENCES investment_implications(implication_id),
    generated_at               TEXT NOT NULL
);

-- Step 13: second/third-order effects, each pointing at an affected entity
-- (company/sector/commodity/macro variable — all already modeled as
-- `entities` rows per the architecture doc's §5 knowledge graph).
CREATE TABLE IF NOT EXISTS effect_chains (
    effect_id        INTEGER PRIMARY KEY,
    implication_id   INTEGER NOT NULL REFERENCES investment_implications(implication_id),
    order_n          INTEGER NOT NULL CHECK (order_n IN (1, 2, 3)),
    description      TEXT NOT NULL,
    affected_entity_id INTEGER REFERENCES entities(entity_id),
    evidence_id      INTEGER REFERENCES evidence(evidence_id)
);

-- Step 13: "Research Tasks" output — a lightweight, human-reviewable
-- worklist. NOT a hypothesis, NOT a portfolio action — see §9.
CREATE TABLE IF NOT EXISTS research_task_candidates (
    task_id          INTEGER PRIMARY KEY,
    implication_id   INTEGER NOT NULL REFERENCES investment_implications(implication_id),
    description      TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'open'
                       CHECK (status IN ('open','in_review','promoted','dismissed')),
    created_at       TEXT NOT NULL
);
```

`duration_bucket` and `magnitude` are `NOT NULL` deliberately — the
owner's rule is that every fact gets BOTH assessed, never left implicit.
`confidence_rationale` is `NOT NULL` for the same reason: a bare
confidence number without a stated reason for uncertainty is exactly the
"never say X without explaining" failure mode this whole document exists
to prevent.

## 4. Fact taxonomy (Step 2, config-driven — `configs/fact_taxonomy.toml`)

Same pattern as `event_taxonomy.toml`/`document_taxonomy.toml`: adding a
leaf is a config change, not a code change. Categories group the owner's
example list; an `[uncategorized]` leaf exists explicitly so "nothing
important is ignored" is never violated by a missing taxonomy entry (an
ungrouped fact is still captured, just flagged for taxonomy triage):

```toml
[operating_performance]
types = ["earnings", "guidance", "margin_change", "market_share_change",
         "customer_loss", "supplier_issue", "competition_change"]

[corporate_events]
types = ["management_change", "ceo_resignation", "acquisition", "asset_sale",
         "major_contract", "product_launch", "factory_shutdown", "capacity_expansion"]

[capital_and_balance_sheet]
types = ["capital_raise", "share_buyback", "dividend", "rights_issue",
         "private_placement", "debt_change", "cash_change", "capex", "credit_rating_change"]

[legal_and_regulatory]
types = ["litigation", "regulation_change", "government_policy", "tax_change"]

[macro_exposure]
types = ["fx_exposure", "commodity_exposure", "interest_rate_change", "inflation_release"]

[security_and_operational_risk]
types = ["cyber_attack", "operational_disruption"]

[uncategorized]
types = ["other"]   -- catch-all; a fact landing here is a taxonomy-triage flag, never dropped
```

## 5. The 14 impact categories (Step 4)

Fixed vocabulary (schema CHECK constraint, §3): `revenue`, `margins`,
`cash_flow`, `capital_allocation`, `balance_sheet`, `growth`,
`competitive_advantage`, `execution_risk`, `regulatory_risk`, `liquidity`,
`valuation`, `market_expectations`, `long_term_moat` — 13 explicit
categories from the owner's Step 4 list (Long-term Moat included).
**Every fact gets an `impact_assessments` row for every category** —
`direction='unknown'` with an explanation of why it's unassessable is a
valid, expected, non-error row (mirrors the platform's existing "unknown
stays unknown" discipline), not a gap to be silently skipped.

## 6. Duration and magnitude taxonomies (Steps 5-6)

Fixed vocabularies, no free text — this is what makes the platform
queryable ("show me every Large-magnitude, Structural-duration fact from
the last 90 days") instead of just readable:

- **Duration**: `very_short` (intraday/days) → `short` (weeks) → `medium`
  (a few quarters) → `long` (multi-year) → `structural` (changes the
  industry's operating rules) → `permanent` (irreversible).
- **Magnitude**: `tiny` → `small` → `medium` → `large` →
  `transformational`. No numeric mapping is pre-defined (e.g. "large =
  +5% revenue") — that would be inventing a threshold with no evidence
  behind it; the reasoning engine states the bucket AND the
  `confidence_rationale` explains the judgment, same as every other
  qualitative call this layer makes.

## 7. Cross-referencing (Step 11) reuses existing quantitative machinery

The owner's Step 11 asks "did similar announcements lead to abnormal
returns historically?" — this is not a new capability to build. It is
exactly the event-study question the platform already answers for H-003
-style hypotheses (`signal.event_window_scores`, the generic event-study
runner path built for MPC-window and catalyst-rotation testing,
`docs/FACTOR_REGISTRY.md`'s H-003/H-005 entries). When a `fact_type`
accumulates enough historical instances in `extracted_facts`/`events`,
the reasoning engine's cross-reference step queries that EXISTING
machinery for the historical abnormal-return pattern, and cites the
result as evidence in `investment_implications.confidence_rationale` —
**the query result is evidence, not a new alpha claim**; if the pattern
looks promising enough to matter, it still goes through Discovery →
pre-registration → the full gauntlet before anything treats it as real,
exactly like every other candidate. This keeps "cross-reference" from
becoming a backdoor around the validation process — it reuses the
process's own historical outputs as an input, nothing more.

## 8. Consistency, contradiction, and versioning (Step 12)

Directly extends a pattern already coded, not a new mechanism:
`event_pipeline.py`'s `validate_batch` already handles "same natural key,
different source, disagreeing values" by preserving BOTH rows and logging
a CONFLICT rather than deleting or overwriting. This layer's
`investment_implications` follows the identical rule: before writing a
new implication, the pipeline searches prior implications for the same
`ticker`/overlapping `fact_type` within a lookback window. If the new
conclusion agrees, `corroborates_implication_id` is set. If it disagrees,
`contradicts_implication_id` is set, `consistency_note` MUST explain which
source is more reliable and why (based on `source_confidence`,
`extraction_confidence`, and reviewed status — the two-and-three-axis
confidence model from the architecture doc's §6, unchanged) — **and the
old row is never touched.** Both stand, append-only, exactly like every
other table on this platform.

## 9. Mapping Step 13's outputs to the governance boundary

| Step 13 output | Storage | Governance status |
|---|---|---|
| Summary / Key Facts / Economic Meaning | `extracted_facts` + `causal_chain_steps` | Descriptive, not a claim |
| Bullish / Bearish Arguments | `investment_implications.bull_case_delta`/`bear_case_delta` | Labeled `unvalidated_ai_interpretation` |
| Second/Third-order Effects | `effect_chains` | Same label, explicitly ORDER-tagged so a third-order guess is never shown with first-order confidence |
| Affected Companies/Industries/... | `effect_chains.affected_entity_id` → `entities` | Knowledge graph, not a factor exposure |
| Risk Changes | `investment_implications.risk_profile_direction` | Qualitative, not a risk-model input (Risk Engine module remains GATED) |
| Confidence | `investment_implications.confidence` + mandatory `confidence_rationale` | Never a bare number |
| Evidence Quotes | `evidence` table (architecture doc §4.4), joined via every `evidence_id` FK above | Mandatory, not optional |
| Reasoning Chain | `causal_chain_steps` | Explicit, ordered, `inferred` flag distinguishes fact from inference |
| Knowledge Graph Updates | `entities`/`entity_relationships`/`entity_mentions` | Unchanged from architecture doc §5 |
| Research Tasks | `research_task_candidates` | A worklist for a human, not an instruction |
| **Hypotheses Created** | `discovery_feed.py`'s aggregation input (architecture doc §9) | **Never a new hypothesis ID directly — only a Discovery-candidate row; H-012+ requires full pre-registration** |
| **Portfolio Implications** | `investment_implications.portfolio_sizing_note` (TEXT) | **Qualitative note only — Portfolio Construction is GATED; nothing here is a position size or trade instruction** |

## 10. Engine-specific reading guidance (maps onto the 4 engines, architecture doc §4.5)

- **Earnings/filings guidance** (revenue/margin/cash-flow drivers,
  management quality, capital-allocation quality, forward guidance, hidden
  positives/negatives, accounting red flags, one-offs vs. recurring,
  executive-language changes, risk-factor additions/removals) → **Financial
  Reasoning Engine**'s `fact_type` scope is `operating_performance` +
  `capital_and_balance_sheet` + `legal_and_regulatory` (§4). Its
  `intrinsic_value_reasoning` field is where "hidden positives/negatives"
  and "one-off vs. recurring" judgments get written — always with a
  `causal_chain_steps` trail, never a bare label.
- **News guidance** (noise/narrative/catalyst/... classification, over
  /underreaction) → **News Understanding Engine** populates
  `documents.news_classification` (§2) and
  `investment_implications.market_reaction_assessment` (§3); both require
  the `news_outlets.reliability_tier` join from the architecture doc's
  §4.1 news-source registry before being trusted at anything above the
  unreviewed floor.
- **Macro guidance** (who benefits/loses, which sectors/factors/styles) →
  **Macroeconomic Reasoning Engine**'s `effect_chains` rows are how
  "which sectors, which styles (growth/value/momentum/quality/size/
  dividend/liquidity/low-vol)" gets recorded — each style tag is an
  `affected_entity_id` pointing at a `sector`-type or a (future) style
  -factor entity, never a bare inference with no linked evidence.
- **Multiple-document synthesis** (patterns, contradictions,
  confirmation, emerging themes before consensus) → this is Steps 11-12
  run ACROSS documents rather than within one, using the same
  `corroborates_implication_id`/`contradicts_implication_id` mechanism.
  "Emerging theme before consensus" is operationalized as: N
  `investment_implications` rows across DIFFERENT documents/tickers,
  same `fact_type`, same `direction`, within a rolling window — this
  aggregate is exactly what `discovery_feed.py` feeds to the Hypothesis
  Discovery scanner (§9), never asserted as a theme on its own authority.

## 11. Mechanical anti-vagueness checks (not just instructions to a model)

The owner's rules ("never say 'this is good,' explain WHY"; "never say
'bullish,' explain WHY"; "never say 'increases value,' explain HOW") are
enforced as validation, not just prompted:

1. **NOT NULL explanation fields everywhere a verdict exists**
   (`impact_assessments.explanation`, `investment_implications
   .confidence_rationale`/`intrinsic_value_reasoning`) — a row cannot be
   written without one, full stop.
2. **A banned-phrase check** (new function in `grounding.py`, alongside
   the existing quote-grounding check from the architecture doc's §4.4):
   flags explanation/reasoning text that is just a restated verdict with
   no causal content (e.g., text matching `/^(this is|it'?s)\s+(good|bad|
   bullish|bearish|positive|negative)\.?$/i` or below a minimum length/
   causal-connective heuristic) — `grounding_check='failed'`, same
   consequence as an ungrounded quote (capped confidence, human review
   required before it counts for anything).
3. **Chain-completeness check**: an `investment_implications` row whose
   `fact_id` has zero linked `causal_chain_steps` fails validation before
   insert — there is no such thing as a conclusion with an empty
   reasoning chain in this schema.

## 12. Self-critique gate (Step 14 — the devil's-advocate pass)

Steps 1-13 produce a draft. **A draft is not knowledge** — it is written
to `investment_implications` with `status='draft_pending_self_critique'`
(§3), which no downstream consumer (`discovery_feed.py`, Company
Intelligence, any report) is permitted to read, exactly as
`staging.py`'s quarantine already keeps unvalidated price data away from
every reader on this platform until it clears. The self-critique gate is
what moves a row out of quarantine — and it can just as easily block it.

**Design requirement: the critique pass is a SEPARATE reasoning call from
the one that produced the draft**, run against an adversarial prompt whose
only job is to find fault with the draft — not the same completion
re-affirming itself. A model asked to critique its own immediately-prior
output in the same context is a weak check (well-documented failure mode:
it tends to defend what it just said); a fresh call, given only the draft
plus the underlying evidence and told to argue against it, is the actual
"investment committee challenging the analyst" the owner asked for. Where
practical, this should even be a different `model_id` than the one that
generated the draft — recorded on the critique row, so the platform can
later check whether critique quality varies by model pairing.

### 12.1 The eight mandatory questions

Every draft gets a `self_critique_reviews` row for EACH question, always
— same completeness discipline as the 14 impact categories in §5. A
question with nothing to flag is a `pass` verdict with a stated reason,
never a silently skipped row.

```sql
CREATE TABLE IF NOT EXISTS self_critique_reviews (
    critique_id      INTEGER PRIMARY KEY,
    implication_id   INTEGER NOT NULL REFERENCES investment_implications(implication_id),
    question         TEXT NOT NULL CHECK (question IN
                        ('unevidenced_inference', 'correlation_vs_causation',
                         'ignored_alternative_explanation', 'single_document_overreaction',
                         'contradicts_prior_evidence', 'insufficient_information',
                         'confidence_improving_information', 'market_noise_check')),
    finding          TEXT NOT NULL CHECK (finding IN ('pass', 'concern', 'fail')),
    explanation      TEXT NOT NULL,     -- MUST justify the verdict — same NOT NULL discipline as §11
    resulting_action TEXT NOT NULL CHECK (resulting_action IN
                        ('none', 'confidence_lowered', 'status_downgraded',
                         'research_task_created', 'flagged_for_human_review')),
    model_id         TEXT NOT NULL,     -- the CRITIC's model, distinct from the draft's model_id
    prompt_version   TEXT NOT NULL,
    reviewed_at      TEXT NOT NULL
);
```

Mapped to the owner's exact wording, and to a mechanical check that runs
alongside the model's own self-report (a model saying "no concerns" is
not itself sufficient — the same "don't just trust the model" principle
as §11's banned-phrase check):

| Question | `question` value | Mechanical check that runs regardless of what the model reports |
|---|---|---|
| Did I infer something without evidence? | `unevidenced_inference` | Any `causal_chain_steps` row with `inferred=1` and no earlier evidenced step in the same chain → auto `concern` |
| Did I confuse correlation with causation? | `correlation_vs_causation` | A chain whose `inferred=1` steps outnumber `inferred=0` steps by more than 2:1 → auto `concern` (a long inferential leap on thin direct evidence) |
| Did I ignore an alternative explanation? | `ignored_alternative_explanation` | None (inherently generative — the critique call must state at least one plausible alternative and why the draft's explanation is more likely; an empty/templated answer here fails §11's banned-phrase check) |
| Did I overreact to a single document? | `single_document_overreaction` | Count of DISTINCT `doc_id` values across the fact's `evidence` rows == 1 AND `magnitude` IN ('large','transformational') → auto `concern` (a transformational call resting on one document is exactly the overreaction risk named) |
| Does this contradict prior evidence? | `contradicts_prior_evidence` | Re-runs the §8 cross-reference query; if it finds a disagreeing prior implication that `investment_implications.contradicts_implication_id` did NOT already capture → auto `fail` (the draft missed its own Step 12) |
| Is there enough information to reach this conclusion? | `insufficient_information` | Total linked `evidence` row count below a floor (value TBD with owner during Phase D pilot, not invented here) → auto `concern` |
| What information would most increase my confidence? | `confidence_improving_information` | None (generative); `resulting_action` is REQUIRED to be `research_task_created` for this question — it always produces a `research_task_candidates` row naming the missing information, turning the answer into an actionable worklist item rather than a rhetorical aside |
| Could this simply be market noise? | `market_noise_check` | Reuses §7's historical base-rate query: if this `fact_type` occurs frequently for this ticker/sector with no historically observed price effect, → auto `concern`; for news-sourced facts, `documents.news_classification='noise'` on the source document → auto `fail` |

### 12.2 Gate outcome

- **Any `fail`** → `investment_implications.status` set to
  `'blocked_by_self_critique'`. Blocked rows are excluded from every
  consumer exactly like `rejected_by_review` rows are today; a human
  reviewer resolves them (to `under_review`, `rejected_by_review`, or —
  if the fail was itself a false alarm — a note explaining why, mirroring
  how `event_pipeline.py` never silently deletes a flagged row).
- **Any `concern`, no `fail`** → `status` advances to
  `'unvalidated_ai_interpretation'` (now readable, same as any other AI
  -sourced row) but `confidence` is mechanically reduced (a fixed discount
  per unresolved `concern`, value TBD with owner) and every `concern`'s
  `explanation` is appended to `confidence_rationale` — the uncertainty
  the critique surfaced is never dropped on the floor once the gate
  passes, it travels with the row.
- **All eight `pass`** → `status` advances to
  `'unvalidated_ai_interpretation'` unchanged, `confidence` untouched.

This is the same append-only, never-hide-uncertainty discipline as
everything else on this platform, applied one step earlier: the critique
doesn't get to quietly wave a draft through, and a human doesn't have to
read eight paragraphs of model self-talk to know something needs
attention — `resulting_action` and `finding` make it queryable
(`SELECT * FROM self_critique_reviews WHERE finding = 'fail'` is the
review queue).

## 13. Non-goals (unchanged from the architecture doc, restated because
this document's outputs are the richest yet and easiest to over-trust)

- No numeric intrinsic-value/DCF output — `intrinsic_value_direction` is
  qualitative, `intrinsic_value_reasoning` explains the mechanism, neither
  is a valuation model output (no financial-statements dataset exists yet).
- No automatic promotion of a `research_task_candidates` row to a
  hypothesis, and no automatic hypothesis promotion to `confirmed` —
  human review at every promotion boundary, unchanged.
- No portfolio sizing — `portfolio_sizing_note` is prose, not a number,
  and nothing reads it as one.
- Steps 11's historical-pattern query reuses existing event-study
  machinery for evidence; it does not create a new, separate signal
  -validation shortcut.
- The self-critique gate (§12) does not make a draft "validated" — a row
  that passes all eight questions is still `unvalidated_ai_interpretation`,
  same label as before. Self-critique catches sloppy reasoning; it is not
  a substitute for the pre-registration/placebo/walk-forward gauntlet, and
  a passing critique is never cited as if it were.

## 14. What's still required before Phase D can execute this (unchanged
open decisions from the architecture doc, reaffirmed)

LLM vendor/cost, OCR engine (36% of the Phase A archive still has no
usable text — the Financial Reasoning Engine's filing-derived facts are
capped at the 7,399 native-text documents until this resolves), the
pilot claim/fact type choice, human-review staffing, and — new from §12 —
the confidence-discount-per-`concern` value and the minimum-evidence-count
floor for `insufficient_information`. This document does not resolve any
of them — it specifies what happens once they are.
