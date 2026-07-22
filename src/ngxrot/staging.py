"""Pre-ingestion staging validation: no row enters the research database
until its containing period is verified research-ready.

Checks per index series:
  - duplicate observations (same date, differing values);
  - suspicious jumps: |daily return| >= jump_threshold (default 15% — a
    diversified index should never print this; it usually means a rebase,
    a decimal error, or a vendor splice);
  - abnormal gaps: >= gap_days consecutive weekdays with no observation;
  - monthly weekday coverage (NGX holidays make ~100% unattainable; months
    below min_month_coverage are not research-ready);
  - anchor cross-reference: independently sourced (index, date, value)
    triples must match within anchor_tolerance.

Policy (per research mandate): a month containing an unexplained jump, an
abnormal gap, or sub-threshold coverage is EXCLUDED, not repaired. A failed
anchor fails the whole series. Research-ready windows are the maximal
contiguous runs of clean months, reported per index. Losing sample beats
ingesting questionable data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

PKG_ROOT = Path(__file__).resolve().parents[2]
REPORTS = PKG_ROOT / "reports"

DEFAULTS = dict(jump_threshold=0.15, gap_days=5, min_month_coverage=0.75,
                anchor_tolerance=0.005)


@dataclass
class SeriesVerdict:
    index_code: str
    n_rows: int
    first: str
    last: str
    weekday_coverage: float
    duplicates: int
    jumps: list = field(default_factory=list)          # [(date, ret)]
    gaps: list = field(default_factory=list)           # [(start, end, n_days)]
    excluded_months: list = field(default_factory=list)
    anchor_results: list = field(default_factory=list) # [(date, expected, got, ok)]
    anchors_ok: bool = True
    ready_windows: list = field(default_factory=list)  # [(start, end)]

    @property
    def ready_days(self) -> int:
        return sum((pd.Timestamp(b) - pd.Timestamp(a)).days
                   for a, b in self.ready_windows)


def validate_series(df: pd.DataFrame, anchors: pd.DataFrame | None = None,
                    **params) -> SeriesVerdict:
    p = {**DEFAULTS, **params}
    code = df.index_code.iloc[0]
    df = df.sort_values("trade_date")
    dates = pd.to_datetime(df.trade_date)

    dup_mask = df.duplicated(subset=["trade_date"], keep=False)
    n_dup = int(df[dup_mask].trade_date.nunique())

    s = df.drop_duplicates("trade_date").set_index(pd.DatetimeIndex(
        pd.to_datetime(df.drop_duplicates("trade_date").trade_date)))["close_value"]
    ret = s.pct_change()
    jumps = [(d.strftime("%Y-%m-%d"), round(float(r), 4))
             for d, r in ret[ret.abs() >= p["jump_threshold"]].items()]

    all_wd = pd.bdate_range(s.index.min(), s.index.max())
    missing = all_wd.difference(s.index)
    gaps = []
    if len(missing):
        grp = (pd.Series(missing).diff().dt.days != 1).cumsum()
        for _, g in pd.Series(missing).groupby(grp):
            if len(g) >= p["gap_days"]:
                gaps.append((g.iloc[0].strftime("%Y-%m-%d"),
                             g.iloc[-1].strftime("%Y-%m-%d"), len(g)))

    cov_by_month = (s.groupby(s.index.to_period("M")).size() /
                    pd.Series(all_wd, index=all_wd).groupby(all_wd.to_period("M")).size())
    bad_months = set(str(m) for m, c in cov_by_month.items()
                     if c < p["min_month_coverage"])
    for d, _ in jumps:
        bad_months.add(d[:7])
    for a, b, _ in gaps:
        for m in pd.period_range(a[:7], b[:7], freq="M"):
            bad_months.add(str(m))

    anchor_results, anchors_ok = [], True
    if anchors is not None:
        for _, a in anchors[anchors.index_code == code].iterrows():
            got = s.get(pd.Timestamp(a.trade_date))
            if got is None:
                anchor_results.append((a.trade_date, a.expected_value, None, False))
                anchors_ok = False
            else:
                ok = abs(got / a.expected_value - 1) <= p["anchor_tolerance"]
                anchor_results.append((a.trade_date, a.expected_value,
                                       round(float(got), 2), ok))
                anchors_ok &= ok

    ready = []
    if anchors_ok:
        months = [str(m) for m in cov_by_month.index if str(m) not in bad_months]
        if months:
            run_start = months[0]
            prev = pd.Period(months[0])
            for m in months[1:] + [None]:
                if m is None or pd.Period(m) != prev + 1:
                    ready.append((f"{run_start}-01",
                                  str((prev.to_timestamp("M") + pd.offsets.MonthEnd(0)).date())))
                    if m is not None:
                        run_start = m
                if m is not None:
                    prev = pd.Period(m)

    return SeriesVerdict(
        index_code=code, n_rows=len(s),
        first=str(s.index.min().date()), last=str(s.index.max().date()),
        weekday_coverage=round(len(s) / len(all_wd), 4),
        duplicates=n_dup, jumps=jumps, gaps=gaps,
        excluded_months=sorted(bad_months), anchor_results=anchor_results,
        anchors_ok=anchors_ok, ready_windows=ready)


def filter_to_ready(df: pd.DataFrame, verdict: SeriesVerdict) -> pd.DataFrame:
    """Keep only rows inside research-ready windows."""
    keep = pd.Series(False, index=df.index)
    for a, b in verdict.ready_windows:
        keep |= (df.trade_date >= a) & (df.trade_date <= b)
    return df[keep]


def completeness_report(verdicts: list[SeriesVerdict], stats: dict,
                        anchors_note: str) -> Path:
    REPORTS.mkdir(exist_ok=True)
    lines = [f"# Data Completeness Report — investing_com — {date.today().isoformat()}",
             "", anchors_note, "",
             "| index | rows | first | last | wd-coverage | dup | jumps | gaps | "
             "excluded months | anchors | research-ready windows |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in verdicts:
        anch = ("n/a" if not v.anchor_results else
                ("PASS" if v.anchors_ok else "FAIL"))
        wins = "; ".join(f"{a}..{b}" for a, b in v.ready_windows) or "NONE"
        lines.append(
            f"| {v.index_code} | {v.n_rows} | {v.first} | {v.last} | "
            f"{v.weekday_coverage:.1%} | {v.duplicates} | {len(v.jumps)} | "
            f"{len(v.gaps)} | {len(v.excluded_months)} | {anch} | {wins} |")
    lines += ["", "## Anomaly detail", ""]
    for v in verdicts:
        if v.jumps or v.gaps or v.anchor_results:
            lines.append(f"### {v.index_code}")
            for d, r in v.jumps:
                lines.append(f"- jump {r:+.1%} on {d} — month excluded pending "
                             f"explanation (rebase? vendor splice?)")
            for a, b, n in v.gaps:
                lines.append(f"- gap {a}..{b} ({n} weekdays) — months excluded")
            for d, exp, got, ok in v.anchor_results:
                lines.append(f"- anchor {d}: expected {exp:,.2f}, got "
                             f"{got if got is not None else 'MISSING'} — "
                             f"{'OK' if ok else 'FAIL'}")
            lines.append("")
    lines += ["## Ingestion statistics", ""]
    for k, v in stats.items():
        lines.append(f"- {k}: {v}")
    lines += ["", "Periods not listed as research-ready are treated as "
              "UNAVAILABLE. No reconstruction, interpolation, or backfill "
              "was performed."]
    path = REPORTS / f"data_completeness_{date.today().isoformat()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
