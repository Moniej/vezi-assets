"""Stage 27 -- Final data-completeness/adversarial audit for the insider-
PURCHASE track (2026-08-09). Integrates the 40 OCR-recovered filings
(hand-verified directly, 100% of the previously-unreadable subset -- see
data/staging/stage27/ocr_recovered_filings.csv) with the existing 123
native-text filings, then re-runs the Stage 24/26 diagnostics with the
exact frozen k=20 spec, benchmark, PIT rule, cost floor, and aggregation
method. No signal-rule changes. No new hypothesis, no backtest.

  PYTHONPATH=src python scripts/stage27_completeness_diagnostic.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from stage24_insider_dealing_diagnostic import (  # noqa: E402
    HORIZONS, load_prices, load_benchmark, aggregate_events, compute_event_returns,
)
from stage26_clustering_diagnostic import (  # noqa: E402
    cluster_robust_mean_test, exact_sign_permutation_test, COST,
)

OUT = ROOT / "data" / "staging" / "stage27"


def build_combined_corpus(con: sqlite3.Connection) -> pd.DataFrame:
    base = pd.read_csv(ROOT / "data" / "staging" / "stage24" / "all_filings_classified.csv")
    ocr = pd.read_csv(OUT / "ocr_recovered_filings.csv")

    # merge filing_date/source_url from the DB for the OCR-recovered rows
    docs = pd.read_sql("SELECT doc_id, filing_date, source_url FROM documents WHERE doc_type='dealing'", con)
    ocr = ocr.merge(docs, on="doc_id", how="left")

    # drop the 40 placeholder rows in `base` (they are all classification='unusable/ambiguous'
    # with no text -- the exact set this stage replaces) and splice in the hand-verified rows
    base_kept = base[~base["doc_id"].isin(ocr["doc_id"])].copy()
    for col in ["ticker_resolved", "resolution_method"]:
        if col not in ocr.columns:
            ocr[col] = ocr["ticker"] if col == "ticker_resolved" else "ocr_hand_verified"
    ocr["ticker_resolved"] = ocr["ticker"]
    ocr["resolution_method"] = "ocr_hand_verified"

    combined = pd.concat([base_kept, ocr], ignore_index=True, sort=False)
    return combined


def genuine_subset(df: pd.DataFrame, exclude_duplicates: bool = True) -> pd.DataFrame:
    g = df[df["classification"].astype(str).str.startswith("genuine", na=False)].copy()
    g = g[g["ticker_resolved"].notna() & (g["ticker_resolved"] != "UNKNOWN")]
    if exclude_duplicates:
        g = g[~((g["doc_id"] == 4322))]  # flagged duplicate of 4141's underlying transaction
    if "scheme_flag" not in g.columns:
        g["scheme_flag"] = False
    return g


def run_diagnostic(genuine: pd.DataFrame, px: pd.DataFrame, bench: pd.Series, label: str) -> pd.DataFrame:
    print(f"\n{'='*70}\n{label}  (n_filings={len(genuine)})\n{'='*70}")
    events = aggregate_events(genuine)
    print(f"aggregated events: {len(events)}  (unique tickers={events['ticker_resolved'].nunique()}, "
          f"unique insiders={events['insider_name'].nunique()})")

    er = compute_event_returns(events, px, bench)
    p20 = er[(er.transaction_type == "PURCHASE") & (~er.censored_20)]
    if len(p20) == 0:
        print("no usable PURCHASE events at k=20")
        return er

    print(f"\nPURCHASE k=20: n={len(p20)}  mean={p20.excess_ret_20.mean():+.4%}  "
          f"median={p20.excess_ret_20.median():+.4%}  pct_positive={(p20.raw_ret_20>0).mean():.1%}  "
          f"clears_cost(mean)={'YES' if p20.excess_ret_20.mean()>COST else 'NO'}")

    if p20.ticker_resolved.nunique() >= 3:
        tclus = cluster_robust_mean_test(p20.excess_ret_20.values, p20.ticker_resolved.values)
        print(f"ticker-clustered: se={tclus['se']:.4%}  t={tclus['t']:.2f}  G={tclus['n_clusters']}  "
              f"p={tclus['p']:.4f}  95% CI=[{tclus['ci_lo']:+.4%},{tclus['ci_hi']:+.4%}]")
        ticker_means = p20.groupby("ticker_resolved").excess_ret_20.mean().values
        perm_p = exact_sign_permutation_test(ticker_means) if len(ticker_means) <= 20 else np.nan
        print(f"exact sign-permutation p-value on {len(ticker_means)} ticker means: {perm_p:.4f}")
        print("equal-ticker-weighted mean:", f"{ticker_means.mean():+.4%}")

    print("\nhorizon table:")
    for k in HORIZONS:
        sub = er[(er.transaction_type == "PURCHASE") & (~er[f"censored_{k}"])]
        if len(sub):
            print(f"  k={k}: n={len(sub)}  mean={sub[f'excess_ret_{k}'].mean():+.4%}  "
                  f"median={sub[f'excess_ret_{k}'].median():+.4%}")

    print("\nleave-one-ticker-out (k=20):")
    for t in sorted(p20.ticker_resolved.unique()):
        excl = p20[p20.ticker_resolved != t]
        print(f"  ex-{t} (n_removed={ (p20.ticker_resolved==t).sum() }): n={len(excl)}  "
              f"mean={excl.excess_ret_20.mean():+.4%}  clears_cost={'YES' if excl.excess_ret_20.mean()>COST else 'NO'}")

    return er


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")
    combined = build_combined_corpus(con)
    combined.to_csv(OUT / "combined_all_filings.csv", index=False)

    print("=== Classification counts, combined 163-filing corpus ===")
    print(combined["classification"].value_counts(dropna=False).to_string())

    ocr = pd.read_csv(OUT / "ocr_recovered_filings.csv")
    print(f"\n=== Section: OCR-recovered composition (n=40) ===")
    print(ocr["classification"].value_counts(dropna=False).to_string())
    print("\nby ticker (recovered genuine only):")
    print(ocr[ocr["classification"].astype(str).str.startswith("genuine", na=False)]["ticker"].value_counts().to_string())
    print("\nby direction (recovered genuine only):")
    print(ocr[ocr["classification"].astype(str).str.startswith("genuine", na=False)]["transaction_type"].value_counts().to_string())

    px = load_prices(con)
    bench = load_benchmark(con)

    genuine_baseline = genuine_subset(combined[combined["resolution_method"] != "ocr_hand_verified"])
    # baseline = 123-native-text corpus only (i.e. Stage 24's original set, ticker-resolved)
    baseline_full = pd.read_csv(ROOT / "data" / "staging" / "stage24" / "all_filings_classified.csv")
    baseline_full["ticker_resolved"] = baseline_full["ticker_resolved"]
    genuine_baseline = genuine_subset(baseline_full)

    genuine_combined = genuine_subset(combined)

    run_diagnostic(genuine_baseline, px, bench, "WITHOUT OCR-recovered (Stage 24/25/26 baseline)")
    run_diagnostic(genuine_combined, px, bench, "WITH OCR-recovered (complete 163-filing corpus)")

    print("\n\n=== Section 8: systematic-difference test (OCR-recovered vs. already-readable) ===")
    ocr_genuine = ocr[ocr["classification"].astype(str).str.startswith("genuine", na=False)].copy()
    ocr_genuine["year"] = pd.to_datetime(ocr_genuine["transaction_date"]).dt.year
    orig_genuine = baseline_full[baseline_full["classification"].astype(str).str.startswith("genuine", na=False)].copy()

    print("recovered: n=", len(ocr_genuine), " purchase/sale split:",
          ocr_genuine["transaction_type"].value_counts().to_dict())
    print("original 123-corpus: n=", len(orig_genuine), " purchase/sale split:",
          orig_genuine["transaction_type"].value_counts().to_dict())
    print("\nrecovered filings' year distribution:")
    print(ocr_genuine["year"].value_counts().sort_index().to_string())
    print("\nrecovered filings' tickers already present in original corpus?",
          set(ocr_genuine["ticker"].unique()) - set(orig_genuine["ticker_resolved"].dropna().unique()), "(new tickers, empty set = all overlap)")
    print("\nmedian transaction value (shares*price), recovered:",
          (ocr_genuine["shares"] * ocr_genuine["price"]).median())


if __name__ == "__main__":
    main()
