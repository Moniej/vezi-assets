"""Database layer for the NGX sector-rotation system.

All read paths intended for backtesting are point-in-time (PIT) along TWO
separate time axes:

  sim_date  — the simulation/trade date. Filters what the MARKET knew:
              trade_date <= sim_date, announced_date <= sim_date. This is the
              lookahead guard the backtest loop moves forward day by day.
  vintage   — the data capture vintage. Filters OUR knowledge:
              as_of_date <= vintage, latest surviving capture wins. Defaults
              to None = use everything (latest restatements). A validation
              run pins vintage to a freeze date so later data corrections
              cannot silently change published results.

These are different things: backfilled history captured today has
as_of_date = today for 2016 trade dates — sim_date must still be able to
walk through 2016. Phase 2/3 code must go through these helpers, never raw
SELECTs on the base tables.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

PKG_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = PKG_ROOT / "schema"

# Incident, 2026-08-01 (docs/fre_runs/incident_2026-08-01_prod_db_wipe.md):
# two old smoke/demo scripts hardcoded this exact literal path and called
# `.unlink()` on it directly, bypassing this module entirely, which deleted
# the real production database. DEFAULT_DB now honors an NGXROT_DB_PATH
# environment override so any script that relies on the default (via
# connect()/init_db() with no explicit path) can be redirected to a scratch
# location by CONFIGURATION -- e.g. in a CI/sandboxed test run -- without
# touching that script's code. This does NOT protect a script that hardcodes
# its own literal path instead of using DEFAULT_DB (as both incident scripts
# did) -- see new_scratch_db_path()/assert_not_default_db() below for that
# case, and scripts/check_db_safety.py for the automated audit that now
# catches the hardcoded-path pattern itself.
DEFAULT_DB = Path(os.environ.get("NGXROT_DB_PATH", str(PKG_ROOT / "data" / "ngx.sqlite")))


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def new_scratch_db_path() -> Path:
    """A throwaway database path for a smoke test / demo / rehearsal script
    that wants a fresh, empty database -- guaranteed never to collide with
    DEFAULT_DB. This is the ONE sanctioned way to get a "fresh empty DB for
    a one-off script" on this platform; prefer it over hand-rolling
    `ROOT / "data" / "ngx.sqlite"` + `.unlink()`, which is exactly the
    pattern that caused the 2026-08-01 production-database wipe (see
    DEFAULT_DB's comment above). The directory is fresh (tempfile.mkdtemp())
    so no unlink is ever needed before use.
    """
    return Path(tempfile.mkdtemp()) / "scratch.sqlite"


def assert_not_default_db(path: str | Path) -> None:
    """Defense-in-depth guard: raise if `path` resolves to DEFAULT_DB.
    Call this before any destructive operation (unlink/DROP/wholesale
    overwrite) in a script that must never be allowed to target the real
    production database. Cheap, explicit, and independent of whether the
    caller remembered to use new_scratch_db_path() instead."""
    if Path(path).resolve() == DEFAULT_DB.resolve():
        raise RuntimeError(
            f"Refusing a destructive operation against the production "
            f"database at {DEFAULT_DB} -- use db.new_scratch_db_path() for "
            f"a smoke test/demo/rehearsal script instead."
        )


def init_db(db_path: str | Path = DEFAULT_DB, seed: bool = True) -> sqlite3.Connection:
    """Create all tables/views and (optionally) load reference seeds."""
    con = connect(db_path)
    _migrate_events_table(con)
    _migrate_entities_table(con)
    # additive migration, 2026-08-01 (FRE-1, docs/fre/03_evidence_graph.md +
    # docs/fre/04_reasoning_engine.md): both nullable, no existing row is
    # affected. schema.sql's CREATE TABLE IF NOT EXISTS already carries
    # these for a fresh database; this covers a database that already has
    # causal_chain_steps from before this change (same try/except
    # OperationalError pattern as every other ALTER in this function).
    try:
        con.execute("ALTER TABLE causal_chain_steps ADD COLUMN implication_layer TEXT "
                    "CHECK (implication_layer IN ('financial','business','competitive'))")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE causal_chain_steps ADD COLUMN reasoning_mode TEXT "
                    "CHECK (reasoning_mode IN ('causal','counterfactual','historical','trend',"
                    "'comparative','sector','macro','valuation','uncertainty','portfolio'))")
    except sqlite3.OperationalError:
        pass
    # additive migration, 2026-08-01 (FSI Phase 1, docs/fre_runs/
    # fsi_phase1_preregistration.md): both nullable, no existing row is
    # affected. schema.sql's CREATE TABLE IF NOT EXISTS already carries
    # these for a fresh database; this covers a database that already has
    # extracted_facts from before this change.
    try:
        con.execute("ALTER TABLE extracted_facts ADD COLUMN period_start TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE extracted_facts ADD COLUMN period_end TEXT")
    except sqlite3.OperationalError:
        pass
    # additive migration, 2026-08-01 (FSI Phase 2, docs/fre_runs/
    # fsi_phase2_execution_plan.md section 4.1). All three nullable, no
    # existing row is affected. schema.sql's CREATE TABLE IF NOT EXISTS
    # already carries these for a fresh database; this covers a database
    # that already has extracted_facts from before this change.
    try:
        con.execute("ALTER TABLE extracted_facts ADD COLUMN period_type TEXT "
                    "CHECK (period_type IN ('Q1','Q2','Q3','Q4','H1','H2','9M','FY'))")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE extracted_facts ADD COLUMN confidence_tier TEXT "
                    "CHECK (confidence_tier IN "
                    "('direct_reported','mapped_equivalent','derived','interpretation'))")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE extracted_facts ADD COLUMN restates_fact_id INTEGER "
                    "REFERENCES extracted_facts(fact_id)")
    except sqlite3.OperationalError:
        pass
    try:  # additive migration for pre-uid events tables
        con.execute("ALTER TABLE events ADD COLUMN event_uid TEXT")
    except sqlite3.OperationalError:
        pass
    # additive migration for pre-Phase-C documents tables (2026-07-22,
    # docs/REASONING_ENGINE_SPECIFICATION.md §2) — schema.sql's CREATE TABLE
    # IF NOT EXISTS already carries these columns for fresh databases; this
    # covers the database that already existed before Phase C.
    for col, decl in [("sector", "TEXT"), ("exchange", "TEXT DEFAULT 'NGX'"),
                      ("country", "TEXT DEFAULT 'NG'"), ("event_date", "TEXT"),
                      ("news_classification", "TEXT")]:
        try:
            con.execute(f"ALTER TABLE documents ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    # additive migration, 2026-07-22 pipeline hardening: investment_
    # implications/llm_calls already held real pilot data by this point, so
    # this is ALTER (never DROP+recreate) — same reasoning as every prior
    # migration in this function.
    try:
        con.execute("ALTER TABLE investment_implications ADD COLUMN model_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE investment_implications ADD COLUMN prompt_version TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE llm_calls ADD COLUMN document_hash TEXT")
    except sqlite3.OperationalError:
        pass
    # additive migration, 2026-08-04, MC-001 (docs/MULTI_CURRENCY_FINANCIAL_
    # ARCHITECTURE_REVIEW_2026-08-04.md). Both nullable, no existing row is
    # affected -- schema.sql's CREATE TABLE IF NOT EXISTS already carries
    # these for a fresh database; this covers a database that already has
    # extracted_facts/securities from before this change (same try/except
    # OperationalError pattern as every other ALTER in this function).
    try:
        con.execute("ALTER TABLE extracted_facts ADD COLUMN currency TEXT "
                    "CHECK (currency IS NULL OR currency GLOB '[A-Z][A-Z][A-Z]')")
    except sqlite3.OperationalError:
        pass
    try:
        con.execute("ALTER TABLE securities ADD COLUMN reporting_currency TEXT "
                    "CHECK (reporting_currency IS NULL OR reporting_currency GLOB '[A-Z][A-Z][A-Z]')")
    except sqlite3.OperationalError:
        pass
    # additive migration, 2026-08-11 (loading real dividend data into
    # corporate_actions, HANDOFF.md). Nullable, no existing row is affected
    # -- schema.sql's CREATE TABLE IF NOT EXISTS already carries this for a
    # fresh database; this covers a database that already has
    # corporate_actions from before this change.
    try:
        con.execute("ALTER TABLE corporate_actions ADD COLUMN source_fact_id INTEGER "
                    "REFERENCES extracted_facts(fact_id)")
    except sqlite3.OperationalError:
        pass
    con.executescript((SCHEMA_DIR / "schema.sql").read_text(encoding="utf-8"))
    if seed:
        con.executescript((SCHEMA_DIR / "seed_reference.sql").read_text(encoding="utf-8"))
    con.commit()
    return con


def _migrate_events_table(con: sqlite3.Connection) -> None:
    """One-time rebuild of a pre-H-003 events table (hardcoded type CHECK, no
    category/severity/direction columns) to the taxonomy-driven layout.
    Existing rows are preserved verbatim; new columns default to NULL/'unknown'."""
    info = con.execute("PRAGMA table_info(events)").fetchall()
    if not info or any(col[1] == "category" for col in info):
        return  # table absent (fresh DB) or already migrated
    con.executescript("""
        ALTER TABLE events RENAME TO events_legacy;
    """)
    # schema.sql (run right after this) recreates `events` with the new
    # layout; copy legacy rows in afterwards via a deferred statement stored
    # on the connection is overkill — just create the new table here from the
    # same DDL source, copy, and drop.
    ddl = (SCHEMA_DIR / "schema.sql").read_text(encoding="utf-8")
    start = ddl.index("CREATE TABLE IF NOT EXISTS events (")
    end = ddl.index(");", start) + 2
    con.executescript(ddl[start:end])
    con.execute("""
        INSERT INTO events (event_id, event_type, announced_date, effective_date,
                            scope, index_code, ticker, headline, outcome_numeric,
                            outcome_text, structurally_impairing, source_id,
                            confidence, as_of_date)
        SELECT event_id, event_type, announced_date, effective_date, scope,
               index_code, ticker, headline, outcome_numeric, outcome_text,
               structurally_impairing, source_id, confidence, as_of_date
        FROM events_legacy""")
    con.execute("DROP TABLE events_legacy")
    con.commit()


def _migrate_entities_table(con: sqlite3.Connection) -> None:
    """One-time rebuild of a pre-FRE-1 `entities` table (narrower entity_type
    CHECK) to the widened layout (docs/fre/02_knowledge_graph_expansion.md).
    Existing rows are preserved verbatim -- entity_type has only ever held
    'company'/'competitor_mention' in practice, both still valid under the
    widened CHECK.

    Unlike _migrate_events_table, `entities` IS referenced by foreign keys
    from other tables (entity_mentions.entity_id, entity_relationships.
    subject_entity_id/object_entity_id, effect_chains.affected_entity_id).
    RENAME TABLE would otherwise silently rewrite those tables' own FK
    clauses to point at `entities_legacy` instead of following the table
    back to its original name once recreated -- EMPIRICALLY VERIFIED (on a
    disposable scratch copy of the real database, not assumed from
    documentation) that this rewrite is suppressed only when BOTH
    `foreign_keys=OFF` AND `legacy_alter_table=ON` are set before the
    RENAME; either alone is insufficient. Every statement here uses
    `execute()`, never `executescript()` -- the latter forces an implicit
    COMMIT before running each script, which would make a failure midway
    (e.g. the foreign_key_check below) impossible to cleanly roll back.
    Keeping everything on plain `execute()` keeps the whole rebuild inside
    one transaction that `rollback()` can fully undo.
    """
    info = con.execute("PRAGMA table_info(entities)").fetchall()
    if not info:
        return  # fresh DB -- schema.sql's CREATE TABLE IF NOT EXISTS handles it
    row = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='entities'"
    ).fetchone()
    if row and row[0] and "'commodity'" in row[0]:
        return  # already migrated
    try:
        con.execute("PRAGMA foreign_keys = OFF")
        con.execute("PRAGMA legacy_alter_table = ON")
        con.execute("ALTER TABLE entities RENAME TO entities_legacy")
        con.execute("PRAGMA legacy_alter_table = OFF")
        ddl = (SCHEMA_DIR / "schema.sql").read_text(encoding="utf-8")
        start = ddl.index("CREATE TABLE IF NOT EXISTS entities (")
        end = ddl.index(");", start) + 2
        con.execute(ddl[start:end])
        con.execute("""
            INSERT INTO entities (entity_id, entity_type, canonical_name, ticker, first_seen_doc_id)
            SELECT entity_id, entity_type, canonical_name, ticker, first_seen_doc_id
            FROM entities_legacy""")
        con.execute("DROP TABLE entities_legacy")
        bad_fks = con.execute("PRAGMA foreign_key_check").fetchall()
        if bad_fks:
            raise RuntimeError(f"entities migration left dangling foreign keys: {bad_fks}")
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")


# ---------------------------------------------------------------------------
# Point-in-time readers
# ---------------------------------------------------------------------------

def index_levels_asof(
    con: sqlite3.Connection,
    sim_date: str,
    index_codes: list[str] | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
    sources: list[str] | None = None,
) -> pd.DataFrame:
    """Index closes visible on simulation date ``sim_date``.

    ``sources`` (list of sources.name) pins which provider's rows are used —
    this is how a config reruns the identical experiment on different data.

    trade_date <= sim_date (market knowledge); as_of_date <= vintage (our
    capture vintage, default = no limit i.e. latest restatements); latest
    surviving capture wins per (index, trade_date).

    ``min_confidence`` filters BEFORE the latest-capture dedup, so raising the
    floor falls back to older-but-more-trusted captures rather than dropping
    the date. Robustness tests sweep this floor upward; synthetic dev data
    (confidence 0.0) survives only at floor 0.0.
    """
    src_clause = ""
    params: dict = {"sd": sim_date, "vin": vintage or "9999-12-31",
                    "mc": min_confidence}
    if sources:
        ph = ",".join(f":s{i}" for i in range(len(sources)))
        src_clause = (f" AND source_id IN (SELECT source_id FROM sources "
                      f"WHERE name IN ({ph}))")
        params |= {f"s{i}": s for i, s in enumerate(sources)}
    q = f"""
    SELECT il.index_code, il.trade_date, il.close_value, il.confidence,
           il.source_id, il.as_of_date
    FROM index_levels il
    JOIN (
        SELECT index_code, trade_date, MAX(as_of_date) AS max_asof
        FROM index_levels
        WHERE trade_date <= :sd AND as_of_date <= :vin AND confidence >= :mc
              {src_clause}
        GROUP BY index_code, trade_date
    ) m ON il.index_code = m.index_code
       AND il.trade_date = m.trade_date
       AND il.as_of_date = m.max_asof
    WHERE il.confidence >= :mc
    """
    if index_codes:
        placeholders = ",".join(f":c{i}" for i in range(len(index_codes)))
        q += f" AND il.index_code IN ({placeholders})"
        params |= {f"c{i}": c for i, c in enumerate(index_codes)}
    q += " ORDER BY il.index_code, il.trade_date"
    return pd.read_sql(q, con, params=params)


def equity_prices_asof(
    con: sqlite3.Connection,
    sim_date: str,
    tickers: list[str] | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
) -> pd.DataFrame:
    """Constituent daily bars visible on ``sim_date`` (same PIT semantics as
    index_levels_asof)."""
    q = """
    SELECT ep.ticker, ep.trade_date, ep.close, ep.volume, ep.value_traded,
           ep.deals, ep.confidence
    FROM equity_prices ep
    JOIN (
        SELECT ticker, trade_date, MAX(as_of_date) AS max_asof
        FROM equity_prices
        WHERE trade_date <= :sd AND as_of_date <= :vin AND confidence >= :mc
        GROUP BY ticker, trade_date
    ) m ON ep.ticker = m.ticker AND ep.trade_date = m.trade_date
       AND ep.as_of_date = m.max_asof
    WHERE ep.confidence >= :mc
    """
    params: dict = {"sd": sim_date, "vin": vintage or "9999-12-31",
                    "mc": min_confidence}
    if tickers:
        ph = ",".join(f":t{i}" for i in range(len(tickers)))
        q += f" AND ep.ticker IN ({ph})"
        params |= {f"t{i}": t for i, t in enumerate(tickers)}
    q += " ORDER BY ep.ticker, ep.trade_date"
    return pd.read_sql(q, con, params=params)


def equity_prices_range(
    con: sqlite3.Connection,
    start: str,
    end: str,
    tickers: list[str] | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
    sources: list[str] | None = None,
) -> pd.DataFrame:
    """Equity bars with trade_date BETWEEN start AND end (inclusive), same
    latest-capture-wins/vintage semantics as equity_prices_asof. This is the
    research-facing counterpart to equity_prices_asof: a backtest walks
    sim_date forward one day at a time (lookahead guard), but a research
    query over a fixed historical window just needs "what does the record
    show for this whole span, as captured by vintage X" -- there is no
    day-by-day lookahead concern once the window itself is already fully in
    the past relative to vintage. Do not use this inside a backtest loop."""
    src_clause = ""
    params: dict = {"start": start, "end": end, "vin": vintage or "9999-12-31",
                    "mc": min_confidence}
    if sources:
        ph = ",".join(f":s{i}" for i in range(len(sources)))
        src_clause = (f" AND source_id IN (SELECT source_id FROM sources "
                      f"WHERE name IN ({ph}))")
        params |= {f"s{i}": s for i, s in enumerate(sources)}
    q = f"""
    SELECT ep.ticker, ep.trade_date, ep.open, ep.high, ep.low, ep.close,
           ep.volume, ep.value_traded, ep.deals, ep.source_id, ep.confidence,
           ep.as_of_date
    FROM equity_prices ep
    JOIN (
        SELECT ticker, trade_date, MAX(as_of_date) AS max_asof
        FROM equity_prices
        WHERE trade_date BETWEEN :start AND :end
          AND as_of_date <= :vin AND confidence >= :mc
          {src_clause}
        GROUP BY ticker, trade_date
    ) m ON ep.ticker = m.ticker AND ep.trade_date = m.trade_date
       AND ep.as_of_date = m.max_asof
    WHERE ep.confidence >= :mc
    """
    if tickers:
        ph = ",".join(f":t{i}" for i in range(len(tickers)))
        q += f" AND ep.ticker IN ({ph})"
        params |= {f"t{i}": t for i, t in enumerate(tickers)}
    q += " ORDER BY ep.ticker, ep.trade_date"
    return pd.read_sql(q, con, params=params)


def index_levels_range(
    con: sqlite3.Connection,
    start: str,
    end: str,
    index_codes: list[str] | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
    sources: list[str] | None = None,
) -> pd.DataFrame:
    """Index closes with trade_date BETWEEN start AND end (inclusive) --
    research-facing counterpart to index_levels_asof. See
    equity_prices_range's docstring for why a range query is safe outside
    a backtest loop but index_levels_asof remains the one to use inside
    one."""
    src_clause = ""
    params: dict = {"start": start, "end": end, "vin": vintage or "9999-12-31",
                    "mc": min_confidence}
    if sources:
        ph = ",".join(f":s{i}" for i in range(len(sources)))
        src_clause = (f" AND source_id IN (SELECT source_id FROM sources "
                      f"WHERE name IN ({ph}))")
        params |= {f"s{i}": s for i, s in enumerate(sources)}
    q = f"""
    SELECT il.index_code, il.trade_date, il.close_value, il.confidence,
           il.source_id, il.as_of_date
    FROM index_levels il
    JOIN (
        SELECT index_code, trade_date, MAX(as_of_date) AS max_asof
        FROM index_levels
        WHERE trade_date BETWEEN :start AND :end
          AND as_of_date <= :vin AND confidence >= :mc
              {src_clause}
        GROUP BY index_code, trade_date
    ) m ON il.index_code = m.index_code
       AND il.trade_date = m.trade_date
       AND il.as_of_date = m.max_asof
    WHERE il.confidence >= :mc
    """
    if index_codes:
        placeholders = ",".join(f":c{i}" for i in range(len(index_codes)))
        q += f" AND il.index_code IN ({placeholders})"
        params |= {f"c{i}": c for i, c in enumerate(index_codes)}
    q += " ORDER BY il.index_code, il.trade_date"
    return pd.read_sql(q, con, params=params)


def macro_series_asof(
    con: sqlite3.Connection,
    series_code: str,
    sim_date: str,
    min_confidence: float = 0.0,
    vintage: str | None = None,
) -> pd.Series:
    """Macro/commodity series values visible on ``sim_date`` (PIT), indexed by
    date, latest surviving capture per date."""
    q = """
    SELECT ms.trade_date, ms.value
    FROM macro_series ms
    JOIN (
        SELECT series_code, trade_date, MAX(as_of_date) AS max_asof
        FROM macro_series
        WHERE series_code = :sc AND trade_date <= :sd
          AND as_of_date <= :vin AND confidence >= :mc
        GROUP BY series_code, trade_date
    ) m ON ms.series_code = :sc AND ms.trade_date = m.trade_date
       AND ms.as_of_date = m.max_asof
    WHERE ms.confidence >= :mc
    ORDER BY ms.trade_date
    """
    df = pd.read_sql(q, con, params={"sc": series_code, "sd": sim_date,
                                     "vin": vintage or "9999-12-31",
                                     "mc": min_confidence})
    s = pd.Series(df.value.values, index=pd.to_datetime(df.trade_date),
                  name=series_code)
    return s


def corporate_actions_asof(
    con: sqlite3.Connection,
    sim_date: str,
    min_confidence: float = 0.0,
    vintage: str | None = None,
) -> pd.DataFrame:
    """Corporate actions ANNOUNCED (declared) by ``sim_date``. Falls back to
    markdown_date when declared_date is unrecorded (conservative: the action
    is then only usable from its markdown)."""
    q = """
    SELECT ticker, action_type, declared_date, qualification_date, markdown_date,
           payment_date, dividend_per_share, ratio_new, ratio_old, rights_price,
           withholding_tax_pct, confidence
    FROM corporate_actions
    WHERE COALESCE(declared_date, markdown_date) <= :sd
      AND as_of_date <= :vin AND confidence >= :mc
    ORDER BY ticker, markdown_date
    """
    return pd.read_sql(q, con, params={"sd": sim_date,
                                       "vin": vintage or "9999-12-31",
                                       "mc": min_confidence})


def membership_intervals(
    con: sqlite3.Connection,
    index_codes: list[str],
    min_confidence: float = 0.0,
    vintage: str | None = None,
) -> pd.DataFrame:
    """Raw membership intervals (engine applies the announced_date PIT filter
    per simulation date as it walks forward)."""
    ph = ",".join(f":c{i}" for i in range(len(index_codes)))
    q = f"""
    SELECT index_code, ticker, effective_from, effective_to, announced_date
    FROM index_membership
    WHERE index_code IN ({ph}) AND as_of_date <= :vin AND confidence >= :mc
    """
    params = {f"c{i}": c for i, c in enumerate(index_codes)}
    params |= {"vin": vintage or "9999-12-31", "mc": min_confidence}
    return pd.read_sql(q, con, params=params)


def membership_asof(
    con: sqlite3.Connection,
    index_code: str,
    sim_date: str,
    min_confidence: float = 0.0,
    vintage: str | None = None,
) -> pd.DataFrame:
    """Constituents of ``index_code`` as knowable on simulation date ``sim_date``.

    A stock counts as a member iff:
      - effective_from <= sim_date < effective_to (or effective_to NULL)
      - the membership record itself was public: announced_date (or, if
        unknown, effective_from) <= sim_date
      - our capture of the record is within the vintage (as_of guard)
    """
    q = """
    SELECT ticker, effective_from, effective_to, announced_date, reason_in,
           confidence, source_id
    FROM index_membership
    WHERE index_code = :idx
      AND effective_from <= :sd
      AND (effective_to IS NULL OR effective_to > :sd)
      AND COALESCE(announced_date, effective_from) <= :sd
      AND as_of_date <= :vin
      AND confidence >= :mc
    ORDER BY ticker
    """
    return pd.read_sql(q, con, params={"idx": index_code, "sd": sim_date,
                                       "vin": vintage or "9999-12-31",
                                       "mc": min_confidence})


def events_asof(
    con: sqlite3.Connection,
    sim_date: str,
    event_types: list[str] | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
) -> pd.DataFrame:
    """Events ANNOUNCED on or before ``sim_date`` (the catalyst-filter feed).

    Filters on announced_date, never effective_date: a deadline in 2026 is
    tradeable information from its 2024 announcement, but an event announced
    tomorrow is invisible today.
    """
    q = """
    SELECT e.event_id, e.event_type, e.event_uid, e.category, e.announced_date,
           e.effective_date, e.publication_ts, e.scope, e.index_code, e.ticker,
           e.headline, e.outcome_numeric, e.outcome_text, e.severity,
           e.direction, e.structurally_impairing, e.source_url, e.confidence
    FROM events e
    WHERE e.announced_date <= :sd AND e.as_of_date <= :vin
      AND e.confidence >= :mc
      AND (e.event_uid IS NULL OR e.event_id = (
            SELECT e2.event_id FROM events e2
            WHERE e2.event_uid = e.event_uid AND e2.as_of_date <= :vin
              AND e2.confidence >= :mc
            ORDER BY e2.as_of_date DESC, e2.event_id DESC LIMIT 1))
    """
    params: dict = {"sd": sim_date, "vin": vintage or "9999-12-31",
                    "mc": min_confidence}
    if event_types:
        placeholders = ",".join(f":t{i}" for i in range(len(event_types)))
        q += f" AND event_type IN ({placeholders})"
        params |= {f"t{i}": t for i, t in enumerate(event_types)}
    q += " ORDER BY announced_date"
    return pd.read_sql(q, con, params=params)


def cost_schedule_asof(con: sqlite3.Connection, trade_date: str) -> pd.DataFrame:
    """Fee rates in force on ``trade_date`` (effective-dated, e.g. VAT change)."""
    q = """
    SELECT fee_name, side, rate_pct, applies_to, confidence, notes
    FROM cost_schedule
    WHERE effective_from <= :td
      AND (effective_to IS NULL OR effective_to >= :td)
    ORDER BY fee_name, side
    """
    return pd.read_sql(q, con, params={"td": trade_date})
