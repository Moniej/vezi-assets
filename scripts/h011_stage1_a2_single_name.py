"""Stage 1 / A-2 — single-name concentration diagnostic for H-011.

Uses the generic ``single_name_dependency`` check just added to
failure_conditions.py (applies to any future cross-sectional hypothesis,
not hard-coded to H-011). Runs H-011's UNCHANGED base configuration
through the normal runner.run_resolved path — same signal, same
portfolio construction, same PIT/vintage/confidence rules — so the new
check's result is persisted in the immutable experiment registry exactly
like every other reported metric, under H-011's own hypothesis_id.

Only ``experiment.name``/``experiment.stage`` are set here to label this
as a diagnostic re-evaluation, not a new result — the same bookkeeping-
only pattern every Phase 4 stability/walk-forward run already uses
(configs/h011_size.toml itself, docs/PREREG_H-011.md, and H-011's signal/
portfolio/data sections are read but never written).
"""

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import runner  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "h011_size.toml"


def run_diagnostic(label, sim_start, sim_end, stage):
    base = runner.load_config(CONFIG_PATH)
    cfg = copy.deepcopy(base)
    cfg["experiment"]["name"] = f"a2_single_name_diagnostic_{label}"
    cfg["experiment"]["stage"] = stage
    cfg["data"]["sim_start"], cfg["data"]["sim_end"] = sim_start, sim_end
    r = runner.run_resolved(cfg, label=f"A-2 {label}")
    snd = r["flags"]["failure_conditions"]["single_name_dependency"]
    print(f"\n=== {label} ({sim_start} to {sim_end}) — exp_id {r['exp_id'][:8]} ===")
    print(f"  triggered: {snd['triggered']}")
    print(f"  evidence : {snd['evidence']}")
    return r["exp_id"], snd


def main():
    results = {}
    exp_id, snd = run_diagnostic("dev", "2016-01-02", "2024-12-31", "development")
    results["dev"] = {"exp_id": exp_id, **snd}
    exp_id, snd = run_diagnostic("oos_2025_26", "2025-01-02", "2026-06-30", "final_oos")
    results["oos_2025_26"] = {"exp_id": exp_id, **snd}

    threshold = 0.25
    print(f"\nThreshold used: max_single_name_share = {threshold:.0%} "
          f"(code default, configs/h011_size.toml NOT modified — no "
          f"[failure_conditions] key added for this run)")
    for label, r in results.items():
        verdict = "FAIL" if r["triggered"] else "PASS"
        print(f"  {label}: {verdict} — top name {r.get('top_name')} "
              f"share={r.get('top_name_share')} top3={r.get('top3_share')}")


if __name__ == "__main__":
    main()
