"""Read-only Phase 1 historical identity evidence and coverage audit.

The script creates review artifacts only. It does not apply the assertion
migration, insert aliases, or resolve H-024 identity through current tickers.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "ngx.sqlite"
RENAMES = ROOT / "data" / "reference" / "symbol_renames.csv"
POLICY = ROOT / "configs" / "historical_identity_source_policy.toml"
H024 = ROOT / "fixtures" / "frozen" / "h024_liquidity_shock_volatility.sqlite"
OUT = ROOT / "fixtures" / "frozen"
CANDIDATES = OUT / "historical_identity_phase1_candidates.json"
REPORT = OUT / "historical_identity_phase1_coverage_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    aliases = pd.read_sql("SELECT * FROM identifier_aliases", con)
    instruments = pd.read_sql("SELECT * FROM instrument_listings", con)
    mappings = pd.read_sql("SELECT * FROM legacy_identity_mappings", con)
    prices = pd.read_sql("SELECT ticker,trade_date FROM equity_prices", con)
    securities = pd.read_sql("SELECT ticker,name,listing_date,delisting_date FROM securities", con)
    con.close()
    prices["year"] = prices.trade_date.str[:4]
    canonical_by_ticker = dict(zip(aliases.identifier_value, aliases.subject_id))
    renames = pd.read_csv(RENAMES)
    verified = renames[renames.status == "verified"].copy()
    candidate_rows = []
    for row in verified.itertuples(index=False):
        instrument = canonical_by_ticker.get(row.new_symbol)
        candidate_rows.extend([
            {"candidate_key": f"{row.old_symbol}:{row.old_last}", "canonical_instrument_id": instrument,
             "identifier_type": "ticker", "identifier_value": row.old_symbol, "exchange_code": "NGX",
             "valid_from": row.old_last, "valid_to": None, "validity_precision": "observed_on_date_only",
             "verification_status": "corroborated", "verification_method": "local_verified_rename_reference_pending_evidence_item",
             "source_authority_tier": "tier3", "citation_reference": f"data/reference/symbol_renames.csv#{row.old_symbol}->{row.new_symbol}",
             "evidence_item_id": None, "recorded_at": None,
             "promotion_blocker": "No EvidenceItem/Citation chain attached; cannot be verified or H-024 eligible."},
            {"candidate_key": f"{row.new_symbol}:{row.new_first}", "canonical_instrument_id": instrument,
             "identifier_type": "ticker", "identifier_value": row.new_symbol, "exchange_code": "NGX",
             "valid_from": row.new_first, "valid_to": None, "validity_precision": "observed_on_date_only",
             "verification_status": "corroborated", "verification_method": "local_verified_rename_reference_pending_evidence_item",
             "source_authority_tier": "tier3", "citation_reference": f"data/reference/symbol_renames.csv#{row.old_symbol}->{row.new_symbol}",
             "evidence_item_id": None, "recorded_at": None,
             "promotion_blocker": "No EvidenceItem/Citation chain attached; cannot be verified or H-024 eligible."},
        ])
    candidate_payload = {"classification": "review_candidates_not_identity_assertions", "source_sha256": sha256(RENAMES),
                         "source_policy_sha256": sha256(POLICY), "rows": candidate_rows,
                         "rule": "Local rename-reference rows never become verified without an approved EvidenceItem/Citation chain."}
    CANDIDATES.write_text(json.dumps(candidate_payload, indent=2, sort_keys=True), encoding="utf-8")

    coverage = {}
    for year in map(str, range(2014, 2027)):
        tickers = set(prices.loc[prices.year == year, "ticker"])
        coverage[year] = {"candidate_tickers": len(tickers), "historically_resolvable_verified": 0,
                          "unresolved_or_current_only": len(tickers), "ambiguous": 0, "coverage_pct": 0.0}
    h024 = sqlite3.connect(f"file:{H024}?mode=ro", uri=True)
    h024_rows = h024.execute("SELECT COUNT(*),COUNT(DISTINCT legacy_ticker),COUNT(DISTINCT formation_date) FROM h024_observations").fetchone()
    # This is deliberately an observation-count priority queue only.  It does
    # not select, materialize, or inspect any forward outcome field.
    h024_priority = [
        {"legacy_ticker": ticker, "candidate_instrument_formations": count}
        for ticker, count in h024.execute("""
            SELECT legacy_ticker, COUNT(*) FROM h024_observations
            GROUP BY legacy_ticker
            ORDER BY COUNT(*) DESC, legacy_ticker ASC
        """)
    ]
    h024.close()
    historical_tickers = set(prices.ticker)
    current_tickers = set(securities.ticker)
    report = {
        "current_identity_state": {"instrument_listings": len(instruments), "identifier_aliases": len(aliases),
            "aliases_valid_from": int(aliases.valid_from.notna().sum()), "aliases_valid_to": int(aliases.valid_to.notna().sum()),
            "aliases_without_historical_bounds": int(((aliases.valid_from.isna()) & (aliases.valid_to.isna())).sum()),
            "legacy_identity_mappings": len(mappings),
            "historically_unresolved_securities": len(instruments),
            "duplicate_ticker_namespaces": int(aliases.groupby(["identifier_value", "exchange_code"]).subject_id.nunique().gt(1).sum()),
            "known_verified_rename_rows": len(verified), "known_delisting_dates": int(securities.delisting_date.notna().sum())},
        "historical_resolution_coverage_by_year": coverage,
        "historical_universe_audit": {"historical_price_tickers": len(historical_tickers), "current_canonical_instruments": len(instruments),
            "historical_only_names": sorted(historical_tickers - current_tickers), "unmatched_historical_symbols": sorted(historical_tickers - set(canonical_by_ticker)),
            "delisting_dates_recorded": int(securities.delisting_date.notna().sum()),
            "survivorship_risk": "High: zero delisting dates are recorded; historical symbols remain legacy records but are not evidence-backed canonical history."},
        "source_availability": {"tier1_local_artifacts": [], "tier2_local_artifacts": [],
            "tier3_local_artifacts": ["data/reference/symbol_renames.csv (four internally marked verified rows; no EvidenceItem/Citation chain)"],
            "tier4_used": []},
        "assertion_counts": {"verified": 0, "corroborated_review_candidates": len(candidate_rows), "candidate": 0, "conflicting": 0, "unresolved": len(historical_tickers)},
        "h024_coverage_simulation": {"candidate_instrument_formations": h024_rows[0], "verified_identities": 0,
            "instrument_formations_unlocked": 0, "eligible_observations": 0, "instrument_clusters": 0, "formation_clusters": 0,
            "note": "No candidate is promoted to verified; no H-024 outcome data was opened."},
        "h024_identity_evidence_priority": {
            "method": "descending count of existing candidate instrument-formations; no predictor/outcome values inspected",
            "priority_1": h024_priority,
        },
        "proposed_pre_outcome_coverage_gate": {"minimum_verified_primary_observations": 5000,
            "minimum_verified_instrument_clusters": 30, "minimum_verified_formation_clusters": 24,
            "minimum_years_with_at_least_50_verified_observations": 5, "maximum_single_instrument_observation_share": 0.10,
            "maximum_single_year_observation_share": 0.40,
            "status": "requires_owner_approval_before_H024_outcome_testing"},
        "temporal_governance": "valid_from/valid_to describe real-world evidence; recorded_at is actual capture only. Strict system vintage remains unchanged; verified historical reconstruction is identity-only and explicitly disclosed.",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
