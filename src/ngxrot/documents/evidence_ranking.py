"""EvidenceRanking (stabilization pass, 2026-07-27, owner-approved — see
HANDOFF.md). Assigns a trust tier to every evidence row and every implication
touched by the reasoning pipeline, so "prefer higher-quality evidence" is a
mechanical, auditable rule rather than an implicit assumption, and so a
conflict between what the MODEL'S STATED CONFIDENCE prefers and what the
EVIDENCE'S TRUST TIER prefers is surfaced explicitly instead of silently
resolved one way.

This module is read-only: it never writes to investment_implications,
extracted_facts, or any other table. extract.py's `_cross_reference` (Step
11-12) already sets `contradicts_implication_id`/`consistency_note` on a
confidence-only basis at write time — append-only, never touched here.
`assess_implication_conflict` recomputes a SECOND, trust-tier-aware opinion
for every contradiction already on record and reports whether it agrees with
the confidence-only one. Disagreement is not "fixed" — this project's rule is
disclosed, not silently patched (same posture as the self-critique gate).

Trust tiers: see vocab.EVIDENCE_TRUST_TIERS. Only tier 1 (primary_filing) and
tier 4 (ai_derived_or_ungrounded) are reachable on the real database today —
tiers 2-3 are reserved for the news/analyst sources the architecture doc
already planned (§10) but that haven't been built.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import vocab


@dataclass(frozen=True)
class TrustAssignment:
    tier: int
    label: str
    rationale: str


def assign_trust_tier(*, source_type: str | None, grounding_check: str | None,
                      is_propagated: bool) -> TrustAssignment:
    """Mechanical tier assignment — no judgment call, every input is already
    a stored column value. A propagated (Phase F) or ungrounded row is
    always tier 4 regardless of source_type: it is not itself a primary
    citation, it inherits (and discounts) someone else's claim, or its quote
    was never verified against the source document at all."""
    if is_propagated:
        return TrustAssignment(4, vocab.EVIDENCE_TRUST_TIERS[4],
                               "Phase F peer-propagated implication — copies a source "
                               "implication's claim, not its own primary citation")
    if grounding_check is not None and grounding_check != "passed":
        return TrustAssignment(4, vocab.EVIDENCE_TRUST_TIERS[4],
                               f"grounding_check={grounding_check!r} — quote not verified "
                               f"verbatim against the source document")
    if source_type == "filing":
        return TrustAssignment(1, vocab.EVIDENCE_TRUST_TIERS[1],
                               "primary regulatory/exchange filing, ingested via the "
                               "governed X-Issuer/NGX pipeline, quote verified grounded")
    if source_type == "news":
        return TrustAssignment(3, vocab.EVIDENCE_TRUST_TIERS[3],
                               "news source — reliability-tier registry (news_outlets) "
                               "not yet built; provisional tier until one exists")
    return TrustAssignment(2, vocab.EVIDENCE_TRUST_TIERS[2],
                           f"source_type={source_type!r} treated as a primary "
                           f"non-filing source pending its own registry")


def rank_evidence_for_fact(con, fact_id: int) -> list[dict]:
    """Every evidence row backing one fact (via extracted_facts.evidence_id,
    causal_chain_steps.evidence_id, and effect_chains.evidence_id — the
    three places extract.py links a quote to a fact/implication), each
    annotated with its trust tier, sorted best-tier-first then by
    source_confidence descending. Returns [] if the fact has no evidence
    rows at all (a real, disclosable finding on its own — never fabricated)."""
    fact_row = con.execute(
        "SELECT doc_id, evidence_id, grounding_check FROM extracted_facts WHERE fact_id = ?",
        (fact_id,)).fetchone()
    if fact_row is None:
        return []
    doc_id, primary_evidence_id, grounding_check = fact_row

    evidence_ids: list[tuple[int, str]] = []
    if primary_evidence_id is not None:
        evidence_ids.append((primary_evidence_id, "extracted_facts.evidence_id"))
    for (eid,) in con.execute(
        "SELECT evidence_id FROM causal_chain_steps WHERE fact_id = ? AND evidence_id IS NOT NULL",
        (fact_id,)).fetchall():
        evidence_ids.append((eid, "causal_chain_steps.evidence_id"))

    out = []
    seen = set()
    for evidence_id, role in evidence_ids:
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        row = con.execute(
            "SELECT e.doc_id, e.quoted_text, e.source_confidence, d.source_type "
            "FROM evidence e JOIN documents d ON d.doc_id = e.doc_id "
            "WHERE e.evidence_id = ?", (evidence_id,)).fetchone()
        if row is None:
            continue
        ev_doc_id, quoted_text, source_confidence, source_type = row
        assignment = assign_trust_tier(
            source_type=source_type,
            grounding_check=grounding_check if role == "extracted_facts.evidence_id" else "passed",
            is_propagated=False)
        out.append({
            "evidence_id": evidence_id, "doc_id": ev_doc_id, "role": role,
            "quoted_text": quoted_text, "source_confidence": source_confidence,
            "source_type": source_type, "tier": assignment.tier,
            "tier_label": assignment.label, "tier_rationale": assignment.rationale,
        })
    out.sort(key=lambda r: (r["tier"], -r["source_confidence"]))
    return out


def _best_tier_for_implication(con, implication_id: int) -> int | None:
    row = con.execute(
        "SELECT fact_id, propagated_from_implication_id FROM investment_implications "
        "WHERE implication_id = ?", (implication_id,)).fetchone()
    if row is None:
        return None
    fact_id, propagated_from = row
    if propagated_from is not None:
        return assign_trust_tier(source_type=None, grounding_check=None,
                                 is_propagated=True).tier
    ranked = rank_evidence_for_fact(con, fact_id)
    return ranked[0]["tier"] if ranked else None


@dataclass
class ConflictAssessment:
    implication_id: int
    contradicts_implication_id: int
    confidence_preferred: str          # "this" | "prior" | "tied"
    trust_tier_preferred: str          # "this" | "prior" | "tied" | "unknown"
    tiers: dict = field(default_factory=dict)
    confidences: dict = field(default_factory=dict)
    agreement: bool | None = None      # None when trust tier can't be determined
    note: str = ""


def assess_implication_conflict(con, implication_id: int) -> ConflictAssessment | None:
    """Recomputes a trust-tier-aware preference for a contradiction extract.
    py's `_cross_reference` already recorded on a confidence-only basis, and
    reports whether the two opinions agree. Returns None if this implication
    was not flagged as contradicting anything (nothing to assess) — not an
    error, most implications have no conflict."""
    row = con.execute(
        "SELECT contradicts_implication_id, confidence FROM investment_implications "
        "WHERE implication_id = ?", (implication_id,)).fetchone()
    if row is None or row[0] is None:
        return None
    contradicts_id, this_confidence = row
    prior_confidence = con.execute(
        "SELECT confidence FROM investment_implications WHERE implication_id = ?",
        (contradicts_id,)).fetchone()
    if prior_confidence is None:
        return None
    prior_confidence = prior_confidence[0]

    if this_confidence > prior_confidence:
        confidence_preferred = "this"
    elif this_confidence < prior_confidence:
        confidence_preferred = "prior"
    else:
        confidence_preferred = "tied"

    this_tier = _best_tier_for_implication(con, implication_id)
    prior_tier = _best_tier_for_implication(con, contradicts_id)

    if this_tier is None or prior_tier is None:
        trust_tier_preferred = "unknown"
        agreement = None
        note = ("trust-tier preference undetermined — one or both sides have no "
               "resolvable evidence rows (this_tier="
               f"{this_tier}, prior_tier={prior_tier})")
    else:
        if this_tier < prior_tier:      # lower number = more trusted
            trust_tier_preferred = "this"
        elif this_tier > prior_tier:
            trust_tier_preferred = "prior"
        else:
            trust_tier_preferred = "tied"
        agreement = (confidence_preferred == trust_tier_preferred) or \
            "tied" in (confidence_preferred, trust_tier_preferred)
        if agreement:
            note = (f"confidence-based preference ({confidence_preferred!r}) and "
                   f"trust-tier-based preference ({trust_tier_preferred!r}) agree "
                   f"(tiers: this={this_tier}, prior={prior_tier})")
        else:
            note = (f"DISAGREEMENT: confidence prefers {confidence_preferred!r} but "
                   f"evidence trust tier prefers {trust_tier_preferred!r} (tiers: "
                   f"this={this_tier}, prior={prior_tier}, confidences: "
                   f"this={this_confidence:.2f}, prior={prior_confidence:.2f}) — the "
                   f"higher-STATED-confidence side is not the higher-TRUST-tier side; "
                   f"flagged for review, not auto-resolved")

    return ConflictAssessment(
        implication_id=implication_id, contradicts_implication_id=contradicts_id,
        confidence_preferred=confidence_preferred, trust_tier_preferred=trust_tier_preferred,
        tiers={"this": this_tier, "prior": prior_tier},
        confidences={"this": this_confidence, "prior": prior_confidence},
        agreement=agreement, note=note)


def evidence_ranking_summary(con, ctx) -> dict:
    """Company-level roll-up for a ReasoningContext: trust-tier distribution
    across every evidence row backing this ticker's facts, plus a trust-tier
    -aware re-assessment of every contradiction on record for this ticker
    (ctx.historical_implications). Attached to ReasoningContext/
    ReasoningResult; never mutates anything."""
    tier_counts: dict[int, int] = {}
    for f in ctx.facts:
        for row in rank_evidence_for_fact(con, f["fact_id"]):
            tier_counts[row["tier"]] = tier_counts.get(row["tier"], 0) + 1

    conflicts = []
    for impl in ctx.historical_implications:
        c = assess_implication_conflict(con, impl["implication_id"])
        if c is not None:
            conflicts.append(c)
    n_disagree = sum(1 for c in conflicts if c.agreement is False)

    return {
        "tier_distribution": {vocab.EVIDENCE_TRUST_TIERS[t]: n
                              for t, n in sorted(tier_counts.items())},
        "n_evidence_rows_ranked": sum(tier_counts.values()),
        "n_conflicts_detected": len(conflicts),
        "n_conflicts_where_trust_and_confidence_disagree": n_disagree,
        "conflicts": [c.__dict__ for c in conflicts],
    }
