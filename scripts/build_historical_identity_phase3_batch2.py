"""Freeze Phase 3 Batch 2 reviews without live identity or H-024 outcome access."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ngxrot.identity.evidence_retention import RetentionStatus


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "ngx.sqlite"
OUT = ROOT / "fixtures" / "frozen" / "historical_identity_phase3_batch2"
SERIES = ROOT / "fixtures" / "frozen" / "historical_market_series.json"
PRIORITY = ROOT / "fixtures" / "frozen" / "historical_identity_phase1_coverage_report.json"
POLICY = ROOT / "configs" / "historical_identity_source_policy.toml"
SOURCE_BASELINE = "1d48f95290ccb51073980a9eb4ef166e58a429de"
RETRIEVAL_ATTEMPTED_AT = "2026-08-31T17:15:23+00:00"

TIER1 = {
    "FO_ARDOVA": {
        "source_url": "https://doclib.ngxgroup.com/Listings-site/corporate-disclosure-site/Documents/Market%20Bulletin%20-%20Forte%20Oil%20Change%20of%20Name.pdf",
        "publication_date": "2020-02-24", "locator": "NSE/RD/LRD/MB15/20/02/24",
        "claim": "NSE implemented the company name and trading-symbol change from FO to ARDOVA on 2020-02-24.",
    },
    "FBNH_FIRSTHOLDCO": {
        "source_url": "https://doclib.ngxgroup.com/Listings-site/corporate-disclosure-site/Documents/Market%20Bulletin%20on%20the%20Change%20of%20Name%20of%20FBN%20Holdings%20Plc.pdf",
        "publication_date": "2025-03-05", "locator": "NGXREG/IRD/MB15/25/03/5",
        "claim": "NGX implemented the FBN Holdings name change and changed the trading symbol from FBNH to FirstHoldCo.",
    },
    "ACCESS_ACCESSCORP": {
        "source_url": "https://doclib.ngxgroup.com/market_data-site/other-market-information-site/Week%20Market%20Report/Weekly%20Market%20Report%20for%20the%20Week%20Ended%2001-04-2022.pdf",
        "publication_date": "2022-04-01", "locator": "New Listing / Delisting of Access Bank Plc and listing of Access Holdings Plc",
        "claim": "NGX reported the Access Bank delisting and Access HoldCo listing on 2022-03-28 under a court-sanctioned scheme.",
    },
    "GUARANTY_GTCO": {
        "source_url": "https://doclib.ngxgroup.com/market_data-site/other-market-information-site/Week%20Market%20Report/Weekly%20Market%20Report%20for%20the%20Week%20Ended%2025-06-2021.pdf",
        "publication_date": "2021-06-25", "locator": "Other News / Delisting of Guaranty Trust Bank Plc and Listing of Guaranty Trust Holding Company Plc",
        "claim": "NGX reported GTB delisting and GT HoldCo listing on 2021-06-24 under a court-sanctioned scheme.",
    },
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def write(name: str, payload: dict) -> str:
    target = OUT / name
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digest(target)


def instrument_id(ticker: str) -> str | None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("""SELECT subject_id FROM identifier_aliases
                        WHERE subject_type='instrument' AND identifier_type='ticker'
                          AND exchange_code='NGX' AND identifier_value=?""", (ticker,)).fetchall()
    con.close()
    return rows[0][0] if len(rows) == 1 else None


def source_series(symbol: str) -> dict:
    rows = json.loads(SERIES.read_text(encoding="utf-8"))
    row = next(item for item in rows if item["published_symbol"] == symbol)
    return {key: row[key] for key in (
        "source_series_id", "published_symbol", "first_observed_in_available_source",
        "last_observed_in_available_source", "source_file_first", "source_file_last",
        "observation_count", "published_names",
    )}


def failed_tier1(name: str) -> dict:
    source = TIER1[name]
    return {
        "source_name": name, "source_authority_tier": "tier_1", "source_authority": "Nigerian Exchange",
        **source, "source_discovered": True, "source_accessible_in_browser": True,
        "source_download_blocked_in_environment": True, "retrieval_attempted_at": RETRIEVAL_ATTEMPTED_AT,
        "retrieval_status": RetentionStatus.RETRIEVAL_FAILED.value,
        "retrieval_error_class": "ProxyError", "archive_status": "not_archived",
        "content_sha256": None, "parsed_status": "not_parsed", "evidence_locator_status": "not_created",
        "evidence_grade_eligible": False,
    }


def retained_local(name: str, relative_path: str, *, source_url: str, tier: str,
                   parsed: bool, locator: str) -> dict:
    path = ROOT / relative_path
    return {
        "source_name": name, "source_authority_tier": tier, "source_url": source_url,
        "source_discovered": True, "source_retrieved": True, "retrieval_status": (
            RetentionStatus.ARCHIVED_PARSED.value if parsed else RetentionStatus.ARCHIVED_UNPARSED.value),
        "archive_status": "archived_original_source", "artifact_path": relative_path.replace("\\", "/"),
        "content_sha256": digest(path), "byte_size": path.stat().st_size,
        "parsed_status": "native_text_available" if parsed else "not_parsed_or_scanned",
        "evidence_locator_status": locator, "evidence_grade_eligible": False,
        "reason_not_evidence_grade": "No canonical DocumentVersion, EvidenceLocator, EvidenceItem, or Citation is persisted in this review-only batch.",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fo, ardova = source_series("FO"), source_series("ARDOVA")
    fo_review = {
        "review_kind": "historical_identity_continuity_review", "case": "FO -> ARDOVA",
        "canonical_mutation": False, "h024_outcome_access": "none",
        "predecessor_source_series": fo, "successor_source_series": ardova,
        "predecessor_canonical_instrument_id": instrument_id("FO"),
        "successor_canonical_instrument_id": instrument_id("ARDOVA"),
        "observed_handoff_bounds": {"last_FO_observed": fo["last_observed_in_available_source"], "first_ARDOVA_observed": ardova["first_observed_in_available_source"]},
        "observed_bound_policy": "These are observations in available official source artifacts, not alias validity or legal transition dates.",
        "issuer_continuity": "same", "security_continuity": "same_security",
        "ticker_continuity": "simple_ticker_name_change", "event_classification": "company_name_and_ticker_change",
        "effective_date": {"value": "2020-02-24", "precision": "date", "basis": "official exchange bulletin"},
        "supporting_evidence": [failed_tier1("FO_ARDOVA")],
        "market_series_ownership": {
            "FO": {"series_ownership_confidence": "moderate", "ticker_validity_confidence": "tier1_discovered_but_not_retained", "instrument_continuity_confidence": "strong_but_not_canonical_evidence_grade"},
            "ARDOVA": {"series_ownership_confidence": "moderate", "ticker_validity_confidence": "tier1_discovered_but_not_retained", "instrument_continuity_confidence": "strong_but_not_canonical_evidence_grade"},
        },
        "recommended_canonical_treatment": "future_forward_reconciliation_candidate",
        "future_design_supported": "one InstrumentListing with FO historical alias and ARDOVA successor/current alias, only after the Tier 1 original is archived and a canonical evidence chain is persisted.",
        "evidence_support": "strong_for_review; not_evidence_grade_for_canonical_assertion", "canonical_assertion_authorized": False,
    }
    local_access = retained_local(
        "ACCESS_scheme_issuer_document", "data/archive/xissuer_docs/15197_34667_ACCESS_BANK_PLC_SCHEME_OF_ARRANGEMENT_BETWEEN_ACCESS_.pdf",
        source_url="https://doclib.ngxgroup.com/Financial_NewsDocs/34667_ACCESS_BANK_PLC%20SCHEME_OF_ARRANGEMENT_BETWEEN_ACCESS_.pdf",
        tier="tier_2", parsed=True, locator="review_locator_only: pp. 1, 4-5",
    )
    local_fbn = retained_local(
        "FBNH_issuer_change_notice", "data/archive/xissuer_docs/25784_43129_FBN_HOLDINGS_PLC-FIRST_HOLDCO_PLC_-_CHANGE_OF_NAME_NOTIFICATION_CORPORATE_ACTIONS_FEBRUARY_2025.pdf",
        source_url="https://doclib.ngxgroup.com/Financial_NewsDocs/43129_FBN_HOLDINGS_PLC-FIRST_HOLDCO_PLC_-_CHANGE_OF_NAME_NOTIFICATION_CORPORATE_ACTIONS_FEBRUARY_2025.pdf",
        tier="tier_2", parsed=True, locator="review_locator_only: pp. 1-2",
    )
    retention = {
        "review_kind": "evidence_retention_readiness", "canonical_mutation": False,
        "h024_outcome_access": "none", "url_citation_only_policy": "not_evidence_grade",
        "canonical_ingestion_policy": "not_executed_in_batch2",
        "existing_supported_path": [
            "SourceEndpoint(canonical_uri, retention_policy)", "retrieve immutable bytes",
            "LocalImmutableArchive.put -> DocumentArtifact(sha256, storage_uri, byte_size)",
            "future additive persistence: DocumentVersion -> ParsedDocumentRepresentation -> EvidenceLocator -> EvidenceItem -> Citation",
        ],
        "persistence_gap": "The Stage 1 contracts and archive work today, but no approved persistent DocumentArtifact/DocumentVersion/EvidenceItem adapter exists; Batch 2 therefore cannot create canonical evidence records without a later additive migration.",
        "sources": [failed_tier1(name) for name in TIER1] + [local_access, local_fbn],
    }
    fbn_retention = {"case": "FBNH -> FIRSTHOLDCO", "canonical_mutation": False, "tier1": failed_tier1("FBNH_FIRSTHOLDCO"), "tier2": local_fbn, "retention_gap_closed": False, "conclusion": "Issuer-primary material is archived and review-parsed, but the Tier 1 NGX bulletin remains unarchived and no canonical evidence chain exists."}
    access_retention = {"case": "ACCESS -> ACCESSCORP", "canonical_mutation": False, "tier1": failed_tier1("ACCESS_ACCESSCORP"), "tier2": local_access, "retention_gap_closed": False, "conclusion": "The local issuer scheme is archived and review-parsed; the official NGX bulletin remains URL-only and no canonical evidence chain exists."}
    gtco_retention = {"case": "GUARANTY -> GTCO", "canonical_mutation": False, "tier1": failed_tier1("GUARANTY_GTCO"), "retention_gap_closed": False, "conclusion": "The decisive official NGX bulletin remains URL-only; this case is not locally evidence-grade."}
    hashes = {
        "FO_ARDOVA_review.json": write("FO_ARDOVA_review.json", fo_review),
        "evidence_retention_status.json": write("evidence_retention_status.json", retention),
        "FBNH_FIRSTHOLDCO_retention_review.json": write("FBNH_FIRSTHOLDCO_retention_review.json", fbn_retention),
        "ACCESS_ACCESSCORP_retention_review.json": write("ACCESS_ACCESSCORP_retention_review.json", access_retention),
        "GUARANTY_GTCO_retention_review.json": write("GUARANTY_GTCO_retention_review.json", gtco_retention),
    }
    candidates = json.loads(PRIORITY.read_text(encoding="utf-8"))["h024_identity_evidence_priority"]["priority_1"]
    by_ticker = {row["legacy_ticker"]: row["candidate_instrument_formations"] for row in candidates}
    manifest = {
        "batch": "historical_identity_phase3_batch2", "source_baseline_commit": SOURCE_BASELINE,
        "evidence_policy_version": "historical_identity_source_policy_v1", "source_policy_sha256": digest(POLICY),
        "canonical_mutation": False, "live_identity_mutation": "none", "h024_outcome_access": "none",
        "review_artifact_hashes": hashes,
        "h024_potential_impact": {"FO_candidate_formations": by_ticker.get("FO", 0), "ARDOVA_candidate_formations": by_ticker.get("ARDOVA", 0), "hypothetical_unlocked_if_future_assertion_approved": by_ticker.get("ARDOVA", 0), "remaining_blocked_without_future_assertion": 13620, "outcome_access": "none"},
        "batch3_scaleup_readiness": {"ready": True, "selection_basis": "candidate-formation count, observable-universe relevance, unresolved continuity, and source availability only", "recommended_cases": ["WAPCO->HBMNG", "UBCAP->UCAP", "OASISINS->LINKASSURE", "STERLNBANK->STERLINGNG", "CUSTODYINS->CUSTODIAN"], "excluded_false_candidate": "FLOURMILL->FGS202669 is excluded because the successor is a debt series, not a plausible ordinary-equity continuity case."},
    }
    write("batch_manifest.json", manifest)
    print(json.dumps({"output": str(OUT), "canonical_mutation": False, "h024_outcome_access": "none"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
