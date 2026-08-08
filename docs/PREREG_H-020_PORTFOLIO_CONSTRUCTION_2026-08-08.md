# Pre-Registration — H-020: Portfolio Construction for H-019 (News-Event GMC/CIR)

*Drafted 2026-08-08, BEFORE any H-019/H-020 backtest, and before any return
or price-performance data was examined by the author of this document.
Governs how the already-frozen, already-audited H-019 event dataset
(`data/hypotheses/h019/h019_event_dataset_2026-08-08.csv`, 6 rows, audited
`docs/H019_INDEPENDENT_AUDIT_2026-08-08...` — see the audit transcript in
this conversation's record) is translated into a tradable portfolio. This
document does not modify, re-derive, or reopen the H-019 dataset in any way
— it consumes it exactly as constructed and frozen. Changes after first
backtest results = new hypothesis ID, per this platform's standing
convention (see every prior `PREREG_H-*.md`).*

**What was consulted while writing this document**: `docs/PREREG_H-019.md`,
`docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md` (§14A-§14J),
`configs/h011_size.toml`, `docs/PREREG_H-011.md`, `schema/schema.sql`'s
`cost_schedule` table definition, and `src/ngxrot/execution_realism.py`'s
existing participation-capped fill simulator. **What was not consulted**:
any `equity_prices`/`index_levels` return series, any backtest output, any
prior experiment's realized metrics for H-019 specifically. No performance
number of any kind informed any choice below.

---

## 1. Eligible universe

**Signal-eligible universe**: exactly the 20 H-011 holdings,
`data/reference/stage6_h011_universe_2026-08-08.json` (formation date
2026-06-30) — identical to H-019's own universe, not the broader ~96-100
name IRU. This is not a new restriction invented for backtest convenience:
it is the actual universe the underlying news corpus (Stages 11-13) was
built against — extending to the full IRU would require new event
collection, which is explicitly out of scope for this stage.

**Position-eligible on a given date**: a strict subset of the above — only
tickers carrying an active (§4), non-neutral (§3), PIT-safe H-019 signal as
of that date. A ticker can be in the signal-eligible universe with zero
position-eligible dates across the whole sample (this is expected and
correct, not an error, given only 6 total events exist).

## 2. Signal activation

Exactly the frozen Stage 14 §14E rule, unmodified: a signal becomes
activatable at `eligible_from` — the first NGX trading session (`index_levels.trade_date`,
`confidence >= 0.5`) strictly after `knowledge_timestamp`. No same-session
or intraday assumption is made anywhere in this document. `event_date`
(effective date) is never used as an activation trigger — only
`knowledge_timestamp_eligible_from`, exactly as `docs/PREREG_H-019.md`'s
no-lookahead rule requires (restated here because §14F/§14I already flagged
this as an easy mistake to make: 3 of the 6 GMC-family rows in the H-019
dataset have `effective_date` earlier than `announced_date`).

## 3. Signal representation

Reused exactly from Stage 14 §14C — no new directional rule is introduced,
and `investment_implications.direction` (Gemini-derived) is not used
anywhere in this document, consistent with H-019's own construction.

`direction ∈ {positive, neutral, negative}` maps to a raw score
`{+1, 0, -1}`. **A `neutral`-direction event does not generate a tradable
position.** This is a direct, mechanical consequence of the signal
definition, not a data-driven convenience: a classification of `neutral`
under the frozen §14C rule means the objective rule found no
determinable sign — there is nothing directional to act on, by
construction. This is disclosed explicitly here, before any return
inspection, because it is known in advance to shrink the current
in-sample tradable set to exactly the 2 `positive` events already in the
frozen dataset (DEAPCAP, LEGENDINT) — **this consequence is accepted, not
avoided, and is not a reason to loosen §14C's rule**, which remains frozen
and out of scope for this document per the explicit constraint against
loosening GMC/CIR definitions.

## 4. Overlapping events

If a second qualifying H-019 event arrives for a ticker that already has an
active position (§8), the new event **replaces** the existing signal in
full: the holding-period clock resets to the new event's own
`eligible_from`, and the position's direction is updated to the new event's
`direction` (including to `neutral`, which closes the position — see §3).
This rule is chosen for determinism and to avoid inventing an ad hoc
netting/scoring convention across two qualitatively different disclosures
(e.g. a resignation followed by an unrelated appointment): the platform
treats the newest confirmed information as the current state, exactly the
same "latest `as_of_date` wins" principle already used by `events_asof()`
for PIT reads elsewhere in this codebase — reused here, not invented fresh.
**With only 6 events in the current dataset and no ticker holding two
events within a plausible window (confirmed in the H-019 audit), this rule
is currently inert** — stated here as a complete, deterministic
specification for when the dataset grows, not because it currently binds.

## 5. Position selection

**Hold all currently position-eligible tickers — no `top_n` restriction.**
This is a mechanically forced choice, not a preference: the signal is
event-driven and sparse (6 total events observed across roughly 19 months
of coverage), so on almost every trading date the number of active,
non-neutral positions will be far below any plausible `top_n` value (0, 1,
or 2 in the current dataset, never more). A fixed `top_n` would either be
vacuous (never binding) or would require an ad hoc ranking rule among too
few candidates to rank meaningfully — neither serves this design. Stated
explicitly, before any return analysis: **if a future dataset expansion
produces enough concurrent eligible names that a `top_n` restriction
becomes meaningful, that is a new specification decision requiring its own
pre-registration, not a silent amendment to this one.**

## 6. Weighting

**Equal-weight, long-only.** Every active position (§5) receives weight
`1 / N_active` on each date, where `N_active` = the count of currently
active positive-direction positions (0 currently possible on most dates,
1 on the 2 current in-sample event dates). This mirrors H-011's own
`construction = "equal_weight"` convention exactly — reused, not
independently chosen.

**Negative-direction events are recorded but not traded.** No hypothesis on
this platform has ever run a short book — H-011's own prereg states
explicitly "Long-only, fully invested, no leverage, no shorts," and every
other `PREREG_H-*.md` on record follows the same convention. Introducing
short-selling mechanics for H-020 alone, with no platform precedent and no
established NGX short-borrow/margin cost model on this platform, would be a
new and untested assumption stacked on top of an already-thin dataset. A
`negative`-direction H-019 event is therefore recorded in the tradable
book's log as "signal present, not executed (long-only constraint)" rather
than silently dropped — this is disclosed as a real, stated limitation of
this specification, not hidden. **The current dataset contains zero
`negative` observations, so this constraint is also currently inert** —
again stated as a complete rule for a case that has not yet occurred, not
retrofitted to avoid one that has.

## 7. Entry timing

Execution occurs at the **closing price on the `eligible_from` session**
(the first NGX trading session strictly after `knowledge_timestamp`) — not
the open, not an intraday price, and not the session in which the news was
published. This is consistent with, and exactly as conservative as, the
platform's existing `execution_lag_days = 1` convention (H-011) in
magnitude — `eligible_from` is already one full session later than
`knowledge_timestamp` by construction (§14E), so no *additional* lag is
layered on top; using the close (not the open) of that already-lagged
session is the conservative choice within it, since intraday ordering is
explicitly unresolvable in this corpus (Stage 13 §13E: 0% intraday
precision).

## 8. Holding period

**Fixed at 60 NGX trading sessions** from entry (§7), unless superseded
earlier by §4's overlapping-event replacement rule. 60 sessions matches this
platform's own standard quarterly rebalance cadence (H-011 and every prior
cross-sectional hypothesis, e.g. `configs/h011_size.toml`'s
`rebalance = "quarterly"`), and — more directly on point, since H-019 is
event-driven rather than periodically rebalanced — matches the identical
60-session holding window already used by `docs/PREREG_H-006.md` (PEAD, an
earlier, unrelated, already-rejected event-driven hypothesis on this
platform, drafted 2026-07-21, over two weeks before H-019/H-020 existed).
Reused from both precedents for consistency, **not derived from or tuned to
any H-019 return observation**, since none was examined while writing this
document — and the H-006 precedent in particular predates H-019's existence
entirely, making a hindsight-selection story for this specific number
implausible. If a position's 60-session window elapses with no superseding
event, the position is closed at the closing price of the session on which
the window elapses (same conservative closing-price convention as entry).

