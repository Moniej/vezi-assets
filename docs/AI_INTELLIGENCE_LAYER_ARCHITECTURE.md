# Fund Alpha — AI Intelligence Layer: Comprehensive Architecture

*2026-07-22, revision 2 (supersedes the same-day initial draft — scope
expanded by owner directive from "Document Intelligence module" to a full
AI Intelligence Layer with financial/news/macro/industry reasoning).
Design document only. No code written against it. No existing file
modified except this one and `HANDOFF.md`'s pointer. The frozen V1
architecture (`docs/PLATFORM_ARCHITECTURE.md`) and the validated research
engine (`runner.py`, `phase4.py`, `stats.py`, the hypothesis ledger) are
UNCHANGED and are not redesigned anywhere below — this document describes
a new layer that produces INPUTS to that engine, never a replacement for
it.*

## 1. Purpose

The platform is evolving from a quantitative factor research engine into a
complete AI-powered institutional investment research platform. The
quantitative engine remains the foundation and is not touched. This
document specifies the layer that lets the platform read and reason over
the same categories of information a human institutional analyst would —
filings, transcripts, news, macro releases, industry reports — and convert
that reading into structured, evidence-linked, explainable intelligence.

**Non-negotiables this document is designed against, restated with the
mechanism that enforces each one (not just the promise):**

| Principle | Enforcing mechanism |
|---|---|
| Never invent alpha | Nothing produced by this layer is readable by `alpha_engine.py` or any portfolio module. The only path to a trading signal is a fully pre-registered, gauntlet-passed hypothesis (§9). |
| Every score/recommendation is evidence-based | Every reasoning conclusion stores foreign keys to the exact evidence rows it used (§6); a conclusion with zero linked evidence is a schema violation. |
| Hypothesis testing, pre-reg, placebo, walk-forward, PIT, audit trail, factor library unchanged | Zero modifications proposed to `runner.py`, `phase4.py`, `stats.py`, `registry.py`, `ledger.py`, `db.py`'s existing readers, or `schema.sql`'s existing tables. All new tables are additive. |
| Nothing bypasses the research process | Aggregated AI outputs enter the SAME Hypothesis Discovery scanner path (`docs/HYPOTHESIS_DISCOVERY_DESIGN.md`) as any other candidate signal — no special-cased shortcut for AI-sourced ideas. |

## 2. Master architecture — the full flow

```
Raw Data (existing Data Layer — prices, corp actions, macro series, events)
        │
        ▼
Document Intelligence   <-- THIS DOCUMENT, layers 1-6 (section 4)
        │  (documents, entities, events, evidence, reasoning,
        │   investment_implications — all append-only, all confidence-scored)
        ▼
Knowledge Graph          <-- THIS DOCUMENT, section 5
        │  (queryable structured store: entities + relationships + every
        │   event/evidence/reasoning/implication attached to them)
        ▼
Research Engine           <-- UNCHANGED. Aggregated KG signals become
        │                     Hypothesis Discovery scanner candidates,
        │                     scored + BH-corrected like any other
        │                     candidate. Promotion to a real hypothesis
        │                     (H-012+) requires full pre-registration +
        │                     gauntlet (phase4.py) — NO exception.
        ▼
Validated Factor Library    <-- UNCHANGED (docs/FACTOR_REGISTRY.md). Only
        │                       mechanically-verdicted hypotheses enter.
        ▼
Company Intelligence         <-- EXTENDED (not redesigned): qualitative
        │                        fields sourced from investment_implications,
        │                        always badged unvalidated vs. validated
        │                        exactly as `company_intelligence.py`
        │                        already distinguishes Size (validated)
        │                        from Momentum/Low-Vol/PEAD (rejected).
        ▼
Ranking Engine                 <-- STILL GATED (frozen precondition: ≥2
        │                          validated independent factors). This
        │                          layer supplies richer qualitative
        │                          CONTENT for when the gate opens; it
        │                          does not lower the gate.
        ▼
Portfolio Construction           <-- STILL GATED, same precondition, unchanged.
        ▼
Risk Engine                       <-- STILL GATED, unchanged.
```

Every downward arrow past "Research Engine" only carries **validated**
content. Every arrow from "Document Intelligence" through "Knowledge
Graph" into "Research Engine" only carries **candidates** — labeled,
confidence-scored, never presented as validated. This single distinction
is the entire governance boundary; every section below exists to make it
mechanically true rather than merely documented.

## 3. Module breakdown

