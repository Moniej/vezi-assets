"""FRE-5: CompanyThesis -- an explainable investment-research artifact, NOT
a statistically validated thesis-folding experiment
(docs/fre_runs/fre5_thesis_folding_preregistration.md).

Per the owner's approved scope adjustment: real NGX implication data
cannot support a fold-weight comparison (only one ticker, TOTAL, has a
real multi-point history -- 4 implications -- and even that is far too
small a sample for a statistically powered experiment). This module
therefore implements exactly ONE, fully transparent synthesis rule --
the naive baseline itself, per the pre-registration's own framing -- with
ZERO numeric weighting of any kind, per the owner's explicit "no hidden
scoring weights" constraint:

  current bull/bear/base case = the MOST RECENT non-blocked
  implication's own bull_case_delta/bear_case_delta/base_case_delta,
  verbatim. thesis_history shows every prior implication in full,
  unblended, so a reader can see exactly how "current" was derived and
  audit the whole trajectory themselves. No mean, no decay, no tunable
  parameter of any kind.

Built entirely from four already-existing, already-verified FRE inputs,
per the owner's exact composition:
  - Evidence Graph (evidence_graph.build_evidence_chain) -- financial/
    business/competitive layer breakdown and missing-evidence gaps, per
    fact.
  - Company Memory (company_memory.build_company_memory) -- the real,
    PIT-safe, per-ticker implication/fact history, already excluding
    blocked_by_self_critique rows.
  - Cross-document reasoning -- investment_implications.corroborates_
    implication_id/contradicts_implication_id + consistency_note
    (already populated by the existing AI layer for 6 real rows -- not
    re-computed here, only surfaced).
  - Market Reaction Validation (reaction_check.reaction_check) -- the
    deterministic price-direction cross-check, surfaced alongside the
    thesis, never blended into confidence.

No expected-return prediction, no alpha claim, no valuation output, no
scoring formula. `confidence` is the most recent non-blocked
implication's own recorded `confidence` value, verbatim -- never
computed, blended, or inflated by this module.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ngxrot.fre.company_memory import build_company_memory
from ngxrot.fre.evidence_graph import build_evidence_chain
from ngxrot.fre.reaction_check import reaction_check

_FINANCIAL_IMPACT_CATEGORIES = ("revenue", "margins", "cash_flow", "balance_sheet", "liquidity")
_RISK_CATEGORIES = ("execution_risk", "regulatory_risk", "liquidity")


@dataclass
class ThesisHistoryEntry:
    implication_id: int
    filing_date: str
    direction: str
    magnitude: str
    confidence: float
    bull_case_delta: str | None
    bear_case_delta: str | None
    base_case_delta: str | None
    corroborates_implication_id: int | None
    contradicts_implication_id: int | None
    consistency_note: str | None


@dataclass
class CompanyThesis:
    ticker: str
    as_of_date: str
    is_pilot: bool  # always True in this pass -- a case-study artifact, not a validated product

    bull_case: str | None
    bear_case: str | None
    base_case: str | None
    contradiction_note: str | None  # surfaced verbatim from the AI layer's own consistency_note, if any

    key_risks: list[str]
    catalysts: list[str]  # known reference dates from extracted_facts -- historical in this dataset, disclosed as such
    competitive_position: str
    financial_signal_summary: str  # explicitly NOT the same as company_intelligence.py's blocked "Financial Quality"
    management_assessment: str
    capital_allocation_assessment: str

    confidence: float | None  # verbatim from the most recent non-blocked implication, never computed
    confidence_rationale: str | None

    market_reaction_crosscheck: str  # from reaction_check(), never blended into confidence

    excluded_blocked_count: int
    thesis_history: list[ThesisHistoryEntry]
    missing_evidence: list[str] = field(default_factory=list)
    source_implication_ids: list[int] = field(default_factory=list)


def _no_evidence(note: str) -> str:
    return f"No evidence found: {note}"


def build_company_thesis(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyThesis:
    memory = build_company_memory(con, ticker, as_of_date)

    impl_rows = con.execute(
        """
        SELECT ii.implication_id, d.filing_date, ii.direction, ii.magnitude, ii.confidence,
               ii.confidence_rationale, ii.bull_case_delta, ii.bear_case_delta, ii.base_case_delta,
               ii.corroborates_implication_id, ii.contradicts_implication_id, ii.consistency_note,
               ii.status, ii.fact_id
        FROM investment_implications ii
        JOIN extracted_facts f ON f.fact_id = ii.fact_id
        JOIN documents d ON d.doc_id = f.doc_id
        WHERE ii.ticker = ? AND d.filing_date <= ?
        ORDER BY d.filing_date
        """,
        (ticker, as_of_date),
    ).fetchall()

    all_count = len(impl_rows)
    usable_rows = [r for r in impl_rows if r[12] != "blocked_by_self_critique"]
    excluded_blocked_count = all_count - len(usable_rows)

    thesis_history = [
        ThesisHistoryEntry(
            implication_id=r[0], filing_date=r[1], direction=r[2], magnitude=r[3],
            confidence=r[4], bull_case_delta=r[6], bear_case_delta=r[7], base_case_delta=r[8],
            corroborates_implication_id=r[9], contradicts_implication_id=r[10], consistency_note=r[11],
        )
        for r in usable_rows
    ]

    missing_evidence: list[str] = []
    if not usable_rows:
        bull_case = bear_case = base_case = None
        confidence = confidence_rationale = None
        contradiction_note = None
        source_implication_ids: list[int] = []
        if excluded_blocked_count > 0:
            missing_evidence.append(
                f"The only {excluded_blocked_count} real implication(s) for this ticker "
                f"were blocked_by_self_critique -- correctly declining to synthesize a "
                f"bull/bear/base narrative from a rejected implication, pending human review."
            )
        else:
            missing_evidence.append("No investment_implications row exists for this ticker as of this date.")
    else:
        most_recent = usable_rows[-1]
        bull_case, bear_case, base_case = most_recent[6], most_recent[7], most_recent[8]
        confidence, confidence_rationale = most_recent[4], most_recent[5]
        source_implication_ids = [r[0] for r in usable_rows]
        contradiction_note = None
        if most_recent[10] is not None:  # contradicts_implication_id
            contradiction_note = (
                f"The current base case CONTRADICTS an earlier implication "
                f"(#{most_recent[10]}). Recorded reasoning: {most_recent[11]}"
            )
        if excluded_blocked_count > 0:
            missing_evidence.append(
                f"{excluded_blocked_count} additional real implication(s) for this ticker "
                f"were excluded from this thesis for being blocked_by_self_critique."
            )

    # Key risks: real impact_assessments across every usable fact for this ticker.
    key_risks: list[str] = []
    fact_ids = [r[13] for r in usable_rows]
    for fid in fact_ids:
        rows = con.execute(
            "SELECT category, direction, explanation FROM impact_assessments "
            "WHERE fact_id = ? AND category IN (?,?,?) AND direction IN ('negative','mixed')",
            (fid, *_RISK_CATEGORIES),
        ).fetchall()
        key_risks.extend(f"[{cat}, fact {fid}] {expl}" for cat, _, expl in rows)
    if not key_risks:
        key_risks = [_no_evidence("no negative/mixed execution_risk, regulatory_risk, or "
                                   "liquidity impact_assessments found across this ticker's usable facts")]

    # Catalysts: real, structured reference dates -- historical in this dataset (every
    # date here is necessarily in the past relative to 2026), disclosed as such, never
    # presented as a forward-looking prediction.
    catalysts: list[str] = []
    for fid in fact_ids:
        row = con.execute(
            "SELECT qualification_date, payment_date, agm_date, closure_date FROM extracted_facts "
            "WHERE fact_id = ?", (fid,)
        ).fetchone()
        if row:
            labels = ["qualification_date", "payment_date", "agm_date", "closure_date"]
            for label, value in zip(labels, row):
                if value:
                    catalysts.append(f"fact {fid}: {label} = {value} (historical reference date, not a forecast)")
    if not catalysts:
        catalysts = [_no_evidence("no structured qualification/payment/AGM/closure dates found")]

    # Competitive position: Evidence Graph's competitive-classified steps, per fact.
    competitive_notes: list[str] = []
    for fid in fact_ids:
        chain = build_evidence_chain(con, fid)
        competitive_notes.extend(s.statement for s in chain.competitive_steps)
        row = con.execute(
            "SELECT category, direction, explanation FROM impact_assessments "
            "WHERE fact_id = ? AND category IN ('competitive_advantage','long_term_moat') "
            "AND direction != 'neutral'", (fid,)
        ).fetchall()
        competitive_notes.extend(f"[{cat}] {expl}" for cat, _, expl in row)
    competitive_position = (
        "; ".join(competitive_notes) if competitive_notes else
        _no_evidence("no causal-chain step classifies as competitive, and no non-neutral "
                     "competitive_advantage/long_term_moat impact_assessment exists for this ticker "
                     "(a real, disclosed property of the current data -- see FRE-2's finding that "
                     "competitive reasoning rarely appears explicitly in causal chains)")
    )

    # Financial signal summary -- explicitly NOT company_intelligence.py's "Financial
    # Quality" (which requires a financial-statements dataset this platform doesn't have).
    financial_notes: list[str] = []
    for fid in fact_ids:
        rows = con.execute(
            "SELECT category, direction, explanation FROM impact_assessments "
            "WHERE fact_id = ? AND category IN (?,?,?,?,?) AND direction != 'neutral'",
            (fid, *_FINANCIAL_IMPACT_CATEGORIES),
        ).fetchall()
        financial_notes.extend(f"[{cat}={dirn}] {expl}" for cat, dirn, expl in rows)
    financial_signal_summary = (
        "; ".join(financial_notes) if financial_notes else
        _no_evidence("no non-neutral revenue/margins/cash_flow/balance_sheet/liquidity "
                     "impact_assessments found")
    )
    financial_signal_summary += (
        " [DISCLOSED: this is a qualitative signal derived from impact_assessments, NOT "
        "a financial-statements-based quality score -- that remains blocked pending a "
        "financial-statements dataset, per company_intelligence.py's own UNAVAILABLE_FIELDS.]"
    )

    # Management assessment: Company Memory's real, currently-always-empty lineage read.
    management_assessment = (
        _no_evidence("management_history is empty (no management_change extraction has "
                     "been run at any volume yet -- a real, disclosed, systemic gap, not "
                     "specific to this ticker)")
        if not memory.management_history else
        "; ".join(str(m) for m in memory.management_history)
    )

    # Capital allocation assessment: impact_assessments.capital_allocation, real and
    # usually active (paying/proposing a dividend IS a capital-allocation act).
    capalloc_notes: list[str] = []
    for fid in fact_ids:
        row = con.execute(
            "SELECT direction, explanation FROM impact_assessments "
            "WHERE fact_id = ? AND category = 'capital_allocation' AND direction != 'neutral'",
            (fid,),
        ).fetchall()
        capalloc_notes.extend(f"[{dirn}] {expl}" for dirn, expl in row)
    capital_allocation_assessment = (
        "; ".join(capalloc_notes) if capalloc_notes else
        _no_evidence("no non-neutral capital_allocation impact_assessment found")
    )

    # Market Reaction Validation: reaction_check() on the most recent usable implication,
    # never blended into confidence -- surfaced as its own, separate cross-check.
    if usable_rows:
        rc = reaction_check(con, usable_rows[-1][0])
        market_reaction_crosscheck = (
            f"direction_check={rc.direction_check}, realized_return="
            f"{f'{rc.realized_return:+.2%}' if rc.realized_return is not None else 'N/A'}, "
            f"thin_liquidity={rc.thin_liquidity_flag}, existing_AI_layer_verdict="
            f"{rc.existing_market_reaction_assessment} ({rc.note})"
        )
    else:
        market_reaction_crosscheck = _no_evidence("no usable implication to reaction-check")

    # Missing evidence: real open research tasks across every usable fact.
    for fid in fact_ids:
        impl_id_row = con.execute(
            "SELECT implication_id FROM investment_implications WHERE fact_id = ?", (fid,)
        ).fetchone()
        if impl_id_row:
            tasks = con.execute(
                "SELECT description FROM research_task_candidates WHERE implication_id = ? AND status = 'open'",
                impl_id_row,
            ).fetchall()
            missing_evidence.extend(t[0] for t in tasks)

    return CompanyThesis(
        ticker=ticker, as_of_date=as_of_date, is_pilot=True,
        bull_case=bull_case, bear_case=bear_case, base_case=base_case,
        contradiction_note=contradiction_note,
        key_risks=key_risks, catalysts=catalysts, competitive_position=competitive_position,
        financial_signal_summary=financial_signal_summary,
        management_assessment=management_assessment,
        capital_allocation_assessment=capital_allocation_assessment,
        confidence=confidence, confidence_rationale=confidence_rationale,
        market_reaction_crosscheck=market_reaction_crosscheck,
        excluded_blocked_count=excluded_blocked_count,
        thesis_history=thesis_history,
        missing_evidence=missing_evidence,
        source_implication_ids=source_implication_ids,
    )
