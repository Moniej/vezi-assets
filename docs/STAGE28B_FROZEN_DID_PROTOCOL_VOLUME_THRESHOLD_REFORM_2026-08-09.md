# Stage 28B — Frozen Diagnostic Protocol: NGX Volume-Threshold Reform (Natural Experiment)

**Date frozen:** 2026-08-09. Platform price data currently ends **2026-07-21** — 27 calendar days before
the reform's 2026-08-17 effective date. **Nothing in this document has been run.** This is a
specification only, written before any post-reform observation exists, so that no part of it can be
tuned by hindsight. No hypothesis is registered. No DB write occurs. No backtest, no factor, no
optimization. The single candidate under investigation is the SEC-approved, NGX-implemented
volume-threshold price-movement reform (Stage 28 §1, §5, §6).

**Deviation protocol**: if any step below turns out to be infeasible once real data exists (e.g. a field
doesn't behave as expected), the deviation and its reason must be logged in a dated addendum to this same
document — the frozen text is never silently edited after data exists.

---

## 1. Treatment assignment — frozen now, computed later

**Rule facts, as sourced in Stage 28:**
- Old threshold (all securities, uniform): 100,000 cumulative shares must trade before the quoted price
  may move.
- New threshold (tiered, SEC-approved 2026-06-16): ≥₦1,000/share → 10,000 shares; ₦500–₦999.99/share →
  50,000 shares; <₦500/share → 100,000 shares (unchanged).
- Effective date: **2026-08-17**.

**Treatment group**: every ticker whose closing price on the **last trading session strictly before
2026-08-17** is ≥₦1,000. This is the group whose threshold falls by 10x (100,000→10,000).

**Control group**: every ticker whose closing price on that same reference session is **<₦500**. This
group's threshold is explicitly unchanged by the rule (100,000 both before and after) — a genuine placebo
group, not an arbitrary low-price bucket.

**The ₦500–₦999.99 band is explicitly excluded from both groups, not silently assigned.** Its own
threshold *also* changes (100,000→50,000, a 2x reduction) — it experiences a real but smaller treatment
than the ≥₦1,000 group, and folding it into either the treatment or control group would contaminate both
comparisons. It is retained in the raw dataset and reported separately (§3, §5) as a **dose-response check
group**, never pooled into the primary DiD.

**Reference session**: fixed as the last trading session with a valid close **strictly before**
2026-08-17 — i.e., whatever date `MAX(trade_date) WHERE trade_date < '2026-08-17'` resolves to once the
platform's price feed covers that period. Not computed today, since today's latest available date
(2026-07-21) is not the correct reference point and using it now would itself be a form of pre-reform
peeking at a stale price level. **Non-binding preview only**, using 2026-07-21 data purely to size the
likely groups, explicitly not the frozen reference date: of 139 tickers with a same-day close on
2026-07-21, 7 were ≥₦1,000, 6 were ₦500–999.99, and 126 were <₦500. This previews a real concentration
risk (§5, §7) — the treatment group may end up very small — but the actual group membership will be
computed fresh from the real reference-session data, not from this preview.

**Board/security-type scope caveat (carried over from Stage 28, still unresolved)**: the sourced articles
describe the rule as applying to "equities trading" generally. Whether it applies uniformly across
Main/Premium/Growth boards or has any carve-outs was not confirmed against a primary NGX circular in
Stage 28 and remains unconfirmed here. If a scope exception is found before the diagnostic runs, it must
be incorporated into treatment assignment and logged as a deviation; if not found, the diagnostic proceeds
on the "applies to all listed equities" reading with that limitation disclosed in the results, not
silently assumed away.

## 2. Primary outcome — frozen definition

**Metric**: zero-return session frequency per security, reusing Stage 21's own definition verbatim (no
redefinition):

- **Price field**: `equity_prices.close`.
- **Session definition**: a row in `equity_prices` for that `ticker`/`trade_date`.
- **Zero-return session**: `close == previous available close` for the same ticker (strict equality on
  the stored value — not a rounded or tolerance-banded comparison), where "previous available close" is
  the immediately preceding row for that ticker in the table, **not** the immediately preceding calendar
  date. This matches Stage 21's `is_zero` definition exactly.
- **Genuine unchanged vs. missing**: as in Stage 21/23, a session is further split into (a) genuinely
  traded-but-unchanged (`volume IS NOT NULL AND volume > 0`) vs. (b) no recorded trade (`volume IS NULL OR
  volume = 0`). Both count toward "zero-return" for the primary metric (consistent with Stage 21), but are
  reported separately so a spurious result driven entirely by missing-data patterns rather than genuine
  price stickiness can be caught.
