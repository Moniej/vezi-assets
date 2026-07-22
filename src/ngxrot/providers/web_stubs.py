"""Free/open web providers — INTERFACE STUBS, deliberately unimplemented.

Each stub declares its intended capabilities, base confidence, and known
caveats so the DAL is demonstrably extensible; the actual fetch code will be
written per-source after a feasibility probe of what each site actually
serves (bot-blocking, history depth, adjustment quality). Nothing in the
research engine changes when these are filled in — that is the point of the
DAL.

Confidence rationale:
  - ngx_web (0.9): exchange-official, but current-day only; history requires
    the paid X-DataPortal or archive reconstruction (0.3 via web_archive).
  - investing_com / tradingview (0.5): aggregators; unknown corporate-action
    adjustment policy, occasional gaps and bad prints; acceptable as
    cross-check or provisional primary, results must carry the caveat.
"""

from __future__ import annotations

from .base import DataProvider, ProviderInfo


class NGXWebProvider(DataProvider):
    """Daily index summary + full price list from ngxgroup.com (current-day)."""
    def __init__(self):
        self.info = ProviderInfo(
            name="ngx_web", kind="exchange_official", reliability="primary",
            base_confidence=0.9,
            url_template="https://ngxgroup.com/exchange/data/",
            notes="official daily values; NOT a history source — collect forward daily",
            capabilities=frozenset({"index_levels", "equity_prices"}),
        )
    # fetch_* to be implemented after feasibility probe (see docs/PHASE1_DATA_GAPS.md)


class TradingViewProvider(DataProvider):
    """NGX symbols via TradingView public endpoints (aggregator)."""
    def __init__(self):
        self.info = ProviderInfo(
            name="tradingview", kind="vendor", reliability="secondary",
            base_confidence=0.5,
            url_template="https://www.tradingview.com/symbols/NSENG-{symbol}/",
            notes="unofficial access paths; terms-of-use to be reviewed before use",
            capabilities=frozenset({"index_levels", "equity_prices"}),
        )


class WebArchiveProvider(DataProvider):
    """Historical reconstruction from archived NGX pages/circulars (Wayback)."""
    def __init__(self):
        self.info = ProviderInfo(
            name="web_archive", kind="web_archive", reliability="secondary",
            base_confidence=0.3,
            url_template="https://web.archive.org/web/*/ngxgroup.com*",
            notes="only route to PIT-correct historical membership without a vendor; slow",
            capabilities=frozenset({"index_levels", "index_membership", "events"}),
        )
