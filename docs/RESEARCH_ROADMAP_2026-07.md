# Factor Research Roadmap — 2026-07-21

Author role: Head of Quantitative Research. Governance: every candidate
factor runs the UNCHANGED gauntlet (pre-registration → PIT → walk-forward →
placebo → Holm/BH → costs → capacity → untouched OOS). The Validated Factor
Library is empty and stays empty until evidence says otherwise. Data vintage
pinned: 2026-07-21 (`docs/DATA_FREEZE_2026-07-21.md`).

## 1. Current state (verified, not aspirational)

COMPLETE / production: PIT store (3 validated price sources, 320,159 rows /
2,933 days / 12 gate-ready years); IRU v2 (~100 names/yr, PIT,
rename-canonical); Coverage Gate PASS; earnings calendar (10,690 filings,
PIT `created`); ex-div closure calendar (1,044 events); gainers transitions
(official adjusted bases, 138k rows); official prev-close table; events DB
(MPC 80, regulatory 13); Brent; cost schedule (retail, 'assumed');
experiment registry + ledger + phase4 gauntlet + reproducibility (all
battle-tested across 4 honest rejections); diagnostics D1–D4.

IN FLIGHT: corp-actions PDF archive (~8.8k/11,546, background, resumable).

NOT AVAILABLE (blocks specific families): fundamentals VALUES (revenue,
margins, book value — needs statement parsing/OCR); shares outstanding
(harvest not built); dividend AMOUNTS (dates exist; amounts sit unparsed in
DOL dividend columns); analyst data (does not exist for NGX); intraday
data (never).

STRUCTURAL CONSTRAINTS every design must respect:
- No shorting on NGX → every factor is a LONG-ONLY tilt vs an investable
  benchmark. Benchmark must be defined ex-ante (see §4).