| Module | Status | One-line role |
|---|---|---|
| Document Ingestion | NEW | Retrieval bookkeeping for every source type (§4.1) across exchanges |
| Text Extraction (native/OCR) | NEW | Turns bytes into clean text + a source-quality confidence |
| Entity Extraction | NEW | Companies, executives, competitors, regulators, sectors → nodes |
| Event Extraction | NEW (extends existing `events` table) | Discrete, dateable happenings — reuses existing taxonomy machinery |
| Evidence Tracking | NEW | Exact quoted/located spans backing every downstream claim |
| Financial Reasoning Engine | NEW | Earnings/margin/valuation-direction reasoning from filings |
| News Understanding Engine | NEW | Same pipeline, news-specific source-reliability tiering |
| Macroeconomic Reasoning Engine | NEW | Transmission reasoning: macro event → sector/company exposure |
| Industry Reasoning Engine | NEW | Peer/competitor propagation via the knowledge graph |
| Investment Implications | NEW | Terminal synthesis: horizon, earnings direction, thesis impact |
| Knowledge Graph | NEW | The queryable union of all of the above |
| Research Engine | UNCHANGED | `runner.py`/`phase4.py` gauntlet — reads KG only via Discovery scanner |
| Validated Factor Library | UNCHANGED | `docs/FACTOR_REGISTRY.md` |
| Company Intelligence | EXTENDED | `company_intelligence.py` gains a qualitative section |
| Ranking / Portfolio / Risk | UNCHANGED, still GATED | Preconditions untouched |

## 4. Document Intelligence pipeline

The core sub-flow, per owner's explicit diagram:

```
Document → Entities → Events → Evidence → Reasoning → Investment Implications
```

### 4.1 Document ingestion & source taxonomy

Every source type gets a `DocumentProvider` implementation (parallel to
`providers/base.py`'s `DataProvider`) and a `doc_type` taxonomy leaf in a
new `configs/document_taxonomy.toml` (same config-driven pattern as
`event_taxonomy.toml` — adding a source or type is a config change):

| Source | Provider | Status on NGX today | Reliability tier |
|---|---|---|---|
| Corporate filings / corp actions / earnings releases | `XIssuerDocumentProvider` | 11,534 already archived (`data/archive/xissuer_docs/`) | primary (source_confidence 0.85, OCR-capped subset 0.5) |
| Investor presentations | `XIssuerDocumentProvider` (same feed, different doc_type) | Present in the same archive, unclassified by type yet | primary |
| Dividend notices / corporate announcements | `XIssuerDocumentProvider` | Already the source of the existing deterministic dividend/EPS extractors | primary |
| Central bank releases (CBN) | `CBNDocumentProvider` | MPC communiqué PDFs already tracked at the metadata level (`data/events_mpc/`); full-text harvest not yet done | primary |
| Macro/industry reports (NBS, SEC, sector bodies) | `MacroDocumentProvider` | Not yet harvested; probe only (per 2026-07-15 acquisition plan) | primary, pending harvest |
| News articles | `NewsDocumentProvider` | Not yet built. Requires a **source-reliability registry** (below) since, unlike a regulatory filing, "the same fact" from two outlets can carry very different trust | secondary/unverified, per-outlet |
| Analyst research | `AnalystResearchProvider` | Legally gated — only where licensing permits; NOT a general harvest target | secondary, licensing-dependent |
| Earnings call transcripts | `TranscriptDocumentProvider` | **Not applicable to NGX today** — most NGX issuers do not hold analyst transcript calls in a transcribable format (open finding, not yet re-verified this session). Built generically for future exchanges (NYSE/LSE/etc.) where transcripts are standard; NGX-specific harvesting work is explicitly NOT scheduled until this data-availability question is answered as its own scoping task. | primary, where it exists |
| SEC/other-exchange filings | Future `SECEdgarDocumentProvider`, `LSERNSDocumentProvider`, etc. | Not built — Module 12 (multi-exchange) placeholder, §10 | primary |

**News source-reliability registry** (new, required before any news
ingestion): a small reference table `news_outlets(outlet_name,
reliability_tier, base_confidence, notes)`, populated by owner judgment
(mirrors how `cost_schedule`'s retail-rate assumptions are owner-confirmed
today) — never inferred by the AI itself, since an AI judging its own
sources' trustworthiness is circular.

Text extraction (native PDF via `pdfplumber`, OCR for scans) is unchanged
from the initial draft (§2 of the prior version) — native text gets
`source_confidence≈0.85`, OCR gets a capped tier pending an anchor-based
accuracy validation, exactly as already flagged for the ~25% scanned
subset of corporate-action notices.

### 4.2 Entity extraction

Populates `entities` / `entity_mentions` (schema in §8). Entity types:
`company` (linked to existing `securities.ticker` — no duplication),
`executive`, `competitor_mention`, `regulator`, `sector` (linked to
`securities.sector_ngx` / `indices.index_code` where classifiable).
Extraction is schema-constrained LLM output (name + type + the exact
mention span, never a free-text guess) followed by an entity-resolution
step: a new mention either matches an existing entity (fuzzy name match +
human-confirmable merge queue) or creates a new one — this resolution
queue is itself human-reviewed before two mentions are silently merged,
avoiding a wrong-merge from silently combining two different people or
subsidiaries. NGX's `sector_ngx` classification gap (`securities.sector_ngx`
0/320 populated, a known blocker in `company_intelligence.py`'s
`UNAVAILABLE_FIELDS`) is a natural early win here: entity extraction over
filings can populate sector labels from disclosed SIC-style classifications
in the documents themselves, closing that gap as a side effect rather than
requiring a separate acquisition project.

