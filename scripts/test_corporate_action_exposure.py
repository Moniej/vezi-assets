"""Stage 1 / A-3 regression test — corporate-action exposure detection.

Standalone assert-based test, matching this platform's existing
convention (scripts/test_company_intelligence.py, phase1_smoke_test.py)
rather than pytest. Documents, executably, the CURRENT measured state of
a real, previously-undisclosed-for-H-011 risk:

  H-011's own engine (backtest_xs.py) has no bonus/scrip/rights price
  adjustment (confirmed: docs/METHODOLOGY_HARDENING_2026-08-04.md, and
  re-confirmed here by grep — zero adjustment call sites). No real,
  verified bonus/scrip event with a clean ratio+ex-date exists anywhere
  in this platform's data (corporate_actions has zero real rows; the one
  narrative bonus-issue fact has no usable ratio) — so no fix is
  implemented here; fabricating a ratio would be worse than the gap it
  claims to close.

This test instead locks in the one thing that IS knowable without
fabrication: which of H-011's own actual holding-period/ticker pairs
overlap a real ``unexplained_jump`` diagnostic flag. If a future data
refresh or diagnostic change alters this count, the test fails and forces
a human to look — it is a tripwire, not a correctness proof.

Run: python scripts/test_corporate_action_exposure.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import backtest_xs, corporate_action_audit, db, runner  # noqa: E402


def test_no_adjustment_call_sites():
    """Documents current behavior: backtest_xs.py (H-011's engine) does not
    reference corporate_actions or any adjustment factor. Fails loudly if
    that ever silently changes without this test being updated."""
    src = (ROOT / "src" / "ngxrot" / "backtest_xs.py").read_text(encoding="utf-8")
    # A bare mention (e.g. a docstring note contrasting with the real,
    # PIT-safe dividend source) is fine; an actual QUERY against the table
    # would mean adjustment logic was added and this disclosure is stale.
    assert "FROM corporate_actions" not in src, (
        "backtest_xs.py now QUERIES corporate_actions — bonus/scrip "
        "adjustment behavior may have changed; update this test and "
        "docs/METHODOLOGY_HARDENING_2026-08-04.md's disclosure together.")
    print("PASS: backtest_xs.py has no corporate_actions QUERY "
          "(no adjustment mechanism — matches disclosed limitation; a "
          "bare docstring mention, if any, is not itself a query)")


def test_h011_holding_period_exposure():
    """Real, computed (not fabricated) count of H-011's own holding
    periods that overlap an unexplained_jump flag, across dev+OOS."""
    con = db.init_db(ROOT / "data" / "ngx.sqlite")
    base = runner.load_config(ROOT / "configs" / "h011_size.toml")
    import copy
    cfg = copy.deepcopy(base)
    cfg["data"]["sim_start"], cfg["data"]["sim_end"] = "2016-01-02", "2026-06-30"

    panel = backtest_xs.load_panel(con, cfg)
    panel["mcap"] = backtest_xs.load_market_cap_panel(panel["close_ff"])
    scores = backtest_xs.size_scores(con, panel, cfg)
    close = panel["close_ff"]
    targets = backtest_xs.targets_from_scores(
        scores, close.loc[:cfg["data"]["sim_end"]].index, 20, 1)

    holdings = corporate_action_audit.holding_periods_from_targets(
        targets, cfg["data"]["sim_end"])
    hits = corporate_action_audit.unexplained_jump_exposure(
        con, holdings, cfg["data"]["sim_start"], cfg["data"]["sim_end"])

    print(f"H-011 holding-period / unexplained_jump overlaps: {len(hits)}")
    if len(hits):
        print(hits.to_string(index=False))

    # Tripwire, not a pass/fail correctness bar: as of 2026-08-08, exactly
    # 5 overlaps are known and disclosed (CILEASING 2024-01-05, IMG
    # 2023-12-29, LASACO 2021-02-22, PRESTIGE 2018-06-08, PRESTIGE
    # 2018-11-28 — see reports/H011_STAGE1_A3_CORPORATE_ACTIONS_2026-08-08.md).
    # A DIFFERENT count means either the price panel, the IRU membership,
    # or the diagnostic log changed since — investigate before assuming
    # this is fine.
    known_count = 5
    assert len(hits) == known_count, (
        f"expected {known_count} known overlaps, got {len(hits)} — "
        f"underlying data or diagnostics changed; re-audit before trusting "
        f"H-011's return series unchanged")
    print(f"PASS: matches the {known_count} previously-audited overlaps")


if __name__ == "__main__":
    test_no_adjustment_call_sites()
    test_h011_holding_period_exposure()
    print("\nAll A-3 regression checks passed.")
