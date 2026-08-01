# Financial Statement Intelligence — Phase 2 Pre-registration

*Design only. No implementation, no extraction, no schema change, no
dependency installation, no valuation activation. Per instruction, this
document is written and frozen BEFORE any execution begins — the same
two-gate discipline used for Phase 1
(`docs/fre_runs/fsi_phase1_preregistration.md`), FRE-5, and every LIM
training experiment. Builds on `fsi-phase1-baseline-2026-08-01` and its
five recorded limitations (small hand-selected pilot, no external
validation, no OCR validation, limited financial taxonomy, not
production-scale) — every one of those limitations is a live constraint
on what Phase 2 is allowed to assume, not a closed matter.*

## Objective

Expand verified financial intelligence beyond Revenue and Net Profit —
balance sheet, cash flow, EBITDA/EBIT, and derived ratios — while treating
period normalization, restatement handling, and accounting-terminology
mapping as first-class design problems (not incidental details), because
Phase 1 already surfaced real instances of all three. Phase 2 is
explicitly a **design and methodology expansion**, evaluated the same
disciplined way Phase 1 was: pre-registered thresholds, honest reporting
of partial or negative results, no forced conclusions.

## What Phase 1 actually taught, restated precisely (the evidence base for every design choice below)

Every design decision in this document traces to a specific, real
observation from Phase 1's 15 filings, not a generic assumption:

- **EBITDA is often directly stated**, not always requiring derivation —
  BUAFOODS's filings had explicit `EBITDA`/`EBITDA Margin` rows; NASCON's
  filings had the same. This is a genuinely favorable finding for Phase 2's
  EBITDA scope, not an assumption.
- **Ratios are frequently directly disclosed**, not only derivable — CAP,
  NASCON, and BUAFOODS filings all contained explicit `Gross Margin`,
  `PBT Margin`, `PAT Margin`, and (for BUAFOODS/NASCON) `EBITDA Margin`
  rows in their own compact highlights tables.
- **Accounting terminology varies by company AND by sector**, confirmed
  concretely: AFRIPRUD (a share registrar) has no line item literally
  called "Revenue," only "Gross Earnings" — and even that label was
  inconsistent across AFRIPRUD's own filings over time ("Gross earnings"
  vs. "Gross Revenue").
- **Periods are labeled loosely relative to what they actually represent**
  — UCAP's "Q3 2020" headline referred to a 9-month cumulative period, not
  a standalone third quarter. This is a real, confirmed ambiguity in how
  NGX earnings releases use period labels, not a hypothetical risk.
- **Restatements are real and can silently diverge** — CAP's FY2021 filing
  showed a different FY2020 comparative revenue figure than FY2020's own
  originally-filed figure (likely from its 2021 merger with Portland
  Paints), confirmed by direct comparison across two real filings.
- **PDF-to-text layout artifacts are real and non-trivial** — BUAFOODS's
  FY2024 filing's detailed statement table extracted with its row labels
  and numeric columns scrambled, resolved only by cross-matching against
  a cleanly-formatted parallel table in the same document.
- **`documents.doc_type` is not a reliable content filter** — confirmed in
  Phase 1's own scoping step; Phase 2 inherits this and must not assume
  otherwise.

## Scope — the nine required design areas

### 1. Balance sheet extraction

