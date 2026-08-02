# FSI Phase 26 — Pre-registration

*Sector-to-Company-Type Mapping. Per the owner's explicit instruction:
gap identified, ≥3 alternatives compared and rejected, implemented
without an approval checkpoint.*

## Why this is the highest-priority remaining architectural gap

Phase 23 populated `securities.sector_ngx` for 136/320 real securities
from NGX's own official classification. `valuation_engine.
classify_company_type()` (FRE-6) has, since it was first written,
returned `"general"` for every ticker with no owner-confirmed override
— not because `"general"` is usually correct, but because the one
input that could make it more accurate (`sector_ngx`) did not exist
yet. It now does. This is a genuine architectural disconnect between
two already-completed subsystems (Phase 23's real sector data; FRE-6's
company-type-conditioned method-eligibility design), not a new
capability being invented — closing it is squarely "removing blocking
technical debt between existing subsystems," one of the standing
authorization's three named justifications for a phase.

## Alternatives considered and rejected (≥3, with technical justification)

1. **Industry Exposure Integration first** (the user's own named
   Phase 27). Rejected as Phase 26's own scope, not as a bad idea —
   `company_intelligence.py`'s `UNAVAILABLE_FIELDS["Industry
   Exposure"]` is a *disclosure* field with no consuming logic today;
   wiring it requires designing what "Industry Exposure" should
   actually state (a single sector label? a peer set? something else)
   — a distinct design surface from a deterministic sector→
   company_type lookup table. Sequencing this second, as the user's
   own instruction already specifies, avoids conflating two different
   kinds of judgment call in one phase.
2. **A `reit` (or similar new) company_type**, to give
   `CONSTRUCTION/REAL ESTATE`'s REIT sub-industry (`NREIT`, `SFSREIT`,
   `UHOMREIT`, `UPDCREIT`) its own valuation-method set (NAV/FFO-style,
   not DCF/EV-EBITDA/PE). Rejected for this phase — inventing a new
   company_type is a valuation-*architecture* change (a new entry in
   `configs/valuation_method_eligibility.toml` with its own method
   set and rationale), not a translation-layer change onto the
   *existing* six-type taxonomy this phase is scoped to. REITs are
   mapped to `"general"` here (the conservative default), with this
   gap disclosed explicitly rather than silently guessed around.
3. **Resolving `FINANCIAL SERVICES`'s `"Other Financial Institutions"`
   sub-industry to `"bank"` or `"general"` by researching each of its
   9 real tickers individually** (AFRIPRUD, DEAPCAP, FCMB, NGXGROUP,
   ROYALEX, STANBIC, UCAP, ACCESSCORP, FIRSTHOLDCO). Rejected — this
   sub-industry is confirmed, directly against real data, to be a
   genuine NGX-defined grab-bag spanning a capital-markets firm
   (UCAP), a capital-management firm (DEAPCAP), the exchange operator
   itself (NGXGROUP), an insurance/general-commerce name (ROYALEX),
   and several de facto bank holding companies (FCMB, STANBIC,
   ACCESSCORP, FIRSTHOLDCO) — resolving it would require researching
   each ticker's own actual business individually, which is
   *per-company inference*, exactly what this phase's own
   "deterministic translation, never inference" mandate forbids. Left
   unresolved, disclosed, falling back to `"general"`.
4. **Extending Phase 24's `sector_coverage.py` to also break down
   coverage by company_type**, instead of this phase. Rejected — that
   would consume this mapping before it exists; sequencing is the
   other way around, and Phase 24's own scope (research/watchlist
   coverage) is a distinct question from valuation-method eligibility.

## Design

