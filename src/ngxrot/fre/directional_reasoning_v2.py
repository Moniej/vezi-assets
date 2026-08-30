"""FRE-8: Directional Reasoning Repair & Validation
(docs/alpha/DIRECTIONAL_REASONING_REPAIR_AND_VALIDATION_2026-08-17.md).

Investigates whether investment_implications' naive FACT -> DIRECTION
mapping (see reaction_check.py's real finding: 10 confirmed / 11
contradicted across 21 scoreable calls, bullish calls failing at 62.5%)
can be repaired into something with real incremental value, WITHOUT
touching the Alpha Engine or H-011 in any way.

Deliberately separate from alpha_engine.py, engine_full.py, runner.py,
registry.py -- imports nothing from them, and nothing in them imports
this module. reasoning_weight is fixed at 0.0 (see REASONING_WEIGHT
below); this module never writes to any table.

Reuses existing, validated infrastructure rather than rebuilding it:
  - reaction_check() for realized-return ground truth
  - valuation_engine.py's PEAdapter/PBAdapter for real (not invented)
    valuation checks
  - financial_reasoning_conclusions (financial_health_flags.py's own
    rule definitions, re-applied here with an explicit period_end<=asof
    filter for point-in-time correctness -- the existing module has no
    such filter since it is a live-monitoring tool, not a backtesting
    one; that gap is the one new thing this module adds, not a rebuild)
  - index_levels (NGXASI) for market-context, informational only
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.reaction_check import reaction_check
from ngxrot.fre.valuation_engine import PEAdapter, PBAdapter

REASONING_WEIGHT = 0.0  # Phase 7 firewall: fixed until separately validated. Never read by
                        # alpha_engine.py / engine_full.py / runner.py / registry.py.

_PE, _PB = PEAdapter(), PBAdapter()


# ---------------------------------------------------------------- Phase 2: contradiction engine

@dataclass
class ConflictResult:
    ticker: str
    anchor_date: str
    implication_ids: tuple[int, ...]
    directions: tuple[str, ...]
    conflicted: bool
    reason: str


def detect_contradictions(con: sqlite3.Connection) -> list[ConflictResult]:
    """Groups investment_implications by (ticker, anchor filing_date) --
    the exact same anchor reaction_check() uses -- and flags any group
    whose directional claims disagree. A group of size 1 is never
    conflicted by construction (nothing to disagree with)."""
    rows = con.execute(
        "SELECT ii.implication_id, ii.ticker, ii.direction, d.filing_date "
        "FROM investment_implications ii "
        "JOIN extracted_facts f ON f.fact_id = ii.fact_id "
        "JOIN documents d ON d.doc_id = f.doc_id "
        "ORDER BY ii.ticker, d.filing_date"
    ).fetchall()
    groups: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for iid, ticker, direction, filing_date in rows:
        groups.setdefault((ticker, filing_date), []).append((iid, direction))

    out = []
    for (ticker, anchor), members in groups.items():
        ids = tuple(m[0] for m in members)
        dirs = tuple(m[1] for m in members)
        directional = {d for d in dirs if d in ("bullish", "bearish")}
        conflicted = len(directional) > 1
        reason = (f"{len(directional)} opposing directional claims ({sorted(directional)}) on the "
                   f"same filing" if conflicted else "no opposing directional claim in this group")
        out.append(ConflictResult(ticker=ticker, anchor_date=anchor, implication_ids=ids,
                                  directions=dirs, conflicted=conflicted, reason=reason))
    return out


# ---------------------------------------------------------------- Phase 3: staged schema

@dataclass
class FundamentalInterpretation:
    label: str  # 'fundamental_positive' | 'fundamental_negative' | 'insufficient_evidence'
    fact_type: str
    numeric_value: float | None
    source: str  # provenance disclosure


@dataclass
class MaterialityAssessment:
    label: str  # 'material' | 'immaterial' | 'insufficient_evidence'
    reused_llm_magnitude: str | None
    reason: str


@dataclass
class ValuationCheck:
    label: str  # 'valuation_computable' | 'insufficient_evidence'
    method: str | None
    point_estimate: float | None
    reason: str


@dataclass
class ExpectationCheck:
    label: str  # always 'insufficient_evidence' -- no expectations dataset exists on this platform
    reason: str


@dataclass
class ConflictCheck:
    label: str  # 'conflicted' | 'no_conflict'
    opposing_implication_ids: tuple[int, ...]
    reason: str


@dataclass
class MarketContextCheck:
    label: str  # 'aligned_with_market' | 'diverges_from_market' | 'insufficient_evidence'
    benchmark_return: float | None
    reason: str


@dataclass
class StagedConclusion:
    implication_id: int
    ticker: str
    original_direction: str
    fundamental: FundamentalInterpretation
    materiality: MaterialityAssessment
    valuation: ValuationCheck
    expectation: ExpectationCheck
    conflict: ConflictCheck
    market_context: MarketContextCheck
    conclusion: str  # 'CONFLICTED' | 'DIRECTIONAL_WEAK' | 'INSUFFICIENT_EVIDENCE'
    conclusion_reason: str


_ASI = "NGXASI"


def _asi_return(con: sqlite3.Connection, before_date: str, after_date: str) -> float | None:
    b = con.execute("SELECT close_value FROM index_levels WHERE index_code=? AND trade_date<=? "
                    "ORDER BY trade_date DESC LIMIT 1", (_ASI, before_date)).fetchone()
    a = con.execute("SELECT close_value FROM index_levels WHERE index_code=? AND trade_date<=? "
                    "ORDER BY trade_date DESC LIMIT 1", (_ASI, after_date)).fetchone()
    if not b or not a or not b[0]:
        return None
    return (a[0] - b[0]) / b[0]


def _health_flag_asof(con: sqlite3.Connection, ticker: str, conclusion_type: str, metric: str,
                      asof: str) -> tuple | None:
    """Same query shape as financial_health_flags._latest_conclusion, with
    an explicit period_end<=asof filter added -- the source module has no
    such filter (it always reads the CURRENT most-recent conclusion,
    correct for live monitoring, wrong for a no-hindsight historical
    check). This is the one genuinely new query in this module."""
    return con.execute(
        "SELECT conclusion_id, value_numeric, value_text, confidence_tier, period_start, period_end "
        "FROM financial_reasoning_conclusions "
        "WHERE ticker=? AND conclusion_type=? AND metric=? AND status='computed' AND period_end<=? "
        "ORDER BY period_end DESC LIMIT 1",
        (ticker, conclusion_type, metric, asof)).fetchone()


def staged_conclusion(con: sqlite3.Connection, implication_id: int,
                      contradiction_index: dict[int, ConflictResult] | None = None) -> StagedConclusion:
    row = con.execute(
        "SELECT ii.ticker, ii.direction, ii.magnitude, f.fact_type, f.numeric_value, d.filing_date "
        "FROM investment_implications ii JOIN extracted_facts f ON f.fact_id=ii.fact_id "
        "JOIN documents d ON d.doc_id=f.doc_id WHERE ii.implication_id=?", (implication_id,)).fetchone()
    if row is None:
        raise ValueError(f"no investment_implications row for implication_id={implication_id}")
    ticker, direction, magnitude, fact_type, numeric_value, anchor_date = row

    # Stage 1: fundamental interpretation -- reuses the existing LLM's own
    # qualitative direction as the fundamental-improvement/-deterioration
    # signal (re-deriving it from raw prior-period deltas is out of scope
    # for this repair pass; disclosed, not hidden).
    if direction == "bullish":
        fundamental = FundamentalInterpretation("fundamental_positive", fact_type, numeric_value,
                                                 "reused from investment_implications.direction (LLM-assigned)")
    elif direction == "bearish":
        fundamental = FundamentalInterpretation("fundamental_negative", fact_type, numeric_value,
                                                 "reused from investment_implications.direction (LLM-assigned)")
    else:
        fundamental = FundamentalInterpretation("insufficient_evidence", fact_type, numeric_value,
                                                 f"direction={direction!r} carries no directional claim")

    # Stage 2: materiality -- reuses the LLM's own magnitude field
    # (informational reuse, not an independently derived judgment).
    if magnitude in ("large", "transformational"):
        materiality = MaterialityAssessment("material", magnitude, "LLM-assigned magnitude bucket")
    elif magnitude in ("small", "tiny"):
        materiality = MaterialityAssessment("immaterial", magnitude, "LLM-assigned magnitude bucket")
    elif magnitude:
        materiality = MaterialityAssessment("material", magnitude, "LLM-assigned magnitude bucket (medium)")
    else:
        materiality = MaterialityAssessment("insufficient_evidence", magnitude, "no magnitude recorded")

    # Stage 3: valuation -- real compute() calls, PIT as_of=anchor_date,
    # never a fabricated number (point_estimate=None IS the answer when
    # data doesn't exist).
    valuation = ValuationCheck("insufficient_evidence", None, None,
                               "neither P/E nor P/B is computable for this ticker as of this date")
    for adapter in (_PE, _PB):
        if adapter.is_ready(con, ticker).ready:
            r = adapter.compute(con, ticker, anchor_date, {})
            if r.point_estimate is not None:
                valuation = ValuationCheck("valuation_computable", adapter.method_name,
                                           r.point_estimate, r.confidence_note)
                break

    # Stage 4: expectations -- structurally insufficient platform-wide; no
    # analyst/consensus/estimate dataset exists anywhere on this platform
    # (verified: zero matching tables). Never fabricated.
    expectation = ExpectationCheck("insufficient_evidence",
                                   "no earnings-expectations/analyst-consensus dataset exists on "
                                   "this platform (verified against the live schema, not assumed)")

    # Stage 5: conflict check -- from the real contradiction engine (Phase 2).
    if contradiction_index is not None and implication_id in contradiction_index:
        cr = contradiction_index[implication_id]
        if cr.conflicted:
            others = tuple(i for i in cr.implication_ids if i != implication_id)
            conflict = ConflictCheck("conflicted", others,
                                     f"opposing directional claim(s) on the same filing: {others}")
        else:
            conflict = ConflictCheck("no_conflict", (), "no opposing directional claim on this filing")
    else:
        conflict = ConflictCheck("no_conflict", (), "contradiction index not supplied")

    # Stage 6 (informational only, never gates the conclusion): market context.
    after_row = con.execute("SELECT trade_date FROM equity_prices WHERE ticker=? AND trade_date>? "
                            "ORDER BY trade_date ASC LIMIT 5", (ticker, anchor_date)).fetchall()
    market_context = MarketContextCheck("insufficient_evidence", None, "insufficient price window")
    if after_row:
        after_date = after_row[-1][0]
        asi_ret = _asi_return(con, anchor_date, after_date)
        if asi_ret is not None:
            label = "aligned_with_market" if (direction == "bullish") == (asi_ret >= 0) else "diverges_from_market"
            market_context = MarketContextCheck(label, asi_ret,
                                                f"NGXASI moved {asi_ret:+.2%} over the same window")

    # Final: staged conclusion. CONFLICTED wins outright (Phase 3's explicit
    # requirement: never silently retain both BULLISH and BEARISH). Absent
    # a conflict, valuation and expectations are BOTH insufficient for
    # every real case checked in this repair pass -- so a full directional
    # MARKET conclusion is never actually reachable from this platform's
    # current data; the strongest honest output is a WEAK, fundamentals-
    # only directional lean, explicitly labeled as such (this is the
    # concrete mechanism enforcing "business improved" != "security
    # should outperform").
    if conflict.label == "conflicted":
        conclusion, reason = "CONFLICTED", conflict.reason
    elif fundamental.label == "insufficient_evidence":
        conclusion, reason = "INSUFFICIENT_EVIDENCE", "no directional fundamental claim to begin with"
    elif valuation.label == "insufficient_evidence" and expectation.label == "insufficient_evidence":
        conclusion = "DIRECTIONAL_WEAK"
        reason = ("fundamental-only signal; valuation AND expectations are both insufficient_evidence "
                  "for this ticker/date -- NOT promoted to a full market-direction call")
    else:
        conclusion = "DIRECTIONAL_WEAK"
        reason = "fundamental signal with partial corroboration; still not a full market-direction call"

    return StagedConclusion(implication_id, ticker, direction, fundamental, materiality, valuation,
                            expectation, conflict, market_context, conclusion, reason)


# ---------------------------------------------------------------- Phase 1: failure taxonomy

TAXONOMY_CATEGORIES = (
    "fundamental_improvement_incorrectly_bullish",
    "fundamental_deterioration_incorrectly_bearish",
    "valuation_blindness",
    "expectations_blindness",
    "conflicting_factor_blindness",
    "magnitude_materiality_failure",
    "confirmed_no_failure",
    "not_applicable",
    "inconclusive",
    "insufficient_evidence",
)


@dataclass
class TaxonomyResult:
    implication_id: int
    ticker: str
    direction: str
    direction_check: str  # from reaction_check()
    categories: tuple[str, ...]
    staged: StagedConclusion


def classify_taxonomy(con: sqlite3.Connection, implication_id: int,
                      contradiction_index: dict[int, ConflictResult]) -> TaxonomyResult:
    rc = reaction_check(con, implication_id)
    staged = staged_conclusion(con, implication_id, contradiction_index)
    cats: list[str] = []

    if rc.direction_check == "not_applicable":
        cats.append("not_applicable")
    elif rc.direction_check == "inconclusive":
        cats.append("inconclusive")
    elif rc.direction_check == "direction_confirmed":
        cats.append("confirmed_no_failure")
    elif rc.direction_check == "direction_contradicted":
        if rc.direction == "bullish":
            cats.append("fundamental_improvement_incorrectly_bullish")
        elif rc.direction == "bearish":
            cats.append("fundamental_deterioration_incorrectly_bearish")
        if staged.valuation.label == "insufficient_evidence":
            cats.append("valuation_blindness")
        if staged.expectation.label == "insufficient_evidence":
            cats.append("expectations_blindness")
        if staged.conflict.label == "conflicted":
            cats.append("conflicting_factor_blindness")
        if staged.materiality.label == "insufficient_evidence":
            cats.append("magnitude_materiality_failure")

    if not cats:
        cats.append("insufficient_evidence")
    return TaxonomyResult(implication_id, rc.ticker, rc.direction, rc.direction_check, tuple(cats), staged)


# ---------------------------------------------------------------- Phase 5: unweighted score

@dataclass
class UnweightedScore:
    implication_id: int
    ticker: str
    stages_resolved: int  # of {fundamental, materiality, valuation, expectation}, non-insufficient count
    stages_total: int
    conflicted: bool
    score_label: str  # 'high_evidence_completeness' | 'low_evidence_completeness'


@dataclass
class FilingContext:
    """Phase 5: a deterministic, filing-level context object the reasoning
    layer SHOULD consume instead of isolated facts -- data structure only,
    no new inference. Every field is either real data or an explicit
    'unavailable' sentinel; nothing here invents missing context."""
    doc_id: int
    ticker: str
    filing_date: str
    facts: tuple[dict, ...]              # every extracted_facts row for this doc_id
    implication_ids: tuple[int, ...]     # any investment_implications already generated from these facts
    positive_factors: tuple[str, ...]    # fact_types whose OWN implication direction is bullish
    negative_factors: tuple[str, ...]    # fact_types whose OWN implication direction is bearish
    valuation_context: str               # 'unavailable' unless a real ValuationCheck resolved
    expectation_context: str             # always 'unavailable' -- no expectations dataset exists
    conflicts: tuple[int, ...]           # implication_ids in a detected same-filing conflict


def build_filing_context(con: sqlite3.Connection, doc_id: int,
                         contradiction_index: dict[int, ConflictResult] | None = None) -> FilingContext:
    frow = con.execute("SELECT ticker, filing_date FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
    if frow is None:
        raise ValueError(f"no documents row for doc_id={doc_id}")
    ticker, filing_date = frow

    fact_rows = con.execute(
        "SELECT fact_id, fact_type, numeric_value, period_start, period_end, period_type, currency "
        "FROM extracted_facts WHERE doc_id=?", (doc_id,)).fetchall()
    facts = tuple({"fact_id": r[0], "fact_type": r[1], "numeric_value": r[2], "period_start": r[3],
                  "period_end": r[4], "period_type": r[5], "currency": r[6]} for r in fact_rows)

    impl_rows = con.execute(
        "SELECT ii.implication_id, ii.direction FROM investment_implications ii "
        "JOIN extracted_facts f ON f.fact_id=ii.fact_id WHERE f.doc_id=?", (doc_id,)).fetchall()
    implication_ids = tuple(r[0] for r in impl_rows)
    positive_factors = tuple(_fact_type_for_implication(con, r[0]) for r in impl_rows if r[1] == "bullish")
    negative_factors = tuple(_fact_type_for_implication(con, r[0]) for r in impl_rows if r[1] == "bearish")

    valuation_context = "unavailable"
    for adapter in (_PE, _PB):
        if adapter.is_ready(con, ticker).ready:
            r = adapter.compute(con, ticker, filing_date, {})
            if r.point_estimate is not None:
                valuation_context = f"{adapter.method_name}={r.point_estimate:.2f}"
                break

    conflicted_ids = ()
    if contradiction_index is not None:
        for iid in implication_ids:
            if iid in contradiction_index and contradiction_index[iid].conflicted:
                conflicted_ids = tuple(sorted(set(conflicted_ids) | {iid}))

    return FilingContext(doc_id=doc_id, ticker=ticker, filing_date=filing_date, facts=facts,
                         implication_ids=implication_ids, positive_factors=positive_factors,
                         negative_factors=negative_factors, valuation_context=valuation_context,
                         expectation_context="unavailable", conflicts=conflicted_ids)


def _fact_type_for_implication(con: sqlite3.Connection, implication_id: int) -> str:
    row = con.execute(
        "SELECT f.fact_type FROM investment_implications ii JOIN extracted_facts f ON f.fact_id=ii.fact_id "
        "WHERE ii.implication_id=?", (implication_id,)).fetchone()
    return row[0] if row else "unknown"


def unweighted_score(sc: StagedConclusion) -> UnweightedScore:
    """Deliberately NOT a weighted composite -- Phase 5's guardrail
    forbids inventing weights against 21 observations. This counts how
    many of the four evidence stages actually resolved to something
    other than insufficient_evidence -- a completeness score, not a
    directional confidence score."""
    stages = [sc.fundamental.label, sc.materiality.label, sc.valuation.label, sc.expectation.label]
    resolved = sum(1 for s in stages if s not in ("insufficient_evidence",))
    label = "high_evidence_completeness" if resolved >= 3 else "low_evidence_completeness"
    return UnweightedScore(sc.implication_id, sc.ticker, resolved, len(stages),
                           sc.conflict.label == "conflicted", label)
