"""Stage 2C: opt-in, immutable Research OS canonical identity references."""
from __future__ import annotations

import shutil
import sqlite3
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import TemporalQueryContext, TemporalValue
from ngxrot.identity.migration import apply_identity_foundation
from ngxrot.research_identity_references import (
    CanonicalIdentityRequest, CanonicalReferenceValidationStatus,
    apply_registry_identity_reference_migration,
    reconcile_canonical_instrument_references,
    validate_canonical_instrument_reference,
)
from ngxrot.research_query import QuerySpec, execute

ROOT = Path(__file__).resolve().parents[2]
NGX = ROOT / "fixtures" / "stage1" / "frozen" / "ngx_regression.sqlite"
REGISTRY = ROOT / "fixtures" / "stage1" / "frozen" / "registry_regression.sqlite"


class ResearchIdentityPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime = ROOT / ".test-runtime"; runtime.mkdir(exist_ok=True)
        self.ngx_path, self.registry_path = runtime / "stage2c-ngx.sqlite", runtime / "stage2c-registry.sqlite"
        for path, source in ((self.ngx_path, NGX), (self.registry_path, REGISTRY)):
            if path.exists(): path.chmod(0o666); path.unlink()
            shutil.copy(source, path); path.chmod(0o666)
        self.os, self.reg = sqlite3.connect(self.ngx_path), sqlite3.connect(self.registry_path)
        apply_identity_foundation(self.os, backup_manifest_sha256="fixture")
        apply_registry_identity_reference_migration(self.reg, backup_manifest_sha256="fixture")

    def tearDown(self) -> None:
        self.os.close(); self.reg.close()
        for path in (self.ngx_path, self.registry_path):
            if path.exists(): path.unlink()

    def _metadata(self, request: CanonicalIdentityRequest | None = None) -> str:
        return execute(self.os, QuerySpec(query_type="metadata", entities=["GTCO"]), reg=self.reg,
                       canonical_identity=request).query_id

    def _row(self, query_id: str):
        return self.reg.execute(
            "SELECT canonical_instrument_id, canonical_resolution_status, canonical_reference_status, "
            "canonical_exchange, canonical_resolution_decision_time, canonical_resolution_system_vintage, "
            "canonical_availability_policy FROM query_log WHERE query_id=?", (query_id,)
        ).fetchone()

    def test_resolved_identity_is_inserted_with_immutable_context(self) -> None:
        row = self._row(self._metadata(CanonicalIdentityRequest("GTCO", exchange="NGX")))
        self.assertIsNotNone(row[0]); self.assertEqual(row[1:4], ("resolved", "validated", "NGX"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.reg.execute("UPDATE query_log SET canonical_instrument_id='x' WHERE canonical_instrument_id=?", (row[0],))

    def test_default_legacy_creation_remains_not_requested(self) -> None:
        self.assertEqual(self._row(self._metadata())[0:3], (None, "not_requested", "not_applicable"))

    def test_unavailable_or_fallback_never_persists_a_canonical_id(self) -> None:
        historical = TemporalQueryContext(TemporalValue(datetime(2010, 1, 1, tzinfo=timezone.utc)),
                                           TemporalValue(datetime(2026, 8, 30, tzinfo=timezone.utc)))
        fallback = self._row(self._metadata(CanonicalIdentityRequest("GTCO", exchange="NGX", temporal_context=historical)))
        self.assertEqual(fallback[0:3], (None, "legacy_fallback", "unresolved"))
        self.assertEqual(fallback[4], "2010-01-01T00:00:00+00:00")
        self.assertEqual(fallback[5], "2026-08-30T00:00:00+00:00")
        self.assertEqual(fallback[6], "strict_system_vintage")
        unknown = self._row(self._metadata(CanonicalIdentityRequest("NOPE", exchange="NGX", allow_legacy_fallback=False)))
        self.assertEqual(unknown[0:3], (None, "unknown", "unresolved"))

    def test_ambiguous_alias_never_persists_an_arbitrary_instrument(self) -> None:
        one, two = [row[0] for row in self.os.execute("SELECT instrument_id FROM instrument_listings ORDER BY instrument_id LIMIT 2")]
        self.os.executemany(
            "INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
            [("01800000-0000-7000-8000-000000000201", "instrument", one, "ticker", "DUP", "NGX", "verified", "2026-08-30T00:00:00+00:00"),
             ("01800000-0000-7000-8000-000000000202", "instrument", two, "ticker", "DUP", "NGX", "verified", "2026-08-30T00:00:00+00:00")],
        ); self.os.commit()
        row = self._row(self._metadata(CanonicalIdentityRequest("DUP", exchange="NGX")))
        self.assertEqual(row[0:3], (None, "ambiguous", "unresolved"))

    def test_cross_database_validation_and_read_only_reconciliation(self) -> None:
        instrument_id = self._row(self._metadata(CanonicalIdentityRequest("GTCO", exchange="NGX")))[0]
        self.assertEqual(validate_canonical_instrument_reference(self.os, instrument_id, exchange="NGX").status,
                         CanonicalReferenceValidationStatus.VALID)
        summary = reconcile_canonical_instrument_references(self.reg, self.os)
        self.assertEqual((summary.total, summary.valid, summary.missing_target, summary.invalid), (1, 1, 0, 0))
        empty = sqlite3.connect(":memory:"); empty.execute("CREATE TABLE instrument_listings(instrument_id TEXT PRIMARY KEY, exchange_code TEXT)")
        self.assertEqual(reconcile_canonical_instrument_references(self.reg, empty).missing_target, 1); empty.close()

    def test_os_unavailable_is_not_missing_target(self) -> None:
        closed = sqlite3.connect(":memory:"); closed.close()
        result = validate_canonical_instrument_reference(closed, "01800000-0000-7000-8000-000000000001")
        self.assertEqual(result.status, CanonicalReferenceValidationStatus.OS_UNAVAILABLE)

    def test_no_cross_database_foreign_key_or_historical_backfill(self) -> None:
        self.assertFalse(any(row[2] == "instrument_listings" for row in self.reg.execute("PRAGMA foreign_key_list(query_log)")))
        self.assertEqual(self.reg.execute("SELECT COUNT(*) FROM query_log WHERE canonical_instrument_id IS NOT NULL").fetchone()[0], 0)
        apply_registry_identity_reference_migration(self.reg, backup_manifest_sha256="fixture")
        self.assertEqual(self.reg.execute("SELECT COUNT(*) FROM schema_migration_ledger WHERE migration_id LIKE '%research_canonical_identity_reference'").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
