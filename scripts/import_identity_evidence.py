"""Operator-only import into the canonical evidence bridge.

This command never creates an alias, continuity assertion, or identity mapping.
It requires the evidence-persistence migration to have already been applied.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot.canonical.contracts import SourceAuthorityTier, TemporalPrecision, TemporalValue
from ngxrot.canonical.evidence_store import CanonicalEvidenceStore, MIGRATION_ID


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_path", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--authority-tier", required=True, choices=[tier.value for tier in SourceAuthorityTier])
    parser.add_argument("--document-type", default="historical_identity_notice")
    parser.add_argument("--published-date", type=date.fromisoformat,
                        help="Document-supported publication date; stored with date precision.")
    parser.add_argument("--publication-time-verification",
                        help="How publication timing was evidenced, e.g. document_header_date.")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "ngx.sqlite")
    parser.add_argument("--archive-root", type=Path, default=ROOT / "data" / "archive" / "canonical_evidence")
    args = parser.parse_args()
    if not args.local_path.is_file():
        parser.error("local_path must be an operator-supplied file")
    con = sqlite3.connect(args.database)
    try:
        exists = con.execute("SELECT 1 FROM schema_migration_ledger WHERE migration_id=?", (MIGRATION_ID,)).fetchone()
        if not exists:
            raise RuntimeError(f"{MIGRATION_ID} is not applied to {args.database}; refusing import")
        now = TemporalValue(datetime.now(timezone.utc), TemporalPrecision.SECOND)
        result = CanonicalEvidenceStore(con, archive_root=args.archive_root).import_evidence_document(
            args.local_path, source_url=args.source_url, source_name=args.source_name,
            source_authority=SourceAuthorityTier(args.authority_tier), retrieved_at=now,
            document_type=args.document_type,
            published_at=(TemporalValue(args.published_date, TemporalPrecision.DATE) if args.published_date else None),
            publication_time_verification=args.publication_time_verification,
        )
        print(f"archived artifact_id={result.artifact_id} sha256={result.artifact.sha256}")
        print(f"document_version_id={result.document_version_id} acquisition_mode=manual_operator_import")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
