# FSI Phase 27 — Implementation Log

*Per `docs/fre_runs/fsi_phase27_preregistration.md` and the owner's
explicit instruction to proceed directly after Phase 26. Append-only.*

## Entry 0 — Confirmed no existing test file or consumer would break

Checked `scripts/company_profile.py` (the one existing consumer of
`CompanyProfile`) before changing the dataclass: it dumps the whole
object via `dataclasses.asdict()` to JSON, with no field-specific
logic — a new field is fully additive and safe there, confirmed by
inspection, not assumed. No dedicated test file existed for
`company_intelligence.py` before this phase.

## Entry 1 — `CompanyProfile.industry_exposure` and `build_profile()`

One new field, `industry_exposure: str | None = None` — the ticker's
own `securities.sector_ngx` value, verbatim, or `None`. `build_
profile()`'s existing `SELECT name FROM securities` was widened to
also select `sector_ngx` (no new query, no new table) — when non-NULL,
`profile.industry_exposure` is set and `"Industry Exposure"` is
removed from `profile.unavailable` for that profile instance only.

## Entry 2 — Isolation verified directly, not assumed from the dataclass pattern alone

`CompanyProfile.unavailable`'s `default_factory=lambda: dict(
UNAVAILABLE_FIELDS)` gives every profile instance its own fresh dict
copy — but rather than trust that pattern by inspection alone, built
two profiles (`NASCON`, known sector; `UBN`, unknown) sharing the SAME
cache dict in one batch run and confirmed directly: `NASCON`'s
`"Industry Exposure"` removal does not appear in `UBN`'s own
`unavailable`, and the module-level `UNAVAILABLE_FIELDS` dict itself
remains untouched after both builds.

## Entry 3 — `UNAVAILABLE_FIELDS["Industry Exposure"]`'s reason text corrected

The Phase-23-era text ("...build_profile() has no logic wired to
consume it yet") would have gone stale the instant this phase shipped.
Corrected to describe the real, current, per-ticker-conditional state:
populated for tickers with a known `sector_ngx` (136/320), disclosed
and unavailable for the rest — accurate both before this phase's
change (implicitly, since the field didn't exist) and after (exactly
describes which tickers get it and why the others don't).

## Entry 4 — Real-data verification

Confirmed directly: `NASCON` → `industry_exposure="CONSUMER GOODS"`,
`"Industry Exposure"` absent from `unavailable`; `UBN` → `industry_
exposure=None`, `"Industry Exposure"` present in `unavailable`; an
unknown ticker (`NOTAREALTICKER`, no `securities` row) does not crash
and leaves `industry_exposure=None`.

## Entry 5 — Full regression and validation (complete)

`scripts/test_company_intelligence.py` (new, 10/10 — placed at the
top-level `scripts/` directory, matching `company_intelligence.py`'s
own module location outside the `ngxrot.fre` package, the same
convention `scripts/test_reasoning_pipeline.py` already establishes).
Full regression: 37 test files across both `scripts/fre/` and
top-level `scripts/`, all green — no existing test file needed any
change. `check_db_safety.py` PASS. Phase 5 harness: all 4 components
PASS — 31 tables, unchanged before/after (this phase adds no table,
touches no FSI-track table at all).

**No modification to any table, and no modification to any other
field `build_profile()` already populates** — confirmed directly
(NASCON's `name` field, unrelated to this change, still populated
correctly). No schema change.

**FSI Phase 27 is now complete, validated, and documented.** Both
sector_ngx-consuming phases the owner named (26: Valuation Engine
company-type mapping; 27: Company Intelligence Industry Exposure) are
now built. Per the owner's own instruction, a fresh full-platform
review follows before proposing anything further.
