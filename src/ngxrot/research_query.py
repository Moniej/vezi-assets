"""Research Query Layer -- Phase 2 of the Research OS.

Sits directly ON TOP of the Phase-1 Research OS infrastructure
(`research_dataset.py`, `research_quality.py`, `lineage.py`,
`instrument_identity.py`, `universe.py`, `db.py`) -- it does not
reimplement data access, identity resolution, lineage, or PIT semantics.
It adds exactly what those modules did not have: a structured query
contract (`QuerySpec`/`QueryResult`), validation/guardrails, entity-
resolution glue, a handful of general-purpose query types, descriptive
(non-alpha) calculations, and lightweight query logging.

Pipeline this module occupies:

    Data Sources -> Providers -> DataProvider -> ingest.py -> SQLite PIT
    -> identity/lineage/quality (Phase 1) -> RESEARCH QUERY LAYER (here)
    -> Research Questions -> Structured Results -> Evidence/Provenance

No new database, no new provider, no new ingestion path, no new identity
or lineage system. `query_log` is one new, generic, lightweight table
added to the EXISTING `data/registry.sqlite` (schema/registry.sql).

## No silent transformations

Every function here either returns raw, unmodified observations plus
explicit `warnings`, or refuses with a clear error. Nothing here
adjusts prices, forward-fills missing data, changes a sector
classification, or substitutes a provider. `sector_ngx` in particular
has NO historical versioning anywhere in this schema (`securities.
sector_ngx` is a single current value; `sector_ngx_provenance` records
only where the CURRENT value came from, not prior values) -- any
cross-sectional/sector query with a historical `as_of` therefore always
carries an explicit warning that classification history is unavailable,
rather than silently assuming today's sector applied historically.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum

import pandas as pd

from . import db, registry, universe
from .documents import retrieval as doc_retrieval
from .instrument_identity import resolve_ticker_history_symbols
from .canonical.contracts import TemporalQueryContext
from .identity.resolver import ResolutionStatus, resolve_instrument

# ---------------------------------------------------------------------------
# Field registries -- the ONLY fields a query may request. Anything not
# listed here does not exist in the schema and must be rejected, not
# faked (e.g. market_cap, dividend_yield are NOT present anywhere in this
# database and are deliberately absent from these sets).
# ---------------------------------------------------------------------------

EQUITY_PRICE_FIELDS = {"open", "high", "low", "close", "volume", "value_traded",
                        "deals", "confidence", "source_id", "as_of_date"}
INDEX_LEVEL_FIELDS = {"close_value", "confidence", "source_id", "as_of_date"}
SECURITY_METADATA_FIELDS = {"isin", "name", "board", "listing_date", "delisting_date",
                             "delisting_reason", "sector_ngx", "notes", "reporting_currency"}

FIELD_REGISTRIES = {
    "equity_prices": EQUITY_PRICE_FIELDS,
    "index_levels": INDEX_LEVEL_FIELDS,
    "securities": SECURITY_METADATA_FIELDS,
}


class QueryValidationError(ValueError):
    """Raised when a QuerySpec cannot be executed safely -- unknown
    entity/field, invalid dates, or a look-ahead attempt. Always carries
    a specific, actionable message; never a generic failure."""


# ---------------------------------------------------------------------------
# Query specification / result contract
# ---------------------------------------------------------------------------

@dataclass
class QuerySpec:
    query_type: str  # 'prices'|'cross_section'|'universe_history'|'compare'|'metadata'|'entity_lookup'
                      # |'facts'|'events'|'entity_relationships'|'document_context'
    entities: list[str] = field(default_factory=list)
    entity_kind: str = "ticker"  # 'ticker'|'sector'|'index'
    start: str | None = None
    end: str | None = None
    as_of: str | None = None  # information-availability cutoff (vintage); NOT the same as `end`
    fields: list[str] = field(default_factory=lambda: ["close"])
    filters: dict = field(default_factory=dict)
    group_by: str | None = None
    sort_by: str | None = None
    limit: int | None = None
    min_confidence: float = 0.0
    sources: list[str] | None = None


@dataclass
class EntityResolution:
    requested: str
    resolved_kind: str
    found: bool
    canonical: str | None = None
    full_chain: list[str] = field(default_factory=list)
    notes: str | None = None


class ResearchIdentityStatus(str, Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    TEMPORALLY_UNAVAILABLE = "temporally_unavailable"
    LEGACY_FALLBACK = "legacy_fallback"


@dataclass(frozen=True)
class ResearchIdentityLookupResult:
    """Read-only identity inspection result; it does not alter QuerySpec or registry records."""
    status: ResearchIdentityStatus
    requested_identifier: str
    identifier_type: str
    exchange: str | None
    canonical_status: str
    instrument_id: str | None = None
    company_id: str | None = None
    matched_alias_id: str | None = None
    verification_status: str | None = None
    issuer_status: str = "unresolved"
    decision_time: object | None = None
    system_vintage: object | None = None
    availability_policy: str | None = None
    fallback_used: bool = False
    legacy_ticker: str | None = None
    compatibility_status: str | None = None
    pit_safe_canonical_resolution: bool = False
    resolution_reason: str | None = None


def lookup_identity(con: sqlite3.Connection, identifier: str, *, exchange: str | None = None,
                    identifier_type: str = "ticker",
                    temporal_context: TemporalQueryContext | None = None,
                    allow_legacy_fallback: bool = True) -> ResearchIdentityLookupResult:
    """Explicit canonical-first Research OS inspection, with labeled legacy fallback.

    Existing research queries continue calling ``resolve_entity``. This helper
    only reads the Investment OS connection and never writes registry state.
    """
    canonical = resolve_instrument(con, identifier=identifier, identifier_type=identifier_type,
                                   exchange=exchange, temporal_context=temporal_context)
    temporal = {}
    if temporal_context is not None:
        temporal = {
            "decision_time": temporal_context.decision_time.value,
            "system_vintage": temporal_context.system_vintage.value,
            "availability_policy": temporal_context.availability_policy.value,
        }
    if canonical.status is ResolutionStatus.RESOLVED:
        return ResearchIdentityLookupResult(
            ResearchIdentityStatus.RESOLVED, identifier, identifier_type, exchange,
            canonical.status.value, canonical.instrument_id, canonical.company_id,
            canonical.alias_id, canonical.verification_status,
            "resolved" if canonical.company_id else "unresolved",
            pit_safe_canonical_resolution=True,
            resolution_reason="canonical alias matched",
            **temporal,
        )
    status = ResearchIdentityStatus(canonical.status.value)
    # Ambiguity may never be escaped through a ticker fallback; that would
    # select a legacy row arbitrarily and conceal the canonical conflict.
    if allow_legacy_fallback and canonical.status is not ResolutionStatus.AMBIGUOUS and identifier_type == "ticker":
        row = con.execute("SELECT ticker FROM securities WHERE ticker=?", (identifier,)).fetchone()
        if row:
            return ResearchIdentityLookupResult(
                ResearchIdentityStatus.LEGACY_FALLBACK, identifier, identifier_type, exchange,
                canonical.status.value, fallback_used=True, legacy_ticker=row[0],
                compatibility_status="legacy_only_non_pit_safe" if temporal_context else "legacy_only",
                pit_safe_canonical_resolution=False,
                resolution_reason=f"canonical {canonical.status.value}; legacy ticker found",
                **temporal,
            )
    return ResearchIdentityLookupResult(
        status, identifier, identifier_type, exchange, canonical.status.value,
        pit_safe_canonical_resolution=False,
        resolution_reason=f"canonical {canonical.status.value}",
        **temporal,
    )


@dataclass
class QueryResult:
    query_id: str
    query_type: str
    parameters: dict
    entities_requested: list[str]
    entities_resolved: list[dict]  # [EntityResolution.__dict__, ...]
    observations: pd.DataFrame
    row_count: int
    date_range: tuple[str | None, str | None]
    data_sources: list[str]
    warnings: list[str]
    provenance: list[dict]
    execution_metadata: dict

    def content_hash(self) -> str:
        """Deterministic hash of `observations`, independent of row order.
        List/dict-valued cells (e.g. entity_lookup's `full_chain`) are not
        sortable by pandas, so every column is stringified first purely
        for hashing purposes -- the returned `observations` DataFrame
        itself is never mutated."""
        if self.observations.empty:
            return hashlib.sha256(b"empty").hexdigest()[:16]
        stringified = self.observations.astype(str)
        sortable = stringified.sort_values(list(stringified.columns)).reset_index(drop=True)
        return hashlib.sha256(sortable.to_csv(index=False).encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id, "query_type": self.query_type, "parameters": self.parameters,
            "entities_requested": self.entities_requested, "entities_resolved": self.entities_resolved,
            "row_count": self.row_count, "date_range": self.date_range, "data_sources": self.data_sources,
            "warnings": self.warnings, "provenance": self.provenance,
            "execution_metadata": self.execution_metadata,
        }

    def to_json(self) -> str:
        payload = self.to_dict()
        payload["observations"] = self.observations.to_dict(orient="records")
        return json.dumps(payload, indent=2, default=str)

    def to_csv(self) -> str:
        return self.observations.to_csv(index=False)


# ---------------------------------------------------------------------------
# Entity resolution -- glues onto instrument_identity.py ONLY. No second
# ticker-resolution mechanism.
# ---------------------------------------------------------------------------

def resolve_entity(con: sqlite3.Connection, identifier: str, kind: str = "ticker") -> EntityResolution:
    if kind == "ticker":
        row = con.execute("SELECT ticker FROM securities WHERE ticker = ?", (identifier,)).fetchone()
        if row is None:
            return EntityResolution(requested=identifier, resolved_kind=kind, found=False,
                                    notes="no matching row in securities")
        eras = resolve_ticker_history_symbols(con, identifier)
        canonical = eras[-1].ticker
        return EntityResolution(requested=identifier, resolved_kind=kind, found=True,
                                canonical=canonical, full_chain=[e.ticker for e in eras],
                                notes=("resolved via instrument_identity.py rename chain"
                                       if len(eras) > 1 else "no known rename history"))
    if kind == "sector":
        row = con.execute("SELECT 1 FROM securities WHERE sector_ngx = ? LIMIT 1", (identifier,)).fetchone()
        return EntityResolution(requested=identifier, resolved_kind=kind, found=row is not None,
                                canonical=identifier if row else None,
                                notes="matched against securities.sector_ngx (CURRENT classification only; "
                                      "no historical sector versioning exists in this schema)")
    if kind == "index":
        row = con.execute("SELECT 1 FROM index_membership WHERE index_code = ? LIMIT 1",
                          (identifier,)).fetchone()
        return EntityResolution(requested=identifier, resolved_kind=kind, found=row is not None,
                                canonical=identifier if row else None)
    raise QueryValidationError(f"unsupported entity_kind {kind!r} (must be 'ticker'/'sector'/'index')")


# ---------------------------------------------------------------------------
# Validation / guardrails
# ---------------------------------------------------------------------------

def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


def validate_spec(con: sqlite3.Connection, spec: QuerySpec) -> list[str]:
    """Raises QueryValidationError on anything unsafe/unresolvable.
    Returns a list of non-fatal WARNINGS (survivorship / classification-
    history caveats) that the caller should carry into the QueryResult."""
    warnings: list[str] = []

    for d, name in [(spec.start, "start"), (spec.end, "end"), (spec.as_of, "as_of")]:
        if d is not None and not _valid_date(d):
            raise QueryValidationError(f"invalid date for {name!r}: {d!r} (expected YYYY-MM-DD)")
    if spec.start and spec.end and spec.start > spec.end:
        raise QueryValidationError(f"start ({spec.start}) is after end ({spec.end})")

    # Look-ahead guard: `as_of` is the information-availability cutoff. A
    # query asking for observations dated AFTER as_of would be asking the
    # system what it "already knew" about the future -- rejected outright
    # rather than silently truncated (truncation is itself an undisclosed
    # transformation of the request).
    if spec.as_of and spec.end and spec.end > spec.as_of:
        raise QueryValidationError(
            f"look-ahead rejected: end date {spec.end} is after as_of {spec.as_of} -- "
            f"a query cannot request observations dated later than its own information cutoff")

    dataset = "equity_prices" if spec.query_type in ("prices", "compare", "cross_section") else \
              "index_levels" if spec.entity_kind == "index" and spec.query_type == "prices" else None
    registry_fields = FIELD_REGISTRIES.get(dataset) if dataset else None
    if registry_fields is not None:
        unknown = [f for f in spec.fields if f not in registry_fields and f not in ("ticker", "trade_date")]
        if unknown:
            raise QueryValidationError(
                f"unsupported field(s) {unknown} for dataset {dataset!r} -- this schema does not have "
                f"them (never fabricated). Supported: {sorted(registry_fields)}")

    for e in spec.entities:
        res = resolve_entity(con, e, spec.entity_kind)
        if not res.found:
            raise QueryValidationError(f"unknown {spec.entity_kind} {e!r} -- not found in the database")

    # Survivorship guard: a sector/cross-section query with an historical
    # as_of cannot actually know historical sector membership (no
    # versioning exists) -- must warn, never silently apply today's
    # classification to a past date.
    if spec.query_type == "cross_section" and spec.filters.get("sector") and spec.as_of:
        today = date.today().isoformat()
        if spec.as_of < today:
            warnings.append(
                f"sector membership for 'as_of'={spec.as_of} is answered using the CURRENT "
                f"securities.sector_ngx classification -- this schema has no historical sector "
                f"versioning, so this may not reflect the sector as it was actually classified on "
                f"that date (survivorship-style risk, disclosed not corrected)")

    if spec.limit is not None and spec.limit <= 0:
        raise QueryValidationError(f"limit must be positive, got {spec.limit}")

    return warnings


# ---------------------------------------------------------------------------
# Descriptive (non-alpha) calculations. Explicitly NOT momentum/alpha
# factors -- pure, generic descriptive statistics a researcher can apply
# to ANY series to understand the data, not to score or rank securities.
# ---------------------------------------------------------------------------

def abs_change(s: pd.Series) -> pd.Series:
    return s.diff()


def pct_change(s: pd.Series) -> pd.Series:
    return s.pct_change()


def rolling_stats(s: pd.Series, window: int) -> pd.DataFrame:
    return pd.DataFrame({
        "mean": s.rolling(window).mean(), "median": s.rolling(window).median(),
        "min": s.rolling(window).min(), "max": s.rolling(window).max(),
        "std": s.rolling(window).std(),
    })


def drawdown(s: pd.Series) -> pd.Series:
    running_max = s.cummax()
    return s / running_max - 1.0


def observation_counts(df: pd.DataFrame, group_col: str = "ticker") -> pd.DataFrame:
    return df.groupby(group_col).size().rename("n_observations").reset_index()


# ---------------------------------------------------------------------------
# Core query types
# ---------------------------------------------------------------------------

def _latest_snapshot_per_ticker(con: sqlite3.Connection, tickers: list[str], as_of: str,
                                min_confidence: float) -> pd.DataFrame:
    """One row per ticker: the latest equity_prices observation with
    trade_date <= as_of, latest-capture (as_of_date) wins on that date --
    same PIT semantics as db.equity_prices_asof, but resolved directly in
    SQL instead of materializing full history first."""
    if not tickers:
        return pd.DataFrame(columns=["ticker", "trade_date", "open", "high", "low", "close",
                                     "volume", "value_traded", "deals", "source_id", "confidence",
                                     "as_of_date"])
    ph = ",".join("?" * len(tickers))
    q = f"""
    SELECT ep.ticker, ep.trade_date, ep.open, ep.high, ep.low, ep.close, ep.volume,
           ep.value_traded, ep.deals, ep.source_id, ep.confidence, ep.as_of_date
    FROM equity_prices ep
    JOIN (
        SELECT ticker, MAX(trade_date) AS latest_date
        FROM equity_prices
        WHERE ticker IN ({ph}) AND trade_date <= ? AND confidence >= ?
        GROUP BY ticker
    ) d ON ep.ticker = d.ticker AND ep.trade_date = d.latest_date
    JOIN (
        SELECT ticker, trade_date, MAX(as_of_date) AS max_asof
        FROM equity_prices
        WHERE ticker IN ({ph}) AND trade_date <= ? AND confidence >= ?
        GROUP BY ticker, trade_date
    ) m ON ep.ticker = m.ticker AND ep.trade_date = m.trade_date AND ep.as_of_date = m.max_asof
    WHERE ep.confidence >= ?
    """
    params = [*tickers, as_of, min_confidence, *tickers, as_of, min_confidence, min_confidence]
    return pd.read_sql(q, con, params=params)


def _apply_limit_sort(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    if spec.sort_by and spec.sort_by.lstrip("-") in df.columns:
        col = spec.sort_by.lstrip("-")
        df = df.sort_values(col, ascending=not spec.sort_by.startswith("-"))
    if spec.limit is not None:
        df = df.head(spec.limit)
    return df.reset_index(drop=True)


def query_prices(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Time-series query: one or more tickers over [start, end].

    `as_of` maps to the trade_date/observation cutoff (the db.py "sim_date"
    axis, i.e. what the market knew) -- enforced by validate_spec's
    look-ahead rejection (end must not exceed as_of). It does NOT restrict
    `vintage` (the db.py "our capture" axis): a researcher asking "what
    happened by 2023-06-30" normally wants the best-known/latest-corrected
    record of that period, not an artificially frozen data-capture
    snapshot -- freezing capture vintage for strict reproducibility is a
    separate concern already served by Phase 1's `research_dataset.
    ResearchDataset.record_snapshot()` content-hash mechanism."""
    warnings = validate_spec(con, spec)
    resolved = [resolve_entity(con, e, "ticker") for e in spec.entities]

    fields = [f for f in spec.fields if f in EQUITY_PRICE_FIELDS] or ["close"]
    full_df = db.equity_prices_range(con, spec.start, spec.end, tickers=spec.entities,
                                     min_confidence=spec.min_confidence, sources=spec.sources)
    cols = ["ticker", "trade_date"] + [f for f in fields if f in full_df.columns]
    df = full_df[cols] if not full_df.empty else full_df
    if spec.group_by:
        warnings.append(f"group_by={spec.group_by!r} has no effect on a single-entity time series; "
                         f"ignored (only meaningful for cross_section/compare)")
    df = _apply_limit_sort(df, spec)

    src_names = _source_names(con, full_df["source_id"] if "source_id" in full_df.columns else None)
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="prices", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(spec.start, spec.end),
        data_sources=src_names, warnings=warnings,
        provenance=_provenance_summary(con, full_df), execution_metadata=_exec_meta(),
    )


