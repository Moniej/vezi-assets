"""The frozen regression fixture is a committed, independently verifiable test input."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "fixtures" / "stage1" / "frozen"


class FrozenFixtureTests(unittest.TestCase):
    def test_fixture_database_matches_manifest(self) -> None:
        manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
        db_path = FIXTURE_DIR / manifest["database_file"]
        self.assertTrue(db_path.is_file(), "frozen fixture database is missing")
        digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
        self.assertEqual(digest, manifest["database_sha256"])
        con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            actual = {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                      for name in manifest["table_row_counts"]}
        finally:
            con.close()
        self.assertEqual(actual, manifest["table_row_counts"])

    def test_registry_fixture_matches_manifest(self) -> None:
        manifest = json.loads((FIXTURE_DIR / "manifest.json").read_text(encoding="utf-8"))
        db_path = FIXTURE_DIR / manifest["registry_database_file"]
        self.assertEqual(hashlib.sha256(db_path.read_bytes()).hexdigest(), manifest["registry_database_sha256"])
        con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            actual = {name: con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                      for name in manifest["registry_table_row_counts"]}
        finally:
            con.close()
        self.assertEqual(actual, manifest["registry_table_row_counts"])


if __name__ == "__main__":
    unittest.main()
