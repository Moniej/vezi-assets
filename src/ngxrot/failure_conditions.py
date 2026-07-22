"""Strategy failure conditions: automatic hypothesis-rejection triggers.

Two categories, per the research mandate:
  signal_quality — a trigger means the SIGNAL is not real/robust. These
    drive hypothesis_reject_recommended.
  scalability    — a trigger means the strategy cannot absorb the configured
    AUM. This does NOT invalidate the signal: genuine alpha capped at small
    AUM is a finding, not a failure. Triggers set scalability_limited and a
    max-deployable-AUM estimate instead of a rejection.

Each condition returns triggered = True / False / None (not evaluable yet).
"""

from __future__ import annotations

CATEGORY = {
    "capacity_below_minimum": "scalability",
    "cost_drag_eliminates_excess": "signal_quality",   # at capacity-feasible AUM
    "single_sector_dependency": "signal_quality",
    "placebo_performs_similarly": "signal_quality",
    "oos_performance_collapses": "signal_quality",
    "single_regime_dependency": "signal_quality",
}


def evaluate(fc_cfg: dict, metrics: dict, capacity: dict,
             sector_contribution: dict, phase4: dict | None = None) -> dict:
    """``phase4`` (optional) supplies placebo/oos/regime evidence once known:
    {placebo_p, oos_sharpe, is_sharpe, regime_excess: {name: excess}}."""
    out = {}

    min_cap = fc_cfg.get("min_median_capacity_ngn", 0.0)
    med = capacity.get("median_capacity_ngn")
    out["capacity_below_minimum"] = {
        "triggered": (med is not None and med < min_cap) if min_cap else False,
        "evidence": (f"median capacity {med:,.0f} NGN vs mandate {min_cap:,.0f}; "
                     f"signal validity unaffected — deployable AUM is capped near "
                     f"the median capacity figure"
                     if med is not None else "no capacity records"),
    }

    g, n = metrics.get("gross_ann_return"), metrics.get("ann_return")
    b = metrics.get("ann_return_benchmark")
    triggered = None
    if None not in (g, n, b):
        triggered = (g - b > 0) and (n - b <= 0)
    out["cost_drag_eliminates_excess"] = {
        "triggered": triggered,
        "evidence": f"gross excess {g - b:+.2%}, net excess {n - b:+.2%}"
                    if triggered is not None else "metrics unavailable",
    }

    max_share = fc_cfg.get("max_single_sector_share", 1.0)
    pos = {k: v for k, v in sector_contribution.items() if v > 0}
    if pos and sum(pos.values()) > 0:
        top_sec = max(pos, key=pos.get)
        share = pos[top_sec] / sum(pos.values())
        out["single_sector_dependency"] = {
            "triggered": share > max_share,
            "evidence": f"{top_sec} contributes {share:.0%} of positive return "
                        f"(limit {max_share:.0%})",
        }
    else:
        out["single_sector_dependency"] = {
            "triggered": None, "evidence": "no positive sector contributions"}

    p4 = phase4 or {}
    alpha = fc_cfg.get("placebo_alpha", 0.05)
    pp = p4.get("placebo_p")
    out["placebo_performs_similarly"] = {
        "triggered": (pp > alpha) if pp is not None else None,
        "evidence": (f"placebo p={pp:.3f} (alpha={alpha}): real strategy "
                     f"{'NOT distinguishable' if pp > alpha else 'distinguishable'} "
                     f"from shuffled sector labels" if pp is not None
                     else "not evaluable until Phase 4 placebo run"),
    }

    oos_s, is_s = p4.get("oos_sharpe"), p4.get("is_sharpe")
    keep = fc_cfg.get("min_oos_sharpe_retention", 0.25)
    if None not in (oos_s, is_s) and is_s:
        trig = (oos_s < keep * is_s) or (oos_s < 0)
        ev = f"OOS Sharpe {oos_s:.2f} vs IS {is_s:.2f} (retention floor {keep:.0%})"
    else:
        trig, ev = None, "not evaluable until Phase 4 walk-forward"
    out["oos_performance_collapses"] = {"triggered": trig, "evidence": ev}

    regimes = p4.get("regime_excess") or {}
    max_reg = fc_cfg.get("max_single_regime_share", 1.0)
    pos_r = {k: v for k, v in regimes.items() if v > 0}
    if pos_r and sum(pos_r.values()) > 0 and len(regimes) >= 2:
        top_r = max(pos_r, key=pos_r.get)
        share_r = pos_r[top_r] / sum(pos_r.values())
        out["single_regime_dependency"] = {
            "triggered": share_r > max_reg,
            "evidence": f"regime '{top_r}' contributes {share_r:.0%} of positive "
                        f"excess (limit {max_reg:.0%}); per-regime excess: "
                        + ", ".join(f"{k}={v:+.1%}" for k, v in regimes.items()),
        }
    else:
        out["single_regime_dependency"] = {
            "triggered": None,
            "evidence": "not evaluable until Phase 4 walk-forward"
                        if not regimes else "no positive regime excess to attribute"}

    for k, v in out.items():
        v["category"] = CATEGORY[k]
    out["_signal_reject_recommended"] = any(
        v.get("triggered") is True for k, v in out.items()
        if not k.startswith("_") and CATEGORY[k] == "signal_quality")
    out["_scalability_limited"] = any(
        v.get("triggered") is True for k, v in out.items()
        if not k.startswith("_") and CATEGORY[k] == "scalability")
    out["_any_triggered"] = out["_signal_reject_recommended"]  # back-compat
    return out
