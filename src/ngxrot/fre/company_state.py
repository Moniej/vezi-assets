"""Decision Intelligence Phase 1: Company State Engine.

Purely additive, read-only composition layer. Does not reimplement any
existing computation -- every field below is sourced from an already-real,
already-tested FRE/FSI module or table, called unmodified:
`economic_peer_taxonomy.classify_ticker`, `valuation_engine.
get_normalized_statement`/`value_company`, `company_memory.
build_company_memory`, `entity_context.get_entity_context`,
`financial_health_flags.compute_flags_for_ticker`, `watchlist.list_active`,
`company_intelligence.build_profile`, plus two direct, read-only queries
against `events` (ticker-scoped, PIT-gated on `announced_date`) and
`documents` (doc_type='dealing', insider filings, classified with the
exact same deterministic keyword rules `scripts/stage23_insider_dealing_
pilot.py` already established and validated -- not reinvented).

Every field is a `DataPoint` carrying an explicit status --
`KNOWN`/`UNKNOWN`/`CONFLICTING`/`STALE` -- never a silently-filled gap.
`UNKNOWN` is the correct, honest output wherever this platform genuinely
has no data (business description, segments, geography -- confirmed by
direct inspection to not exist anywhere in `ngx.sqlite`), not a defect to
work around.

## Known limitation, disclosed rather than hidden

`financial_health_flags.compute_flags_for_ticker()` has no `as_of_date`
parameter -- it always reads the LATEST conclusion regardless of the
state's own `as_of_date`. When `as_of_date` is not "today," this state
engine still calls it (there is no PIT-safe alternative on this platform
today) but marks the resulting DataPoints `STALE` with an explicit note,
rather than presenting them as PIT-correct.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from ngxrot import company_intelligence
from ngxrot.fre import economic_peer_taxonomy as ept
from ngxrot.fre.company_memory import build_company_memory
from ngxrot.fre.entity_context import get_entity_context
from ngxrot.fre.financial_health_flags import compute_flags_for_ticker
from ngxrot.fre.valuation_engine import get_normalized_statement, value_company
from ngxrot.fre.watchlist import list_active

ROOT = Path(__file__).resolve().parents[3]
DEALING_TEXT_DIR = ROOT / "data" / "staging" / "document_text"

KNOWN, UNKNOWN, CONFLICTING, STALE = "KNOWN", "UNKNOWN", "CONFLICTING", "STALE"

# Reused verbatim from scripts/stage23_insider_dealing_pilot.py -- the
# platform's own already-validated deterministic classification rule.
# Vesting/non-transactional disclosures are explicitly excluded here per
# that rule, never counted as a purchase or sale.
_VESTING_MARKERS = [
    r"not a purchase or sale", r"vesting of shares",
    r"restricted shares? performance plan",
    r"notification on vesting", r"notification of vesting",
]
_PURCHASE_MARKERS = [r"\bPURCHASE\b", r"\bBOUGHT\b", r"\bACQUISITION\b", r"\bACQUIRED\b"]
_SALE_MARKERS = [r"\bSALE\b", r"\bSOLD\b", r"\bDISPOSAL\b", r"\bDISPOSED\b"]

# Ticker-level event_type values from configs/event_taxonomy.toml's
# 'corporate' category that are regulatory/compliance in nature, split
# from the remaining corporate-event types.
_REGULATORY_EVENT_TYPES = {
    "regulatory_action", "regulatory_approval", "litigation", "suspension",
    "resumption", "delisting", "credit_rating_change",
}


@dataclass
class DataPoint:
    status: str  # KNOWN | UNKNOWN | CONFLICTING | STALE
    value: object | None
    as_of: str | None
    source: str  # always populated -- names the exact module/table this came from


def _known(value, as_of: str | None, source: str) -> DataPoint:
    return DataPoint(KNOWN, value, as_of, source)


def _unknown(source: str) -> DataPoint:
    return DataPoint(UNKNOWN, None, None, source)


# Public aliases -- other Decision Intelligence modules (e.g.
# company_economic_profile.py) construct DataPoints of their own and
# should use these rather than reaching into this module's underscore-
# prefixed internals.
known_point = _known
unknown_point = _unknown


@dataclass
class InsiderTransaction:
    doc_id: int
    filing_date: str
    nature: str  # PURCHASE | SALE
    routine_flag: bool  # scheme/plan/ESOS keyword present alongside a real transaction


@dataclass
class CompanyState:
    ticker: str
    as_of_date: str
    business: dict[str, DataPoint]
    financial: dict[str, DataPoint]
    corporate_events: DataPoint  # value: list[dict] when KNOWN
    regulatory: DataPoint
    insider_activity: DataPoint  # value: list[InsiderTransaction] when KNOWN
    market: dict[str, DataPoint]
    data_completeness: float  # fraction of all DataPoints above with status == KNOWN


def _classify_dealing_doc(doc_id: int) -> tuple[str | None, bool]:
    """(nature, routine_flag) -- nature is PURCHASE/SALE/None (vesting or
    ambiguous, excluded per the platform's own established rule)."""
    p = DEALING_TEXT_DIR / f"{doc_id}.txt"
    if not p.exists():
        return None, False
    text = p.read_text(encoding="utf-8", errors="ignore")
    if len(text.strip()) < 20:
        return None, False
    low = text.lower()
    if any(re.search(m, low) for m in _VESTING_MARKERS):
        return None, False
    n_purchase = len(re.findall("|".join(_PURCHASE_MARKERS), text, re.IGNORECASE))
    n_sale = len(re.findall("|".join(_SALE_MARKERS), text, re.IGNORECASE))
    if n_purchase > 0 and n_sale == 0:
        nature = "PURCHASE"
    elif n_sale > 0 and n_purchase == 0:
        nature = "SALE"
    else:
        return None, False
    routine = bool(re.search(r"\b(scheme|esos|reinvestment plan|vesting)\b", low))
    return nature, routine


def _insider_activity(con: sqlite3.Connection, ticker: str, as_of_date: str) -> DataPoint:
    rows = con.execute(
        "SELECT doc_id, filing_date FROM documents WHERE ticker = ? AND doc_type = 'dealing' "
        "AND filing_date <= ? ORDER BY filing_date", (ticker, as_of_date),
    ).fetchall()
    if not rows:
        return _unknown("documents WHERE doc_type='dealing' -- none on record for this ticker")
    txns: list[InsiderTransaction] = []
    for doc_id, filing_date in rows:
        nature, routine = _classify_dealing_doc(doc_id)
        if nature is not None:
            txns.append(InsiderTransaction(doc_id, filing_date, nature, routine))
    if not txns:
        return _unknown(f"{len(rows)} dealing filing(s) exist but all were vesting/ambiguous "
                         f"(classification per scripts/stage23_insider_dealing_pilot.py's own rule)")
    return _known(txns, as_of_date, f"{len(txns)} classified insider transaction(s) from "
                                     f"{len(rows)} real 'dealing' filing(s), PIT-gated on filing_date")


def _corporate_events(con: sqlite3.Connection, ticker: str, as_of_date: str) -> DataPoint:
    rows = con.execute(
        "SELECT event_id, event_type, announced_date, effective_date, headline, direction, "
        "severity, structurally_impairing, confidence FROM events "
        "WHERE ticker = ? AND category = 'corporate' AND event_type NOT IN ({}) "
        "AND announced_date <= ? ORDER BY announced_date".format(
            ",".join("?" * len(_REGULATORY_EVENT_TYPES))),
        (ticker, *_REGULATORY_EVENT_TYPES, as_of_date),
    ).fetchall()
    if not rows:
        return _unknown("events WHERE category='corporate' -- none on record for this ticker "
                         "as of this date")
    events = [dict(event_id=r[0], event_type=r[1], announced_date=r[2], effective_date=r[3],
                    headline=r[4], direction=r[5], severity=r[6],
                    structurally_impairing=bool(r[7]), confidence=r[8]) for r in rows]
    return _known(events, as_of_date, f"{len(events)} real event(s) from the events table, "
                                       f"PIT-gated on announced_date")


def _regulatory(con: sqlite3.Connection, ticker: str, as_of_date: str, level1: str | None) -> DataPoint:
    ticker_rows = con.execute(
        "SELECT event_id, event_type, category, announced_date, headline, direction, severity "
        "FROM events WHERE ticker = ? AND (category = 'corporate' AND event_type IN ({})) "
        "AND announced_date <= ? ORDER BY announced_date".format(
            ",".join("?" * len(_REGULATORY_EVENT_TYPES))),
        (ticker, *_REGULATORY_EVENT_TYPES, as_of_date),
    ).fetchall()
    sector_rows = []
    if level1 == "Financials":
        # 'banking' is this platform's only real sector-scoped regulatory
        # category with any rows today (5) -- applied only when the
        # ticker's own level1 is Financials, never blindly to every ticker.
        sector_rows = con.execute(
            "SELECT event_id, event_type, category, announced_date, headline, direction, severity "
            "FROM events WHERE category = 'banking' AND ticker IS NULL AND announced_date <= ? "
            "ORDER BY announced_date", (as_of_date,),
        ).fetchall()
    all_rows = list(ticker_rows) + list(sector_rows)
    if not all_rows:
        return _unknown("events WHERE event_type is a regulatory type -- none on record for "
                         "this ticker or its sector as of this date")
    reg = [dict(event_id=r[0], event_type=r[1], category=r[2], announced_date=r[3],
                headline=r[4], direction=r[5], severity=r[6]) for r in all_rows]
    return _known(reg, as_of_date, f"{len(ticker_rows)} ticker-specific + {len(sector_rows)} "
                                    f"sector-level regulatory event(s), PIT-gated on announced_date")


def build_company_state(con: sqlite3.Connection, ticker: str, as_of_date: str,
                         intelligence_cache: dict | None = None) -> CompanyState:
    """`intelligence_cache` is passed straight through to `company_intelligence.
    build_profile()`'s own `cache` parameter -- that call is expensive on a
    cold cache (~15-20s, one-time universe/price-panel load) and near-free
    once warm (~0.4s). Callers building state for multiple tickers/dates
    should pass the SAME dict across calls; a fresh `None` is safe but slow."""
    business: dict[str, DataPoint] = {}
    tax = ept.classify_ticker(con, ticker, as_of_date)
    if tax.classified:
        business["sector"] = _known(tax.level1, tax.retrieval_date, tax.evidence_source)
        business["sub_industry"] = _known(tax.level2, tax.retrieval_date, tax.evidence_source)
        business["business_model"] = _known(tax.business_model, tax.retrieval_date, tax.evidence_source)
    else:
        business["sector"] = _unknown(f"economic_peer_taxonomy: {tax.exclusion_reason}")
        business["sub_industry"] = _unknown(f"economic_peer_taxonomy: {tax.exclusion_reason}")
        business["business_model"] = _unknown(f"economic_peer_taxonomy: {tax.exclusion_reason}")
    # Confirmed by direct inspection (decision_intelligence_baseline_audit.md
    # Section 3): no business-description, segment, or geography data exists
    # anywhere on this platform. Honest UNKNOWN, not a guess.
    business["business_description"] = _unknown("no business-description field exists on this platform")
    business["segments"] = _unknown("no segment-reporting data exists on this platform")
    business["geography"] = _unknown("no structured geography field exists on this platform "
                                      "(AIRTELAFRI's USD reporting currency implies pan-African "
                                      "operations, but this is inference, not a stored fact -- "
                                      "correctly left UNKNOWN, not asserted as geography)")
    ec = get_entity_context(con, ticker, as_of_date)
    if ec is not None:
        business["entity_relationships"] = _known(
            ec.relationships, as_of_date, "entity_context.get_entity_context()")
    else:
        business["entity_relationships"] = _unknown("no entity-graph presence known for this ticker")

    financial: dict[str, DataPoint] = {}
    stmt = get_normalized_statement(con, ticker, as_of_date)
    for line_item in ("revenue", "net_profit", "equity", "assets", "liabilities"):
        li = stmt.line_items[line_item]
        if li.status == "known":
            financial[line_item] = _known(li.value, li.period_end,
                                           f"valuation_engine.get_normalized_statement, fact_id={li.fact_id}")
        else:
            financial[line_item] = _unknown("valuation_engine.get_normalized_statement: DATA_GAP")
    tv = value_company(con, ticker, as_of_date)
    financial["valuation_confidence"] = _known(
        tv.valuation_confidence, as_of_date, "valuation_engine.value_company()")
    financial["intrinsic_value_range"] = (
        _known(tv.intrinsic_value_range, as_of_date, "valuation_engine.value_company()")
        if tv.intrinsic_value_range is not None
        else _unknown("valuation_engine.value_company(): no numeric method result available"))
    flags = compute_flags_for_ticker(con, ticker)
    flag_status = STALE if as_of_date != date.today().isoformat() else KNOWN
    fired_flags = {f.flag_name: f.triggering_value for f in flags if f.status == "computed" and f.fired}
    if any(f.status == "computed" for f in flags):
        financial["accounting_anomaly_flags"] = DataPoint(
            flag_status, fired_flags, as_of_date,
            "financial_health_flags.compute_flags_for_ticker() -- NOT PIT-parameterized, "
            "always reads the latest conclusion; marked STALE when as_of_date != today")
    else:
        financial["accounting_anomaly_flags"] = _unknown(
            "financial_health_flags: insufficient_data for every rule")
    mem = build_company_memory(con, ticker, as_of_date)
    financial["dividend_history"] = (
        _known(mem.dividend_history, as_of_date, "company_memory.build_company_memory()")
        if mem.dividend_history else
        _unknown("company_memory: no dividend history on record"))

    market: dict[str, DataPoint] = {}
    try:
        profile = company_intelligence.build_profile(con, ticker, as_of=as_of_date, cache=intelligence_cache)
        market["close"] = (_known(profile.close, as_of_date, "company_intelligence.build_profile()")
                            if profile.close is not None else _unknown("company_intelligence: no price on record"))
        market["adtv_60d_ngn"] = (_known(profile.adtv_60d_ngn, as_of_date, "company_intelligence.build_profile()")
                                   if profile.adtv_60d_ngn is not None else _unknown("company_intelligence: ADTV unavailable"))
        market["realized_vol_ann_12m"] = (
            _known(profile.realized_vol_ann_12m, as_of_date, "company_intelligence.build_profile()")
            if profile.realized_vol_ann_12m is not None else _unknown("company_intelligence: volatility unavailable"))
        market["max_drawdown_3y"] = (
            _known(profile.max_drawdown_3y, as_of_date, "company_intelligence.build_profile()")
            if profile.max_drawdown_3y is not None else _unknown("company_intelligence: drawdown unavailable"))
        market["data_quality_flags"] = (
            _known(profile.data_quality_flags, as_of_date, "company_intelligence.build_profile()")
            if profile.data_quality_flags else _known([], as_of_date, "company_intelligence.build_profile()"))
    except Exception as exc:  # company_intelligence has real, disclosed failure modes for thin tickers
        market["close"] = _unknown(f"company_intelligence.build_profile() raised: {exc}")
        for k in ("adtv_60d_ngn", "realized_vol_ann_12m", "max_drawdown_3y", "data_quality_flags"):
            market[k] = _unknown(f"company_intelligence.build_profile() raised: {exc}")
    active_watch = [w for w in list_active(con, as_of_date) if w.ticker == ticker]
    market["watchlist_status"] = (_known(active_watch[0], as_of_date, "watchlist.list_active()")
                                   if active_watch else _unknown("watchlist: not currently on the watchlist"))

    corporate_events = _corporate_events(con, ticker, as_of_date)
    regulatory = _regulatory(con, ticker, as_of_date, tax.level1 if tax.classified else None)
    insider_activity = _insider_activity(con, ticker, as_of_date)

    all_points = (list(business.values()) + list(financial.values()) + list(market.values())
                  + [corporate_events, regulatory, insider_activity])
    n_known = sum(1 for p in all_points if p.status == KNOWN)
    completeness = n_known / len(all_points) if all_points else 0.0

    return CompanyState(
        ticker=ticker, as_of_date=as_of_date, business=business, financial=financial,
        corporate_events=corporate_events, regulatory=regulatory, insider_activity=insider_activity,
        market=market, data_completeness=completeness,
    )
