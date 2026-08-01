# FSI Phase 5 — Regression & Consistency Validation Harness (Pre-registration)

*Design only. No implementation, no schema change, no new fact type, no
new document, no valuation output, no alpha claim, no portfolio ranking,
no scoring, no buy/sell output, no unsupported conclusion. Per
instruction, written and frozen BEFORE any execution begins. Builds on
`fsi-phase4-baseline-2026-08-01` (177 conclusions, PIT-safe read access)
and modifies nothing in Phases 1-4 — all four remain frozen, touched
only for future bug fixes per standing instruction.*

## A note on scope selection, stated up front (as in Phase 4's own precedent)

As with Phase 4, the owner's approval message asks for the next phase's
complete research design without naming its topic — bounded only by the
standing exclusions (no alpha, ranking, buy/sell output, hidden scoring,
unsupported conclusions) and standards to preserve (provenance, PIT
correctness, uncertainty, reproducibility, auditability). The owner's
closing line — "any FUTURE investment reasoning layer must preserve…" —
is read here as a standing principle for whatever eventually follows,
not as an instruction to build that layer now. Given the exclusions have
now been restated in every one of the last three approvals, this
document treats them as durable, not phase-specific, and proposes a
scope that keeps the entire program furthest from that boundary: a
**validation harness**, not a new reasoning capability. If this is not
the intended direction, redirection is expected, per the same standing
practice.

## Objective

Build a mechanical **regression and consistency validation harness**
over the frozen Phase 1-4 pipeline: a permanent safety net proving that
(a) rerunning the pipeline against unchanged data reproduces byte-
identical output, (b) a deliberately-injected defect is actually
detected, not silently passed, and (c) Phase 3 and Phase 4 remain
mutually consistent (Phase 4's PIT-filtered view, taken at each ticker's
own latest real filing date, always exactly reproduces Phase 3's full,
unfiltered conclusion set for that ticker). This is infrastructure
ABOUT the existing frozen phases, not a new fact, ratio, trend, flag, or
narrative — it adds no analytical capability of its own.

## Research question

Can a harness be built that (1) never produces a false positive against
the real, unmodified pipeline, and (2) reliably detects a real class of
regression when one is deliberately introduced on a disposable scratch
copy — the same two-sided bar FRE-10's own original design named as the
minimum for a validation harness to be trustworthy ("a harness that
passes everything regardless of quality is the single worst failure
mode for an evaluation system")?

## Hypothesis

A harness built from three mechanical layers — golden-snapshot
reproducibility, cross-phase consistency, and injected-defect detection
— can meet this bar WITHOUT requiring a human-authored gold set (the
dependency that blocked the original roadmap's FRE-10 from starting
immediately): every check this phase proposes compares the pipeline
against ITSELF (a frozen snapshot of its own real, already-validated
output, or a deliberately-corrupted copy of its own code), never against
an external ground truth that doesn't yet exist. Genuinely open: it is
not yet known whether mechanical self-comparison alone is a sufficient
substitute for a human-authored gold set, or whether some defect classes
would only be caught by one and not the other — this phase's own
results will answer that honestly, not assume it.

## Scope — three required components

### 1. Golden-snapshot reproducibility

Freeze a snapshot of every real, current Phase 1-4 output relevant to
regression detection: `extracted_facts` row count and per-fact-type
breakdown (106), `financial_reasoning_conclusions` row count and
per-type breakdown (177: 75 ratio + 87 trend + 15 flag), and the exact
value/confidence_tier/status of every one of the 177 conclusions.
Rerunning any Phase 1-4 script that is idempotent (all of them are, by
existing design — every extraction/derivation script already checks
before/after counts) against the CURRENT, unmodified database must
reproduce this snapshot exactly. This formalizes, as a permanent,
automated check, a property every prior phase already informally
verified once at implementation time but never re-tests afterward.

### 2. Cross-phase consistency

A mechanical check that `pit_financial_memory.as_of(ticker, <ticker's
own latest real filing_date>)` returns EXACTLY the same conclusion_ids,
in full, as an unfiltered query of `financial_reasoning_conclusions`
for that ticker — for all 5 tickers. This was informally true by
construction in Phase 4's own tests (NASCON's `as_of()` at its last
filing date returned all 33 of its real conclusions), but has not been
verified for the other 4 tickers, nor formalized as a permanent,
re-runnable guard against a future change silently breaking it.

### 3. Injected-defect detection (the FRE-10-style sanity check)

On a disposable scratch copy only, deliberately introduce a small,
realistic defect drawn from this program's own real incident history —
not a hypothetical — and confirm the harness's own checks (1) and (2)
above, or a dedicated third check, actually detect it. Candidate,
concrete, real-precedent defects (illustrative, not exhaustive — the
exact injected set is an execution-time decision):

- Re-introduce the ORIGINAL (pre-Entry-5) overlap-only restatement rule
  on a scratch copy and confirm a regression test built from the real
  NASCON H1-2024-vs-FY2024 case (already exists,
  `test_restatement_detection.py`) fails loudly, rather than silently
  passing — proving the harness would have caught the real defect this
  program actually shipped once, had it existed at the time.
