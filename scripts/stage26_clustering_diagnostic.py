"""Stage 26 -- Statistical-independence and clustering diagnostic for the
insider-PURCHASE k=20 signal (2026-08-09). Diagnostic only -- no hypothesis,
no factor, no backtest. Uses the exact frozen Stage 24/25 PURCHASE, k=20
dataset (event_returns_with_k3.csv), unmodified signal definition.

  PYTHONPATH=src python scripts/stage26_clustering_diagnostic.py
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "stage26"
OUT.mkdir(parents=True, exist_ok=True)

COST = 0.037915
HORIZONS = [3, 5, 10, 20, 40, 60]


def cluster_robust_mean_test(x: np.ndarray, cluster: np.ndarray) -> dict:
    """CR1 sandwich variance for a one-sample mean (intercept-only OLS),
    clustered by `cluster`, with the standard small-G finite-sample
    correction and t(G-1) reference distribution (Cameron-Miller 2015)."""
    n = len(x)
    xbar = x.mean()
    resid = x - xbar
    clusters = pd.unique(cluster)
    G = len(clusters)
    meat = 0.0
    for g in clusters:
        s_g = resid[cluster == g].sum()
        meat += s_g ** 2
    correction = (G / (G - 1)) * ((n - 1) / (n - 1))  # K=1 (intercept only)
    var = correction * meat / (n ** 2)
    se = np.sqrt(var)
    t = xbar / se if se > 0 else np.nan
    df = G - 1
    p = 2 * (1 - stats.t.cdf(abs(t), df)) if df > 0 else np.nan
    ci_lo, ci_hi = xbar - stats.t.ppf(0.975, df) * se, xbar + stats.t.ppf(0.975, df) * se
    return dict(point=xbar, se=se, t=t, df=df, p=p, ci_lo=ci_lo, ci_hi=ci_hi, n_clusters=G)


def two_way_cluster_se(x: np.ndarray, c1: np.ndarray, c2: np.ndarray) -> dict:
    """Cameron-Gelbach-Miller (2011) two-way cluster-robust variance:
    V = V(c1) + V(c2) - V(c1 x c2)."""
    n = len(x)
    xbar = x.mean()
    resid = x - xbar

    def meat_for(cluster_ids):
        m = 0.0
        for g in pd.unique(cluster_ids):
            s_g = resid[cluster_ids == g].sum()
            m += s_g ** 2
        return m

    c12 = pd.Series([f"{a}||{b}" for a, b in zip(c1, c2)])
    meat = meat_for(c1) + meat_for(c2) - meat_for(c12)
    var = meat / (n ** 2)
    se = np.sqrt(max(var, 0))
    t = xbar / se if se > 0 else np.nan
    G = min(len(pd.unique(c1)), len(pd.unique(c2)))
    df = G - 1
    p = 2 * (1 - stats.t.cdf(abs(t), df)) if df > 0 else np.nan
    return dict(point=xbar, se=se, t=t, df=df, p=p, n_clusters_min=G)


def exact_sign_permutation_test(cluster_means: np.ndarray) -> float:
    """Exact randomization p-value: under H0 the sign of each cluster's
    demeaned... here, sign of each cluster mean is equally likely +/-
    (symmetry-around-zero null), enumerate all 2^G sign patterns (feasible
    for G<=20)."""
    G = len(cluster_means)
    obs_stat = cluster_means.mean()
    abs_vals = np.abs(cluster_means)
    count_ge = 0
    total = 0
    for signs in itertools.product([1, -1], repeat=G):
        stat = np.mean(np.array(signs) * abs_vals)
        total += 1
        if abs(stat) >= abs(obs_stat) - 1e-12:
            count_ge += 1
    return count_ge / total


def main() -> None:
    er = pd.read_csv(ROOT / "data" / "staging" / "stage24" / "event_returns_with_k3.csv",
                      parse_dates=["event_disclosure_date"])
    p20 = er[(er.transaction_type == "PURCHASE") & (~er.censored_20)].copy()
    print(f"=== Baseline: n={len(p20)}  mean={p20.excess_ret_20.mean():+.4%}  "
          f"median={p20.excess_ret_20.median():+.4%} ===")

    print("\n=== Section 1: dependence structure ===")
    print(f"unique tickers: {p20.ticker_resolved.nunique()}")
    print(f"unique insiders: {p20.insider_name.nunique()}")
    print(f"insiders appearing >1x: {(p20.insider_name.value_counts() > 1).sum()} / {p20.insider_name.nunique()}")
    ixt = p20.groupby(["insider_name", "ticker_resolved"]).size()
    print(f"insider x ticker combos: {len(ixt)}, of which >1 obs: {(ixt > 1).sum()}")
    print(f"largest ticker cluster: UCAP, n={p20.ticker_resolved.value_counts().max()}")
    same_date = p20.event_disclosure_date.value_counts()
    print(f"largest same-disclosure-date cluster: {same_date.max()} events on {same_date.idxmax().date()}")
    same_date_detail = p20[p20.event_disclosure_date == same_date.idxmax()]
    print("  -- detail (likely single information episode, multiple insiders, same company action):")
    print(same_date_detail[["ticker_resolved", "insider_name", "excess_ret_20"]].to_string(index=False))

    print("\n=== Section 2: cluster-robust inference, k=20 ===")
    x = p20.excess_ret_20.values
    naive_se = p20.excess_ret_20.std() / np.sqrt(len(p20))
    naive_t = x.mean() / naive_se
    print(f"NAIVE (i.i.d. assumption): mean={x.mean():+.4%}  se={naive_se:.4%}  t={naive_t:.2f}  "
          f"df={len(p20)-1}  p={2*(1-stats.t.cdf(abs(naive_t), len(p20)-1)):.4f}")

    tclus = cluster_robust_mean_test(x, p20.ticker_resolved.values)
    print(f"\nTICKER-CLUSTERED (G={tclus['n_clusters']}): mean={tclus['point']:+.4%}  se={tclus['se']:.4%}  "
          f"t={tclus['t']:.2f}  df={tclus['df']}  p={tclus['p']:.4f}  "
          f"95% CI=[{tclus['ci_lo']:+.4%}, {tclus['ci_hi']:+.4%}]")

    iclus = cluster_robust_mean_test(x, p20.insider_name.values)
    print(f"\nINSIDER-CLUSTERED (G={iclus['n_clusters']}, {iclus['n_clusters']}/{len(p20)} obs -- "
          f"mostly singleton clusters, this is close to naive by construction):")
    print(f"  mean={iclus['point']:+.4%}  se={iclus['se']:.4%}  t={iclus['t']:.2f}  df={iclus['df']}  "
          f"p={iclus['p']:.4f}  95% CI=[{iclus['ci_lo']:+.4%}, {iclus['ci_hi']:+.4%}]")

    ixt_id = (p20.insider_name.astype(str) + "||" + p20.ticker_resolved.astype(str)).values
    tw = two_way_cluster_se(x, p20.ticker_resolved.values, ixt_id)
    print(f"\nTWO-WAY (ticker x insider-x-ticker): se={tw['se']:.4%}  t={tw['t']:.2f}  "
          f"min(G)={tw['n_clusters_min']}  p={tw['p']:.4f}")
    print("NOTE: G=10 ticker clusters is well below the conventional G>=30-40 comfort threshold for "
          "cluster-robust asymptotics -- t(9) reference and the exact permutation test below are used "
          "instead of trusting the asymptotic p-value at face value.")

    print("\n=== Section 2b: exact sign-permutation test on ticker-cluster means (G=10, exact, 2^10=1024) ===")
    ticker_means = p20.groupby("ticker_resolved").excess_ret_20.mean().values
    perm_p = exact_sign_permutation_test(ticker_means)
    print(f"cluster means: {np.round(ticker_means, 4)}")
    print(f"exact two-sided permutation p-value (H0: cluster means symmetric around 0): {perm_p:.4f}")

    print("\n=== Section 3: cluster-aware equal-weighted aggregation (one obs per ticker) ===")
    per_ticker = p20.groupby("ticker_resolved").agg(
        n=("excess_ret_20", "count"), mean_excess=("excess_ret_20", "mean"),
        median_excess=("excess_ret_20", "median")
    ).reset_index()
    per_ticker.to_csv(OUT / "ticker_cluster_means.csv", index=False)
    print(per_ticker.to_string(index=False))
    eq_mean = per_ticker.mean_excess.mean()
    eq_median = per_ticker.mean_excess.median()
    print(f"\nEQUAL-WEIGHTED across {len(per_ticker)} ticker clusters: mean-of-means={eq_mean:+.4%}  "
          f"median-of-means={eq_median:+.4%}")
    print(f"(for comparison, observation-weighted: mean={x.mean():+.4%}  median={np.median(x):+.4%})")
    print(f"clears {COST:.4%} cost floor (equal-weighted mean)? {'YES' if eq_mean > COST else 'NO'}")

    print("\n=== Section 4: distributional robustness ===")
    lo, hi = p20.excess_ret_20.quantile([0.05, 0.95])
    wz_mean = p20.excess_ret_20.clip(lo, hi).mean()
    pct_pos = (p20.raw_ret_20 > 0).mean()
    sorted_desc = p20.sort_values("excess_ret_20", ascending=False)
    top1_contrib = sorted_desc.excess_ret_20.iloc[0] / len(p20)
    top3_contrib = sorted_desc.excess_ret_20.iloc[:3].sum() / len(p20)
    print(f"mean={x.mean():+.4%}  median={np.median(x):+.4%}  winsorized_mean={wz_mean:+.4%}  "
          f"pct_positive={pct_pos:.1%}")
    print(f"top-1 observation's contribution to mean: {top1_contrib:+.4%} "
          f"({top1_contrib/x.mean():.1%} of total mean)")
    print(f"top-3 observations' contribution to mean: {top3_contrib:+.4%} "
          f"({top3_contrib/x.mean():.1%} of total mean)")

    print("\n=== Section 5: horizon check -- observation-weighted vs equal-ticker-weighted ===")
    for k in HORIZONS:
        sub = er[(er.transaction_type == "PURCHASE") & (~er[f"censored_{k}"])]
        obs_mean = sub[f"excess_ret_{k}"].mean()
        per_t = sub.groupby("ticker_resolved")[f"excess_ret_{k}"].mean()
        eqw_mean = per_t.mean()
        print(f"  k={k}: n={len(sub)}  obs-weighted mean={obs_mean:+.4%}  "
              f"equal-ticker-weighted mean={eqw_mean:+.4%} (over {len(per_t)} tickers)")

    print("\n=== Section 6: OCR gap quantification ===")
    all_df = pd.read_csv(ROOT / "data" / "staging" / "stage24" / "all_filings_classified.csv")
    total = len(all_df)
    genuine = (all_df["classification"].str.startswith("genuine", na=False)).sum()
    scanned = (all_df["classification"] == "unusable/ambiguous").sum()
    print(f"original filings: {total}")
    print(f"genuine (native-text) transactions: {genuine} ({genuine/total:.1%})")
    print(f"unusable/ambiguous (incl. 40 scanned/OCR-blocked): {scanned} ({scanned/total:.1%})")
    print("Of the unusable set, 40/163 (24.5% of the FULL corpus) are confirmed scanned-image PDFs "
          "(Stage 23) -- their tickers/directions are unknown without OCR, not run here. Cannot assume "
          "random distribution across tickers -- e.g. if these are concentrated in a filer with a "
          "systematically different disclosure pattern (paper filer, older/smaller issuer), concentration "
          "and/or effect estimates above could shift in either direction. This is a genuine, unresolved "
          "DATA GAP for the corpus's true concentration profile, not assumed benign.")


if __name__ == "__main__":
    main()
