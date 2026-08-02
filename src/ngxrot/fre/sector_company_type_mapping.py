"""FSI Phase 26: Sector-to-Company-Type Mapping (docs/fre_runs/
fsi_phase26_preregistration.md).

A pure, read-only translation layer from NGX's own official
`securities.sector_ngx` (FSI Phase 23) onto `valuation_engine.py`'s own
company_type taxonomy (`configs/valuation_method_eligibility.toml`).
Deterministic lookup only -- `configs/sector_company_type_mapping.toml`
is the sole source of truth for every mapping; this module never
infers, never guesses, and returns `None` (never a fallback value of
its own) whenever a ticker's sector or sub-industry is not present in
that config, exactly like every other "unknown stays unknown" reader
on this platform.

`growth_company`/`turnaround_company` are financial-lifecycle
classifications, not industry classifications, and can never be
derived here by design -- they remain reachable only via
`configs/company_type_overrides.toml`'s own owner-judged mechanism.
"""
from __future__ import annotations

import sqlite3
import tomllib
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"

FINANCIAL_SERVICES_SECTOR = "FINANCIAL SERVICES"


def _load_mapping() -> dict:
    with open(CONFIG_DIR / "sector_company_type_mapping.toml", "rb") as fh:
        return tomllib.load(fh)


def derive_company_type_for_ticker(con: sqlite3.Connection, ticker: str) -> str | None:
    """Single-ticker only. Returns a company_type string only when the
    ticker's own securities.sector_ngx (and, for FINANCIAL SERVICES,
    its own sector_ngx_provenance.sub_industry) resolves unambiguously
    per configs/sector_company_type_mapping.toml. Returns None --
    never a guessed default -- when sector_ngx is NULL, or when the
    sector/sub-industry is deliberately absent from that config."""
    row = con.execute("SELECT sector_ngx FROM securities WHERE ticker = ?", (ticker,)).fetchone()
    if row is None or row[0] is None:
        return None
    sector_ngx = row[0]

    mapping = _load_mapping()

    if sector_ngx == FINANCIAL_SERVICES_SECTOR:
        sub_row = con.execute(
            "SELECT sub_industry FROM sector_ngx_provenance WHERE ticker = ?", (ticker,)
        ).fetchone()
        if sub_row is None or sub_row[0] is None:
            return None
        return mapping.get("financial_services_sub_industry", {}).get(sub_row[0])

    return mapping.get("sector", {}).get(sector_ngx)