- **Suspended securities**: detected the same way as every prior stage in this project (Stage 19 §5,
  Stage 23 §8) — via absence of rows in `equity_prices`, not via `securities.delisting_date` (confirmed
  NULL platform-wide, not usable). A security with **no row at all** for a given session is simply absent
  from that session's panel — it does not count as a zero-return session (there is no comparison to make),
  and does not count as a non-zero session either. It is excluded from both the numerator and denominator
  for any session it's absent. If a ticker has fewer rows in the post-period than the minimum below, it is
  excluded from the analysis entirely (not imputed, not forward-filled).
- **Newly listed securities**: a ticker whose `securities.listing_date` (or first `equity_prices` row,
  whichever is later/more conservative) falls after the pre-period window start is excluded from the
  pre-period entirely (it has no valid pre-trend to compare) and flagged separately if it appears in the
  post-period — not silently included as if it had a full pre-period history.
- **Minimum observations required**: a ticker must have **at least 30 of the 40 pre-period sessions and at
  least 30 of the 40 post-period sessions present** (i.e. ≤10 missing/suspended sessions in each window)
  to be included in the primary DiD. This threshold is fixed now; it is not to be loosened if it produces
  an inconveniently small sample, nor tightened if a larger sample would look more favorable.
- **No calendar-day substitution anywhere** — every window below is defined in trading sessions (rows in
  `equity_prices`), never calendar days.

## 3. Difference-in-differences — frozen model

**Windows**:
- **Pre-period**: the 40 trading sessions immediately preceding the reference session defined in §1 (i.e.
  40 rows per ticker ending at that session, inclusive).
- **Post-period**: the first 40 trading sessions on or after 2026-08-17, per ticker (the first `40`
  available rows with `trade_date >= '2026-08-17'`).
- Both windows are **40 sessions each, fixed now**, matching this program's existing convention (Stage 21B
  used the same round horizon-selection discipline). Not shortened or extended after seeing early results.

**Unit of observation**: security-level. For each ticker `i` and period `t ∈ {pre, post}`, compute
`zero_freq(i, t)` = zero-return session count / eligible session count within that ticker's window (using
only sessions where the ticker has a row, per §2's suspension handling).

**Model**:

```
zero_freq(i, t) = β0 + β1·Treated(i) + β2·Post(t) + β3·(Treated(i) × Post(t)) + ε(i, t)
```

with `Treated(i)` fixed at 1 for the ≥₦1,000 group, 0 for the <₦500 control group (the ₦500-999.99 band
is not in this regression at all — see §1 and §5). **β3 is the parameter of interest.**

**Clustering**: standard errors clustered by security (`ticker`), reusing the exact CR1 small-sample
sandwich estimator already built in `scripts/stage26_clustering_diagnostic.py`
(`cluster_robust_mean_test`, generalized to a two-group difference-in-means-of-differences rather than a
single mean — same estimator family, not a new method). Given the treatment group is expected to be small
(single digits, per the §1 preview), an **exact sign-permutation test** (as used in Stage 26, feasible up
to ~20 clusters) will also be reported as the primary inferential result if the treatment group has fewer
than ~15 members, since asymptotic clustered SEs are not trustworthy at that scale — this mirrors exactly
the discipline already applied to the small-G ticker-clustering problem in Stage 26.

**Market/session controls**: only if justified from data already on the platform — specifically, the
NGXASI index return over the same session (from `index_levels`) may be added as a session-level control
if the pre-trend check (§5) reveals a market-wide confound coincident with 2026-08-17 (e.g. a broad
volatility event unrelated to the reform). This control is **not added by default** — adding it is
conditional on a specific, disclosed reason found in the pre-trend diagnostic, not a default part of the
model, to avoid covariate-shopping.

**Primary question, stated exactly as it will be answered**: did the ≥₦1,000 group experience a
disproportionate reduction in zero-return frequency after 2026-08-17, relative to the <₦500 control group,
beyond what either group's own pre-existing trend would predict?

## 4. Second-stage economic gate — specified now, **not run now**

A statistically real reduction in zero-return frequency is **not evidence of alpha** and will not be
treated as such. If and only if §3's DiD is positive and survives §5's falsification checks, the required
next diagnostic (still not a backtest) must establish, in this order:

1. Whether the reduced staleness corresponds to **larger, not just more frequent**, price moves (a
   genuinely more responsive price-formation process) versus merely more frequent *small* moves (which
   would not be economically meaningful even if statistically real).
2. Market-relative return behavior around the newly-unstuck price moves, using the same NGXASI-relative
   methodology as Stage 21C/24 (reused, not reinvented).
