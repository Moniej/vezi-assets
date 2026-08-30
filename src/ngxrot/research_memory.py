"""Research OS -- Research Memory (2026-08-13, Investment OS end-to-end
build). Answers "have we tested something materially similar before?"
against the EXISTING hypothesis history -- the formal, statistically-
tested ledger (`hypotheses`/`experiments`, registry.sql, gates
alpha_engine.py) and the qualitative workspace ledger
(`research_hypotheses`/`research_findings`, research_workspace.py).

Deliberately deterministic, no LLM call anywhere in this module (per
explicit instruction: "do not create an LLM-dependent system if
deterministic retrieval is sufficient" -- a keyword/family-overlap
search over ~20 real hypotheses does not need semantic embeddings).
Read-only against registry.sqlite; never writes.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

# A small, disclosed, controlled vocabulary -- not exhaustive, expand as
# real new factor families get pre-registered. Matching is substring-based
# on lowercased text, deliberately simple and auditable (a human can read
# this list and know exactly why a match fired) rather than a black-box
# similarity model.
FACTOR_FAMILY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "momentum": ("momentum", "12-1", "3-6m", "trend"),
    "size": ("size", "small-cap", "smallest-cap", "market cap"),
    "liquidity": ("liquidity", "adtv", "illiquid", "turnover-budgeted"),
    "volatility": ("volatility", "low-vol", "low volatility"),
    "value": ("value", "book-to-market", "earnings yield", "p/e", "p/b"),
    "quality": ("quality", "piotroski", "accruals", "roe", "roa"),
    "profitability": ("profitability", "margin", "gross profit"),
    "dividend": ("dividend", "payer-status", "payer status", "yield"),
    "sector_rotation": ("sector rotation", "sector momentum", "catalyst"),
    "event_driven": ("event-driven", "event driven", "pead", "filing-window",
                     "announcement-window", "governance/management-change", "corporate action"),
    "macro_lead_lag": ("lead-lag", "lead lag", "brent", "oil-to-equity", "mpc announcement"),
    "regime": ("regime-conditional", "regime conditional", "regime-gated"),
    "interaction": (" x ", "interaction", "forensic decomposition"),
    "earnings": ("earnings acceleration", "earnings surprise", "earnings momentum"),
    "sentiment": ("sentiment", "news-derived"),
    "management_guidance": ("management guidance", "guidance"),
}

_WORD_RE = re.compile(r"[a-z][a-z0-9]{2,}")
_STOPWORDS = frozenset({
    "the", "and", "for", "with", "within", "vs", "long", "top", "docs", "family",
    "quarterly", "annual", "semiannual", "cross", "sectional", "cross-sectional",
})


def _tokenize(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall((text or "").lower()) if w not in _STOPWORDS}


def classify_families(text: str) -> set[str]:
    """Deterministic keyword match against FACTOR_FAMILY_KEYWORDS. A
    hypothesis can legitimately belong to more than one family (e.g. an
    interaction hypothesis references two base families) -- returns
    every family whose keyword appears, not just the best one."""
    low = (text or "").lower()
    return {family for family, keywords in FACTOR_FAMILY_KEYWORDS.items()
           if any(kw in low for kw in keywords)}


def _overlap_score(a: set[str], b: set[str]) -> float:
    """Jaccard similarity -- simple, symmetric, auditable. 0.0 if either
    side is empty (never divide by zero, never a spurious 1.0 on two
    empty sets)."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _conclusion_summary(conclusion: str | None, max_chars: int = 300) -> str | None:
    """First sentence-ish chunk of a real conclusion, not the whole
    multi-paragraph text -- a summary for a ranked list, not a
    replacement for reading the real conclusion (every result below
    carries the hypothesis_id a caller can look up directly)."""
    if not conclusion:
        return None
    if len(conclusion) <= max_chars:
        return conclusion
    return conclusion[:max_chars].rsplit(" ", 1)[0] + "..."


@dataclass
class PriorArtMatch:
    hypothesis_id: str
    source: str            # 'formal_ledger' | 'workspace'
    status: str
    description: str
    shared_families: tuple[str, ...]
    overlap_score: float
    conclusion_summary: str | None = None
    n_experiments: int = 0
    research_id: str | None = None   # workspace matches only


@dataclass
class PriorArtReport:
    candidate_families: tuple[str, ...]
    formal_matches: list[PriorArtMatch] = field(default_factory=list)
    workspace_matches: list[PriorArtMatch] = field(default_factory=list)
    related_findings: list[dict] = field(default_factory=list)

    def has_any_match(self) -> bool:
        return bool(self.formal_matches or self.workspace_matches)

    def summary_lines(self) -> list[str]:
        """Plain-text lines suitable for a pre-registration document's
        own 'prior art checked' section -- deterministic, reproducible
        given the same registry state, never phrased as a recommendation
        (this module reports what exists; it does not decide whether a
        new hypothesis is worth registering)."""
        if not self.has_any_match():
            return [f"No prior hypothesis found sharing a factor family with "
                    f"{{{', '.join(self.candidate_families) or 'none classified'}}}."]
        lines = []
        for m in self.formal_matches:
            lines.append(
                f"{m.hypothesis_id} [{m.source}, {m.status}] shares "
                f"{{{', '.join(m.shared_families)}}} (overlap={m.overlap_score:.2f}, "
                f"{m.n_experiments} experiment(s)): {m.conclusion_summary or '(no conclusion recorded)'}")
        for m in self.workspace_matches:
            lines.append(
                f"{m.hypothesis_id} [workspace, {m.status}] (research_id={m.research_id}) "
                f"shares {{{', '.join(m.shared_families)}}} (overlap={m.overlap_score:.2f}): "
                f"{m.description[:200]}")
        return lines