### 4.3 Event extraction — reuses the existing `events` table, does not fork it

This is the single most important continuity decision in this design.
The platform already has an `events` table with exactly the columns the
owner's question list needs: `ticker` and `index_code`/`scope` answer
"which companies/sectors are affected"; `announced_date`/`effective_date`
answer timing; `severity`/`direction` already exist; `event_type` is
taxonomy-driven and config-extensible (`configs/event_taxonomy.toml`).

**AI-detected events (CEO resigned, factory expansion announced, dividend
increased, regulatory fine imposed, product launched, margin guidance
reduced, debt refinanced) become NEW rows in the SAME `events` table**,
under new taxonomy categories added to `event_taxonomy.toml` (proposed:
`[corporate_operational]` — ceo_change, capacity_expansion,
product_launch, guidance_revision, debt_refinancing,
regulatory_enforcement, market_share_change), ingested through the
UNCHANGED `event_pipeline.validate_batch` (taxonomy/chronology/duplicate/
conflict checks apply identically, no code path forked).

The only new mechanism needed: two additive companion tables (never a
change to `events`' own columns or constraints) carrying AI-specific
provenance that hand-curated events (like the 93 MPC/regulatory events
already in the ledger) don't need:

- `event_ai_provenance` — links an `event_id` to `extraction_method`,
  `model_id`, `prompt_version`, `grounding_check`, `reviewed_by`,
  `reviewed_at`. Absence of a row = a human-curated event, exactly as
  today.
- AI-sourced events default `events.confidence` to a low unreviewed floor
  (proposed 0.3, matching the platform's existing convention of gating
  synthetic/unverified data at low confidence bands) until
  `event_ai_provenance.reviewed_by` is set, at which point a reviewer
  -confirmed confidence (typically 0.7, matching secondary-source human
  -verified events elsewhere in the events table) replaces it — an
  append-only restatement via the existing `event_uid` mechanism
  (`events_asof` already resolves to the latest `as_of_date` per uid;
  no new resolution logic needed).

### 4.4 Evidence tracking

A new `evidence` table is the formal citation layer answering "traceable
back to documents, paragraphs, filings, numerical evidence" literally:

`evidence(evidence_id, doc_id, event_id NULLABLE, quoted_text, page_number,
char_start, char_end, source_confidence)`.

Every event created via §4.3, and every reasoning conclusion in §4.5,
references one or more evidence rows through join tables
(`event_evidence`, `reasoning_evidence` — plain many-to-many, no new
pattern). An **explain function** (§9) walks
`investment_implication → reasoning → evidence → document` and returns the
full chain; no report or Company Intelligence field may render a
conclusion without this chain resolving to at least one evidence row —
enforced by a write-time check in the CLI/ingestion layer (§9), not just a
convention.

### 4.5 Reasoning: four specialized engines, one shared schema

**Superseded in detail by `docs/REASONING_ENGINE_SPECIFICATION.md`
(2026-07-22, now at revision 2)** — the owner's follow-up directives
expanded this section's sketch into a full 14-step reasoning chain (13
analytical steps plus a mandatory self-critique/devil's-advocate gate), a
14-category impact taxonomy, duration/magnitude vocabularies,
second/third-order effect chains, and mechanical (not just prompted)
anti-vagueness and self-critique checks. That document's
`reasoning`/`investment_implications`/`self_critique_reviews` schema
replaces the sketch below AND §4.6's `investment_implications` sketch
(including its `status` enum, which gained `draft_pending_self_critique`
and `blocked_by_self_critique` stages that must be cleared before a row
reaches `unvalidated_ai_interpretation`) — both sections are kept here for
the one-paragraph summary and the governance framing, which are unchanged.

The owner's ten questions ("what happened," "why does it matter," "is it
fundamentally important," which companies/sectors, short/long-term,
earnings direction, intrinsic-value change, thesis impact, confidence) are
operationalized as a **structured schema**, not a prose blob — this is
what makes the platform queryable and auditable instead of just "an LLM
wrote something plausible":

