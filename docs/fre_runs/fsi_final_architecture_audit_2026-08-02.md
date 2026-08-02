# FSI/FRE Final Architecture Audit — 2026-08-02 (Revision 3)

*Produced at the natural stopping point reached under the owner's
standing continuous-execution authorization (Phases 14-27, no
per-phase approval checkpoint). Supersedes Revision 2 (produced after
Phase 25). The owner named two further phases explicitly (26:
Sector-to-Company-Type Mapping; 27: Industry Exposure Integration),
both now complete. This revision reviews the entire platform again —
FRE, FSI, LIM, Quant Engine, Knowledge Graph, Research Engine,
Validation Harness, Portfolio infrastructure, CLI tools, and
documentation — from the new state.*

## 1. What changed since Revision 2

Revision 2 (after Phase 25) reported Part 9 fully closed and flagged
two new, not-yet-scoped candidates: mapping NGX's sectors onto the
Valuation Engine's own company-type taxonomy, and wiring `sector_ngx`
into Company Intelligence's Industry Exposure field. The owner named
both explicitly as Phases 26 and 27:

- **Phase 26**: `configs/sector_company_type_mapping.toml` +
  `sector_company_type_mapping.py` deterministically translate 12 of
  NGX's 13 top-level sectors (plus Banking/Insurance within Financial
  Services) onto `valuation_engine.py`'s existing six company types.
  `classify_company_type()` gained one new precedence tier (owner
  override → sector-derived → `"general"`), with zero visible change
  to any of the 10 real FSI tickers' actual readiness/valuation
  output, verified directly before and after implementation.
- **Phase 27**: `CompanyProfile.industry_exposure` now surfaces
  `sector_ngx` verbatim for the 136/320 tickers where it is known,
  correctly removed from `unavailable` per-profile, with isolation
  between profiles built in the same batch run verified directly.

Both phases activated zero new valuation/analytical output — Phase
26's `compute()` still unconditionally refuses on every adapter;
Phase 27 states a single sector label, nothing computed or inferred.

## 2. Why this is a natural stopping point again

Re-checked, not assumed, before writing this section:
`entity_relationships` still holds exactly 5 rows (4 `renamed_from`,
1 `affects_order_1`) — zero `subsidiary_of` or `macro_exposure` edges
exist, so a `sum_of_the_parts` adapter (named in `valuation_method_
eligibility.toml` but never built) would have no real data to ever
report `READY`, and `correlation_notes.py`'s CLI remains not worth
building. `cfo`/`cfi`/`cff` each still have exactly 1 computed trend
conclusion, `fcf` still 0 — unchanged since Revision 1's original
finding. Every other candidate on Revision 2's list is unchanged:
still owner-blocked (Evaluation Framework, news-source registry, LIM
checkpoint), still guardrail-blocked (valuation activation, Portfolio
Construction Tier 2), or still correctly judged not-currently-
justified (coverage expansion, `ebit_margin` rule extension).

No new "Can-implement-immediately" candidate was found. The two
candidates Revision 2 itself surfaced are now closed; nothing replaced
them.

## 3. Remaining possible phases, categorized (updated)

### Can-implement-immediately
*None identified*, unchanged from Revision 2's own finding.

### Requires-owner-decision
- Evaluation Framework (FRE-10 / Part 11) — analyst-authored gold set.
- News-source reliability-tier registry — vetted outlet list.
- LIM Phase LIM-0 onward — exact checkpoint/version.
- Valuation Engine activation (Part 8) — a future, separate,
  explicit architecture-revision authorization.
- Building the `sum_of_the_parts`/`normalized_earnings_multiple`/
  `asset_based_floor` adapter classes as empty, always-`NOT_READY`
  stubs — technically possible now, but purely cosmetic (no real
  behavior change; the "adapter is None" branch already discloses
  "not yet built" correctly) — an owner call on whether that
  cosmetic completeness is worth a phase, not an architectural gap.

### Requires-external-data-or-vendor
- Coverage expansion beyond the current 10 FSI tickers (39 of 49
  scoped, hand-extraction labor).
- The remaining 184 securities' `sector_ngx` (bonds/ETFs/synthetic
  placeholders out of scope by nature; the rest absent from NGX's
  Daily Official List, most plausibly delisted/suspended, unconfirmed).
- A working macro-conditioning factor — Wave-3 quant research track.

### Requires-new-research
- Any second validated factor — Wave-3/H-0xx track, never to be
  shortcut here.
- A `cfo`/`cfi`/`cff`/`fcf`-based health flag — re-checked again this
  revision: still 0-1 computed trend conclusions per metric.

### Not-currently-justified
- A CLI wrapper for `correlation_notes.py` — `entity_relationships`
  still 100% empty of macro_exposure edges, re-confirmed this
  revision.
- Extending `financial_health_flags.py`'s rules to check
  `ebit_margin` — would modify a frozen module, reads as
  coverage-expansion-in-disguise.
- A second round of coverage expansion for its own sake.

## 4. Remaining technical debt (unchanged from Revision 2, plus one addition)

- `valuation_engine.py`'s coarse `is_ready()` per-adapter check.
- 39 of 49 originally-scoped tickers remain unextracted.
- The pre-existing `FIRSTHOLDCO`/`FirstHoldCo` duplicate-case ticker
  row in `securities`.
- No single test threads a CLI-added watchlist entry through the
  CLI-rendered annotated dossier end-to-end.
- New, minor: `sector_company_type_mapping.toml`'s deliberately
  unresolved Financial-Services sub-industries (Micro-Finance Banks,
  Mortgage Carriers, "Other Financial Institutions") could in
  principle be revisited if `valuation_method_eligibility.toml` ever
  grows a dedicated company_type for one of them — not urgent, no
  real ticker in these buckets has financial-statement facts today.

## 5. Long-term roadmap recommendations (updated)

- **Do not build Part 8 or Part 9 Tier 2 reactively.** Unchanged.
- **The sector_ngx consumption loop is now closed** — both
  Valuation Engine and Company Intelligence consume it; no third
  consumer has been identified as a real gap (Sector-coverage view,
  Part 9, already consumes it independently via Phase 24).
- **If `valuation_method_eligibility.toml` ever grows a `reit`
  company_type** (for `CONSTRUCTION/REAL ESTATE`'s REIT sub-industry,
  currently mapped to the conservative `"general"` default), revisit
  `sector_company_type_mapping.toml` alongside it — they were
  designed together and share the same precondition.
- **The next continuous-execution run, if one is authorized**, should
  re-check `entity_relationships`' `subsidiary_of`/`macro_exposure`
  edge counts and `cfo`/`cfi`/`cff`/`fcf` filing-period growth before
  assuming the same stopping point still holds.

## 6. Summary

Phases 26-27 closed the two sector_ngx-consumption gaps Revision 2
itself surfaced, both explicitly named by the owner, both verified to
activate zero new valuation/analytical output despite real, disclosed
behavior changes for non-FSI tickers. A fresh full-platform review —
re-checking, not assuming, `entity_relationships` and `cfo`/`cfi`/
`cff`/`fcf` coverage — found no further buildable-now, guardrail-
compliant, genuinely-new capability. That is the basis for stopping
here, again, with the same honesty as Revisions 1 and 2: a snapshot
of 2026-08-02's real state, not a permanent verdict.
