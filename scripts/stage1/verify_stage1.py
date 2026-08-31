"""Canonical pre-Stage-2 verification; never writes a live database."""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys


def sha256_or_absent(path: pathlib.Path) -> str:
    if not path.exists():
        return "ABSENT"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(name: str, command: list[str], *, root: pathlib.Path, env: dict[str, str]) -> bool:
    result = subprocess.run(command, cwd=root, env=env, check=False)
    print(f"{'PASS' if result.returncode == 0 else 'FAIL'} {name}")
    return result.returncode == 0


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    runtime = root / ".test-runtime"
    live = [root / "data" / "ngx.sqlite", root / "data" / "registry.sqlite", root / "data" / "portfolio.sqlite"]
    before = {path: sha256_or_absent(path) for path in live}
    checks = [
        ("Stage 1 contracts, invariants, migrations, fixture integrity", [sys.executable, "-m", "unittest", "discover", "-s", "tests/stage1"]),
        ("Stage 2A canonical identity migration/resolver", [sys.executable, "-m", "unittest", "tests.stage2.test_canonical_identity"]),
        ("Stage 2B Research OS canonical identity lookup", [sys.executable, "-m", "unittest", "tests.stage2.test_research_identity_lookup"]),
        ("Stage 2C Research OS canonical identity persistence", [sys.executable, "-m", "unittest", "tests.stage2.test_research_identity_persistence"]),
        ("Stage 2D Research OS canonical-preferred reads", [sys.executable, "-m", "unittest", "tests.stage2.test_research_identity_preferred_reads"]),
        ("H-011 frozen liquidity comparison fixture", [sys.executable, "-m", "unittest", "tests.stage2.test_h011_liquidity_fixture"]),
        ("H-024 frozen pre-outcome dataset guards", [sys.executable, "-m", "unittest", "tests.stage2.test_h024_dataset"]),
        ("Historical identity reconstruction assertions", [sys.executable, "-m", "unittest", "tests.stage2.test_historical_identity"]),
        ("Historical identity Phase 1 evidence/coverage fixture", [sys.executable, "-m", "unittest", "tests.stage2.test_historical_identity_phase1_fixture"]),
        ("Historical market-data identity semantics audit", [sys.executable, "-m", "unittest", "tests.stage2.test_historical_market_identity_semantics"]),
        ("Historical universe reconstruction and continuity audit", [sys.executable, "-m", "unittest", "tests.stage2.test_historical_universe_reconstruction"]),
        ("FRE frozen financial-ratio regression", [sys.executable, "scripts/fre/test_financial_ratios.py", "--temp-dir", str(runtime)]),
        ("Research OS frozen regression", [sys.executable, "scripts/test_research_memory.py"]),
        ("Alpha governance regression", [sys.executable, "-m", "unittest", "tests.stage1.test_stage1_contracts"]),
        ("Portfolio paper-only frozen integration", [sys.executable, "scripts/portfolio/test_integration_e2e.py", "--temp-dir", str(runtime)]),
    ]
    outcomes = [run(name, command, root=root, env=env) for name, command in checks]
    after = {path: sha256_or_absent(path) for path in live}
    unchanged = before == after
    print(f"{'PASS' if unchanged else 'FAIL'} live database immutability")
    for path in live:
        print(f"  {path.name}: {before[path]} -> {after[path]}")
    return 0 if all(outcomes) and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
