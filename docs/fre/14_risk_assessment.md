# FRE Part 14 — Risk Assessment

*Consolidation + new cross-cutting risks. Most individual risks were
already named where they arise (Parts 1-11); this document (a) indexes
them by category so they can be tracked as a set, and (b) adds
program-level risks that only become visible when the fifteen parts are
viewed together. See `docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Categorize every material risk in this program — technical, research,
architectural, data, evaluation, scalability, overfitting, market-specific,
deployment — with likelihood/impact framed qualitatively (this platform's
own discipline: never invent a numeric probability with no evidence behind
it), current mitigation status, and origin, so nothing is lost across
fifteen separate documents.

## Technical risks

| Risk | Origin | Mitigation status |
|---|---|---|
| Retokenization / cross-session generation non-determinism in local model inference | LIM research (confirmed, not hypothesized — `rb3b_determinism_check.py`) | Confirmed and designed around for LIM's own eval methodology; **not yet accounted for** in any FRE design that might eventually consume LIM output — flag for whenever LIM becomes a candidate provider |
| **New — infrastructure fragility on the current single-machine setup** | Observed repeatedly this session: OS memory-pressure crashes (RB-1/RB-2/RB-2b/RB-3), a GPU-memory conflict from an unrelated process (RB-3b), an unattended-process external termination (RB-3c Phase 0) | Each incident individually diagnosed and disclosed honestly; **no systemic fix exists** — this is a real, recurring operational risk for any FRE component that runs local, long, unattended compute, not a one-off nuisance |
| **New — external-vendor dependency and cost** | Gemini is the *only* provider that has ever produced a real reasoning result on this platform; the real pilot run hit Google's free-tier quota (20 requests/day) mid-run | A paid-tier decision is an unavoidable, undiscussed cost the moment FRE reasoning volume scales past pilot size — not resolved by any design document in this program, flagged here as a real gap |
| Retrieval-first context sizing at 32K-token native context | LIM Architecture §2.1 | Already addressed by design (real observed max: 35,636 tokens in one call exceeded even Qwen3's native window before chunking) — the retrieval-first design is the actual mitigation, not a config choice alone |

## Research risks

| Risk | Origin | Mitigation status |
|---|---|---|
| LIM's `self_critique_quality` remaining at 0.0 across every completed evaluation, with mode collapse as the leading confirmed mechanism | Part 13 (Gap Analysis) | Actively under investigation via RB-3c; **not resolved**, and this program does not assume it will be |
| Ontology edges (Part 1) encoding an oversimplified or wrong causal mechanism with unearned authority | Part 1 Risks | `evidence_status` tagging + self-critique mechanical check; not a complete solution — a wrong edge can still exist at `theoretical` status and mislead before it's ever tested |
| Fold-weight parameter (Part 7) and calibration-metric floor (Part 11) both genuinely unstudied | Part 12 Roadmap | Scoped as their own pre-registered, single-variable experiments (FRE-5, FRE-10) — not guessed at in this program |

## Architectural risks

| Risk | Origin | Mitigation status |
|---|---|---|
| Hard-boundary erosion (`ngxrot.documents` → `alpha_engine.py`) under convenience pressure | Named repeatedly (Parts 8, 9) | Procedural (code review) + a proposed mechanical import-graph check (architecture doc §9, FRE-9's review checkpoint) — enforcement is process-dependent, not automatic today |
| **New — config/taxonomy sprawl** | This program alone proposes `relation_taxonomy.toml`, `financial_ontology.toml`, `valuation_method_eligibility.toml`, plus extensions to `fact_taxonomy.toml` — on top of the platform's existing `event_taxonomy.toml`/`document_taxonomy.toml`/`llm_provider.toml` | Each individually justified by the "config change, not code change" convention; **the aggregate is a real, growing audit surface** no single document in this program addresses — a future consolidated taxonomy-registry review is a legitimate future extension, not built here |
| Conflating a deterministic calculation (Part 8's Valuation Engine) with a validated signal despite correct architectural framing | Part 8 Risks | Enforced by routing through Discovery-candidate pipeline only, never direct-to-`alpha_engine.py` — named as "the most likely single point of governance erosion in the entire FRE design if implemented carelessly" |

## Data risks

| Risk | Origin | Mitigation status |
|---|---|---|
| OCR coverage gap (36% of Phase A's archive) compounding across nearly every text-dependent dataset | Part 10 Risks | Unresolved, open since 2026-07-16 — the single oldest unresolved item this whole program inherits |
| Financial-statements dataset acquisition cost/quality/vendor-dependency | Part 10/12/13 | Its own dedicated, owner-scoped phase (FRE-6) — not rushed, not assumed |
| Ownership/shareholding data sensitivity | Part 2 Risks | Elevated human-review bar proposed, never above `unvalidated_ai_interpretation` without review |
| **New — disclosure-quality heterogeneity across NGX issuers** | Not previously named directly: some issuers' filings are far more informative/complete than others (a real, expected feature of an emerging-market exchange), which means Company Memory/Thesis coverage will be systematically uneven by issuer, not just by document-processing gap | No mitigation designed — `coverage_assessment.py`'s existing 10 (soon 11, Part 5) dimensions already surface this per-ticker rather than hiding it, which is the correct posture, but does not fix the underlying unevenness |
| **New — survivorship/attention bias in the archive** | Named in Part 5 Risks | Disclosed via `coverage_note`, not solved |

## Evaluation risks

| Risk | Origin | Mitigation status |
|---|---|---|
| Metric gaming via mechanical-check-shaped output | Part 11 Risks | Paired human review, consistent with LIM's own "exact-match is a known blind spot" lesson |
| Calibration's time-dependent floor being skipped under pressure to report a number | Part 11 | Explicitly forbidden in this design; enforcement is a documentation/process discipline, not a technical lock |
| A false-negative evaluation harness (passes everything regardless of quality) | Part 12, FRE-10's own stop condition | A dedicated injected-regression sanity check before the harness is trusted for gating |

## Scalability risks

| Risk | Origin | Mitigation status |
|---|---|---|
| **New — entity-resolution human-review queue becoming a bottleneck at volume** | Every new relation type (Part 2), every new fact type (Part 5's ownership, Part 6's cross-document corroboration) adds volume to the *same* existing human-review queue (architecture doc §4.2) | Not addressed by any document in this program — worth flagging directly: this program significantly *increases load* on a queue that was sized for a much smaller pilot scope, and no staffing/cadence decision has been made (architecture doc §13's open decision #7, inherited unchanged and now more urgent) |
| **New — 2-3 hop SQL join assumption at larger graph scale** | The Knowledge Graph design (architecture doc §5, reaffirmed in Part 2) explicitly chose plain SQL over a graph database because no query has ever needed more than 2-3 hops at 11,534-document scale | Untested at 10x+ document/entity volume — a legitimate future re-evaluation trigger (already named as such in the architecture doc), not a current problem |
| LIM's 6GB-VRAM local hardware ceiling, if LIM is ever asked to serve real FRE-scale reasoning volume | `docs/LIM_ARCHITECTURE.md` §2.3/2.4 | An upgrade path exists on paper (bigger GPU / cloud burst training) but is untested at any real serving volume |

## Overfitting risks

| Risk | Origin | Mitigation status |
|---|---|---|
| A fold-weight or valuation-triangulation parameter tuned to a small pilot set failing to generalize | Parts 8, 12 | Named explicitly, pre-registration required before trusting a result (FRE-5, FRE-7) |
| A small, analyst-authored strategy-narrative gold set (tens of pairs) not representative of the full space of real strategy shifts | Part 10 | Disclosed as deliberately small ("gold set used sparingly and last," per the LIM precedent) — a known limitation, not a hidden one |
| Ontology `evidence_status` overfit to the specific hypotheses tested so far (only H-004/H-005/H-008 currently mapped) | Part 1 | The ontology's own design allows arbitrarily many more mappings as `docs/FACTOR_REGISTRY.md` grows — today's coverage is a starting seed, explicitly not comprehensive |

## Market-specific (NGX) risks

| Risk | Origin | Mitigation status |
|---|---|---|
| Thin liquidity distorting the reaction-check mechanism | Part 6 Risks | Named, flagged for future liquidity-aware confidence discounting, not yet designed in full |
| Regime sensitivity of any causal claim (the H-008 lesson: NGX 2016-2026's violent regime transitions can flip a sign that looked stable in a calmer market) | Part 1 (`ngx_rejected`/`ngx_mixed` evidence status exists partly for this) | Ontology's evidence-status design is the direct mitigation; genuinely new regime shifts will still surprise it — an inherent limit of any evidence-based system, disclosed rather than claimed away |
| **New — single-exchange concentration of the entire FRE program** | Every part of this design is NGX-specific by data, even where architecturally exchange-agnostic (Part 1's core ontology skeleton, Part 2's entity model) | Consistent with the charter's own explicit current scope (`docs/FUND_ALPHA_CHARTER.md`: "the objective is never NGX... pointed wherever alpha exists" as a long-term aspiration, not a current commitment) — the multi-exchange extension points (Module 12) exist on paper throughout this program but are untested by construction |

## Deployment risks

| Risk | Origin | Mitigation status |
|---|---|---|
| **New — no data-governance/access-control design exists for a future institutional research product** | Not addressed anywhere in this program — ownership data (Part 2), management assessments (Part 7), and watchlists (Part 9) are all sensitive research outputs with no described access-control, audit-log-for-reads, or redistribution policy | **Genuinely out of scope for this design pass** (the owner's brief was architecture/research, not a security/compliance design) — flagged explicitly here so it is not silently assumed solved |
| Gemini API cost at real production volume (see Technical risks) | Part 10/14 | Unresolved, same entry as above, cross-referenced deliberately since it is both a technical and a deployment concern |
| LIM's local-machine-only deployment model, if ever promoted | `docs/LIM_ARCHITECTURE.md` §5.1 | `llama-server` architecture designed but never load-tested at institutional scale |

## Alternatives considered

1. **Score every risk with a numeric likelihood/impact matrix.** Rejected
   — this platform's own discipline explicitly refuses invented numeric
   thresholds with no evidence behind them (Reasoning Engine Spec §6); a
   qualitative table with honest "not addressed"/"unresolved" labels is
   more truthful than a spuriously precise risk score.
2. **Only list risks already named per-part, with no new cross-cutting
   ones.** Rejected — several real risks (config sprawl, entity-resolution
   queue load, vendor cost, data governance) are only visible when all
   fifteen parts are considered together, and a pure index would have
   missed them.

## Trade-offs

- Naming genuinely unaddressed risks (data governance, vendor cost,
  queue-load scaling) without proposing solutions is intentional — this
  document's job is honest surfacing, not scope creep into designing
  security/compliance/cost-management systems that were not asked for.

## Risks (of this document itself)

- A risk assessment written by the same process that produced the design
  it is assessing has an inherent blind-spot risk — an independent review
  pass (the owner's own judgment, or a future dedicated red-team exercise)
  would likely surface risks this document missed. Disclosed, not solved.

## Future extensions

- A living risk register, updated at each Part 12 phase checkpoint
  (mirroring Part 13's same "living document" future extension) rather
  than a point-in-time snapshot.
- A dedicated data-governance/access-control design pass, once (and if)
  the owner scopes it — explicitly not started here.

## Dependencies

- Every part in this program (1-13) as the source of each individual risk;
  no new dependency beyond re-reading them together.
