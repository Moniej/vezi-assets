"""Read-only audit of historical price-series identity semantics.

This intentionally examines only price-source lineage and metadata.  It never
opens the H-024 dataset and never reads a forward return or volatility field.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "ngx.sqlite"
PARSED = ROOT / "data" / "staging" / "parsed_pricelists"
ZIP_ARCHIVE = ROOT / "data" / "archive" / "pricelist_zips"
DOL_ARCHIVE = ROOT / "data" / "archive" / "dol_equities"
RENAMES = ROOT / "data" / "reference" / "symbol_renames.csv"
OUT = ROOT / "fixtures" / "frozen"
REPORT = OUT / "historical_market_identity_semantics_report.json"
SERIES = OUT / "historical_market_series_persistence.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_symbol_sets() -> dict[str, set[str]]:
    """Use parsed pre-ingestion files, not the database, as the raw audit side."""
    result = {str(year): set() for year in range(2014, 2027)}
    for path in sorted(PARSED.glob("*.csv")):
        if path.name.startswith("_"):
            continue
        year = path.name[:4]
        if year not in result:
            continue
        frame = pd.read_csv(path, usecols=["symbol"], dtype={"symbol": str})
        result[year].update(frame.symbol.dropna())
    return result


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    source_rows = pd.read_sql("""
        SELECT s.source_id,s.name,s.kind,s.reliability,s.base_confidence,
               COUNT(p.ticker) AS rows, COUNT(DISTINCT p.ticker) AS tickers,
               MIN(p.trade_date) AS first_date, MAX(p.trade_date) AS last_date
        FROM sources s LEFT JOIN equity_prices p ON p.source_id=s.source_id
        GROUP BY s.source_id,s.name,s.kind,s.reliability,s.base_confidence
        ORDER BY rows DESC,s.name
    """, con)
    primary = pd.read_sql("""
        SELECT ticker,trade_date,source_id FROM equity_prices
        WHERE source_id=(SELECT source_id FROM sources WHERE name='ngx_pricelist_v2')
    """, con)
    all_primary = pd.read_sql("""
        SELECT ticker,trade_date FROM equity_prices WHERE confidence>=0.9
          AND source_id IN (SELECT source_id FROM sources WHERE name IN
             ('ngx_pricelist_v1','ngx_pricelist_v2','ngx_dol_v1','ngx_list2_v1'))
    """, con)
    securities = pd.read_sql("SELECT ticker,name,listing_date,delisting_date FROM securities", con)
    aliases = pd.read_sql("SELECT identifier_value,subject_id FROM identifier_aliases WHERE subject_type='instrument' AND identifier_type='ticker' AND exchange_code='NGX'", con)
    relationships = pd.read_sql("""
        SELECT newer.canonical_name AS newer_symbol, older.canonical_name AS older_symbol,
               r.valid_from,r.valid_to,r.source_evidence_id,r.confidence,r.recorded_at
        FROM entity_relationships r
        JOIN entities newer ON newer.entity_id=r.subject_entity_id
        JOIN entities older ON older.entity_id=r.object_entity_id
        WHERE r.relation_type='renamed_from'
    """, con)
    con.close()

    raw_by_year = raw_symbol_sets()
    primary["year"] = primary.trade_date.str[:4]
    by_year = {}
    for year in map(str, range(2014, 2027)):
        raw = raw_by_year[year]
        ingested = set(primary.loc[primary.year == year, "ticker"])
        by_year[year] = {
            "raw_symbol_count": len(raw), "ingested_symbol_count": len(ingested),
            "raw_only_symbols": sorted(raw - ingested),
            "ingested_only_symbols": sorted(ingested - raw),
            "raw_ingested_exact_set_match": raw == ingested,
        }
    exact_raw_ingested_years = [year for year, values in by_year.items()
                                if values["raw_ingested_exact_set_match"]]
    mismatch_years = [year for year, values in by_year.items()
                      if not values["raw_ingested_exact_set_match"]]

    all_primary["year"] = all_primary.trade_date.str[:4]
    span = all_primary.groupby("ticker").agg(first_observation=("trade_date", "min"),
                                               last_observation=("trade_date", "max"),
                                               observations=("trade_date", "size"))
    annual = all_primary.groupby(["ticker", "year"]).size().rename("days").reset_index()
    years_by_ticker = annual.groupby("ticker").year.agg(list)
    security_map = securities.set_index("ticker")
    alias_map = aliases.groupby("identifier_value").subject_id.agg(list).to_dict()
    persistence = []
    for ticker, row in span.sort_index().iterrows():
        years = years_by_ticker[ticker]
        gaps = max(0, int(years[-1]) - int(years[0]) + 1 - len(years))
        mappings = alias_map.get(ticker, [])
        persistence.append({
            "ticker": ticker, "first_observation": row.first_observation,
            "last_observation": row.last_observation, "years_observed": len(years),
            "calendar_year_gaps": gaps, "observations": int(row.observations),
            "current_security_present": ticker in security_map.index,
            "canonical_instrument_id": mappings[0] if len(mappings) == 1 else None,
            "canonical_mapping_status": "unique_current_alias" if len(mappings) == 1 else
                                        ("ambiguous_current_alias" if len(mappings) > 1 else "unmapped"),
        })
    persistence_frame = pd.DataFrame(persistence)
    persistence_frame.to_csv(SERIES, index=False)

    renames = pd.read_csv(RENAMES)
    rename_audit = []
    for r in renames[renames.status == "verified"].itertuples(index=False):
        old = persistence_frame[persistence_frame.ticker == r.old_symbol]
        new = persistence_frame[persistence_frame.ticker == r.new_symbol]
        rename_audit.append({
            "old_symbol": r.old_symbol, "new_symbol": r.new_symbol,
            "review_file_status": "diagnostic_only_not_historical_alias_evidence",
            "old_raw_and_ingested": not old.empty, "new_raw_and_ingested": not new.empty,
            "old_last_observation": None if old.empty else old.iloc[0].last_observation,
            "new_first_observation": None if new.empty else new.iloc[0].first_observation,
            "stored_under_separate_tickers": not old.empty and not new.empty,
            "fund_alpha_row_relabeling_detected": False,
            "conclusion": "separate as-traded series; no alias promotion from this diagnostic",
        })

    yearly_active = all_primary.groupby("year").ticker.nunique()
    first_year = persistence_frame.first_observation.str[:4]
    last_year = persistence_frame.last_observation.str[:4]
    series_metrics = {
        "primary_official_tickers": len(persistence_frame),
        "share_starting_before_2016": float((persistence_frame.first_observation < "2016-01-01").mean()),
        "share_ending_before_2026": float((persistence_frame.last_observation < "2026-01-01").mean()),
        "average_years_observed": float(persistence_frame.years_observed.mean()),
        "active_series_by_year": {year: int(yearly_active.get(year, 0)) for year in map(str, range(2014, 2027))},
        "entries_by_year": {year: int((first_year == year).sum()) for year in map(str, range(2014, 2027))},
        "exits_by_year": {year: int((last_year == year).sum()) for year in map(str, range(2014, 2027))},
        "security_listing_dates_known": int(securities.listing_date.notna().sum()),
        "security_delisting_dates_known": int(securities.delisting_date.notna().sum()),
    }

    report = {
        "audit_version": 1,
        "outcome_access": "none",
        "raw_artifacts": {
            "official_pricelist_zip_count": len(list(ZIP_ARCHIVE.glob("*.zip"))),
            "official_dol_pdf_count": len(list(DOL_ARCHIVE.glob("*.pdf"))),
            "parsed_pre_ingestion_csv_count": len([p for p in PARSED.glob("*.csv") if not p.name.startswith("_")]),
            "raw_symbol_field": "symbol", "ingested_symbol_field": "ticker",
        },
        "data_lineage": [
            {"step": "Raw source", "value": "official NGX PRICES1 archive ZIPs; DOL PDFs; LIST2 recovery", "identity": "as-published symbol"},
            {"step": "Provider", "value": "ngx_pricelist_v2 (primary); ngx_dol_v1/list2_v1 gap recovery", "identity": "unchanged"},
            {"step": "Symbol handling", "value": "parsed symbol copied to ticker", "identity": "unchanged"},
            {"step": "Filtering", "value": "current code guards symbol/positive close/row confidence and has no current-security join; historic raw-to-DB exclusions remain partly unreconstructed", "identity": "filtered only / partly unknown"},
            {"step": "Normalization", "value": "none in primary row ingestion; rename_chain occurs only in IRU research grouping", "identity": "mapped downstream only"},
            {"step": "Ingestion", "value": "append-only equity_prices, source/confidence/as_of stamped", "identity": "unchanged"},
        ],
        "symbol_semantics": {
            "primary_official_pricelist": ["as_traded_historical_symbol", "classification_A"],
            "fund_alpha_research_universe": ["fund_alpha_normalized_symbol_for_grouping_only", "classification_C_consumer_layer"],
            "investing_backfill_code_path": ["currentish_filing_universe_requested_symbols", "classification_D_risk_if_used"],
            "overall": ["mixed", "classification_E_at_combined_panel_level"],
        },
        "raw_vs_ingested_by_year": by_year,
        "raw_to_ingested_lineage_limit": {
            "exact_set_match_years": exact_raw_ingested_years,
            "mismatch_years": mismatch_years,
            "conclusion": "Raw-only symbols are retained as explicit diagnostics. The checked-in current ingestion code has no current-security join, but it does not by itself explain every historic raw-to-DB exclusion; do not infer a historical filter policy.",
        },
        "series_persistence_artifact": {"path": str(SERIES.relative_to(ROOT)).replace("\\\\", "/"), "sha256": sha256(SERIES)},
        "series_metrics": series_metrics,
        "known_rename_diagnostics": rename_audit,
        "entity_relationship_rename_edges": relationships.to_dict(orient="records"),
        "entity_relationship_rename_edge_limits": {
            "edge_count": len(relationships),
            "missing_evidence_references": int(relationships.source_evidence_id.isna().sum()),
            "missing_recorded_at": int(relationships.recorded_at.isna().sum()),
            "conclusion": "These legacy graph edges explain existing downstream normalization but are not Phase-1 evidence-grade historical aliases or series-ownership mappings.",
        },
        "universe_construction": {
            "official_pricelist_method_1_historical_exchange_universe": True,
            "official_pricelist_evidence": "ingest_pricelists iterates parsed daily files and inserts their symbol rows; it does not start from securities.",
            "investing_backfill_method_2_currentish_filing_universe": True,
            "investing_backfill_evidence": "backfill_equities starts from the X-Issuer filing/corporate-action symbol universe and requests vendor history per resolved symbol.",
            "production_investing_rows": int(source_rows.loc[source_rows.name == "investing_com", "rows"].sum()),
        },
        "survivorship_assessment": {
            "classification": "high",
            "reason": "primary official rows originate from historical daily lists, but raw-to-DB exclusions are not fully reconstructed, listing/delisting metadata are empty, historical universe completeness has not been independently reconciled, and a currentish vendor-backfill path exists.",
            "known_historical_symbols_represented_by_primary": len(persistence_frame),
            "known_historical_symbols_missing_from_primary": None,
            "identity_unresolved": len(persistence_frame),
        },
        "market_series_ownership": {
            "can_prove_for_each_series_independently_of_alias": False,
            "separate_mapping_concept_justified": True,
            "proposed_type": "MarketSeriesIdentityMapping",
            "mapping_semantics": ["historical_exchange_symbol", "provider_normalized_symbol", "fund_alpha_normalized_symbol"],
            "guardrail": "must_not_create_identifier_alias_from_provider_or_fund_alpha_normalized_series_label",
            "current_evidence": "official source lineage supports as-traded series labels; current canonical InstrumentListing mappings do not prove historical issuer/instrument continuity.",
        },
        "h024_implication": "Remain blocked. Primary official rows retain historical symbols, so verified alias/series ownership evidence and historical-universe reconciliation are required before identity reconstruction can unlock H-024.",
        "coverage_gate_recommendation": {
            "minimum_primary_eligible_observations": 5000,
            "minimum_instrument_clusters": 30,
            "minimum_formation_month_clusters": 48,
            "minimum_calendar_years_with_meaningful_verified_coverage": 5,
            "maximum_single_instrument_share": 0.10,
            "maximum_single_year_share": 0.40,
            "minimum_verified_coverage_of_otherwise_data_eligible_observations": 0.40,
            "recommendation": "40% is a floor, not sufficient alone: it must pass all concentration, 48-month, and survivorship-reconciliation gates.",
            "status": "requires_owner_approval",
        },
        "next_action": "combination_ordered_phases: (1) normalized/as-traded MarketSeriesIdentityMapping lineage audit; (2) historical-universe reconstruction including delisted names; (3) Tier 1/2 alias evidence acquisition only for surviving verified series mappings.",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "series": str(SERIES), "outcome_access": "none"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
