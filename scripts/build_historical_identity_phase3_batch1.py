"""Freeze Batch 1 historical continuity reviews without mutating identity.

This script reads retained official materials and official historical price-list
parses.  It produces review artifacts only: it does not insert aliases, apply
the declared historical-identity migration, reconcile InstrumentListings, or
open H-024 outcome data.
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
ARCHIVE = ROOT / "data" / "archive" / "xissuer_docs"
OUT = ROOT / "fixtures" / "frozen" / "historical_identity_phase3_batch1"
POLICY = ROOT / "configs" / "historical_identity_source_policy.toml"
PRIORITY = ROOT / "fixtures" / "frozen" / "historical_identity_phase1_coverage_report.json"
SOURCE_BASELINE_COMMIT = "36316cb10a471f1a7e0af7f7d933e71442d25963"

CASE_FILES = {
    "access_scheme": "15197_34667_ACCESS_BANK_PLC_SCHEME_OF_ARRANGEMENT_BETWEEN_ACCESS_.pdf",
    "access_court": "15877_35271_ACCESS_BANK_PLC_COURT_SANCTION_OF_SCHEME_OF_ARRANGEME.pdf",
    "fbn_change": "25784_43129_FBN_HOLDINGS_PLC-FIRST_HOLDCO_PLC_-_CHANGE_OF_NAME_NOTIFICATION_CORPORATE_ACTIONS_FEBRUARY_2025.pdf",
    "fbn_agm": "25077_42626_FBN_HOLDINGS_PLC-FBN_HOLDINGS_PLC_-_RESOLUTIONS_PASSED_AT_THE_12TH_AGM_CORPORATE_ACTIONS_NOVEMBER_2024.pdf",
}

EXTERNAL_PRIMARY_SOURCES = {
    "ngx_gtb_delisting_gtco_listing": {
        "authority_tier": "tier_1",
        "source_authority": "Nigerian Exchange Limited",
        "document_type": "weekly_market_report_market_bulletin",
        "publication_date": "2021-06-25",
        "publication_precision": "date",
        "source_url": "https://doclib.ngxgroup.com/market_data-site/other-market-information-site/Week%20Market%20Report/Weekly%20Market%20Report%20for%20the%20Week%20Ended%2025-06-2021.pdf",
        "locator": "Other News / Delisting of Guaranty Trust Bank Plc and Listing of Guaranty Trust Holding Company Plc",
        "supported_claim": "GTB was delisted and GT HoldCo was listed on 2021-06-24 pursuant to a court-sanctioned scheme.",
        "artifact_retention": "external_url_only; direct download was unavailable in the managed environment",
        "content_sha256": None,
    },
    "ngx_fbn_name_and_symbol_change": {
        "authority_tier": "tier_1",
        "source_authority": "Nigerian Exchange Limited",
        "document_type": "market_bulletin",
        "publication_date": "2025-03-05",
        "publication_precision": "date",
        "source_url": "https://doclib.ngxgroup.com/Listings-site/corporate-disclosure-site/Documents/Market%20Bulletin%20on%20the%20Change%20of%20Name%20of%20FBN%20Holdings%20Plc.pdf",
        "locator": "Market Bulletin NGXREG/IRD/MB15/25/03/5",
        "supported_claim": "NGX implemented the change of name FBN Holdings Plc to First HoldCo Plc and changed the trading symbol from FBNH to FirstHoldCo.",
        "artifact_retention": "external_url_only; direct download was unavailable in the managed environment",
        "content_sha256": None,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def document_rows() -> dict[str, dict]:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = {}
    for key, filename in CASE_FILES.items():
        row = con.execute(
            """SELECT doc_id, source_url, filing_date, retrieved_date, source_id, source_confidence
                 FROM documents WHERE local_path LIKE ?""",
            (f"%{filename}%",),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"retained document metadata is missing: {filename}")
        artifact = ARCHIVE / filename
        if not artifact.exists():
            raise RuntimeError(f"retained document artifact is missing: {artifact}")
        rows[key] = {
            "document_id": row[0], "source_url": row[1], "metadata_filing_date": row[2],
            "retrieved_at": row[3], "source_id": row[4], "source_confidence": row[5],
            "artifact_path": str(artifact.relative_to(ROOT)).replace("\\", "/"),
            "byte_size": artifact.stat().st_size, "content_sha256": sha256(artifact),
            "artifact_retention": "locally_retained_original_pdf",
        }
    aliases = {}
    for ticker in ("ACCESS", "ACCESSCORP", "GUARANTY", "GTCO", "FBNH", "FIRSTHOLDCO"):
        rows_for_ticker = con.execute(
            """SELECT subject_id FROM identifier_aliases
                 WHERE subject_type='instrument' AND identifier_type='ticker'
                   AND exchange_code='NGX' AND identifier_value=?""", (ticker,)
        ).fetchall()
        aliases[ticker] = rows_for_ticker[0][0] if len(rows_for_ticker) == 1 else None
    con.close()
    return rows, aliases


def observed_symbol(symbol: str) -> dict:
    report = json.loads((ROOT / "fixtures" / "frozen" / "historical_market_series.json").read_text(encoding="utf-8"))
    record = next(row for row in report if row["published_symbol"] == symbol)
    return {
        "source_series_id": record["source_series_id"],
        "published_symbol": symbol,
        "published_names": record["published_names"],
        "first_observed_in_available_source": record["first_observed_in_available_source"],
        "last_observed_in_available_source": record["last_observed_in_available_source"],
        "source_file_first": record["source_file_first"],
        "source_file_last": record["source_file_last"],
    }


def source_file_symbol(date: str) -> dict:
    path = next(PARSED.glob(f"{date}_*.csv"))
    frame = pd.read_csv(path, usecols=["symbol", "company"])
    subset = frame[frame.symbol.isin(["FBNH", "FirstHoldCo", "FIRSTHOLDCO"])]
    return {
        "source_file": path.name,
        "symbols": subset.to_dict(orient="records"),
    }


def write_json(filename: str, value: dict) -> str:
    path = OUT / filename
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sha256(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    docs, instruments = document_rows()
    access_old, access_new = observed_symbol("ACCESS"), observed_symbol("ACCESSCORP")
    gtb_old, gtb_new = observed_symbol("GUARANTY"), observed_symbol("GTCO")
    fbn_old, fbn_new = observed_symbol("FBNH"), observed_symbol("FIRSTHOLDCO")

    common = {
        "review_kind": "historical_identity_continuity_review",
        "evidence_policy_version": "historical_identity_source_policy_v1",
        "canonical_mutation": False,
        "recorded_at_policy": "No historical validity or canonical record timestamp is backdated; this review is a frozen artifact, not an IdentifierAlias assertion.",
        "observation_bound_policy": "first/last source observation dates are not listing, delisting, alias valid_from, or alias valid_to dates.",
        "h024_outcome_access": "none",
    }
    reviews = {
        "ACCESS_ACCESSCORP_review.json": {
            **common,
            "case": "ACCESS -> ACCESSCORP",
            "predecessor_source_series": access_old,
            "successor_source_series": access_new,
            "predecessor_canonical_instrument_id": instruments["ACCESS"],
            "successor_canonical_instrument_id": instruments["ACCESSCORP"],
            "observed_handoff_bounds": {"last_old_symbol_observed": access_old["last_observed_in_available_source"], "first_new_symbol_observed": access_new["first_observed_in_available_source"]},
            "issuer_continuity": "different",
            "security_continuity": "replacement_security",
            "ticker_continuity": "replacement_successor_symbol",
            "event_type": "holding_company_reorganization_scheme_of_arrangement",
            "effective_date": {"value": None, "precision": "unknown", "basis": "the retained scheme defines effectiveness but this review does not infer the effective date from observed handoff dates"},
            "evidence_support": "strong",
            "supporting_evidence": [
                {**docs["access_scheme"], "authority_tier": "tier_2", "source_authority": "issuer scheme document", "locator": "pp. 1, 4-5", "supported_claim": "Access Holdings Plc was a new non-operating holding company intended to become the listed parent/entity owner; the existing Access Bank shares were scheme shares."},
                {**docs["access_court"], "authority_tier": "tier_2", "source_authority": "issuer court-sanction notice", "locator": "document-level (scanned original; no reliable text locator)", "supported_claim": "court sanction notice retained for the scheme; locator completeness is limited by scan extraction."},
            ],
            "market_series_ownership": {"predecessor": "supported_as_traded_series_for_predecessor_instrument", "successor": "supported_as_traded_series_for_successor_instrument", "ticker_validity": "separate_future_assertion_required", "instrument_continuity": "replacement_security"},
            "recommended_canonical_treatment": "retain_two_instruments",
            "confidence": {"authority": "tier_2_primary", "continuity": "strong", "locator_completeness": "partial"},
            "missing_evidence": ["exact exchange effective transition date if a future temporal alias/event assertion is proposed", "canonical EvidenceItem creation is intentionally deferred"],
        },
        "GUARANTY_GTCO_review.json": {
            **common,
            "case": "GUARANTY -> GTCO",
            "predecessor_source_series": gtb_old,
            "successor_source_series": gtb_new,
            "predecessor_canonical_instrument_id": instruments["GUARANTY"],
            "successor_canonical_instrument_id": instruments["GTCO"],
            "observed_handoff_bounds": {"last_old_symbol_observed": gtb_old["last_observed_in_available_source"], "first_new_symbol_observed": gtb_new["first_observed_in_available_source"]},
            "issuer_continuity": "different",
            "security_continuity": "replacement_security",
            "ticker_continuity": "replacement_successor_symbol",
            "event_type": "holding_company_reorganization_scheme_of_arrangement",
            "effective_date": {"value": "2021-06-24", "precision": "date", "basis": "official NGX bulletin reports GTB delisting and GT HoldCo listing on this date"},
            "evidence_support": "strong",
            "supporting_evidence": [EXTERNAL_PRIMARY_SOURCES["ngx_gtb_delisting_gtco_listing"]],
            "market_series_ownership": {"predecessor": "supported_as_traded_series_for_predecessor_instrument", "successor": "supported_as_traded_series_for_successor_instrument", "ticker_validity": "future_assertion_requires_locally_retained_or_canonical_evidence_item", "instrument_continuity": "replacement_security"},
            "recommended_canonical_treatment": "retain_two_instruments",
            "confidence": {"authority": "tier_1_primary", "continuity": "strong", "locator_completeness": "partial_external_artifact_not_retained"},
            "missing_evidence": ["locally retained original of the cited NGX bulletin before canonical assertion ingestion", "canonical EvidenceItem creation is intentionally deferred"],
        },
        "FBNH_FIRSTHOLDCO_review.json": {
            **common,
            "case": "FBNH -> FIRSTHOLDCO",
            "predecessor_source_series": fbn_old,
            "successor_source_series": fbn_new,
            "predecessor_canonical_instrument_id": instruments["FBNH"],
            "successor_canonical_instrument_id": instruments["FIRSTHOLDCO"],
            "observed_handoff_bounds": {"last_old_symbol_observed": fbn_old["last_observed_in_available_source"], "first_new_symbol_observed": fbn_new["first_observed_in_available_source"]},
            "issuer_continuity": "same",
            "security_continuity": "same_security",
            "ticker_continuity": "simple_alias_change",
            "event_type": "company_name_and_ticker_change",
            "effective_date": {"value": "2025-03-05", "precision": "date", "basis": "official NGX market bulletin reports implementation and the symbol change"},
            "evidence_support": "strong",
            "supporting_evidence": [
                {**docs["fbn_change"], "authority_tier": "tier_2", "source_authority": "issuer notification", "locator": "pp. 1-2", "supported_claim": "FBN Holdings announced its change of name to First HoldCo; the retained document identifies First HoldCo as formerly FBN Holdings."},
                {**docs["fbn_agm"], "authority_tier": "tier_2", "source_authority": "issuer AGM resolution", "locator": "resolution 9a", "supported_claim": "shareholders approved change of legal and brand names from FBN Holdings/FBNHoldings to First Holdco/FirstHoldco."},
                EXTERNAL_PRIMARY_SOURCES["ngx_fbn_name_and_symbol_change"],
            ],
            "market_series_ownership": {"predecessor": "supported_as_traded_series_for_same_continuing_security_pending_canonical_review", "successor": "supported_as_traded_series_for_same_continuing_security_pending_canonical_review", "ticker_validity": "review_qualified_but_no_alias_assertion_created", "instrument_continuity": "same_security"},
            "recommended_canonical_treatment": "future_forward_reconciliation_candidate",
            "confidence": {"authority": "tier_1_plus_tier_2", "continuity": "strong", "locator_completeness": "partial_external_artifact_not_retained"},
            "missing_evidence": ["locally retained original of the cited NGX bulletin before canonical assertion ingestion", "referential-impact analysis before any forward reconciliation"],
        },
        "FIRSTHOLDCO_case_normalization_review.json": {
            **common,
            "review_kind": "source_series_normalization_review",
            "case": "FirstHoldCo <-> FIRSTHOLDCO",
            "raw_source_observations": [source_file_symbol(date) for date in ("2025-03-04", "2025-03-06", "2025-03-07", "2025-03-10")],
            "parser_behavior": "the official-price-list parser preserves the published symbol string; it does not case-normalize this field",
            "source_normalization_equivalent": True,
            "evidence_support": "moderate",
            "supported_claim": "available official source parses show FirstHoldCo on 2025-03-06/07 and FIRSTHOLDCO on 2025-03-10; this review treats casing/presentation as a source normalization equivalence only.",
            "historical_alias_assertion_created": False,
            "recommended_canonical_treatment": "source_normalization_only",
            "missing_evidence": ["a canonical IdentifierAlias assertion, which is intentionally out of scope", "a claim that case presentation by itself proves any historical legal interval"],
        },
    }
    hashes = {filename: write_json(filename, review) for filename, review in reviews.items()}
    priority = json.loads(PRIORITY.read_text(encoding="utf-8"))["h024_identity_evidence_priority"]["priority_1"]
    potential = sum(row["candidate_instrument_formations"] for row in priority if row["legacy_ticker"] == "FIRSTHOLDCO")
    manifest = {
        "batch": "historical_identity_phase3_batch1",
        "review_status": "complete_review_no_canonical_mutation",
        "canonical_mutation": False,
        "live_identity_mutation": "none",
        "h024_outcome_access": "none",
        "evidence_policy_version": "historical_identity_source_policy_v1",
        "source_policy_sha256": sha256(POLICY),
        "source_baseline_commit": SOURCE_BASELINE_COMMIT,
        "review_artifact_hashes": hashes,
        "retained_source_artifact_hashes": {key: docs[key]["content_sha256"] for key in docs},
        "external_primary_sources_not_locally_retained": EXTERNAL_PRIMARY_SOURCES,
        "h024_potential_impact": {
            "method": "existing Phase 1 priority counts only; no H-024 dataset/outcome access",
            "canonical_mappings_applied": 0,
            "potential_formations_if_future_assertions_approved": potential,
            "still_blocked_without_future_assertion": 13620,
            "outcome_access": "none",
        },
    }
    write_json("batch_manifest.json", manifest)
    print(json.dumps({"output": str(OUT), "canonical_mutation": False, "h024_outcome_access": "none"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
