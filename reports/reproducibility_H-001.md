# Reproducibility Report — H-001

Generated 2026-07-15. Source of truth: `data/registry.sqlite` (immutable) + `experiments/*.json` snapshots.

## Hypothesis

Cross-sectional 3-6M price momentum across NGX sector indices, long-only top-N rotation, outperforms the NGX ASI after realistic transaction costs and liquidity constraints, out of sample.

- status: **testing**
- conclusion: (pending)

## Experiment inventory

- total experiments: **111**
  - investing_com / development: 46
  - investing_com / final_oos: 4
  - investing_com / placebo: 2
  - investing_com / walk_forward: 10
  - synthetic_dev / development: 35
  - synthetic_dev / final_oos: 4
  - synthetic_dev / placebo: 1
  - synthetic_dev / walk_forward: 9
- code fingerprints used: 2742acc6ec9119f4, 436550005d783681, 49ac43f1443d5881, 72090503772e054f, f1deaf3c344e85c6
- config files: C:\Users\nonso\Desktop\vezi assets\ngx-rotation\configs\p3_full_synthetic.toml, configs/p2_baseline_synthetic.toml, configs/p2_catalyst_synthetic.toml, configs/p2_cost_sensitivity.toml, configs/p2_cost_sensitivity_real.toml, configs/p3_full_synthetic.toml
- distinct resolved-config hashes: 107 (full config stored verbatim per experiment)

## Evidence-grade (real data) runs

- provider: investing_com (aggregator, base confidence 0.5)
- data vintage (as_of): latest (ingested 2026-07-15)
- confidence floor: 0.4
- RNG: PCG64, seeds [42], placebo iterations [100]
- anchor cross-reference: NGXASI verified at 3 independent year-end values (see data/reference_anchors.csv); staging validation report: reports/data_completeness_2026-07-15.md

## Validation status (real data, both pre-registered variants)

- `0c7c52d5` [final_oos] 2025-01-02..2026-06-30 excess=-15.40% sharpe=2.419 reject_flag=False
- `1cedcc5c` [final_oos] 2025-01-02..2026-06-30 excess=-15.40% sharpe=2.419 reject_flag=False
- `2a9a1a1e` [walk_forward] 2023-01-02..2024-12-31 excess=+18.82% sharpe=2.696 reject_flag=False
- `37a40983` [walk_forward] 2020-09-01..2022-12-30 excess=-27.47% sharpe=0.333 reject_flag=False
- `406e5e34` [walk_forward] 2016-06-01..2022-12-30 excess=-7.37% sharpe=0.109 reject_flag=False
- `506ee0fc` [final_oos] 2025-01-02..2026-06-30 excess=-38.62% sharpe=1.413 reject_flag=False
- `628621e9` [final_oos] 2025-01-02..2026-06-30 excess=-38.62% sharpe=1.413 reject_flag=False
- `6da9a533` [walk_forward] 2020-09-01..2022-12-30 excess=-27.47% sharpe=0.333 reject_flag=False
- `7657564f` [walk_forward] 2020-09-01..2024-12-31 excess=-3.42% sharpe=1.554 reject_flag=True
- `83d3ae94` [walk_forward] 2023-01-02..2024-12-31 excess=+47.68% sharpe=2.937 reject_flag=False
- `93cce116` [walk_forward] 2023-01-02..2024-12-31 excess=+47.68% sharpe=2.937 reject_flag=False
- `b8e559b6` [walk_forward] 2016-06-01..2022-12-30 excess=-7.37% sharpe=0.109 reject_flag=False
- `d95de827` [walk_forward] 2023-01-02..2024-12-31 excess=+18.82% sharpe=2.696 reject_flag=False
- `f0e341cf` [walk_forward] 2016-06-01..2024-12-31 excess=+0.85% sharpe=0.813 reject_flag=True

## Unresolved data limitations

- no constituent-level data — capacity/liquidity constraints not evaluable on real data
- price indices only — dividends not included (understates high-yield sector momentum, notably Banking)
- risk-free rate placeholder 0% — NGN T-bill yields not applied
- NGX Premium index unavailable from this provider; Consumer Goods from 2018-12, Industrial from 2020-02, Pension from 2021-06 only
- 2023-06 excluded across five sector indices (synchronized >15% jumps coinciding with FX liberalization; unverified, therefore dropped)
- catalyst/event data not yet ingested from a real source — the catalyst filter variant is untested on real data

## Reproduction recipe

1. `python scripts/ingest_investing.py` (same provider, new vintage — note investing.com may restate history; the as_of/vintage axis captures this)
2. For any experiment id: load its `config_json` from the registry and run `ngxrot.runner.run_resolved(json.loads(config_json))`
3. Deterministic engines + recorded seeds => bit-identical metrics (verified in-session for the full engine sweep)