def query_cross_section(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """All companies matching filters (e.g. sector) as of a date, with
    optional latest field values."""
    warnings = validate_spec(con, spec)
    sector = spec.filters.get("sector")
    if sector is None:
        raise QueryValidationError("cross_section query requires filters={'sector': ...} "
                                    "(no other cross-section dimension is supported yet)")
    tickers_df = pd.read_sql("SELECT ticker FROM securities WHERE sector_ngx = ?", con, params=(sector,))
    tickers = tickers_df.ticker.tolist()
    as_of = spec.as_of or date.today().isoformat()
    # as_of here is the trade_date/observation cutoff (sim_date axis) --
    # vintage intentionally left unrestricted, same reasoning as
    # query_prices's docstring. A cross-section needs exactly one row per
    # ticker (the latest observation at/before as_of), NOT each ticker's
    # full history -- reduced directly in SQL (two cheap steps: latest
    # trade_date per ticker, then latest-capture-wins per that date) so a
    # sector query never materializes years of daily bars just to keep
    # the last row, which was the real performance bug found benchmarking
    # this (4.2s -> <100ms on the CONSUMER GOODS sector, 19 tickers).
    full_df = _latest_snapshot_per_ticker(con, tickers, as_of, spec.min_confidence)
    fields = [f for f in spec.fields if f in EQUITY_PRICE_FIELDS] or ["close"]
    cols = ["ticker", "trade_date"] + [f for f in fields if f in full_df.columns]
    df = full_df[cols] if not full_df.empty else full_df
    df = _apply_limit_sort(df, spec)

    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="cross_section", parameters=_spec_params(spec),
        entities_requested=tickers, entities_resolved=[{"requested": sector, "resolved_kind": "sector",
                                                         "found": len(tickers) > 0, "canonical": sector}],
        observations=df, row_count=len(df), date_range=(as_of, as_of),
        data_sources=_source_names(con, full_df["source_id"] if "source_id" in full_df.columns else None),
        warnings=warnings, provenance=_provenance_summary(con, full_df), execution_metadata=_exec_meta(),
    )


