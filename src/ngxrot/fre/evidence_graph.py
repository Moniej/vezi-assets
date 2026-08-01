"""FRE-2: the Evidence Graph (docs/fre/03_evidence_graph.md), implemented.

Operationalizes the owner's chain -- Evidence -> Observation -> Financial
Implication -> Business Implication -> Competitive Implication -> Investment
Implication -> Confidence -> Missing Evidence -- entirely by READING and, for
one narrowly-scoped step, classifying/backfilling two columns FRE-1 already
added (`causal_chain_steps.implication_layer`/`.reasoning_mode`). No schema
change in this module. No LLM call. No modification to `extract.py`,
`self_critique.py`, or any other AI Intelligence Layer pipeline file --
consistent with the standing instruction not to touch that layer absent a
documented blocker (none was found: everything this module needs already
exists in the schema and in real, already-extracted data).

Design grounded in the REAL data, not assumed. Before writing the
classifier below, all 18 real facts with a causal chain (fact_ids 144-161,
`data/ngx.sqlite`, 2026-08-01) were inspected directly. Finding: 17/18 are
simple `dividend` facts whose entire 2-3-step chain is genuinely financial
(cash/balance-sheet/liquidity mechanics) -- there is no business or
competitive content to find, because a routine dividend payment doesn't
have any. Only one fact (144, GTCO's real ₦400.5bn rights issue -- the same
case already on record in HANDOFF.md as a real self-critique block) touches
all three layers. This shaped two concrete decisions: (1) the classifier
below is deliberately conservative -- it leaves a step unclassified rather
than forcing a layer onto text that doesn't support one, so the expected,
correct outcome on this real dataset is "most facts are 100% financial,
zero business/competitive, and that is accurate, not a classifier
shortfall"; (2) `layer_gap_report()` below cross-references against
`impact_assessments` rather than just counting distinct layers, because a
real, concrete finding from fact 144 is that its competitive_advantage/
long_term_moat assessments ARE genuinely non-neutral, but the supporting
reasoning lives in `impact_assessments.explanation` text, not in any
`causal_chain_steps.statement` -- the current AI Intelligence Layer's
causal-chain construction does not yet write a distinct competitive-
implication step even when a fact has real competitive content elsewhere.
That is a genuine "missing evidence" finding this module is built to
surface mechanically, not something to paper over with a looser classifier.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Step 1: the layer classifier (financial / business / competitive / None)
# ---------------------------------------------------------------------------
# Deliberately small, precise, and disclosed in full here -- not tuned to
# maximize classification RATE (that would risk overfitting a lexicon to
# this session's 18 facts), only to be recognizably grounded in Part 1's
# ontology node families and the impact_assessments category vocabulary.
# Matching is a case-insensitive substring search against a step's own
# `statement` text; a step is assigned the layer with the STRICT majority of
# keyword hits (must be > 0 and not tied with another layer) -- a tie or a
# zero-hit step is left UNCLASSIFIED (None), never guessed. This is the same
# "unknown stays unknown" discipline this platform has used since Phase A,
# applied to a new, mechanical classifier rather than to a data-quality gap.

_FINANCIAL_TERMS = (
    "cash", "dividend", "balance sheet", "retained earning", "liquidity",
    "liquid asset", "proceeds", "equity", "net asset value", "nav",
    "cash flow", "distribution", "payout", "revenue", "margin",
    "interest income", "earning", "capital base", "tier 1", "capital ratio",
    "market capitalization", "market capitalisation", "share capital",
    "yield", "fee revenue", "payment", "per share", "share dilution",
    "asset management", "asset base",
)
_BUSINESS_TERMS = (
    "strategy", "strategic", "allocat", "deploy", "acquisition", "expand",
    "capacity", "compliance", "regulatory", "mandate", "plan", "growth",
    "execution", "integrat", "lending capacity", "recapitalis",
    "recapitaliz", "non-banking", "organic",
)
_COMPETITIVE_TERMS = (
    "competit", "market position", "moat", "peer", "tier-1", "tier 1 institution",
    "cross-sell", "market share", "rival", "sector position",
    "holding company structure",
)

_LEXICONS: dict[str, tuple[str, ...]] = {
    "financial": _FINANCIAL_TERMS,
    "business": _BUSINESS_TERMS,
    "competitive": _COMPETITIVE_TERMS,
}

# impact_assessments.category -> the layer it evidences, when its direction
# is NOT 'neutral' (every fact gets all 13 categories assessed by design,
# Reasoning Engine Spec §5 -- most are 'neutral' padding, not real signal;
# 'unknown' is the schema's true not-assessed sentinel and is equally
# excluded). Only categories with a REAL (non-neutral, non-unknown) verdict
# count as "this layer is genuinely active for this fact" -- see
# layer_gap_report()'s docstring for why this distinction matters.
_CATEGORY_TO_LAYER = {
    "revenue": "financial", "margins": "financial", "cash_flow": "financial",
    "balance_sheet": "financial", "liquidity": "financial",
    "capital_allocation": "business", "growth": "business",
    "execution_risk": "business", "regulatory_risk": "business",
    "market_expectations": "business",
    "competitive_advantage": "competitive", "long_term_moat": "competitive",
    # 'valuation' deliberately maps to no layer -- it is Part 8's
    # (Valuation Engine's) concern, explicitly out of FRE-2's scope, and is
    # not one of the three values causal_chain_steps.implication_layer's
    # CHECK constraint (FRE-1) permits.
}


def classify_step_layer(statement: str) -> str | None:
    """Classify one causal_chain_steps.statement into 'financial'/
    'business'/'competitive', or None if unclassifiable (zero hits, or a
    tie between two+ layers). Pure function, no I/O."""
    text = statement.lower()
    counts = {layer: sum(1 for term in terms if term in text)
              for layer, terms in _LEXICONS.items()}
    max_count = max(counts.values())
    if max_count == 0:
        return None
    winners = [layer for layer, c in counts.items() if c == max_count]
    if len(winners) != 1:
        return None
    return winners[0]


def classify_causal_chain_layers(con: sqlite3.Connection, fact_id: int) -> dict[int, str | None]:
    """chain_id -> classified layer (or None) for every step of `fact_id`."""
    rows = con.execute(
        "SELECT chain_id, statement FROM causal_chain_steps WHERE fact_id = ? "
        "ORDER BY step_order", (fact_id,)
    ).fetchall()
    return {chain_id: classify_step_layer(statement) for chain_id, statement in rows}


# ---------------------------------------------------------------------------
# Step 2: backfill (the only write path in this module -- two already-
# existing, already-approved nullable columns, never a schema change)
# ---------------------------------------------------------------------------

@dataclass
class BackfillReport:
    total_steps: int
    already_labeled: int
    newly_financial: int
    newly_business: int
    newly_competitive: int
    left_unclassified: int
    applied: bool  # False for a dry run -- nothing was written


def backfill_implication_layers(con: sqlite3.Connection, dry_run: bool = True) -> BackfillReport:
    """Classify every causal_chain_steps row that doesn't already have an
    implication_layer, and (unless dry_run) write the result. Idempotent:
    rows that already carry a non-NULL implication_layer are left untouched
    and counted separately, so re-running never overwrites a prior decision
    (including a human-corrected one, should that ever be added later)."""
    rows = con.execute(
        "SELECT chain_id, statement, implication_layer FROM causal_chain_steps"
    ).fetchall()
    already_labeled = sum(1 for _, _, layer in rows if layer is not None)
    counts = {"financial": 0, "business": 0, "competitive": 0, None: 0}
    to_write: list[tuple[str, int]] = []
    for chain_id, statement, existing_layer in rows:
        if existing_layer is not None:
            continue
        layer = classify_step_layer(statement)
        counts[layer] += 1
        if layer is not None:
            to_write.append((layer, chain_id))
    if not dry_run and to_write:
        con.executemany(
            "UPDATE causal_chain_steps SET implication_layer = ? WHERE chain_id = ?",
            to_write,
        )
        con.commit()
    return BackfillReport(
        total_steps=len(rows),
        already_labeled=already_labeled,
        newly_financial=counts["financial"],
        newly_business=counts["business"],
        newly_competitive=counts["competitive"],
        left_unclassified=counts[None],
        applied=(not dry_run),
    )


# ---------------------------------------------------------------------------
# Step 3: the full Evidence Graph chain, read-only, per fact
# ---------------------------------------------------------------------------

@dataclass
class EvidenceChainStep:
    chain_id: int
    step_order: int
    statement: str
    inferred: bool
    implication_layer: str | None


@dataclass
class EvidenceChain:
    """Evidence -> Observation -> Financial/Business/Competitive Implication
    -> Investment Implication -> Confidence -> Missing Evidence, for ONE
    fact_id. Purely an assembly of rows that already exist -- no new claim
    is created or inferred by this function."""
    fact_id: int
    fact_type: str
    observation: str  # extracted_facts.description
    evidence_quotes: list[str]  # evidence.quoted_text, via extracted_facts + causal_chain_steps
    financial_steps: list[EvidenceChainStep]
    business_steps: list[EvidenceChainStep]
    competitive_steps: list[EvidenceChainStep]
    unclassified_steps: list[EvidenceChainStep]
    investment_implication_id: int | None
    action_recommendation: str | None
    confidence: float | None
    confidence_rationale: str | None
    status: str | None
    bull_case_delta: str | None
    bear_case_delta: str | None
    base_case_delta: str | None
    missing_evidence: list[str] = field(default_factory=list)  # open research_task_candidates + gap notes


def build_evidence_chain(con: sqlite3.Connection, fact_id: int) -> EvidenceChain:
    fact_row = con.execute(
        "SELECT fact_type, description, evidence_id FROM extracted_facts WHERE fact_id = ?",
        (fact_id,),
    ).fetchone()
    if fact_row is None:
        raise ValueError(f"no extracted_facts row for fact_id={fact_id}")
    fact_type, description, fact_evidence_id = fact_row

    step_rows = con.execute(
        "SELECT chain_id, step_order, statement, inferred, implication_layer, evidence_id "
        "FROM causal_chain_steps WHERE fact_id = ? ORDER BY step_order",
        (fact_id,),
    ).fetchall()

    evidence_ids = {fact_evidence_id} if fact_evidence_id is not None else set()
    steps_by_layer: dict[str | None, list[EvidenceChainStep]] = {
        "financial": [], "business": [], "competitive": [], None: []
    }
    for chain_id, step_order, statement, inferred, layer, ev_id in step_rows:
        if ev_id is not None:
            evidence_ids.add(ev_id)
        steps_by_layer[layer].append(EvidenceChainStep(
            chain_id=chain_id, step_order=step_order, statement=statement,
            inferred=bool(inferred), implication_layer=layer,
        ))

    evidence_quotes = []
    if evidence_ids:
        placeholders = ",".join("?" * len(evidence_ids))
        evidence_quotes = [r[0] for r in con.execute(
            f"SELECT quoted_text FROM evidence WHERE evidence_id IN ({placeholders})",
            tuple(evidence_ids),
        ).fetchall()]

    impl_row = con.execute(
        "SELECT implication_id, action_recommendation, confidence, confidence_rationale, "
        "status, bull_case_delta, bear_case_delta, base_case_delta "
        "FROM investment_implications WHERE fact_id = ? LIMIT 1",
        (fact_id,),
    ).fetchone()

    missing_evidence: list[str] = []
    implication_id = impl_row[0] if impl_row else None
    if implication_id is not None:
        tasks = con.execute(
            "SELECT description FROM research_task_candidates "
            "WHERE implication_id = ? AND status = 'open'",
            (implication_id,),
        ).fetchall()
        missing_evidence.extend(t[0] for t in tasks)
    else:
        missing_evidence.append("no investment_implications row exists for this fact")

    return EvidenceChain(
        fact_id=fact_id,
        fact_type=fact_type,
        observation=description,
        evidence_quotes=evidence_quotes,
        financial_steps=steps_by_layer["financial"],
        business_steps=steps_by_layer["business"],
        competitive_steps=steps_by_layer["competitive"],
        unclassified_steps=steps_by_layer[None],
        investment_implication_id=implication_id,
        action_recommendation=impl_row[1] if impl_row else None,
        confidence=impl_row[2] if impl_row else None,
        confidence_rationale=impl_row[3] if impl_row else None,
        status=impl_row[4] if impl_row else None,
        bull_case_delta=impl_row[5] if impl_row else None,
        bear_case_delta=impl_row[6] if impl_row else None,
        base_case_delta=impl_row[7] if impl_row else None,
        missing_evidence=missing_evidence,
    )


# ---------------------------------------------------------------------------
# Step 4: the layer-completeness / missing-evidence audit
# ---------------------------------------------------------------------------

def layer_gap_report(con: sqlite3.Connection) -> list[dict]:
    """For every fact with a causal chain, cross-reference the layers
    actually represented among its (backfilled) causal_chain_steps against
    the layers its OWN impact_assessments say are genuinely active
    (non-neutral, non-unknown direction). Flags a gap wherever a layer is
    impact-active but zero steps were classified into it -- e.g. fact 144's
    real, disclosed finding: competitive_advantage/long_term_moat are both
    'positive' (genuinely active), but zero of its 5 causal_chain_steps
    classify as 'competitive', because that reasoning lives only in
    impact_assessments.explanation text. This is a materially more precise
    signal than a bare `COUNT(DISTINCT implication_layer) < 3` check (Part
    3's original sketch), which would also flag a simple dividend fact that
    has NO real business/competitive content to find in the first place --
    that is not a gap, it is an accurate reflection of the fact."""
    fact_ids = [r[0] for r in con.execute(
        "SELECT DISTINCT fact_id FROM causal_chain_steps ORDER BY fact_id"
    ).fetchall()]
    report = []
    for fact_id in fact_ids:
        active_layers = {
            _CATEGORY_TO_LAYER[cat] for cat, direction in con.execute(
                "SELECT category, direction FROM impact_assessments WHERE fact_id = ?",
                (fact_id,),
            ).fetchall()
            if direction not in ("neutral", "unknown") and cat in _CATEGORY_TO_LAYER
        }
        represented_layers = {
            layer for (layer,) in con.execute(
                "SELECT DISTINCT implication_layer FROM causal_chain_steps "
                "WHERE fact_id = ? AND implication_layer IS NOT NULL",
                (fact_id,),
            ).fetchall()
        }
        gaps = sorted(active_layers - represented_layers)
        if gaps:
            report.append({
                "fact_id": fact_id,
                "active_layers": sorted(active_layers),
                "represented_layers": sorted(represented_layers),
                "missing_layers": gaps,
            })
    return report
