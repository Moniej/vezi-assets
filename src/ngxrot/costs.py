"""Transaction cost model (Phase 2 level: per-side rates on traded value).

Rates come from the effective-dated cost_schedule table; brokerage can be
overridden per experiment (costs are an EXPERIMENTAL VARIABLE — every run
records its full cost assumption line items in the experiment registry).
Phase 3 upgrades this to per-constituent line-item P&L; the per-side rates
here are the aggregation of the same line items.

VAT base assumption (marked 'assumed'): VAT applies to brokerage + CSCS fee,
not to stamp duty or SEC/NGX statutory fees. Confirm against a contract note.
"""

from __future__ import annotations

import pandas as pd

VATABLE = {"brokerage", "cscs_fee"}


def side_rates(schedule: pd.DataFrame, brokerage_override_pct: float | None = None
               ) -> dict:
    """Compute total buy-side and sell-side cost rates (fractions of value).

    Returns dict with 'buy_rate', 'sell_rate' (fractions, e.g. 0.0189) and
    'line_items' for the experiment record.
    """
    sch = schedule.copy()
    if brokerage_override_pct is not None and brokerage_override_pct >= 0:
        sch.loc[sch.fee_name == "brokerage", "rate_pct"] = brokerage_override_pct
        sch.loc[sch.fee_name == "brokerage", "confidence"] = "assumed"

    vat_pct = float(sch.loc[sch.fee_name == "vat", "rate_pct"].iloc[0]) \
        if (sch.fee_name == "vat").any() else 0.0
    tv = sch[sch.applies_to == "trade_value"]

    def one_side(side: str) -> float:
        rows = tv[tv.side.isin([side, "both"])]
        base = rows.rate_pct.sum()
        vatable = rows[rows.fee_name.isin(VATABLE)].rate_pct.sum()
        return (base + vatable * vat_pct / 100.0) / 100.0

    return {
        "buy_rate": one_side("buy"),
        "sell_rate": one_side("sell"),
        "vat_pct": vat_pct,
        "line_items": [
            dict(fee=r.fee_name, side=r.side, rate_pct=float(r.rate_pct),
                 confidence=r.confidence)
            for r in sch.itertuples()
        ],
    }
