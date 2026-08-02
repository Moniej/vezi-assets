# FSI Phase 27 — Final Report

*Industry Exposure Integration. Full narrative in
`docs/fre_runs/fsi_phase27_implementation_log.md`.*

## Executive summary

FSI Phase 27 wired NGX's own official sector classification
(`securities.sector_ngx`, Phase 23) into `src/ngxrot/company_
intelligence.py`'s `CompanyProfile.industry_exposure` — the second and
last of the two sector_ngx-consuming phases the owner named after
Phase 25's stopping point. `build_profile()` now populates this field,
verbatim, for the 136/320 tickers with a known sector, and correctly
leaves it `None` (with `"Industry Exposure"` remaining in `unavailable`,
disclosed) for the rest.

## Files created/modified

- `src/ngxrot/company_intelligence.py`: `CompanyProfile` gains
  `industry_exposure: str | None = None`; `build_profile()` populates
  it from a widened (not new) `SELECT`; `UNAVAILABLE_FIELDS["Industry
  Exposure"]`'s reason text corrected to describe the real,
  per-ticker-conditional state.
- `scripts/test_company_intelligence.py` (new, 10 assertions) — the
  first dedicated test file for this module.
- This report, the implementation log, and the pre-registration.

**No schema change, no new table, no modification to any other field
this module already populates.**

## Results

- `NASCON` → `industry_exposure="CONSUMER GOODS"`, correctly removed
  from `unavailable`; `UBN` → stays `None`, correctly remains in
  `unavailable`, disclosed rather than guessed.
- Confirmed directly (not assumed from the dataclass pattern alone):
  one profile's `unavailable` mutation does not leak into another
  profile built in the same shared-cache batch run, and the
  module-level `UNAVAILABLE_FIELDS` dict itself is never mutated.
- An unknown ticker does not crash; `industry_exposure` stays `None`.
- Full regression (37 test files across `scripts/fre/` and top-level
  `scripts/`), `check_db_safety.py`, and Phase 5's harness (4
  components, 31 tables) all pass — zero unintended data mutations,
  confirmed via row-count checks throughout.

## Status

Both of the owner's named sector_ngx-consuming phases are now
complete: Phase 26 (Valuation Engine company-type mapping) and Phase
27 (Company Intelligence Industry Exposure). Every subsystem on this
platform that could plausibly consume NGX's own official sector
classification now does — deterministically, disclosed, with zero
inference anywhere.

## Recommendations for the next phase

Per the owner's own instruction: perform a fresh full-platform
architectural review before proposing any further phase, to confirm
whether a genuine stopping point has been reached or a real,
guardrail-compliant, non-owner-blocked capability improvement remains.

---

**FSI Phase 27 is complete: fully implemented, validated, and
documented.**
