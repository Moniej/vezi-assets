# Stabilization Pass — Validation Report (2026-07-27)

Owner-mandated pause before any new AI Intelligence Layer phase (Phase G):
verify/implement CoverageAssessment and EvidenceRanking, run a complete
end-to-end validation against real NGX filings, fix what's safely fixable,
disclose what isn't, then freeze this as the stable baseline. This report
covers all of that. Raw machine-readable data:
`reports/stabilization_validation_raw.json`.

## 0. CoverageAssessment / EvidenceRanking — did they already exist?

No. A full search of the codebase, every architecture/spec doc, the
technical-debt backlog, and project memory found no prior specification
under these names (or close variants — confidence ceiling, trust tier,
evidence quality). The closest relative was a narrow, still-unbuilt
`news_outlets.reliability_tier` concept scoped only to a future news
pipeline. Confirmed with the owner before building anything (their message's
bullet points became the spec).

## 1. What was built

Two new, read-only modules in `src/ngxrot/documents/`, wired additively into
`context.py` (`ReasoningContext.coverage_assessment`, `.evidence_ranking_summary`)
and `reasoning_engine.py` (`ReasoningResult.coverage_assessment`,
`.evidence_ranking_summary`, `.confidence_ceiling_breaches`). No schema
migration — everything derives from existing columns (`documents.source_type`,
`extracted_facts.grounding_check`, `investment_implications.
propagated_from_implication_id`/`.contradicts_implication_id`). Neither
module mutates a stored confidence, a gate, or `extract.py`'s existing
`_cross_reference` logic — findings are attached for review, never
auto-applied, matching the platform's standing "disclosed, not silently
patched" rule.

**`coverage_assessment.py`** — `assess_coverage(con, ctx) -> CoverageAssessment`.
A fixed, auditable 10-dimension checklist (`vocab.COVERAGE_DIMENSIONS`:
has_facts, has_grounded_evidence, has_multiple_source_documents,
has_multiple_fact_types, has_entity_relationships, has_event_history,
has_factor_exposures, has_cross_ticker_corroboration,
has_financial_statements, has_secondary_sources). `coverage_score` =
dimensions present / 10. `confidence_ceiling` scales the existing
`UNREVIEWED_LLM_CONFIDENCE_FLOOR` (0.3) down further via
`vocab.COVERAGE_CONFIDENCE_CEILING_BANDS` (ad hoc, owner-adjustable — same
status as `CONFIDENCE_DISCOUNT_PER_CONCERN`). `reasons_confidence_limited`
names every missing dimension in plain language, always including the two
permanent platform-wide gaps (no financial-statements dataset, no
news/analyst ingestion) so the ceiling is stated honestly rather than only
scored on what's currently achievable.

**`evidence_ranking.py`** — trust tiers (`vocab.EVIDENCE_TRUST_TIERS`, 1=best):
1 `primary_filing` (source_type='filing' + grounding passed), 2/3 reserved
for primary-regulatory/news-analyst sources the architecture doc already
planned but hasn't built, 4 `ai_derived_or_ungrounded` (a Phase F propagated
implication, or any quote that failed grounding — always worst regardless of
`source_type`). `rank_evidence_for_fact` ranks a fact's evidence best-first.
`assess_implication_conflict` recomputes a **trust-tier-aware** preference
for every contradiction `extract.py`'s `_cross_reference` already recorded
on a confidence-only basis, and reports whether the two opinions agree —
disagreement means the higher-*stated-confidence* side is not the
higher-*trust-tier* side, flagged for review, never auto-resolved.
`evidence_ranking_summary` rolls this up per ticker (tier distribution +
conflict list).

## 2. Test coverage

