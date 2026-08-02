# FSI Phase 26 — Implementation Log

*Per `docs/fre_runs/fsi_phase26_preregistration.md` and the owner's
explicit instruction. Append-only.*

## Entry 0 — Verified the real sub-industry breakdown of FINANCIAL SERVICES before designing

Queried `sector_ngx_provenance` directly: `FINANCIAL SERVICES` splits
into Banking (8 tickers), Insurance Carriers/Brokers/Services (19),
Micro-Finance Banks (1: NPFMCRFBK), Mortgage Carriers/Brokers/Services
(2: ABBEYBDS/INFINITY), and "Other Financial Institutions" (9:
AFRIPRUD, DEAPCAP, FCMB, NGXGROUP, ROYALEX, STANBIC, UCAP,
ACCESSCORP, FIRSTHOLDCO). Confirmed "Other Financial Institutions" is
a genuine heterogeneous grab-bag by NGX's own design (spans a
capital-markets firm, a capital-management firm, the exchange
operator itself, an insurance/general-commerce name, and several de
facto bank holding companies) — this determined the decision to leave
it, Micro-Finance Banks, and Mortgage Carriers unresolved rather than
force a single company_type onto any of them.

## Entry 1 — `configs/sector_company_type_mapping.toml` and `sector_company_type_mapping.py`

12 of NGX's 13 top-level sectors map to a single company_type
(11 to `"general"`, `CONGLOMERATES` to `"holding_company"`);
`FINANCIAL SERVICES` is resolved via sub-industry only (`Banking` →
`"bank"`, `"Insurance Carriers, Brokers and Services"` → `"insurance"`,
the other three sub-industries deliberately absent). `derive_company_
type_for_ticker(con, ticker)` is a pure, read-only lookup — returns
`None`, never a guess, whenever `sector_ngx` is `NULL` or the
sector/sub-industry is absent from the config.

## Entry 2 — `classify_company_type()` extended, not replaced

Signature changed from `(ticker)` to `(con, ticker)` — `con` was
already in scope at the function's one real call site
(`value_company()`). New precedence: (1) owner override, unchanged,
highest — (2) NEW: sector-derived mapping — (3) `"general"`, unchanged
fallback. `classify_company_type()` is a free function, not one of
the six `ValuationMethodAdapter` subclasses, so this does not modify
"existing valuation adapters" in the sense the instruction means; no
adapter's own `is_ready()`/`compute()` logic was touched, confirmed by
`git diff` scoped to exactly the two functions changed plus the
docstring update.

## Entry 3 — Real-data backward-compatibility check, before writing a single test

Computed `derive_company_type_for_ticker()` for all 10 real FSI
tickers before writing any assertion: none resolve to `"bank"` or
`"insurance"` (MTNN/DANGCEM/OANDO/NESTLE/NASCON/CAP/BUAFOODS map to
`"general"` directly via their own sector; UCAP/AFRIPRUD fall into the
deliberately-unresolved "Other Financial Institutions" bucket and also
default to `"general"`; UBN has no known `sector_ngx` at all and
defaults to `"general"`). This confirmed, before implementation, that
every existing `test_valuation_engine.py` assertion for these 10
tickers would hold unchanged — verified directly afterward: all 42
assertions in that file pass, including the 9 pre-existing readiness/
compute assertions this phase touches nothing in.

## Entry 4 — Readiness-gate change verified honest, not a crash

`CONGLOMERATES`-classified tickers (e.g. TRANSCORP) now get
`eligible_methods=['sum_of_the_parts']` instead of `['dcf',
'ev_ebitda', 'pe']` — `sum_of_the_parts` has no adapter implementation
at all in `_ALL_ADAPTERS`. Confirmed directly: `value_company()`'s
existing "adapter is None" branch (already written, pre-dating this
phase) correctly reports a clear, disclosed "no adapter implementation
yet" reason — never a crash, never a fabricated result, `results`
stays empty. This is a real, disclosed output-shape change for these
5 tickers (none of which are FSI-covered, so no readiness/valuation
test previously asserted anything about them) — confirmed to remain
honest, not silently broken.

## Entry 5 — Updated the one existing test assertion this phase changes real behavior for

`test_valuation_engine.py`'s `ve.classify_company_type("GTCO")`
call — updated to `ve.classify_company_type(con, "GTCO")`, with the
expected value changed from `"general"` to `"bank"` (GTCO's real
sector_ngx/sub_industry resolves unambiguously) — plus two new
assertions confirming UBN (unknown sector) and AFRIPRUD/UCAP
(deliberately-unresolved sub-industry) all still correctly fall back
to `"general"`, identical to every unresolvable ticker's pre-Phase-26
behavior.

## Entry 6 — Full regression and validation (complete)

`scripts/fre/test_sector_company_type_mapping.py` (new, 18/18). Full
regression: 36 test files (was 35), all green, including
`test_valuation_engine.py`'s updated assertions (42/42, up from 40 —
2 new checks added, 1 updated). `check_db_safety.py` PASS. `test_
reasoning_pipeline.py` ALL CHECKS PASSED. Phase 5 harness: all 4
components PASS — 31 tables, unchanged before/after (this phase adds
no table).

**No modification to any of the six `ValuationMethodAdapter`
subclasses, and no valuation output activated anywhere** —
`compute()` still unconditionally raises `NotImplementedError` on
every adapter, confirmed directly, unchanged. No schema change. The
golden snapshot is unaffected.

**FSI Phase 26 is now complete, validated, and documented.** This
closes the sector-to-valuation architectural disconnect Phase 23
opened, using NGX's own official classification as the sole input,
with zero inference and zero visible change to any of the 10 real
FSI tickers' actual valuation/readiness behavior.