3. Whether the effect is tradable at all — realistic execution given the treatment group's own liquidity
   (informed by the same ADTV/capacity framework used throughout this project), since the treatment group
   is expected to be small and may include exactly the kind of thin, previously-stale names for which
   execution has been a binding constraint in every prior stage of this program.
4. The existing 3.79% round-trip cost floor (`cost_schedule`, unmodified) as a hard gate, exactly as
   applied in Stages 21C, 24, and 27.

**This second-stage work is explicitly deferred — it is not authorized to begin until §3's first-stage
result exists and is evaluated against §7's kill criteria.** Writing it down now (rather than after seeing
the DiD result) is itself part of protecting the experiment from hindsight bias.

## 5. Falsification checks — frozen now

- **Placebo reform dates**: the identical DiD (§3) re-run with the "reform date" artificially set to two
  placebo dates with no real rule change — one placebo 40 sessions before 2026-08-17 (entirely within the
  old regime) and one placebo 40 sessions before that (a second, earlier old-regime placebo). If either
  placebo produces a DiD estimate of similar magnitude/significance to the real 2026-08-17 result, the
  real result is not credible as reform-specific.
- **Pre-trend comparison**: within the 40-session pre-period, split into two 20-session halves and confirm
  `Treated × (first-half vs. second-half)` is statistically indistinguishable from zero for both groups
  before trusting the main post-reform comparison — a standard parallel-trends check, run on data that
  entirely predates the reform (so this specific check *can* be run today, once the pre-period is fully
  defined at the real reference date — it does not require post-reform data and is not blocked by the
  current data-timing gap).
- **₦500–999.99 dose-response check**: this band's own threshold drops 2x (100,000→50,000), a real but
  smaller treatment than the ≥₦1,000 group's 10x drop. If the mechanism is real, this band's DiD estimate
  should sit **between** zero (the untreated control) and the ≥₦1,000 group's estimate — a monotonic
  dose-response pattern. If this band shows an equal-or-larger effect than the ≥₦1,000 group, or no
  relationship to treatment intensity at all, that weakens the causal story materially.
- **Bound-vs-unbound check (the most important one, per instruction)**: within the ≥₦1,000 treatment
  group, split tickers by whether they were actually **constrained** by the old 100,000-share threshold
  pre-reform — operationalized as: a ticker's own pre-period zero-return frequency in the top half of the
  treatment group's distribution (i.e., names that were visibly sticky under the old rule) vs. the bottom
  half (names that traded freely below 100,000 shares' worth of friction even under the old rule, e.g.
  because their own typical daily volume already exceeded it comfortably). **The mechanism specifically
  predicts the top half (previously bound) should show a materially larger post-reform reduction in
  zero-return frequency than the bottom half (never really bound).** If both halves move equally, the
  causal story collapses to "something else changed for high-priced stocks in August 2026," not "the
  volume-threshold rule was binding and its relaxation mattered."

## 6. Data sufficiency gate

The diagnostic **does not start** until the platform's price feed contains at least 40 full trading
sessions with `trade_date >= '2026-08-17'` for the treatment and control groups as defined in §1. Given
NGX's trading calendar, 40 sessions is roughly 8 calendar weeks — expect the earliest feasible run date to
be **mid-to-late October 2026**, not before. The window is not shortened because an early partial read
looks interesting, and not lengthened past 40 sessions to chase significance. Pre-trend checks (§5, second
bullet) are the only piece of this protocol that can run before that date, since they use only pre-period
(already-available-once-the-reference-date-is-known) data.

## 7. Hard kill criteria — restated as the literal decision rule

The mechanism is killed (not iterated on, not rescued by adjusting a definition above) if **any** of:

- Pre-trends (§5) are materially incompatible between treatment and control.
- The DiD estimate (§3) is statistically indistinguishable from zero or unstable across the clustering/
  permutation methods specified.
- A placebo date (§5) produces a comparable effect to the real date.
- The ₦500–999.99 band (§5) shows no dose-response relationship to treatment intensity.
- The bound-vs-unbound split (§5) shows no differential — i.e., previously-constrained names don't respond
  more than never-constrained names.
- The second-stage economic gate (§4), if reached, shows the effect doesn't translate into economically
  meaningful, cost-surviving price discovery.

**A successful first-stage DiD, on its own, does not authorize §4, a hypothesis, or a backtest.** It only
establishes whether the 2026 rule change altered NGX price formation the way the mechanism predicts. Every
step past that remains separately gated, exactly as written above.

---

**Status: WAIT.** Nothing above is executed. The next action on this track is calendar-driven, not
effort-driven: re-open this document once `equity_prices` contains ≥40 post-2026-08-17 sessions, run §3
and §5 exactly as specified, and report the result against §7 before anything else is authorized.

---

## Amendment log

