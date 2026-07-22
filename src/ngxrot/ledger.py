"""Research ledger: persistent record of hypotheses and their fates.

Rules (enforced by SQL triggers in registry.sql, re-checked here):
  - hypotheses are never deleted; a dead idea stays on the books as 'rejected'
    with its conclusion — negative findings are findings;
  - description/motivation/created_at are immutable after creation;
  - every status change is appended to hypothesis_status_log with a reason;
  - resolving to confirmed/rejected requires a written conclusion.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pandas as pd

_VALID = {"untested", "testing", "confirmed", "rejected"}
_TRANSITIONS = {
    "untested": {"testing", "rejected"},
    "testing": {"confirmed", "rejected", "untested"},
    "confirmed": {"testing"},   # reopening is allowed and logged
    "rejected": {"testing"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_hypothesis(reg: sqlite3.Connection, hypothesis_id: str,
                   description: str, motivation: str) -> None:
    reg.execute(
        "INSERT INTO hypotheses (hypothesis_id, description, motivation, status, created_at) "
        "VALUES (?,?,?,'untested',?)",
        (hypothesis_id, description, motivation, _now()))
    reg.execute(
        "INSERT INTO hypothesis_status_log (hypothesis_id, old_status, new_status, "
        "changed_at, reason) VALUES (?,NULL,'untested',?,?)",
        (hypothesis_id, _now(), "created"))
    reg.commit()


def set_status(reg: sqlite3.Connection, hypothesis_id: str, new_status: str,
               reason: str, conclusion: str | None = None) -> None:
    if new_status not in _VALID:
        raise ValueError(f"invalid status {new_status!r}")
    row = reg.execute("SELECT status FROM hypotheses WHERE hypothesis_id = ?",
                      (hypothesis_id,)).fetchone()
    if not row:
        raise KeyError(f"unknown hypothesis {hypothesis_id}")
    old = row[0]
    if new_status not in _TRANSITIONS[old]:
        raise ValueError(f"illegal transition {old} -> {new_status}")
    resolved = _now() if new_status in {"confirmed", "rejected"} else None
    reg.execute(
        "UPDATE hypotheses SET status=?, resolved_at=?, conclusion=? WHERE hypothesis_id=?",
        (new_status, resolved,
         conclusion if new_status in {"confirmed", "rejected"} else None,
         hypothesis_id))
    reg.execute(
        "INSERT INTO hypothesis_status_log (hypothesis_id, old_status, new_status, "
        "changed_at, reason) VALUES (?,?,?,?,?)",
        (hypothesis_id, old, new_status, _now(), reason))
    reg.commit()


def freeze(reg: sqlite3.Connection, hypothesis_id: str, reason: str) -> None:
    """Permanently close a RESOLVED hypothesis: no further status changes and
    no new experiments under this ID (both enforced by SQL triggers). There
    is deliberately no unfreeze."""
    row = reg.execute("SELECT status, frozen FROM hypotheses WHERE hypothesis_id = ?",
                      (hypothesis_id,)).fetchone()
    if not row:
        raise KeyError(f"unknown hypothesis {hypothesis_id}")
    status, frozen = row
    if frozen:
        raise ValueError(f"{hypothesis_id} is already frozen")
    if status not in ("confirmed", "rejected"):
        raise ValueError(f"only resolved hypotheses can be frozen "
                         f"(status is {status!r})")
    reg.execute("UPDATE hypotheses SET frozen = 1 WHERE hypothesis_id = ?",
                (hypothesis_id,))
    reg.execute(
        "INSERT INTO hypothesis_status_log (hypothesis_id, old_status, new_status, "
        "changed_at, reason) VALUES (?,?,?,?,?)",
        (hypothesis_id, status, status, _now(), f"FROZEN: {reason}"))
    reg.commit()


def ledger(reg: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT h.hypothesis_id, h.status, h.frozen, h.description, h.created_at,
               h.resolved_at,
               (SELECT COUNT(*) FROM hypothesis_experiments he
                 WHERE he.hypothesis_id = h.hypothesis_id) AS n_experiments
        FROM hypotheses h ORDER BY h.hypothesis_id""", reg)
