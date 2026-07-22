"""Dataset contracts: the standard shapes every provider must emit.

The research engine only ever sees these shapes. Providers (NGX scrape, CSV,
Investing.com, TradingView, a future premium vendor) adapt whatever they have
INTO these shapes; the ingestion pipeline validates against them before
anything touches the database.

A contract is: required columns, optional columns, and per-column validators.
Validators return an error string or None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

Validator = Callable[[pd.Series], "pd.Series | None"]  # returns bool mask of BAD rows


def _bad_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce").isna()


def _bad_positive(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return v.isna() | (v <= 0)


def _bad_nonneg_or_null(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return s.notna() & (v.isna() | (v < 0))


@dataclass(frozen=True)
class Contract:
    name: str
    required: dict[str, Validator]           # column -> bad-row detector
    optional: dict[str, Validator] = field(default_factory=dict)
    key: tuple[str, ...] = ()                # duplicate-detection key

    def all_columns(self) -> list[str]:
        return list(self.required) + list(self.optional)


INDEX_LEVELS = Contract(
    name="index_levels",
    required={
        "index_code": lambda s: s.isna() | (s.astype(str).str.strip() == ""),
        "trade_date": _bad_date,
        "close_value": _bad_positive,
    },
    key=("index_code", "trade_date"),
)

EQUITY_PRICES = Contract(
    name="equity_prices",
    required={
        "ticker": lambda s: s.isna() | (s.astype(str).str.strip() == ""),
        "trade_date": _bad_date,
        "close": _bad_positive,
    },
    optional={
        "open": _bad_nonneg_or_null,
        "high": _bad_nonneg_or_null,
        "low": _bad_nonneg_or_null,
        "volume": _bad_nonneg_or_null,
        "value_traded": _bad_nonneg_or_null,
        "deals": _bad_nonneg_or_null,
    },
    key=("ticker", "trade_date"),
)

CORPORATE_ACTIONS = Contract(
    name="corporate_actions",
    required={
        "ticker": lambda s: s.isna(),
        "action_type": lambda s: s.isna(),
        "markdown_date": _bad_date,
    },
    optional={
        "declared_date": lambda s: s.notna() & _bad_date(s),
        "qualification_date": lambda s: s.notna() & _bad_date(s),
        "payment_date": lambda s: s.notna() & _bad_date(s),
        "dividend_per_share": _bad_nonneg_or_null,
        "ratio_new": _bad_nonneg_or_null,
        "ratio_old": _bad_nonneg_or_null,
        "rights_price": _bad_nonneg_or_null,
        "details": lambda s: pd.Series(False, index=s.index),
    },
    key=("ticker", "action_type", "markdown_date"),
)

INDEX_MEMBERSHIP = Contract(
    name="index_membership",
    required={
        "index_code": lambda s: s.isna(),
        "ticker": lambda s: s.isna(),
        "effective_from": _bad_date,
    },
    optional={
        "effective_to": lambda s: s.notna() & _bad_date(s),
        "announced_date": lambda s: s.notna() & _bad_date(s),
        "reason_in": lambda s: pd.Series(False, index=s.index),
        "reason_out": lambda s: pd.Series(False, index=s.index),
    },
    key=("index_code", "ticker", "effective_from"),
)

EVENTS = Contract(
    name="events",
    required={
        "event_type": lambda s: s.isna(),
        "announced_date": _bad_date,
        "scope": lambda s: ~s.isin(["market", "sector", "ticker"]),
        "headline": lambda s: s.isna(),
    },
    optional={
        "effective_date": lambda s: s.notna() & _bad_date(s),
        "event_uid": lambda s: pd.Series(False, index=s.index),
        "category": lambda s: pd.Series(False, index=s.index),
        "publication_ts": lambda s: pd.Series(False, index=s.index),
        "index_code": lambda s: pd.Series(False, index=s.index),
        "ticker": lambda s: pd.Series(False, index=s.index),
        "outcome_numeric": lambda s: pd.Series(False, index=s.index),
        "outcome_text": lambda s: pd.Series(False, index=s.index),
        "severity": lambda s: s.notna() & ~s.astype(str).isin(
            ["low", "medium", "high", "critical"]),
        "direction": lambda s: s.notna() & ~s.astype(str).isin(
            ["bullish", "bearish", "neutral", "unknown"]),
        "structurally_impairing": lambda s: s.notna() & ~s.astype(str).isin(["0", "1"]),
        "source_url": lambda s: pd.Series(False, index=s.index),
        "notes": lambda s: pd.Series(False, index=s.index),
    },
    key=("event_type", "announced_date", "headline"),
)

CONTRACTS: dict[str, Contract] = {
    c.name: c
    for c in (INDEX_LEVELS, EQUITY_PRICES, CORPORATE_ACTIONS, INDEX_MEMBERSHIP, EVENTS)
}