## 9. Rebalancing

**Continuous, event-driven, evaluated on every NGX trading session** — not
a calendar-fixed quarterly rebalance like H-011's, because the underlying
signal itself is irregular and event-triggered, not a periodic
cross-sectional re-ranking. On each session: (a) any position whose
60-session window has elapsed with no new event is closed (§8); (b) any
newly-eligible signal (§2) with `direction != neutral` (§3) is entered
(§7) or replaces an existing position for the same ticker (§4). This
process is fully deterministic and mechanical — there is no discretionary
or performance-triggered rebalance step anywhere in this specification.

## 10. Transaction costs and slippage

**Reuse the platform's existing `cost_schedule` table exactly**
(`schema/schema.sql`), the same `source = "db"` convention already used by
H-011 and every other hypothesis on this platform — brokerage, SEC fee, NGX
fee, CSCS fee, stamp duty, and VAT, each at their currently-recorded
`rate_pct` and `confidence` (predominantly `'assumed'`, per H-011's own
disclosed L4 limitation — this specification does not upgrade that
confidence level for H-019, since no new cost-schedule verification work
has been done). This is a platform-wide, pre-existing schedule, not
something newly chosen for H-020, and is therefore not tunable to make
H-019 look more or less attractive — using it as-is is the conservative,
non-selective choice.

