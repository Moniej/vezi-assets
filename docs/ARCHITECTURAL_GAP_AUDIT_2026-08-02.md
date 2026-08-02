# Full Architectural Gap Audit — 2026-08-02

*Performed at v1.0 (`platform-baseline-2026-08-02-stable`), per the
owner's explicit instruction to audit before proposing any next phase.
Covers all four layers: Quant Engine, AI Intelligence Layer, Financial
Reasoning Engine (FRE) / Financial Statement Intelligence (FSI), and
the Portfolio Research Toolkit. Every claim below was checked directly
against the real codebase/database/registry before being stated — not
restated from the v1.0 summary without verification.*

## A factual correction, found while verifying the stated project numbers

The v1.0 summary states "8 quant hypotheses tested: 1 confirmed, 7
rejected." Checked directly against `docs/FACTOR_REGISTRY.md`: the
real count is **10 hypotheses with a completed verdict** — 1 confirmed
(H-011, Size) and **9 rejected**: H-001 (sector momentum), H-003
(event catalyst rotation), H-004 (macro oil lead-lag), H-005 (macro
MPC windows), H-006 (PEAD), H-007 (cross-sectional momentum), H-008
(low volatility), H-009 (turnover-budgeted momentum), H-010 (pooled
overlapping-cohort momentum). A further ID, **H-002** (total-return
momentum / dividend effects), was pre-registered but has never been
run — it remains `blocked-on-data` per `docs/HYPOTHESIS_FAMILY_MAP.md`
(the DOL dividend/EPS extraction attempt failed validation twice; see
`reports/eps_pe_extraction_status.md`). This correction doesn't change
any conclusion below, but it is stated because "verify before
restating" is this platform's own standing discipline, applied here to
its own summary of itself.

---

## Q1 — What capabilities are missing?

### Quant Engine
- **A second validated factor.** Portfolio Construction's own ≥2-factor
  gate remains one short. This is the single most consequential gap on
  the entire platform — every downstream Tier-2 portfolio capability
  (ranking, sizing, risk, rotation) is designed and waiting on it.
- **A regime-conditional research methodology.** No hypothesis has ever
  tested a signal *conditioned* on a pre-declared macro-stability
  regime, despite two independent findings (H-004's sign reversal after
  the 2023 float; H-008's robust rejection across three violent regime
  transitions) pointing directly at this as untested infrastructure,
  not just an untested factor.
- **Float-adjusted market capitalization** (shares-outstanding/free-
  float dataset) — H-011's own stated construct-validity limitation.
- **A validated corporate-actions classification pipeline** — the
  archive is 97% complete but was never itself promoted to evidence
  grade as a research input (only as a data-quality/gate tool).

### AI Intelligence Layer / FRE / FSI
Re-verified against `docs/fre_runs/fsi_final_architecture_audit_
2026-08-02.md` (Revision 3, produced after Phase 27) and the real
database state directly (not assumed unchanged):
- `entity_relationships` still holds exactly 5 rows (4 `renamed_from`,
  1 `affects_order_1`) — zero `subsidiary_of` or `macro_exposure`
  edges. Confirmed again just now: unchanged since Revision 3.
- `cfo`/`cfi`/`cff` trend conclusions: still 1/1/1; `fcf`: still 0.
  Confirmed again just now: unchanged.
- Every item on Revision 3's own backlog (Evaluation Framework gold
  set, news-source registry, LIM checkpoint, valuation activation, a
  second quant factor) remains exactly where it was — no new external
  input has arrived.

**No new FRE/FSI capability gap was found.** The exhaustive review that
produced three successive audit revisions already covers this layer
completely; re-deriving it from scratch here would not change the
conclusion, and the platform's own standing rule against "creating
phases just to increase count" applies with equal force to re-running
an audit that would return an identical answer.

### Portfolio Research Toolkit (Part 9)
Complete — all five Tier-1 capabilities built, tested, and
operator-reachable (confirmed: 38 test files, 31 tables, all passing,
re-checked this session). Tier 2 remains correctly gated (see Quant
Engine, above — this is the SAME gap, not a separate one).

---

## Q2 — Categorized: immediately buildable / externally blocked / not yet justified