def query_universe_history(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Universe membership as of a date -- either the rule-based IRU
    (spec.filters['universe']='iru', reuses universe.iru_members) or a
    real NGX index (spec.entity_kind='index', reuses db.membership_asof).
    """
    warnings = validate_spec(con, spec)
    as_of = spec.as_of or spec.end
    if as_of is None:
        raise QueryValidationError("universe_history query requires as_of (or end)")

    if spec.filters.get("universe") == "iru":
        rules = universe.load_rules()
        mem = universe.iru_members(con, as_of, rules)
        entities = mem.ticker.tolist()
        universe_version = rules["version"]
        out = mem[["ticker", "n_days", "avg_value", "last_trade", "liq_rank"]].copy()
        out.insert(0, "as_of", as_of)
    elif spec.entities:
        index_code = spec.entities[0]
        # as_of is the trade_date/observation-availability cutoff (sim_date
        # axis); vintage intentionally left unrestricted -- see
        # query_prices's docstring for why.
        mem = db.membership_asof(con, index_code, as_of, min_confidence=spec.min_confidence)
        entities = mem.ticker.tolist() if not mem.empty else []
        universe_version = None
        out = mem.copy()
        if not out.empty:
            out.insert(0, "as_of", as_of)
    else:
        raise QueryValidationError("universe_history query requires either "
                                    "filters={'universe': 'iru'} or entities=['<INDEX_CODE>']")
    out = _apply_limit_sort(out, spec)

    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="universe_history", parameters=_spec_params(spec),
        entities_requested=entities, entities_resolved=[], observations=out, row_count=len(out),
        date_range=(as_of, as_of), data_sources=[], warnings=warnings, provenance=[],
        execution_metadata={**_exec_meta(), "universe_version": universe_version},
    )


def query_compare(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Multiple tickers, same window, side by side, with descriptive
    (non-alpha) comparison stats appended: total pct_change over the
    window and per-ticker observation counts. No ranking, no score."""
    base = query_prices(con, spec)
    if base.observations.empty:
        return base
    field = next((f for f in spec.fields if f in base.observations.columns and f != "trade_date"), "close")
    summary_rows = []
    for t, g in base.observations.groupby("ticker"):
        g = g.sort_values("trade_date")
        series = g[field].astype(float)
        total_pct = (series.iloc[-1] / series.iloc[0] - 1.0) if len(series) > 1 and series.iloc[0] else None
        summary_rows.append({"ticker": t, "n_observations": len(g), "first_date": g.trade_date.iloc[0],
                             "last_date": g.trade_date.iloc[-1], f"first_{field}": series.iloc[0],
                             f"last_{field}": series.iloc[-1], "total_pct_change": total_pct})
    summary = pd.DataFrame(summary_rows)
    base.query_type = "compare"
    base.execution_metadata["comparison_summary"] = summary.to_dict(orient="records")
    return base


def query_metadata(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Security metadata + identity + a lightweight lineage summary, for
    each requested ticker."""
    warnings = validate_spec(con, spec)
    resolved = [resolve_entity(con, e, "ticker") for e in spec.entities]
    rows = []
    for e, res in zip(spec.entities, resolved):
        meta = pd.read_sql("SELECT * FROM securities WHERE ticker = ?", con, params=(e,))
        row = meta.iloc[0].to_dict() if not meta.empty else {}
        row["ticker"] = e
        row["rename_chain"] = res.full_chain
        rows.append(row)
    df = pd.DataFrame(rows)
    df = _apply_limit_sort(df, spec)
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="metadata", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(None, None), data_sources=["securities"],
        warnings=warnings, provenance=[], execution_metadata=_exec_meta(),
    )


def query_entity_lookup(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Resolve one or more identifiers (any kind) without pulling any
    observations -- the "find company/ticker/sector/index" primitive."""
    resolved = [resolve_entity(con, e, spec.entity_kind) for e in spec.entities]
    df = pd.DataFrame([vars(r) for r in resolved])
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="entity_lookup", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(None, None), data_sources=[],
        warnings=[], provenance=[], execution_metadata=_exec_meta(),
    )


# ---------------------------------------------------------------------------
# Document / evidence intelligence bridge (added 2026-08-11, per the
# Investment OS reframe -- docs/INVESTMENT_OS_SPECIFICATION.md's verified
# gap: the price/market side already had a query layer, the document/FRE
# side (documents, extracted_facts, evidence, investment_implications,
# events, entity_relationships) did not. These are thin QueryResult
# wrappers around the EXISTING, already-tested FRE retrieval primitives
# (`documents.retrieval`, `documents.context`) -- no new fact/evidence
# reading logic is added here, matching every other query type in this
# module (a wrapper, not a reimplementation).
# ---------------------------------------------------------------------------

def _document_provenance_summary(con: sqlite3.Connection, doc_ids) -> list[dict]:
    """Same shape/intent as `_provenance_summary`, but for the documents
    table's own `source_id` (documents.source_id -> sources), since facts/
    events/entity-relationships trace back to a document, not an
    equity_prices row."""
    ids = sorted(set(int(i) for i in doc_ids)) if doc_ids is not None else []
    if not ids:
        return []
    ph = ",".join("?" * len(ids))
    rows = con.execute(
        f"SELECT d.doc_id, d.ticker, d.doc_type, d.filing_date, d.source_confidence, "
        f"s.name, s.kind, s.reliability "
        f"FROM documents d JOIN sources s ON s.source_id = d.source_id "
        f"WHERE d.doc_id IN ({ph})", ids).fetchall()
    cols = ["doc_id", "ticker", "doc_type", "filing_date", "source_confidence",
           "source_name", "source_kind", "source_reliability"]
    return [dict(zip(cols, r)) for r in rows]


def query_facts(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Extracted facts (deterministic + LLM-sourced) for one or more
    tickers -- thin wrapper around `documents.retrieval.find_facts`.
    `filters={'fact_type': ...}` narrows by taxonomy leaf;
    `start`/`end` map to the underlying filing-date range. `end` defaults
    to `as_of` when not given (fixed 2026-08-11, HANDOFF.md -- Priority 5):
    a caller asking for facts "as of" a date with no explicit `end` was
    previously getting every fact regardless of filing date -- a real
    look-ahead gap in this wrapper, not in find_facts itself (a deliberately
    unopinionated primitive whose caller is expected to pass a bound)."""
    warnings = validate_spec(con, spec)
    resolved = [resolve_entity(con, e, "ticker") for e in spec.entities]
    fact_type = spec.filters.get("fact_type")
    date_to = spec.end or spec.as_of
    rows = []
    for e in spec.entities:
        rows.extend(doc_retrieval.find_facts(
            con, ticker=e, fact_type=fact_type, date_from=spec.start, date_to=date_to,
            limit=spec.limit or 50))
    df = pd.DataFrame(rows)
    if df.empty:
        warnings.append("no extracted_facts found for the requested ticker(s)/filters")
    df = _apply_limit_sort(df, spec)
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="facts", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(spec.start, date_to),
        data_sources=["extracted_facts", "documents"], warnings=warnings,
        provenance=_document_provenance_summary(con, df["doc_id"] if "doc_id" in df.columns else None),
        execution_metadata=_exec_meta(),
    )


def query_events(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """PIT-correct company/market events -- thin wrapper around the
    existing `db.events_asof` via `documents.retrieval.find_events`
    (already reused, not duplicated, by that module). `as_of` (or `end`)
    is the sim_date cutoff; `filters={'event_type': ...}` narrows by type."""
    warnings = validate_spec(con, spec)
    resolved = [resolve_entity(con, e, "ticker") for e in spec.entities] if spec.entities else []
    sim_date = spec.as_of or spec.end
    event_type = spec.filters.get("event_type")
    frames = []
    tickers = spec.entities or [None]
    for e in tickers:
        edf = doc_retrieval.find_events(con, ticker=e, event_type=event_type, sim_date=sim_date,
                                        min_confidence=spec.min_confidence, limit=spec.limit or 50)
        if edf is not None and len(edf):
            frames.append(edf)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        warnings.append("no events found for the requested ticker(s)/filters as of the given date")
    df = _apply_limit_sort(df, spec)
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="events", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(spec.start, sim_date),
        data_sources=["events"], warnings=warnings, provenance=[], execution_metadata=_exec_meta(),
    )


def query_entity_relationships(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """Persisted entity relationships (competitor/supplier/etc. mentions)
    for one or more tickers -- thin wrapper around
    `documents.retrieval.find_entity_relationships`. `as_of` (or `end`)
    now filters on `valid_from`/`valid_to` (fixed 2026-08-11, HANDOFF.md --
    Priority 5) -- this query type previously had no date filtering
    whatsoever, a real look-ahead gap given valid_from genuinely spans
    2020-2026 on the real database."""
    warnings = validate_spec(con, spec)
    resolved = [resolve_entity(con, e, "ticker") for e in spec.entities]
    relation_type = spec.filters.get("relation_type")
    as_of = spec.as_of or spec.end
    rows = []
    for e in spec.entities:
        rows.extend(doc_retrieval.find_entity_relationships(
            con, ticker=e, relation_type=relation_type, as_of=as_of, limit=spec.limit or 50))
    df = pd.DataFrame(rows)
    if df.empty:
        warnings.append("no entity_relationships found for the requested ticker(s)/filters")
    df = _apply_limit_sort(df, spec)
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="entity_relationships", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(None, as_of),
        data_sources=["entity_relationships"], warnings=warnings, provenance=[],
        execution_metadata=_exec_meta(),
    )


def query_document_context(con: sqlite3.Connection, spec: QuerySpec) -> QueryResult:
    """One-row-per-ticker summary of the full FRE `ReasoningContext`
    (documents/facts/evidence/events/relationships/coverage/confidence),
    via `documents.context.build_reasoning_context` -- the SAME assembly
    function `reasoning_engine.py` uses internally, not a second one.
    Only ONE entity per call (a reasoning context is comparatively
    expensive to assemble -- multiple LLM-adjacent DB reads); use `facts`/
    `events`/`entity_relationships` directly for a lighter, multi-ticker
    query. This is the closest thing this layer has to "what's the current
    picture on ticker X" in one call."""
    from .documents.context import build_reasoning_context
    warnings = validate_spec(con, spec)
    if len(spec.entities) != 1:
        raise QueryValidationError(
            "document_context accepts exactly one ticker per call (a reasoning context is "
            "assembled fresh, not read off a cheap index) -- use 'facts'/'events'/"
            "'entity_relationships' for multi-ticker queries")
    ticker = spec.entities[0]
    resolved = [resolve_entity(con, ticker, "ticker")]
    as_of = spec.as_of or spec.end
    ctx = build_reasoning_context(con, ticker, as_of=as_of)
    warnings.extend(ctx.coverage_notes)
    if len(ctx.documents) == 100:  # RetrievalQuery(limit=100) in context.py --
        warnings.append("document count hit the retrieval limit (100) -- there may be MORE "
                        "documents for this ticker than were fetched; not silently treated as "
                        "complete coverage")
    cov = ctx.coverage_assessment
    ers = ctx.evidence_ranking_summary or {}
    row = {
        "ticker": ticker, "as_of": ctx.as_of, "name": ctx.name,
        "n_documents": len(ctx.documents), "n_facts": len(ctx.facts),
        "n_evidence": len(ctx.evidence), "n_events": len(ctx.events),
        "n_entity_relationships": len(ctx.entity_relationships),
        "n_historical_implications": len(ctx.historical_implications),
        "n_peer_propagations": len(ctx.peer_propagations),
        "coverage_score": cov.coverage_score if cov else None,
        "confidence_ceiling": cov.confidence_ceiling if cov else None,
        # Added 2026-08-11, HANDOFF.md -- Priority 7 (research
        # quality/completeness): both already computed by
        # build_reasoning_context/assess_coverage/evidence_ranking_summary,
        # just never surfaced in this row before now.
        "dimensions_missing": ",".join(cov.dimensions_missing) if cov else None,
        "source_tier_distribution": json.dumps(ers.get("tier_distribution", {})),
        "n_conflicts_detected": ers.get("n_conflicts_detected", 0),
        "n_conflicts_trust_vs_confidence_disagree":
            ers.get("n_conflicts_where_trust_and_confidence_disagree", 0),
    }
    df = pd.DataFrame([row])
    return QueryResult(
        query_id=str(uuid.uuid4()), query_type="document_context", parameters=_spec_params(spec),
        entities_requested=spec.entities, entities_resolved=[vars(r) for r in resolved],
        observations=df, row_count=len(df), date_range=(as_of, as_of),
        data_sources=["documents", "extracted_facts", "evidence", "events",
                      "entity_relationships", "investment_implications"],
        warnings=warnings,
        provenance=_document_provenance_summary(con, [d.doc_id for d in ctx.documents]),
        execution_metadata={**_exec_meta(), "reasoning_context_object_available_via": "documents.context.build_reasoning_context"},
    )


_DISPATCH = {
    "prices": query_prices, "cross_section": query_cross_section,
    "universe_history": query_universe_history, "compare": query_compare,
    "metadata": query_metadata, "entity_lookup": query_entity_lookup,
    "facts": query_facts, "events": query_events,
    "entity_relationships": query_entity_relationships,
    "document_context": query_document_context,
}


def execute(con: sqlite3.Connection, spec: QuerySpec, reg: sqlite3.Connection | None = None,
            log: bool = True) -> QueryResult:
    """Single entry point: validate -> resolve -> execute -> (optionally)
    log. `reg` defaults to the real registry.sqlite unless a scratch
    connection is passed (e.g. in tests)."""
    fn = _DISPATCH.get(spec.query_type)
    if fn is None:
        raise QueryValidationError(f"unknown query_type {spec.query_type!r} -- "
                                    f"must be one of {sorted(_DISPATCH)}")
    t0 = time.monotonic()
    result = fn(con, spec)
    result.execution_metadata["duration_ms"] = round((time.monotonic() - t0) * 1000, 2)
    if log:
        _log_query(reg or registry.connect_registry(), result)
    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _spec_params(spec: QuerySpec) -> dict:
    return {"entities": spec.entities, "entity_kind": spec.entity_kind, "start": spec.start,
            "end": spec.end, "as_of": spec.as_of, "fields": spec.fields, "filters": spec.filters,
            "group_by": spec.group_by, "sort_by": spec.sort_by, "limit": spec.limit,
            "min_confidence": spec.min_confidence, "sources": spec.sources}


def _exec_meta() -> dict:
    return {"executed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "code_fingerprint": registry.code_fingerprint()}


def _source_names(con: sqlite3.Connection, source_ids) -> list[str]:
    if source_ids is None or len(source_ids) == 0:
        return []
    ids = sorted(set(int(i) for i in source_ids.dropna().unique()))
    if not ids:
        return []
    ph = ",".join("?" * len(ids))
    rows = con.execute(f"SELECT name FROM sources WHERE source_id IN ({ph})", ids).fetchall()
    return sorted(r[0] for r in rows)


def _provenance_summary(con: sqlite3.Connection, df: pd.DataFrame) -> list[dict]:
    """Batch/summarized provenance -- one entry per (ticker, source_id,
    as_of_date) group actually present in the result, NOT one lineage
    lookup per row (would be O(n) against lineage.trace_equity_observation
    for large result sets). For full single-observation provenance
    (validation status, individual flags), call
    lineage.trace_equity_observation(con, ticker, trade_date) directly --
    this summary tells you WHICH groups exist so you know what to drill
    into."""
    if df.empty or "source_id" not in df.columns:
        return []
    g = df.groupby(["ticker", "source_id"]).agg(
        n_rows=("trade_date", "count"), first_date=("trade_date", "min"), last_date=("trade_date", "max"),
    ).reset_index()
    out = []
    for _, r in g.iterrows():
        src = con.execute("SELECT name, kind, reliability FROM sources WHERE source_id = ?",
                          (int(r.source_id),)).fetchone()
        out.append({"ticker": r.ticker, "source_id": int(r.source_id),
                   "source_name": src[0] if src else None, "source_kind": src[1] if src else None,
                   "source_reliability": src[2] if src else None, "n_rows": int(r.n_rows),
                   "first_date": r.first_date, "last_date": r.last_date})
    return out


def _log_query(reg: sqlite3.Connection, result: QueryResult) -> None:
    """query_log is deliberately lightweight -- parameters + result
    metadata only, never the observations DataFrame itself (per spec:
    'Do NOT store enormous duplicated result datasets unnecessarily')."""
    reg.execute(
        "INSERT INTO query_log (query_id, executed_at, code_fingerprint, query_type, "
        "parameters_json, row_count, date_range_start, date_range_end, data_sources_json, "
        "warnings_json, content_hash, entities_requested_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (result.query_id, result.execution_metadata["executed_at"],
         result.execution_metadata["code_fingerprint"], result.query_type,
         json.dumps(result.parameters, sort_keys=True, default=str), result.row_count,
         result.date_range[0], result.date_range[1], json.dumps(result.data_sources),
         json.dumps(result.warnings), result.content_hash(),
         json.dumps(result.entities_requested)),
    )
    reg.commit()
