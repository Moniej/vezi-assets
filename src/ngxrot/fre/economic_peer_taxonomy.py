"""FRE-7A: Economic Peer Taxonomy (docs/fre_runs/fre7a_peer_taxonomy_report.md).

Diagnostic/remediation stage, NOT a new valuation experiment. FRE-7's own
pilot gate failed (2/7 = 29% bracket rate; see
docs/fre_runs/fre7_valuation_activation_report.md Section 5) with a
diagnosed root cause: `valuation_engine.py`'s only peer-grouping axis
(`classify_company_type()`'s `company_type`) is too coarse -- 19 of the 26
real fact-bearing tickers collapse into one `"general"` bucket spanning
industrial goods, consumer goods, oil & gas, ICT, and conglomerates.

This module builds a finer-grained, two-level economic taxonomy
(`level1`/broad economic sector, `level2`/subsector) plus a
`business_model` tag, sourced entirely from NGX's own official Daily
Official List sector/sub-industry classification
(`securities.sector_ngx` + `sector_ngx_provenance.sub_industry`, FSI Phase
23/26 -- the only first-party structural reference data this platform
holds) via the static, auditable `configs/economic_peer_taxonomy.toml`
lookup table. No business-description or filing-text data exists on this
platform to refine the taxonomy further; where NGX's own sub_industry is a
genuine catch-all, this is disclosed via `confidence`/`notes`, not guessed
away. A ticker with no `sector_ngx` on record (or whose pair is somehow
absent from the config) classifies as UNKNOWN -- never inferred.

## Deliberately NOT touched (FRE-7A hard governance rules 1-4, 11)

This module is purely additive. It does not import from, and is not
imported by, `valuation_engine.py`'s adapter classes -- the DCF/P-E/P-B
formulas, the WACC/terminal-growth handling, and the original FRE-7
pilot's own results are all byte-for-byte unchanged. This module only
supplies an alternative peer-selection input; `scripts/fre/
fre7a_rerun_pilot.py` is the only place that combines it with
`valuation_engine.py`'s own (unmodified) EPS/BVPS/price extraction
helpers to recompute a peer-triangulated multiple.

## PIT discipline

`sector_ngx_provenance.retrieval_date` is a single real snapshot
(2026-08-02, all 136 classified tickers) of when NGX's own Daily Official
List was captured. A classification is only "knowable" as of a given
as_of_date if that retrieval_date <= as_of_date -- the same filing-date
gating discipline `pit_financial_memory.py` applies to financial facts,
applied here to structural/reference data instead. No classification is
ever back-dated to before it was actually retrieved.
"""
from __future__ import annotations

import sqlite3
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"

# Level 2 subsectors that are themselves disclosed catch-alls / too
# heterogeneous to trust as a "same subsector" peer-match tier, even
# though they resolve to a level1/level2 pair. Excluded from subsector-tier
# peer eligibility (falls through to the sector-tier or NOT_READY) --
# never silently included as if they were a clean comparable set.
_UNRELIABLE_LEVEL2_FOR_PEER_MATCHING = frozenset({
    "Other Financial Services",  # known to span registrars/asset managers/investment banks
    "Specialty (Unclassified)",  # NGX's own catch-all, no economic content
    "Diversified Conglomerate",  # by construction has no single-business-model peer group
})


@dataclass
class EconomicClassification:
    ticker: str
    classified: bool  # False means every field below is None -- UNKNOWN, not guessed
    level1: str | None
    level2: str | None
    business_model: str | None
    confidence: str | None  # 'high' | 'medium' | 'low' -- from the mapping table, disclosed not asserted
    evidence_source: str | None  # e.g. "sector_ngx=INDUSTRIAL GOODS, sub_industry=Building Materials"
    retrieval_date: str | None  # when the underlying NGX reference data was captured
    pit_valid: bool  # True iff retrieval_date <= the as_of_date this classification was requested for
    exclusion_reason: str | None  # populated iff classified is False


_taxonomy_cache: dict[tuple[str, str], dict] | None = None


def _load_taxonomy() -> dict[tuple[str, str], dict]:
    global _taxonomy_cache
    if _taxonomy_cache is None:
        with open(CONFIG_DIR / "economic_peer_taxonomy.toml", "rb") as fh:
            data = tomllib.load(fh)
        _taxonomy_cache = {(m["sector_ngx"], m["sub_industry"]): m for m in data["mapping"]}
    return _taxonomy_cache


