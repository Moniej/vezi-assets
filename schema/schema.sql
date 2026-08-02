-- ============================================================================
-- NGX Sector Rotation — Data Schema (Phase 1)
-- Engine: SQLite (single-file, portable; trivially portable to Postgres later)
--
-- Design principles:
--   1. Point-in-time (PIT) correctness: every observational row carries
--      (source_id, as_of_date). as_of_date = the date we KNEW this value.
--      Restatements/corrections APPEND a new row with a later as_of_date;
--      nothing is ever overwritten. Backtest queries must filter
--      as_of_date <= knowledge_date and take the latest surviving row.
--   2. Lineage: no row without a source. Sources are a registry table.
--   3. Announcement vs effective dates are separate columns everywhere it
--      matters (events, reconstitutions, corporate actions). The backtest
--      may only act on information whose announcement date <= trade date.
--   3b. Confidence scoring: every observation carries confidence in [0,1],
--      defaulted from its source's base_confidence, overridable per row
--      (e.g. upgraded after cross-source verification). Scale convention:
--        1.0 exchange-official, cross-verified   0.9 exchange-official, single
--        0.7 reputable vendor                     0.5 aggregator (investing.com/TV)
--        0.4 manual/unverified                    0.3 web-archive reconstruction
--        0.0 SYNTHETIC/TEST — must never contribute to research conclusions.
--      Robustness tests re-run the backtest at rising min_confidence floors.
--   4. Honest limitation (do not paper over this): if history is
--      RECONSTRUCTED after the fact (e.g., constituent lists scraped from
--      web archives in 2026), as_of_date reflects when WE captured it, not
--      when the market knew it. PIT filtering on as_of_date protects against
--      future revisions; it cannot repair a wrong reconstruction. The
--      announced_date / effective_date columns are the real survivorship
--      defense and must be populated from period-appropriate documents.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 0. Source registry (data lineage)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    source_id     INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,        -- e.g. 'ngx_website_daily_pricelist'
    kind          TEXT NOT NULL CHECK (kind IN
                    ('exchange_official','vendor','regulator','company_filing',
                     'web_archive','manual_entry','derived')),
    url_template  TEXT,                        -- where it came from, if applicable
    reliability   TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (reliability IN ('primary','secondary','unverified','synthetic')),
    base_confidence REAL NOT NULL DEFAULT 0.4
                    CHECK (base_confidence >= 0.0 AND base_confidence <= 1.0),
    notes         TEXT
);

