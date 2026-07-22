"""SyntheticProvider: deterministic NGX-like data for engine development.

PURPOSE — develop and test Phases 2-4 (signal, costs, validation) end-to-end
before real data exists. Every row carries confidence 0.0: the schema-level
convention that this data may exercise the machinery but must NEVER feed a
research conclusion. Any report computed over confidence-0 data is a test of
the PLUMBING, not of the strategy.

Structure (loosely NGX-shaped, dates/magnitudes invented):
  - business-daily index levels 2016-01-04 .. 2026-06-30 for 8 sector indices
    + ASI, generated from a common market factor plus sector idiosyncratic
    noise, with three regimes: pre-2023 drift, 2023-24 devaluation shock
    (high vol, high common factor), 2025-26 bull with banking leadership;
  - 12 constituents across 4 sectors with size-tiered value_traded (so the
    Phase 3 ADTV constraint has something to bind on);
  - membership intervals incl. one mid-sample addition with a late
    announcement (PIT exercise);
  - corporate actions: annual bank dividends, one rights issue;
  - events: bi-monthly MPC decisions, one recapitalisation directive.

PLANTED FLAWS (Phase 3 diagnostics must catch these — do not fix them here):
  1. 'SYNINSA' has a -33% single-day drop with no corporate action recorded
     (simulates an unadjusted rights markdown) on 2024-05-15.
  2. 'SYNCONB' price is stale (unchanged) for 40 consecutive sessions from
     2023-02-01 (simulates NGX price-floor / no-trade stretches).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import DataProvider, ProviderInfo

SEED = 20260715

REGIMES = [  # (start, end, market annual drift, market annual vol)
    ("2016-01-04", "2022-12-30", 0.06, 0.13),
    ("2023-01-02", "2024-12-31", 0.45, 0.28),
    ("2025-01-02", "2026-06-30", 0.30, 0.20),
]

# sector: (beta to market, idio annual vol, extra annual drift per regime)
SECTORS = {
    "NGXBNK":      (1.15, 0.14, (0.00, 0.10, 0.35)),   # recap-era leadership
    "NGXINS":      (0.90, 0.22, (-0.04, 0.05, 0.20)),
    "NGXOILGAS":   (0.85, 0.18, (0.02, 0.30, -0.10)),  # strong in shock, fades
    "NGXINDUSTR":  (0.95, 0.12, (0.04, 0.05, 0.02)),
    "NGXCNSMRGDS": (1.00, 0.15, (-0.02, 0.12, 0.08)),
    "NGXPREMIUM":  (1.05, 0.10, (0.01, 0.08, 0.20)),
    "NGXPENSION":  (1.00, 0.08, (0.01, 0.06, 0.12)),
    "NGX30":       (1.00, 0.05, (0.01, 0.05, 0.08)),
}

TICKERS = {  # ticker: (sector index, start price, ADTV tier in NGN millions/day)
    "SYNBNKA": ("NGXBNK", 38.0, 900), "SYNBNKB": ("NGXBNK", 25.0, 700),
    "SYNBNKC": ("NGXBNK", 9.0, 150),
    "SYNINSA": ("NGXINS", 2.1, 15),  "SYNINSB": ("NGXINS", 0.9, 6),
    "SYNOILA": ("NGXOILGAS", 220.0, 400), "SYNOILB": ("NGXOILGAS", 31.0, 60),
    "SYNINDA": ("NGXINDUSTR", 285.0, 500), "SYNINDB": ("NGXINDUSTR", 95.0, 200),
    "SYNCONA": ("NGXCNSMRGDS", 55.0, 250), "SYNCONB": ("NGXCNSMRGDS", 14.0, 25),
    "SYNCONC": ("NGXCNSMRGDS", 4.5, 10),
}


def _bdays(start: str, end: str) -> pd.DatetimeIndex:
    return pd.bdate_range(start, end)


class SyntheticProvider(DataProvider):
    def __init__(self):
        self.info = ProviderInfo(
            name="synthetic_dev", kind="derived", reliability="synthetic",
            base_confidence=0.0,
            notes="deterministic synthetic data for engine development ONLY",
            capabilities=frozenset(
                {"index_levels", "equity_prices", "corporate_actions",
                 "index_membership", "events"}),
        )
        self._levels = self._build_levels()
        self._prices = self._build_prices()

    # ------------------------------------------------------------------
    def _daily_returns(self, rng, n_regime_days) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        mkt_parts, sec_parts = [], {s: [] for s in SECTORS}
        for r_i, ((_, _, drift, vol), n) in enumerate(zip(REGIMES, n_regime_days)):
            m = rng.normal(drift / 252, vol / np.sqrt(252), n)
            mkt_parts.append(m)
            for s, (beta, ivol, extras) in SECTORS.items():
                idio = rng.normal(extras[r_i] / 252, ivol / np.sqrt(252), n)
                sec_parts[s].append(beta * m + idio)
        return np.concatenate(mkt_parts), {s: np.concatenate(p) for s, p in sec_parts.items()}

    def _build_levels(self) -> pd.DataFrame:
        rng = np.random.default_rng(SEED)
        dates = pd.DatetimeIndex(np.concatenate([_bdays(a, b) for a, b, *_ in REGIMES]))
        n_per = [len(_bdays(a, b)) for a, b, *_ in REGIMES]
        mkt, sec = self._daily_returns(rng, n_per)

        frames = []
        for code, rets in {**sec, "NGXASI": mkt}.items():
            base = 1000.0 if code != "NGXASI" else 26000.0
            levels = base * np.exp(np.cumsum(rets))
            frames.append(pd.DataFrame({
                "index_code": code,
                "trade_date": dates.strftime("%Y-%m-%d"),
                "close_value": np.round(levels, 2),
            }))
        return pd.concat(frames, ignore_index=True)

    def _build_prices(self) -> pd.DataFrame:
        rng = np.random.default_rng(SEED + 1)
        lv = self._levels.pivot(index="trade_date", columns="index_code",
                                values="close_value")
        sec_ret = np.log(lv / lv.shift(1)).fillna(0.0)
        frames = []
        for tkr, (sector, p0, adtv_mm) in TICKERS.items():
            idio = rng.normal(0, 0.018, len(sec_ret))
            r = sec_ret[sector].to_numpy() + idio
            px = p0 * np.exp(np.cumsum(r))
            px = np.maximum(px, 0.20)  # NGX-style price floor
            value = np.maximum(
                rng.lognormal(np.log(adtv_mm * 1e6), 0.9, len(px)), 1e4)
            df = pd.DataFrame({
                "ticker": tkr,
                "trade_date": sec_ret.index,
                "close": np.round(px, 2),
                "volume": (value / px).astype(int),
                "value_traded": np.round(value, 0),
                "deals": np.maximum((value / (px * 5000)).astype(int), 1),
            })
            frames.append(df)
        out = pd.concat(frames, ignore_index=True)

        # PLANTED FLAW 1: unexplained -33% one-day drop (unadjusted markdown)
        m = (out.ticker == "SYNINSA") & (out.trade_date >= "2024-05-15")
        out.loc[m, "close"] = np.round(out.loc[m, "close"] * (2 / 3), 2)
        # PLANTED FLAW 2: 40-session stale price stretch
        m2 = (out.ticker == "SYNCONB") & (out.trade_date >= "2023-02-01")
        idx2 = out.index[m2][:40]
        out.loc[idx2, "close"] = out.loc[idx2[0], "close"]
        out.loc[idx2, ["volume", "value_traded", "deals"]] = 0
        return out

    # ------------------------------------------------------------------
    def fetch_index_levels(self, index_codes, start, end):
        df = self._levels
        df = df[df.index_code.isin(index_codes)] if index_codes else df
        return df[(df.trade_date >= start) & (df.trade_date <= end)].copy()

    def fetch_equity_prices(self, tickers, start, end):
        df = self._prices
        df = df[df.ticker.isin(tickers)] if tickers else df
        return df[(df.trade_date >= start) & (df.trade_date <= end)].copy()

    def fetch_corporate_actions(self, tickers=None):
        rows = []
        for tkr, (sector, p0, _) in TICKERS.items():
            if sector != "NGXBNK":
                continue
            for yr in range(2016, 2026):  # annual final dividend, ~5% yield-ish
                rows.append(dict(
                    ticker=tkr, action_type="dividend_cash",
                    declared_date=f"{yr}-03-10", qualification_date=f"{yr}-04-02",
                    markdown_date=f"{yr}-04-03", payment_date=f"{yr}-04-20",
                    dividend_per_share=round(p0 * 0.05 * (1.12 ** (yr - 2016)), 2)))
        rows.append(dict(  # rights issue, properly recorded (contrast to flaw 1)
            ticker="SYNBNKC", action_type="rights_issue",
            declared_date="2024-06-14", qualification_date="2024-07-19",
            markdown_date="2024-07-22", payment_date=None,
            ratio_new=1.0, ratio_old=2.0, rights_price=6.50))
        df = pd.DataFrame(rows)
        return df[df.ticker.isin(tickers)] if tickers else df

    def fetch_index_membership(self, index_codes=None):
        rows = [dict(index_code=s, ticker=t, effective_from="2016-01-04",
                     effective_to=None, announced_date="2015-12-15",
                     reason_in="index_launch")
                for t, (s, _, _) in TICKERS.items() if t != "SYNCONC"]
        rows.append(dict(  # mid-sample add, announced 11 days before effective
            index_code="NGXCNSMRGDS", ticker="SYNCONC",
            effective_from="2021-07-01", effective_to=None,
            announced_date="2021-06-20", reason_in="review_add"))
        df = pd.DataFrame(rows)
        return df[df.index_code.isin(index_codes)] if index_codes else df

    def fetch_events(self, start, end):
        rows = []
        rng = np.random.default_rng(SEED + 2)
        mpr = 11.5
        for d in pd.date_range("2016-01-26", "2026-05-26", freq="2MS"):
            d = d + pd.offsets.BDay(15)
            mpr = max(6.0, mpr + rng.choice([-0.5, 0, 0, 0.25, 0.5, 1.0]))
            rows.append(dict(event_type="mpc_decision",
                             announced_date=d.strftime("%Y-%m-%d"),
                             effective_date=d.strftime("%Y-%m-%d"),
                             scope="market", headline=f"MPC sets MPR {mpr:.2f}%",
                             outcome_numeric=round(mpr, 2),
                             structurally_impairing=0))
        rows.append(dict(event_type="recapitalisation_directive",
                         announced_date="2024-03-28", effective_date="2026-03-31",
                         scope="sector", index_code="NGXBNK",
                         headline="Synthetic: minimum capital directive for banks",
                         structurally_impairing=1))
        df = pd.DataFrame(rows)
        return df[(df.announced_date >= start) & (df.announced_date <= end)]
