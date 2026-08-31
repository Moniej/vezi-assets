"""Freeze the pre-outcome H-024 predictor/eligibility substrate.

This script is intentionally incapable of materialising forward RV, joining an
outcome to a predictor, or running a regression. It reads only frozen H-011
market data and a read-only canonical identity database.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tomllib
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ngxrot.canonical.contracts import AvailabilityPolicy, TemporalPrecision, TemporalQueryContext, TemporalValue  # noqa: E402
from ngxrot.h024_dataset import action_flags, eligibility_reason, predictor_row  # noqa: E402
from ngxrot.identity.resolver import resolve_instrument  # noqa: E402
from ngxrot.universe import rename_chain  # noqa: E402

CONFIG = ROOT / "configs" / "h024_liquidity_shock_volatility.toml"
PROTOCOL = ROOT / "docs" / "research_protocols" / "H024_LIQUIDITY_SHOCK_VOLATILITY_PROTOCOL_2026-08-31.md"
SOURCE = ROOT / "fixtures" / "frozen" / "h011_liquidity_comparison.sqlite"
IDENTITY_DB = ROOT / "data" / "ngx.sqlite"
OUT = ROOT / "fixtures" / "frozen"
FIXTURE = OUT / "h024_liquidity_shock_volatility.sqlite"
MANIFEST = OUT / "h024_liquidity_shock_volatility_manifest.json"
COVERAGE = OUT / "h024_liquidity_shock_volatility_coverage_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def monthly_formations(market_dates: pd.DatetimeIndex) -> list[pd.Timestamp]:
    series = pd.Series(market_dates, index=market_dates)
    return list(series.groupby(series.index.to_period("M")).max())


def iru_v2(raw: pd.DataFrame, formation: pd.Timestamp, rules: dict) -> pd.DataFrame:
    """IRU-v2 reconstructed only from the frozen source market panel."""
    membership = rules["membership"]
    start = formation - pd.Timedelta(days=int(membership["trailing_days"]))
    window = raw[(raw.trade_date > start) & (raw.trade_date <= formation)]
    grouped = window.groupby("ticker").agg(
        n_days=("trade_date", "nunique"), avg_value=("value_traded", "mean"),
        last_trade=("trade_date", "max"),
    ).reset_index()
    excluded = set(rules["instrument"]["exclude_symbols"])
    patterns = "|".join(rules["instrument"]["exclude_patterns"])
    grouped = grouped[~grouped.ticker.isin(excluded)]
    grouped = grouped[~grouped.ticker.str.upper().str.contains(patterns, regex=True)]
    market_dates = raw.loc[raw.trade_date <= formation, "trade_date"].drop_duplicates().sort_values()
    stale_cutoff = market_dates.tail(int(membership["max_stale_sessions"])).min()
    qualified = grouped[(grouped.n_days >= int(membership["min_trading_days"])) &
                        (grouped.last_trade >= stale_cutoff)].sort_values("avg_value", ascending=False).copy()
    qualified["liquidity_rank"] = range(1, len(qualified) + 1)
    return qualified[qualified.liquidity_rank <= int(membership["liquidity_rank_max"])]


def count_by_year(rows: list[dict], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row["formation_date"])[:4] for row in rows if row.get(key)).items()))


def forward_window_available(frame: pd.DataFrame, formation: pd.Timestamp,
                             sessions: pd.DatetimeIndex, horizon: int) -> bool:
    """Missingness-only check; it never reads, computes, or stores returns."""
    position = sessions.get_indexer([formation])[0]
    needed = sessions[position:position + horizon + 1]
    if len(needed) != horizon + 1:
        return False
    available = set(frame.loc[pd.to_numeric(frame.close, errors="coerce").notna(), "trade_date"])
    return set(needed).issubset(available)


def main() -> int:
    if FIXTURE.exists() and "--replace" not in sys.argv:
        raise RuntimeError("refusing to replace frozen H-024 fixture; use --replace for a reviewed new version")
    if FIXTURE.exists():
        FIXTURE.unlink()
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    rules = tomllib.loads((ROOT / "configs" / "iru.toml").read_text(encoding="utf-8"))
    source = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True)
    raw = pd.read_sql("SELECT * FROM daily_market_data", source)
    raw["trade_date"] = pd.to_datetime(raw["trade_date"])
    raw = raw[(raw.trade_date >= config["data"]["sample_start"]) &
              (raw.trade_date <= config["data"]["sample_end"])].copy()
    raw = raw.sort_values(["ticker", "trade_date", "as_of_date", "confidence", "source_id"]).drop_duplicates(["ticker", "trade_date"], keep="last")
    actions = pd.read_sql("SELECT action_id,ticker,action_type,declared_date,markdown_date,qualification_date,as_of_date FROM corporate_action_flags", source)
    security_count = source.execute("SELECT COUNT(*) FROM security_identity").fetchone()[0]
    source.close()
    rename = rename_chain()
    raw["ticker"] = raw.ticker.map(lambda value: rename.get(value, value))
    raw = raw.sort_values(["ticker", "trade_date"]).drop_duplicates(["ticker", "trade_date"], keep="last")
    ticker_frames = {ticker: group.copy() for ticker, group in raw.groupby("ticker", sort=False)}
    sessions = pd.DatetimeIndex(sorted(raw.trade_date.unique()))
    forms = monthly_formations(sessions)
    identity = sqlite3.connect(f"file:{IDENTITY_DB}?mode=ro", uri=True)
    system_vintage = pd.Timestamp(config["data"]["system_vintage"]).date()
    action_dates = {}
    material = set(config["corporate_actions"]["material_action_types"])
    for ticker, group in actions.groupby("ticker"):
        if group.action_type.isin(material).any():
            action_dates[ticker] = [pd.Timestamp(value) for value in pd.concat(
                [group.markdown_date, group.qualification_date]
            ).dropna().unique()]

    rows: list[dict] = []
    schedule: list[dict] = []
    action_rows: list[dict] = []
    staleness_rows: list[dict] = []
    for formation in forms:
        expected = formation.strftime("%Y-%m-%d")
        members = iru_v2(raw, formation, rules)
        schedule.append({"intended_formation_date": expected, "actual_formation_date": expected,
                         "status": "valid", "skip_reason": None, "iru_candidate_count": len(members)})
        context = TemporalQueryContext(TemporalValue(formation.date(), TemporalPrecision.DATE), TemporalValue(system_vintage, TemporalPrecision.DATE),
                                       AvailabilityPolicy.STRICT_SYSTEM_VINTAGE)
        for member in members.itertuples(index=False):
            ticker = member.ticker
            predictor = predictor_row(ticker_frames[ticker], formation)
            forward_available = {f"forward_{horizon}d_window_available": int(
                forward_window_available(ticker_frames[ticker], formation, sessions, horizon)
            ) for horizon in (5, 20, 60)}
            resolution = resolve_instrument(identity, identifier=ticker, identifier_type="ticker",
                                            exchange="NGX", temporal_context=context)
            flags = action_flags(formation, action_dates.get(ticker, []), sessions)
            reason = eligibility_reason(
                adtv_valid_count=predictor["adtv60_valid_count"],
                baseline_valid_count=predictor["historical_adtv_valid_count"],
                identity_status=resolution.status.value,
                zero_return_fraction=predictor["trailing_zero_return_fraction"],
            )
            action_excluded = flags["action_in_lagged_vol_window"] or flags["action_in_forward_20d_window"]
            if reason is None and action_excluded:
                reason = "known_material_corporate_action"
            record = {
                "instrument_id": resolution.instrument_id, "legacy_ticker": ticker,
                "formation_date": expected, "decision_time": expected,
                "system_vintage": str(system_vintage),
                "availability_policy": config["data"]["availability_policy"],
                "identity_status": resolution.status.value,
                "identity_exclusion_reason": None if resolution.status.value == "resolved" else f"identity_{resolution.status.value}",
                "iru_liquidity_rank": int(member.liquidity_rank), "iru_avg_value": float(member.avg_value),
                **predictor, **forward_available, **flags,
                "primary_action_excluded": int(action_excluded),
                "higher_activity_subset": int((predictor["trailing_median_deals"] or 0) >= config["staleness"]["higher_activity_median_deals_minimum"]),
                "extreme_staleness": int((predictor["trailing_zero_return_fraction"] or 0) > config["staleness"]["extreme_zero_return_fraction"]),
                "eligible_for_primary": int(reason is None), "exclusion_reason": reason,
                "source_vintage": config["data"]["source_vintage"], "source_fixture": str(SOURCE.relative_to(ROOT)),
            }
            rows.append(record)
            action_rows.append({key: record[key] for key in ("instrument_id", "legacy_ticker", "formation_date", "action_in_lagged_vol_window", "action_in_forward_5d_window", "action_in_forward_20d_window", "action_in_forward_60d_window", "primary_action_excluded")})
            staleness_rows.append({key: record[key] for key in ("instrument_id", "legacy_ticker", "formation_date", "trailing_zero_return_fraction", "trailing_positive_volume_zero_return_fraction", "trailing_median_deals", "extreme_staleness", "higher_activity_subset")})
    identity.close()

    fixture_con = sqlite3.connect(FIXTURE)
    pd.DataFrame(rows).to_sql("h024_observations", fixture_con, index=False)
    pd.DataFrame(schedule).to_sql("formation_schedule", fixture_con, index=False)
    pd.DataFrame(action_rows).to_sql("corporate_action_exclusions", fixture_con, index=False)
    pd.DataFrame(staleness_rows).to_sql("staleness_diagnostics", fixture_con, index=False)
    fixture_con.execute("CREATE INDEX idx_h024_formation ON h024_observations(formation_date)")
    fixture_con.execute("CREATE INDEX idx_h024_ticker ON h024_observations(legacy_ticker)")
    fixture_con.commit()
    tables = {name: fixture_con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
              for name in ("h024_observations", "formation_schedule", "corporate_action_exclusions", "staleness_diagnostics")}
    columns = [{"name": row[1], "type": row[2], "nullable": not bool(row[3])}
               for row in fixture_con.execute("PRAGMA table_info(h024_observations)")]
    fixture_con.close()

    exclusions = Counter(row["exclusion_reason"] or "eligible" for row in rows)
    coverage = {
        "coverage_by_year": {
            year: {"candidate_observations": sum(1 for row in rows if row["formation_date"].startswith(year)),
                   "primary_eligible": sum(1 for row in rows if row["formation_date"].startswith(year) and row["eligible_for_primary"]),
                   "adtv60_coverage": sum(1 for row in rows if row["formation_date"].startswith(year) and row["adtv60_valid_count"] >= 45),
                   "baseline_coverage": sum(1 for row in rows if row["formation_date"].startswith(year) and row["historical_adtv_valid_count"] >= 120),
                   "lagged_rv20_coverage": sum(1 for row in rows if row["formation_date"].startswith(year) and row["lagged_rv20"] is not None),
                   "forward_5d_window_available": sum(1 for row in rows if row["formation_date"].startswith(year) and row["forward_5d_window_available"]),
                   "forward_20d_window_available": sum(1 for row in rows if row["formation_date"].startswith(year) and row["forward_20d_window_available"]),
                   "forward_60d_window_available": sum(1 for row in rows if row["formation_date"].startswith(year) and row["forward_60d_window_available"])}
            for year in sorted({row["formation_date"][:4] for row in rows})
        },
        "total_canonical_instruments": identity_count(IDENTITY_DB),
        "legacy_security_count": security_count,
        "candidate_instrument_formations": len(rows), "primary_eligible_instrument_formations": exclusions["eligible"],
        "exclusion_counts": dict(sorted(exclusions.items())),
        "outcome_availability": {"values": "not_materialized_or_inspected_by_design",
                                   "forward_5d_complete_price_window_count": sum(row["forward_5d_window_available"] for row in rows),
                                   "forward_20d_complete_price_window_count": sum(row["forward_20d_window_available"] for row in rows),
                                   "forward_60d_complete_price_window_count": sum(row["forward_60d_window_available"] for row in rows)},
        "cluster_adequacy": {"instrument_clusters": len({row["instrument_id"] for row in rows if row["eligible_for_primary"]}),
                             "time_clusters": len({row["formation_date"] for row in rows if row["eligible_for_primary"]}),
                             "adequate": False, "reason": "no PIT-safe historical canonical identities"},
    }
    COVERAGE.write_text(json.dumps(coverage, indent=2, sort_keys=True), encoding="utf-8")
    plan_checksum = hashlib.sha256((sha256(CONFIG) + sha256(PROTOCOL)).encode()).hexdigest()
    manifest = {
        "fixture_version": "1", "classification": "frozen_pre_outcome_research_dataset",
        "evidence_eligibility": "research_protocol_only", "dataset_sha256": sha256(FIXTURE),
        "config_sha256": sha256(CONFIG), "protocol_sha256": sha256(PROTOCOL), "analysis_plan_checksum": plan_checksum,
        "builder_sha256": sha256(Path(__file__)), "predictor_module_sha256": sha256(ROOT / "src" / "ngxrot" / "h024_dataset.py"),
        "code_commit": current_commit(), "source_fixture_sha256": sha256(SOURCE), "source_identity_database_sha256": sha256(IDENTITY_DB),
        "source_data_vintage": config["data"]["source_vintage"], "outcome_materialization": "not_materialized",
        "row_count": len(rows), "instrument_count": len({row["legacy_ticker"] for row in rows}), "formation_count": len(forms),
        "date_range": {"start": str(min(forms).date()), "end": str(max(forms).date())}, "tables": tables,
        "observation_schema": columns, "eligibility_counts": dict(sorted(exclusions.items())),
        "corporate_action_limitations": "Known recorded material actions are flagged; unrecorded actions remain residual risk; raw prices are not adjusted.",
        "staleness_limitations": "Zero returns are price-staleness proxies, not zero-trade counts; positive-volume zero-return remains separately retained.",
        "identity_resolution_policy": "strict_system_vintage canonical resolver; no historical alias inference or current ticker repair.",
        "inference_specification": config["inference"], "multiple_testing_family": config["validation"]["multiple_testing_family"],
        "coverage_report_sha256": sha256(COVERAGE), "deterministic_rebuild_required": True,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"dataset_sha256": manifest["dataset_sha256"], "rows": len(rows), "coverage": coverage}, indent=2))
    return 0


def identity_count(path: Path) -> int:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    count = con.execute("SELECT COUNT(*) FROM instrument_listings").fetchone()[0]
    con.close()
    return count


def current_commit() -> str:
    import subprocess
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


if __name__ == "__main__":
    raise SystemExit(main())