### Amendment 1 (2026-08-09) — closes the §1 treatment-assignment ambiguity found in Stage 28C

Stage 28C's validation ran §1's rule against real data under two readings and found they diverge sharply,
with the unbounded look-back reading badly contaminated by tickers whose reference price is up to ~12
years stale. **§1 is amended, effective immediately, to read:**

> Treatment assignment uses the closing price on the last trading session strictly before 2026-08-17.
> **A ticker with no `equity_prices` row on that exact session is classified INELIGIBLE for
> treatment/control assignment** — excluded from the treated, mid-band, and control groups alike, not
> defaulted into any of them via a historical look-back of any length.

This is a closing of an unspecified case, not a retuning of an already-specified one — no threshold,
window, or outcome definition changes. The original §1 text is left in place above for the audit trail;
this amendment controls.

### Amendment 2 (2026-08-09) — closes the §2 newly-listed-security gap found in Stage 28C

`securities.listing_date` is confirmed **0/320 populated** — entirely unusable, not merely incomplete.
**§2's newly-listed handling is amended to rely solely on the fallback already named in the original
text**: a ticker's first `equity_prices` row is its listing-date proxy. This was already an allowed
alternative in the frozen text ("or first `equity_prices` row, whichever is later") — the amendment simply
removes `listing_date` as a live option rather than leaving it as a nominal primary that never resolves.

**No other element of §2, §3, §5, §6, or §7 is touched by either amendment** — the zero-return definition,
suspension handling, ≥30/40-session minimum, DiD specification, clustering/permutation method, placebo
windows, and dose-response check all stand exactly as originally frozen.

### Amendment 3 (2026-08-09) — operational clarification, not a redefinition: `equity_prices` deduplication

Discovered while fixing the market-data freshness gap (Stage 28D): `equity_prices` carries **multiple
source rows per (ticker, trade_date)** by design (`ngx_pricelist_v1`, `ngx_pricelist_v2`, `ngx_dol_v1` —
independent parser/source vintages, tracked via `source_id`, no unique constraint on
`(ticker, trade_date)` alone). This is pre-existing and platform-wide (301,459 duplicate pairs found,
296,586 of them already present before today's data refresh — not introduced by it). 301,405 of those
pairs carry byte-identical `close`/`volume` across sources; a small residual **54 pairs genuinely
conflict**. The platform's own established canonical-panel function
(`backtest_xs.load_panel()`) already resolves this via `drop_duplicates(subset=["ticker","trade_date"],
keep="last")`.

**§2's outcome definition is clarified, not changed**: "previous available close" must be read against a
**de-duplicated one-row-per-(ticker, trade_date) series**, using the same `keep="last"` rule
`load_panel()` already uses — not a new tie-break invented for this protocol. Without this
clarification, a ticker with duplicate same-day rows spuriously registers an extra same-day
"zero-return" (a day compared against its own duplicate), inflating the metric. This does not change
`close`/`volume` values themselves (nearly all duplicates agree exactly) and does not touch any
threshold, window, or model specification — it specifies *how* to correctly read the existing table,
which the frozen text assumed implicitly and did not need to state until real multi-source duplication
was found in practice.

### Amendment 4 (2026-08-09) — supersedes Amendment 3's volume/value_traded tie-break (Stage 28E audit)

Stage 28E audited all 54 `(ticker, trade_date)` pairs where duplicate rows genuinely disagree and found
the disagreement is **confined entirely to `volume`/`value_traded`/`deals`** — `open`/`high`/`low`/`close`
are unanimous in 100% of the 54 groups, so Amendment 3's `close`-reading clarification (and the primary
outcome, which depends only on `close`) is confirmed unaffected and stands as written. The conflicts
themselves trace to a specific, identified parser defect (`ngx_pricelist_v1`'s volume/value-field
mis-parse, partially fixed by `v2` but reproduced on 2026-08-09's re-ingest because already-staged
historical files are not re-parsed on a version bump).

**Amendment 3's plain `keep="last"`-by-`source_id` tie-break is not safe for volume/value_traded** — for 3
of the 54 conflicting dates, it would silently select a corrupted, ~10^19-magnitude volume value over a
correct one, and this is superseded by: **prefer the row (or agreeing rows) with a non-null
`value_traded`; if none exists, mark the observation's volume fields UNRESOLVED; if more than one
*distinct* non-null `value_traded` value exists in a group (did not occur in practice, 0/301,459 groups),
mark it AMBIGUOUS and exclude rather than guess.** This governs only how `volume`/`value_traded`/`deals`
are read for any secondary or deferred use (e.g. §4's economic gate) — it does not touch the primary
`close`-only outcome, any threshold, window, estimator, placebo construction, or kill criterion.