-- ----------------------------------------------------------------------------
-- 1. Reference: indices and securities
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indices (
    index_code    TEXT PRIMARY KEY,            -- 'NGXASI','NGXBNK','NGXINS','NGXOILGAS',
                                               -- 'NGXINDUSTR','NGXCNSMRGDS','NGXPREMIUM',
                                               -- 'NGXPENSION','NGX30'
    name          TEXT NOT NULL,
    weighting     TEXT NOT NULL CHECK (weighting IN
                    ('full_mcap','float_adjusted_mcap','capped_float_mcap','price','equal')),
    cap_pct       REAL,                        -- single-stock cap if capped (e.g. NGX30)
    base_date     TEXT,                        -- ISO date; also = earliest possible history
    base_value    REAL,
    is_total_return INTEGER NOT NULL DEFAULT 0, -- 1 if the published series reinvests divs
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS securities (
    ticker        TEXT PRIMARY KEY,            -- NGX symbol, e.g. 'ZENITHBANK'
    isin          TEXT,
    name          TEXT NOT NULL,
    board         TEXT CHECK (board IN ('main','premium','growth','asem','delisted_unknown')),
    listing_date  TEXT,
    delisting_date TEXT,                       -- NULL if still listed. NEVER delete delisted
                                               -- rows: they are the survivorship-bias defense.
    delisting_reason TEXT,                     -- 'voluntary','regulatory','merger','nationalised',...
    sector_ngx    TEXT,                        -- NGX's own sector classification label
    notes         TEXT
);

-- ----------------------------------------------------------------------------
-- 2. Index level data (daily closes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS index_levels (
    index_code    TEXT NOT NULL REFERENCES indices(index_code),
    trade_date    TEXT NOT NULL,               -- ISO 'YYYY-MM-DD'
    close_value   REAL NOT NULL CHECK (close_value > 0),
    currency      TEXT NOT NULL DEFAULT 'NGN',
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,               -- when this value was captured/known by us
    inserted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (index_code, trade_date, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_index_levels_lookup
    ON index_levels (index_code, trade_date, as_of_date);

-- ----------------------------------------------------------------------------
-- 3. Constituent-level daily prices (what we can actually trade)
--    value_traded is the critical field: it drives ADTV-based capacity
--    constraints in Phase 3.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equity_prices (
    ticker        TEXT NOT NULL REFERENCES securities(ticker),
    trade_date    TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL NOT NULL CHECK (close > 0),
    volume        INTEGER,                     -- shares
    value_traded  REAL,                        -- NGN turnover that day (for ADTV)
    deals         INTEGER,                     -- number of trades (thin-market diagnostic)
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,
    inserted_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (ticker, trade_date, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_equity_prices_lookup
    ON equity_prices (ticker, trade_date, as_of_date);

-- ----------------------------------------------------------------------------
-- 4. Index membership (intervals) and periodic weight snapshots
--    Membership = which stocks were in which index and WHEN (reconstitution
--    history). Weights drift daily with prices, so exact weights are stored
--    as dated snapshots (NGX publishes at reviews); daily weights between
--    snapshots are DERIVED (mcap-proportional) and marked as such via source.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS index_membership (
    index_code     TEXT NOT NULL REFERENCES indices(index_code),
    ticker         TEXT NOT NULL REFERENCES securities(ticker),
    effective_from TEXT NOT NULL,              -- date membership took effect
    effective_to   TEXT,                       -- NULL = still a member
    announced_date TEXT,                       -- when the review result was PUBLIC.
                                               -- Backtest may not use membership
                                               -- before this date. NULL = unknown
                                               -- (treated as effective_from).
    reason_in      TEXT,                       -- 'index_launch','review_add','ipo',...
    reason_out     TEXT,                       -- 'review_drop','delisting','merger',...
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL,
    PRIMARY KEY (index_code, ticker, effective_from, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_membership_lookup
    ON index_membership (index_code, effective_from, effective_to);

CREATE TABLE IF NOT EXISTS constituent_weights (
    index_code     TEXT NOT NULL REFERENCES indices(index_code),
    ticker         TEXT NOT NULL REFERENCES securities(ticker),
    snapshot_date  TEXT NOT NULL,              -- date the weight applies to
    weight         REAL NOT NULL CHECK (weight >= 0 AND weight <= 1),
    free_float_pct REAL,                       -- float factor if known
    is_derived     INTEGER NOT NULL DEFAULT 0, -- 1 = we computed it, not published
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL,
    PRIMARY KEY (index_code, ticker, snapshot_date, source_id, as_of_date)
);

-- ----------------------------------------------------------------------------
-- 5. Corporate actions
--    NGX mechanics: price is marked down on the QUALIFICATION date (NGX's
--    ex-date analogue). Total-return adjustment keys off markdown_date.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id      INTEGER PRIMARY KEY,
    ticker         TEXT NOT NULL REFERENCES securities(ticker),
    action_type    TEXT NOT NULL CHECK (action_type IN
                     ('dividend_cash','dividend_interim','dividend_scrip','bonus',
                      'stock_split','reverse_split','rights_issue','public_offer',
                      'private_placement','share_reconstruction','delisting',
                      'suspension','resumption','merger','capital_return')),
    declared_date  TEXT,                       -- announcement (PIT anchor)
    qualification_date TEXT,                   -- NGX qualification/closure-of-register
    markdown_date  TEXT,                       -- date price adjusts on the board
    payment_date   TEXT,
    dividend_per_share REAL,                   -- NGN, for dividend_*
    ratio_new      REAL,                       -- for bonus/split/rights: new shares...
    ratio_old      REAL,                       -- ...per old shares (e.g. bonus 1-for-4)
    rights_price   REAL,                       -- subscription price for rights
    currency       TEXT NOT NULL DEFAULT 'NGN',
    withholding_tax_pct REAL DEFAULT 10.0,     -- NGN dividend WHT (confirm rate/applicability)
    details        TEXT,
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_corp_actions_ticker
    ON corporate_actions (ticker, markdown_date);

-- ----------------------------------------------------------------------------
-- 6. Regulatory / macro event calendar
--    announced_date vs effective_date is the whole point of this table:
--    e.g. CBN recapitalisation circular announced 2024-03-28, deadline
--    2026-03-31. A catalyst filter may react on 2024-03-28, not before.
-- ----------------------------------------------------------------------------
-- Event types are validated against configs/event_taxonomy.toml by the event
-- pipeline (ngxrot/event_pipeline.py), NOT by a CHECK constraint — the
-- taxonomy is configurable per the H-003 research design. Chronology,
-- duplicate, and cross-source-conflict checks also live in the pipeline.
CREATE TABLE IF NOT EXISTS events (
    event_id       INTEGER PRIMARY KEY,
    event_type     TEXT NOT NULL,             -- taxonomy leaf (pipeline-validated)
    event_uid      TEXT,                      -- stable source-assigned ID (e.g.
                                              -- 'CBN-MPC-295'). Restatements share
                                              -- the uid; PIT reads keep the latest
                                              -- as_of per uid. NULL = no uid known.
    category       TEXT,                      -- taxonomy branch: monetary/banking/...
    announced_date TEXT NOT NULL,             -- when the market learned of it
    effective_date TEXT,                      -- when it takes/took effect (NULL = unknown)
    publication_ts TEXT,                      -- exact publication timestamp if knowable
    scope          TEXT NOT NULL CHECK (scope IN ('market','sector','ticker')),
    index_code     TEXT REFERENCES indices(index_code),   -- if sector-scoped
    ticker         TEXT REFERENCES securities(ticker),    -- if ticker-scoped
    headline       TEXT NOT NULL,
    outcome_numeric REAL,                     -- e.g. MPR level after MPC (27.50)
    outcome_text   TEXT,                      -- e.g. 'hold', 'hike +50bps'
    severity       TEXT CHECK (severity IN ('low','medium','high','critical')),
    direction      TEXT NOT NULL DEFAULT 'unknown'
                     CHECK (direction IN ('bullish','bearish','neutral','unknown')),
    structurally_impairing INTEGER NOT NULL DEFAULT 0,
    source_url     TEXT,                      -- primary document URL where possible
    notes          TEXT,                      -- supporting notes incl. verification trail
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    confidence     REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_dates ON events (announced_date, event_type);

-- ----------------------------------------------------------------------------
-- 7. FX rates (regime definition + real-return sanity checks)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fx_rates (
    trade_date    TEXT NOT NULL,
    rate_type     TEXT NOT NULL CHECK (rate_type IN ('official','nafem','parallel')),
    ngn_per_usd   REAL NOT NULL CHECK (ngn_per_usd > 0),
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,
    PRIMARY KEY (trade_date, rate_type, source_id, as_of_date)
);

-- ----------------------------------------------------------------------------
-- 7b. Generic macro/commodity daily series (Brent, T-bills, CPI level, ...)
--     Reusable home for any external daily/periodic series feeding models.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS macro_series (
    series_code   TEXT NOT NULL,               -- 'BRENT', 'NGN_TBILL_91D', ...
    trade_date    TEXT NOT NULL,
    value         REAL NOT NULL,
    source_id     INTEGER NOT NULL REFERENCES sources(source_id),
    confidence    REAL NOT NULL DEFAULT 0.4 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    as_of_date    TEXT NOT NULL,
    PRIMARY KEY (series_code, trade_date, source_id, as_of_date)
);
CREATE INDEX IF NOT EXISTS ix_macro_series ON macro_series (series_code, trade_date);

-- ----------------------------------------------------------------------------
-- 8. Transaction cost schedule (effective-dated, overridable — Phase 3 input)
--    Seeded with ASSUMED NGX retail fee stack; every rate must be confirmed
--    against a real broker contract note before results are trusted.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cost_schedule (
    fee_name       TEXT NOT NULL,              -- 'brokerage','sec_fee','ngx_fee',
                                               -- 'cscs_fee','stamp_duty','vat'
    side           TEXT NOT NULL CHECK (side IN ('buy','sell','both')),
    rate_pct       REAL NOT NULL,              -- % of trade value (VAT: % of fees)
    applies_to     TEXT NOT NULL DEFAULT 'trade_value'
                     CHECK (applies_to IN ('trade_value','commission_and_fees')),
    effective_from TEXT NOT NULL,
    effective_to   TEXT,
    confidence     TEXT NOT NULL DEFAULT 'assumed'
                     CHECK (confidence IN ('confirmed','assumed')),
    source_id      INTEGER NOT NULL REFERENCES sources(source_id),
    notes          TEXT,
    PRIMARY KEY (fee_name, side, effective_from)
);

-- ----------------------------------------------------------------------------
-- 9. Data quality log (Phase 3 diagnostics write here)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_quality_log (
    check_name    TEXT NOT NULL,               -- 'unadjusted_jump','stale_series',
                                               -- 'missing_days','weight_sum_error',...
    entity_type   TEXT NOT NULL CHECK (entity_type IN ('index','ticker')),
    entity_code   TEXT NOT NULL,
    trade_date    TEXT,
    severity      TEXT NOT NULL CHECK (severity IN ('info','warn','error')),
    detail        TEXT,
    resolved      INTEGER NOT NULL DEFAULT 0,
    logged_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ----------------------------------------------------------------------------
-- 10. AI Intelligence Layer — Phase A foundation (docs/AI_INTELLIGENCE_LAYER_
--     ARCHITECTURE.md). documents = one row per filing/document, whether or
--     not its text has been extracted yet. entities/entity_mentions are
--     schema-only in Phase A (populated starting Phase C) — created now so
--     later phases are additive-column migrations, not new tables.
--     ticker is nullable + a REFERENCES constraint: many archived filings use
--     pre-rename symbols (GUARANTY, FBNH, ...) not in `securities` yet; only
--     VERIFIED renames (data/reference/symbol_renames.csv, status='verified')
--     resolve to ticker, everything else stays NULL with raw_symbol preserved
--     verbatim — "unknown stays unknown", never a guessed match.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    doc_id            INTEGER PRIMARY KEY,
    ticker            TEXT REFERENCES securities(ticker),
    raw_symbol        TEXT,                      -- as disclosed, pre-rename-resolution
    doc_type          TEXT NOT NULL,              -- configs/document_taxonomy.toml leaf
    source_type       TEXT NOT NULL DEFAULT 'filing',
    filing_date       TEXT NOT NULL,              -- announced/created date (market's knowledge date)
    retrieved_date    TEXT NOT NULL,
    source_url        TEXT,
    local_path        TEXT NOT NULL,
    text_path         TEXT,                       -- NULL until text is extracted
    extraction_method TEXT CHECK (extraction_method IN ('native','ocr')),
                                                   -- NULL = not yet extracted (OCR-pending)
    char_count        INTEGER,
    source_confidence REAL NOT NULL DEFAULT 0.0 CHECK (source_confidence BETWEEN 0.0 AND 1.0),
                                                   -- 0.0 until text is usably extracted
    source_id         INTEGER NOT NULL REFERENCES sources(source_id),
    as_of_date        TEXT NOT NULL,
    -- Phase C additions (docs/REASONING_ENGINE_SPECIFICATION.md §2, Step 1
    -- "Identify"). Native here for fresh databases; existing populated
    -- databases get these via the ALTER-with-try/except in db.py's
    -- init_db() (CREATE TABLE IF NOT EXISTS does not add columns to a
    -- table that already exists — same reason event_uid is handled both
    -- places for `events`).
    sector             TEXT,
    exchange           TEXT DEFAULT 'NGX',
    country            TEXT DEFAULT 'NG',
    event_date         TEXT,
    news_classification TEXT
);
CREATE INDEX IF NOT EXISTS ix_documents_ticker ON documents (ticker);
CREATE INDEX IF NOT EXISTS ix_documents_doc_type ON documents (doc_type);

CREATE TABLE IF NOT EXISTS entities (
    entity_id         INTEGER PRIMARY KEY,
    -- Widened 2026-08-01 (docs/fre/02_knowledge_graph_expansion.md, FRE-1):
    -- 'commodity'/'macro_variable'/'subsidiary'/'index' added. Purely
    -- additive to the CHECK set -- every pre-existing row's entity_type
    -- ('company'/'competitor_mention', the only two ever populated so far)
    -- remains valid. A fresh DB gets this widened CHECK directly from this
    -- CREATE TABLE; an existing DB is migrated via db.py's
    -- _migrate_entities_table() (table-rebuild, same pattern as
    -- _migrate_events_table -- SQLite cannot ALTER an existing CHECK).
    entity_type       TEXT NOT NULL CHECK (entity_type IN
                        ('company','executive','competitor_mention','regulator','sector',
                         'commodity','macro_variable','subsidiary','index')),
    canonical_name    TEXT NOT NULL,
    ticker            TEXT REFERENCES securities(ticker),
    first_seen_doc_id INTEGER REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS entity_mentions (
    mention_id   INTEGER PRIMARY KEY,
    doc_id       INTEGER NOT NULL REFERENCES documents(doc_id),
    entity_id    INTEGER NOT NULL REFERENCES entities(entity_id)
);

-- ----------------------------------------------------------------------------
-- 11. AI Intelligence Layer — Phase B (docs/AI_INTELLIGENCE_LAYER_
--     ARCHITECTURE.md §4.4, docs/REASONING_ENGINE_SPECIFICATION.md §3-4).
--     evidence = the exact citation backing a fact (architecture doc §4.4).
--     extracted_facts = one row per material fact (spec §3), extended here
--     with numeric_value/qualification_date/payment_date/agm_date/
--     closure_date — a Phase B refinement: the design sketch had no place
--     to put a REGEX-extracted number/date, only a prose `description`.
--     Kept nullable/generic rather than one column per fact_type so the
--     table doesn't grow a column per future taxonomy leaf; qualification_
--     date/payment_date/agm_date/closure_date are specific to corporate
--     -action facts today but are generic enough to be reused as-is by any
--     future fact_type with an analogous shape (e.g. AGM date for a
--     governance fact) rather than adding parallel fact_type-specific ones.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id       INTEGER PRIMARY KEY,
    doc_id            INTEGER NOT NULL REFERENCES documents(doc_id),
    event_id          INTEGER,               -- reserved for Phase C+ (events table linkage)
    quoted_text       TEXT NOT NULL,
    page_number       INTEGER,
    char_start        INTEGER,
    char_end          INTEGER,
    source_confidence REAL NOT NULL CHECK (source_confidence BETWEEN 0.0 AND 1.0)
);

CREATE TABLE IF NOT EXISTS extracted_facts (
    fact_id               INTEGER PRIMARY KEY,
    doc_id                INTEGER NOT NULL REFERENCES documents(doc_id),
    fact_type             TEXT NOT NULL,      -- configs/fact_taxonomy.toml leaf
    description           TEXT NOT NULL,
    numeric_value         REAL,               -- e.g. dividend_per_share
    qualification_date    TEXT,
    payment_date          TEXT,
    agm_date              TEXT,
    closure_date          TEXT,
    -- Added 2026-08-01, FSI Phase 1 (docs/fre_runs/fsi_phase1_preregistration.md):
    -- a financial-statement line item (revenue/net_profit) needs a fiscal
    -- PERIOD, distinct from the corporate-action-specific dates above.
    -- Nullable, additive -- no existing row is affected. For a pre-existing
    -- database these are added via db.py's init_db() ALTER TABLE calls
    -- (this CREATE TABLE only takes effect on a fresh database), per the
    -- same convention documented for causal_chain_steps' FRE-1 columns.
    period_start          TEXT,
    period_end            TEXT,
    -- Added 2026-08-01, FSI Phase 2 (docs/fre_runs/fsi_phase2_execution_plan.md
    -- section 4.1). All three nullable, additive -- no existing row is
    -- affected. For a pre-existing database these are added via db.py's
    -- init_db() ALTER TABLE calls, same convention as every prior addition.
    -- period_type: derived from the actual period_start/period_end span,
    -- NEVER from a filing's own headline label (the real, confirmed reason:
    -- UCAP's "Q3 2020" headline described what was actually a 9-month
    -- cumulative period -- see fsi_phase2_implementation_log.md).
    period_type           TEXT CHECK (period_type IN ('Q1','Q2','Q3','Q4','H1','H2','9M','FY')),
    -- confidence_tier: a QUALITATIVE dimension distinct from the existing
    -- numeric extraction_confidence float below -- see docs/fre_runs/
    -- fsi_phase2_execution_plan.md section 2 for the four-tier definition.
    -- 'interpretation' is a defined, real value in this CHECK constraint,
    -- but is never written by any Phase 2 extraction script -- the schema
    -- permits it (so a future, explicitly-approved phase could use it) but
    -- the current pipeline code enforces "no inferred financial facts" by
    -- simply never producing that tier.
    confidence_tier        TEXT CHECK (confidence_tier IN
                             ('direct_reported','mapped_equivalent','derived','interpretation')),
    -- restates_fact_id: self-referencing, nullable -- modeled directly on
    -- investment_implications.corroborates_implication_id/.contradicts_
    -- implication_id (architecture doc Sec 8, proven, already-audited
    -- pattern). A fact with this set restates an earlier fact for an
    -- overlapping period at a different value; BOTH rows stand, append
    -- -only, exactly like every other table on this platform -- never an
    -- UPDATE, never a delete of the original.
    restates_fact_id       INTEGER REFERENCES extracted_facts(fact_id),
    evidence_id           INTEGER REFERENCES evidence(evidence_id),
    extraction_confidence REAL NOT NULL CHECK (extraction_confidence BETWEEN 0.0 AND 1.0),
    model_id              TEXT,               -- NULL for regex/manual
    prompt_version        TEXT,               -- NULL for regex/manual
    grounding_check        TEXT NOT NULL DEFAULT 'not_run'
                             CHECK (grounding_check IN ('not_run','passed','failed','overridden')),
    extracted_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_extracted_facts_doc ON extracted_facts (doc_id);
CREATE INDEX IF NOT EXISTS ix_extracted_facts_type ON extracted_facts (fact_type);

-- ----------------------------------------------------------------------------
-- 12. AI Intelligence Layer — Phase C (docs/REASONING_ENGINE_SPECIFICATION.md
--     §2-3, §12). Step-1 identification columns on `documents`, plus the full
--     reasoning chain: causal_chain_steps, impact_assessments,
--     investment_implications (fact_id-keyed — supersedes the architecture
--     doc's older event_id-keyed sketch, per the reasoning spec's revision),
--     effect_chains, research_task_candidates, self_critique_reviews.
--     entity_relationships (architecture doc §8) added for schema completeness
--     even though this pilot's single-document scope is unlikely to populate
--     it much. All additive; nothing above this line is touched.
--     NOTE: documents' new Step-1 identification columns (sector/exchange/
--     country/event_date/news_classification) are added via ALTER TABLE in
--     db.py's init_db(), NOT here — ALTER TABLE is not idempotent under
--     sqlite (no "ADD COLUMN IF NOT EXISTS"), so it can't live inside this
--     executescript-run file; it follows the exact try/except OperationalError
--     pattern already used there for events.event_uid.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id     INTEGER PRIMARY KEY,
    subject_entity_id   INTEGER NOT NULL REFERENCES entities(entity_id),
    relation_type       TEXT NOT NULL,
    object_entity_id    INTEGER NOT NULL REFERENCES entities(entity_id),
    valid_from          TEXT,
    valid_to            TEXT,
    source_evidence_id  INTEGER REFERENCES evidence(evidence_id),
    confidence          REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0)
);

CREATE TABLE IF NOT EXISTS causal_chain_steps (
    chain_id      INTEGER PRIMARY KEY,
    fact_id       INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    step_order    INTEGER NOT NULL,
    statement     TEXT NOT NULL,
    inferred      INTEGER NOT NULL DEFAULT 0,
    evidence_id   INTEGER REFERENCES evidence(evidence_id),
    -- Added 2026-08-01 (FRE-1): both nullable, narrative/mechanism tags,
    -- never required for a pre-FRE row to remain valid. implication_layer
    -- = docs/fre/03_evidence_graph.md's financial/business/competitive
    -- staging of a causal chain. reasoning_mode = docs/fre/
    -- 04_reasoning_engine.md's ten reasoning modes. Existing rows keep
    -- both NULL -- a CHECK is satisfied (not violated) by NULL under
    -- standard SQL semantics, same convention as documents.extraction_
    -- method/news_classification elsewhere in this file. For a pre-existing
    -- database, these columns are added via db.py's init_db() ALTER TABLE
    -- calls (this CREATE TABLE only takes effect on a fresh database),
    -- per the convention documented above entity_relationships.
    implication_layer TEXT CHECK (implication_layer IN
                        ('financial','business','competitive')),
    reasoning_mode     TEXT CHECK (reasoning_mode IN
                        ('causal','counterfactual','historical','trend','comparative',
                         'sector','macro','valuation','uncertainty','portfolio')),
    UNIQUE (fact_id, step_order)
);

CREATE TABLE IF NOT EXISTS impact_assessments (
    assessment_id  INTEGER PRIMARY KEY,
    fact_id        INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    category       TEXT NOT NULL CHECK (category IN
                     ('revenue','margins','cash_flow','capital_allocation','balance_sheet',
                      'growth','competitive_advantage','execution_risk','regulatory_risk',
                      'liquidity','valuation','market_expectations','long_term_moat')),
    direction      TEXT NOT NULL CHECK (direction IN
                     ('positive','negative','neutral','mixed','unknown')),
    explanation    TEXT NOT NULL,
    evidence_id    INTEGER REFERENCES evidence(evidence_id),
    UNIQUE (fact_id, category)
);

CREATE TABLE IF NOT EXISTS investment_implications (
    implication_id              INTEGER PRIMARY KEY,
    fact_id                     INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    ticker                      TEXT REFERENCES securities(ticker),
    index_code                  TEXT REFERENCES indices(index_code),
    model_id                    TEXT,        -- 2026-07-22 hardening: the draft
                                             -- model/prompt that produced THIS
                                             -- reasoning record, not just the
                                             -- parent fact (queryable without
                                             -- a join; a future prompt version
                                             -- never overwrites this — it is a
                                             -- new row, this stays put)
    prompt_version               TEXT,
    duration_bucket             TEXT NOT NULL CHECK (duration_bucket IN
                                  ('very_short','short','medium','long','structural','permanent')),
    magnitude                   TEXT NOT NULL CHECK (magnitude IN
                                  ('tiny','small','medium','large','transformational')),
    confidence                  REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    confidence_rationale        TEXT NOT NULL,
    direction                   TEXT NOT NULL DEFAULT 'unknown'
                                  CHECK (direction IN ('bullish','bearish','neutral','unknown')),
    assumptions                 TEXT,             -- explicit statement of what's being assumed —
                                                    -- "never fabricate missing data" made checkable:
                                                    -- an assumption stated here, not silently baked
                                                    -- into a conclusion
    bull_case_delta             TEXT,
    bear_case_delta             TEXT,
    base_case_delta             TEXT,
    intrinsic_value_direction   TEXT CHECK (intrinsic_value_direction IN
                                  ('increase','decrease','unclear')),
    intrinsic_value_reasoning   TEXT,
    expected_earnings_direction TEXT CHECK (expected_earnings_direction IN
                                  ('increase','decrease','unclear')),
    target_multiple_direction   TEXT CHECK (target_multiple_direction IN
                                  ('increase','decrease','unclear','not_assessed')),
    risk_profile_direction      TEXT CHECK (risk_profile_direction IN
                                  ('increase','decrease','unclear','not_assessed')),
    portfolio_sizing_note       TEXT,
    action_recommendation       TEXT NOT NULL CHECK (action_recommendation IN
                                  ('no_action','watchlist','research_task','model_update',
                                   'valuation_update','factor_candidate','immediate_review')),
    corroborates_implication_id INTEGER REFERENCES investment_implications(implication_id),
    contradicts_implication_id  INTEGER REFERENCES investment_implications(implication_id),
    consistency_note             TEXT,
    market_reaction_assessment  TEXT CHECK (market_reaction_assessment IN
                                  ('underreacting','overreacting','fairly_priced','unclear')),
    market_reaction_reasoning   TEXT,
    status                      TEXT NOT NULL DEFAULT 'draft_pending_self_critique'
                                  CHECK (status IN ('draft_pending_self_critique',
                                                     'blocked_by_self_critique',
                                                     'unvalidated_ai_interpretation','under_review',
                                                     'promoted_to_discovery_candidate','rejected_by_review')),
    propagated_from_implication_id INTEGER REFERENCES investment_implications(implication_id),
    generated_at                TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_implications_fact ON investment_implications (fact_id);
CREATE INDEX IF NOT EXISTS ix_implications_ticker ON investment_implications (ticker);
CREATE INDEX IF NOT EXISTS ix_implications_status ON investment_implications (status);

CREATE TABLE IF NOT EXISTS effect_chains (
    effect_id          INTEGER PRIMARY KEY,
    implication_id     INTEGER NOT NULL REFERENCES investment_implications(implication_id),
    order_n            INTEGER NOT NULL CHECK (order_n IN (1, 2, 3)),
    description        TEXT NOT NULL,
    affected_entity_id INTEGER REFERENCES entities(entity_id),
    evidence_id        INTEGER REFERENCES evidence(evidence_id)
);

CREATE TABLE IF NOT EXISTS research_task_candidates (
    task_id        INTEGER PRIMARY KEY,
    implication_id INTEGER NOT NULL REFERENCES investment_implications(implication_id),
    description    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'open'
                     CHECK (status IN ('open','in_review','promoted','dismissed')),
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS self_critique_reviews (
    critique_id      INTEGER PRIMARY KEY,
    implication_id   INTEGER NOT NULL REFERENCES investment_implications(implication_id),
    question         TEXT NOT NULL CHECK (question IN
                        ('unevidenced_inference', 'correlation_vs_causation',
                         'ignored_alternative_explanation', 'single_document_overreaction',
                         'contradicts_prior_evidence', 'insufficient_information',
                         'confidence_improving_information', 'market_noise_check')),
    finding          TEXT NOT NULL CHECK (finding IN ('pass', 'concern', 'fail')),
    explanation      TEXT NOT NULL,
    resulting_action TEXT NOT NULL CHECK (resulting_action IN
                        ('none', 'confidence_lowered', 'status_downgraded',
                         'research_task_created', 'flagged_for_human_review')),
    model_id         TEXT NOT NULL,
    prompt_version   TEXT NOT NULL,
    reviewed_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_critique_implication ON self_critique_reviews (implication_id);

-- Full audit trail of every LLM call (draft reasoning AND self-critique),
-- whether served from cache or a live request — "store every prompt,
-- response, token usage and model version" as a queryable table, not just
-- the on-disk JSON cache (data/staging/llm_cache/) which is a performance/
-- reproducibility mechanism, not the audit record of truth.
CREATE TABLE IF NOT EXISTS llm_calls (
    call_id         INTEGER PRIMARY KEY,
    doc_id          INTEGER REFERENCES documents(doc_id),
    purpose         TEXT NOT NULL CHECK (purpose IN ('draft_reasoning', 'self_critique')),
    model_id        TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    document_hash   TEXT,        -- 2026-07-22 hardening: sha256 of the source
                                 -- document text alone (distinct from
                                 -- cache_key, which hashes the full prompt) —
                                 -- makes "did this document's TEXT change
                                 -- since it was last processed" an explicit,
                                 -- auditable query instead of an implicit
                                 -- side-effect of the cache key
    system_prompt   TEXT NOT NULL,
    user_prompt     TEXT NOT NULL,
    response_text   TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    stop_reason     TEXT,
    request_id      TEXT,
    cache_key       TEXT NOT NULL,
    served_from_cache INTEGER NOT NULL DEFAULT 0,
    latency_s       REAL,
    called_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_llm_calls_doc ON llm_calls (doc_id);
CREATE INDEX IF NOT EXISTS ix_llm_calls_cache_key ON llm_calls (cache_key);
CREATE INDEX IF NOT EXISTS ix_llm_calls_document_hash ON llm_calls (document_hash);

-- ----------------------------------------------------------------------------
-- FSI Phase 3 (docs/fre_runs/fsi_phase3_preregistration.md Area 6):
-- Financial Reasoning conclusions -- ratios, trends, and rule-based health
-- flags DERIVED from already-validated extracted_facts (FSI Phase 1-2). No
-- new fact_type, no new document, no valuation output. Append-only: a rerun
-- under a new rule_version inserts new rows, never overwrites old ones,
-- exactly like restates_fact_id/investment_implications elsewhere in this
-- file. confidence_tier is NULLABLE and a NULL result is a real, meaningful
-- signal ("this conclusion's confidence floor is unknown because at least
-- one input fact predates the confidence_tier column and was never
-- backfilled" -- Phase 1's own 30 original facts) -- never silently upgraded
-- to a real tier.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS financial_reasoning_conclusions (
    conclusion_id   INTEGER PRIMARY KEY,
    ticker          TEXT NOT NULL,
    conclusion_type TEXT NOT NULL CHECK (conclusion_type IN ('ratio', 'trend', 'flag')),
    metric          TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('computed', 'insufficient_data')),
    value_numeric   REAL,             -- ratio value, or pct change for a trend; NULL if insufficient_data
    value_text      TEXT,             -- e.g. 'increasing'/'decreasing'/'stable' for a trend, or a flag's own name
    confidence_tier TEXT CHECK (confidence_tier IN
                       ('direct_reported', 'mapped_equivalent', 'derived', 'interpretation')),
    method          TEXT NOT NULL,    -- e.g. "debt_to_equity = liabilities / equity" -- the exact calculation, never left implicit
    limitations     TEXT NOT NULL,    -- always populated, even for a clean 'computed' result (e.g. period-span caveats)
    rule_version    TEXT NOT NULL,    -- distinguishes a rule-set change from a data change; never overwritten
    period_start    TEXT,             -- the (later, for a trend) period this conclusion is about
    period_end      TEXT,
    computed_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fr_conclusions_ticker ON financial_reasoning_conclusions (ticker);
CREATE INDEX IF NOT EXISTS ix_fr_conclusions_type_metric ON financial_reasoning_conclusions (conclusion_type, metric);

-- Join table, not a free-text blob, per the pre-registration's own explicit
-- requirement ("input_fact_ids (a traceable list/join table)") -- every
-- conclusion's exact source facts are queryable, not embedded as text.
CREATE TABLE IF NOT EXISTS financial_reasoning_conclusion_facts (
    conclusion_id INTEGER NOT NULL REFERENCES financial_reasoning_conclusions(conclusion_id),
    fact_id       INTEGER NOT NULL REFERENCES extracted_facts(fact_id),
    role          TEXT NOT NULL,   -- e.g. 'numerator', 'denominator', 'earlier_period', 'later_period', 'input'
    PRIMARY KEY (conclusion_id, fact_id, role)
);

-- 2026-07-22 hardening: per-document pilot processing lifecycle — what
-- makes run_phase_c_pilot.py resumable. The status here is the fast,
-- authoritative "should I skip this document" signal; the actual
-- extracted_facts/investment_implications rows remain the source of truth
-- for what was actually produced (a resume checks BOTH — see
-- pipeline_status.py — so a stale/crashed status row can never cause a
-- document to be silently re-extracted and duplicated).
CREATE TABLE IF NOT EXISTS document_processing_status (
    doc_id            INTEGER PRIMARY KEY REFERENCES documents(doc_id),
    status            TEXT NOT NULL CHECK (status IN
                        ('pending', 'processing', 'completed', 'failed',
                         'quota_exceeded', 'blocked_by_self_critique')),
    fact_count        INTEGER,
    implication_count INTEGER,
    error_detail      TEXT,
    model_id          TEXT,
    prompt_version    TEXT,
    started_at        TEXT,
    updated_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_doc_status_status ON document_processing_status (status);

-- ----------------------------------------------------------------------------
-- FSI Phase 18 (docs/fre_runs/fsi_phase18_preregistration.md): Watchlist
-- persistence -- Part 9's own Tier-1 "Watchlist" capability
-- (docs/fre/09_portfolio_reasoning.md), the last of its three Tier-1
-- items to be built (Screening: Phase 14/15; Portfolio memory: Phase
-- 17). Append-only: a watchlist entry is never deleted, only marked
-- removed via removed_at/removal_reason (same convention as
-- securities.delisting_date and restates_fact_id elsewhere in this
-- file) -- the full history of what was ever watchlisted, and why, is
-- always reconstructible. entry_criteria is NOT NULL by design, per
-- Part 9's own explicit requirement: "what would need to be true for
-- this to become portfolio-relevant" is written down BEFORE it's met,
-- not rationalized after -- this platform's own pre-registration
-- discipline applied to watchlist membership. source_thesis_as_of_date
-- is a reproducible POINTER (ticker + this date), never a stored copy
-- of CompanyThesis360's own data -- the same convention every other PIT
-- object on this platform uses.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS watchlist_entries (
    watchlist_entry_id       INTEGER PRIMARY KEY,
    ticker                   TEXT NOT NULL REFERENCES securities(ticker),
    added_at                 TEXT NOT NULL,
    rationale                TEXT NOT NULL,
    source_thesis_as_of_date TEXT NOT NULL,
    review_cadence           TEXT,
    entry_criteria           TEXT NOT NULL,
    removed_at               TEXT,
    removal_reason           TEXT
);
CREATE INDEX IF NOT EXISTS ix_watchlist_entries_ticker ON watchlist_entries (ticker);

-- FSI Phase 23: full provenance for every securities.sector_ngx value
-- ever populated -- source, retrieval date, and document/URL, mirroring
-- the same "never a bare value with no traceable source" discipline
-- extracted_facts/evidence already establish. One row per populated
-- ticker; sector_ngx here always matches the value written to
-- securities.sector_ngx at the time of population.
CREATE TABLE IF NOT EXISTS sector_ngx_provenance (
    provenance_id   INTEGER PRIMARY KEY,
    ticker          TEXT NOT NULL REFERENCES securities(ticker),
    sector_ngx      TEXT NOT NULL,
    sub_industry    TEXT,
    board_section   TEXT,
    source_document TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    retrieval_date  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sector_ngx_provenance_ticker ON sector_ngx_provenance (ticker);

-- ----------------------------------------------------------------------------
-- Point-in-time views: latest as_of per (entity, trade_date).
-- The Python layer exposes as-of-a-knowledge-date variants of these.
-- ----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_index_levels_latest AS
SELECT il.*
FROM index_levels il
JOIN (
    SELECT index_code, trade_date, MAX(as_of_date) AS max_asof
    FROM index_levels GROUP BY index_code, trade_date
) m ON il.index_code = m.index_code
   AND il.trade_date = m.trade_date
   AND il.as_of_date = m.max_asof;

CREATE VIEW IF NOT EXISTS v_equity_prices_latest AS
SELECT ep.*
FROM equity_prices ep
JOIN (
    SELECT ticker, trade_date, MAX(as_of_date) AS max_asof
    FROM equity_prices GROUP BY ticker, trade_date
) m ON ep.ticker = m.ticker
   AND ep.trade_date = m.trade_date
   AND ep.as_of_date = m.max_asof;
