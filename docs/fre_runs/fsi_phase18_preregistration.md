# FSI Phase 18 — Watchlist Persistence (Pre-registration)

*Per the owner's standing continuous-execution authorization. Builds on
`fsi-phase17-baseline-2026-08-02`.*

## Architectural gap

Part 9's Tier-1 list has three items: Watchlist, Screening, Portfolio
memory. Screening (14/15) and Portfolio memory (17) are built. Watchlist
— a persisted, curated list of tickers a researcher is tracking, each
entry required to state its own `entry_criteria` ("what would need to be
true for this to become portfolio-relevant") IN ADVANCE — remains the
only undone Tier-1 item.

## Why highest-priority now

Closes Part 9 entirely. It is also the natural consumer of Screening's
own output: a researcher runs `screen_companies.py`, finds a real,
evidence-backed candidate, and now has a real, honest place to record
"I'm tracking this, and here is what would need to be true before it
matters" — without that place existing, Screening's own results have
nowhere durable to go.

## Alternatives considered and rejected

1. **A new Financial Intelligence health-flag type** (e.g. capital-
   allocation quality via dividend/FCF history). Real, but Watchlist
   closes a whole named architectural section (Part 9); a 4th flag
   extends an already-mature rule set incrementally.
2. **More coverage expansion (remaining 39 scoped tickers).** Legitimate
   future work, but Phase 13 already exercised this exact methodology at
   scale this session; repeating it now is "more of the same," lower
   architectural leverage than closing Part 9's last gap.
3. **A CLI wrapper for Watchlist, bundled into this same phase.**
   Rejected as bundling — per this program's single-dominant-risk-surface
   discipline (explicit in Phase 14's own pre-registration), this phase's
   own new risk surface (the platform's first genuinely persistent,
   write-capable FSI module, plus its first new table since Phase 3) is
   enough for one phase. A CLI is a natural, small follow-on, not a
   reason to delay this one.

## Why this fits the long-term architecture

Additive schema only (one new table, `watchlist_entries`, zero
modification to any existing table). Append-only by the same convention
already used throughout this platform (`removed_at`/`removal_reason`
columns instead of `DELETE`, mirroring `securities.delisting_date` and
`restates_fact_id` elsewhere in the same schema file) — a watchlist
entry's full history is always reconstructible, never overwritten.
`entry_criteria` is `NOT NULL` by design: this is literally this
platform's own pre-registration discipline (declare success/failure
criteria before the fact) applied to watchlist membership, per Part 9's
own explicit framing.

## Design decisions (conservative, no pause)

- **`source_thesis_as_of_date` is a reproducible POINTER (ticker + date),
  never a stored blob or duplicate of `CompanyThesis360`'s own data** —
  consistent with how every other PIT object on this platform is
  referenced (by ticker + date, re-computed on demand), not copied.
  `add_entry()` validates this pointer is REAL by calling `company_
  thesis_360.as_of(ticker, source_thesis_as_of_date)` and requiring it
  not to raise — it does NOT require non-empty evidence (an entry can
  legitimately watch a company before much evidence exists).
- **No `DELETE` anywhere.** `remove_entry()` sets `removed_at`/
  `removal_reason`; a row already removed cannot be removed again or
  "un-removed" — once closed, permanently closed, matching this
  platform's append-only discipline everywhere else.
- **`list_active()` is the one cross-ticker function this module adds** —
  same guardrails as Screening: alphabetical-ticker order, no score/
  rank/weight field, no numeric-threshold parameter. It answers "what is
  currently on the watchlist," never "which watchlist entry is most
  important."
- **No wiring into `company_research_dossier.py`** in this phase, for the
  same single-risk-surface reason as Phase 17's own deferred dossier
  wiring.

## Success criteria

`add_entry()`/`remove_entry()`/`list_active()`/`get_history_for_ticker()`
all function correctly against real tickers; append-only guarantee
mechanically verified (no `DELETE` statement anywhere in the module, via
AST inspection); `entry_criteria`/`rationale` are enforced `NOT NULL` at
the schema level; `list_active()` guardrails (ordering, no score field,
no numeric threshold) mechanically verified, same style as Screening's
own test suite. Schema migration applied to production via the
established `db.init_db()` mechanism, with an automatic pre-write backup.
Full regression + Phase 5 harness both still pass.

## Implementation boundaries

**In scope**: one new table (`watchlist_entries`); `src/ngxrot/fre/
watchlist.py`; its own dedicated test file. **Out of scope**: any CLI
wrapper (deferred); any wiring into `company_research_dossier.py`
(deferred); any modification to any existing table or frozen module.

---
*Implementation proceeds immediately.*
