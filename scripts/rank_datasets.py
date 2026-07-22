"""Regenerate the data-moat priority ranking from configs/dataset_priorities.toml.

  python scripts/rank_datasets.py
"""

import sys
import tomllib
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
cfg = tomllib.loads((ROOT / "configs" / "dataset_priorities.toml")
                    .read_text(encoding="utf-8"))

rows = []
for key, d in cfg.items():
    score = d["gen"] * d["uniqueness"] * d["replication"] * d["maintenance"] * d["coverage"]
    rows.append({
        "dataset": d["name"], "key": key, "mechanism": d.get("mechanism", "?"),
        "GEN": d["gen"], "families": ",".join(d.get("families", [])),
        "U": d["uniqueness"], "R": d["replication"],
        "M": d["maintenance"], "C": d["coverage"], "score": score,
        "necessity": d.get("necessity", False),
        "notes": d.get("notes", ""),
    })
df = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
df.index += 1

lines = [f"# Data Moat Priority Ranking — {date.today().isoformat()}",
         "",
         "Objective: maximize decade-rate of alpha discovery. Priority = "
         "GENERATIVITY x Uniqueness x Replication-difficulty x Maintenance "
         "(inverted cost) x Coverage, each 1-5. Generativity must trace to "
         "named hypothesis families in `docs/HYPOTHESIS_FAMILY_MAP.md`. "
         "Scores and rationale live in `configs/dataset_priorities.toml`; "
         "edit there and rerun this script.",
         "", "| # | dataset | mech | GEN | families | U | R | M | C | score | necessity |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
for i, r in df.iterrows():
    lines.append(f"| {i} | {r.dataset} | {r.mechanism} | {r.GEN} | {r.families} "
                 f"| {r.U} | {r.R} | {r.M} | {r.C} | **{r.score}** | "
                 f"{'yes' if r.necessity else ''} |")
lines += ["", "## Gates and notes", ""]
for _, r in df.iterrows():
    if r.notes:
        lines.append(f"- **{r.key}**: {r.notes}")
lines += ["", "## Reading the ranking",
          "",
          "- Moat assets (M1/M2/M3) are ranked by score and acquired top-down.",
          "- `necessity` rows are table stakes for active research: acquired "
          "early regardless of score, never mistaken for edge.",
          "- Coverage for forward-capture assets (M1) rises mechanically with "
          "time — their scores are understated today and grow every trading "
          "day the capture job runs. This is the argument for starting them "
          "immediately."]
out = ROOT / "reports" / "data_moat_ranking.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(df[["dataset", "mechanism", "score", "necessity"]].to_string())
print(f"\nwritten: {out}")