def find_similar_formal_hypotheses(reg: sqlite3.Connection, description: str,
                                   motivation: str = "", min_score: float = 0.08,
                                   limit: int = 10) -> list[PriorArtMatch]:
    """Searches the FORMAL, statistically-tested ledger (`hypotheses`,
    gates alpha_engine.py) -- the ledger that matters most for "haven't
    we already rejected this." Ranked by family overlap first (a shared,
    named factor family is a much stronger signal than incidental word
    overlap), then by raw token-overlap score as a tiebreak."""
    candidate_text = f"{description} {motivation}"
    candidate_families = classify_families(candidate_text)
    candidate_tokens = _tokenize(candidate_text)

    rows = reg.execute(
        "SELECT hypothesis_id, description, motivation, status, conclusion "
        "FROM hypotheses ORDER BY hypothesis_id").fetchall()
    matches = []
    for hyp_id, desc, motiv, status, conclusion in rows:
        text = f"{desc} {motiv}"
        families = classify_families(text)
        shared = candidate_families & families
        score = _overlap_score(candidate_tokens, _tokenize(text))
        if not shared and score < min_score:
            continue
        n_exp = reg.execute(
            "SELECT COUNT(*) FROM hypothesis_experiments WHERE hypothesis_id = ?",
            (hyp_id,)).fetchone()[0]
        matches.append(PriorArtMatch(
            hypothesis_id=hyp_id, source="formal_ledger", status=status, description=desc,
            shared_families=tuple(sorted(shared)), overlap_score=score,
            conclusion_summary=_conclusion_summary(conclusion), n_experiments=n_exp))
    matches.sort(key=lambda m: (len(m.shared_families), m.overlap_score), reverse=True)
    return matches[:limit]


def find_similar_workspace_hypotheses(reg: sqlite3.Connection, description: str,
                                      motivation: str = "", min_score: float = 0.08,
                                      limit: int = 10) -> list[PriorArtMatch]:
    """Searches the qualitative research-workspace ledger
    (`research_hypotheses`) -- exploratory/in-progress hypotheses that
    may never have reached (or may never reach) the formal ledger."""
    candidate_text = f"{description} {motivation}"
    candidate_families = classify_families(candidate_text)
    candidate_tokens = _tokenize(candidate_text)

    rows = reg.execute(
        "SELECT hypothesis_id, research_id, statement, status FROM research_hypotheses"
    ).fetchall()
    matches = []
    for hyp_id, research_id, statement, status in rows:
        families = classify_families(statement)
        shared = candidate_families & families
        score = _overlap_score(candidate_tokens, _tokenize(statement))
        if not shared and score < min_score:
            continue
        matches.append(PriorArtMatch(
            hypothesis_id=hyp_id, source="workspace", status=status, description=statement,
            shared_families=tuple(sorted(shared)), overlap_score=score,
            research_id=research_id))
    matches.sort(key=lambda m: (len(m.shared_families), m.overlap_score), reverse=True)
    return matches[:limit]


def find_related_findings(reg: sqlite3.Connection, description: str, motivation: str = "",
                          min_score: float = 0.10, limit: int = 10) -> list[dict]:
    """Research findings (research_workspace.py's `research_findings`) --
    narrower than a full hypothesis but often the first place a real
    data-quality issue or a dead end gets recorded ("MTNN's dividend
    data is unreliable pre-2019" is a finding, not a hypothesis)."""
    candidate_tokens = _tokenize(f"{description} {motivation}")
    rows = reg.execute(
        "SELECT finding_id, research_id, title, statement, status FROM research_findings"
    ).fetchall()
    out = []
    for finding_id, research_id, title, statement, status in rows:
        score = _overlap_score(candidate_tokens, _tokenize(f"{title} {statement}"))
        if score < min_score:
            continue
        out.append({"finding_id": finding_id, "research_id": research_id, "title": title,
                    "status": status, "overlap_score": score})
    out.sort(key=lambda d: d["overlap_score"], reverse=True)
    return out[:limit]


def check_prior_art(reg: sqlite3.Connection, description: str, motivation: str = "") -> PriorArtReport:
    """The single entry point: "have we tested something materially
    similar before?" Searches all three sources this platform already
    has real history in. Read-only, deterministic, reproducible given
    the same registry.sqlite state -- calling this twice with the same
    inputs against an unchanged database returns identical results."""
    candidate_families = classify_families(f"{description} {motivation}")
    return PriorArtReport(
        candidate_families=tuple(sorted(candidate_families)),
        formal_matches=find_similar_formal_hypotheses(reg, description, motivation),
        workspace_matches=find_similar_workspace_hypotheses(reg, description, motivation),
        related_findings=find_related_findings(reg, description, motivation),
    )
