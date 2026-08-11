"""Research OS -- dataset access + reproducibility snapshots.

A clean, research-facing query surface on top of the EXISTING db.py PIT
readers and universe.py's IRU -- no new provider, no new ingestion path,
no parallel database. This module answers "give me the data a researcher
would actually query" (a security/universe over a date range, tagged with
full provenance) and "let me pin exactly what I just queried so someone
else can reproduce it later."

Reproducibility model: every dataset returned by this module can be
snapshotted via `record_snapshot()`, which writes one immutable row to
registry.sqlite's `dataset_snapshots` table (schema/registry.sql, 2026-
08-10 addition) -- the query parameters (universe/date range/vintage/
sources/confidence floor) plus a deterministic content hash of the
returned rows and the code_fingerprint that produced them. A later
researcher who wants "exactly the dataset that existed at snapshot X" can
re-run the same query with the same vintage and compare content_hash.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from . import db, registry, universe


def _content_hash(df: pd.DataFrame) -> str:
    """Deterministic hash of a DataFrame's content, independent of row
    order -- sort by every column first so two logically-identical result
    sets always hash identically."""
    if df.empty:
        return hashlib.sha256(b"empty").hexdigest()[:16]
    sortable = df.sort_values(list(df.columns)).reset_index(drop=True)
    return hashlib.sha256(
        sortable.to_csv(index=False).encode("utf-8")
    ).hexdigest()[:16]


@dataclass
class ResearchDataset:
    """A queried dataset plus everything needed to describe/reproduce it.
    `data` is the actual DataFrame; everything else is provenance."""
    dataset_kind: str
    query_params: dict
    data: pd.DataFrame
    universe_version: str | None = None
    captured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def row_count(self) -> int:
        return len(self.data)

    @property
    def content_hash(self) -> str:
        return _content_hash(self.data)

    def manifest(self) -> dict:
        """JSON-serializable reproducibility manifest -- everything a
        future researcher needs to know WHAT this dataset was and HOW to
        re-derive it, without embedding the data itself."""
        return {
            "dataset_kind": self.dataset_kind,
            "query_params": self.query_params,
            "universe_version": self.universe_version,
            "row_count": self.row_count,
            "content_hash": self.content_hash,
            "captured_at": self.captured_at,
            "code_fingerprint": registry.code_fingerprint(),
        }

    def record_snapshot(self, reg: sqlite3.Connection, notes: str = "") -> str:
        """Writes one immutable row to registry.sqlite's dataset_snapshots
        table. Returns the snapshot_id."""
        snapshot_id = str(uuid.uuid4())
        reg.execute(
            "INSERT INTO dataset_snapshots (snapshot_id, created_at, code_fingerprint, "
            "git_commit, dataset_kind, query_params_json, row_count, content_hash, "
            "universe_version, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (snapshot_id, self.captured_at, registry.code_fingerprint(), registry._git_commit(),
             self.dataset_kind, json.dumps(self.query_params, sort_keys=True), self.row_count,
             self.content_hash, self.universe_version, notes),
        )
        reg.commit()
        return snapshot_id


def get_equity_dataset(
    con: sqlite3.Connection,
    start: str,
    end: str,
    tickers: list[str] | None = None,
    universe_as_of: str | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
    sources: list[str] | None = None,
) -> ResearchDataset:
    """Equity price research dataset over [start, end]. If `tickers` is
    omitted and `universe_as_of` is given, the IRU (existing
    universe.iru_members) as of that date defines the ticker set --
    reuses the existing rule-based, versioned, PIT eligibility logic
    rather than inventing a second universe concept. If neither is given,
    every ticker with data in range is returned (unfiltered, disclosed
    via query_params)."""
    universe_version = None
    resolved_tickers = tickers
    if resolved_tickers is None and universe_as_of is not None:
        rules = universe.load_rules()
        mem = universe.iru_members(con, universe_as_of, rules)
        resolved_tickers = mem.ticker.tolist()
        universe_version = rules["version"]

    df = db.equity_prices_range(con, start, end, tickers=resolved_tickers,
                                min_confidence=min_confidence, vintage=vintage, sources=sources)
    params = {"start": start, "end": end, "tickers": sorted(resolved_tickers) if resolved_tickers else None,
              "universe_as_of": universe_as_of, "min_confidence": min_confidence,
              "vintage": vintage, "sources": sources}
    return ResearchDataset(dataset_kind="equity_prices_range", query_params=params, data=df,
                           universe_version=universe_version)


def get_index_dataset(
    con: sqlite3.Connection,
    start: str,
    end: str,
    index_codes: list[str] | None = None,
    min_confidence: float = 0.0,
    vintage: str | None = None,
    sources: list[str] | None = None,
) -> ResearchDataset:
    """Index-level research dataset over [start, end]."""
    df = db.index_levels_range(con, start, end, index_codes=index_codes,
                               min_confidence=min_confidence, vintage=vintage, sources=sources)
    params = {"start": start, "end": end, "index_codes": index_codes, "min_confidence": min_confidence,
              "vintage": vintage, "sources": sources}
    return ResearchDataset(dataset_kind="index_levels_range", query_params=params, data=df)
