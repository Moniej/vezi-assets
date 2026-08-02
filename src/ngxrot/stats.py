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


# ---------------------------------------------------------------------------
# METH-001 (2026-08-02): cross-hypothesis statistical hardening.
# Pre-registered in docs/PREREG_METH-001_statistical_hardening.md BEFORE any
# real value below was computed. Additive only — nothing above this line
# was modified. Both functions report an existing test alongside a new,
# more conservative one; neither replaces excess_ttest/placebo_p_value,
# which remain the primary criteria per existing hypothesis convention.
# ---------------------------------------------------------------------------

_EULER_MASCHERONI = 0.5772156649015329


def newey_west_tstat(x: pd.Series, lag: int | None = None) -> dict:
    """HAC (Newey-West 1987) corrected one-sample t-test for mean(x) == 0.

    Corrects excess_ttest's i.i.d. assumption for serial correlation in
    the daily return series (real, not hypothetical here: a
    monthly/quarterly-rebalanced strategy's daily returns are
    autocorrelated within a holding period). Bartlett kernel; lag length
    defaults to the Newey & West (1994) automatic rule
    floor(4*(T/100)^(2/9)), never hand-tuned after seeing a result.
    """
    x = x.dropna()
    n = len(x)
    if n < 30:
        return {"t_stat": None, "p_value": None, "n_obs": n, "lag": None}
    if lag is None:
        lag = int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    xc = x - x.mean()
    gamma0 = float((xc * xc).sum()) / n
    v = gamma0
    for j in range(1, lag + 1):
        w = 1.0 - j / (lag + 1.0)
        gamma_j = float((xc[j:].values * xc[:-j].values).sum()) / n
        v += 2.0 * w * gamma_j
    var_mean = v / n
    if var_mean <= 0:
        return {"t_stat": None, "p_value": None, "n_obs": n, "lag": lag}
    t = float(x.mean() / math.sqrt(var_mean))
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return {"t_stat": round(t, 3), "p_value": round(p, 5), "n_obs": n, "lag": lag}


def _norm_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation,
    accurate to ~1.15e-9 — sufficient for a reporting-grade statistic)."""
    if not 0 < p < 1:
        raise ValueError("p must be in (0,1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def probabilistic_sharpe_ratio(sr_hat: float, sr_benchmark: float,
                               skew: float, kurtosis: float, n_obs: int) -> float:
    """PSR (Bailey & Lopez de Prado, 2012): P(true Sharpe > sr_benchmark)
    given an estimated Sharpe sr_hat over n_obs periods with the return
    series' own skewness and (regular, normal=3) kurtosis. sr_hat,
    sr_benchmark, skew, kurtosis must all be computed at the SAME return
    frequency (this platform uses daily throughout, per pre-registration)."""
    if n_obs < 2:
        raise ValueError("PSR requires at least 2 observations")
    denom = math.sqrt(max(1 - skew * sr_hat + ((kurtosis - 1) / 4.0) * sr_hat**2, 1e-12))
    z = (sr_hat - sr_benchmark) * math.sqrt(n_obs - 1) / denom
    return _norm_cdf(z)


def deflated_sharpe_ratio(trial_sharpes: list[float], focal_sharpe: float,
                          focal_skew: float, focal_kurtosis: float,
                          focal_n_obs: int) -> dict:
    """DSR (Bailey & Lopez de Prado, 2014). trial_sharpes: the daily Sharpe
    ratios of every independently-conceived, actually-executed hypothesis
    in the program (including the focal one), at the SAME frequency as
    focal_sharpe. Returns the expected-max-Sharpe-by-chance benchmark
    (sr_star) alongside the deflated probability, so both are visible —
    never just the final number.

    LIMITATION (disclosed every time this is reported, not just once):
    the extreme-value approximation behind sr_star assumes the N trials
    are independent. Hypotheses tested on the same market history and
    sharing signal ingredients are not fully independent — sr_star is a
    conservative-leaning but imperfect proxy, not an exact correction.
    """
    n = len(trial_sharpes)
    if n < 2:
        sr_star = 0.0  # no selection effect to correct for with <2 trials
    else:
        var_sr = float(pd.Series(trial_sharpes).var(ddof=1))
        sr_star = math.sqrt(max(var_sr, 0.0)) * (
            (1 - _EULER_MASCHERONI) * _norm_ppf(1 - 1.0 / n)
            + _EULER_MASCHERONI * _norm_ppf(1 - 1.0 / (n * math.e)))
    dsr = probabilistic_sharpe_ratio(focal_sharpe, sr_star, focal_skew,
                                     focal_kurtosis, focal_n_obs)
    return {"dsr": round(dsr, 5), "sr_star_chance_benchmark": round(sr_star, 5),
            "n_trials": n, "focal_sharpe": round(focal_sharpe, 5)}
