"""Data Coverage Dashboard + Coverage Gate v2 — quality WITHIN the IRU.

Separation of concepts (IC directive 2026-07-17):
  - IRU (ngxrot.universe, configs/iru.toml): which securities are ELIGIBLE
    for research — rule-based, PIT, versioned.
  - Coverage Gate (this module, configs/coverage_thresholds.toml): whether
    sufficient HIGH-QUALITY data exists for those eligible securities —
    breadth, archive day-completeness, and quality-flag rates per year.

generate() rebuilds reports/data_coverage_dashboard.md and
data/coverage_gate.json; called automatically after equity ingestions.
runner.run_resolved refuses configs with data.requires_coverage_gate = true
while the gate fails or is stale.
"""

from __future__ import annotations

import json
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

PKG_ROOT = Path(__file__).resolve().parents[2]
REPORTS = PKG_ROOT / "reports"
GATE_PATH = PKG_ROOT / "data" / "coverage_gate.json"
THRESHOLDS = PKG_ROOT / "configs" / "coverage_thresholds.toml"
NOMINAL_TRADING_DAYS = 247


def generate(con) -> dict:
    from . import universe
    cfg = tomllib.loads(THRESHOLDS.read_text(encoding="utf-8"))
    thr = cfg["gate"]
    iru_rules = universe.load_rules()

    px_years = pd.read_sql(
        "SELECT substr(trade_date,1,4) AS yr, COUNT(DISTINCT trade_date) AS days "
        "FROM equity_prices WHERE confidence >= 0.9 GROUP BY yr", con)
    per_stock = pd.read_sql(
        "SELECT ticker, COUNT(*) AS n_obs, MIN(trade_date) AS first_date, "
        "MAX(trade_date) AS last_date FROM equity_prices "
        "WHERE confidence >= 0.9 GROUP BY ticker", con)
    fl = pd.read_sql(
        "SELECT entity_code, substr(trade_date,1,4) AS yr FROM data_quality_log "
        "WHERE check_name = 'unexplained_jump' AND entity_type = 'ticker'", con)
    flagged_by_year = fl.groupby("yr").entity_code.apply(set).to_dict()
    flagged = set(fl.entity_code)

    this_year = date.today().year
    rows, ready_years = [], []
    for _, yr_row in px_years.iterrows():
        y = int(yr_row.yr)
        as_of = f"{y}-12-31" if y < this_year else date.today().isoformat()
        mem = universe.iru_members(con, as_of, iru_rules)
        iru = set(mem.ticker)
        nominal = NOMINAL_TRADING_DAYS
        if y == this_year:  # prorate the year in progress
            nominal = max(int(NOMINAL_TRADING_DAYS
                              * (date.today().timetuple().tm_yday / 365)), 1)
        completeness = min(yr_row.days / nominal, 1.0)
        yr_flags = flagged_by_year.get(str(y), set())
        jump_rate = (len(iru & yr_flags) / len(iru)) if iru else 1.0
        ready = (len(iru) >= thr["min_iru_breadth"]
                 and completeness >= thr["min_day_completeness"]
                 and jump_rate <= thr["max_unexplained_jump_rate"])
        if ready:
            ready_years.append(y)
        rows.append(dict(year=y, iru_size=len(iru), days=int(yr_row.days),
                         completeness=round(completeness, 3),
                         jump_rate=round(jump_rate, 4), ready=ready))

    recent_ok = all(y in ready_years
                    for y in range(this_year - thr["require_recent_years"],
                                   this_year))
    gate_pass = (len(ready_years) >= thr["min_ready_years"] and recent_ok
                 and len(per_stock) > 0)

    gate = dict(generated=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                gate_version="v2_iru",
                iru_version=iru_rules["version"],
                gate_pass=bool(gate_pass), ready_years=ready_years,
                n_ready_years=len(ready_years), recent_years_ok=bool(recent_ok),
                covered_stocks=int(len(per_stock)),
                thresholds=thr)
    GATE_PATH.parent.mkdir(exist_ok=True)
    GATE_PATH.write_text(json.dumps(gate, indent=1), encoding="utf-8")

    REPORTS.mkdir(exist_ok=True)
    lines = [f"# Data Coverage Dashboard — generated {gate['generated']}",
             "",
             f"**COVERAGE GATE v2 (IRU {iru_rules['version']}): "
             f"{'PASS' if gate_pass else 'FAIL'}** — "
             f"{len(ready_years)} ready years (need ≥{thr['min_ready_years']}), "
             f"recent-years {'ok' if recent_ok else 'NOT ready'}.",
             "",
             "IRU decides eligibility (rule-based, PIT, rename-canonical); this "
             "gate scores data quality within it: breadth ≥ "
             f"{thr['min_iru_breadth']}, day-completeness ≥ "
             f"{thr['min_day_completeness']:.0%}, unexplained-jump rate ≤ "
             f"{thr['max_unexplained_jump_rate']:.0%}. Jump scan: adjacency "
             "moves >12% (beyond NGX ±10% band) with no corporate-action "
             "filing within ±5 business days.",
             "",
             "| year | IRU size | days present | completeness | jump rate | ready |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['year']} | {r['iru_size']} | {r['days']} | "
                     f"{r['completeness']:.1%} | {r['jump_rate']:.2%} | "
                     f"{'✅' if r['ready'] else '❌'} |")

    lines += ["", "## Per-stock inventory (top 60 by observations)", "",
              "| ticker | obs | first | last | flags |", "|---|---|---|---|---|"]
    for _, s in per_stock.sort_values("n_obs", ascending=False).head(60).iterrows():
        fl = "unexplained-jump" if s.ticker in flagged else ""
        lines.append(f"| {s.ticker} | {s.n_obs} | {s.first_date} | "
                     f"{s.last_date} | {fl} |")

    (REPORTS / "data_coverage_dashboard.md").write_text("\n".join(lines),
                                                        encoding="utf-8")
    return gate


def gate_status() -> dict:
    if not GATE_PATH.exists():
        return {"gate_pass": False, "reason": "dashboard never generated"}
    g = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    stale_days = tomllib.loads(THRESHOLDS.read_text(encoding="utf-8"))[
        "dashboard"]["staleness_days"]
    age = (datetime.now(timezone.utc)
           - datetime.fromisoformat(g["generated"])).days
    if age > stale_days:
        return {"gate_pass": False, "reason": f"dashboard stale ({age}d)"}
    return g
