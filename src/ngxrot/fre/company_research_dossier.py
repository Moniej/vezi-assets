"""FSI Phase 11: Complete Institutional Research Dossier
(docs/fre_runs/fsi_phase11_preregistration.md).

A pure, read-only COMPOSITION layer combining three already-frozen,
already-tested objects for one ticker: FRE-5/Phase 8's `CompanyThesis`
(bull/bear/base case + FSI concern/supplementary evidence, via
`company_thesis_360.as_of()`) and Phase 10's knowledge-graph identity/
lineage (via `get_entity_context()`). Neither underlying module is
modified.

`build_dossier()` calls `company_thesis_360.as_of()` ONCE (which itself
computes `company_memory_360.as_of()` exactly once) and `get_entity_
context()` directly ONCE (bypassing `entity_context.as_of()`, which
would otherwise recompute `company_memory_360.as_of()` a second time) --
see docs/fre_runs/fsi_phase11_implementation_log.md Entry 0 for the
disclosed reasoning.

`render_dossier()` reuses Phase 7's `render_report()` VERBATIM for the
Company Memory section (byte-identical to calling it directly on the
same `CompanyMemory360` snapshot) and appends two new, equally
deterministic, template-only sections -- Investment Thesis Evidence and
Knowledge Graph Context. No new reasoning, no synthesized conclusion
across sections, no combined score/rating/ranking/recommendation/
valuation/portfolio suggestion of any kind. No LLM call.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ngxrot.fre import company_thesis_360
from ngxrot.fre.company_memory_360 import CompanyMemory360
from ngxrot.fre.company_thesis import CompanyThesis
from ngxrot.fre.company_thesis_360 import FSIEvidenceItem
from ngxrot.fre.entity_context import EntityContext, get_entity_context
from ngxrot.fre.financial_reasoning_report import render_report

# Two small, independent copies of Phase 7's own formatting rules --
# financial_reasoning_report.py is frozen and must not be modified, even
# to make its private helpers public (see implementation log Entry 1).
_CONFIDENCE_TIER_LABELS = {
    "direct_reported": "direct_reported (literally stated in the source filing)",
    "mapped_equivalent": "mapped_equivalent (derived from a differently-labeled but "
                          "structurally equivalent filing line)",
    "derived": "derived (computed from other reported figures via a disclosed formula)",
    "interpretation": "interpretation",
}
_NULL_CONFIDENCE_LABEL = (
    "confidence tier NOT RECORDED -- this fact predates the confidence_tier "
    "column introduced in FSI Phase 2 and was never backfilled; treat as "
    "UNKNOWN confidence, not as equivalent to a recorded tier"
)


def _format_confidence_tier(tier: str | None) -> str:
    if tier is None:
        return _NULL_CONFIDENCE_LABEL
    return _CONFIDENCE_TIER_LABELS.get(tier, tier)


def _format_value(value_numeric: float | None, value_text: str | None) -> str:
    parts = []
    if value_numeric is not None:
        parts.append(f"{value_numeric:.6f}")
    if value_text is not None:
        parts.append(value_text)
    return " / ".join(parts) if parts else "(no value -- see status below)"


@dataclass
class CompanyResearchDossier:
    ticker: str
    as_of_date: str
    thesis: CompanyThesis
    memory: CompanyMemory360
    graph: EntityContext
    concern_evidence: list[FSIEvidenceItem]
    supplementary_evidence: list[FSIEvidenceItem]


def build_dossier(con: sqlite3.Connection, ticker: str, as_of_date: str) -> CompanyResearchDossier:
    """Single-ticker only. Calls company_thesis_360.as_of() exactly once
    (thesis + memory + concern/supplementary evidence, one memory
    computation) and get_entity_context() exactly once (bypassing
    entity_context.as_of()'s own redundant memory call)."""
    bundle = company_thesis_360.as_of(con, ticker, as_of_date)
    graph = get_entity_context(con, ticker, as_of_date)
    return CompanyResearchDossier(
        ticker=ticker, as_of_date=as_of_date,
        thesis=bundle.thesis, memory=bundle.memory, graph=graph,
        concern_evidence=bundle.concern_evidence,
        supplementary_evidence=bundle.supplementary_evidence,
    )


def _render_evidence_item(item: FSIEvidenceItem) -> list[str]:
    return [
        f"- **{item.metric}** ({item.period_start or 'n/a'} to {item.period_end or 'n/a'}): "
        f"conclusion_id={item.conclusion_id}, conclusion_type={item.conclusion_type}",
        f"  - Status: {item.status}",
        f"  - Value: {_format_value(item.value_numeric, item.value_text)}",
        f"  - Confidence tier: {_format_confidence_tier(item.confidence_tier)}",
        f"  - Method: {item.method}",
        f"  - Limitations: {item.limitations}",
        "",
    ]


def _render_thesis_section(thesis: CompanyThesis, concern_evidence: list[FSIEvidenceItem],
                            supplementary_evidence: list[FSIEvidenceItem]) -> list[str]:
    lines = ["## Investment Thesis Evidence", ""]
    lines.append(
        "*This section restates FRE-5's own CompanyThesis fields and FSI Phase 8's "
        "concern/supplementary evidence verbatim -- no new synthesis, no combined "
        "score, no recommendation. `is_pilot=True` means this thesis is an "
        "explainable research artifact, not a statistically validated product.*"
    )
    lines.append("")
    lines.append(f"- is_pilot: {thesis.is_pilot}")
    lines.append(f"- Bull case: {thesis.bull_case or '(none recorded)'}")
    lines.append(f"- Bear case: {thesis.bear_case or '(none recorded)'}")
    lines.append(f"- Base case: {thesis.base_case or '(none recorded)'}")
    lines.append(f"- Contradiction note: {thesis.contradiction_note or '(none)'}")
    lines.append(f"- Key risks: {thesis.key_risks or '(none recorded)'}")
    lines.append(f"- Catalysts: {thesis.catalysts or '(none recorded)'}")
    lines.append(f"- Competitive position: {thesis.competitive_position}")
    lines.append(f"- Financial signal summary: {thesis.financial_signal_summary}")
    lines.append(f"- Management assessment: {thesis.management_assessment}")
    lines.append(f"- Capital allocation assessment: {thesis.capital_allocation_assessment}")
    lines.append(f"- Confidence: {thesis.confidence if thesis.confidence is not None else '(not recorded)'}")
    lines.append(f"- Confidence rationale: {thesis.confidence_rationale or '(none)'}")
    lines.append(f"- Market reaction cross-check: {thesis.market_reaction_crosscheck}")
    lines.append(f"- Excluded blocked_by_self_critique count: {thesis.excluded_blocked_count}")
    lines.append(f"- Missing evidence: {thesis.missing_evidence or '(none recorded)'}")
    lines.append(f"- Source implication_ids: {thesis.source_implication_ids or '(none)'}")
    lines.append("")

    lines.append("### Thesis History")
    lines.append("")
    if not thesis.thesis_history:
        lines.append("No thesis history entries.")
    else:
        for h in thesis.thesis_history:
            lines.append(
                f"- implication_id={h.implication_id} | filed {h.filing_date} | "
                f"direction={h.direction} | magnitude={h.magnitude} | confidence={h.confidence}"
            )
    lines.append("")

    lines.append("### FSI Concern Evidence (fired financial-health flags)")
    lines.append("")
    if not concern_evidence:
        lines.append("No fired concern flags as of this date.")
        lines.append("")
    else:
        for item in sorted(concern_evidence, key=lambda i: (i.metric, i.period_end or "")):
            lines.extend(_render_evidence_item(item))

    lines.append("### FSI Supplementary Evidence (ratios, trends, non-fired flags, insufficient_data)")
    lines.append("")
    if not supplementary_evidence:
        lines.append("No supplementary evidence as of this date.")
        lines.append("")
    else:
        for item in sorted(supplementary_evidence, key=lambda i: (i.metric, i.period_end or "")):
            lines.extend(_render_evidence_item(item))

    return lines


def _render_graph_section(graph: EntityContext) -> list[str]:
    lines = ["## Knowledge Graph Context", ""]
    lines.append(
        "*This section restates FSI Phase 9/10's own knowledge-graph fields "
        "verbatim -- no graph traversal beyond this ticker's own direct "
        "relationships, no centrality metric, no inferred relationship.*"
    )
    lines.append("")
    if graph.entity_id is None:
        lines.append(
            "No knowledge-graph presence is yet KNOWN for this ticker as of this "
            "date -- this means no graph node has been recorded as of this date, "
            "NOT that the company did not exist."
        )
        lines.append("")
        return lines

    lines.append(f"- entity_id: {graph.entity_id}")
    lines.append(f"- canonical_name: {graph.canonical_name}")
    lines.append(f"- first_seen_doc_id: {graph.first_seen_doc_id}")
    lines.append("")
    lines.append("### Relationships")
    lines.append("")
    if not graph.relationships:
        lines.append("No known relationships as of this date.")
        lines.append("")
    else:
        for r in graph.relationships:
            lines.append(
                f"- relationship_id={r.relationship_id} | relation_type={r.relation_type} | "
                f"direction={r.direction} | counterpart={r.counterpart_canonical_name} "
                f"(entity_id={r.counterpart_entity_id}) | valid_from={r.valid_from} | "
                f"valid_to={r.valid_to or '(ongoing)'} | confidence={r.confidence} | "
                f"source_evidence_id={r.source_evidence_id}"
            )
        lines.append("")
    return lines


def render_dossier(dossier: CompanyResearchDossier) -> str:
    """Pure, deterministic: identical input always produces identical
    output. The Company Memory portion is byte-identical to calling
    render_report() directly on the same CompanyMemory360 snapshot."""
    lines = [render_report(dossier.memory), ""]
    lines.append("---")
    lines.append("")
    lines.extend(_render_thesis_section(dossier.thesis, dossier.concern_evidence,
                                          dossier.supplementary_evidence))
    lines.append("---")
    lines.append("")
    lines.extend(_render_graph_section(dossier.graph))
    return "\n".join(lines)