**Target**: `assets` (Total Assets), `liabilities` (Total Liabilities),
`equity` (Total Shareholders'/Total Equity) — the three top-level
ontology nodes from `configs/financial_ontology.toml`'s `balance_sheet`
family, deliberately not the more granular sub-line items (cash,
receivables, PP&E, etc.) this pass. Rationale: Phase 1's own revenue/
net_profit precedent shows top-level "Total X" figures are usually a
single, unambiguous stated line — the same expected shape applies here,
and granular sub-items (already seen to have real complexity, e.g.
AFRIPRUD's "Debt Instruments at Amortised Cost" vs. simpler "Cash and
cash equivalents") are deferred to a future phase, not attempted
prematurely.

**Design note — a mechanical validation Phase 1 could not do, now
possible**: `configs/financial_ontology.toml` already encodes
`liabilities component_of assets` and `equity component_of assets`
(FRE-1's definitional skeleton) — meaning `assets ≈ liabilities + equity`
is a real accounting identity, not a judgment call. Phase 2 can (design
only, not built here) mechanically check this identity for every extracted
balance-sheet triple, exactly analogous to how a self-critique gate checks
a claim mechanically rather than trusting a stated verdict alone. This is
new methodology Phase 1's 2-metric scope never enabled.

### 2. Cash flow extraction

**Target**: `cfo` (Net Cash from Operating Activities), `capex` (Net Cash
used in Investing Activities — a disclosed approximation, since "capex"
strictly means capital expenditure, a sub-component of investing
activities, not the full investing-activities total; Phase 2 must extract
the specific "purchase of property, plant and equipment" line if
separately stated, falling back to the investing-activities total only
when it is not, and must record which case applied per fact). `fcf`
(Free Cash Flow) is **derived, not independently extracted** — per
`configs/financial_ontology.toml`'s existing `cfo component_of fcf` /
`capex component_of fcf` definitional edges (`fcf = cfo − capex`) — the
ontology already specifies this, Phase 2 only needs to apply it.

**Genuinely untested territory, stated honestly**: unlike EBITDA/ratios,
Phase 1's 15 filings did not examine cash-flow statements at all (they
were not in scope). Cash flow extraction has **no prior signal on this
platform** — proposed with the same "genuinely open" honesty this
program has used for every untested LIM hyperparameter (learning rate,
batch size). No success rate is assumed; Phase 2 measures it.

### 3. EBITDA/EBIT extraction

**Target**: `ebitda`, `ebit`. Per Phase 1's own finding, extraction should
be **hybrid**: (a) use the directly-stated figure where a filing explicitly
labels an `EBITDA`/`EBIT`/`Operating Profit` row (common, per Phase 1's
BUAFOODS/NASCON/CAP observations), recording which literal label was used;
(b) derive `ebitda = ebit + d_and_a` only when no direct figure exists,
per the existing ontology edge, and flag every derived (vs. directly
stated) value distinctly — never presenting a derived figure with the
same confidence as a directly-read one.

**A named, disclosed ambiguity**: several Phase 1 filings used "Operating
Profit" as apparently synonymous with EBIT, but accounting convention does
not guarantee this equivalence in every case (Operating Profit can exclude
items EBIT conventionally includes, or vice versa, depending on a
company's own income-statement structure). Phase 2 must NOT silently
treat "Operating Profit" and "EBIT" as interchangeable labels without a
per-filing check — this is exactly the kind of terminology-mapping risk
named in area 7 below, surfaced here because EBIT is where it is most
likely to bite first.

### 4. Financial ratio derivation

**Target**: `gross_margin`, `ebitda_margin`, `pbt_margin`, `pat_margin`
(all as a % of revenue, matching the convention every Phase 1 filing that
disclosed a margin used). **Dual-source design, extending Phase 1's own
cross-validation methodology to a third axis**: where a filing directly
states a margin (common, per Phase 1's finding), extract it directly AND
independently derive the same ratio from the extracted absolute figures
(e.g., `gross_profit / revenue`); disagreement between stated and derived
values beyond a disclosed tolerance (proposed: 1 percentage point,
accounting for normal rounding — a reasoned, not empirically validated,
choice, stated as such) is itself a new, valuable finding, not an error to
silently average away. This mirrors Phase 1's "highlights vs. detailed
table" internal cross-check, applied one level higher.

### 5. Period normalization

**The real UCAP "Q3 2020 label, actually a 9-month cumulative figure"
finding demands a formal fix, not another ad hoc reading per filing.**
Proposed: a `period_type` classification, config-driven (matching this
platform's taxonomy-as-config convention), with values `Q1`/`Q2`/`Q3`/`Q4`
(standalone quarter), `H1`/`H2` (half-year cumulative), `9M` (nine-month
cumulative), `FY` (full year) — assigned by **checking the actual
`period_start`-to-`period_end` span**, never by trusting a filing's own
headline label (e.g., "Q3 2020" in UCAP's own headline was confirmed
wrong as a *standalone*-quarter description; the span itself, Jan 1–Sep
30, is the reliable signal). This is a genuine methodological correction
Phase 2 must apply retroactively when reviewing Phase 1's own 15 facts
too (a re-labeling exercise, not a re-extraction — Phase 1's stored
`period_start`/`period_end` values are already correct; only a
`period_type` derived tag would be new, and adding it is a **schema
question flagged for approval, not decided here** — see Dependencies.

### 6. Restatement handling

**CAP's real, confirmed FY2020-comparative-vs-original discrepancy is the
concrete case this design responds to.** Proposed mechanism, modeled
directly on the existing, already-proven `investment_implications
.corroborates_implication_id`/`.contradicts_implication_id` pattern (Part
6/`docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md` §8's append-only
conflict-preservation convention): when a newly-extracted fact's period
overlaps a previously-extracted fact's period for the same ticker/metric
with a different value, record a `restates_fact_id`-style link (a new,
disclosed schema need, **not built here**) rather than silently preferring
either figure. Both rows stand, exactly like every other append-only
table on this platform — a restatement is evidence of something real
(often a merger, a reclassification, or an audit adjustment), never
treated as a simple extraction error to be corrected away.

### 7. Accounting terminology mapping

**A config-driven synonym table** (`configs/financial_statement_terminology.toml`,
proposed name, **not created in this pass**), mapping observed real
label variants to canonical ontology fact_type names, seeded from Phase
1's own confirmed observations:

```
# proposed structure, illustrative only -- not created this pass
[revenue]
synonyms = ["Revenue", "Turnover", "Gross Earnings", "Gross Revenue"]
sector_note = "Gross Earnings/Gross Revenue used by financial-services/registrar firms (e.g. AFRIPRUD) lacking a literal 'Revenue' line"

[net_profit]
synonyms = ["Profit for the period", "Profit for the year", "Profit After Tax", "PAT"]

[ebit]
synonyms = ["EBIT", "Operating Profit"]
caveat = "NOT guaranteed equivalent across all filers -- verify per filing, per area 3 above"
```

This is the direct, disclosed answer to "how does Phase 2 avoid
re-deriving AFRIPRUD's Gross-Earnings judgment call from scratch for
every new company" — a durable, config-driven artifact (matching every
other taxonomy on this platform), seeded but not finalized in this
pre-registration.

### 8. Validation methodology

Extends Phase 1's two-way internal cross-check (highlights narrative vs.
detailed statement table) with three new, concrete mechanisms enabled
directly by Phase 2's expanded scope:

1. **Accounting-identity checks** (area 1): `assets ≈ liabilities + equity`,
   `ebitda ≈ ebit + d_and_a` — mechanical, using existing
   `financial_ontology.toml` definitional edges, a disclosed tolerance
   (proposed 0.5%, accounting for rounding), genuinely new methodology
   Phase 1's 2-metric scope could not exercise.
2. **Stated-vs-derived ratio checks** (area 4) — disagreement is a
   finding, not smoothed over.
3. **Restatement flags** (area 6) — every same-ticker/metric/overlapping
   -period value conflict is surfaced, never silently resolved.

**No external/vendor validation is proposed for Phase 2 either** —
consistent with Phase 1's own recorded limitation ("no external
validation") and the standing "no vendor data" constraint; Phase 2 extends
INTERNAL cross-validation depth, it does not add an external source.

### 9. Scaling strategy

**Phase 2 is explicitly NOT a production-scale rollout** — restating
Phase 1's own recorded limitation as a live constraint, not something
Phase 2 is expected to resolve. Two deliberate, disclosed design choices:

- **Sample size**: propose 40–60 filings across 12–15 companies (roughly
  3–4× Phase 1's scale) — large enough to test the new metrics/mechanisms
  across genuine variety (multiple sectors, multiple report-format eras),
  still far short of the 349-candidate/49-ticker full scoped set Phase 1's
  own scoping step already found, and nowhere near the full native-text
  archive.
- **Extraction method**: propose a deterministic-parser-first approach for
  the common "Key Financial Highlights"-style compact table format
  observed in every one of Phase 1's 15 real filings (a recognizable,
  regular `[Metric] [Period] [Prior Period] [Change%]` row structure),
  with manual/analyst reading as the fallback for filings that don't match
  — inverting Phase 1's method (manual-first) now that a common template
  has been confirmed to exist across multiple real companies. **Not built
  in this pass** — a design recommendation for Phase 2's own execution
  pre-registration/implementation, once approved.
- Genuine production scaling (the full archive, OCR-pending documents,
  automation/scheduling) remains explicitly out of scope for Phase 2,
  deferred to a later, separately-gated phase — consistent with this
  entire program's discipline of never bundling an untested capability
  expansion with a scale expansion in the same step.

## Pre-registered success / partial / failure criteria (per new metric family)

Set now, before any extraction, per standing discipline — thresholds are
disclosed judgment calls, not derived from prior data (Phase 2 is
genuinely new territory for 6 of its 8 new metrics):

| Metric family | Success | Partial | Failure |
|---|---|---|---|
| Balance sheet (assets/liabilities/equity) | ≥80% correct + accounting identity holds (±0.5%) for ≥90% of triples | 40–79% correct | <40% correct |
| Cash flow (cfo/capex/fcf) | ≥70% correct (lower bar — genuinely untested, no prior signal, disclosed as such) | 30–69% correct | <30% correct |
| EBITDA/EBIT | ≥80% correct (direct-stated or correctly-derived) | 40–79% correct | <40% correct |
| Ratios | ≥80% of stated-vs-derived pairs agree within 1 percentage point | 40–79% agree | <40% agree |

A metric family scoring below its own success bar does **not** block the
others — each is evaluated and reported independently, exactly as Phase
1's own single-variable discipline requires.

## What Phase 2 explicitly does NOT do (per instruction, restated)

- No implementation of any kind in this pass — this document is design
  only.
- No schema change — `period_type` and `restates_fact_id` are named as
  **real, identified needs requiring their own explicit approval**, not
  assumed or built here (unlike Phase 1, where the schema step was
  bundled into the same approved pre-registration — this pass is
  design-only by explicit instruction, so even a FRE-1-pattern additive
  column is deferred to a future, separately-approved execution step).
- No valuation activation — nothing in this design feeds
  `valuation_engine.py`; that module's adapters remain formula
  -unimplemented regardless of any Phase 2 outcome.
- No OCR work, no vendor data — inherited unchanged from Phase 1.
- No production-scale rollout — per area 9 above.

## Dependencies

Phase 1's real data and code (`extracted_facts.period_start/period_end`,
`configs/fact_taxonomy.toml`'s `[financial_statements]` group, the 30 real
Phase 1 facts as a cross-reference base). `configs/financial_ontology.toml`'s
existing definitional edges (for the new accounting-identity checks —
read-only reuse, no change proposed). Two new, unbuilt schema needs
flagged for future approval: `extracted_facts.period_type` (area 5) and a
restatement-link mechanism (area 6). A new, unbuilt config file
(`configs/financial_statement_terminology.toml`, area 7).

## Risks

- **Metric-family scope creep**: 8 new fact types (vs. Phase 1's 2) is a
  larger single expansion — mitigated by the per-family independent
  success criteria above (a weak cash-flow result does not retroactively
  cast doubt on a strong balance-sheet result, and vice versa).
- **The EBIT/Operating-Profit equivalence risk** (area 3) is the single
  most likely source of a real, silent metric-mapping error if not
  checked per filing — flagged as the top methodological risk for
  Phase 2's actual execution to design defenses against explicitly.
  Restatement detection (area 6) and terminology mapping (area 7) both
  require the NEW schema/config artifacts named above — Phase 2's design
  is complete without them, but its EXECUTION cannot begin until they are
  separately approved and built, creating a real sequencing dependency
  this document does not resolve.
- **Small-sample risk carries forward**: even Phase 2's proposed 40-60
  -filing scale remains far short of anything that could support a
  statistically powered claim — restated explicitly so a strong Phase 2
  result is not over-generalized any more than Phase 1's was.

## Stop condition

Per Phase 1's own precedent: if the document-scoping step (extended to
the new metric families) cannot identify a usable candidate set meeting
the proposed 40-60 filing floor, or if any individual metric family's
extraction rate falls below its own failure threshold, report that
honestly as the finding — do not lower a bar or substitute unapproved
data sources to manufacture a passing result.

## Review checkpoint

Per the same two-gate discipline as Phase 1: this pre-registration must
be reviewed and approved — including, explicitly, a decision on the two
named schema needs (`period_type`, restatement-linking) and the new
terminology-mapping config — before any Phase 2 execution begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