- Retail costs ~4% per full round trip → sub-quarterly holding is dead on
  arrival (H-005's lesson); low-turnover designs strongly favored.
- Breadth ~100 investable names; dev window 2015-2024, untouched OOS
  2025-26. Pivot-memo power math: per-stock quarterly detection of IC≈0.05
  needs ~10 years — we have exactly that. Power is adequate, not lavish:
  maximize breadth per test, no sub-slicing.

## 2. Factor family readiness

### Ready now — zero new engineering

**H-007 — Cross-sectional momentum (12-1)** — PRIORITY 1
- Rationale: slow information diffusion + investor underreaction; the most
  replicated cross-sectional effect in EM/frontier markets; NGX retail
  dominance and absence of shorting mean overpricing corrects slowly but
  underpricing persists — long-only momentum harvests the latter.
- Data: price panel + IRU (both frozen). Holding: quarterly rebalance,
  monthly-overlapping portfolios (power without turnover). Turnover: ~60-100%
  /yr one-way → ~2.5-4%/yr cost drag at retail rates — the binding hurdle.
- Capacity: top-quintile ADTV concentration; report distribution per
  standard protocol. Frontier momentum lives in mid-liquidity names — watch
  the capacity-signal tradeoff explicitly.
- Risks/failure modes: crash risk at regime turns (2023 float, 2020);
  band-limited price discovery may smear formation returns (12-1 skip
  month helps); stale prices inflate measured momentum (staleness filter
  ex-ante: exclude names stale >N sessions in formation window — rule set
  in prereg, not after).
- Power: ~40 quarters × ~100 names. Adequate.

**H-006 — Post-earnings-announcement drift (PEAD)** — PRIORITY 2
- Rationale: underreaction to earnings news; no analyst coverage and
  slow retail information processing on NGX should PROLONG drift; filing
  timestamps are true PIT (SharePoint `created`).
- Surprise proxy (no fundamentals values): market-reaction PEAD — the
  abnormal return over the filing window (t0..t0+2) classifies the news;
  drift measured t0+3 → t0+60. Standard where estimates don't exist.
- Data: earnings calendar × price panel (both frozen). ~10,690 filings →
  ~5-6k usable IRU events in dev window. Holding: ~3 months. Turnover:
  event-driven, capped by design.
- Risks/failure modes: 4% round trip vs. realistic drift magnitude — the
  honest failure mode is "signal real, net dead" (that outcome still feeds
  the library design: PEAD as tilt inside another portfolio shares costs);
  thin trading contaminates the reaction window (min-liquidity filter
  ex-ante); filing-type heterogeneity (audited vs interim — pooled first,
  no sub-slicing without pre-registered hierarchy).
- Power: thousands of events — best-powered event test available to us.

**F13a — Low volatility** — wave 2 (prereg after H-006/H-007 verdicts)
- Rationale: leverage-constraint/lottery-preference anomaly; strongest in
  markets where shorting is impossible (ours literally is). Long-only
  friendly, LOW turnover → cost hurdle is minimal (~1%/yr) — structurally
  the best-suited factor for NGX costs.
- Data: price panel only. Holding: quarters-years. Failure modes: vol
  estimates corrupted by stale prices (require trading-frequency floor);
  low-vol ≈ large-liquid on NGX → may collapse into beta/size confound
  (pre-register the orthogonality check).

**F13b — Short-term reversal**: monthly horizon → killed by costs with
near-certainty. Deprioritized; test only if a cost-shared implementation
(overlay on rebalance trades) is designed. Knowledge value low relative to
slot cost.

**F4 — Liquidity premium**: measurable now (ADTV/Amihud from value_traded).
Paradox: validating it certifies a premium we cannot harvest at scale
(capacity IS the factor). Research value = risk-model input more than
standalone alpha. Wave 3, as infrastructure for the Risk Engine.

### One parser extension away (moderate engineering, no OCR)

**F6/FV — Dividend yield + Value (E/P)** — the DOL dividend region prints
Interim/Final dividend AMOUNTS + EPS + P/E per stock per day; only the
DATE bands were parsed for the gate. One char-level extension of the
validated exdiv parser yields a daily PIT dividend/EPS panel 2014→2026 →
unlocks dividend-yield and E/P value factors, plus total-return
construction for every other factor's benchmark. HIGHEST-VALUE ENGINEERING
ITEM. (Validation: GTCO/Zenith anchors + cross-era spot checks, same
protocol as the gate parsers.)

**Market-cap layer from LIST2** — PRICES_LIST2 prints market cap per stock
per day across ~2,800 archived days; the LIST2 parser already regexes the
column and discards it. Unlocks: SIZE factor, cap-weighted investable
benchmark, capacity refinement (float proxy). Small engineering step.

### Blocked (do not schedule yet)

Quality / Growth / earnings-revision / accruals: need statement VALUES →
OCR + financial-statement parsing (user-gated tesseract decision; scanned
majors). Event-driven corp-actions detail: needs the same OCR. Revisit
after wave 2.

## 3. Roadmap to the first validated strategy

- **R0 (now, zero engineering)**: draft H-006 + H-007 preregs (pattern
  PREREG_H-005; vintage/gate/IRU pinned; staleness + liquidity filters and
  benchmark defined ex-ante) → owner review → gauntlet → mechanical
  verdicts. Two shots on goal with the two best-powered ready families.
- **R1 (parallel with R0 runs)**: DOL dividend/EPS layer parse + LIST2
  market-cap layer (both validated before use). No new hypotheses run
  until R0 verdicts are in — concurrency cap = 2 preregs.
- **R2**: wave-2 preregs from {low-vol, E/P value, dividend yield},
  informed by R0 *process* learnings (never by peeking at OOS).
- **R3**: first `confirmed` factor → Stock Scoring Engine speaks its first
  non-empty output (alpha_engine adapter, provenance-checked). Second
  confirmed factor → Portfolio Construction + Risk Engine build begins
  (charter milestone rule).
- **Continuous**: factor-decay monitoring design lands WITH the first
  confirmed factor (rolling IC vs validation-era IC, alarm thresholds
  pre-registered in the factor's library entry); corp-actions harvest
  completes in background; daily capture scheduling remains a pending
  owner decision — every missed day is unrecoverable.

## 4. Program-level rules (new, additive — no governance relaxed)

1. Benchmark ex-ante: until the LIST2 cap layer is validated, the
   investable benchmark is the equal-weighted IRU portfolio at quarterly
   rebalance with the same cost model, reported alongside ASI. Cap-weighted
   benchmark replaces it (new prereg field) once validated.
2. Concurrency cap: ≤2 open preregs; program multiple-testing tracked in
   the ledger (family-level count reported in every IC memo).
3. A factor enters the library only with: validation history, expected-alpha
   interval from walk-forward, capacity distribution, stability metrics,
   decay-monitoring spec, and an economic-rationale paragraph written at
   prereg time (not post hoc).
4. Every rejection updates this roadmap's family table before the next
   prereg is drafted.