- Corrupt one `confidence_tier` value on a scratch copy (e.g. force a
  `NULL`-tier legacy fact to `direct_reported`) and confirm the golden-
  snapshot check (component 1) detects the deviation.
- Break `periods_overlap()`'s boundary condition (e.g. make touching-
  but-non-overlapping periods register as overlapping) and confirm a
  trend-count deviation is detected against the golden snapshot.

## Alternatives considered

1. **A human-authored "strategy-narrative gold set"**, per the original
   FRE-10 roadmap design. Rejected for THIS phase, not permanently — it
   requires owner-authored analyst content this session cannot fabricate
   and was already named as FRE-10's own blocking dependency; nothing
   here forecloses adding it later as a genuine FRE-10 execution once
   that dependency is resolved.
2. **Unified Company Memory** (merging FRE-3's existing dividend/event
   `CompanyMemory` with Phase 4's `CompanyFinancialReasoningMemory` into
   one combined `as_of()` view). Rejected for this phase specifically
   because it is a genuine, new INTEGRATION capability (a new function,
   new combined return shape) rather than pure validation of what
   already exists — a reasonable candidate for a later phase, but a
   bigger step than the owner's repeated emphasis on reproducibility/
   auditability suggests is wanted right now.
3. **The optional narrative ("why") reasoning layer** named but
   deliberately not built in Phase 3's Area 4. Rejected for this phase —
   it is the single highest-risk candidate (requires an LLM call, sits
   closest to "unsupported conclusion" risk, needs its own vendor/cost
   decision) and is explicitly the kind of "future investment reasoning
   layer" the owner's closing standard-setting line reads as preparing
   for, not requesting now.
4. **Extending Phase 3's rule set or Phase 1/2's fact-type coverage.**
   Rejected — both would modify or extend already-frozen phases, which
   the owner has now said three times running should not happen absent
   a bug fix.
5. **Do nothing / treat the pipeline as complete.** Rejected — the
   pipeline has never been tested for regression-safety as new data or
   code changes arrive in the future; a harness is cheap, low-risk, and
   directly serves the two standards (reproducibility, auditability)
   the owner has repeatedly named.

## Success / partial / failure criteria

| Component | Success | Partial | Failure |
|---|---|---|---|
| Golden-snapshot reproducibility | 0 deviations on a real rerun against unmodified data | n/a — this is binary | Any deviation on an unmodified rerun (a genuine, serious finding — would mean the pipeline is not actually deterministic) |
| Cross-phase consistency | All 5 tickers' `as_of()` at their own latest filing date exactly matches their unfiltered conclusion set | 4/5 tickers match, 1 has a disclosed, explained discrepancy | Any undisclosed/unexplained mismatch |
| Injected-defect detection | All 3 candidate defects (Area 3) are caught by the harness on the scratch copy | 2/3 caught, the miss disclosed with root cause | 0-1/3 caught — the harness would need redesign before being trusted |

## Dependencies

The frozen `fsi-phase4-baseline-2026-08-01` state in full (Phases 1-4).
`test_restatement_detection.py`'s existing real NASCON/CAP anchors
(reused for defect-injection component 3, not duplicated).
`db.new_scratch_db_path()` (existing, proven safe-copy convention) for
every injected-defect test — no defect is ever introduced on production.

## Risks

- **Self-comparison harnesses can pass "by construction" without proving
  much** if every check is trivially true given the code being tested —
  mitigated directly by component 3 (injected-defect detection), which
  exists specifically to prove the harness isn't a rubber stamp, per
  FRE-10's own named risk.
- **Only 3 candidate defects are proposed, all drawn from this
  program's own real incident history** — a real defect of a
  genuinely different shape (not resembling anything in Phases 1-4's
  own past) might not be caught; disclosed as a real limitation, not
  overstated as comprehensive coverage.
- **Scope-selection risk, restated**: this document's own topic choice
  may not match the owner's actual intent for "the next phase" — flagged
  explicitly, exactly as Phase 4's own pre-registration flagged the same
  risk before being approved.

## Stop conditions

If golden-snapshot reproducibility (component 1) fails on a real,
unmodified rerun, stop immediately and report it as a genuine
architectural finding — a supposedly-idempotent pipeline turning out not
to be deterministic is a serious defect in already-frozen infrastructure,
not something to patch quietly inside this phase. If fewer than 2 of the
3 injected defects (component 3) are detected, do not report the harness
as complete or trustworthy — report the miss honestly and stop for
redesign review, per the same discipline used when the Phase 2
restatement-detection defect was found.

## Review checkpoint

Per the same two-gate discipline as every prior phase: this
pre-registration — including, explicitly, whether this is the scope the
owner intended — must be reviewed and approved before any implementation
begins.

---

*Awaiting approval of this pre-registration before any implementation
begins.*