def classify_ticker(con: sqlite3.Connection, ticker: str, as_of_date: str) -> EconomicClassification:
    """Single-ticker, PIT-gated. Returns classified=False (every taxonomy
    field None) whenever: no sector_ngx is on record for this ticker, no
    sub_industry provenance row exists, the (sector_ngx, sub_industry)
    pair is somehow absent from the config, or the underlying NGX
    reference data's own retrieval_date is AFTER as_of_date (not yet
    knowable at that historical point) -- never a guessed fallback."""
    sector_row = con.execute(
        "SELECT sector_ngx FROM securities WHERE ticker = ?", (ticker,)
    ).fetchone()
    if sector_row is None or sector_row[0] is None:
        return EconomicClassification(
            ticker=ticker, classified=False, level1=None, level2=None, business_model=None,
            confidence=None, evidence_source=None, retrieval_date=None, pit_valid=False,
            exclusion_reason="no securities.sector_ngx on record for this ticker",
        )
    sector_ngx = sector_row[0]

    prov_row = con.execute(
        "SELECT sub_industry, retrieval_date FROM sector_ngx_provenance WHERE ticker = ?", (ticker,)
    ).fetchone()
    if prov_row is None or prov_row[0] is None:
        return EconomicClassification(
            ticker=ticker, classified=False, level1=None, level2=None, business_model=None,
            confidence=None, evidence_source=None, retrieval_date=None, pit_valid=False,
            exclusion_reason=f"sector_ngx={sector_ngx!r} is on record, but no sub_industry "
                              f"provenance row exists for this ticker",
        )
    sub_industry, retrieval_date = prov_row

    pit_valid = retrieval_date <= as_of_date
    if not pit_valid:
        return EconomicClassification(
            ticker=ticker, classified=False, level1=None, level2=None, business_model=None,
            confidence=None, evidence_source=None, retrieval_date=retrieval_date, pit_valid=False,
            exclusion_reason=f"classification data was retrieved {retrieval_date}, which is AFTER "
                              f"as_of_date={as_of_date} -- not yet knowable at that historical point",
        )

    entry = _load_taxonomy().get((sector_ngx, sub_industry))
    if entry is None:
        return EconomicClassification(
            ticker=ticker, classified=False, level1=None, level2=None, business_model=None,
            confidence=None, evidence_source=None, retrieval_date=retrieval_date, pit_valid=True,
            exclusion_reason=f"(sector_ngx={sector_ngx!r}, sub_industry={sub_industry!r}) has no "
                              f"entry in configs/economic_peer_taxonomy.toml",
        )

    return EconomicClassification(
        ticker=ticker, classified=True, level1=entry["level1"], level2=entry["level2"],
        business_model=entry["business_model"], confidence=entry["confidence"],
        evidence_source=f"sector_ngx={sector_ngx!r}, sub_industry={sub_industry!r} "
                         f"(NGX Daily Official List, retrieved {retrieval_date})",
        retrieval_date=retrieval_date, pit_valid=True, exclusion_reason=None,
    )


@dataclass
class PeerSelectionResult:
    ticker: str
    tier: str  # 'subsector' | 'sector' | 'none'
    peers: list[str]
    reason: str


def select_peers(con: sqlite3.Connection, ticker: str, as_of_date: str,
                  candidate_tickers: list[str], min_peers: int = 2) -> PeerSelectionResult:
    """Deterministic hierarchy (FRE-7A peer-selection architecture):
    (1) same level2 subsector, excluding self and any level2 flagged
    unreliable-for-matching; (2) same level1 broad sector, as a disclosed
    fallback, only if tier 1 has fewer than min_peers; (3) 'none' --
    NOT_READY -- if neither tier reaches min_peers. `candidate_tickers`
    is the caller's own universe (e.g. every real fact-bearing ticker);
    this function does not decide financial-data sufficiency (whether a
    peer's own EPS/BVPS is computable) -- that filtering still happens
    downstream, exactly where it always did."""
    subj = classify_ticker(con, ticker, as_of_date)
    if not subj.classified:
        return PeerSelectionResult(
            ticker=ticker, tier="none", peers=[],
            reason=f"subject ticker itself is unclassified: {subj.exclusion_reason}",
        )

    others = [t for t in candidate_tickers if t != ticker]
    classifications = {t: classify_ticker(con, t, as_of_date) for t in others}

    if subj.level2 not in _UNRELIABLE_LEVEL2_FOR_PEER_MATCHING:
        subsector_peers = [t for t, c in classifications.items()
                            if c.classified and c.level2 == subj.level2]
        if len(subsector_peers) >= min_peers:
            return PeerSelectionResult(
                ticker=ticker, tier="subsector", peers=subsector_peers,
                reason=f"{len(subsector_peers)} peer(s) share subsector {subj.level2!r} "
                       f"(level1={subj.level1!r})",
            )
    else:
        subsector_peers = []

    sector_peers = [t for t, c in classifications.items()
                     if c.classified and c.level1 == subj.level1]
    if len(sector_peers) >= min_peers:
        return PeerSelectionResult(
            ticker=ticker, tier="sector", peers=sector_peers,
            reason=(f"subsector {subj.level2!r} had only {len(subsector_peers)} peer(s) "
                     f"(need {min_peers}); falling back to broader level1={subj.level1!r} "
                     f"({len(sector_peers)} peer(s))")
                    if subj.level2 not in _UNRELIABLE_LEVEL2_FOR_PEER_MATCHING else
                    (f"subsector {subj.level2!r} is flagged unreliable for peer-matching "
                     f"(disclosed heterogeneous catch-all); using broader level1="
                     f"{subj.level1!r} ({len(sector_peers)} peer(s))"),
        )

    return PeerSelectionResult(
        ticker=ticker, tier="none", peers=[],
        reason=f"fewer than {min_peers} classified peers at either subsector "
               f"({subj.level2!r}: {len(subsector_peers)}) or sector "
               f"({subj.level1!r}: {len(sector_peers)}) level -- refusing to force an "
               f"economically unsuitable peer group",
    )
