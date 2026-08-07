# Multi-Currency Financial Architecture Review

*2026-08-04. Architecture review only — no implementation, no schema
changes, no database writes, no currency conversion, no FX acquisition.
Triggered directly by the FSI Depth Pilot's own AIRTELAFRI finding
(`docs/FSI_DEPTH_PILOT_EXECUTION_2026-08-04.md`): a fully clean,
fully-verified filing that could not be safely written because
`extracted_facts` has no currency representation and every other
extracted company reports in NGN. Every claim below is tagged
**[Verified — schema]** (confirmed by direct inspection of
`data/ngx.sqlite` this session), **[Verified — code]** (confirmed by
reading `src/ngxrot/`), or **[Judgment]** (design reasoning, not a
direct measurement).*

---

## Owner Decision (read this first)

**Should the platform become fully multi-currency before expanding FSI
beyond the pilot? No — not "fully multi-currency" as a prerequisite,
but yes to one small, additive, currency-AWARE metadata change before
any further extraction touches a non-NGN filing.**

The evidence in this review does not support a large multi-currency
migration project. It supports something much narrower: **the platform
needs a currency field at the fact level (and a reporting-currency
attribute at the security level) before writing a second foreign-
currency fact — not a conversion engine, not a normalization pipeline,
not FX acquisition.** Native-currency storage with explicit metadata
(Section 5's recommended model) is the only option that requires no FX
data acquisition, introduces no look-ahead risk, and preserves the
platform's own PIT discipline unchanged. Normalized, dual-storage, and
deferred-conversion models are all evaluated in Section 5 and all
rejected as premature — each depends on FX data the platform does not
yet have (`fx_rates` exists as a table **[Verified — schema]** but
holds zero rows) and each introduces a real, avoidable conversion/
look-ahead risk this review does not recommend accepting yet.

**This is a metadata gap, not an architecture crisis.** Section 3
shows the platform already has *dormant* multi-currency scaffolding in
three separate places (`index_levels.currency`, `corporate_actions.currency`,
`fx_rates`) that nobody wired to `extracted_facts` — this review's
practical recommendation is to extend that same, already-established
pattern to the one table that's missing it, not to invent a new one.

---

## 1. The problem, precisely stated

Two genuinely different currency questions exist on this platform, and
conflating them is the single most likely design mistake a rushed fix
could make:

1. **Trading/market currency** — the currency a security's SHARE PRICE
   is quoted in on the exchange. For every NGX-listed security, this
   is NGN, always, by construction — **[Judgment, economically certain]**
   this is not actually a variable to model; `equity_prices` correctly
   has no currency column because there is no ambiguity to resolve.
2. **Financial-statement reporting currency** — the currency a
   company's INCOME STATEMENT, BALANCE SHEET, and CASH FLOW STATEMENT
   are prepared in. This is independent of trading currency. Airtel
   Africa plc trades on NGX in Naira but reports its consolidated
   financial statements in US dollars, because it is UK-incorporated
   and dual-listed (LSE/NGX) **[Verified — the FSI Depth Pilot's own
   direct reading of doc 9809]**. This is the actual, real ambiguity —
   and it is scoped to exactly one table on this platform:
   `extracted_facts`.

**This distinction matters concretely**: a fix that added a currency
field to `equity_prices` would be solving a problem that does not
exist. A fix scoped to `extracted_facts` (and the security-level
default that feeds it) addresses the real one.

---

## 2. Current-state audit — every currency-relevant table

*Every row below is a direct schema inspection this session
**[Verified — schema]**, not carried forward from prior documentation.*

| Table | Currency-relevant column(s) | Populated? | Status |
|---|---|---|---|
| `equity_prices` | none | N/A | Correctly currency-agnostic — NGX trading price is always NGN, no ambiguity exists to encode |
| `index_levels` | `currency` | Only `'NGN'` ever written | **Dormant scaffolding** — the column exists, was clearly anticipated, never diverges from NGN in practice |
| `corporate_actions` | `currency` | Only `'NGN'` ever written, and only for synthetic test-fixture rows (`SYNBNKA/B/C`, per the H-017 pre-registration's own erratum finding) — **zero real corporate-action rows exist at all** | **Dormant scaffolding, unused in practice for real data** |
| `fx_rates` | dedicated table: `trade_date, rate_type, ngn_per_usd, source_id, confidence, as_of_date` | **Zero rows** | **Fully dormant** — a real, PIT-shaped schema (has `as_of_date`) already exists for exactly this purpose and has simply never been populated |
| `macro_series` | none | N/A (only series present: `BRENT`, USD/barrel) | **A live, if currently harmless, gap** — Brent crude is stored as a bare `value` with no currency/unit metadata; this has not caused a visible problem because H-004 (the only hypothesis to consume it) used it as a lagged-return input, not an absolute level, but the ambiguity is real and unresolved |
| `extracted_facts` | none | N/A | **The actual blocker** — `numeric_value` has no currency field, and every fact ever written (dividend/rights_issue/bonus_issue/revenue/net_profit/assets/.../cfo/cfi/cff, 300+ rows across every FSI phase) is implicitly NGN because every company extracted to date happens to report in NGN. AIRTELAFRI is the first real case where that implicit assumption would have been wrong |
| `securities` | none | N/A | **No entity-level reporting-currency attribute exists** — there is nowhere on the platform today to record "this company reports in USD" as a standing fact about the company, independent of any single filing |

---

## 3. Which modules assume NGN, and which are genuinely currency-agnostic

*Direct code inspection this session **[Verified — code]**, not
inferred.*

### Modules that implicitly assume NGN (would need review before touching a foreign-currency fact)

- **`src/ngxrot/fre/financial_ratios.py`** — reads `extracted_facts.numeric_value`
  directly with no currency check. **Important nuance, precise rather
  than alarmist**: most ratios computed here (e.g., net_profit/revenue)
  divide two facts belonging to the SAME ticker, and a single company
  reports its entire statement set in one currency — so a same-ticker
  ratio is currency-safe **by construction**, even without an explicit
  check, as long as no cross-ticker ratio is ever computed. The real
  risk is narrower than "this module is broken" — it is "this module
  has no explicit guard against a future cross-ticker or
  currency-mixing computation," which does not exist yet but could be
  added carelessly later.
- **`src/ngxrot/fre/financial_health_flags.py`** — same profile as
  `financial_ratios.py`: same-ticker ratio logic, currency-safe today
  by construction, unguarded against future misuse.
- **`src/ngxrot/fre/valuation_engine.py`** — architecture-only, no
  implemented formula yet **[Verified — code, module docstring: "This is
  still not a working valuation model"]**. **This is the module most
  directly at risk once it IS implemented**: an EV/EBITDA-style
  multiple requires dividing a market-cap figure (derived from NGX
  share price × share count — always NGN) by an EBITDA figure (from
  `extracted_facts` — could be foreign-currency). This is a genuine,
  concrete, CROSS-METRIC currency mismatch, not merely a cross-ticker
  one — the clearest illustration in this review of why the gap
  matters for a real, planned future consumer, not a hypothetical one.
- **`src/ngxrot/alpha_engine.py`** — reports capacity figures in NGN
  text (`"median leg capacity ~NGN 694,336"`), currently accurate
  because capacity derives from `equity_prices`/ADTV (always NGN), not
  from `extracted_facts` — not at risk today, but would need review if
  a future capacity concept ever blended in a financial-statement
  figure.
- **`src/ngxrot/list2_parser.py`** — market cap panel explicitly
  documented as "NGN millions" **[Verified — code, docstring]** —
  correctly currency-specific because it derives from NGX trading
  price × shares outstanding, not from financial statements.
- **`src/ngxrot/company_intelligence.py`** — consumes facts for
  narrative/reasoning output; not verified in this pass to have an
  explicit currency guard, flagged as needing the same review as
  `financial_ratios.py` once multi-currency facts exist.

### Modules that are genuinely currency-agnostic (no change needed)

- **`stats.py`** (Holm/BH, placebo, HAC, DSR) — operates on returns and
  p-values, dimensionless by construction.
- **`costs.py`** — rates are percentages, not currency amounts.
- **`riskfree.py`** — CBN MPR is a percentage rate, not a currency
  amount; already correctly disclosed as a nominal, NGN-policy-context
  rate, unaffected by financial-statement currency questions.
- **`rng.py`, `confidence_rating.py`, `ic_report.py`** — no monetary
  values at all.
- **`backtest_xs.py`'s return/Sharpe/placebo machinery** — operates on
  price returns (`equity_prices`), which per Section 1 has no currency
  ambiguity to begin with.

### Reasoning-layer tables — a nuanced, mostly-safe picture

- **`financial_reasoning_conclusions.value_numeric`** — inherits
  whatever currency its source facts carry. For a `ratio`-type
  conclusion, currency-safe by the same same-ticker logic as
  `financial_ratios.py`. For a `trend`-type conclusion on an absolute
  figure (e.g., "revenue trending up"), the DIRECTION is currency-safe
  (a USD revenue trending up is still trending up) but the MAGNITUDE
  would not be comparable across a mixed-currency universe without
  normalization — not a defect today (no foreign-currency trend
  conclusion has ever been computed), but a real constraint on any
  future cross-ticker trend ranking.
- **`investment_implications`** — columns are overwhelmingly
  qualitative/directional (`direction`, `magnitude`, `*_delta` fields
  read as bucketed/qualitative per the schema's own naming, not
  audited line-by-line in this pass) — **[Judgment]** likely low risk,
  flagged as needing the same one-time review as the other reasoning
  tables before any foreign-currency company's implications are
  generated, not audited exhaustively here per the "no implementation"
  scope of this review.

---

## 4. Worked example: why this is not a hypothetical concern

Per Section 3, `valuation_engine.py`'s own architecture anticipates an
EV/EBITDA-style multiple. For AIRTELAFRI specifically:

- Market capitalization would derive from NGX share price (NGN) ×
  shares outstanding.
- EBITDA would derive from `extracted_facts` — for AIRTELAFRI, US$
  millions **[Verified — FSI Depth Pilot's own direct reading]**.
- **Computing EV/EBITDA today, with no currency awareness anywhere in
  the pipeline, would silently divide an NGN numerator by a USD
  denominator** — not a cross-TICKER comparison error (the kind a
  careful analyst might catch by inspection), but a cross-CURRENCY
  error INSIDE a single company's own single ratio, the harder kind of
  bug to notice because the ticker, the period, and the company are
  all self-consistent — only the unit is wrong.

This is the concrete, load-bearing reason this review exists before
`valuation_engine.py` is ever implemented for real, and before FSI
extraction touches a second foreign-currency filing (Seplat, per prior
FSI documentation, is another dual-listed name with the same profile).

---

## 5. Architecture alternatives

### 5.1 Native-currency storage (store each fact in its own reporting currency, with a currency field)

Add a `currency` column to `extracted_facts` (and a default
`reporting_currency` attribute at the `securities` level, so every new
fact can inherit a sensible default without requiring it to be
re-specified every time). No conversion happens anywhere in the
pipeline. Every consumer that needs a single comparable unit
(cross-ticker ranking, portfolio-level aggregation) must explicitly
check currency and either skip mixed-currency comparisons or convert
at the point of use, never silently.

### 5.2 Normalized-to-base-currency storage (convert every fact to NGN at extraction time, store only the converted value)

Every fact is converted to NGN using the FX rate applicable to its
filing's PIT date, and only the converted NGN value is stored. The
native figure is discarded (or kept only in `description`/`evidence`
text, not as a structured, queryable value).

### 5.3 Dual storage (store both native and normalized value)

Both the native-currency figure and an NGN-normalized figure are
stored as separate columns, computed once at extraction/write time.

### 5.4 Deferred conversion (store native value + FX metadata, convert only at query/consumption time, never at write time)

Store the native-currency value plus a reference to the FX rate/date
that WOULD be used to convert it, but never actually compute and store
a converted number — conversion happens, if ever, in a downstream
query or analysis step, using whatever FX rate is appropriate for that
specific use (which may differ by use case — a spot rate for a
point-in-time snapshot vs. an average rate for a period comparison).

### 5.5 Comparison

| Dimension | Native-currency (5.1) | Normalized (5.2) | Dual (5.3) | Deferred (5.4) |
|---|---|---|---|---|
| **Point-in-time integrity** | Strongest — no conversion, nothing to get wrong about which FX rate/date applies | Weakest — requires committing to ONE PIT-appropriate FX rate at write time, permanently; a later-discovered FX data error would require re-extracting the fact, not just fixing a rate | Same PIT risk as 5.2, doubled (must get the FX rate right AND keep both columns in sync) | Strong — defers the PIT-rate decision to whoever actually needs a converted number, at the moment they need it, with full context about which rate is appropriate for their specific use |
| **Auditability** | Strongest — the stored number is exactly what the filing said, always independently verifiable against the source document (the platform's own grounding-check discipline stays meaningful) | Weaker — the stored number is a DERIVED figure; auditing it requires also auditing the FX rate used, adding a second dependency to every grounding check | Weakest in one sense (two numbers to keep consistent) but preserves the native figure for direct audit | Strong — native figure stays directly auditable; any conversion is computed and can be re-derived/re-audited independently at consumption time |
| **Reproducibility** | Strongest — a fact written today reads identically in five years; nothing about it depends on when a query is run | Weakest — reproducing a historical NGN-normalized figure requires reproducing the EXACT FX rate/date/source used originally, a new reproducibility dependency that doesn't exist anywhere else on this platform today | Same weakness as 5.2 for the normalized column specifically | Strong for the stored value; the CONVERTED figure (if computed later) is only as reproducible as whatever FX data source is queried at that time — a real, disclosed limitation, but isolated to the consumption step, not baked into the stored fact |
| **Implementation complexity** | Lowest — one additive column, no conversion logic, no FX data pipeline required at all | Highest — requires FX data acquisition (not yet done — `fx_rates` has zero rows), a PIT-safe rate-lookup function (a new piece of infrastructure), and a conversion step wired into every future extraction | Highest of all — everything normalized storage requires, plus keeping two values consistent | Medium — the metadata field is cheap; the actual FX-lookup/conversion logic can be built later, incrementally, only when a real consumer needs it |
| **Future scalability** | Good — works cleanly as more foreign-currency companies are added; consumers that need normalization can build it on top without re-touching historical facts | Good ONCE built, but every currency added requires trustworthy historical FX data for its full sample window — a real, recurring acquisition cost per currency, not a one-time cost | Same as normalized, plus doubled storage/consistency burden per currency added | Good — scales the same way as native storage; conversion logic, once built, applies uniformly to any currency without re-touching stored facts |
| **Frontier-market research relevance** | High — preserves the platform's own FX-regime-conditioning research interest (per `docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`'s FMDQ NAFEX candidate) as a SEPARATE, explicit research question rather than a silently-baked-in assumption | Actively works against this interest — collapsing a company's real reporting currency into NGN at write time destroys the very information (which companies report in which currency, and how FX-sensitive their reported figures are) that a future FX-regime-conditioning hypothesis would want to examine | Partially preserves it (native column survives) but at doubled cost for no clear research benefit over 5.1 | Preserves it fully, same as native storage |

### 5.6 Recommendation

**Native-currency storage (5.1), extended later by deferred conversion
(5.4) only once a real consumer needs a normalized number.** This is
not a close call across the table above — native storage wins or ties
on every dimension except "immediate usability for cross-currency
ranking," which no current consumer actually needs yet (per Section 3,
every existing consumer either doesn't touch `extracted_facts` at all,
or only computes same-ticker ratios that are currency-safe already).
Normalized and dual storage both require FX data acquisition this
review is explicitly not authorized to begin, and both introduce a new
reproducibility dependency (a committed historical FX rate) that
nothing else on this platform currently requires.

---

## 6. Required metadata (design specification, not implementation)

- **At the fact level** (`extracted_facts`): a `currency` field
  (ISO 4217 code, e.g. `NGN`, `USD`), required, no silent default —
  every future INSERT must specify it explicitly, matching the
  platform's own existing discipline of refusing silent defaults
  elsewhere (e.g. `rng.py`'s mandatory-seed refusal, per the Frontier
  Methodology Audit's own Part 1 findings).
- **At the security level** (`securities`): an optional
  `reporting_currency` default attribute, used only to pre-fill the
  expected currency for a new extraction (a convenience, not a source
  of truth) — the fact-level field remains authoritative, since a
  company could in principle change reporting currency over time (rare
  but not impossible, e.g. following a corporate restructuring).
- **For any future normalized/converted figure** (Section 5.4, deferred):
  the FX rate value, the FX rate's own `as_of`/PIT date, and the source
  of that rate must all be recorded alongside the converted figure —
  never a bare converted number with no record of how it was produced,
  mirroring the platform's own `riskfree.py` precedent
  (`mpr_asof_series()`'s point-in-time, never-forward-filled discipline)
  as the correct model to reuse, not reinvent.

---

## 7. Required validation rules (design specification)

1. **No fact may be written without an explicit currency** — no
   default, no inference from the ticker alone (a `securities`-level
   default may pre-fill a form/script, but the write itself must
   confirm it, not silently trust it).
2. **Any ratio or derived computation spanning two facts must assert
   both facts share the same currency before dividing** — a cheap,
   mechanical guard that would have caught the EV/EBITDA scenario in
   Section 4 before it ever produced a silently wrong number.
3. **`fcf`/`ebitda`-style DERIVED facts (per the existing
   `confidence_tier='derived'` convention, extended in the FSI Depth
   Pilot to `ebitda`) must derive from same-currency source facts
   only** — GEREGU's own derived EBITDA (operating profit + D&A) is
   currency-safe today only because both legs were NGN; this rule
   makes that an enforced invariant, not an accident.
4. **Any future FX-rate lookup used for a converted figure must be
   PIT-safe** — the rate known as of the filing's own knowability date,
   never a rate queried "as of today" applied retroactively, mirroring
   `riskfree.py`'s existing pattern exactly.
5. **Cross-ticker or cross-currency aggregation (e.g., a future
   portfolio-level sum of EBITDA across multiple holdings) must fail
   loudly, not silently sum mismatched currencies** — the single most
   important validation rule this review can specify, since it is
   exactly the failure mode that would be hardest to notice after the
   fact.

---

## 8. Subsystems explicitly identified as affected

| Subsystem | Affected? | How |
|---|---|---|
| `extracted_facts` (schema) | **Yes — the core change** | Needs a `currency` field (design only, not implemented here) |
| `securities` (schema) | **Yes, optionally** | A `reporting_currency` default attribute would help, not strictly required |
| `fre/financial_ratios.py` | **Yes — needs a same-currency assertion added** | Currently safe by accident (same-ticker ratios), not by design |
| `fre/financial_health_flags.py` | **Yes — same reason as financial_ratios.py** | Same fix needed |
| `fre/valuation_engine.py` | **Yes — the highest-stakes consumer** | Not yet implemented; must NOT be implemented with a formula that mixes an NGN market-cap figure and a foreign-currency fundamentals figure without an explicit conversion step |
| `financial_reasoning_conclusions` | **Partially** | Ratio-type conclusions safe; magnitude comparisons across a mixed-currency universe are not, and don't exist yet |
| `investment_implications` | **Likely low risk, not fully audited** | Flagged for a follow-up review, not resolved here |
| `alpha_engine.py` | **No, currently** | Derives capacity from price/ADTV data only, which has no currency ambiguity |
| `backtest_xs.py`, `stats.py`, `costs.py`, `riskfree.py` | **No** | Operate on returns, rates, or percentages — dimensionless or already currency-specific in a way this review doesn't change |
| `fx_rates` (schema) | **Relevant, dormant** | Already exists, already PIT-shaped (`as_of_date`), the natural home for Section 5.4's deferred-conversion rate lookups whenever that is built — no new table needed |
| `index_levels`, `corporate_actions` | **Already scaffolded, unaffected** | Both already have a `currency` column; this review's recommendation extends the SAME pattern to `extracted_facts`, not a new one |

---

## 9. Migration strategy — additive, preserving historical reproducibility

1. **Add the `currency` field to `extracted_facts` as a nullable
   column with no default value enforced at the database level, but a
   mandatory value enforced at the application/write-code level for
   every NEW fact going forward.** This is additive per the platform's
   own established convention (every prior schema evolution on this
   platform — `restates_fact_id`, `confidence_tier`, etc. — has been
   additive, not destructive).
2. **Backfill existing facts with `currency='NGN'` as a one-time,
   fully justified, evidence-based operation** — every one of the
   300+ existing facts was extracted from a company already confirmed
   (by the extraction process itself) to report in Naira; this is not
   a guess, it is recording a fact that was always true but never
   encoded. This backfill changes no VALUES, only adds metadata —
   historical reproducibility is fully preserved because every
   existing `numeric_value` stays byte-identical.
3. **Do not touch `equity_prices`, `index_levels`'s existing NGN rows,
   or any other table** — Section 2 already shows these are either
   correctly currency-agnostic or already correctly scaffolded.
4. **Re-attempt AIRTELAFRI as the first fact written under the new
   field** — already fully read and verified clean per the FSI Depth
   Pilot; this becomes the first real test of the new metadata, not a
   new extraction effort.
5. **Do not build FX conversion, normalization, or dual-storage until
   a real, specific consumer needs it** — per Section 5's comparison,
   this is not a cost worth paying speculatively; `valuation_engine.py`
   remains architecture-only and unimplemented regardless of this
   migration, so there is no current urgency to solve the conversion
   problem, only the metadata-integrity problem.
6. **Add the same-currency assertion (Section 7, rule 2) to
   `financial_ratios.py` and `financial_health_flags.py` as a defensive
   guard**, even though today's data would pass it trivially — this
   converts an accidental safety property into an enforced one, cheap
   to add now, expensive to discover missing later once more
   currencies are added.

This migration is deliberately small. It does not resolve every
question this review raises (normalization strategy, FX acquisition,
full reasoning-layer audit) — it resolves the one that is actually
blocking the next unit of real work (writing AIRTELAFRI's facts),
consistent with every prior document in this series' own discipline of
recommending the smallest action that unblocks the next real step,
not the largest defensible project.

---

## 10. What this review does not resolve (explicitly out of scope, named rather than ignored)

- **FX rate acquisition** — `fx_rates` remains empty; this review does
  not recommend populating it yet, since no consumer requires a
  converted figure today (Section 5.6).
- **A full audit of `investment_implications`** — flagged as likely
  low-risk in Section 3 but not exhaustively verified line-by-line.
- **Whether any company other than AIRTELAFRI and Seplat reports in a
  non-NGN currency** — not surveyed in this review; a real, cheap,
  future scoping question (mirroring the FSI audit series' own
  discipline of scoping before acting) that should precede any broader
  FSI expansion resuming, per the owner's own stated sequencing.
- **Historical FX-rate data quality**, should normalization ever be
  pursued later — Section 5.5's comparison already names this as a
  real, recurring cost per currency, not resolved here.
