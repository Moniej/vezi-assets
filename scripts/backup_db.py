"""Timestamped backup/restore-test for both live databases (production-
reliability audit, 2026-08-12, Priority H / Finding F).

Two databases hold accumulated, non-reproducible state:
  data/ngx.sqlite       -- market/document/FRE/monitoring data (db.DEFAULT_DB)
  data/registry.sqlite  -- experiment registry + research workspace state
                            (registry.REGISTRY_DB)

Both are *.sqlite*-gitignored, so neither is protected by git. The existing
ngx.sqlite.pre_*_backup_* files are manual, ad-hoc, pre-migration copies
living in the SAME data/ directory as the primary database -- a single
data/ loss event destroys the database and every one of those "backups"
together. This script is the automated, timestamped replacement: it uses
sqlite3's own backup API (safe against a concurrently-open writer, unlike
a raw file copy, which can capture a torn/inconsistent snapshot mid-write),
writes into backups/ (a sibling of data/, not inside it), verifies each
backup with PRAGMA integrity_check before counting it as successful, and
prunes to a retention count. Restoring never overwrites either live
database without an explicit --force flag (defense-in-depth, same
reasoning as db.assert_not_default_db) and always backs up the current
live database first when it does.

  python scripts/backup_db.py                       # take a backup of both DBs
  python scripts/backup_db.py --verify               # backup + full restore-test (default target: scratch dir)
  python scripts/backup_db.py --list                 # list existing snapshots
  python scripts/backup_db.py --restore TIMESTAMP --target ngx --force
                                                       # restore data/ngx.sqlite from a snapshot (destructive; backs up
                                                       # current live file first)
  python scripts/backup_db.py --keep 10               # retention count (default 10 snapshots)
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402
from ngxrot import registry  # noqa: E402

BACKUP_ROOT = ROOT / "backups"
DATABASES = {"ngx": db.DEFAULT_DB, "registry": registry.REGISTRY_DB}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sqlite_backup(src_path: Path, dst_path: Path) -> None:
    """Uses sqlite3's own online backup API -- safe to run against a
    database that another process currently has open, unlike shutil.copy
    on a live file (which can copy a partially-written page and produce a
    corrupt snapshot)."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    src_con = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    dst_con = sqlite3.connect(dst_path)
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()


def _integrity_check(path: Path) -> tuple[bool, str]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        return result == "ok", result
    finally:
        con.close()


def _table_counts(path: Path) -> dict[str, int]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'").fetchall()]
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        con.close()


def cmd_backup(args) -> int:
    ts = _timestamp()
    snap_dir = BACKUP_ROOT / ts
    ok = True
    for name, src in DATABASES.items():
        if not src.exists():
            print(f"SKIP {name}: {src} does not exist")
            continue
        dst = snap_dir / f"{name}.sqlite"
        _sqlite_backup(src, dst)
        valid, result = _integrity_check(dst)
        size_kb = dst.stat().st_size / 1024
        print(f"{'OK  ' if valid else 'FAIL'} {name}: {src} -> {dst} "
              f"({size_kb:.0f} KB, integrity_check={result})")
        ok = ok and valid
    if not ok:
        print("BACKUP FAILED integrity check -- see above", file=sys.stderr)
        return 1
    print(f"\nSnapshot: {snap_dir}")
    _prune(args.keep)
    return 0


def _prune(keep: int) -> None:
    if not BACKUP_ROOT.exists():
        return
    snapshots = sorted((p for p in BACKUP_ROOT.iterdir() if p.is_dir()), reverse=True)
    for stale in snapshots[keep:]:
        shutil.rmtree(stale)
        print(f"pruned old snapshot: {stale.name}")


def cmd_list(args) -> int:
    if not BACKUP_ROOT.exists():
        print("(no backups yet)")
        return 0
    snapshots = sorted((p for p in BACKUP_ROOT.iterdir() if p.is_dir()), reverse=True)
    if not snapshots:
        print("(no backups yet)")
        return 0
    for snap in snapshots:
        files = sorted(p.name for p in snap.iterdir())
        print(f"{snap.name}: {files}")
    return 0


