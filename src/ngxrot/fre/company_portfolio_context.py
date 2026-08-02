"""FSI Phase 20: Portfolio-Context-Annotated Research Dossier
(docs/fre_runs/fsi_phase20_preregistration.md).

Closes a gap Part 9 itself specifies (docs/fre/09_portfolio_reasoning.md,
lines 82-93: "attach a note to a CompanyThesis or watchlist entry...
purely informational, so a researcher knows their qualitative thesis
concerns a name the fund is actually exposed to") but that no phase had
ever wired together: Phase 11's institutional research dossier, Phase
18's watchlist, and Phase 17's live-sleeve cross-reference.

A pure, read-only COMPOSITION layer over three already-frozen,
already-tested functions, each called exactly once and none modified:
`company_research_dossier.build_dossier()`, `watchlist.list_active()`,
`portfolio_memory.cross_reference()`. No new reasoning, no new SQL, no
combined score/rating/ranking/recommendation of any kind, no write path,
no LLM call.

`list_active()` (not `get_history_for_ticker()`) is reused deliberately:
it is the one watchlist reader that already implements point-in-time
correctness (an entry counts as active only if `added_at <= as_of_date`
and not yet removed as of that date). `get_history_for_ticker()` would
return an entry's LIVE `removed_at`, regardless of `as_of_date`, leaking
a future removal into a supposedly point-in-time view.

Disclosed, inherited limitation (not introduced here): `portfolio_memory.
cross_reference()` has no `as_of_date` parameter and always reflects
`alpha_engine.py`'s current live sleeve, never a historical one --
`AlphaEngine.recommendations()` itself has no "as of a past date" query
capability. `PortfolioAnnotatedDossier.portfolio_memory` is therefore
always-live, not point-in-time, exactly as Phase 17 built it.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre.company_research_dossier import CompanyResearchDossier, build_dossier, render_dossier
from ngxrot.fre.portfolio_memory import PortfolioMemoryNote, cross_reference
from ngxrot.fre.watchlist import WatchlistEntryRecord, list_active


@dataclass
class PortfolioAnnotatedDossier:
    ticker: str
    as_of_date: str
    dossier: CompanyResearchDossier
    watchlist_status: list[WatchlistEntryRecord]  # PIT-correct as of as_of_date; usually 0 or 1 entries
    portfolio_memory: PortfolioMemoryNote  # always LIVE -- see module docstring


def as_of(con: sqlite3.Connection, ticker: str, as_of_date: str) -> PortfolioAnnotatedDossier:
    """Single-ticker only. Calls build_dossier(), list_active(), and
    cross_reference() -- each exactly once, none modified."""
    dossier = build_dossier(con, ticker, as_of_date)
    watchlist_status = [e for e in list_active(con, as_of_date=as_of_date) if e.ticker == ticker]
    memory_note = cross_reference(ticker)
    return PortfolioAnnotatedDossier(
        ticker=ticker, as_of_date=as_of_date, dossier=dossier,
        watchlist_status=watchlist_status, portfolio_memory=memory_note,
    )


def _render_watchlist_section(watchlist_status: list[WatchlistEntryRecord]) -> list[str]:
    lines = ["## Watchlist Status", ""]
    lines.append(
        "*This section restates FSI Phase 18's own watchlist fields verbatim, "
        "filtered to point-in-time-active entries only as of this dossier's own "
        "as_of_date -- no score, no priority, no ranking.*"
    )
    lines.append("")
    if not watchlist_status:
        lines.append("Not on the watchlist as of this date.")
        lines.append("")
        return lines
    for e in watchlist_status:
        lines.append(
            f"- watchlist_entry_id={e.watchlist_entry_id} | added_at={e.added_at} | "
            f"entry_criteria: {e.entry_criteria}"
        )
        lines.append(f"  - Rationale: {e.rationale}")
        lines.append(f"  - Source thesis as-of: {e.source_thesis_as_of_date}")
        lines.append(f"  - Review cadence: {e.review_cadence or '(none stated)'}")
        lines.append("")
    return lines


def _render_portfolio_memory_section(note: PortfolioMemoryNote) -> list[str]:
    lines = ["## Portfolio Memory Cross-Reference", ""]
    lines.append(
        "*This section restates FSI Phase 17's own cross-reference verbatim -- "
        "read-only against `alpha_engine.py`'s CURRENT live recommendation set. "
        "Unlike every other section in this dossier, this is NOT point-in-time: "
        "it always reflects today's live sleeve, regardless of this dossier's own "
        "as_of_date, because the underlying AlphaEngine has no historical query "
        "capability. No score, no ranking, no write path back into the registry.*"
    )
    lines.append("")
    if not note.in_live_sleeve:
        lines.append("Not currently in the live sleeve.")
        lines.append("")
        return lines
    lines.append(f"- Currently in the live sleeve (hypothesis_id={note.hypothesis_id})")
    lines.append(f"  - Action: {note.action}")
    lines.append(f"  - Size (% NAV): {note.size_pct_nav}")
    lines.append(f"  - As of: {note.as_of}")
    lines.append(f"  - Rationale: {note.rationale}")
    lines.append("")
    return lines


def render(annotated: PortfolioAnnotatedDossier) -> str:
    """Pure, deterministic. The first three sections are byte-identical
    to calling render_dossier(annotated.dossier) directly; two new
    template-only sections are appended."""
    lines = [render_dossier(annotated.dossier)]
    lines.append("---")
    lines.append("")
    lines.extend(_render_watchlist_section(annotated.watchlist_status))
    lines.append("---")
    lines.append("")
    lines.extend(_render_portfolio_memory_section(annotated.portfolio_memory))
    return "\n".join(lines)
