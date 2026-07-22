"""Event ingestion & validation pipeline (H-003 data layer).

Sits between any event source (CSV batches, future scrapers) and the events
table. Enforces, per batch:

  taxonomy    — event_type must be a leaf of configs/event_taxonomy.toml;
                category, direction, severity vocabularies checked;
  chronology  — announced_date must parse; effective_date earlier than
                announced_date is flagged (possible but suspicious);
                publication_ts on a different day than announced_date is
                flagged; nothing dated after the batch as_of is accepted;
  unknowns    — missing effective dates/directions stay NULL/'unknown'.
                The pipeline never infers, backfills, or fabricates;
  duplicates  — same (event_type, announced_date, scope, index_code) within
                the batch or already in the DB from the same source;
  conflicts   — same natural key already in the DB from a DIFFERENT source
                with different effective_date or direction: both rows are
                preserved (PIT append-only), the conflict is logged and
                reported for resolution by confidence, never by deletion;
  reporting   — every ingestion writes reports/event_quality_<date>.md and
                appends to data_quality_log.

Historical records are never overwritten: ingestion is append-only with
(source_id, as_of_date) lineage, same as every other dataset.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from . import ingest as ingest_mod

PKG_ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = PKG_ROOT / "configs" / "event_taxonomy.toml"
REPORTS = PKG_ROOT / "reports"

_DIRECTIONS = {"bullish", "bearish", "neutral", "unknown"}
_SEVERITIES = {"low", "medium", "high", "critical"}


def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    type_to_cat = {}
    for cat, spec in raw.items():
        for t in spec.get("types", []):
            if t in type_to_cat:
                raise ValueError(f"event type {t!r} appears in two categories")
            type_to_cat[t] = cat
    return {"categories": raw, "type_to_category": type_to_cat}


@dataclass
class EventBatchReport:
    batch_rows: int = 0
    accepted: int = 0
    rejected: int = 0
    issues: list = field(default_factory=list)   # (severity, row_ref, message)

    def add(self, sev: str, ref: str, msg: str):
        self.issues.append((sev, ref, msg))


def validate_batch(df: pd.DataFrame, con, as_of: str,
                   taxonomy: dict | None = None) -> tuple[pd.DataFrame, EventBatchReport]:
    tax = taxonomy or load_taxonomy()
    rep = EventBatchReport(batch_rows=len(df))
    df = df.copy()
    drop = pd.Series(False, index=df.index)

    for i, r in df.iterrows():
        ref = f"{r.get('event_type')}@{r.get('announced_date')}"
        # taxonomy
        cat = tax["type_to_category"].get(str(r.get("event_type")))
        if cat is None:
            rep.add("REJECT", ref, f"event_type {r.get('event_type')!r} not in taxonomy")
            drop[i] = True
            continue
        if pd.isna(r.get("category")) or not str(r.get("category")).strip():
            rep.add("REJECT", ref, "category missing (must be stated, not inferred)")
            drop[i] = True
            continue
        if str(r.get("category")) != cat:
            rep.add("WARN", ref, f"category {r.get('category')!r} != taxonomy home "
                                 f"category {cat!r} for this type")
        # vocabularies
        if pd.notna(r.get("direction")) and str(r.get("direction")) not in _DIRECTIONS:
            rep.add("REJECT", ref, f"direction {r.get('direction')!r} invalid")
            drop[i] = True
            continue
        if pd.notna(r.get("severity")) and str(r.get("severity")) not in _SEVERITIES:
            rep.add("REJECT", ref, f"severity {r.get('severity')!r} invalid")
            drop[i] = True
            continue
        # chronology
        ann, eff = r.get("announced_date"), r.get("effective_date")
        if pd.notna(eff) and str(eff) < str(ann):
            rep.add("WARN", ref, f"effective_date {eff} precedes announced_date "
                                 f"{ann} — verify (retroactive policy?)")
        if str(ann) > as_of:
            rep.add("REJECT", ref, f"announced_date {ann} is after batch as_of {as_of}")
            drop[i] = True
            continue
        pub = r.get("publication_ts")
        if pd.notna(pub) and str(pub)[:10] != str(ann):
            rep.add("WARN", ref, f"publication_ts date {str(pub)[:10]} differs from "
                                 f"announced_date {ann}")

    # duplicates within batch
    key = ["event_type", "announced_date", "scope", "index_code"]
    have = [k for k in key if k in df.columns]
    dup = df.duplicated(subset=have, keep="first")
    for i in df.index[dup & ~drop]:
        rep.add("REJECT", f"row {i}", "duplicate natural key within batch")
    drop |= dup

    # duplicates / conflicts vs existing DB
    existing = pd.read_sql(
        "SELECT e.event_type, e.event_uid, e.announced_date, e.scope, "
        "e.index_code, e.effective_date, e.direction, e.outcome_numeric, "
        "e.headline, s.name AS src "
        "FROM events e JOIN sources s USING (source_id)", con)
    for i, r in df[~drop].iterrows():
        m = existing[(existing.event_type == r.get("event_type"))
                     & (existing.announced_date == r.get("announced_date"))
                     & (existing.scope == r.get("scope"))]
        if m.empty:
            continue
        ref = f"{r.get('event_type')}@{r.get('announced_date')}"
        same_src = m[m.src == r.get("_source_name", "")]
        if len(same_src):
            uid = r.get("event_uid")
            if uid:
                prior_uid = same_src[same_src.event_uid == uid]
                if len(prior_uid) == 0:
                    rep.add("REJECT", ref,
                            f"same natural key exists from this source WITHOUT "
                            f"uid {uid} — uid-less priors cannot be superseded "
                            f"in-place; resolve the legacy rows first")
                    drop[i] = True
                    continue
                identical = prior_uid[
                    (prior_uid.headline == r.get("headline"))
                    & (prior_uid.outcome_numeric.astype(float).round(4)
                       == round(float(r.get("outcome_numeric") or 0), 4))]
                if len(identical):
                    rep.add("REJECT", ref, "already ingested from this source "
                                           "with identical payload")
                    drop[i] = True
                else:
                    rep.add("RESTATEMENT", ref,
                            f"uid {uid}: payload changed vs prior capture — "
                            f"appended with new as_of; PIT reads use the latest")
                continue
            rep.add("REJECT", ref, "already ingested from this source "
                                   "(no uid to restate against)")
            drop[i] = True
            continue
        diff = m[(m.effective_date.fillna("") != str(r.get("effective_date") or ""))
                 | (m.direction.fillna("unknown") != str(r.get("direction") or "unknown"))]
        if len(diff):
            rep.add("CONFLICT", ref,
                    f"existing source(s) {sorted(diff.src.unique())} disagree on "
                    f"effective_date/direction — both preserved; resolve by "
                    f"confidence, never by deletion")

    clean = df[~drop].drop(columns=["_source_name"], errors="ignore")
    rep.accepted, rep.rejected = len(clean), int(drop.sum())
    return clean, rep


def write_quality_report(rep: EventBatchReport, source_name: str,
                         taxonomy_counts: pd.Series | None) -> Path:
    REPORTS.mkdir(exist_ok=True)
    lines = [f"# Event Ingestion Quality Report — {source_name} — "
             f"{date.today().isoformat()}", "",
             f"- batch rows: {rep.batch_rows}",
             f"- accepted: {rep.accepted}",
             f"- rejected: {rep.rejected}",
             f"- issues: {len(rep.issues)}", ""]
    if rep.issues:
        lines += ["| severity | event | message |", "|---|---|---|"]
        lines += [f"| {s} | {ref} | {msg} |" for s, ref, msg in rep.issues]
    if taxonomy_counts is not None and len(taxonomy_counts):
        lines += ["", "## Events in database by category (post-ingest)", ""]
        lines += [f"- {k}: {v}" for k, v in taxonomy_counts.items()]
    lines += ["", "Chronology, duplicate, and conflict rules: see "
              "`src/ngxrot/event_pipeline.py` docstring. Unknown fields remain "
              "NULL — nothing in this table is inferred from later summaries."]
    path = REPORTS / f"event_quality_{date.today().isoformat()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def ingest_events(con, provider, as_of: str | None = None, **fetch_kwargs) -> Path:
    """Full pipeline: fetch -> validate -> ingest clean rows -> quality report."""
    as_of = as_of or date.today().isoformat()
    df = provider.fetch("events", **fetch_kwargs)
    df["_source_name"] = provider.info.name
    clean, rep = validate_batch(df, con, as_of)

    if len(clean):
        source_id = ingest_mod.register_provider(con, provider)
        out = clean.copy()
        keep = [c for c in ("event_type", "event_uid", "category", "announced_date",
                            "effective_date", "publication_ts", "scope",
                            "index_code", "ticker", "headline", "outcome_numeric",
                            "outcome_text", "severity", "direction",
                            "structurally_impairing", "source_url", "notes")
                if c in out.columns]
        out = out[keep]
        out["source_id"] = source_id
        out["confidence"] = provider.info.base_confidence
        out["as_of_date"] = as_of
        out.to_sql("events", con, if_exists="append", index=False)

    for sev, ref, msg in rep.issues:
        con.execute(
            "INSERT INTO data_quality_log (check_name, entity_type, entity_code, "
            "severity, detail) VALUES ('event_pipeline','index',?,?,?)",
            (ref[:60], "error" if sev == "REJECT" else "warn", f"{sev}: {msg}"[:300]))
    con.commit()
    counts = pd.read_sql("SELECT category, COUNT(*) n FROM events "
                         "WHERE confidence > 0 GROUP BY category", con)
    counts = counts.set_index("category").n if len(counts) else None
    return write_quality_report(rep, provider.info.name, counts)