def cmd_verify(args) -> int:
    """Full restore test: take a backup, restore each database from it into
    a throwaway scratch location (db.new_scratch_db_path() -- never the
    live path), and compare per-table row counts + integrity_check against
    the live source. This is the actual "can we get our data back" proof,
    not just "did the copy not crash"."""
    rc = cmd_backup(args)
    if rc != 0:
        return rc
    snap_dir = sorted((p for p in BACKUP_ROOT.iterdir() if p.is_dir()), reverse=True)[0]
    all_ok = True
    for name, src in DATABASES.items():
        backup_path = snap_dir / f"{name}.sqlite"
        if not backup_path.exists():
            continue
        scratch = db.new_scratch_db_path()
        shutil.copy(backup_path, scratch)
        valid, result = _integrity_check(scratch)
        live_counts = _table_counts(src)
        restored_counts = _table_counts(scratch)
        counts_match = live_counts == restored_counts
        print(f"\n--- restore test: {name} ---")
        print(f"restored to scratch: {scratch}")
        print(f"integrity_check: {result}")
        print(f"table row counts match live source: {counts_match}")
        if not counts_match:
            for t in sorted(set(live_counts) | set(restored_counts)):
                lv, rv = live_counts.get(t), restored_counts.get(t)
                if lv != rv:
                    print(f"  MISMATCH {t}: live={lv} restored={rv}")
        all_ok = all_ok and valid and counts_match
        shutil.rmtree(scratch.parent, ignore_errors=True)
    print(f"\nRESTORE TEST: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


def cmd_restore(args) -> int:
    if args.target not in DATABASES:
        print(f"--target must be one of {list(DATABASES)}", file=sys.stderr)
        return 1
    snap_dir = BACKUP_ROOT / args.restore
    backup_path = snap_dir / f"{args.target}.sqlite"
    if not backup_path.exists():
        print(f"no such snapshot file: {backup_path}", file=sys.stderr)
        return 1
    live_path = DATABASES[args.target]
    if not args.force:
        print(f"Refusing to restore over {live_path} without --force "
              f"(this OVERWRITES the live database).", file=sys.stderr)
        print(f"Would restore from: {backup_path}", file=sys.stderr)
        return 1
    valid, result = _integrity_check(backup_path)
    if not valid:
        print(f"Refusing to restore -- backup fails integrity_check: {result}", file=sys.stderr)
        return 1
    if live_path.exists():
        safety_dir = BACKUP_ROOT / f"pre_restore_{_timestamp()}"
        safety_dir.mkdir(parents=True, exist_ok=True)
        _sqlite_backup(live_path, safety_dir / f"{args.target}.sqlite")
        print(f"safety snapshot of current live {args.target} taken: {safety_dir}")
    shutil.copy(backup_path, live_path)
    print(f"RESTORED {args.target}: {backup_path} -> {live_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--keep", type=int, default=10, help="retention: snapshots to keep (default 10)")
    p.add_argument("--verify", action="store_true", help="backup + full restore test")
    p.add_argument("--list", action="store_true", help="list existing snapshots")
    p.add_argument("--restore", metavar="TIMESTAMP", default=None,
                   help="restore --target from this snapshot (see --list)")
    p.add_argument("--target", choices=list(DATABASES), default=None)
    p.add_argument("--force", action="store_true", help="required to actually overwrite a live database")
    args = p.parse_args()

    if args.list:
        return cmd_list(args)
    if args.restore:
        if not args.target:
            print("--restore requires --target", file=sys.stderr)
            return 1
        return cmd_restore(args)
    if args.verify:
        return cmd_verify(args)
    return cmd_backup(args)


if __name__ == "__main__":
    sys.exit(main())
