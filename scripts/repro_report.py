"""Generate the final reproducibility report for a hypothesis.

  python scripts/repro_report.py [H-001]

Everything comes from the immutable registry — the report is a view, not a
narrative. Another researcher reproduces any experiment by: checking out the
code at the listed fingerprint, loading the stored config_json, and running
runner.run_resolved on a database built from the same provider at the same
vintage.
"""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ngxrot import registry  # noqa: E402

HYP = sys.argv[1] if len(sys.argv) > 1 else "H-001"
ROOT = Path(__file__).resolve().parents[1]

reg = registry.connect_registry()
exps = pd.read_sql(
    "SELECT e.* FROM experiments e JOIN hypothesis_experiments he "
    "ON e.experiment_id = he.experiment_id WHERE he.hypothesis_id = ?",
    reg, params=(HYP,))
hyp = pd.read_sql("SELECT * FROM hypotheses WHERE hypothesis_id = ?",
                  reg, params=(HYP,)).iloc[0]

real = exps[exps.provider == "investing_com"]
flags_real = [json.loads(f) for f in real.validation_flags]
unresolved = sorted({
    lim for f in flags_real for lim, active in [
        ("price indices only — dividends not included (understates high-yield "
         "sector momentum, notably Banking)", f.get("price_index_only_no_dividends")),
        ("risk-free rate placeholder 0% — NGN T-bill yields not applied",
         f.get("risk_free_rate_is_placeholder")),
        ("no constituent-level data — capacity/liquidity constraints not "
         "evaluable on real data", not f.get("liquidity_constraint_enforced", False)),
    ] if active})

lines = [
    f"# Reproducibility Report — {HYP}",
    f"\nGenerated {date.today().isoformat()}. Source of truth: "
    f"`data/registry.sqlite` (immutable) + `experiments/*.json` snapshots.\n",
    f"## Hypothesis\n\n{hyp.description}\n",
    f"- status: **{hyp.status}**"
    + (f" (resolved {hyp.resolved_at})" if hyp.resolved_at else ""),
    f"- conclusion: {hyp.conclusion or '(pending)'}\n",
    "## Experiment inventory\n",
    f"- total experiments: **{len(exps)}**",
]
by = exps.groupby(["provider", "stage"]).size()
for (prov, stage), n in by.items():
    lines.append(f"  - {prov} / {stage}: {n}")
lines += [
    f"- code fingerprints used: "
    f"{', '.join(sorted(exps.code_fingerprint.unique()))}",
    f"- config files: "
    f"{', '.join(sorted(p for p in exps.config_path.dropna().unique()))}",
    f"- distinct resolved-config hashes: {exps.config_hash.nunique()} "
    f"(full config stored verbatim per experiment)",
    "\n## Evidence-grade (real data) runs\n",
    f"- provider: investing_com (aggregator, base confidence 0.5)",
    f"- data vintage (as_of): "
    f"{', '.join(sorted({json.loads(c)['data'].get('vintage') or 'latest (ingested 2026-07-15)' for c in real.config_json}))}",
    f"- confidence floor: "
    f"{', '.join(str(v) for v in sorted(real.min_confidence.unique()))}",
    f"- RNG: {', '.join(sorted(real.rng_algorithm.dropna().unique()))}, seeds "
    f"{sorted(int(s) for s in real.rng_seed.dropna().unique())}, placebo "
    f"iterations {sorted(int(i) for i in real.rng_iterations.dropna().unique() if i)}",
    f"- anchor cross-reference: NGXASI verified at 3 independent year-end "
    f"values (see data/reference_anchors.csv); staging validation report: "
    f"reports/data_completeness_2026-07-15.md",
    "\n## Validation status (real data, both pre-registered variants)\n",
]
for _, e in real[real.stage.isin(["walk_forward", "final_oos"])].iterrows():
    m, f = json.loads(e.metrics), json.loads(e.validation_flags)
    lines.append(
        f"- `{e.experiment_id[:8]}` [{e.stage}] {e.sim_start}..{e.sim_end} "
        f"excess={m.get('excess_return_ann'):+.2%} sharpe={m.get('sharpe_vs_rf')} "
        f"reject_flag={f.get('hypothesis_reject_recommended')}")
lines += [
    "\n## Unresolved data limitations\n",
    *[f"- {u}" for u in unresolved],
    "- NGX Premium index unavailable from this provider; Consumer Goods from "
    "2018-12, Industrial from 2020-02, Pension from 2021-06 only",
    "- 2023-06 excluded across five sector indices (synchronized >15% jumps "
    "coinciding with FX liberalization; unverified, therefore dropped)",
    "- catalyst/event data not yet ingested from a real source — the catalyst "
    "filter variant is untested on real data",
    "\n## Reproduction recipe\n",
    "1. `python scripts/ingest_investing.py` (same provider, new vintage — "
    "note investing.com may restate history; the as_of/vintage axis captures this)",
    "2. For any experiment id: load its `config_json` from the registry and "
    "run `ngxrot.runner.run_resolved(json.loads(config_json))`",
    "3. Deterministic engines + recorded seeds => bit-identical metrics "
    "(verified in-session for the full engine sweep)",
]
out = ROOT / "reports" / f"reproducibility_{HYP}.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"written: {out}")
print(f"\nexperiments: {len(exps)} | real-data: {len(real)} | "
      f"fingerprints: {exps.code_fingerprint.nunique()}")
