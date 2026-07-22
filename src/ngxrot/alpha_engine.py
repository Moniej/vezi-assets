"""Fund Alpha — the alpha engine (decision-making layer).

This is the product. Everything else in the repository exists to make this
module's output better.

Design (per FUND_ALPHA_CHARTER.md):
  - The engine only speaks from VALIDATED models: hypotheses that are
    `confirmed` in the ledger on evidence-grade data. It discovers them by
    querying the registry — a model is plugged in by validating it, not by
    editing this file.
  - "No position" is a first-class output. With zero validated sources the
    engine's correct recommendation set is empty, plus a pipeline report
    explaining exactly what would change that.
  - Every recommendation carries provenance to immutable experiment records;
    a recommendation without provenance is invalid by construction.

The Recommendation schema is deliberately final-shaped from day one: as
models graduate from the research framework, they implement
`ModelAdapter.generate()` and register in MODEL_ADAPTERS keyed by
hypothesis ID. Nothing else changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import pandas as pd

from . import registry

ACTIONS = ("buy", "sell", "hold", "avoid", "no_position")


@dataclass(frozen=True)
class Recommendation:
    as_of: str
    instrument: str                  # ticker / index code / 'PORTFOLIO'
    action: str                      # one of ACTIONS
    size_pct_nav: float | None       # None when action is no_position
    horizon: str | None              # e.g. 'quarterly'
    expected_excess_ann: float | None
    expected_max_drawdown: float | None
    confidence_rating: str           # High/Moderate/Low/Inconclusive (existing scale)
    rationale: str                   # plain language, always populated
    hypothesis_id: str | None        # provenance — None only for no_position
    experiment_ids: tuple = ()       # provenance to immutable records
    caveats: tuple = ()

    def __post_init__(self):
        if self.action not in ACTIONS:
            raise ValueError(f"invalid action {self.action!r}")
        if self.action != "no_position" and not self.experiment_ids:
            raise ValueError("recommendation without experiment provenance is invalid")


# Validated models register here as they graduate (keyed by hypothesis_id).
# An entry is only consulted if the ledger confirms its hypothesis.
MODEL_ADAPTERS: dict = {}


class H011SizeAdapter:
    """H-011 — Size (confirmed 2026-07-22, the platform's first validated
    factor). Long the smallest-cap quintile within IRU v2, quarterly,
    equal-weighted — the EXACT construction validated in
    docs/PREREG_H-011.md / configs/h011_size.toml. This adapter does not
    invent a new parameter or reselect a "better-looking" cell; top_n=20
    and rebalance="quarterly" are the base configuration that earned the
    High confidence rating, not a discretionary choice made here.

    Live vs. research vintage semantics, stated explicitly because it
    differs from every prereg in this program on purpose: VALIDATION runs
    pin vintage=2026-07-21 (the frozen dataset the gauntlet ran against,
    immutable in the registry). This adapter uses vintage="" (latest
    available) instead — a live recommendation that never sees data
    ingested after validation would be useless for actually acting today.
    The MODEL is frozen (top_n/rebalance/eligibility rules); the DATA it
    reads is current.

    Reuses backtest_xs.size_scores / load_market_cap_panel UNCHANGED —
    the same code path exercised by the gauntlet, not a reimplementation.
    """

    hypothesis_id = "H-011"
    TOP_N = 20
    REBALANCE = "quarterly"
    # Provenance: the final-evaluation experiment (the number the High
    # confidence rating is built from) and the untouched-OOS experiment.
    # docs/FACTOR_REGISTRY.md has the full evidence trail.
    EXPERIMENT_IDS = ("2f6c7f95-ca50-4957-8299-22ca00308001",   # p4_final_evaluation
                      "f20e6eb1-7aa4-414c-bad7-de1e87182d03")  # p4_wf_oos_2025_26
    # Headline figures use the final-evaluation (dev+full-window) result,
    # NOT the flashier untouched-OOS number (+53.0% over an 18-month
    # window) — quoting the short, strong OOS window as "expected" would
    # be cherry-picking; it is disclosed in caveats instead.
    EXPECTED_EXCESS_ANN = 0.1502
    EXPECTED_MAX_DRAWDOWN = -0.3281

    CAVEATS = (
        "SEVERE, MEASURED CAPACITY CONSTRAINT: median leg capacity ~NGN "
        "694,336; 100% of trade legs were rejected at NGN 1bn AUM during "
        "validation — the worst of any hypothesis tested on this "
        "platform. This is a small-AUM-only strategy by construction; "
        "deploying it at institutional scale would itself move the "
        "prices the backtest assumed were fixed.",
        "size_pct_nav is the weight WITHIN this sleeve (1/top_n), not a "
        "recommended share of total fund NAV.",
        "Full-issue market cap, NOT float-adjusted (no shares-"
        "outstanding/free-float dataset exists yet) — see "
        "docs/PREREG_H-011.md known limitations.",
        "Price-only returns (no dividend reinvestment).",
        "Untouched-OOS net excess was materially higher (+53.0% over "
        "2025-01 to 2026-06) than the figure quoted above — an 18-month "
        "window, not extrapolated as a steady-state expectation.",
        "Rebalances quarterly at month-end; this reflects the LATEST "
        "completed formation on or before as_of, not necessarily today.",
    )

    def generate(self, as_of: str) -> list["Recommendation"]:
        from . import backtest_xs, db
        con = db.connect()
        cfg = {
            "data": {"sim_start": "2016-01-02", "sim_end": as_of,
                     "min_confidence": 0.9, "vintage": ""},
            "signal": {"method": "xs_size", "min_obs_formation": 120,
                      "lookback_months": 12},
            "portfolio": {"top_n": self.TOP_N, "rebalance": self.REBALANCE},
        }
        panel = backtest_xs.load_panel(con, cfg)
        panel["mcap"] = backtest_xs.load_market_cap_panel(panel["close_ff"])
        scores = backtest_xs.size_scores(con, panel, cfg)
        if not scores:
            return []   # unknown stays unknown — no eligible formation yet
        latest = max(scores)
        sel = scores[latest].nlargest(min(self.TOP_N, len(scores[latest])))
        n = len(sel)
        if n == 0:
            return []
        return [
            Recommendation(
                as_of=as_of, instrument=ticker, action="buy",
                size_pct_nav=round(1.0 / n, 4), horizon=self.REBALANCE,
                expected_excess_ann=self.EXPECTED_EXCESS_ANN,
                expected_max_drawdown=self.EXPECTED_MAX_DRAWDOWN,
                confidence_rating="High",
                rationale=(
                    f"Size factor (H-011, confirmed 2026-07-22): {ticker} "
                    f"is in the smallest-cap quintile of IRU v2 as of the "
                    f"{latest.date()} formation (latest completed "
                    f"quarterly rebalance on or before {as_of})."),
                hypothesis_id=self.hypothesis_id,
                experiment_ids=self.EXPERIMENT_IDS,
                caveats=self.CAVEATS,
            )
            for ticker in sel.index
        ]


MODEL_ADAPTERS["H-011"] = H011SizeAdapter()


class AlphaEngine:
    def __init__(self):
        self.reg = registry.connect_registry()

    def validated_sources(self) -> pd.DataFrame:
        """Hypotheses the engine is allowed to speak from."""
        return pd.read_sql(
            "SELECT hypothesis_id, description, resolved_at FROM hypotheses "
            "WHERE status = 'confirmed' AND frozen = 0", self.reg)

    def pipeline(self) -> pd.DataFrame:
        return pd.read_sql(
            "SELECT h.hypothesis_id, h.status, h.frozen, "
            "  (SELECT COUNT(*) FROM hypothesis_experiments he "
            "   WHERE he.hypothesis_id = h.hypothesis_id) AS n_experiments, "
            "  substr(h.description, 1, 70) AS description "
            "FROM hypotheses h ORDER BY h.hypothesis_id", self.reg)

    def recommendations(self) -> list[Recommendation]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        sources = self.validated_sources()
        recs: list[Recommendation] = []
        for _, src in sources.iterrows():
            adapter = MODEL_ADAPTERS.get(src.hypothesis_id)
            if adapter is None:
                continue  # confirmed but not yet wired: surfaced in report()
            recs.extend(adapter.generate(as_of=now))
        if not recs:
            recs.append(Recommendation(
                as_of=now, instrument="PORTFOLIO", action="no_position",
                size_pct_nav=None, horizon=None, expected_excess_ann=None,
                expected_max_drawdown=None, confidence_rating="Inconclusive",
                rationale=self._no_position_rationale(sources),
                hypothesis_id=None,
                caveats=("An engine with no validated edge that still trades "
                         "is broken. Default posture: benchmark/cash per "
                         "mandate, outside this engine's scope.",)))
        return recs

    def _no_position_rationale(self, sources: pd.DataFrame) -> str:
        pipe = self.pipeline()
        parts = [f"Validated alpha sources: {len(sources)}."]
        for _, h in pipe.iterrows():
            state = ("FROZEN/" if h.frozen else "") + h.status
            parts.append(f"{h.hypothesis_id} [{state}] {h.description}")
        parts.append("No hypothesis has been confirmed on evidence-grade data; "
                     "therefore no buy/sell/allocation is recommended.")
        return " | ".join(parts)

    def report(self) -> str:
        recs = self.recommendations()
        sources = self.validated_sources()
        pipe = self.pipeline()
        n_rejected = int((pipe.status == "rejected").sum())
        n_queue = int((pipe.status == "untested").sum())
        hyp = pd.read_sql("SELECT created_at, resolved_at FROM hypotheses", self.reg)
        created = pd.to_datetime(hyp.created_at).dt.tz_localize(None)
        this_q = pd.Timestamp.now(tz="UTC").tz_localize(None).to_period("Q")
        gen_rate = int((created.dt.to_period("Q") == this_q).sum())
        resolved = hyp.dropna(subset=["resolved_at"])
        ttv = ((pd.to_datetime(resolved.resolved_at)
                - pd.to_datetime(resolved.created_at)).dt.days.median()
               if len(resolved) else None)
        try:
            from . import db as _db
            mcon = _db.connect()
            n_datasets = mcon.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT source_id FROM index_levels "
                "WHERE confidence > 0 UNION SELECT DISTINCT source_id FROM events "
                "WHERE confidence > 0 UNION SELECT DISTINCT source_id FROM "
                "macro_series WHERE confidence > 0)").fetchone()[0]
            mcon.close()
        except Exception:  # noqa: BLE001 — metric is best-effort
            n_datasets = "n/a"
        lines = ["=" * 72,
                 f"FUND ALPHA — ENGINE STATUS  {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
                 "=" * 72,
                 f"SUCCESS METRICS",
                 f"  independent validated alpha sources : {len(sources)}",
                 f"  discovery throughput                : {n_rejected} verdicts, "
                 f"{n_queue} candidates queued",
                 f"  reusable evidence-grade datasets    : {n_datasets}",
                 f"  median time-to-verdict (days)       : {ttv if ttv is not None else 'n/a'}",
                 f"  hypothesis generation rate (this qtr): {gen_rate}",
                 f"models wired to engine  : {len(MODEL_ADAPTERS)}",
                 f"recommendations         : "
                 f"{sum(1 for r in recs if r.action != 'no_position')} actionable",
                 "", "--- hypothesis pipeline ---",
                 pipe.to_string(index=False),
                 "", "--- recommendations ---"]
        for r in recs:
            lines.append(json.dumps(asdict(r), indent=2, default=str))
        lines += ["", "--- what would change this output ---",
                  "1. H-003 Sprint 1 data (MPC history, CBN circulars, Brent) ->",
                  "   first event-model candidates enter validation.",
                  "2. Any hypothesis reaching 'confirmed' on evidence-grade data",
                  "   after the full gauntlet -> its adapter is wired and the",
                  "   engine begins emitting positions with provenance.",
                  "3. Acquisition core datasets -> more model families testable",
                  "   (see docs/HYPOTHESIS_FAMILY_MAP.md)."]
        return "\n".join(lines)
