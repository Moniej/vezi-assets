"""Stage 2B is a read-only, opt-in Research OS identity inspection path."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import TemporalQueryContext, TemporalValue
from ngxrot.identity.migration import apply_identity_foundation
from ngxrot.research_query import lookup_identity, resolve_entity, ResearchIdentityStatus


ROOT = Path(__file__).resolve().parents[2]
NGX = ROOT / "fixtures" / "stage1" / "frozen" / "ngx_regression.sqlite"
REGISTRY = ROOT / "fixtures" / "stage1" / "frozen" / "registry_regression.sqlite"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchIdentityLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        root = ROOT / ".test-runtime"
        root.mkdir(exist_ok=True)
        self.ngx = root / "research-identity.sqlite"
        if self.ngx.exists():
            self.ngx.chmod(0o666); self.ngx.unlink()
        shutil.copy(NGX, self.ngx); self.ngx.chmod(0o666)
        self.con = sqlite3.connect(self.ngx)
        apply_identity_foundation(self.con, backup_manifest_sha256="fixture")

    def tearDown(self) -> None:
        self.con.close()
        if self.ngx.exists(): self.ngx.unlink()

    def test_current_gtco_is_canonically_resolved_with_unresolved_issuer(self) -> None:
        result = lookup_identity(self.con, "GTCO", exchange="NGX")
        self.assertEqual(result.status, ResearchIdentityStatus.RESOLVED)
        self.assertIsNotNone(result.instrument_id)
        self.assertIsNone(result.company_id)
        self.assertEqual(result.issuer_status, "unresolved")
        self.assertFalse(result.fallback_used)

    def test_unknown_without_fallback_remains_unknown(self) -> None:
        result = lookup_identity(self.con, "NOPE", exchange="NGX", allow_legacy_fallback=False)
        self.assertEqual(result.status, ResearchIdentityStatus.UNKNOWN)
        self.assertFalse(result.fallback_used)

    def test_historical_failure_can_expose_non_pit_safe_legacy_fallback(self) -> None:
        context = TemporalQueryContext(TemporalValue(datetime(2010, 1, 1, tzinfo=timezone.utc)), TemporalValue(datetime(2026, 8, 30, tzinfo=timezone.utc)))
        result = lookup_identity(self.con, "GTCO", exchange="NGX", temporal_context=context, allow_legacy_fallback=True)
        self.assertEqual(result.status, ResearchIdentityStatus.LEGACY_FALLBACK)
        self.assertEqual(result.canonical_status, "temporally_unavailable")
        self.assertTrue(result.fallback_used)
        self.assertFalse(result.pit_safe_canonical_resolution)
        self.assertEqual(result.legacy_ticker, "GTCO")

    def test_ambiguous_canonical_alias_is_never_silently_fallback_resolved(self) -> None:
        one, two = [row[0] for row in self.con.execute("SELECT instrument_id FROM instrument_listings ORDER BY instrument_id LIMIT 2")]
        self.con.executemany("INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?)", [("01800000-0000-7000-8000-000000000101", "instrument", one, "ticker", "DUP", "NGX", "verified", "2026-08-30T00:00:00+00:00"), ("01800000-0000-7000-8000-000000000102", "instrument", two, "ticker", "DUP", "NGX", "verified", "2026-08-30T00:00:00+00:00")])
        self.con.commit()
        result = lookup_identity(self.con, "DUP", exchange="NGX", allow_legacy_fallback=True)
        self.assertEqual(result.status, ResearchIdentityStatus.AMBIGUOUS)
        self.assertFalse(result.fallback_used)
        self.assertIsNone(result.instrument_id)

    def test_lookups_do_not_mutate_os_or_registry_and_legacy_query_is_unchanged(self) -> None:
        before_ngx = digest(self.ngx)
        before_registry = digest(REGISTRY)
        legacy_before = resolve_entity(self.con, "GTCO").__dict__.copy()
        lookup_identity(self.con, "GTCO", exchange="NGX")
        lookup_identity(self.con, "NOPE", exchange="NGX")
        legacy_after = resolve_entity(self.con, "GTCO").__dict__.copy()
        self.assertEqual(legacy_before, legacy_after)
        self.assertEqual(before_ngx, digest(self.ngx))
        self.assertEqual(before_registry, digest(REGISTRY))


if __name__ == "__main__":
    unittest.main()
