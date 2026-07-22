"""Investment Committee memo generator.

Assembles the Phase 4 evidence bundle into a decision memo with a
recommendation from {Proceed, Continue Research, Reject, Insufficient
Evidence}. Capacity limits qualify a Proceed (AUM cap); they never cause a
Reject on their own — signal quality and scalability are scored separately.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2]
REPORTS = PKG_ROOT / "reports"


def _hypothesis_description(hypothesis_id: str | None) -> str:
    """Ledger description of the hypothesis under test. (Until 2026-07-22
    this section was HARDCODED to H-001's sector-momentum text — every memo
    from H-003 on misdescribed its hypothesis. Registry rows were always
    correct; only the memo prose was wrong.)"""
    if not hypothesis_id:
        return "(no hypothesis_id on this run)"
    try:
        from . import registry
        reg = registry.connect_registry()
        row = reg.execute("SELECT description FROM hypotheses WHERE "
                          "hypothesis_id = ?", (hypothesis_id,)).fetchone()
        reg.close()
        return row[0] if row else f"({hypothesis_id} not in ledger)"
    except Exception as e:  # noqa: BLE001
        return f"(ledger lookup failed: {type(e).__name__})"


def _recommend(bundle: dict) -> tuple[str, str]:
    flags = bundle["final_flags"]
    fc = bundle["failure_conditions"]
    rating = bundle["rating"]["rating"]
    scal = flags.get("scalability_limited", False)
    cap = bundle["final_metrics"].get("capacity", {})
    cap_note = (f" Deployable AUM is capped near the median per-rebalance "
                f"capacity of NGN {cap.get('median_capacity_ngn', 0):,.0f} "
                f"(single-session execution assumption)." if scal else "")

    if flags.get("synthetic_data"):
        return ("Insufficient Evidence",
                "All Phase 4 evidence was generated on synthetic (confidence-0) "
                "data. This run validates the MACHINERY, not the hypothesis. "
                "Rerun on evidence-grade data before any capital decision."
                + cap_note)
    if flags.get("hypothesis_reject_recommended"):
        failed = [k for k, v in fc.items() if not k.startswith("_")
                  and v.get("triggered") is True
                  and v.get("category") == "signal_quality"]
        return ("Reject", f"Signal-quality failure condition(s) triggered: "
                          f"{', '.join(failed)}.")
    if rating == "High":
        return ("Proceed", "Signal survived all failure conditions with High "
                           "confidence." + cap_note)
    if rating == "Moderate":
        return ("Continue Research", "Signal survived failure conditions but "
                "evidence is Moderate — extend history/regimes or tighten data "
                "quality before committing capital." + cap_note)
    return ("Insufficient Evidence",
            f"Confidence rating {rating}: evidence does not support a decision "
            f"either way." + cap_note)


def generate(bundle: dict) -> Path:
    REPORTS.mkdir(exist_ok=True)
    fc = bundle["failure_conditions"]
    plc = bundle["placebo"]
    cor = bundle["corrections"]
    cap = bundle["final_metrics"].get("capacity", {})
    att = bundle["attribution"]
    rec, why = _recommend(bundle)

    supporting, contradictory = [], []
    for k, v in fc.items():
        if k.startswith("_"):
            continue
        line = f"{k} [{v['category']}]: {v['evidence']}"
        if v["triggered"] is True:
            contradictory.append(line)
        elif v["triggered"] is False:
            supporting.append(line)
    if plc["placebo_p_value"] <= 0.05:
        supporting.append(
            f"placebo: real Sharpe {plc['real_sharpe']} vs shuffled-label mean "
            f"{plc['placebo_mean_sharpe']} (p={plc['placebo_p_value']}, "
            f"n={plc['n_iterations']})")
    else:
        contradictory.append(
            f"placebo: real strategy indistinguishable from shuffled labels "
            f"(p={plc['placebo_p_value']})")
    if cor["holm"] > 0:
        supporting.append(f"{cor['holm']}/{cor['n_tests']} parameter cells "
                          f"significant after Holm correction")
    else:
        contradictory.append(
            f"NO parameter cell survives Holm correction across "
            f"{cor['n_tests']} tests (raw significant: {cor['raw']})")

    # E16 (2026-07-22): pooled/multi-cohort hypotheses (xs_rank_pooled)
    # carry cohort diagnostics in final_metrics['attribution'] — distinct
    # from bundle['attribution'] above, which is phase4's PER-REGIME
    # attribution and exists for every hypothesis. This section is empty/
    # absent for every non-pooled hypothesis (H-006 through H-009, H-011).
    pooled_diag = bundle["final_metrics"].get("attribution")
    cohort_section = ""
    if pooled_diag and "cohort_return_correlation" in pooled_diag:
        corr = pooled_diag["cohort_return_correlation"]
        cohorts = sorted(corr)
        offdiag = [corr[a][b] for a in cohorts for b in cohorts if a != b]
        mean_corr = sum(offdiag) / len(offdiag) if offdiag else None
        turns = pooled_diag.get("cohort_ann_turnover_oneway", [])
        cohort_section = f"""