- New config `configs/sector_company_type_mapping.toml` — the same
  established pattern as `valuation_method_eligibility.toml`/
  `relation_taxonomy.toml` (a config change, not a code change, to
  add/adjust a mapping). Two tables:
  - `[sector]`: 12 of NGX's 13 top-level sectors, each mapped to
    exactly one company_type. 11 map to `"general"` (matching that
    type's own stated scope: "industrial/consumer/agriculture/
    oil_gas/telecom/utilities/healthcare," which covers AGRICULTURE,
    CONSUMER GOODS, OIL AND GAS, UTILITIES, HEALTHCARE, ICT, and — as
    the conservative default for sectors the existing taxonomy has no
    dedicated bucket for — CONSTRUCTION/REAL ESTATE, INDUSTRIAL GOODS,
    INVESTMENT, NATURAL RESOURCES, SERVICES). `CONGLOMERATES` maps to
    `"holding_company"` — NGX's own "Conglomerates" sector denotes a
    diversified multi-business structure, matching that company
    type's own stated rationale ("value each subsidiary via its own
    applicable method, aggregate, apply a disclosed holdco discount")
    exactly. `FINANCIAL SERVICES` is deliberately absent from this
    table — resolved via sub-industry instead (see below), never
    guessed at the top level.
  - `[financial_services_sub_industry]`: only the two sub-industries
    with an unambiguous, NGX-defined single company_type —
    `"Banking"` → `"bank"`, `"Insurance Carriers, Brokers and
    Services"` → `"insurance"`. `"Micro-Finance Banks"`, `"Mortgage
    Carriers, Brokers and Services"`, and `"Other Financial
    Institutions"` are deliberately absent (disclosed, not guessed —
    see alternative #3).
  - `growth_company`/`turnaround_company` never appear in either
    table — both are financial-lifecycle classifications, not
    industry classifications, and are unreachable from `sector_ngx`
    by design; they remain exclusively reachable via
    `configs/company_type_overrides.toml`'s own owner-judged
    mechanism, unchanged.
- New module `src/ngxrot/fre/sector_company_type_mapping.py`:
  `derive_company_type_for_ticker(con, ticker) -> str | None` — reads
  `securities.sector_ngx`; if it is `"FINANCIAL SERVICES"`, additionally
  reads `sector_ngx_provenance.sub_industry` for that ticker and looks
  it up in `[financial_services_sub_industry]`; otherwise looks up
  `[sector]` directly. Returns `None` (never a guess) if `sector_ngx`
  is `NULL`, or if the sub-industry/sector is not present in either
  table. Read-only, zero new SQL beyond simple lookups.
- `valuation_engine.classify_company_type()` is extended, not
  replaced: its signature changes from `(ticker)` to `(con, ticker)`
  (`con` is already in scope at its one real call site,
  `value_company()`) and it gains exactly one new precedence tier,
  inserted between the existing two: **(1) owner override (unchanged,
  still highest precedence) → (2) NEW: sector-derived mapping (only
  when unambiguously resolvable) → (3) `"general"` (unchanged
  fallback, now reached only when neither (1) nor (2) resolves).**
  This is the one modification to `valuation_engine.py` this phase
  makes — `classify_company_type()` is a free function, not one of
  the six `ValuationMethodAdapter` subclasses, so this does not modify
  "existing valuation adapters" in the sense the instruction means;
  no adapter's own `is_ready()`/`compute()` logic is touched.

## Why this activates nothing new despite changing real output

`classify_company_type()`'s return value only changes which methods
`is_ready()` is checked against — it never itself produces a valuation
number. `compute()` on every adapter still unconditionally raises
`NotImplementedError` regardless of method or company_type (verified,
not assumed, in this phase's own tests). Checked against real data
before implementing: **none of the 10 real FSI tickers (the only
tickers with actual financial-statement facts to compute anything
from) resolve to `"bank"` or `"insurance"` under the new mapping** —
MTNN/DANGCEM/OANDO/NESTLE/NASCON/CAP/BUAFOODS map to `"general"`
directly via their own sector; UCAP/AFRIPRUD fall into the
deliberately-unresolved `"Other Financial Institutions"` bucket and
also default to `"general"`; UBN has no known `sector_ngx` at all and
defaults to `"general"`. Every existing readiness/valuation-output
assertion in `test_valuation_engine.py` for these 10 tickers is
therefore unaffected — confirmed directly, not assumed, before
writing a single line of the new module.

## Backward compatibility

Every ticker with an existing owner override keeps its override
(unchanged, highest precedence). Every ticker with no override and an
unresolvable/unknown sector still defaults to `"general"` — identical
to today's behavior. Only tickers with no override AND a confidently
resolvable sector (12 of NGX's 13 top-level sectors, plus Banking/
Insurance within Financial Services) get a new, more accurate
classification than the blanket `"general"` default — the intended,
disclosed outcome of this phase, not a regression.

## Guardrails (mechanically verified, not just asserted)

- `derive_company_type_for_ticker()` never returns a value absent from
  either config table — confirmed by construction (a strict dict
  lookup, no fallback logic inside the function itself).
- Confirmed directly: none of the 10 real FSI tickers' `compute()`
  results change (still empty, still `NotImplementedError` on every
  adapter) despite some of their `company_type` classifications
  changing.
- Confirmed `growth_company`/`turnaround_company` are absent from
  every value in both new config tables.
- AST inspection confirms no `INSERT`/`UPDATE`/`DELETE` SQL statement
  anywhere in the new module.
- Full regression, `check_db_safety.py`, `test_reasoning_pipeline.py`,
  and Phase 5's harness all re-run after the change.

## Expected outcome

A new, additive config file and module; one precisely-scoped,
disclosed extension to `classify_company_type()`'s own precedence
chain (no adapter touched, no valuation output activated); zero change
to any of the 10 real FSI tickers' actual readiness/valuation
behavior. This closes the sector-to-valuation architectural
disconnect Phase 23 opened, using NGX's own official classification
as the sole input, never inference.
