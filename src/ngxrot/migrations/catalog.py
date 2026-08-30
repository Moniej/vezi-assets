"""The declared migration catalog; baseline rows intentionally make no schema change."""

from __future__ import annotations

from .framework import Migration


def baseline_migrations() -> list[Migration]:
    """Explicitly establish the pre-consolidation state without replaying legacy ALTERs."""
    return [
        Migration("20260830_000_pre_consolidation_baseline", target, 0, 1,
                  "SELECT 1; -- ledger-only pre-consolidation baseline")
        for target in ("ngx", "registry", "portfolio")
    ]