```
reasoning(reasoning_id, event_id, question_type, answer_label, answer_text,
          extraction_confidence, model_id, prompt_version, grounding_check)
```

`question_type` is a fixed, config-driven vocabulary (mirrors
`_DIRECTIONS`/`_SEVERITIES` in `event_pipeline.py`):
`what_happened`, `why_it_matters`, `fundamental_importance`
(binary + rationale — a filing can be newsworthy but not
fundamentally material, e.g. a routine board-meeting notice),
`affected_scope` (resolves to the SAME `ticker`/`index_code`/`scope`
columns on the parent event — this row exists mainly to carry the
propagation *rationale*, since the event row already states *what* is
affected), `time_horizon` (`short_term`/`long_term`/`unclear`),
`earnings_direction` (`increase`/`decrease`/`unclear`),
`intrinsic_value_direction` (`increase`/`decrease`/`unclear`),
`thesis_impact` (`strengthens`/`weakens`/`neutral`). Each has its own
`extraction_confidence` — "what happened" is typically near-certain from
a clear filing; "does this change intrinsic value" is inherently more
speculative and MUST carry a correspondingly lower confidence, never
inflated to match the extraction confidence of the underlying fact.

**Four reasoning engines share this exact schema**, differing only in
their INPUT documents and the domain-specific evidence they cross-check
against:

