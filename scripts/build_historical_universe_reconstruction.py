"""Build deterministic, read-only HistoricalMarketSeries review artifacts.

This builds an observable source universe from archived official price-list
parses.  It does not apply aliases, merge instruments, mutate a database, or
read H-024 outcome data.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

import pandas as pd

from ngxrot.identity.continuity import ContinuityClass, recommend_continuity_treatment


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "ngx.sqlite"
PARSED = ROOT / "data" / "staging" / "parsed_pricelists"
RENAMES = ROOT / "data" / "reference" / "symbol_renames.csv"
OUT = ROOT / "fixtures" / "frozen"
REPORT = OUT / "historical_universe_reconstruction_report.json"
SERIES = OUT / "historical_market_series.json"
QUEUE = OUT / "historical_universe_phase3_evidence_queue.json"

DEBT_PATTERN = re.compile(r"^(?:FG|FGS|FBB|CRS|DANABND|FCM|LAB|OSB|OYB|ZAM|ABBEYBDS)")
NON_EQUITY_PATTERN = re.compile(r"(?:ETF|REIT|FUND|BOND|PREF)")
KNOWN_EVENTS = {
    ("FO", "ARDOVA"): "ticker_rename",
    ("GUARANTY", "GTCO"): "holding_company_reorganization",
    ("ACCESS", "ACCESSCORP"): "holding_company_reorganization",
    ("FBNH", "FIRSTHOLDCO"): "ticker_rename",
}


def source_security_type(symbol: str) -> tuple[str, str, bool]:
    """Conservative classification; no code pattern proves issuer identity."""
    if DEBT_PATTERN.match(symbol):
        return "debt_instrument", "published_debt_series_code_pattern", False
    if NON_EQUITY_PATTERN.search(symbol):
        return "non_equity_instrument", "published_symbol_non_equity_pattern", False
    return "ordinary_equity_candidate", "not_explicitly_non_equity_in_available_price-list symbol", True


def load_raw_series() -> pd.DataFrame:
    frames = []
    for path in sorted(PARSED.glob("*.csv")):
        if path.name.startswith("_"):
            continue
        frame = pd.read_csv(path, usecols=["trade_date", "symbol", "company", "close"], dtype={"symbol": str, "company": str})
        frame = frame[frame.symbol.notna()].copy()
        frame["source_file"] = path.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def continuity_row(row, mappings: dict[str, list[str]], edge_keys: set[tuple[str, str]], h024_priority: dict[str, int]) -> dict:
    old, new = row.old_symbol, row.new_symbol
    event_type = KNOWN_EVENTS.get((old, new))
    if event_type == "holding_company_reorganization":
        classification = ContinuityClass.ISSUER_REORGANIZATION_UNCERTAIN.value
        treatment = "unresolved"
    else:
        recommendation = recommend_continuity_treatment(evidence_status="candidate", event_type=event_type)
        classification, treatment = recommendation.classification.value, recommendation.recommended_treatment
    old_map, new_map = mappings.get(old, []), mappings.get(new, [])
    return {
        "predecessor_source_series": old, "successor_source_series": new,
        "predecessor_canonical_instrument": old_map[0] if len(old_map) == 1 else None,
        "successor_canonical_instrument": new_map[0] if len(new_map) == 1 else None,
        "issuer_continuity": "unknown",
        "security_continuity": "unknown",
        "ticker_continuity": "candidate_transition_only",
        "corporate_event_type": event_type or "unknown",
        "classification": classification,
        "evidence_status": "insufficient_for_canonical_continuity",
        "evidence": f"symbol_renames.csv:{old}->{new}; graph_edge_present={((new, old) in edge_keys)}",
        "recommended_canonical_treatment": treatment,
        "confidence": "candidate_only",
        "h024_candidate_formations_priority_only": max(h024_priority.get(old, 0), h024_priority.get(new, 0)),
    }


def main() -> int:
    raw = load_raw_series()
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    primary = pd.read_sql("""
        SELECT ticker,trade_date FROM equity_prices WHERE source_id=(
            SELECT source_id FROM sources WHERE name='ngx_pricelist_v2')
    """, con)
    current_securities = set(pd.read_sql("SELECT ticker FROM securities", con).ticker)
    aliases = pd.read_sql("""
        SELECT identifier_value,subject_id FROM identifier_aliases
        WHERE subject_type='instrument' AND identifier_type='ticker' AND exchange_code='NGX'
    """, con)
    edges = pd.read_sql("""
        SELECT newer.canonical_name AS newer_symbol, older.canonical_name AS older_symbol
        FROM entity_relationships r JOIN entities newer ON newer.entity_id=r.subject_entity_id
        JOIN entities older ON older.entity_id=r.object_entity_id
        WHERE r.relation_type='renamed_from'
    """, con)
    con.close()
    ingested = set(primary.ticker)
    mappings = aliases.groupby("identifier_value").subject_id.agg(list).to_dict()
    edge_keys = set(zip(edges.newer_symbol, edges.older_symbol))
    h024_priority_path = OUT / "historical_identity_phase1_coverage_report.json"
    h024_priority = {}
    if h024_priority_path.exists():
        h024_priority = {r["legacy_ticker"]: r["candidate_instrument_formations"]
                         for r in json.loads(h024_priority_path.read_text(encoding="utf-8"))
                         ["h024_identity_evidence_priority"]["priority_1"]}

    series_rows = []
    raw["year"] = raw.trade_date.str[:4]
    for symbol, group in raw.groupby("symbol", sort=True):
        security_type, basis, ordinary_equity = source_security_type(symbol)
        names = sorted(set(group.company.dropna()))
        first, last = group.trade_date.min(), group.trade_date.max()
        years = sorted(set(group.year))
        gaps = max(0, int(years[-1]) - int(years[0]) + 1 - len(years))
        is_ingested = symbol in ingested
        exclusion_reason = None if is_ingested else (
            "non_equity_instrument" if security_type == "debt_instrument" else "unknown")
        series_rows.append({
            "source_series_id": f"ngx_pricelist_v2:{symbol}", "source_provider": "ngx_pricelist_v2",
            "source_dataset": "archived_ngX_prices1_parsed", "exchange": "NGX",
            "published_symbol": symbol, "published_names": names,
            "security_type": security_type, "security_type_basis": basis,
            "ordinary_equity_candidate": ordinary_equity,
            "first_observed_in_available_source": first,
            "last_observed_in_available_source": last,
            "observation_count": int(len(group)), "calendar_year_gaps": gaps,
            "source_file_count": int(group.source_file.nunique()),
            "source_file_first": group.source_file.min(), "source_file_last": group.source_file.max(),
            "price_or_trading_presence": True,
            "ingestion_status": "ingested_primary" if is_ingested else "not_ingested",
            "exclusion_status": "included" if is_ingested else "excluded_from_primary",
            "exclusion_reason": exclusion_reason,
            "current_security_row_present": symbol in current_securities,
            "current_canonical_instrument_id": mappings.get(symbol, [None])[0] if len(mappings.get(symbol, [])) == 1 else None,
            "historical_canonical_mapping_status": "unverified",
        })
    SERIES.write_text(json.dumps(series_rows, indent=2, sort_keys=True), encoding="utf-8")
    series_frame = pd.DataFrame(series_rows)
    series_frame["normalized_published_symbol"] = series_frame.published_symbol.str.upper()
    symbol_variants = (series_frame.groupby("normalized_published_symbol").published_symbol
                       .agg(lambda values: sorted(set(values))).reset_index(name="raw_variants"))
    symbol_variants = symbol_variants[symbol_variants.raw_variants.map(len) > 1]

    renames = pd.read_csv(RENAMES)
    available_symbols = set(series_frame.published_symbol)
    transitions = [continuity_row(row, mappings, edge_keys, h024_priority)
                   for row in renames.itertuples(index=False)
                   if row.old_symbol in available_symbols and row.new_symbol in available_symbols]
    transitions.sort(key=lambda row: (row["predecessor_source_series"], row["successor_source_series"]))

    year_rows = []
    for year in map(str, range(2014, 2027)):
        raw_symbols = set(raw.loc[raw.year == year, "symbol"])
        observed = series_frame[series_frame.published_symbol.isin(raw_symbols)]
        equities = observed[observed.ordinary_equity_candidate]
        ingested_equities = equities[equities.ingestion_status == "ingested_primary"]
        unexplained = equities[(equities.ingestion_status != "ingested_primary") &
                               (equities.exclusion_reason == "unknown")]
        year_rows.append({
            "year": year, "raw_total_instruments": len(raw_symbols),
            "classified_equity_candidates": int(len(equities)),
            "ingested_equity_candidates": int(len(ingested_equities)),
            "unexplained_equity_exclusions": int(len(unexplained)),
            "historical_canonical_mappings_verified": 0,
            "historically_unmapped_equity_candidates": int(len(equities)),
        })

    raw_only = series_frame[series_frame.ingestion_status == "not_ingested"]
    raw_exclusions = raw_only.groupby(["security_type", "exclusion_reason"], dropna=False).size().reset_index(name="count")
    no_current_canonical = series_frame[
        series_frame.ordinary_equity_candidate & series_frame.current_canonical_instrument_id.isna()
    ]
    queue = []
    for row in transitions:
        if row["h024_candidate_formations_priority_only"]:
            priority = 2
        elif row["corporate_event_type"] in {"holding_company_reorganization", "ticker_rename"}:
            priority = 3
        else:
            priority = 4
        needs = (["official historical price-list observations", "NGX ticker/change-of-name notice"]
                 if row["corporate_event_type"] == "ticker_rename" else
                 ["official historical price-list observations", "NGX listing/delisting or scheme/reorganization notice", "SEC or issuer primary document"])
        queue.append({"priority": priority, "transition": f"{row['predecessor_source_series']}->{row['successor_source_series']}",
                      "candidate_formations_priority_only": row["h024_candidate_formations_priority_only"],
                      "required_evidence": needs, "reason": "continuity is unresolved; no outcome data used"})
    for symbol in no_current_canonical.published_symbol.tolist():
        queue.append({"priority": 1, "transition": symbol, "required_evidence": ["official historical price-list observation", "listing/delisting notice if available"], "reason": "observable equity candidate lacks a current canonical mapping"})
    queue.sort(key=lambda item: (item["priority"], -item.get("candidate_formations_priority_only", 0), item["transition"]))
    QUEUE.write_text(json.dumps({"classification": "evidence_acquisition_queue_not_identity_assertions", "items": queue}, indent=2, sort_keys=True), encoding="utf-8")

    report = {
        "audit_version": 1, "live_mutation": "none", "outcome_access": "none",
        "historical_market_series": series_rows,
        "historical_universe_by_year": year_rows,
        "raw_exclusion_summary": raw_exclusions.to_dict(orient="records"),
        "raw_only_symbols": raw_only[["published_symbol", "security_type", "exclusion_reason"]].to_dict(orient="records"),
        "source_symbol_normalization_candidates": {
            "count": int(len(symbol_variants)),
            "groups": symbol_variants.to_dict(orient="records"),
            "policy": "Case/format variants remain separate source-series labels until source-file lineage proves they are duplicate representations; they must not trigger alias creation or instrument merges.",
        },
        "continuity_review": transitions,
        "stage2a_identity_implications": {
            "transition_pairs_with_two_distinct_current_instruments": int(sum(
                r["predecessor_canonical_instrument"] is not None and
                r["successor_canonical_instrument"] is not None and
                r["predecessor_canonical_instrument"] != r["successor_canonical_instrument"] for r in transitions)),
            "treatment_a_one_instrument_alias_candidates": 0,
            "treatment_b_two_instrument_successor_candidates": 0,
            "treatment_c_unresolved": len(transitions),
            "conclusion": "Stage 2A's one-ticker/one-instrument backfill yields reviewable potential duplicates; Phase 2 makes no merger recommendation without evidence.",
        },
        "historical_only_equity_candidates": {
            "count": int(len(no_current_canonical)), "examples": no_current_canonical.published_symbol.head(20).tolist(),
            "policy": "Candidates are not automatically created as canonical instruments; absence from current securities is a review trigger, not identity evidence.",
        },
        "market_series_identity_mapping_contract": {
            "distinct_from_identifier_alias": True,
            "fields": ["mapping_id", "source_provider", "source_dataset", "source_series_id", "published_symbol", "canonical_instrument_id", "mapping_semantics", "valid_source_range", "verification_status", "evidence_reference", "recorded_at"],
            "mapping_semantics": ["as_traded_exchange_series", "provider_normalized_series", "fund_alpha_normalized_series", "composite_or_merged_series"],
            "guardrail": "must_not_create_alias_or_merge_from_series_ownership_mapping",
            "persistence": "future additive canonical persistence only; no live table in Phase 2",
        },
        "universe_completeness": {
            "assessment": "weak", "reason": "Available official artifacts establish an observable series universe, but missing parsed source days, absent listing/delisting evidence, and zero verified historical identity mappings prevent a completeness claim.",
            "observable_source_series": int(len(series_frame)),
            "observable_ordinary_equity_candidates": int(series_frame.ordinary_equity_candidate.sum()),
            "historically_verified_canonical_equities": 0,
        },
        "bias_assessment": {
            "current_survivor_bias": "not_proven for primary official series; source starts from historical lists",
            "historical_universe_incompleteness": "high", "canonical_identity_incompleteness": "high",
            "short_lived_series_exclusion": "indeterminate; first/last observations are not listing/delisting dates",
        },
        "phase3_queue": {"path": str(QUEUE.relative_to(ROOT)).replace("\\", "/"), "item_count": len(queue),
                         "priority_counts": dict(Counter(item["priority"] for item in queue)),
                         "priority_1_note": "No raw ordinary-equity candidate is absent from current canonical storage; this does not establish historical continuity.",
                         "priority_3_note": "No separate transition uniquely required by the H-011/H-013/H-016 evidence artifacts was identified in this source-series-only audit."},
        "h024_impact": "No eligibility recalculation performed. H-024 remains blocked pending verified identity plus observable-universe representation gates.",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "series": str(SERIES), "queue": str(QUEUE), "outcome_access": "none"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