| Capability | Category | Why |
|---|---|---|
| **Regime-Conditional Factor Gate** (retest H-008 within a pre-declared stable regime) | **Immediately buildable** | Reuses `vol_scores()` (H-008's own signal, unmodified) + existing `events`/`macro_series` tables (already populated, already used by H-004/H-005). No new dataset. A regime-classification rule can be pre-declared today, verified feasible (§ below), before any result is seen. |
| A second, genuinely new factor family (e.g. Corporate-Action Event Drift, C3) | Not yet justified | The classification pipeline behind it was never promoted to evidence grade — this candidate implicitly asks for that validation work first, and the Wave-3 review itself scored it lowest (28/50) for exactly this reason. |
| Float-adjusted market cap | Externally blocked | No shares-outstanding/free-float dataset exists; a new harvest, not an engineering task. |
| Evaluation Framework (FRE-10), news-source registry, LIM checkpoint | Externally blocked (owner decision) | Unchanged since Revision 3 — see `docs/fre_runs/OWNER_DECISION_BACKLOG_2026-08-02.md`. |
| Valuation Engine activation, Portfolio Construction Tier 2 | Guardrail-gated | Requires ≥2 validated factors (Portfolio Construction) or a future, separate, explicit architecture-revision authorization (Valuation) — neither is a code gap. |

---

## Q3 — Which missing capability creates the highest increase in research quality?

**The Regime-Conditional Factor Gate.** Reasoning, weighed against the
alternatives:

- It is not a single-use factor bet — it is **reusable research
  infrastructure**. Once built and validated once, every future
  hypothesis on this platform gains the option of a regime-conditional
  variant, the same way `xs_rank`/`xs_vol`'s shared scaffolding lets
  every cross-sectional hypothesis reuse one simulation/placebo/
  capacity engine today. `docs/WAVE_3_RESEARCH_DIRECTIONS.md` (2026-
  07-22) independently reached this same conclusion and scored it the
  program's highest long-term-architecture bet (tied 37/50, but the
  ONLY candidate whose value doesn't depend on its own verdict).
- It directly closes the gap between *reporting* regime concentration
  as a post-hoc caveat (every prior IC memo's own regime-attribution
  section) and *testing* it as a designed precondition — the platform
  has observed this pattern twice (H-004, H-008) without ever
  formalizing it as a method.
- It is genuinely buildable today with zero new data acquisition,
  unlike every other quant-side gap.
- The alternative "highest-value" candidates from the same review
  (C1/Pooled Momentum, C4/Size) have both **already been executed**
  since that review was written — C1 as H-010 (rejected), C4 as H-011
  (confirmed). C2 is the one top-tier candidate from the platform's own
  prior prioritization that was explicitly deferred, not rejected or
  completed: *"C2 is the stronger long-term bet and should be the next
  wave after C1/C4... once a regime-definition methodology can be
  pre-registered with full rigor rather than rushed alongside two
  other candidates"* — that condition is met now.

---

## Q4 — What hypothesis should be tested next?

**H-012 — Regime-Conditional Low-Volatility Gate**, re-testing H-008's
rejected low-vol signal restricted to a pre-declared macro-stable
regime. This is not a fresh idea invented for this audit — it is
Wave 3's own candidate C2, already scoped, already scored, explicitly
queued as "the next wave after C1/C4." Both of those have since run
(H-010 rejected, H-011 confirmed), so C2 is next in the platform's own
prior research queue, not a new invention.

A regime-classification rule was drafted and scoped for feasibility
**before seeing any performance data** (the discipline the Wave-3 doc
itself demands, to avoid the regime definition becoming p-hacking
dressed as methodology):

> A formation date is **STABLE** unless a `critical`-severity
> macro/FX/banking event occurred in the trailing 6 months, OR more
> than one `high`-severity monetary-policy (MPC) event occurred in the
> trailing 6 months.

Checked directly against the real `events` table (dates and event
counts only — zero return/performance data touched): of 42 quarterly
formation dates spanning H-008's own development + OOS window
(2016 Q1 – 2026 Q2), **27 classify as stable, 15 as unstable** — a
real, workable sample, smaller than the unconditional test by
construction (exactly the power tradeoff the Wave-3 review flagged in
advance, not discovered after the fact). Full pre-registration:
`docs/PREREG_H-012.md`.

**This audit does not implement or run H-012.** Per this platform's own
unbroken convention (every prior hypothesis, H-001 through H-011, was
pre-registered and reviewed before any run — none was drafted and
executed in the same step), `docs/PREREG_H-012.md` is presented for
review. Running it is Step 2 of the owner's own required workflow,
conditioned on the prereg itself passing scrutiny — not something this
audit assumes permission for.