## Cohort diagnostics ({pooled_diag['n_cohorts']} cohorts, {pooled_diag['offset_months']}-month offset)

- Mean pairwise cohort return correlation: {f'{mean_corr:.3f}' if mean_corr is not None else 'n/a'}
  (measured on REAL data — not the synthetic rehearsal's figure; the
  independence of pooled cohorts must be checked here every run, never
  assumed from a prior rehearsal or a different hypothesis's result).
- Per-cohort annualized one-way turnover: {turns}
- Full correlation matrix: {corr}
"""

    regime_lines = []
    for name, a in att.items():
        contrib = a["sector_contribution"]
        top = max(contrib, key=contrib.get) if contrib else "n/a"
        regime_lines.append(
            f"- **{name}**: excess {a['excess']:+.1%}, Sharpe {a['sharpe']}, "
            f"top contributor {top} ({contrib.get(top, 0):+.2f} cum. gross); "
            f"median capacity NGN {a['capacity'].get('median_capacity_ngn', 0):,.0f}")

    md = f"""# Investment Committee Memo — {bundle['hypothesis_id']}

*Generated {date.today().isoformat()} by the Phase 4 validation pipeline.
All figures trace to immutable experiment records in `data/registry.sqlite`.*

## Recommendation: **{rec}**

{why}

## Hypothesis tested

{_hypothesis_description(bundle['hypothesis_id'])}

## Supporting evidence

{chr(10).join('- ' + s for s in supporting) or '- none'}

## Contradictory evidence

{chr(10).join('- ' + s for s in contradictory) or '- none'}

## Parameter robustness

{bundle['plateau']['frac_positive_excess']:.0%} of {bundle['plateau']['n_cells']}
parameter cells (lookback x top-N x rebalance) show positive net excess;
best-cell minus median-cell excess: {bundle['plateau']['best_minus_median']:+.1%}
(a small gap means a plateau, not a lucky spike).

## Regime attribution

{chr(10).join(regime_lines)}
{cohort_section}
## Data limitations

{chr(10).join('- ' + s for s in bundle['data_limitations'])}

## Capacity limitations

- Median per-rebalance capacity: NGN {cap.get('median_capacity_ngn', 0):,.0f}
  (worst: NGN {cap.get('worst_capacity_ngn', 0):,.0f} on {cap.get('worst_capacity_date', 'n/a')})
- Bottlenecks: {cap.get('bottleneck_constituents', {})}
- {cap.get('pct_legs_rejected', 0)}% of trade legs rejected at configured AUM
  of NGN {cap.get('configured_aum_ngn', 0):,.0f}
- Capacity limits SCALE, not signal validity — kept separate from the
  signal-quality verdict above.

## Implementation risks

{chr(10).join('- ' + s for s in bundle['implementation_risks'])}

## Confidence rating: **{bundle['rating']['rating']}** (score {bundle['rating']['score']}/12)

{chr(10).join('- ' + s for s in bundle['rating']['reasons'])}
"""
    variant = bundle.get("variant", "")
    path = REPORTS / (f"IC_memo_{bundle['hypothesis_id']}"
                      f"{'_' + variant if variant else ''}_"
                      f"{date.today().isoformat()}.md")
    path.write_text(md, encoding="utf-8")
    return path
