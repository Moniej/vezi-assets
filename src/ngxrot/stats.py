"""Statistical testing: excess-return significance and multiple-testing control.

Two p-value sources, used together:
  - parametric: t-test on daily net excess returns (normal approximation for
    the p-value; n is in the thousands). Understates fat-tail risk — treat as
    the OPTIMISTIC bound.
  - nonparametric: placebo rank p-value (share of shuffled-label strategies
    beating the real one). Distribution-free; the primary test.

Multiple-testing control across the experiment family (every parameter cell
counts as a test): Holm (FWER, conservative) and Benjamini-Hochberg (FDR).
A cell only counts as significant if it survives the chosen correction.
"""

from __future__ import annotations

import math

import pandas as pd


def excess_ttest(net_returns: pd.Series, benchmark_returns: pd.Series) -> dict:
    ex = (net_returns - benchmark_returns).dropna()
    n = len(ex)
    if n < 30 or ex.std() == 0:
        return {"t_stat": None, "p_value": None, "n_obs": n}
    t = float(ex.mean() / (ex.std() / math.sqrt(n)))
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))   # two-sided, normal approx
    return {"t_stat": round(t, 3), "p_value": round(p, 5), "n_obs": n}


def holm(pvals: dict[str, float], alpha: float = 0.05) -> pd.DataFrame:
    """Holm-Bonferroni step-down: controls family-wise error rate."""
    items = sorted((p, k) for k, p in pvals.items() if p is not None)
    m = len(items)
    rows, rejected_so_far = [], True
    for i, (p, k) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        reject = rejected_so_far and (adj <= alpha)
        rejected_so_far = reject  # step-down: stop rejecting after first accept
        rows.append(dict(test=k, p_raw=p, p_holm=round(adj, 5),
                         significant_after_holm=reject))
    return pd.DataFrame(rows)


def benjamini_hochberg(pvals: dict[str, float], alpha: float = 0.05) -> pd.DataFrame:
    """BH step-up: controls false discovery rate (less conservative)."""
    items = sorted((p, k) for k, p in pvals.items() if p is not None)
    m = len(items)
    rows = []
    max_k = 0
    for i, (p, k) in enumerate(items, start=1):
        if p <= alpha * i / m:
            max_k = i
    adj_prev = 1.0
    for i, (p, k) in reversed(list(enumerate(items, start=1))):
        adj = min(adj_prev, p * m / i)
        adj_prev = adj
        rows.append(dict(test=k, p_raw=p, p_bh=round(adj, 5),
                         significant_after_bh=i <= max_k))
    return pd.DataFrame(rows[::-1])


def placebo_p_value(real_stat: float, placebo_stats: list[float]) -> float:
    """Rank p: P(placebo >= real) with add-one smoothing."""
    n_ge = sum(1 for s in placebo_stats if s >= real_stat)
    return (1 + n_ge) / (1 + len(placebo_stats))
