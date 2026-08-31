# H-024 — Liquidity Shock and Future Volatility

## Status and boundary

This is a frozen, implementation-ready **risk / market-structure** protocol.
It has not run an outcome regression, does not create an Alpha recommendation,
and cannot alter H-011, H-013, or H-016. A positive result is usable only as
research/risk evidence unless a later governed process authorizes another use.

## Hypothesis and confirmation rule

**H-024.** Negative stock-level liquidity shocks predict higher subsequent
realized volatility on NGX equities. The null is a non-negative or
economically immaterial shock coefficient after the predeclared lagged-volatility
control.

The primary estimand is the coefficient on `LiquidityShock(i,t)` in:

```text
RV_forward_20D(i,t) = alpha + beta * LiquidityShock(i,t)
                       + gamma * LaggedRV20D(i,t) + month fixed effects + error
```

The expected sign is `beta < 0`: lower-than-usual ADTV predicts higher forward
volatility. Use pooled stock-month OLS with two-way clustered standard errors
by ticker and formation month. Do not substitute a GARCH specification or add
macro controls to the primary test. Minimum evidence for confirmation is:

- primary 20D coefficient has the preregistered expected sign;
- two-way-clustered two-sided p < 0.05 on the 20D primary test;
- the estimate survives Holm adjustment across the 5D/20D/60D horizon family;
- a minimum absolute economic effect: a one-standard-deviation adverse shock
  increases predicted annualized 20D RV by at least 2 percentage points;
- at least 24 monthly formations, 100 eligible securities per formation on
  median, and 5,000 stock-month observations overall;
- the final 20% of formations (chronological holdout) retains the expected
  sign and at least half the development-period effect magnitude; and
- no single calendar year supplies more than 40% of weighted observations or
  reverses the estimated sign without a documented data-quality explanation.

Failure of any item means **not confirmed**; it does not imply an Alpha verdict.

## Frozen signal construction

Use the H-011 comparison fixture's price, value-traded, activity, and
corporate-action flag tables; build a distinct H-024 dataset artifact from its
read-only contents before testing.

```text
ADTV60(i,t) = mean(value_traded(i,s)), s in the prior 60 eligible sessions
```

Require at least 45 positive/non-missing value-traded observations in that
window. `t` is a fixed monthly formation date. There is no imputation of zero
or missing value traded.

```text
LiquidityShock(i,t) = log(ADTV60(i,t))
  - median(log(ADTV60(i,s))), s in [t-252, t-1]
```

Require at least 120 valid historical ADTV60 observations for this baseline.
The decision is at `t`; all outcomes begin at `t+1`. The signal never uses a
future session.

## Outcomes and family

For each eligible observation, price-only realized volatility is:

```text
RV_h(i,t) = sqrt(252/h) * SD(r(i,t+1) ... r(i,t+h))
```

The 20-session outcome is primary. The 5- and 60-session outcomes are
secondary robustness horizons. Apply Holm correction once across all three
horizons; they are one hypothesis family, not three independent discoveries.
`LaggedRV20D` uses the preceding 20 sessions ending at `t` only.

## Corporate actions and stale prices

Prices are not canonical adjusted/total-return series. Exclude and flag any
signal, lagged-volatility, or forward-outcome window crossing a known material
split, bonus issue, rights-related markdown, reconstruction/consolidation, or
other price-mechanically material action. The present data only has incomplete
corporate-action coverage; unknown actions remain a disclosed residual risk.

Persist these staleness fields in the frozen H-024 dataset:

- `zero_return_indicator`;
- `positive_volume_zero_return_indicator`;
- available deals/trading-activity;
- trailing zero-return fraction; and
- trailing positive-volume zero-return fraction.

The latter two are **price-staleness proxies**, not zero-trade frequencies.
Predeclared robustness views are: full eligible sample; exclude a security-month
when trailing zero-return fraction exceeds 80%; include lagged staleness as a
reported sensitivity control; and a higher-activity subset requiring median
trailing deals >= 5. These are fixed before outcomes; they cannot be changed
after inspecting coefficients.

## PIT, coverage, and artifact requirements

Use strict system-vintage availability by default and source data no later than
the frozen fixture vintage. The H-024 dataset manifest must record source
fixture SHA-256, source database hash/vintage, code/config hash, formation and
observation counts, excluded corporate-action windows, missingness, and the
exact eligibility/holdout split. Dataset outputs are research artifacts, never
formal research evidence or Alpha evidence.

No macro control set is authorized: current macro coverage does not support a
PIT-safe, sufficiently broad primary control design. Sector controls are also
not primary because historical sector coverage is incomplete.

## Computational plan

On the present local data (~318k frozen daily rows), panel construction and
window eligibility are O(stock-days), approximately seconds to a few minutes;
the three clustered regressions and frozen artifact validation are expected to
fit comfortably on a normal developer workstation. This estimate excludes any
future corporate-action data remediation.
