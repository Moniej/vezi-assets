"""Research-data lineage: composes an existing observation's full
provenance chain (security -> source -> endpoint -> observation date ->
ingestion run -> validation status -> transformation) purely by reading
EXISTING columns/tables. No new schema, no new table, read-only.

Design note (deliberate, not an oversight): this platform has no
`ingestion_runs` table. `(source_id, as_of_date)` already functions as
the de facto ingestion-run identifier -- every row written by a single
`ingest.py` invocation shares both, and `as_of_date` is stamped by
`ingest.py` itself at write time (see ingest.py's INSERT). Adding a
surrogate `ingestion_runs` table would duplicate information already
fully recoverable from `equity_prices` grouped by `(source_id,
as_of_date)`, which the "no second ingestion architecture" constraint on
this project argues against.

  PYTHONPATH=src python -c "from ngxrot import db, lineage; con = db.connect();
  print(lineage.trace_equity_observation(con, 'CILEASING', '2024-01-05'))"
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class ObservationLineage:
    ticker: str
    trade_date: str
    found: bool
    source_id: int | None = None
    source_name: str | None = None
    source_kind: str | None = None
    source_reliability: str | None = None
    source_endpoint: str | None = None
    as_of_date: str | None = None
    ingestion_run: str | None = None  # (source_id, as_of_date) composite id
    confidence: float | None = None
    inserted_at: str | None = None
    close: float | None = None
    validation_flags: list[dict] = field(default_factory=list)
    validation_status: str = "no_flags_found"


def trace_equity_observation(
    con: sqlite3.Connection, ticker: str, trade_date: str, source_id: int | None = None,
) -> ObservationLineage:
    """Traces one (ticker, trade_date) equity_prices observation back
    through every existing column that already encodes provenance. If
    `source_id` is omitted and multiple sources have a row for this
    (ticker, trade_date), the highest-confidence row is traced."""
    row = con.execute(
        "SELECT ticker, trade_date, close, source_id, confidence, as_of_date, inserted_at "
        "FROM equity_prices WHERE ticker = ? AND trade_date = ?"
        + (" AND source_id = ?" if source_id is not None else "")
        + " ORDER BY confidence DESC LIMIT 1",
        (ticker, trade_date, source_id) if source_id is not None else (ticker, trade_date),
    ).fetchone()

    if row is None:
        return ObservationLineage(ticker=ticker, trade_date=trade_date, found=False)

    _, _, close, sid, confidence, as_of_date, inserted_at = row

    src = con.execute(
        "SELECT name, kind, reliability, url_template FROM sources WHERE source_id = ?", (sid,)
    ).fetchone()
    source_name, source_kind, source_reliability, endpoint = src if src else (None, None, None, None)

    flags = con.execute(
        "SELECT check_name, severity, detail, resolved, logged_at FROM data_quality_log "
        "WHERE entity_type = 'ticker' AND entity_code = ? AND (trade_date = ? OR trade_date IS NULL) "
        "ORDER BY logged_at",
        (ticker, trade_date),
    ).fetchall()
    validation_flags = [
        {"check_name": f[0], "severity": f[1], "detail": f[2], "resolved": bool(f[3]), "logged_at": f[4]}
        for f in flags
    ]
    if not validation_flags:
        status = "no_flags_found"
    elif all(f["resolved"] for f in validation_flags):
        status = "flagged_and_resolved"
    else:
        status = "flagged_unresolved"

    return ObservationLineage(
        ticker=ticker, trade_date=trade_date, found=True,
        source_id=sid, source_name=source_name, source_kind=source_kind,
        source_reliability=source_reliability, source_endpoint=endpoint,
        as_of_date=as_of_date, ingestion_run=f"{sid}:{as_of_date}",
        confidence=confidence, inserted_at=inserted_at, close=close,
        validation_flags=validation_flags, validation_status=status,
    )
