"""Ingestion pipeline: provider -> validate -> stamp lineage/confidence -> DB.

This is the ONLY write path for observational data. Rules enforced here:
  - rows failing their dataset contract are rejected (never silently fixed)
    and logged to data_quality_log with a reason;
  - duplicate keys within one batch are rejected;
  - future-dated observations (trade/announced date > as_of) are rejected —
    a provider claiming to know tomorrow's close is a lookahead bug;
  - every accepted row is stamped with source_id, confidence, as_of_date;
  - unknown tickers/indices are auto-registered as skeleton reference rows
    (flagged in data_quality_log at 'info' so gaps are visible, not fatal).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import contracts
from .providers.base import DataProvider

_DATE_COL = {  # column checked against as_of for future-dating, per dataset
    "index_levels": "trade_date",
    "equity_prices": "trade_date",
    "corporate_actions": "declared_date",
    "index_membership": "announced_date",
    "events": "announced_date",
}

_REF_COLS = {  # which entity columns need reference rows to exist
    "index_levels": {"index": "index_code"},
    "equity_prices": {"ticker": "ticker"},
    "corporate_actions": {"ticker": "ticker"},
    "index_membership": {"index": "index_code", "ticker": "ticker"},
    "events": {},
}


@dataclass
class IngestReport:
    provider: str
    dataset: str
    fetched: int = 0
    accepted: int = 0
    rejected: int = 0
    reject_reasons: dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        rr = ", ".join(f"{k}={v}" for k, v in self.reject_reasons.items()) or "-"
        return (f"[{self.provider} -> {self.dataset}] fetched={self.fetched} "
                f"accepted={self.accepted} rejected={self.rejected} ({rr})")


def register_provider(con: sqlite3.Connection, provider: DataProvider) -> int:
    """Idempotently register the provider in the sources table."""
    info = provider.info
    row = con.execute("SELECT source_id FROM sources WHERE name = ?", (info.name,)).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        "INSERT INTO sources (name, kind, reliability, base_confidence, url_template, notes) "
        "VALUES (?,?,?,?,?,?)",
        (info.name, info.kind, info.reliability, info.base_confidence,
         info.url_template, info.notes))
    con.commit()
    return cur.lastrowid


def _log(con, check, etype, code, tdate, sev, detail):
    con.execute(
        "INSERT INTO data_quality_log (check_name, entity_type, entity_code, trade_date, "
        "severity, detail) VALUES (?,?,?,?,?,?)",
        (check, etype, code, tdate, sev, detail))


def _ensure_reference_rows(con, dataset: str, df: pd.DataFrame, provider_name: str):
    for etype, col in _REF_COLS[dataset].items():
        if col not in df.columns:
            continue
        for code in df[col].dropna().unique():
            table, pk = (("indices", "index_code") if etype == "index"
                         else ("securities", "ticker"))
            if con.execute(f"SELECT 1 FROM {table} WHERE {pk} = ?", (code,)).fetchone():
                continue
            if etype == "index":
                con.execute(
                    "INSERT INTO indices (index_code, name, weighting, notes) "
                    "VALUES (?, ?, 'capped_float_mcap', 'AUTO-REGISTERED skeleton; verify')",
                    (code, code))
            else:
                con.execute(
                    "INSERT INTO securities (ticker, name, notes) "
                    "VALUES (?, ?, 'AUTO-REGISTERED skeleton; verify')",
                    (code, code))
            _log(con, "auto_registered_reference", etype, code, None, "info",
                 f"skeleton created during ingest from {provider_name}")


def ingest(
    con: sqlite3.Connection,
    provider: DataProvider,
    dataset: str,
    as_of: str | None = None,
    confidence_override: float | None = None,
    **fetch_kwargs,
) -> IngestReport:
    as_of = as_of or date.today().isoformat()
    contract = contracts.CONTRACTS[dataset]
    report = IngestReport(provider=provider.info.name, dataset=dataset)

    df = provider.fetch(dataset, **fetch_kwargs)
    report.fetched = len(df)
    if df.empty:
        return report

    missing = [c for c in contract.required if c not in df.columns]
    if missing:
        raise ValueError(f"{provider.info.name}/{dataset}: missing required columns {missing}")

    # --- per-row contract validation -----------------------------------
    bad = pd.Series(False, index=df.index)
    reasons = pd.Series("", index=df.index)
    for col, detector in {**contract.required,
                          **{c: v for c, v in contract.optional.items() if c in df.columns}}.items():
        mask = detector(df[col]).fillna(True) if col in df.columns else None
        if mask is not None and mask.any():
            reasons.loc[mask & ~bad] = f"bad_{col}"
            bad |= mask

    # --- duplicate keys within batch ------------------------------------
    if contract.key:
        dup = df.duplicated(subset=list(contract.key), keep="first")
        reasons.loc[dup & ~bad] = "duplicate_key"
        bad |= dup

    # --- future-dating guard --------------------------------------------
    fcol = _DATE_COL[dataset]
    if fcol in df.columns:
        fut = pd.to_datetime(df[fcol], errors="coerce") > pd.Timestamp(as_of)
        fut = fut.fillna(False)
        reasons.loc[fut & ~bad] = "future_dated_vs_as_of"
        bad |= fut

    for i, r in df[bad].iterrows():
        code = r.get("index_code") or r.get("ticker") or "?"
        _log(con, f"ingest_reject_{reasons.at[i]}",
             "index" if "index_code" in df.columns else "ticker",
             str(code), str(r.get(fcol, "")), "warn",
             f"{dataset} row rejected during ingest from {provider.info.name}")
    for reason, n in reasons[bad].value_counts().items():
        report.reject_reasons[reason] = int(n)
    report.rejected = int(bad.sum())

    good = df[~bad].copy()
    if good.empty:
        con.commit()
        return report

    # --- stamp lineage + confidence and insert ---------------------------
    source_id = register_provider(con, provider)
    conf = confidence_override if confidence_override is not None else provider.info.base_confidence
    _ensure_reference_rows(con, dataset, good, provider.info.name)

    cols = [c for c in contract.all_columns() if c in good.columns]
    good = good[cols]
    good["source_id"] = source_id
    good["confidence"] = conf
    good["as_of_date"] = as_of

    good.to_sql(dataset, con, if_exists="append", index=False)
    con.commit()
    report.accepted = len(good)
    return report
