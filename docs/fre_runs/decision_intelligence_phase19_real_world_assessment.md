# Phase 19: Real-World Investment Intelligence Assessment

**Date**: 2026-08-09
**Type**: Assessment/validation only. No new module was built for the assessment
itself (one diagnostic runner script, `scripts/fre/phase19_assessment_pipeline.py`,
same read-only convention as `fre7b_accounting_depth_audit.py`). No hypothesis
registered, no backtest run, no ranking produced, no BUY/SELL/AVOID label anywhere
in any output. Zero database writes (verified: `documents` row count unchanged
before/after every run in this phase).

**Bottom line, stated up front (per the task's own framing question)**: if this
Investment OS were handed to an investment professional today, it could reliably
perform maybe **30-40% of a real company-understanding workflow** — deep, honest,
well-cited financial-change detection and regulatory-context assembly for a
minority of tickers with real FSI coverage, and almost nothing on qualitative
company understanding (business model narrative, customers, suppliers, management,
ownership) for any ticker, ever. It is an **Analyst Research Assistant** (§19E),
not yet institutional infrastructure, and the single highest-leverage next
capability is not a new module — it's closing the FY-data freshness/breadth gap
that FRE-7B/7B.1/7B.2 already diagnosed (§19C, Gap B-1).

---

## 1. Methodology

**Ticker selection rule (pre-declared before any pipeline was run, frozen in
`phase19_assessment_pipeline.py`'s own docstring)**: the alphabetically-first
ticker within each real `economic_peer_taxonomy.level1` group, among
`genuine_fact_universe.list_genuine_financial_statement_tickers()`. This is
deterministic and reproducible — re-running `select_tickers()` against the same
database returns the same 8 tickers — and was not adjusted after seeing any
result.

**Pipeline run per ticker**: `company_economic_profile.build_economic_profile()`
→ `company_intelligence_bundle.build_intelligence_bundle()` (which itself composes
`company_state`, `change_detection`, `materiality`, `confidence_engine`,
`company_thesis`) → `research_questions.answer_all()` →
`company_research_report.build_full_report()`/`render_full_report()` →
`continuous_intelligence.process_new_information()`. This is the complete existing
pipeline the task named, run unmodified — no new composition logic was added for
this assessment beyond the diagnostic runner itself.

**Dates**: `as_of_date=2026-08-09`, `prior_date=2024-01-01` for every ticker
(fixed, not tuned per ticker).

**19A's coverage measurement** was run separately across the FULL 26-ticker
universe (`financial_ratios.list_tickers()`, including the 2 tickers
`genuine_fact_universe.py` already flagged as false positives — NEM and
TRANSCORP are excluded from the 8-ticker pipeline walkthrough but intentionally
INCLUDED in the 19A coverage denominator, since a real coverage audit should not
quietly drop the very tickers a prior stage found to be over-counted; see §7.1).

## 2. Companies selected and why

| Ticker | economic_peer_taxonomy level1 | Selection reason |
|---|---|---|
| BUAFOODS | Consumer | Alphabetically first Consumer-classified, fact-bearing ticker |
| OANDO | Energy | Only Energy-classified fact-bearing ticker (structural, per FRE-7B) |
| AFRIPRUD | Financials | Alphabetically first of 7 Financials-classified tickers |
| AIRTELAFRI | ICT/Telecom | Alphabetically first of 3 ICT/Telecom tickers; also the platform's one confirmed foreign-currency (USD) reporter |
| CAP | Industrials | Alphabetically first of 6 Industrials tickers |
| UACN | Other (conglomerate) | Alphabetically first of the "Other" bucket |
| MCNICHOLS | Unclassified | Alphabetically first of the 2 tickers with no `sector_ngx` on record at all |
| GEREGU | Utilities | Only Utilities-classified fact-bearing ticker |

This set deliberately spans: a rich-vs-thin data gradient (BUAFOODS/CAP/AFRIPRUD
72% `company_state.data_completeness` vs. MCNICHOLS 32%), a genuine foreign-currency
reporter (AIRTELAFRI), a structurally single-constituent sector (OANDO, GEREGU), a
conglomerate ineligible for P/E-style methods (UACN), and a wholly unclassified
ticker (MCNICHOLS) — matching the task's own instruction not to hand-pick for
interesting results.

## 3. Full results — the 20 questions, answered honestly per company

Answering all 160 cells (8 companies × 20 questions) verbatim would just
reproduce the raw pipeline transcript; the patterns below are what actually
matters, with real per-company specifics named where they diverge.

**Q1-2 (what the company does / what the platform KNOWS)**: For every one of
the 8 companies, **the platform cannot state what the company actually does** —
`business_description`, `products_services` are `UNKNOWN` for all 8 (and, per
§4, all 26 real tickers). What IS known, when known at all: sector/sub-industry
classification (6 of 8: all but MCNICHOLS/UACN — UACN's own is a conglomerate,
correctly bucketed "Other," not a data gap), the most recent knowable
balance-sheet/income-statement figures (6 of 8 have at least partial financial
coverage), and market price/liquidity (8 of 8).

**Q3 (UNKNOWN)**: Identical across all 8 — business description, products/
services, revenue segments, geography, customer concentration, supplier
dependencies, management/ownership, material subsidiaries, strategic priorities.
This is the platform's dominant, structural gap (§4), not a per-ticker anomaly.

**Q4-6 (materially changed / strongest positive / strongest negative)**: Every
company except GEREGU and MCNICHOLS (which have only a single detectable
change each, both a large price move) produced multiple real, cited changes.
Concrete examples, each independently spot-checked against the raw database
record (§6.1):
- BUAFOODS: equity +168.5% (₦206.5bn→₦554.3bn, `fact_id=414`, confirmed exact
  match against `extracted_facts`), assets +81.3%, both CRITICAL.
- OANDO: revenue +470.6% (₦722.4bn→₦4,122.1bn, `fact_id=289`) alongside a
  newly-fired `margin_compression` accounting-anomaly flag — a real case of
  simultaneously positive (top-line) and negative (margin-quality) signals
  neither collapsed into one verdict.
- AFRIPRUD: the single largest signal is NOT a company-specific fact at all —
  it's a CRITICAL, sector-level CBN bank-recapitalisation directive (real
  `events` row, `event_id=64`, `severity='critical'`, confirmed), correctly
  disclosed as "0 ticker-specific + 5 sector-level" rather than misattributed
  as AFRIPRUD's own news.

**Q7 (contradictory evidence)**: `contradiction_note` was empty for all 8 of
these specific pilot tickers (a real, negative finding — the one active
contradiction found anywhere in this session's broader testing was on TOTAL,
outside this pilot set, confirming contradiction-preservation isn't a dead
code path, just genuinely rare in this small sample).

**Q8-9 (financial info available / missing)**: Available for 6/8 (all but
UACN and MCNICHOLS, both genuinely lacking usable balance-sheet facts).
Missing: EPS/shares-outstanding as first-class stored facts (derived on the
fly from `market_cap_panel.csv`, never stored), and, per §4, all narrative
context.

**Q10-11 (regulatory / corporate actions)**: Real regulatory content appeared
for exactly 1 of 8 (AFRIPRUD, via sector-level banking events) — everyone
else's regulatory/corporate-events sections are honestly `UNKNOWN`, not
because nothing happened but because the `events` table's real ticker-level
coverage is thin (26 ticker-scoped rows platform-wide, per the Phase 0 audit).

**Q12 (insider activity)**: Real content for exactly 1 of 8 (AIRTELAFRI — 5
genuine, distinct, correctly-classified `PURCHASE` transactions, verified
against real `documents WHERE doc_type='dealing'` rows with 5 different real
`doc_id`s and dates spanning 2024-03-26 to 2024-04-03). See §6.2 for a real
presentation-quality issue found here.

**Q13 (market behavior)**: KNOWN for 8/8 — the single most reliably populated
category across this entire pilot.

**Q14-15 (catalysts / risks)**: Populated (non-`UNKNOWN`) for 3/8 (BUAFOODS,
and the 2 tickers whose real `investment_implications` rows carried a
`bull_case`/`bear_case`); `UNKNOWN` for the other 5, correctly, not guessed.

**Q16 (invalidation)**: Every company received at least one real, specific
invalidation condition (never a generic placeholder) — e.g. CAP's names the
exact fields (`equity`, `assets`) whose next real filing would confirm or
reverse the recorded move.

**Q17 (fact vs. inference)**: Structurally enforced, not a formatting
convention — `research_questions.py`'s own test suite verifies this by
asserting the `is_inference` flag is `False` for bare restatements ("what
changed materially") and `True` for judgment calls ("strongest positive
developments," a top-N selection). Every one of the 8 pilot runs produced
answers with this flag correctly set.

**Q18 (evidence strength)**: Directly readable from `confidence_engine`'s 6
named dimensions — every one of the 8 companies scored overall `LOW`
(§7.3), with the specific weakest dimension(s) always named (never a bare
"LOW" with no reason).

**Q19 (what a professional analyst would still need to investigate manually)**:
See §5 (Analyst Gap Analysis) — the honest answer is "almost everything about
who the company actually is, what it sells, to whom, and who runs it,"
which no dossier from this platform can currently supply.

**Q20 (is the dossier actually useful)**: **Conditionally yes, for a narrow
purpose.** The dossier is genuinely useful as a *fast, auditable financial-
change and regulatory-context brief* — every number traces to a real
`fact_id`/`event_id`, nothing is fabricated, and an analyst could use it to
prioritize which filings to read next. It is **not** useful as a substitute for
reading the actual filing — it cannot describe what the company does, and its
"Bull Case"/"Bear Case" text is inherited verbatim from a single prior LLM-
authored `investment_implications` row (real, but not synthesized fresh from
this session's own evidence), which a professional would need to independently
verify, not merely cite.

## 4. Coverage tables (Phase 19A) — full 26-ticker universe

| Company-context field | KNOWN | UNKNOWN | Category |
|---|---|---|---|
| business_description | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| products_services | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| revenue_segments | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| geographic_exposure | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| customer_concentration | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| supplier_dependencies | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| management_ownership | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| material_subsidiaries | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| strategic_priorities | 0/26 (0%) | 26/26 (100%) | DATA DOES NOT EXIST |
| business_model | 24/26 (92%) | 2/26 (8%) | DATA EXISTS AND IS USABLE (coarse, taxonomy-derived) |
| industry_sub_industry | 24/26 (92%) | 2/26 (8%) | DATA EXISTS AND IS USABLE |
| competitive_peer_context | 20/26 (77%) | 6/26 (23%) | DATA EXISTS AND IS USABLE (disclosed sector-proxy, not a real competitor list) |
| capital_structure | 12/26 (46%) | 14/26 (54%) | DATA EXISTS BUT HAS NOT BEEN EXTRACTED (for most of the 14 — see §5, Gap B) |
| regulatory_exposure | 8/26 (31%) | 18/26 (69%) | DATA EXISTS BUT IS THIN (real `events` coverage is genuinely sparse at ticker level) |
| historical_corporate_events | 6/26 (23%) | 20/26 (77%) | DATA EXISTS BUT IS THIN |

**Categories, kept separate per the explicit instruction (never combined)**:
- **DATA DOES NOT EXIST** (9 of 15 fields, 100% UNKNOWN, every ticker): no
  extraction effort recovers these — this platform's document corpus and
  extraction taxonomy were never designed to capture them (confirmed by direct
  keyword search across `causal_chain_steps`/`impact_assessments`/
  `extracted_facts`, §7 of the Phase 14 report).
- **DATA EXISTS BUT HAS NOT BEEN EXTRACTED**: `capital_structure`'s 14 UNKNOWN
  tickers overlap heavily with FRE-7B/7B.1's own finding — real, un-mined
  `results_notice` filings exist for several of them (e.g. more of CAP's own
  26 un-mined documents could extend its multi-year balance sheet).
- **DATA EXISTS BUT IS UNUSABLE**: none newly found in this pass beyond the
  already-disclosed currency/period-classification guards (covered exhaustively
  in the FRE-7B family of reports) — no new "exists but broken" case surfaced.
- **DATA EXISTS AND IS USABLE**: `business_model`/`industry_sub_industry`/
  `competitive_peer_context` — real, sourced, but coarse (sector-level, not
  company-specific).

**Provenance coverage**: 100% of `KNOWN` fields carry a real, non-empty
`source` string — structurally guaranteed and tested (`test_company_economic_
profile.py`, `test_company_state.py` both assert this for every field, not a
sample). **PIT-safe coverage**: 100% of temporally-scoped data — every date-
gated query in `company_state.py`/`economic_peer_taxonomy.py` filters on
`filing_date`/`announced_date`/`retrieval_date` <= the requested `as_of_date`,
verified by dedicated PIT tests in every relevant test file (`test_company_
state.py`'s monotonic-growth check, `test_economic_peer_taxonomy.py`'s
before/on/after retrieval-date check). No `CONFLICTING` or `STALE` status was
observed on any `EconomicProfile` field across the full 26-ticker run — `STALE`
only ever appears on `company_state.financial['accounting_anomaly_flags']`
(§7.2), not on any Phase 14 field.

**Source diversity**: 8 distinct originating modules/tables contribute `KNOWN`
fields across this pilot: `valuation_engine.get_normalized_statement`,
`company_intelligence.build_profile`, `economic_peer_taxonomy`,
`financial_health_flags`, `events`, `documents` (dealing filings),
`entity_context`, `company_thesis`/`investment_implications`.

**Freshness (a real, previously under-emphasized finding)**: the most recent
*knowable FY period* for the pilot's own financial-fact-bearing tickers is
uneven and, for two of them, badly stale relative to `as_of_date=2026-08-09`:
BUAFOODS/OANDO FY2024 (recent), **AFRIPRUD FY2022 (3.6 years stale)**, **CAP
FY2021 (4.6 years stale)**. AIRTELAFRI/UACN/MCNICHOLS/GEREGU have no FY period
resolvable at all (`fy_period_end=None`). This freshness gap is not visible
from `company_state.data_completeness` alone (which only measures whether a
field is populated, not how current it is) — a genuine blind spot in the
current coverage metric, flagged as an architectural weakness (§8).

## 5. Research-quality audit (Phase 19B)

Spot-checked directly against real database records, not merely re-run:

| Check | Result | Evidence |
|---|---|---|
| Factual consistency | **PASS** | BUAFOODS `fact_id=414` (equity, ₦554,337,667,000) and `fact_id=412` (assets, ₦1,142,637,894,000) match the narrative exactly, queried directly against `extracted_facts` |
| Provenance correctness | **PASS** | AFRIPRUD's CBN recapitalisation event traced to real `events.event_id=64`, `severity='critical'`, `category='banking'`, `announced_date='2024-03-28'` — exact match |
| Contradiction preservation | **PASS (untested in THIS pilot, confirmed elsewhere)** | None of these 8 had an active contradiction; TOTAL (outside this pilot) does, and its contradiction renders correctly per Phase 15's own test suite |
| PIT compliance | **PASS** | Structurally enforced and tested (§4); no lookahead found in any of the 8 runs |
| Stale-data handling | **PASS, with a caveat** | `financial_health_flags` results are explicitly labeled as not-PIT-parameterized in every rendered output (OANDO/AFRIPRUD's `margin_compression` both carry this disclosure inline) — correct behavior, but see §8 for the deeper limitation this papers over |
| Missing-data disclosure | **PASS** | Every UNKNOWN field names a specific, checkable reason (never a bare "UNKNOWN") |
| Fact/inference separation | **PASS** | Verified structurally via `is_inference` flag tests |
| **Duplicate information** | **REAL WEAKNESS FOUND** | AIRTELAFRI's 5 genuine, distinct insider transactions (different `doc_id`s, dates 2024-03-26 through 2024-04-03) render as 5 visually identical `"[MEDIUM] insider purchase"` lines with an identical, non-differentiating source string — a reader cannot tell from the narrative alone that these are 5 different real events without independently querying the underlying `InsiderTransaction` objects. Not fabricated duplication (the underlying data is correct and distinct), but a real presentation-layer defect. |
| Unsupported conclusions | **PASS, none found** | Every claim in every rendered report traces to a named source |
| Materiality consistency | **PASS** | `assess_materiality()`'s fixed thresholds applied identically across all 8 (e.g. every >=50% financial move classified CRITICAL, no exceptions found) |

## 6. Verification detail

### 6.1 Direct database spot-checks (3 of many possible, chosen to span
different evidence types)
1. `extracted_facts` where `fact_id IN (412, 414)` → exact match to BUAFOODS's
   rendered equity/assets figures.
2. `events` where `event_id=64` → exact match to AFRIPRUD's rendered CBN
   recapitalisation-directive description and severity.
3. `documents` where `ticker='AIRTELAFRI' AND doc_type='dealing'` → real count
   of 6, matching the pipeline's own disclosed "5 classified... from 6 real...
   filings" (1 correctly excluded as vesting/ambiguous).

### 6.2 The insider-transaction presentation weakness (detail)
Real underlying data (queried directly): 5 `InsiderTransaction` objects with
distinct `doc_id`s (8190, 8191, 8203, 8204, 8292) and distinct filing dates.
`change_detection.py`'s own per-transaction `description` field is the fixed
string `"insider {nature.lower()}"` with no date/doc_id interpolated — a real,
fixable gap (not investigated further this pass, since Phase 19 is
assessment-only and this pass does not modify code).

## 7. Analyst Gap Analysis (Phase 19C)

| Gap | Category | Priority | Notes |
|---|---|---|---|
| Business description / products & services | **E** — fundamentally unavailable from this platform's current corpus and taxonomy | **HIGHEST** — blocks Q1/Q2 for every company, every time | Would require a new extraction taxonomy targeting narrative sections of annual reports (MD&A-equivalent), not just financial-statement tables |
| Revenue segments / geographic exposure | **E** | HIGH | Same root cause as above — segment reporting is a real, extractable disclosure type in NGX annual reports but this platform's extraction has never targeted it |
| Customer concentration / supplier dependencies | **C** — requires new first-party acquisition effort (targeted extraction from annual-report risk-factor sections) | MEDIUM | Genuinely disclosed by SOME NGX issuers in risk sections; not systematically extracted |
| Management/ownership | **B** — available from the existing first-party corpus but requires new extraction | HIGH | `company_memory.py`'s own `management_history` field already exists in the schema, just never populated — this is an extraction-effort gap, not an acquisition gap |
| Material subsidiaries | **B** | MEDIUM | `02_knowledge_graph_expansion.md` already named this exact need (`subsidiary_of` edges); unlocks the `sum_of_the_parts` valuation adapter too |
| **FY financial-statement freshness (AFRIPRUD/CAP, 3.6-4.6 years stale)** | **A** — already available but not extracted | **HIGHEST** (re-confirms FRE-7B's own finding, now quantified from the consumer-facing dossier side, not just the valuation side) | 94% of FRE-7B's identified un-mined `results_notice` backlog already has retrievable text (per FRE-7B.1) — this is the single most leverage-efficient gap on this entire list |
| Ticker-level regulatory/corporate-event coverage | **B** | MEDIUM | `events` table exists and is real; only 26 ticker-scoped rows exist platform-wide — an extraction-breadth gap, not a schema gap |
| Sector-level peer taxonomy granularity | **B** (already substantially addressed in FRE-7A, remaining gap is data depth not design) | MEDIUM | Confirmed unchanged from FRE-7A/7B.2's own findings |
| Independent, professionally-sourced analyst research/estimates | **D** — requires external data | LOW (explicitly out of licensing scope per `OWNER_DECISION_BACKLOG_2026-08-02.md` §2) | Not pursued |
| Real-time/near-real-time filing ingestion (Phase 18's missing trigger) | **C** | MEDIUM | Infrastructure, not data, gap |

## 8. Capability scorecard (Phase 19D) — independent dimensions, no composite

| Dimension | Assessment | Evidence |
|---|---|---|
| Company understanding (qualitative) | **VERY WEAK** | 0% coverage on 9 of 15 Phase-14 fields, every ticker (§4) |
| Fundamental analysis | **MODERATE, uneven** | Real for 6/8 pilot tickers, but freshness varies wildly (current to 4.6 years stale) |
| Regulatory intelligence | **WEAK, real where present** | 1/8 pilot tickers had real content; when present (AFRIPRUD) it was accurate, well-sourced, and correctly sector-attributed |
| Market intelligence | **STRONG** | 8/8 pilot tickers, real price/liquidity/volatility data, correctly PIT-gated |
| Corporate-event intelligence | **WEAK** | Same 26-row ticker-scoped `events` limitation as regulatory |
| Insider intelligence | **MODERATE mechanism, WEAK coverage** | Classification itself is accurate and well-tested (§5); real content for only 1/8 pilot tickers; a real presentation defect found (§5, §6.2) |
| Valuation | **WEAK, honestly gated** | FRE-7 pilot gate remains FAILED (unchanged); every dossier correctly reports `VALUATION_CONFIDENCE` rather than a fabricated number |
| Risk analysis | **MODERATE** | Real, named risks for 3/8; accounting-anomaly flags work but are not PIT-parameterized (a real, disclosed limitation) |
| Catalyst identification | **WEAK** | Populated for 3/8, entirely dependent on a single inherited `investment_implications` row, never freshly synthesized from this session's own evidence |
| Due diligence support | **MODERATE** | The evidence-citation/fact-vs-inference machinery is genuinely strong and auditable; the underlying facts it operates on are thin |
| Portfolio monitoring | **WEAK infrastructure, UNTESTED at scale** | `portfolio_decision_support.py` works (prior session, 9/9 tests) but was not re-exercised in this pilot; its `cross_reference()` cost (~18s/ticker uncached) makes it impractical for a real multi-holding portfolio today |
| Research automation | **STRONG mechanism, WEAK content depth** | The pipeline runs cleanly end-to-end for every ticker tried, including thin/unclassified ones, without crashing or fabricating — the automation itself is reliable; what it automates is limited by data depth |
| Evidence/provenance | **STRONG** | 100% provenance coverage on populated fields, verified by direct spot-check against 3 independent record types (§6.1), not just asserted |
| Data completeness | **WEAK, correctly measured but incomplete as a metric** | `data_completeness` measures presence, not freshness (§4) — a real metric gap, not just a data gap |

## 9. Production readiness (Phase 19E)

**Classification: Analyst Research Assistant.**

Not a Research Prototype: the pipeline is real, tested (302+ checks across the
prior two build phases, all reconfirmed operable in this pilot), runs cleanly
end-to-end for 8 deliberately-varied real tickers without a single crash or
fabrication, and every claim traced back to a verifiable database record in
every spot-check attempted.

Not Institutional Research Infrastructure or a Production Platform: an
institutional analyst cannot get a company overview (§3, Q1/Q2), regulatory/
corporate-event coverage is present for roughly 1 in 8 real tickers, valuation
is honestly unavailable for the large majority, and freshness varies by years
with no dedicated freshness metric to surface that automatically (§4). A real
analyst would still need to read the primary filings for almost every
qualitative question this task itself posed (Q1, Q2, most of Q10-Q15).

What earns it "Analyst Research Assistant" rather than "Research Prototype":
the evidence/provenance/PIT machinery is genuinely production-grade (100%
sourced, spot-check-verified, structurally tested) — a real analyst could
trust what the system DOES say, even though it says too little. That
reliability-over-coverage trade is exactly what distinguishes an assistant
worth using from a prototype not yet trustworthy enough to use.

## 10. Failures

No pipeline crash, no fabricated fact, no PIT violation, and no unsupported
conclusion was found in this pass. The one real defect found (§5/§6.2,
duplicate-looking insider-transaction presentation) is a quality/UX issue in
already-correct underlying data, not a correctness failure.

## 11. Architectural weaknesses

1. **No freshness metric** — `data_completeness` conflates "ever populated"
   with "current," masking real gaps like AFRIPRUD/CAP's multi-year-stale FY
   data (§4).
2. **`financial_health_flags.compute_flags_for_ticker()` still has no
   `as_of_date` parameter** (inherited from Phase 1, re-surfaced here in a
   live pilot rather than only in unit tests) — every flag-driven change in
   this pilot correctly disclosed this, but the underlying limitation is
   unresolved.
3. **`change_detection.py`'s insider-transaction description string is not
   per-transaction differentiated** (§6.2) — a real, small, fixable gap.
4. **`portfolio_memory.cross_reference()`'s ~18s/call uncached cost** remains
   unresolved and was not exercised at scale in this pilot (deliberately, to
   keep this assessment's own runtime bounded) — genuinely untested at
   realistic portfolio size.
5. **Catalysts/risks/bull-bear-base content is entirely inherited, never
   freshly synthesized** — for tickers whose one `investment_implications` row
   predates this session's own newly-detected changes (e.g. BUAFOODS's
   +168.5% equity move), the thesis text and the freshly-detected changes can
   go stale relative to each other with no mechanism to flag that divergence.

## 12. Data bottlenecks

Unchanged from — and now independently re-confirmed by — the FRE-7B family of
reports: the dominant, highest-leverage bottleneck is FY financial-statement
extraction depth and freshness (Gap A/B in §7), not schema, not architecture,
and not the reasoning/composition layer built in Phases 1-18, which performed
reliably everywhere it had real data to work with.

## 13. Recommended next capability

**Not a new module.** Per this assessment's own evidence: extend the existing,
already-proven FRE-7B.1 targeted-extraction methodology (deterministic label
mapping, grounding-checked, hand-verified) specifically to (a) recover more
recent FY periods for AFRIPRUD/CAP and any other multi-year-stale ticker, and
(b) populate `company_memory.py`'s already-existing but always-empty
`management_history` field from the same corpus — both are Gap A/B items,
both reuse infrastructure that already exists and is already tested, and both
would move real numbers in §4's coverage table rather than adding a new,
untested capability on top of a thin data foundation. A secondary,
independent recommendation: add a freshness field to `CompanyState`/
`EconomicProfile` (the metric gap in §11.1) — small, additive, and would make
the NEXT assessment's coverage table honestly reflect currency, not just
presence.

## 14. Exact files changed

**New**: `scripts/fre/phase19_assessment_pipeline.py` (diagnostic runner, no
test file — same convention as `fre7b_accounting_depth_audit.py`, an audit
tool rather than production code), this report.
**Modified**: none.

## 15. Exact tests run and results

This phase is an assessment, not a build — no new production module required
new tests. The diagnostic runner (`phase19_assessment_pipeline.py`) was
executed directly (not via a test-assertion script) and its output inspected
by hand for §3-§6; its own internal assertion (`doc_after == doc_before`,
i.e. zero database writes) passed. Separately, `scripts/fre/test_company_
economic_profile.py` (25/25), `test_company_intelligence_bundle.py` (16/16),
`test_research_questions.py` (16/16), `test_continuous_intelligence.py`
(9/9), and `test_company_research_report.py` (61/61) — all from the prior
Phases 14-18 build — were confirmed still passing before this assessment
began, establishing that the pipeline being assessed was itself known-good
going in, not assessed in an unverified state.
