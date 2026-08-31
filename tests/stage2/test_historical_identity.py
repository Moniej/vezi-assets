"""Evidence-first historical identity reconstruction guards."""
from __future__ import annotations

import sqlite3
import unittest

from ngxrot.identity.historical import (
    HistoricalIdentityPolicy,
    HistoricalResolutionStatus,
    assert_historical_identity,
    resolve_historical_instrument,
    historical_identity_assertion_migration,
)
from ngxrot.migrations.framework import MigrationRunner


class HistoricalIdentityTests(unittest.TestCase):
    def test_additive_migration_declares_next_ngx_version(self) -> None:
        migration = historical_identity_assertion_migration()
        self.assertEqual(migration.database_target, "ngx")
        self.assertEqual((migration.expected_pre_version, migration.expected_post_version), (3, 4))
        self.assertIn("historical_identifier_assertions", migration.sql)

    def test_migration_applies_to_a_version_two_copy_and_is_append_only(self) -> None:
        con = sqlite3.connect(":memory:")
        con.executescript("""
        CREATE TABLE instrument_listings(instrument_id TEXT PRIMARY KEY);
        CREATE TABLE identifier_aliases(alias_id TEXT PRIMARY KEY);
        CREATE TABLE canonical_evidence_items(evidence_id TEXT PRIMARY KEY);
        CREATE TABLE schema_migration_ledger(
            migration_id TEXT PRIMARY KEY, database_target TEXT NOT NULL, checksum TEXT NOT NULL,
            pre_version INTEGER NOT NULL, post_version INTEGER NOT NULL, applied_at TEXT NOT NULL,
            backup_manifest_sha256 TEXT
        );
        INSERT INTO schema_migration_ledger VALUES
            ('20260830_000_pre_consolidation_baseline','ngx','baseline',0,1,'2026-08-30T00:00:00+00:00','backup'),
            ('20260830_001_canonical_identity_foundation','ngx','identity',1,2,'2026-08-30T00:00:00+00:00','backup'),
            ('20260831_000_canonical_evidence_persistence_foundation','ngx','evidence',2,3,'2026-08-31T00:00:00+00:00','backup');
        """)
        runner = MigrationRunner([historical_identity_assertion_migration()])
        runner.apply_pending(con, database_target="ngx", backup_manifest_verified=True,
                             backup_manifest_sha256="copy-only-test-backup")
        self.assertEqual(runner.current_version(con, "ngx"), 4)
        self.assertIsNotNone(con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name='historical_identity_assertions_no_update'"
        ).fetchone())
        con.close()

    def setUp(self) -> None:
        self.con = sqlite3.connect(":memory:")
        self.con.executescript("""
        CREATE TABLE instrument_listings(instrument_id TEXT PRIMARY KEY, exchange_code TEXT);
        CREATE TABLE canonical_evidence_items(evidence_id TEXT PRIMARY KEY, supporting_text TEXT);
        CREATE TABLE identifier_aliases(alias_id TEXT PRIMARY KEY, subject_type TEXT, subject_id TEXT,
            identifier_type TEXT, identifier_value TEXT, exchange_code TEXT, valid_from TEXT,
            valid_to TEXT, verification_status TEXT, recorded_at TEXT);
        CREATE TABLE historical_identifier_assertions(assertion_id TEXT PRIMARY KEY, alias_id TEXT,
            canonical_instrument_id TEXT, identifier_type TEXT, identifier_value TEXT, exchange_code TEXT,
            valid_from TEXT, valid_to TEXT, validity_precision TEXT, verification_status TEXT,
            verification_method TEXT, evidence_id TEXT, citation_reference TEXT,
            source_authority_tier TEXT, recorded_at TEXT, supersedes_assertion_id TEXT);
        """)
        self.con.executemany("INSERT INTO instrument_listings VALUES (?,?)", [("i1", "NGX"), ("i2", "NGX")])
        self.con.execute("INSERT INTO canonical_evidence_items VALUES ('evidence-1','official historical list')")

    def tearDown(self) -> None:
        self.con.close()

    def test_later_recorded_verified_interval_is_reconstruction_only(self) -> None:
        assert_historical_identity(self.con, assertion_id="a1", instrument_id="i1", ticker="OLD",
                                   valid_from="2018-01-01", valid_to="2018-12-31",
                                   validity_precision="interval_verified", verification_status="verified",
                                   verification_method="official_historical_list", evidence_id="evidence-1",
                                   citation_reference="official://2018", source_authority_tier="tier1",
                                   recorded_at="2026-08-31")
        strict = resolve_historical_instrument(self.con, ticker="OLD", exchange="NGX", decision_date="2018-06-30",
                                               system_vintage="2018-06-30", policy=HistoricalIdentityPolicy.STRICT_SYSTEM_VINTAGE)
        rebuilt = resolve_historical_instrument(self.con, ticker="OLD", exchange="NGX", decision_date="2018-06-30",
                                                system_vintage="2018-06-30", policy=HistoricalIdentityPolicy.VERIFIED_HISTORICAL_RECONSTRUCTION)
        self.assertEqual(strict.status, HistoricalResolutionStatus.UNRESOLVED)
        self.assertEqual(rebuilt.status, HistoricalResolutionStatus.RESOLVED_VERIFIED)
        self.assertEqual(self.con.execute("SELECT recorded_at FROM historical_identifier_assertions WHERE assertion_id='a1'").fetchone()[0], "2026-08-31")

    def test_observed_on_date_only_does_not_extend_an_interval(self) -> None:
        assert_historical_identity(self.con, assertion_id="a2", instrument_id="i1", ticker="ONE_DAY",
                                   valid_from="2019-06-30", valid_to=None, validity_precision="observed_on_date_only",
                                   verification_status="verified", verification_method="official_list", evidence_id="evidence-1",
                                   citation_reference="official://2019-06-30", source_authority_tier="tier1", recorded_at="2026-08-31")
        result = resolve_historical_instrument(self.con, ticker="ONE_DAY", exchange="NGX", decision_date="2019-07-01",
                                               system_vintage="2026-08-31", policy=HistoricalIdentityPolicy.VERIFIED_HISTORICAL_RECONSTRUCTION)
        self.assertEqual(result.status, HistoricalResolutionStatus.UNRESOLVED)

    def test_conflicting_verified_assertions_are_ambiguous(self) -> None:
        for assertion, instrument in (("a3", "i1"), ("a4", "i2")):
            assert_historical_identity(self.con, assertion_id=assertion, instrument_id=instrument, ticker="DUP",
                                       valid_from="2020-01-01", valid_to="2020-12-31", validity_precision="interval_verified",
                                       verification_status="verified", verification_method="official", evidence_id="evidence-1",
                                       citation_reference=f"official://{assertion}", source_authority_tier="tier1", recorded_at="2026-08-31")
        result = resolve_historical_instrument(self.con, ticker="DUP", exchange="NGX", decision_date="2020-06-30",
                                               system_vintage="2026-08-31", policy=HistoricalIdentityPolicy.VERIFIED_HISTORICAL_RECONSTRUCTION)
        self.assertEqual(result.status, HistoricalResolutionStatus.AMBIGUOUS)

    def test_tier_four_or_missing_evidence_cannot_be_verified(self) -> None:
        with self.assertRaises(ValueError):
            assert_historical_identity(self.con, assertion_id="a5", instrument_id="i1", ticker="NEWS",
                                       valid_from="2020-01-01", valid_to="2020-12-31", validity_precision="interval_verified",
                                       verification_status="verified", verification_method="news", evidence_id="evidence-1",
                                       citation_reference="news://x", source_authority_tier="tier4", recorded_at="2026-08-31")
        with self.assertRaises(ValueError):
            assert_historical_identity(self.con, assertion_id="a6", instrument_id="i1", ticker="NOEVID",
                                       valid_from="2020-01-01", valid_to="2020-12-31", validity_precision="interval_verified",
                                       verification_status="verified", verification_method="official", evidence_id=None,
                                       citation_reference=None, source_authority_tier="tier1", recorded_at="2026-08-31")
