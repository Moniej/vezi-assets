"""Static isolation guards: regression runners must require fixture inputs, never live paths."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class EnvironmentIndependenceTests(unittest.TestCase):
    def test_fre_runner_defaults_to_frozen_fixture_not_live_database(self) -> None:
        text = (ROOT / "scripts" / "fre" / "test_financial_ratios.py").read_text(encoding="utf-8")
        self.assertIn("FROZEN_DB", text)
        self.assertNotIn("db.DEFAULT_DB", text)

    def test_portfolio_runner_uses_explicit_fixture_databases(self) -> None:
        text = (ROOT / "scripts" / "portfolio" / "test_integration_e2e.py").read_text(encoding="utf-8")
        self.assertIn("--market-db", text)
        self.assertIn("--registry-db", text)
        self.assertNotIn("AlphaEngine()", text)

    def test_fixtures_are_not_optional(self) -> None:
        for relative in ("scripts/fre/test_financial_ratios.py", "scripts/test_research_memory.py", "scripts/portfolio/test_integration_e2e.py"):
            self.assertIn("fixture", (ROOT / relative).read_text(encoding="utf-8").lower())
