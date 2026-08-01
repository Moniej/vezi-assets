"""Automated safeguard, added 2026-08-01 after a real incident
(docs/fre_runs/incident_2026-08-01_prod_db_wipe.md): scripts/phase1_smoke_test.py
and scripts/dal_demo.py each hardcoded the literal production database path
(data/ngx.sqlite) and unconditionally called `.unlink()` on it, which wiped
the real, populated production database when re-run.

This is a mechanical, permanent check -- NOT relying on a developer
remembering to grep for the pattern by hand next time. It scans every .py
file under scripts/ (recursively) and fails if any file combines a literal
quoted reference to "ngx.sqlite" with a `.unlink(` call in the same file --
exactly the shape of both incident scripts. The two known culprits were
fixed to use db.new_scratch_db_path() instead (which contains neither
substring), so this check should currently report zero violations; it
exists to catch a THIRD recurrence automatically, not to re-flag the two
already-fixed scripts.

Known limitation, disclosed rather than hidden: this is a substring/pattern
check, not a semantic analyzer. A sufficiently indirect reconstruction of
the production path (e.g. string concatenation split across variables)
could evade it. It is a mechanical safety net layered on top of -- not a
replacement for -- DEFAULT_DB's NGXROT_DB_PATH environment override and the
new_scratch_db_path()/assert_not_default_db() helpers in src/ngxrot/db.py.

  python scripts/check_db_safety.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
SELF = Path(__file__).resolve()

DANGEROUS_PATH_MARKERS = ('"ngx.sqlite"', "'ngx.sqlite'")
DANGEROUS_UNLINK_MARKER = ".unlink("


def find_violations() -> list[str]:
    violations = []
    for path in sorted(SCRIPTS_DIR.rglob("*.py")):
        if path.resolve() == SELF:
            continue
        text = path.read_text(encoding="utf-8")
        has_path = any(marker in text for marker in DANGEROUS_PATH_MARKERS)
        has_unlink = DANGEROUS_UNLINK_MARKER in text
        if has_path and has_unlink:
            violations.append(str(path.relative_to(ROOT)))
    return violations


def main() -> int:
    violations = find_violations()
    if violations:
        print("DB SAFETY CHECK: FAIL -- found script(s) combining a hardcoded "
              "\"ngx.sqlite\" path with a destructive .unlink() call:")
        for v in violations:
            print(f"  - {v}")
        print("\nFix: use ngxrot.db.new_scratch_db_path() instead of hardcoding "
              "the production database path (see src/ngxrot/db.py).")
        return 1
    print("DB SAFETY CHECK: PASS -- no script hardcodes the production "
          "database path alongside a destructive unlink.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
