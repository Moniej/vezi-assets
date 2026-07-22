# Pre-Registration — H-006: Post-Earnings-Announcement Drift (family: Event)

*Drafted 2026-07-22, BEFORE any H-006 experiment run. Executable form:
`configs/h006_pead.toml` (to be encoded when the cross-sectional engine
extension lands — see readiness report; the design below is frozen now).
Changes after first results = new hypothesis ID.*

## Economic rationale and market intuition

PEAD: prices underreact to earnings news and drift in the direction of the
surprise for weeks-to-months. On NGX the conditions that historically
STRENGTHEN drift are extreme: zero sell-side estimate coverage, retail
information processing, a ±10% band that truncates day-one repricing, and
no shorting (negative news corrects slowly — but we only trade the long
side). Filing timestamps (`created` on the X-Issuer SharePoint record) are
true point-in-time disclosure events — the dataset this platform was
partly built to exploit.

## Surprise proxy (no estimates exist on NGX — pre-declared)

Surprise = filing-window abnormal return: the stock's cumulative return
over sessions t0..t0+2 minus the EW-IRU return over the same sessions.
t0 = the filing's `created` session if created ≤ 14:30 WAT, else the next
session. Market-reaction PEAD is the standard design where estimates are
unavailable; the claim tested is "the initial reaction underweights the
news," not "we can forecast the reaction."

## Research question / hypotheses

Do stocks whose filing-window reaction is in the top tercile of their
event cohort earn positive net excess returns over the following 60
trading sessions?

- H0: net excess of the event book vs the EW-IRU benchmark ≤ 0.
- H1: net excess > 0, robust across grid and OOS.

## Event set (frozen)

- `data/staging/xissuer/earnings_calendar.csv`, submission_type
  **"Financial Statements" only** (8,685 filings; Board-Meeting notices are
  scheduling announcements, not results — excluded ex-ante).
- Symbol must be an IRU v2 member at t0; filing must pass the liquidity
  screen (a trade on ≥ 2 of the 3 reaction sessions). Multiple filings by
  one symbol within 5 sessions: the FIRST is the event, later ones ignored
  (restatement/attachment noise).
- Estimated usable events: ~4–5k in development. This is the
  best-powered event test available on this platform.

## Signal / portfolio construction

- Each month, events are pooled; reaction ARs standardized within cohort.
- **Base configuration (PRIMARY): long top tercile of cohort, entry at
  t0+3 (one session after the reaction window closes), hold 60 trading
  sessions, equal weight across active positions, max 20 concurrent
  (excess events: highest standardized AR wins — ex-ante tiebreak).**
- Sleeve design: capital not deployed in the event book sits in the EW-IRU
  benchmark portfolio (fully invested at all times, benchmark legs carry
  the same cost model).
- Stability grid (4 cells + base): hold ∈ {40, 60} ×
  selection ∈ {top tercile, top quintile}.

## Benchmark (ex-ante)

EW-IRU portfolio, quarterly rebalance, identical costs (same definition as
H-007 — deliberate: the two candidate factors are measured against the
same investable null).

## Costs / turnover / capacity — honest hurdle statement

Every event position pays a full round trip (~3.8%) against a 60-session
holding window. Frontier-market drift magnitudes for top-tercile reactions
must be exceptional to clear this; the design accepts a high prior of
"gross effect real, net effect dead." That outcome is pre-declared as
REJECT (as an investable standalone factor) with the gross result recorded
in the Factor Registry — it directly informs a future cost-shared overlay
design (new ID). Capacity: distribution reported at the standard AUM grid;
event names skew liquid (filers with active trading), which helps.

## Windows

Development 2015-07-01 → 2024-12-31 (calendar coverage begins 2014-07;
first year is warm-up). **Untouched OOS: 2025-01-02 → 2026-06-30**
(runner-enforced). Regimes: pre_float / float_shock / OOS as in H-007.

## Validation plan

Phase 4 unchanged: stability map (5 cells) → Holm/BH → seeded placebo
(100 iterations; event-to-symbol assignment shuffled within each monthly
cohort — tests whether the REACTION RANKING carries information beyond
event timing, at identical dates/costs) → walk-forward → final OOS → IC
memo.

## Confirmation requires ALL of

1. Placebo p ≤ 0.05 on the base configuration.
2. Base net excess vs EW-IRU > 0 in development AND final OOS.
3. Plateau: ≥ 3 of 5 cells with positive net excess.
4. ≥ 1 cell significant under BH at FDR 0.10.
5. No regime contributes > 80% of cumulative excess.
6. No signal-quality failure condition triggered.

## Rejection (any one suffices)

Placebo p > 0.05 · base OOS net excess ≤ 0 · cost drag eliminates gross ·
regime concentration > 80% · signal-quality failure. Gross-positive but
net-negative = REJECT with gross knowledge recorded (see cost section).

## Multiple-testing treatment

5 cells under BH within-hypothesis; program-level count in the IC memo.
H-006 and H-007 are the wave's ONLY two active hypotheses (program cap).

## Expected Interaction with Existing Factors

- Family: **Event** (earnings). Library empty; wave-mate is H-007
  (Momentum).
- Expected correlation with H-007: LOW-to-moderate positive — drift
  following events feeds later momentum formation windows, but PEAD
  conditions on discrete information arrival over ~3 months while 12-1
  momentum aggregates a year of relative returns; overlap is partial by
  construction (the skip-month in 12-1 removes the freshest events).
- Diversification: expected YES — episodic, event-clock exposure vs
  momentum's calendar-clock exposure; event book turnover is
  self-liquidating rather than rebalance-driven.
- Portfolio construction value if validated: an overlay/sleeve that
  deploys opportunistically against a core factor book — improves the
  combined information ratio if the low-correlation prior holds (to be
  MEASURED, not assumed, before any combination).
- Independence rationale: input is the market's reaction to a specific
  disclosure, orthogonal to price-level (value), risk (low-vol), and
  largely to trailing-return (momentum) inputs.

## Known limitations (pre-declared)

L1 no earnings VALUES — reaction proxy conflates earnings news with
coincident news (works against H1, not for it). L2 filing `created`
timestamps before 2014-07-11 don't exist and 95 migration-batch items have
unknown announcement times — excluded. L3 price-only returns (dividend
markdowns near results season bias measured drift DOWNWARD for payers —
conservative). L4 retail cost schedule 'assumed'. L5 177 single-source
days as in H-007.
