# Capital Allocation Review — 2026-08-13

Scope: CAPITAL ALLOCATION MODE, P0–P5. P0–P3 are sequentially gated behind
one external blocker (live FRE confirmation). That blocker cannot be
re-attempted today without violating the standing "do not repeatedly poll"
instruction — three same-day attempts already failed identically at the
same document (see `docs/alpha/AUTONOMOUS_FRE_PROGRESS_2026-08-13.md`,
Entries 3–4). P4 (Investment OS value test) is not gated on FRE and was run
today. P5 (this document) synthesizes.

---

## P0 — FRE live validation: STATUS UNCHANGED, NOT RE-ATTEMPTED

FACT: 0/4 documents processed live with the v3 prompt fix, three
consecutive same-day attempts, stable pattern (small cached doc succeeds,
ELLAHLAKES — the only document that tests the actual defect — hits `429`
immediately every time).

DECISION: Do not attempt a fourth try this session. Next attempt should
wait for a materially later point (plausibly a new quota day). This is
unchanged from the standing HOLD.

## P1–P3 — Coverage expansion / fundamental alpha / paper capital

Not started. Each is explicitly gated on P0 completing first (coverage
expansion needs a confirmed-reliable extraction pipeline; a fundamental
hypothesis needs coverage; paper capital needs a validated hypothesis).
Attempting any of these now would mean testing on data whose extraction
reliability is not yet live-confirmed — exactly what the gate exists to
prevent.

## P4 — Investment OS value test: RUN TODAY (`scripts/p4_os_value_test.py`)

Three representative research tasks, each run baseline (manual/ad-hoc SQL
or grep) vs. OS-assisted, against real production data:

| Task | Baseline | OS-assisted | Real finding |
|---|---|---|---|
| DANGCEM PIT-safe document context | 2 hand-written SQL queries, 43 raw fact rows, PIT filter manually added (easy to omit), no lineage without a 3rd query | 1 call, structural `as_of`, built-in provenance (100 entries), **but 27.97s wall-clock** vs 0.02s for the baseline | **Not a speed win at this granularity.** `document_context` assembles a full reasoning context (coverage score, confidence ceiling, conflict detection, evidence ranking) the baseline never computed at all — the two aren't doing equivalent work, so raw latency isn't a fair proxy for value here. The real cost is real: 28s per call is not free at scale. |
| Prior-art search: size-premium hypothesis | Naive substring match on `description`, 6 unranked hits, no factor-family classification, false-positive-prone | Deterministic ranked search, 7 matches, correctly topped by the real `H-011`, both near-instant (<5ms) | **Genuine quality win, not a speed win** (baseline was already fast). Ranking + family classification is the value, not latency. |
| UACN data-quality check | Baseline only checks 1 of 10 known failure classes (duplicates), and only if the researcher remembers to write that specific query | All 10 classes in one call, near-instant, each alert carries fact_id + check_name lineage | **Strongest, cleanest case for OS value.** This is a completeness gap, not a speed gap — a manual researcher realistically does not write and run 10 bespoke queries per ticker; the OS makes exhaustive checking the default instead of something that depends on memory/diligence. Real result: 0 alerts either way (UACN is clean) — not forced positive. |

**Net P4 finding**: the Investment OS's value is **not** primarily speed —
one call (`document_context`) is measurably *slower* than the equivalent
narrow SQL. Its value is **completeness and reproducibility that a human
realistically will not sustain by hand**: PIT correctness that can't be
silently skipped, exhaustive 10-class data-quality coverage instead of
whichever check the researcher remembers, and ranked/classified prior-art
search instead of substring luck. This is real evidence, not a forced
conclusion — the honest caveat (latency cost on the heaviest call type) is
reported alongside the wins, per instruction not to force a positive
result.

---

## P5 — Where should the next 100 hours of founder time go

**Decision rule from the framework, applied literally, not assumed:**

- FRE has **not** "failed economically." Its deterministic layer is fully
  validated (Gate 2: 262/265, zero false positives/negatives across 66
  adversarial/enforcement tests). The one open question — does the model
  itself apply the fix live — is blocked by an **external** quota
  constraint, not an internal defect. This does not match the "FRE fails
  economically → stop expanding" branch.
- Fundamentals have **not** been tested at all yet (blocked by P0, not a
  negative result). This does not match "FRE works but fundamentals
  produce no alpha" — there is no alpha *result* yet, positive or
  negative.
- The Investment OS **does** demonstrably improve research completeness
  and reproducibility (P4, above), independent of alpha outcome. Per the
  framework's own rule, this means: **preserve the Investment OS as a
  research asset regardless of how FRE/alpha resolve.**

**Conclusion: the honest state today is "wait," not "pivot."** The single
gating fact (live FRE confirmation) is time-blocked, not effort-blocked —
throwing more founder hours at it today would mean polling, which is
explicitly disallowed and has already been shown three times not to work.
No hard-stop condition was triggered. No infrastructure should be added.

**Recommended allocation of the next 100 hours, conditional on the
external blocker:**
1. **~0 hours now** on FRE — the single remaining action is one measured
   live attempt once Gemini quota genuinely resets (plausibly a new day),
   not effort that scales with hours spent.
2. **0 hours** on new Investment OS infrastructure — P4 confirms it's
   already valuable at its current scope; today's own finding is a reason
   to *use* it, not expand it.
3. The **100 hours are not usefully NGX-allocable today** under this
   framework's own rule ("do not assume NGX deserves the allocation
   merely because substantial work has already been invested") — this
   session has no comparison data on other ventures/opportunities to
   weigh against, so this report does not manufacture a false trade-off.
   That comparison, if wanted, is a separate, explicit ask.
4. When the quota resets: run the single ELLAHLAKES live attempt → if it
   passes, resume P1 (coverage) → P2 (one pre-registered fundamental
   hypothesis, not five) → P3 (paper capital) in that order, each gated
   on the previous passing, per the framework's own decision rule.

**What was deliberately not done**: no new hypothesis was pre-registered,
no Alpha Engine change was made, no paper capital was allocated, no
broker/compliance/fundraising work was started, and FRE was not polled a
fourth time. All correctly out of scope given the current evidence.