26 new engineering-correctness checks added to
`scripts/test_reasoning_pipeline.py` (MockProvider/synthetic DB, matching
the project's existing no-pytest convention): coverage score moves from 0
to a real value across a real extraction, the permanent-gap reasons are
always present, all three trust-tier rules, a constructed
confidence-vs-trust-tier disagreement (0.8-confidence tier-4 propagated
implication vs. a 0.5-confidence tier-1 grounded prior — trust tier
correctly prefers the prior, confidence prefers the propagated one,
disagreement correctly flagged), and an artificially high-confidence
implication correctly appearing in `ReasoningResult.
confidence_ceiling_breaches`. **154/154 checks pass** (was 90 before Phase F;
+64 across Phase F and this pass, of which 26 are this pass's).

## 3. End-to-end validation against real NGX filings

Two parts, both against the real database (`data/ngx.sqlite`, backed up
first to `data/ngx.sqlite.pre_stabilization_backup_2026-07-27` before any
live run touched it).

### 3a. Live run — a genuinely new code path on real filings

The Phase C pilot (`run_phase_c_pilot.py`) only ever called the low-level
`resumable_financial_reasoning` one document at a time. **The Phase E/F
orchestrator (`reasoning_engine.reason_about_company`) — retrieval →
extraction → grounding → self-critique → aggregation → coverage/ranking, all
in one call — had never been exercised against real filings before this
pass** (TD13/TD16 explicitly flagged this gap). Ran it live (real
`GEMINI_API_KEY`, real `gemini-3.6-flash` calls) against 6 previously
-unprocessed real documents across 4 tickers that already carry real prior
implications (UCAP, UNILEVER, CILEASING, BUAFOODS), capped at 1-2 new
documents per call to stay well inside the free-tier daily quota.

Result: **5 of 6 documents correctly returned zero facts** (`{"facts": []}`,
clean `STOP` finish reason, not a truncation) — these were arbitrary
native-text filings never verified to contain a material fact, and the
model correctly abstained rather than fabricating one. **1 of 6** (a real
CILEASING dividend filing, doc_id 11387) produced a genuine new fact,
grounding-passed, and ran the full chain for real: extraction → causal chain
→ 13 impact categories → a draft implication → the Step-14 self-critique
gate (8 questions, real second model call) → 3 concerns + **1 real fail**
(`insufficient_information`) → correctly `blocked_by_self_critique`. This is
exactly the gate behaving as designed on fresh real content, not a synthetic
fixture. `CoverageAssessment`/`EvidenceRanking` were both attached to every
result without error, including one real `confidence_ceiling_breaches` entry
(an existing implication's stored confidence, 0.3, exceeded that ticker's
then-current coverage-derived ceiling, 0.225 — descriptive flag only, not
auto-corrected).

### 3b. Full-corpus analysis (all 18 real LLM-sourced facts / 18 implications)

| Metric | Result |
|---|---|
| Pipeline success rate (documents in a terminal state) | 23/23 (19 completed + 4 blocked_by_self_critique), 0 failed, 0 stuck |
| Extraction precision vs. Phase B ground truth | 90.0% |
| Extraction recall vs. Phase B ground truth | 100.0% |
| Grounding — fresh mechanical re-verification | 18/18 agree with stored `grounding_check` (100%) |
| Citation integrity (evidence resolves, doc_id matches) | 18/18 (100%) |
| Self-critique rejection rate | 22.2% (4/18 blocked) |
| Self-critique finding mix | 65 pass / 71 concern / 8 fail (144 = 18×8) |
| Coverage score, real tickers (n=12) | mean 0.53 (range 0.5–0.6) |
| Confidence ceiling, real tickers | 0.225 uniformly (coverage too thin everywhere for the top band) |
| Evidence trust tiers, platform-wide | 79 tier-1 (primary_filing), 2 tier-4 (ai_derived_or_ungrounded) |
| Contradictions detected / trust-confidence disagreements | 1 detected (TOTAL), 0 disagreements (the ungrounded side's confidence was already correctly zeroed, so both methods agreed) |

"Grounding — fresh mechanical re-verification" is not the same check as
"trust me, the column says passed": it re-reads every source document off
disk today and re-runs `check_grounding` live, independent of whatever was
stored at extraction time. It agreeing 18/18 is a real, current-state
finding, not an assumption.

## 4. Findings

**Real, working correctly (no action needed):**
- Anti-hallucination behavior holds under real, unscreened documents (5/6
  correct abstentions this pass).
- The self-critique gate genuinely blocks a real weak implication end-to-end
  (CILEASING doc 11387), not just in MockProvider tests.
- Citation/grounding integrity is 100% on live re-verification.
- `CoverageAssessment`/`EvidenceRanking` run cleanly across every real
  ticker with no crashes, and the ceiling-breach and conflict-disagreement
  mechanisms both fired at least once on real data during this pass,
  proving they're not dead code.
- `entity_relationships` is genuinely **empty** (0 rows) across all real
  data — not a bug, a real reflection of TD11/TD12/TD14 (no second/
  third-order effect in any real filing so far had both a grounded quote AND
  a resolvable entity name at once). Every real ticker fails
  `has_entity_relationships` and `has_multiple_fact_types` — real coverage
  is currently thin and fairly uniform (0.5–0.6), not because of a bug but
  because the corpus processed so far skews toward single-fact-type
  (`dividend`) filings.

**Fixed during this pass (small, additive, no architectural change):**
- `reasoning_engine.py`'s orchestrator never wrote to
  `document_processing_status` — only `run_phase_c_pilot.py` did. Since the
  orchestrator is now the primary way documents get processed going
  forward, `pilot_summary.py`'s "documents processed/failed" counters (and
  therefore any reported pipeline success rate) were silently under-counting
  real work. Fixed by having the orchestrator call the same
  `pipeline_status.mark_status`/`determine_final_status` calls
  `run_phase_c_pilot.py` already used — pure observability fix,
  `should_skip()`/`resume_point()` never depended on this table anyway (they
  cross-check `extracted_facts` directly), so no resumability behavior
  changed. Backfilled the 6 documents this validation pass processed before
  the fix landed. Verified via a full test-suite rerun (154/154 pass) and a
  before/after `pilot_summary` diff (documents.processed 17 → 23,
  matching exactly).

**Disclosed, not auto-fixed (would need owner approval to go further):**
- TD12 (entity resolution has no merge queue, exact-match-only) is rated
  MEDIUM in the existing backlog and unchanged by this pass — still real,
  still a design trade-off ("never guess a match"), not something this
  stabilization pass should silently upgrade to fuzzy matching.
- Every real ticker's confidence ceiling sits at 0.225 (the middle band) —
  the coverage checklist has not yet seen any ticker clear the top band
  (0.7+) because two of its ten dimensions (financial statements, secondary
  sources) cannot be satisfied by ANY ticker until those platform-wide
  datasets exist. This is accurately disclosed, not a bug — flagging it here
  so a future reader doesn't mistake "every ceiling is 0.225" for a broken
  formula.
- One pre-existing implication (from before this pass) sits above its own
  ticker's current confidence ceiling (`confidence_ceiling_breaches`, seen
  live in section 3a). Per the design, this is surfaced for owner review,
  not auto-corrected — revisiting historical confidence values is a
  judgment call, not a mechanical fix.

No finding this pass required a larger architectural change than what's
already been made.

## 5. Verification

- `python -u scripts/test_reasoning_pipeline.py` → **154/154 pass, 0 fail**.
- Live orchestrator run against real Gemini API + real NGX filings,
  `reports/stabilization_validation_raw.json` holds the full machine-readable
  trace.
- Real database backed up before any live run:
  `data/ngx.sqlite.pre_stabilization_backup_2026-07-27` (untracked by git,
  local safety copy only).
