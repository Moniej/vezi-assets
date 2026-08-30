"""Stage 2A identity foundation is additive, temporal, and non-destructive."""

from __future__ import annotations

import shutil
import sqlite3
import unittest
import json
from datetime import datetime, timezone
from pathlib import Path

from ngxrot.canonical.contracts import AvailabilityPolicy, TemporalQueryContext, TemporalValue
from ngxrot.identity.migration import apply_identity_foundation
from ngxrot.identity.resolver import ResolutionStatus, resolve_instrument


ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "fixtures" / "stage1" / "frozen" / "ngx_regression.sqlite"


def timestamp(value: str) -> TemporalValue:
    return TemporalValue(datetime.fromisoformat(value).replace(tzinfo=timezone.utc))


class CanonicalIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work = ROOT / ".test-runtime" / "identity.sqlite"
        self.work.parent.mkdir(exist_ok=True)
        if self.work.exists():
            self.work.chmod(0o666)
            self.work.unlink()
        shutil.copy(FROZEN, self.work)
        self.work.chmod(0o666)
        self.con = sqlite3.connect(self.work)
        self.securities_before = list(self.con.execute("SELECT * FROM securities ORDER BY ticker"))
        apply_identity_foundation(self.con, backup_manifest_sha256="fixture")

    def tearDown(self) -> None:
        self.con.close()
        if self.work.exists():
            self.work.unlink()

    def test_backfill_creates_instruments_without_issuers_or_security_mutation(self) -> None:
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM instrument_listings").fetchone()[0], len(self.securities_before))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM company_issuers").fetchone()[0], 0)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM instrument_listings WHERE company_id IS NULL").fetchone()[0], len(self.securities_before))
        self.assertEqual(list(self.con.execute("SELECT * FROM securities ORDER BY ticker")), self.securities_before)

    def test_verified_exchange_qualified_ticker_resolves(self) -> None:
        result = resolve_instrument(self.con, identifier="GTCO", identifier_type="ticker", exchange="NGX")
        self.assertEqual(result.status, ResolutionStatus.RESOLVED)
        self.assertIsNotNone(result.instrument_id)
        self.assertIsNone(result.company_id)

    def test_unknown_and_ambiguous_aliases_do_not_pick_first(self) -> None:
        self.assertEqual(resolve_instrument(self.con, identifier="NOPE", identifier_type="ticker", exchange="NGX").status, ResolutionStatus.UNKNOWN)
        one, two = [row[0] for row in self.con.execute("SELECT instrument_id FROM instrument_listings ORDER BY instrument_id LIMIT 2")]
        now = "2026-08-30T00:00:00+00:00"
        self.con.executemany("INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?)", [("01800000-0000-7000-8000-000000000001", "instrument", one, "ticker", "DUP", "NGX", "verified", now), ("01800000-0000-7000-8000-000000000002", "instrument", two, "ticker", "DUP", "NGX", "verified", now)])
        self.con.commit()
        self.assertEqual(resolve_instrument(self.con, identifier="DUP", identifier_type="ticker", exchange="NGX").status, ResolutionStatus.AMBIGUOUS)

    def test_temporal_unknown_and_strict_vintage_are_explicit(self) -> None:
        historic = TemporalQueryContext(timestamp("2010-01-01T00:00:00"), timestamp("2026-08-30T00:00:00"))
        self.assertEqual(resolve_instrument(self.con, identifier="GTCO", identifier_type="ticker", exchange="NGX", temporal_context=historic).status, ResolutionStatus.TEMPORALLY_UNAVAILABLE)
        early = TemporalQueryContext(timestamp("2026-08-30T00:00:00"), timestamp("2026-08-29T00:00:00"), AvailabilityPolicy.STRICT_SYSTEM_VINTAGE)
        self.assertEqual(resolve_instrument(self.con, identifier="GTCO", identifier_type="ticker", exchange="NGX", temporal_context=early).status, ResolutionStatus.TEMPORALLY_UNAVAILABLE)

    def test_duplicate_application_is_idempotent_and_mapping_is_append_only(self) -> None:
        counts = tuple(self.con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("instrument_listings", "identifier_aliases", "legacy_identity_mappings"))
        apply_identity_foundation(self.con, backup_manifest_sha256="fixture")
        self.assertEqual(tuple(self.con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("instrument_listings", "identifier_aliases", "legacy_identity_mappings")), counts)
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("UPDATE legacy_identity_mappings SET mapping_status='retracted'")

    def test_company_may_have_zero_or_multiple_instruments_and_exchange_disambiguates(self) -> None:
        company = "01800000-0000-7000-8000-000000000010"
        one = "01800000-0000-7000-8000-000000000011"
        two = "01800000-0000-7000-8000-000000000012"
        self.con.execute("INSERT INTO company_issuers(company_id,legal_name,issuer_status,recorded_at) VALUES (?,?,?,?)", (company, "Evidence-backed Fixture Issuer", "unknown", "2026-08-30T00:00:00+00:00"))
        self.con.executemany("INSERT INTO instrument_listings(instrument_id,company_id,exchange_code,instrument_type,listing_status,recorded_at) VALUES (?,?,?,?,?,?)", [(one, company, "NGX", "equity", "unknown", "2026-08-30T00:00:00+00:00"), (two, company, "LSE", "equity", "unknown", "2026-08-30T00:00:00+00:00")])
        self.con.executemany("INSERT INTO identifier_aliases(alias_id,subject_type,subject_id,identifier_type,identifier_value,exchange_code,verification_status,recorded_at) VALUES (?,?,?,?,?,?,?,?)", [("01800000-0000-7000-8000-000000000013", "instrument", one, "ticker", "SAME", "NGX", "verified", "2026-08-30T00:00:00+00:00"), ("01800000-0000-7000-8000-000000000014", "instrument", two, "ticker", "SAME", "LSE", "verified", "2026-08-30T00:00:00+00:00")])
        self.con.commit()
        self.assertEqual(resolve_instrument(self.con, identifier="SAME", identifier_type="ticker", exchange="NGX").instrument_id, one)
        self.assertEqual(resolve_instrument(self.con, identifier="SAME", identifier_type="ticker", exchange="LSE").instrument_id, two)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM instrument_listings WHERE company_id=?", (company,)).fetchone()[0], 2)

    def test_minimal_and_adversarial_fixture_scenarios_accept_additive_schema(self) -> None:
        for fixture_name in ("minimal.json", "adversarial.json"):
            fixture = json.loads((ROOT / "fixtures" / "stage1" / fixture_name).read_text(encoding="utf-8"))
            self.assertTrue(fixture["synthetic_non_evidence"])
            con = sqlite3.connect(":memory:")
            try:
                con.executescript((ROOT / "schema" / "schema.sql").read_text(encoding="utf-8"))
                apply_identity_foundation(con, backup_manifest_sha256="synthetic-fixture")
                self.assertEqual(con.execute("SELECT COUNT(*) FROM company_issuers").fetchone()[0], 0)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM instrument_listings").fetchone()[0], 0)
            finally:
                con.close()


if __name__ == "__main__":
    unittest.main()