**Financial Reasoning Engine** — filings, earnings releases, investor
presentations. Where the platform has deterministic numeric data already
(dividend/EPS figures, price/volume), `earnings_direction` and
`intrinsic_value_direction` conclusions are cross-checked against it the
same way §4.4's numeric cross-check works. **Explicit scope limit**: this
engine reasons DIRECTIONALLY and QUALITATIVELY about intrinsic value
("management raised margin guidance, evidence suggests a positive
earnings revision") — it does NOT compute a DCF or a numeric intrinsic
-value estimate, because the platform has not acquired a financial
-statements dataset yet (the same `UNAVAILABLE_FIELDS` blocker
`company_intelligence.py` already discloses for "Financial Quality" and
"Growth"). Building a real valuation-model output before that dataset
exists would itself be inventing alpha from nothing — explicitly refused.

**News Understanding Engine** — news articles. Same reasoning schema, but
every conclusion additionally inherits the source article's
`news_outlets.reliability_tier`, and — because a single event is often
covered by multiple outlets — a **corroboration check**: an
`investment_implication` sourced from news alone (no primary filing
backing it) is flagged `single_source_news` and held to a stricter review
bar, mirroring the platform's existing `single_source_day` diagnostic
pattern in `data_quality_log` for price data with only one corroborating
source.

**Macroeconomic Reasoning Engine** — central bank releases, macro/industry
reports. Input is the EXISTING `macro_series`/`events` tables (MPC
decisions, FX policy, already populated) plus newly-harvested macro
document text. Its distinctive job is **transmission reasoning**: given a
macro event, which sectors/tickers are exposed and why (e.g., "MPR hike →
`why_it_matters` cites historical NGXBNK margin sensitivity from
`docs/FACTOR_REGISTRY.md`'s H-005 finding, NOT a fabricated new
mechanism"). Because H-004 (oil lead-lag) and H-005 (MPC-window effects)
were BOTH rejected on this platform, this engine's reasoning about
"increase/decrease" macro effects must explicitly cite that rejection
history as a caveat wherever relevant — reusing evidence of absence is as
important as reusing evidence of presence (same discipline
`REJECTED_FAMILIES` already applies in `company_intelligence.py`).

**Industry Reasoning Engine** — the only engine that reasons primarily off
the knowledge graph rather than a single document. Given a company-level
`investment_implication`, it walks `entity_relationships`
(`competitor_of` edges) to generate SECONDARY, explicitly lower-confidence
implications for peers (e.g., "Company A cuts prices" →
low-confidence, clearly-labeled secondary implication for Company B: "may
face margin pressure"). Secondary implications are tagged
`propagated_from_implication_id` and inherit a confidence penalty (a fixed
discount factor, TBD with owner) — never presented at the same confidence
as a directly-evidenced implication.

### 4.6 Investment Implications — the terminal synthesis record

```
investment_implications(implication_id, event_id, ticker, index_code,
    time_horizon, earnings_direction, intrinsic_value_direction,
    thesis_impact, confidence, status, propagated_from_implication_id,
    generated_at)
```

`status ∈ {'unvalidated_ai_interpretation', 'under_review',
'promoted_to_discovery_candidate', 'rejected_by_review'}` — note there is
**no** `'validated_factor'` status here; validation only ever happens in
the hypothesis ledger (`registry.sqlite`), never in this table. An
implication reaching `promoted_to_discovery_candidate` means it has been
aggregated into a Hypothesis Discovery scanner input (§9) — it still is
not, and never becomes, a factor by virtue of that status alone.

## 5. Knowledge Graph design

The Knowledge Graph is not a new storage engine — it is the queryable
union of `entities`, `entity_relationships`, `entity_mentions`, `events`
(existing table, extended per §4.3), `evidence`, `reasoning`, and
`investment_implications`, all inside the existing `ngx.sqlite` (or a
sibling file if size/perf later demands separation — not needed at
today's scale: 11,534 documents is small for SQLite). Relational, not
graph-native, for the same reason as the initial draft: no traversal
query on this platform yet needs more than 2-3 hops (entity →
relationship → entity; event → evidence → document), which plain SQL
joins handle without a new query language or infrastructure dependency.
If deep multi-hop traversal becomes a real need (e.g., "sector-wide
contagion three relationships removed"), that is a future, evidence
-driven decision — not pre-built speculatively, matching the platform's
own gating discipline for every other module.

Every node and edge carries the same lineage columns as everything else
on this platform: `source_id`/`confidence`/`as_of_date` where applicable,
append-only (a correction is a new row with a new `as_of_date`, never an
UPDATE).

## 6. Confidence scoring

Three levels, never merged, each answering a different question:

1. **`source_confidence`** (on `documents`, `evidence`) — how much do we
   trust this document's TEXT is accurate to what was actually said/
   published (native text 0.85, OCR pending validation ≤0.5, unverified
   news outlet per its own tier).
2. **`extraction_confidence`** (on `document_claims`-equivalent fields,
   i.e. entity mentions and event creation) — how much do we trust the
   AI's STRUCTURED READING of the text (unreviewed LLM output capped low,
   e.g. 0.3; human-reviewed raised to a reviewer-set value; deterministic
   regex extraction = 1.0, unchanged from the initial draft).
3. **`reasoning.extraction_confidence`** (per reasoning row) — how much do
   we trust THIS SPECIFIC CONCLUSION, independent of whether the
   underlying fact was extracted correctly. "What happened" can be
   near-certain while "does this change intrinsic value" on the same
   event is legitimately uncertain — collapsing these into one number
   would hide exactly the uncertainty the charter requires surfacing
   ("never hide uncertainty," already a MODULE 6 rule for the ranking
   engine, applied here one layer earlier).

Every consumer (Company Intelligence, the Discovery scanner) states its
OWN minimum for each axis independently — identical in spirit to
`min_confidence` already threading through every `db.py` PIT reader.

## 7. Storage architecture

- **Raw bytes**: `data/archive/<source>_docs/` (xissuer archive already
  exists; new sibling directories per new source type — `news_docs/`,
  `macro_docs/`, `cbn_docs/` — same flat, idempotent, resume-safe harvest
  pattern as `harvest_dol.py`/`harvest_corpaction_docs.py`).
- **Extracted text**: `data/staging/document_text/<doc_id>.txt` (staged,
  not final, until Phase A's coverage report is reviewed — mirrors
  `staging.py`'s quarantine-before-ingest pattern used for prices today).
- **Structured tables**: additive schema in `ngx.sqlite` (§8), migrated
  via the same additive-`ALTER`-then-`executescript` pattern already used
  in `db.init_db`/`db._migrate_events_table` — no new database engine.
- **Reports**: `reports/claim_extraction_quality_<date>.md`,
  `reports/entity_resolution_queue_<date>.md`,
  `reports/document_text_coverage.md` — same Markdown-report convention
  as `event_pipeline.write_quality_report` and the coverage dashboard.
- **Registry/audit trail**: unchanged. This layer's outputs are NOT
  experiments and do not enter `registry.sqlite` — only a promoted,
  pre-registered hypothesis built FROM this layer's aggregated signals
  does, exactly like every prior hypothesis.

## 8. Data model (additive schema — DDL sketch)

```sql
CREATE TABLE IF NOT EXISTS documents (
    doc_id            INTEGER PRIMARY KEY,
    ticker            TEXT REFERENCES securities(ticker),
    doc_type          TEXT NOT NULL,        -- configs/document_taxonomy.toml leaf
    source_type       TEXT NOT NULL,        -- 'filing','news','macro_report','transcript',...
    filing_date       TEXT NOT NULL,
    retrieved_date    TEXT NOT NULL,
    source_url        TEXT,
    local_path        TEXT,
    text_path         TEXT,
    extraction_method TEXT CHECK (extraction_method IN ('native','ocr')),
    char_count        INTEGER,
    source_confidence REAL NOT NULL CHECK (source_confidence BETWEEN 0.0 AND 1.0),
    source_id         INTEGER NOT NULL REFERENCES sources(source_id),
    as_of_date        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id         INTEGER PRIMARY KEY,
    entity_type       TEXT NOT NULL CHECK (entity_type IN
                        ('company','executive','competitor_mention','regulator','sector')),
    canonical_name    TEXT NOT NULL,
    ticker            TEXT REFERENCES securities(ticker),
    first_seen_doc_id INTEGER REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id   INTEGER PRIMARY KEY,
    subject_entity_id INTEGER NOT NULL REFERENCES entities(entity_id),
    relation_type     TEXT NOT NULL,       -- config taxonomy: competitor_of, regulated_by, ...
    object_entity_id  INTEGER NOT NULL REFERENCES entities(entity_id),
    valid_from        TEXT,
    valid_to          TEXT,
    source_evidence_id INTEGER REFERENCES evidence(evidence_id),
    confidence        REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0)
);

CREATE TABLE IF NOT EXISTS entity_mentions (
    mention_id   INTEGER PRIMARY KEY,
    doc_id       INTEGER NOT NULL REFERENCES documents(doc_id),
    entity_id    INTEGER NOT NULL REFERENCES entities(entity_id),
    evidence_id  INTEGER REFERENCES evidence(evidence_id)
);

-- events: EXISTING TABLE, unmodified. New taxonomy leaves added to
-- configs/event_taxonomy.toml only (config change, no schema change).

CREATE TABLE IF NOT EXISTS event_ai_provenance (
    event_id          INTEGER PRIMARY KEY REFERENCES events(event_id),
    extraction_method TEXT NOT NULL CHECK (extraction_method IN ('llm','regex')),
    model_id          TEXT,
    prompt_version    TEXT,
    grounding_check   TEXT NOT NULL DEFAULT 'not_run'
                        CHECK (grounding_check IN ('not_run','passed','failed','overridden')),
    reviewed_by       TEXT,
    reviewed_at       TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id        INTEGER PRIMARY KEY,
    doc_id             INTEGER NOT NULL REFERENCES documents(doc_id),
    event_id           INTEGER REFERENCES events(event_id),
    quoted_text        TEXT NOT NULL,
    page_number        INTEGER,
    char_start         INTEGER,
    char_end           INTEGER,
    source_confidence  REAL NOT NULL CHECK (source_confidence BETWEEN 0.0 AND 1.0)
);

CREATE TABLE IF NOT EXISTS reasoning (
    reasoning_id          INTEGER PRIMARY KEY,
    event_id              INTEGER NOT NULL REFERENCES events(event_id),
    question_type         TEXT NOT NULL CHECK (question_type IN
        ('what_happened','why_it_matters','fundamental_importance',
         'affected_scope','time_horizon','earnings_direction',
         'intrinsic_value_direction','thesis_impact')),
    answer_label          TEXT,             -- e.g. 'increase'/'decrease'/'unclear'
    answer_text           TEXT NOT NULL,
    extraction_confidence REAL NOT NULL CHECK (extraction_confidence BETWEEN 0.0 AND 1.0),
    model_id              TEXT,
    prompt_version        TEXT,
    grounding_check       TEXT NOT NULL DEFAULT 'not_run'
                            CHECK (grounding_check IN ('not_run','passed','failed','overridden')),
    generated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reasoning_evidence (
    reasoning_id  INTEGER NOT NULL REFERENCES reasoning(reasoning_id),
    evidence_id   INTEGER NOT NULL REFERENCES evidence(evidence_id),
    PRIMARY KEY (reasoning_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS investment_implications (
    implication_id          INTEGER PRIMARY KEY,
    event_id                INTEGER NOT NULL REFERENCES events(event_id),
    ticker                  TEXT REFERENCES securities(ticker),
    index_code              TEXT REFERENCES indices(index_code),
    time_horizon            TEXT CHECK (time_horizon IN ('short_term','long_term','unclear')),
    earnings_direction      TEXT CHECK (earnings_direction IN ('increase','decrease','unclear')),
    intrinsic_value_direction TEXT CHECK (intrinsic_value_direction IN
                                ('increase','decrease','unclear')),
    thesis_impact           TEXT CHECK (thesis_impact IN ('strengthens','weakens','neutral')),
    confidence              REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    status                  TEXT NOT NULL DEFAULT 'unvalidated_ai_interpretation'
                              CHECK (status IN ('unvalidated_ai_interpretation','under_review',
                                                 'promoted_to_discovery_candidate','rejected_by_review')),
    propagated_from_implication_id INTEGER REFERENCES investment_implications(implication_id),
    generated_at            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_outlets (
    outlet_name       TEXT PRIMARY KEY,
    reliability_tier  TEXT NOT NULL CHECK (reliability_tier IN ('primary','secondary','unverified')),
    base_confidence   REAL NOT NULL CHECK (base_confidence BETWEEN 0.0 AND 1.0),
    notes             TEXT
);
```

All PIT readers (`documents_asof`, `events_asof` — already exists,
unchanged — `investment_implications_asof`) follow `db.py`'s existing
shape exactly: `filing_date`/`announced_date <= sim_date`,
`as_of_date <= vintage`, `confidence >= min_confidence`, latest-vintage
-wins dedup.

## 9. Interfaces with the existing Fund Alpha platform

New package `src/ngxrot/documents/` (flat module style, matching
`src/ngxrot/`'s existing layout, no new nesting convention introduced):

- `providers.py` — all `DocumentProvider` implementations from §4.1.
- `ocr.py` — `extract_text(doc_path) -> (text, method)`.
- `entities.py` — extraction + the human-reviewable resolution queue.
- `events_ai.py` — event extraction that WRITES INTO the existing
  `events` table via `event_pipeline.ingest_events` (unchanged function),
  plus `event_ai_provenance` rows. No fork of `event_pipeline.py`.
- `evidence.py` — evidence row creation + the grounding checker
  (`check_grounding(quoted_text, source_text) -> GroundingResult`).
- `reasoning.py` — the four reasoning engines (§4.5) as separate,
  independently callable functions sharing one `reasoning` writer;
  `financial_reasoning(event_id, ...)`, `news_reasoning(...)`,
  `macro_reasoning(...)`, `industry_reasoning(...)`.
- `implications.py` — synthesis: `build_implication(event_id, ticker) ->
  InvestmentImplication`, plus `explain(implication_id, con) -> ExplainChain`
  — the mandatory explainability function. `ExplainChain` returns the full
  reasoning → evidence → document path; **no report-generation code
  anywhere on the platform may render an implication without calling this
  function and displaying its result** (a lint-style check, not just a
  convention, to be enforced when report generation is built).
- `discovery_feed.py` — aggregates `investment_implications` into scanner
  -shaped candidate series for `docs/HYPOTHESIS_DISCOVERY_DESIGN.md`'s
  (still design-only) scanner plug-in interface. This is the ONLY function
  in this entire package that produces output the Research Engine may
  consume, and even then only as one candidate among many in a BH
  -corrected scan, never as a pre-approved signal.

**The hard boundary, restated as a code-level fact**: grep
`alpha_engine.py`, `runner.py`, and any future Portfolio Construction
module for imports of `ngxrot.documents` — there should never be one.
Enforced by review, and can be enforced mechanically later with a simple
import-graph lint if desired (not built now — no need pre-exists).

## 10. Multi-exchange support

Nothing in §4-§9 is NGX-specific by construction: `doc_type`/`source_type`
are config-driven; `DocumentProvider` is the same extension point
`DataProvider` already is; `entities`/`events`/`evidence`/`reasoning` carry
no exchange column because they hang off `ticker`/`doc_id`, which
already generalize (a future `securities` row for an NYSE ticker works
identically). The two NGX-specific facts baked into THIS document are (a)
the current provider roster (§4.1's table) and (b) the open finding that
transcripts don't apply to NGX today — both are data-availability facts
about this market, not architecture. Adding NASDAQ, LSE, or JSE later is,
per the charter's Module 12 requirement, a new `DocumentProvider` plus a
`securities`/`sources` registration — the extraction, evidence, reasoning,
and implication layers do not change.

## 11. Governance safeguards — full recap, mechanism-mapped

| Rule | Mechanism |
|---|---|
| Never invent alpha | No portfolio-facing module reads this layer's tables (§9) |
| No black-box outputs | `explain()` chain mandatory before any conclusion is shown (§9) |
| Nothing bypasses pre-registration | Discovery-feed candidates go through the unchanged scanner → BH correction → prereg → gauntlet path (§9) |
| Confidence never hidden or collapsed | Three explicit, separately-thresholded axes (§6) |
| Unknown stays unknown | `UNAVAILABLE_FIELDS` pattern in `company_intelligence.py` extended, not overridden — e.g. intrinsic-value NUMBERS remain unavailable until a financial-statements dataset exists (§4.5) |
| Append-only, auditable | Every new table follows `source_id`/`confidence`/`as_of_date`, no UPDATE/DELETE path designed |
| Rejections are evidence too | Macro Reasoning Engine required to cite H-004/H-005 rejection history where relevant (§4.5) |
| ≤2 active hypotheses, one wave at a time | Unaffected — Discovery-sourced hypotheses queue behind the SAME concurrency rule as any other candidate |

## 12. Implementation roadmap

Phased, each gated on owner review of the prior phase's output — no phase
begins without that review, per standing project discipline.

**Phase A — Foundation.** `documents`, `entities`, `entity_mentions`
schema; ingest metadata + native-text extraction for the existing 11,534
xissuer PDFs; classify by `doc_type` (filing/investor-presentation/
dividend-notice/etc., not yet done at the type level). No LLM calls. →
`reports/document_text_coverage.md`.

**Phase B — Deterministic re-labeling.** Route existing dividend/EPS/
P.E./qualification-date extractors' output through the new schema as
`extraction_method='regex'`, `extraction_confidence=1.0` claims/evidence —
validates the schema against already-known-correct data first.

**Phase C — Entity + event extraction pilot.** ONE claim type
(`dividend_policy_statement`, chosen for its free numeric cross-check),
pilot set = the existing GTCO/Zenith FY2023 anchor documents. Build the
grounding checker and entity-resolution queue against this pilot before
any prompt touches the full archive. Owner reviews precision/recall +
grounding-failure rate before Phase D.

**Phase D — Reasoning engine v0 (Financial only).** Wire
`financial_reasoning()` for the piloted claim type, producing full
`reasoning` + `investment_implications` rows for the pilot set only.
Validates the STRUCTURED-QUESTION schema (§4.5) end-to-end on a small,
human-checkable set before scaling.

**Phase E — Scale + additional reasoning engines.** Expand to remaining
filing-derived claim types; add News Understanding (requires the
`news_outlets` registry populated first, an owner task) and Macroeconomic
Reasoning (reuses existing `macro_series`/`events`, lower new-data
burden, likely faster than News).

**Phase F — Industry Reasoning + knowledge-graph propagation.** Requires
`entity_relationships` populated with enough competitor/regulator edges
from E's extraction to be useful; builds the secondary-implication
propagation logic (§4.5) last, since it depends on both a populated graph
and a settled confidence-discount convention.

**Phase G — Company Intelligence + Discovery integration.** Wire
`qualitative_intelligence` into `CompanyProfile` (badged, per §11);
wire `discovery_feed.py` into the (still design-only) Hypothesis Discovery
scanner, re-checking that design's own ≥200-event / constituent-data
preconditions at this point.

## 13. Open decisions requiring the owner

1. **LLM vendor/model** — **RESOLVED 2026-07-22: Google Gemini
   (`gemini-3.6-flash` default, configurable in `configs/llm_provider.toml`,
   never hardcoded — see `src/ngxrot/documents/llm_providers.py`'s
   `PROVIDER_REGISTRY`/`build_default_provider()`).** Cost-read-on-a-small
   -pilot and third-party-data-sharing confirmation still apply the same
   way they would for any vendor — not waived by this choice, just no
   longer blocking on WHICH vendor.
2. **OCR engine** — pre-existing pending decision (flagged 2026-07-16),
   inherited, not new.
3. **News outlet roster + reliability tiers** — must be owner-judged, not
   AI-inferred (§4.1).
4. **Analyst research licensing** — which providers, if any, the platform
   is legally permitted to ingest; a legal/licensing question, not
   engineering.
5. **Transcript availability for NGX** — needs its own short scoping task
   before the `TranscriptDocumentProvider` is anything more than a stub.
6. **Secondary-implication confidence discount factor** (§4.5, Industry
   Reasoning) — a specific number to agree before Phase F.
7. **Human review staffing/cadence** for the review queues this layer
   creates (event review, entity-merge review, claim review).

## 14. Explicit non-goals

- No numeric intrinsic-value/DCF output until a financial-statements
  dataset is acquired (§4.5) — directional, evidence-cited reasoning only.
- No automatic hypothesis promotion, no automatic retraining, no
  automatic weight changes anywhere in this layer (Module 10 rule,
  unchanged from the initial draft).
- No bypass of the ≤2-active-hypotheses concurrency rule for
  Discovery-sourced candidates.
- Ranking Engine, Portfolio Construction, and Risk Engine remain exactly
  as gated as they are today; this layer changes the CONTENT available to
  them once their own preconditions are met, not the preconditions
  themselves.
