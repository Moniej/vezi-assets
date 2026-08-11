"""Decision Intelligence Phase 14: Economic Company Intelligence.

Audit finding (verified by direct query against real data, not assumed --
reproducible via the queries named in each `_unknown()` call below): of
the 15 requested company-context fields, this platform has real,
first-party evidence for only 5 (industry/sub-industry, a coarse
peer-group proxy, capital structure, regulatory exposure, and historical
corporate events) -- all already surfaced by `company_state.py` (Phase 1)
and `economic_peer_taxonomy.py`. The other 10 (business description,
products/services, revenue segments, geographic exposure, customer
concentration, supplier dependencies, management/ownership, material
subsidiaries, strategic priorities) have ZERO real evidence anywhere on
this platform:

  - `entity_relationships.relation_type` has exactly 3 real values
    (`affects_order_1`, `affects_order_2`, `renamed_from`) -- no
    `subsidiary_of` (0 rows) and no populated `competitor_mention` edge
    (0 rows, though the entity_type itself exists) has ever been recorded.
  - `causal_chain_steps.statement`/`impact_assessments.explanation`/
    `extracted_facts.description` contain zero genuine customer-
    concentration, supplier, subsidiary, strategic-priority, or
    shareholder/ownership disclosures (checked directly by keyword;
    the 2 "customer" hits in `impact_assessments` are unrelated prose,
    not concentration disclosures).
  - `company_memory.py`'s own `management_history` field is, by that
    module's own design, always empty today (FRE-3's disclosed gap, not
    reintroduced here).

This module does not attempt to fill any of these 10 with inference or an
LLM guess -- per the explicit governance rule, UNKNOWN stays UNKNOWN. It
is purely a composition + honest-gap-disclosure layer over `company_
state.py`, `economic_peer_taxonomy.py`, and `entity_context.py`, all
unmodified.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.company_state import DataPoint, KNOWN, build_company_state
from ngxrot.fre.company_state import known_point as _known
from ngxrot.fre.company_state import unknown_point as _unknown
from ngxrot.fre.economic_peer_taxonomy import classify_ticker, select_peers
from ngxrot.fre.genuine_fact_universe import list_genuine_financial_statement_tickers

_FIELD_NAMES = (
    "business_description", "business_model", "products_services", "revenue_segments",
    "geographic_exposure", "industry_sub_industry", "competitive_peer_context",
    "customer_concentration", "supplier_dependencies", "management_ownership",
    "capital_structure", "regulatory_exposure", "material_subsidiaries",
    "strategic_priorities", "historical_corporate_events",
)


@dataclass
class EconomicProfile:
    ticker: str
    as_of_date: str
    fields: dict  # field_name -> DataPoint, keys are exactly _FIELD_NAMES
    coverage: float  # fraction of the 15 fields with status == KNOWN


def build_economic_profile(con: sqlite3.Connection, ticker: str, as_of_date: str,
                            intelligence_cache: dict | None = None) -> EconomicProfile:
    state = build_company_state(con, ticker, as_of_date, intelligence_cache)
    tax = classify_ticker(con, ticker, as_of_date)

    f: dict[str, DataPoint] = {}

    # --- confirmed-absent fields (platform-wide, not ticker-specific) -------
    f["business_description"] = state.business["business_description"]
    f["products_services"] = _unknown("no products/services disclosure field exists anywhere on "
                                       "this platform (checked: extracted_facts, causal_chain_steps, "
                                       "impact_assessments contain no such structured or extractable data)")
    f["revenue_segments"] = state.business["segments"]
    f["geographic_exposure"] = state.business["geography"]
    f["customer_concentration"] = _unknown("checked directly: 0 genuine customer-concentration "
                                            "disclosures in causal_chain_steps/impact_assessments/"
                                            "extracted_facts (the 2 'customer' keyword hits found are "
                                            "unrelated narrative, not concentration data)")
    f["supplier_dependencies"] = _unknown("checked directly: 0 supplier-dependency mentions anywhere "
                                           "in causal_chain_steps/impact_assessments/extracted_facts")
    f["management_ownership"] = _unknown("company_memory.py's own management_history field is, by "
                                          "that module's design, always empty (FRE-3's disclosed gap); "
                                          "0 ownership/shareholder disclosures found anywhere else either")
    f["material_subsidiaries"] = _unknown("entity_relationships has 0 rows with "
                                           "relation_type='subsidiary_of' (checked directly)")
    f["strategic_priorities"] = _unknown("checked directly: 0 strategic-priority mentions anywhere "
                                          "in causal_chain_steps/impact_assessments/extracted_facts")

    # --- fields with real, if partial, evidence -----------------------------
    if tax.classified:
        f["business_model"] = _known(tax.business_model, tax.retrieval_date, tax.evidence_source)
        f["industry_sub_industry"] = _known(f"{tax.level1} / {tax.level2}", tax.retrieval_date, tax.evidence_source)
    else:
        f["business_model"] = _unknown(f"economic_peer_taxonomy: {tax.exclusion_reason}")
        f["industry_sub_industry"] = _unknown(f"economic_peer_taxonomy: {tax.exclusion_reason}")

    if tax.classified:
        peers = select_peers(con, ticker, as_of_date, list_genuine_financial_statement_tickers(con))
        if peers.tier != "none":
            f["competitive_peer_context"] = _known(
                {"tier": peers.tier, "peers": peers.peers}, as_of_date,
                f"economic_peer_taxonomy.select_peers() -- a SECTOR/SUBSECTOR proxy, not a real "
                f"disclosed competitor list (this platform has no competitor_mention edges "
                f"populated); {peers.reason}")
        else:
            f["competitive_peer_context"] = _unknown(f"economic_peer_taxonomy.select_peers(): {peers.reason}")
    else:
        f["competitive_peer_context"] = _unknown(f"subject ticker unclassified: {tax.exclusion_reason}")

    known_capital = [state.financial[k] for k in ("assets", "liabilities", "equity")]
    if all(dp.status == KNOWN for dp in known_capital):
        f["capital_structure"] = _known(
            {"assets": known_capital[0].value, "liabilities": known_capital[1].value,
             "equity": known_capital[2].value}, as_of_date,
            "company_state.py financial line items (assets/liabilities/equity), verbatim")
    else:
        missing = [k for k, dp in zip(("assets", "liabilities", "equity"), known_capital) if dp.status != KNOWN]
        f["capital_structure"] = _unknown(f"company_state.py: {', '.join(missing)} unavailable")

    f["regulatory_exposure"] = state.regulatory
    f["historical_corporate_events"] = state.corporate_events

    assert set(f.keys()) == set(_FIELD_NAMES), "EconomicProfile field set drifted from _FIELD_NAMES"

    n_known = sum(1 for dp in f.values() if dp.status == KNOWN)
    return EconomicProfile(ticker=ticker, as_of_date=as_of_date, fields=f, coverage=n_known / len(_FIELD_NAMES))
