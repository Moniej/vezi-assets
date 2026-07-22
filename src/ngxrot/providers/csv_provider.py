"""CSVProvider: ingest user-supplied CSV files through the standard DAL.

Directory layout (one folder per dataset, any number of CSVs inside):

    <root>/index_levels/*.csv        columns: index_code,trade_date,close_value
    <root>/equity_prices/*.csv       columns: ticker,trade_date,close[,open,high,low,
                                              volume,value_traded,deals]
    <root>/corporate_actions/*.csv   columns: ticker,action_type,markdown_date[,...]
    <root>/index_membership/*.csv    columns: index_code,ticker,effective_from[,...]
    <root>/events/*.csv              columns: event_type,announced_date,scope,headline[,...]

Dates ISO YYYY-MM-DD. Extra columns are ignored; malformed rows are rejected
(not repaired) by the ingestion pipeline and logged to data_quality_log.
Confidence defaults to 0.4 (manual/unverified) — pass a higher
confidence_override at ingest time only for files you have verified.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import DataProvider, ProviderInfo, Unsupported


class CSVProvider(DataProvider):
    def __init__(self, root: str | Path, name: str = "user_csv",
                 base_confidence: float = 0.4, kind: str = "manual_entry",
                 reliability: str = "unverified", notes: str = "user-supplied CSV files"):
        self.root = Path(root)
        caps = frozenset(
            d.name for d in self.root.iterdir()
            if d.is_dir() and any(d.glob("*.csv"))
        ) if self.root.exists() else frozenset()
        self.info = ProviderInfo(
            name=name, kind=kind, reliability=reliability,
            base_confidence=base_confidence,
            url_template=str(self.root),
            notes=notes,
            capabilities=caps,
        )

    def _load(self, dataset: str) -> pd.DataFrame:
        folder = self.root / dataset
        files = sorted(folder.glob("*.csv"))
        if not files:
            raise Unsupported(f"no CSVs under {folder}")
        return pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)

    @staticmethod
    def _window(df: pd.DataFrame, col: str, start: str, end: str) -> pd.DataFrame:
        return df[(df[col] >= start) & (df[col] <= end)]

    def fetch_index_levels(self, index_codes, start, end):
        df = self._load("index_levels")
        df = df[df["index_code"].isin(index_codes)] if index_codes else df
        return self._window(df, "trade_date", start, end)

    def fetch_equity_prices(self, tickers, start, end):
        df = self._load("equity_prices")
        df = df[df["ticker"].isin(tickers)] if tickers else df
        return self._window(df, "trade_date", start, end)

    def fetch_corporate_actions(self, tickers=None):
        df = self._load("corporate_actions")
        return df[df["ticker"].isin(tickers)] if tickers else df

    def fetch_index_membership(self, index_codes=None):
        df = self._load("index_membership")
        return df[df["index_code"].isin(index_codes)] if index_codes else df

    def fetch_events(self, start, end):
        return self._window(self._load("events"), "announced_date", start, end)
