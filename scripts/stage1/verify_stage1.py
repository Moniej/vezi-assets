"""Canonical developer/CI verification command for Stage 1."""

from __future__ import annotations

import pathlib
import subprocess
import sys


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[2]
    env = dict(__import__("os").environ, PYTHONPATH=str(root / "src"))
    command = [sys.executable, "-m", "unittest", "tests.stage1.test_stage1_contracts"]
    return subprocess.run(command, cwd=root, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
