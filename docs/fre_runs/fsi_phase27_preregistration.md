# FSI Phase 27 — Pre-registration

*Industry Exposure Integration. Per the owner's explicit instruction to
proceed directly after Phase 26, using the same continuous-execution
workflow.*

## Why this is the next architectural gap

`src/ngxrot/company_intelligence.py`'s `CompanyProfile.unavailable`
has listed `"Industry Exposure"` as blocked since the module's own
v0-scaffolding design (2026-07-22) — originally correctly so, since
`securities.sector_ngx` was 0/320 populated. Phase 23 populated it for
136/320 real securities; Phase 26 wired it into the Valuation Engine's
own company-type taxonomy. `company_intelligence.py`'s own `build_
profile()` still has zero logic consuming `sector_ngx` — the same
kind of disconnect Phase 26 closed for the Valuation Engine, now
recurring in the Company Intelligence Engine. Closing it here
completes the pattern: every subsystem this platform has that could
plausibly consume NGX's own sector classification now does.

## Alternatives considered and rejected

1. **A richer "Industry Exposure" representation** (peer set, sector
   concentration percentile, sector-relative sizing). Rejected — the
   only real data behind this field is a single top-level sector
   label per ticker (`securities.sector_ngx`); anything richer would
   be inference/computation this phase has no evidence to support.
   The module's own charter ("populated ONLY from evidence that
   actually exists today... never a fabricated value") sets the
   ceiling: state the sector label, nothing more.
2. **Also surfacing `sub_industry`** (from `sector_ngx_provenance`,
   Phase 23's finer-grained field) inside `CompanyProfile`. Rejected
   for this phase — `sub_industry` is provenance/detail data Phase 23
   already tracks at the database level; duplicating it into every
   in-memory `CompanyProfile` is unnecessary scope creep for a field
   the platform's own vision names simply as "Industry Exposure," and
   every other `CompanyProfile` field already follows the pattern of
   holding a plain value with provenance tracked once in the database,
   not re-embedded per object.
3. **Extending `sector_coverage.py` (Phase 24) instead**, to report
   Company-Intelligence-specific coverage. Rejected — Phase 24's own
   scope (research/watchlist coverage by sector) is a different
   question from "what does this ONE company's own profile know about
   its sector," and `sector_coverage.py` is a Tier-1 Part-9 module,
   architecturally unrelated to the Company Intelligence Engine.
4. **Leaving `company_intelligence.py` untouched and only updating its
   `UNAVAILABLE_FIELDS` disclosure text** (as Phase 23 did, disclosure-
   only). Rejected as insufficient for THIS phase specifically — the
   owner's own instruction names this as its own phase ("Industry
   Exposure Integration"), and Phase 23's disclosure-only correction
   already exists; this phase's job is the actual wiring Phase 23
   explicitly deferred.

## Design

- `CompanyProfile` (dataclass) gains one new field:
  `industry_exposure: str | None = None` — the ticker's own
  `securities.sector_ngx` value, verbatim, or `None` if unknown. No
  new sub-field, no computed percentage, no peer set.
- `build_profile()` queries `securities.sector_ngx` for the ticker
  (one plain `SELECT`, no new table, no write) and sets `profile.
  industry_exposure` when known. When set, `"Industry Exposure"` is
  removed from `profile.unavailable` for THIS profile instance only
  (each `CompanyProfile.unavailable` starts as its own fresh copy of
  the module-level `UNAVAILABLE_FIELDS` dict via `default_factory`, so
  mutating one instance's copy never affects another ticker's
  profile, or the module-level dict itself).
- `UNAVAILABLE_FIELDS["Industry Exposure"]`'s own reason text is
  corrected to describe the real, current, per-ticker-conditional
  state ("populated only for tickers with a known `sector_ngx`
  (136/320); unavailable, disclosed, for the rest") rather than the
  Phase-23-era "no logic wired yet" text, which this phase makes
  stale the moment it ships.

## Guardrails (mechanically verified, not just asserted)

- Real-data correctness: `industry_exposure` is set correctly for a
  ticker with a known sector (e.g. `NASCON` → `"CONSUMER GOODS"`) and
  stays `None` for one without (`UBN`), with `"Industry Exposure"`
  correctly present/absent from `unavailable` in each case
  respectively.
- Confirmed one profile's `unavailable` mutation never leaks into
  another profile built in the same batch/cache run (a real,
  mechanically-checked isolation test, not assumed from the
  `default_factory` pattern alone).
- No new SQL beyond a single plain `SELECT` on an already-indexed
  primary-key column; no write path anywhere.
- Full regression, `check_db_safety.py`, `test_reasoning_pipeline.py`,
  and Phase 5's harness re-run after the change (this module sits
  outside the FSI track's own harness scope, but shares the same
  production database, so `check_db_safety.py`'s and the harness's
  own database-integrity checks remain the relevant cross-cutting
  verification).

## Expected outcome

`CompanyProfile.industry_exposure` becomes real for 136/320 tickers,
sourced entirely from NGX's own official classification (Phase 23),
with zero inference and zero change to any other field this module
already populates. This is expected to be the last of the two
sector_ngx-consuming phases the owner named (Phase 26, Phase 27) — a
fresh full-platform review follows before proposing anything further.
