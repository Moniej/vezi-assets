"""Stage 24 -- Insider-Dealing Adversarial Diagnostic (2026-08-09).

Mechanism-discovery diagnostic ONLY. No hypothesis, no factor, no backtest,
no H-024. Builds on Stage 23's classification (reused/extended, not
redone from scratch) plus new PIT/aggregation/benchmark/cost/adversarial
logic. Every parameter below is frozen BEFORE any return is examined.

FROZEN PARAMETERS (fixed before execution, not touched after seeing results):
  - Classification: reuses Stage 23's exact vesting-marker list and
    PURCHASE/SALE keyword-dominance rule, unmodified.
  - Null-ticker resolution: a self-referential issuer-name whitelist built
    ONLY from rows in this same corpus that already carry a ticker (i.e. if
    "Nigerian Breweries Plc" already appears as the issuer name on rows
    ticked ticker='NB' elsewhere in the corpus, an exact-text match against
    that same issuer-name string on a null-ticker row resolves to 'NB').
    No external knowledge, no fuzzy filename matching. Anything not
    exactly matched this way stays quarantined.
  - Routine/automatic vs discretionary: deterministic keyword flag only
    (scheme/plan/vesting/ESOS/reinvestment keywords) -- vesting notices
    were already excluded at classification; this is a SEPARATE, narrower
    flag for schemes mentioned within otherwise-classified PURCHASE/SALE
    filings. No inference of intent beyond explicit scheme-name text.
  - Event aggregation window: (insider_name, ticker, transaction_type)
    collapsed within the SAME CALENDAR MONTH of filing_date into one event,
    using the LAST filing_date in that group as the event's disclosure
    date (conservative -- latest, not earliest, public confirmation).
    Chosen because Stage 23 found repeated same-insider filings clustered
    within days-to-weeks of each other; one calendar month is a round,
    pre-declared aggregation window, not tuned to the data.
  - PIT boundary: eligible_from = first equity_prices trade_date STRICTLY
    AFTER filing_date, per the platform's existing PIT convention (Stage
    14 Sec.14E: eligible_from strictly after knowledge_timestamp). No
    same-session eligibility assumed.
  - Horizons (trading sessions after eligible_from): 5, 10, 20, 40, 60.
    60 matches H-020's own frozen holding-period precedent; the others are
    round, conventional multiples, not chosen from a grid.
  - Benchmark: NGXASI index level series (index_levels table), same choice
    and same justification as Stage 21C (EW-IRU would require running
    portfolio-construction machinery).
  - Cost gate: costs.side_rates() against the live cost_schedule table,
    unmodified -- identical method used in Stage 21C.
  - Size control: market_cap_panel.csv market_cap_nm, PIT-matched via
    merge_asof backward within 30 days of the event's run_start/eligible
    date -- identical convention to Stage 21B/21C.

  PYTHONPATH=src python scripts/stage24_insider_dealing_diagnostic.py
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from stage23_insider_dealing_pilot import (  # noqa: E402
    VESTING_MARKERS, load_text, classify_and_extract,
)
from ngxrot import costs  # noqa: E402

OUT = ROOT / "data" / "staging" / "stage24"
OUT.mkdir(parents=True, exist_ok=True)

HORIZONS = [5, 10, 20, 40, 60]
SCHEME_MARKERS = [
    r"employee share (?:scheme|ownership)", r"\bESOS\b", r"share (?:incentive|purchase) plan",
    r"dividend reinvestment", r"scrip dividend", r"share option scheme",
]


# ---------------------------------------------------------------------------
# Step 1-2: classification + null-ticker resolution
# ---------------------------------------------------------------------------

def build_classified_corpus(con: sqlite3.Connection) -> pd.DataFrame:
    docs = con.execute(
        "SELECT doc_id, ticker, filing_date, source_url FROM documents WHERE doc_type='dealing' ORDER BY filing_date"
    ).fetchall()
    records = []
    for doc_id, ticker, filing_date, source_url in docs:
        text = load_text(doc_id)
        rec = classify_and_extract(doc_id, ticker, text)
        rec["filing_date"] = filing_date
        rec["source_url"] = source_url
        rec["text"] = text
        records.append(rec)
    return pd.DataFrame(records)


def resolve_null_tickers_self_referential(df: pd.DataFrame) -> pd.DataFrame:
    """Build issuer-name -> ticker whitelist ONLY from rows that already have
    a ticker, then exact-match null-ticker rows' filing-stated issuer name
    against it. Deterministic, self-referential, no external knowledge."""
    def issuer_name(text: str) -> str | None:
        m = re.search(r"Details of the issuer", text, re.IGNORECASE)
        if not m:
            return None
        window = text[m.end():m.end() + 200]
        nm = re.search(r"Name\s*\n*\s*(?:a\)\s*)?\n*\s*([A-Z][A-Za-z0-9 &\.\-']{3,70})", window)
        return re.sub(r"\s+", " ", nm.group(1)).strip().upper() if nm else None

    df["issuer_name_from_text"] = df["text"].apply(issuer_name)

    whitelist = {}
    ticked = df[df["ticker"].notna()]
    for _, row in ticked.iterrows():
        nm = row["issuer_name_from_text"]
        if nm:
            whitelist.setdefault(nm, set()).add(row["ticker"])
    # keep only unambiguous mappings (one ticker per issuer name)
    whitelist = {k: list(v)[0] for k, v in whitelist.items() if len(v) == 1}

    df["ticker_resolved"] = df["ticker"]
    df["resolution_method"] = np.where(df["ticker"].notna(), "already_present", "unresolved")
    for idx, row in df[df["ticker"].isna()].iterrows():
        nm = row["issuer_name_from_text"]
        if nm and nm in whitelist:
            df.at[idx, "ticker_resolved"] = whitelist[nm]
            df.at[idx, "resolution_method"] = "self_referential_issuer_name_match"
    return df


# ---------------------------------------------------------------------------
# Step 5: routine/scheme flag (narrower than vesting exclusion)
# ---------------------------------------------------------------------------

def flag_scheme(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in SCHEME_MARKERS)


# ---------------------------------------------------------------------------
# Step 6: aggregation
# ---------------------------------------------------------------------------

def aggregate_events(genuine: pd.DataFrame) -> pd.DataFrame:
    genuine = genuine.copy()
    genuine["filing_date"] = pd.to_datetime(genuine["filing_date"])
    genuine["month"] = genuine["filing_date"].dt.to_period("M")
    grp_cols = ["ticker_resolved", "insider_name", "transaction_type", "month"]
    agg = genuine.groupby(grp_cols, dropna=False).agg(
        n_filings=("doc_id", "count"),
        doc_ids=("doc_id", list),
        event_disclosure_date=("filing_date", "max"),
        any_scheme_flag=("scheme_flag", "any"),
    ).reset_index()
    return agg


# ---------------------------------------------------------------------------
# Step 7-10: PIT eligible_from, benchmark-relative returns at frozen horizons
# ---------------------------------------------------------------------------

def load_prices(con) -> pd.DataFrame:
    df = pd.read_sql("SELECT ticker, trade_date, close, volume FROM equity_prices ORDER BY ticker, trade_date", con)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def load_benchmark(con) -> pd.Series:
    df = pd.read_sql("SELECT trade_date, close_value FROM index_levels WHERE index_code='NGXASI' ORDER BY trade_date", con)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.set_index("trade_date")["close_value"]


def compute_event_returns(events: pd.DataFrame, px: pd.DataFrame, bench: pd.Series) -> pd.DataFrame:
    px_by_ticker = {t: g.sort_values("trade_date").reset_index(drop=True) for t, g in px.groupby("ticker")}
    rows = []
    for _, ev in events.iterrows():
        ticker = ev["ticker_resolved"]
        if ticker not in px_by_ticker or pd.isna(ticker):
            continue
        g = px_by_ticker[ticker]
        after = g[g["trade_date"] > ev["event_disclosure_date"]]
        if after.empty:
            continue
        eligible_pos = after.index[0]
        eligible_date = g["trade_date"].iloc[eligible_pos]
        eligible_close = g["close"].iloc[eligible_pos]
        row = dict(ev)
        row["eligible_from"] = eligible_date
        row["eligible_close"] = eligible_close
        for k in HORIZONS:
            idx_k = eligible_pos + k
            if idx_k < len(g):
                end_date = g["trade_date"].iloc[idx_k]
                end_close = g["close"].iloc[idx_k]
                row[f"raw_ret_{k}"] = end_close / eligible_close - 1.0
                row[f"end_date_{k}"] = end_date
                b0, b1 = bench.asof(eligible_date), bench.asof(end_date)
                row[f"bench_ret_{k}"] = (b1 / b0 - 1.0) if pd.notna(b0) and pd.notna(b1) and b0 else np.nan
                row[f"excess_ret_{k}"] = row[f"raw_ret_{k}"] - row[f"bench_ret_{k}"]
                row[f"censored_{k}"] = False
            else:
                row[f"raw_ret_{k}"] = np.nan
                row[f"excess_ret_{k}"] = np.nan
                row[f"censored_{k}"] = True
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")

    print("=== Steps 1-2: classification + null-ticker resolution ===")
    df = build_classified_corpus(con)
    df = resolve_null_tickers_self_referential(df)
    df.drop(columns=["text"]).to_csv(OUT / "all_filings_classified.csv", index=False)
    print(df["classification"].value_counts(dropna=False).to_string())
    null_before = df["ticker"].isna().sum()
    resolved_now = ((df["ticker"].isna()) & (df["resolution_method"] == "self_referential_issuer_name_match")).sum()
    print(f"\nnull_ticker_before={null_before}  resolved_via_self_referential_match={resolved_now}  "
          f"still_quarantined={null_before - resolved_now}")
    print(df[df["ticker"].isna()][["doc_id", "issuer_name_from_text", "ticker_resolved", "resolution_method"]].to_string())

    genuine = df[df["classification"].str.startswith("genuine", na=False)].copy()
    genuine = genuine[genuine["ticker_resolved"] != "UNKNOWN"]
    print(f"\ngenuine transactions with a resolved ticker: {len(genuine)}")
    genuine["scheme_flag"] = genuine["text"].apply(flag_scheme)
    print(f"scheme-flagged (routine, within otherwise-genuine filings): {genuine['scheme_flag'].sum()}")

    print("\n=== Step 3: concentration (pre-aggregation, i.e. raw filing level) ===")
    print("by ticker:")
    print(genuine["ticker_resolved"].value_counts().to_string())
    print("\nby insider_name (top 10):")
    print(genuine["insider_name"].value_counts().head(10).to_string())
    n_with_shares = (genuine["shares"] != "UNKNOWN").sum()
    n_with_consid = (genuine["consideration"] != "UNKNOWN").sum()
    print(f"\nfilings with usable shares field: {n_with_shares}/{len(genuine)}")
    print(f"filings with usable consideration (value) field: {n_with_consid}/{len(genuine)}")

    print("\n=== Step 4+6: PURCHASE/SALE split, then event aggregation ===")
    print(genuine["transaction_type"].value_counts().to_string())
    events = aggregate_events(genuine)
    events.to_csv(OUT / "aggregated_events.csv", index=False)
    print(f"raw genuine filings: {len(genuine)}  ->  aggregated events (insider x ticker x direction x month): {len(events)}")
    print(f"scheme-flagged events (any filing in group scheme-flagged): {events['any_scheme_flag'].sum()}")
    print("\nevents by ticker:")
    print(events["ticker_resolved"].value_counts().to_string())
    print("\nevents by direction:")
    print(events["transaction_type"].value_counts().to_string())
    top3 = events["ticker_resolved"].value_counts().head(3).sum()
    top5 = events["ticker_resolved"].value_counts().head(5).sum()
    print(f"top3_ticker_share={top3}/{len(events)}={top3/len(events):.1%}")
    print(f"top5_ticker_share={top5}/{len(events)}={top5/len(events):.1%}")
    print(f"unique tickers: {events['ticker_resolved'].nunique()}  unique insiders: {events['insider_name'].nunique()}")

    print("\n=== Step 7-10: PIT eligible_from + benchmark-relative returns ===")
    px = load_prices(con)
    bench = load_benchmark(con)
    er = compute_event_returns(events, px, bench)
    er.to_csv(OUT / "event_returns.csv", index=False)
    print(f"events with usable price data: {len(er)}")

    for direction in ["PURCHASE", "SALE"]:
        sub = er[er["transaction_type"] == direction]
        print(f"\n--- {direction} (n={len(sub)}) ---")
        for k in HORIZONS:
            u = sub[~sub[f"censored_{k}"]]
            if len(u) < 3:
                print(f"  k={k}: insufficient uncensored events ({len(u)})")
                continue
            mean_ex = u[f"excess_ret_{k}"].mean()
            med_ex = u[f"excess_ret_{k}"].median()
            se = u[f"excess_ret_{k}"].std() / np.sqrt(len(u)) if len(u) > 1 else np.nan
            t = mean_ex / se if se and se > 0 else np.nan
            pct_pos = (u[f"raw_ret_{k}"] > 0).mean()
            print(f"  k={k}: n={len(u)}  mean_excess={mean_ex:+.4%}  median_excess={med_ex:+.4%}  "
                  f"t~{t:.2f}  pct_positive_raw={pct_pos:.1%}")

    print("\n=== Step 8: H-011 independence -- structural + correlational ===")
    mcap = pd.read_csv(ROOT / "data" / "reference" / "market_cap_panel.csv")
    mcap["trade_date"] = pd.to_datetime(mcap["trade_date"]).rename("event_disclosure_date")
    mcap_sorted = mcap.rename(columns={"trade_date": "event_disclosure_date", "symbol": "ticker_resolved"}).sort_values("event_disclosure_date")
    er_sorted = er.sort_values("event_disclosure_date")
    er_m = pd.merge_asof(er_sorted, mcap_sorted, on="event_disclosure_date", by="ticker_resolved",
                          direction="backward", tolerance=pd.Timedelta(days=45))
    er_m.to_csv(OUT / "event_returns_with_mcap.csv", index=False)
    for k in [10, 20]:
        d = er_m.dropna(subset=[f"excess_ret_{k}", "market_cap_nm"])
        if len(d) > 5:
            print(f"Spearman(excess_ret_{k}, market_cap_nm) = {d[f'excess_ret_{k}'].corr(d['market_cap_nm'], method='spearman'):.4f}  n={len(d)}")
    er_m["size_tercile"] = pd.qcut(er_m["market_cap_nm"], 3, labels=["Small", "Mid", "Large"], duplicates="drop") if er_m["market_cap_nm"].notna().sum() >= 9 else np.nan
    print("\nby size tercile, k=20:")
    print(er_m.groupby("size_tercile", observed=True)["excess_ret_20"].agg(["mean", "median", "count"]).to_string())

    print("\n=== Step 12: adversarial decomposition ===")
    print("-- issuer concentration: leave-top-3-out --")
    top3_tickers = events["ticker_resolved"].value_counts().head(3).index.tolist()
    er_excl = er[~er["ticker_resolved"].isin(top3_tickers)]
    for k in [10, 20]:
        u = er_excl[~er_excl[f"censored_{k}"]]
        print(f"  ex-top3 (excluded={top3_tickers}) k={k}: n={len(u)}  mean_excess={u[f'excess_ret_{k}'].mean():+.4%}")

    print("\n-- extreme-observation sensitivity (winsorized at 5%/95%, k=20) --")
    u20 = er[~er["censored_20"]].copy()
    lo, hi = u20["excess_ret_20"].quantile([0.05, 0.95])
    u20["excess_ret_20_wz"] = u20["excess_ret_20"].clip(lo, hi)
    print(f"  raw mean={u20['excess_ret_20'].mean():+.4%}  winsorized mean={u20['excess_ret_20_wz'].mean():+.4%}")

    print("\n-- repeated-insider sensitivity: raw filings (non-aggregated) vs aggregated events, k=20 --")
    genuine_g = genuine.copy()
    genuine_g["filing_date"] = pd.to_datetime(genuine_g["filing_date"])
    raw_er = compute_event_returns(
        genuine_g.rename(columns={"filing_date": "event_disclosure_date"}), px, bench
    )
    if len(raw_er) and "censored_20" in raw_er:
        u_raw = raw_er[~raw_er["censored_20"]]
        print(f"  raw filings (n={len(u_raw)}): mean_excess_20={u_raw['excess_ret_20'].mean():+.4%}")

    print("\n-- stale-price cross-check: are these tickers high-staleness names? (Stage 21 Part A) --")
    stage21_desc_path = ROOT / "data" / "staging" / "stage21" / "part_a_descriptives.csv"
    if stage21_desc_path.exists():
        s21 = pd.read_csv(stage21_desc_path)
        merged = events[["ticker_resolved"]].drop_duplicates().merge(
            s21[["ticker", "zero_return_freq"]], left_on="ticker_resolved", right_on="ticker", how="left")
        print(merged.to_string(index=False))
    else:
        print("  Stage 21 descriptives not found -- DATA GAP for this specific cross-check")

    print("\n-- corporate-action overlap check --")
    ca = pd.read_sql("SELECT ticker, action_type, declared_date, markdown_date FROM corporate_actions", con)
    ca["declared_date"] = pd.to_datetime(ca["declared_date"])
    overlap_count = 0
    for _, ev in er.iterrows():
        sub = ca[(ca["ticker"] == ev["ticker_resolved"]) &
                 (ca["declared_date"] >= ev["eligible_from"]) &
                 (ca["declared_date"] <= ev.get("end_date_20", ev["eligible_from"]))]
        if len(sub):
            overlap_count += 1
    print(f"  events with a corporate_actions row inside the [eligible_from, +20 sessions] window: {overlap_count}/{len(er)}")

    print("\n=== Step 11: cost/capacity gate ===")
    sch = pd.read_sql("SELECT * FROM cost_schedule", con)
    rates = costs.side_rates(sch)
    rt = rates["buy_rate"] + rates["sell_rate"]
    print(f"round_trip_cost={rt:.4%}")
    for direction in ["PURCHASE", "SALE"]:
        sub = er[er["transaction_type"] == direction]
        for k in HORIZONS:
            u = sub[~sub[f"censored_{k}"]]
            if len(u) < 3:
                continue
            mean_ex = u[f"excess_ret_{k}"].mean()
            med_ex = u[f"excess_ret_{k}"].median()
            survives_mean = "YES" if abs(mean_ex) > rt else "NO"
            survives_med = "YES" if abs(med_ex) > rt else "NO"
            print(f"  {direction} k={k}: mean_excess={mean_ex:+.4%} (clears_cost={survives_mean})  "
                  f"median_excess={med_ex:+.4%} (clears_cost={survives_med})")


if __name__ == "__main__":
    main()