## 11. Liquidity/execution constraints

**Reuse H-011's exact liquidity default**: ADTV participation cap 10%,
60-trading-day ADTV window (`configs/h011_size.toml`'s
`[liquidity]` block). Where a position cannot be filled in full within this
constraint, it is handled by the platform's existing constrained-execution
simulator (`src/ngxrot/execution_realism.py`'s `constrained_simulate()`,
built in Stage 1 specifically for this purpose) — a **partial fill**, not a
silent exclusion of the observation. Per the explicit instruction against
silently dropping inconvenient observations after seeing performance: **no
event, ticker, or date may be removed from the H-019 dataset or from this
portfolio-construction protocol on liquidity grounds** — a liquidity
constraint changes how much of a signal can be executed, never whether the
underlying observation is counted or reported.

## 12. Benchmark

**Equal-weighted IRU (EW-IRU)**, quarterly-priced for comparison purposes
only (the benchmark's own construction is unaffected by H-020's
event-driven rebalance cadence) — identical to the benchmark used by every
other hypothesis on this platform (H-002 through H-018, `docs/PREREG_H-011.md`'s
own "Benchmark (ex-ante)" section: "Equal-weighted IRU portfolio, quarterly
rebalance, identical cost model"). Reused for direct comparability across
the platform's hypothesis library, not chosen to flatter H-019.

## 13. Failure/missing-data rules

- If `index_levels`/`equity_prices` data required to resolve `eligible_from`,
  an entry price, or an exit price is unavailable (no matching row, or only
  a sub-`min_confidence` row exists): the position is **not** entered or
  exited using a substitute/proxy price. The observation is logged as
  `PIT_status = PIT-UNCERTAIN` (reusing Stage 14 §14E's existing
  classification) and excluded from the tradable book for that date,
  exactly mirroring `event_pipeline.py`'s own stated principle: "the
  pipeline never infers, backfills, or fabricates."
- If a required H-019 dataset field (`direction`, `knowledge_timestamp_eligible_from`,
  `canonical_event_id`) is missing or null for an otherwise-qualifying
  event: the event does not enter the tradable book at all — it remains in
  the dataset (per H-019's own frozen construction) but contributes no
  position under this protocol.
- No missing observation is ever treated as `direction = neutral` by
  default — missing and neutral are different states (§14F of Stage 14
  already established this principle for the dataset layer; this document
  applies the same principle at the portfolio layer).

## 14. Multiple-testing discipline

Every parameter fixed in this document — position-selection rule (§5,
"hold all, no `top_n`"), weighting (§6, equal-weight long-only), entry
timing (§7, closing price at `eligible_from`), holding period (§8, 60
sessions), rebalance cadence (§9, continuous/event-driven), cost model
(§10, platform `cost_schedule`), liquidity constraint (§11, 10%/60-day
ADTV cap), and benchmark (§12, EW-IRU) — was chosen **before** any H-019
return or price-performance data was examined, and is now **frozen**. None
of these parameters may be changed after observing H-019 backtest results.
If a future researcher wants to test an alternative (e.g. a 30-session or
90-session holding period, or a `top_n`-restricted variant once more events
exist), that alternative must be **separately pre-registered under a new
hypothesis ID** (H-021 or later), never silently substituted into H-020's
own results after the fact — exactly the platform's standing rule ("changes
after first results = new hypothesis ID"), applied here explicitly to the
portfolio-construction layer specifically, not just the signal layer.

## Explicit restatement of what this document does NOT do

Per the critical constraint governing this stage: this document does not
modify the 6 qualifying H-019 events, does not loosen the GMC/CIR
definitions in Stage 14 §14A/§14C, does not add earnings events, does not
change any PIT rule (§2 reuses §14E verbatim), does not touch H-011, does
not create any additional observation, and was written without inspecting
any historical return or price-performance series. No backtest has been
run.
