"""Provider interface — the Data Abstraction Layer.

Every data source (NGX website, user CSVs, Investing.com, TradingView, a
future premium vendor) is a DataProvider. The research engine never talks to
a provider directly: providers hand DataFrames matching the contracts in
``ngxrot.contracts`` to the ingestion pipeline, which validates, stamps
lineage + confidence, and writes to the PIT database. Swapping or adding a
vendor therefore never touches the research engine.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field

import pandas as pd

DATASETS = frozenset(
    {"index_levels", "equity_prices", "corporate_actions", "index_membership", "events"}
)


class Unsupported(NotImplementedError):
    """Raised when a provider is asked for a dataset it does not carry."""


@dataclass(frozen=True)
class ProviderInfo:
    name: str                    # unique, stable — becomes sources.name
    kind: str                    # matches sources.kind CHECK constraint
    reliability: str             # 'primary' | 'secondary' | 'unverified' | 'synthetic'
    base_confidence: float       # default confidence stamped on rows (0..1)
    url_template: str | None = None
    notes: str = ""
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        unknown = self.capabilities - DATASETS
        if unknown:
            raise ValueError(f"unknown capabilities: {unknown}")
        if not (0.0 <= self.base_confidence <= 1.0):
            raise ValueError("base_confidence must be in [0,1]")


class DataProvider(ABC):
    """Subclasses set ``info`` and override the fetch_* they support.

    Each fetch_* returns a DataFrame matching the corresponding contract in
    ``ngxrot.contracts`` (extra columns are ignored by ingestion). Providers
    must NOT write to the database themselves.
    """

    info: ProviderInfo

    def fetch_index_levels(self, index_codes: list[str], start: str, end: str) -> pd.DataFrame:
        raise Unsupported(f"{self.info.name} does not provide index_levels")

    def fetch_equity_prices(self, tickers: list[str], start: str, end: str) -> pd.DataFrame:
        raise Unsupported(f"{self.info.name} does not provide equity_prices")

    def fetch_corporate_actions(self, tickers: list[str] | None = None) -> pd.DataFrame:
        raise Unsupported(f"{self.info.name} does not provide corporate_actions")

    def fetch_index_membership(self, index_codes: list[str] | None = None) -> pd.DataFrame:
        raise Unsupported(f"{self.info.name} does not provide index_membership")

    def fetch_events(self, start: str, end: str) -> pd.DataFrame:
        raise Unsupported(f"{self.info.name} does not provide events")

    def fetch(self, dataset: str, **kwargs) -> pd.DataFrame:
        """Uniform dispatch used by the ingestion pipeline."""
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset {dataset!r}")
        if dataset not in self.info.capabilities:
            raise Unsupported(f"{self.info.name} does not provide {dataset}")
        return getattr(self, f"fetch_{dataset}")(**kwargs)
