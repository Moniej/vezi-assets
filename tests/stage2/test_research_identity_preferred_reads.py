"""Stage 2D canonical-preferred metadata inspection contract."""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import TemporalQueryContext, TemporalValue
from ngxrot.identity.migration import apply_identity_foundation
from ngxrot.research_identity_reads import IdentityReadMode, inspect_metadata_identity
from ngxrot.research_identity_references import (
    CanonicalIdentityRequest, apply_registry_identity_reference_migration,
)
from ngxrot.research_query import QuerySpec, execute
from ngxrot.research_query import lookup_identity

ROOT = Path(__file__).resolve().parents[2]
NGX = ROOT / "fixtures" / "stage1" / "frozen" / "ngx_regression.sqlite"
REGISTRY = ROOT / "fixtures" / "stage1" / "frozen" / "registry_regression.sqlite"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchIdentityPreferredReadTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime = ROOT / ".test-runtime"; runtime.mkdir(exist_ok=True)
        self.ngx_path, self.registry_path = runtime / "stage2d-ngx.sqlite", runtime / "stage2d-registry.sqlite"
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

    def _persist_gtco(self) -> str:
        return execute(self.os, QuerySpec(query_type="metadata", entities=["GTCO"]), reg=self.reg,
                       canonical_identity=CanonicalIdentityRequest("GTCO", exchange="NGX")).query_id

    def test_persisted_canonical_reference_is_preferred_without_reresolution(self) -> None:
        query_id = self._persist_gtco()
        expected = self.reg.execute("SELECT canonical_instrument_id FROM query_log WHERE query_id=?", (query_id,)).fetchone()[0]
        result = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX",
                                           identity_mode="canonical_preferred", registry_connection=self.reg, query_id=query_id)
        self.assertEqual(result.identity.effective_identity_kind, "canonical")
        self.assertEqual(result.identity.canonical_instrument_id, expected)
        self.assertTrue(result.identity.persisted_reference_present)
        self.assertFalse(result.identity.fresh_resolver_used)
        self.assertIsNone(result.identity.canonical_company_id)

    def test_missing_persisted_target_is_observable_and_not_replaced(self) -> None:
        query_id = self._persist_gtco()
        instrument = self.reg.execute("SELECT canonical_instrument_id FROM query_log WHERE query_id=?", (query_id,)).fetchone()[0]
        self.os.execute("DELETE FROM instrument_listings WHERE instrument_id=?", (instrument,)); self.os.commit()
        result = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX",
                                           identity_mode=IdentityReadMode.CANONICAL_PREFERRED,
                                           registry_connection=self.reg, query_id=query_id)
        self.assertEqual(result.identity.effective_identity_kind, "legacy")
        self.assertEqual(result.identity.canonical_instrument_id, instrument)
        self.assertEqual(result.identity.canonical_reference_status, "missing_target")
        self.assertTrue(result.identity.mismatch_detected)
        self.assertFalse(result.identity.fresh_resolver_used)

    def test_persisted_reference_is_not_replaced_when_current_resolver_changes(self) -> None:
        query_id = self._persist_gtco()
        original = self.reg.execute("SELECT canonical_instrument_id FROM query_log WHERE query_id=?", (query_id,)).fetchone()[0]
        replacement = self.os.execute("SELECT instrument_id FROM instrument_listings WHERE instrument_id<>? ORDER BY instrument_id LIMIT 1", (original,)).fetchone()[0]
        self.os.execute("DELETE FROM identifier_aliases WHERE subject_id=? AND identifier_type='ticker' AND identifier_value='GTCO'", (original,))
        self.os.execute("INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
                        ("01800000-0000-7000-8000-000000000401", "instrument", replacement, "ticker", "GTCO", "NGX", "verified", "2026-08-30T00:00:00+00:00")); self.os.commit()
        self.assertEqual(lookup_identity(self.os, "GTCO", exchange="NGX").instrument_id, replacement)
        result = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX", identity_mode="canonical_preferred",
                                           registry_connection=self.reg, query_id=query_id)
        self.assertEqual(result.identity.canonical_instrument_id, original)
        self.assertFalse(result.identity.fresh_resolver_used)

    def test_fresh_canonical_preferred_and_legacy_modes_are_explicit(self) -> None:
        canonical = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX", identity_mode="canonical_preferred")
        legacy = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX", identity_mode="legacy")
        self.assertEqual(canonical.identity.effective_identity_kind, "canonical")
        self.assertIsNotNone(canonical.identity.canonical_instrument_id)
        self.assertEqual(legacy.identity.effective_identity_kind, "legacy")
        self.assertIsNone(legacy.identity.canonical_instrument_id)
        self.assertEqual(canonical.metadata, legacy.metadata)

    def test_historical_fallback_is_labeled_non_pit_safe_and_canonical_required_refuses_it(self) -> None:
        historical = TemporalQueryContext(TemporalValue(datetime(2010, 1, 1, tzinfo=timezone.utc)),
                                           TemporalValue(datetime(2026, 8, 30, tzinfo=timezone.utc)))
        fallback = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX",
                                             identity_mode="canonical_preferred", temporal_context=historical)
        required = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX",
                                             identity_mode="canonical", temporal_context=historical)
        self.assertEqual((fallback.identity.effective_identity_kind, fallback.identity.canonical_resolution_status),
                         ("legacy", "temporally_unavailable"))
        self.assertTrue(fallback.identity.fallback_used); self.assertFalse(fallback.identity.pit_safe)
        self.assertEqual(required.identity.effective_identity_kind, "none")
        self.assertFalse(required.identity.fallback_used)

    def test_canonical_mode_refuses_a_persisted_legacy_fallback(self) -> None:
        historical = TemporalQueryContext(TemporalValue(datetime(2010, 1, 1, tzinfo=timezone.utc)),
                                           TemporalValue(datetime(2026, 8, 30, tzinfo=timezone.utc)))
        query_id = execute(self.os, QuerySpec(query_type="metadata", entities=["GTCO"]), reg=self.reg,
                           canonical_identity=CanonicalIdentityRequest("GTCO", exchange="NGX", temporal_context=historical)).query_id
        result = inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX", identity_mode="canonical",
                                           registry_connection=self.reg, query_id=query_id)
        self.assertEqual((result.identity.effective_identity_kind, result.identity.canonical_resolution_status),
                         ("none", "legacy_fallback"))

    def test_unknown_and_ambiguous_are_never_arbitrarily_canonical(self) -> None:
        unknown = inspect_metadata_identity(self.os, identifier="NOPE", exchange="NGX",
                                            identity_mode="canonical_preferred", allow_legacy_fallback=False)
        one, two = [r[0] for r in self.os.execute("SELECT instrument_id FROM instrument_listings ORDER BY instrument_id LIMIT 2")]
        self.os.executemany(
            "INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?)",
            [("01800000-0000-7000-8000-000000000301", "instrument", one, "ticker", "DUP", "NGX", "verified", "2026-08-30T00:00:00+00:00"),
             ("01800000-0000-7000-8000-000000000302", "instrument", two, "ticker", "DUP", "NGX", "verified", "2026-08-30T00:00:00+00:00")],
        ); self.os.commit()
        ambiguous = inspect_metadata_identity(self.os, identifier="DUP", exchange="NGX", identity_mode="canonical_preferred")
        self.assertEqual((unknown.identity.effective_identity_kind, unknown.identity.canonical_resolution_status), ("none", "unknown"))
        self.assertEqual((ambiguous.identity.effective_identity_kind, ambiguous.identity.canonical_resolution_status), ("none", "ambiguous"))
        self.assertIsNone(ambiguous.identity.canonical_instrument_id)

    def test_reads_do_not_mutate_either_database(self) -> None:
        query_id = self._persist_gtco()
        before = digest(self.ngx_path), digest(self.registry_path)
        inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX", identity_mode="canonical_preferred",
                                  registry_connection=self.reg, query_id=query_id)
        inspect_metadata_identity(self.os, identifier="GTCO", exchange="NGX", identity_mode="legacy")
        self.assertEqual(before, (digest(self.ngx_path), digest(self.registry_path)))


if __name__ == "__main__":
    unittest.main()
