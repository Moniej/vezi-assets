"""Regression test for scripts/ngxrot_workspace.py (2026-08-11,
HANDOFF.md, Priority 8). Runs the real CLI via subprocess against the
real production database/registry (same convention as
scripts/ngxrot_research.py itself has no scratch-DB mode) -- every
project created here is archived at the end so nothing lingers as
apparent real research. Does NOT touch the alerts table (see
scripts/test_alerts_cli.py for that, tested against a scratch DB only,
since alert acknowledgment is a one-way, real-world-meaningful state
change that must never be exercised against real alerts).

  PYTHONPATH=src python scripts/test_workspace_cli.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
ENV_PYTHONPATH = str(ROOT / "src")

passed = 0
failed = 0


def check(name: str, condition: bool) -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if condition:
        passed += 1
    else:
        failed += 1


def run(*args: str) -> subprocess.CompletedProcess:
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = ENV_PYTHONPATH
    return subprocess.run([PY, "-u", str(ROOT / "scripts" / "ngxrot_workspace.py"), *args],
                          capture_output=True, text=True, env=env, timeout=60)


def main() -> int:
    r = run("create", "--title", "CLI regression test", "--question",
            "Does scripts/ngxrot_workspace.py work end to end?")
    check("create: exits 0", r.returncode == 0)
    research_id = r.stdout.split()[1] if r.returncode == 0 else None
    check("create: prints a real RP- research_id", bool(research_id) and research_id.startswith("RP-"))

    r = run("note", "--id", research_id, "--type", "observation", "--content", "CLI test note")
    check("note: exits 0 and returns a NOTE- id", r.returncode == 0 and r.stdout.strip().startswith("NOTE-"))

    r = run("market-evidence", "--id", research_id, "--type", "dataset_observation",
           "--ref", json.dumps({"ticker": "GTCO", "trade_date": "2026-01-05"}),
           "--description", "CLI test evidence")
    check("market-evidence: exits 0 and returns an EV- id",
         r.returncode == 0 and r.stdout.strip().startswith("EV-"))

    r = run("doc-evidence", "--id", research_id, "--query-type", "facts", "--symbol", "NASCON")
    check("doc-evidence: exits 0, real query attached, real evidence recorded",
         r.returncode == 0 and "query_id=" in r.stdout and "evidence_id=EV-" in r.stdout)

    r = run("finding", "--id", research_id, "--title", "CLI test finding",
           "--statement", "The CLI can record findings.")
    check("finding: exits 0 and returns a FIND- id",
         r.returncode == 0 and r.stdout.strip().startswith("FIND-"))

    r = run("hypothesis", "--id", research_id, "--statement", "CLI test hypothesis, not a real claim.")
    check("hypothesis: exits 0 and returns a HYP- id", r.returncode == 0 and r.stdout.strip().startswith("HYP-"))

    r = run("completeness", "--id", research_id)
    check("completeness: exits 0 and returns real JSON with NASCON in tickers_missing_document_context "
         "(only 'facts' was attached, not 'document_context')",
         r.returncode == 0 and "NASCON" in json.loads(r.stdout)["tickers_missing_document_context"])

    r = run("integrity", "--id", research_id)
    check("integrity: exits 0 and surfaces the same completeness gap as a warning line",
         r.returncode == 0 and "NASCON" in r.stdout)

    r = run("snapshot", "--id", research_id)
    check("snapshot: exits 0 and returns a real SNAP- id", r.returncode == 0 and r.stdout.strip().startswith("SNAP-"))

    r = run("export", "--id", research_id, "--format", "markdown")
    check("export: exits 0 and produces a real Markdown report containing the research question",
         r.returncode == 0 and "Does scripts/ngxrot_workspace.py work end to end?" in r.stdout)

    r = run("list", "--status", "DRAFT")
    check("list: exits 0 and includes this project", r.returncode == 0 and research_id in r.stdout)

    r = run("show", "--id", research_id)
    check("show: exits 0 and reports real, non-zero counts",
         r.returncode == 0 and "evidence recorded: 2" in r.stdout)

    r = run("archive", "--id", research_id, "--reason", "regression test complete")
    check("archive: exits 0 (cleans up -- this project no longer looks like live research)",
         r.returncode == 0 and "archived" in r.stdout)

    r = run("note", "--id", research_id, "--type", "observation", "--content", "should be rejected")
    check("archive: further mutation via the CLI is correctly rejected (exit 1)", r.returncode == 1)

    print()
    print(f"{passed}/{passed + failed} checks passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
