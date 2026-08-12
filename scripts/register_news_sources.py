"""Register secondary-source (news) infrastructure (2026-08-11, HANDOFF.md,
Priority 4: OS infrastructure only, no alpha-path involvement).

Does three things, each idempotent:

1. Creates `sources` rows for Nairametrics and MarketForces Africa
   (kind='vendor', reliability='secondary' -- the same classification
   this platform already gives ngx_pulse, a real aggregator/vendor, not
   an exchange-official feed).
2. Creates `news_outlets` rows for both, with PROPOSED reliability_tier/
   base_confidence values (see PROPOSED_OUTLETS below) -- disclosed as
   proposed, not asserted as an owner-confirmed final judgment; correct
   them directly in the table if the actual values should differ.
3. Registers the 26 real, already-staged news articles in
   `data/staging/news_text/` as real `documents` rows (doc_type='news',
   source_type='news') -- metadata only, NO extraction. `extract_document()`
   is NOT called here: no GEMINI_API_KEY is configured in this
   environment's .env, so no LLM call is possible right now. These
   documents are real, dated, ticker-mapped, and ready for extraction the
   moment a key is available -- extraction is a distinct, disclosed next
   step, not silently skipped.

Explicitly NOT done here (disclosed, not silently deferred):
- No live scraping of Nairametrics/MarketForces beyond what STAGE10A/10B
  already did (those articles are the ones staged in data/staging/news_text/).
- No ngx_pulse fetch_corporate_actions/fetch_events (disclosures) live
  ingestion -- both corporate_actions and events are live inputs to
  engine_full.py/runner.py/backtest_xs.py (the Alpha Engine), and
  populating them for real needs the same explicit alpha-safety decision
  the dividend load required (see scripts/load_real_corporate_actions_dividends.py).

Ticker mapping is an explicit, hand-verified dict (never guessed/fuzzy-
matched) -- every ticker below was confirmed to exist in `securities`
before this script was written.

  PYTHONPATH=src python scripts/register_news_sources.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ngxrot import db  # noqa: E402

NEWS_TEXT_DIR = ROOT / "data" / "staging" / "news_text"

# PROPOSED, not owner-confirmed -- see module docstring. Both sources
# passed STAGE10A/10B's access-policy check (open robots.txt, no AI-crawler
# block) and showed real, verified NGX ticker-level coverage including small/
# illiquid names other sources missed entirely. Tier 3 = "secondary_reputable"
# (vocab.EVIDENCE_TRUST_TIERS) -- editorially real Nigerian financial-news
# outlets, not primary filings and not unverified/AI-derived either.
PROPOSED_OUTLETS = {
    "Nairametrics": {"reliability_tier": 3, "base_confidence": 0.5, "covers_ngx_directly": 1},
    "MarketForces Africa": {"reliability_tier": 3, "base_confidence": 0.5, "covers_ngx_directly": 1},
}

# filename prefix -> (ticker, outlet_name). Every ticker hand-verified to
# exist in `securities` before this script was written -- never fuzzy-matched.
FILE_TICKER_MAP = {
    "caverton_fy2024.txt": "CAVERTON",
    "caverton_h1_2026_loss.txt": "CAVERTON",
    "cileasing_coo_appointment.txt": "CILEASING",
    "cileasing_q1_2026.txt": "CILEASING",
    "cutix_fy2026_loss.txt": "CUTIX",
    "deapcap_name_change.txt": "DEAPCAP",
    "lasaco_rights_issue.txt": "LASACO",
    "legendint_spectranet_merger.txt": "LEGENDINT",
    "mcnichols_dividend_2025.txt": "MCNICHOLS",
    "ncr_2025_turnaround.txt": "NCR",
    "prestige_h1_2026.txt": "PRESTIGE",
    "redstarex_logistics_merger.txt": "REDSTAREX",
    "redstarex_q2_2025.txt": "REDSTAREX",
    "regalins_capital_raise_completion.txt": "REGALINS",
    "regalins_suspension.txt": "REGALINS",
    "royalex_chairman_appointment.txt": "ROYALEX",
    "royalex_nexamont_stake.txt": "ROYALEX",
    "rtbriscoe_capital_raise.txt": "RTBRISCOE",
    "sunuassur_board_change.txt": "SUNUASSUR",
    "sunuassur_rights_issue.txt": "SUNUASSUR",
    "tantalizer_majority_shareholder.txt": "TANTALIZER",
    "tantalizer_ngx_warning.txt": "TANTALIZER",
    "tantalizer_ogidan_appointment.txt": "TANTALIZER",
    "univinsure_capital_raise.txt": "UNIVINSURE",
    "univinsure_ceo_appointment.txt": "UNIVINSURE",
    "veritaskap_chairman_election.txt": "VERITASKAP",
    "veritaskap_q1_2026.txt": "VERITASKAP",
}


def _parse_header(text: str) -> dict:
    """Every staged file carries a plain-text header: title line, then
    'Publication Date:'/'Author:'/'Source:'/'URL:' lines. Parsed, never
    inferred -- a missing field stays missing."""
    lines = text.splitlines()
    out = {"title": lines[0].strip() if lines else ""}
    for line in lines[1:8]:
        for key in ("Publication Date", "Author", "Source", "URL"):
            if line.startswith(f"{key}:"):
                out[key] = line[len(key) + 1:].strip()
    return out


def _to_iso_date(raw: str) -> str | None:
    raw = raw.split("(")[0].strip()  # strip "(excerpted from ...)"-style suffixes
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    con = db.init_db()

    # --- 1. sources rows -----------------------------------------------------
    outlet_source_id = {}
    for outlet_name in PROPOSED_OUTLETS:
        row = con.execute("SELECT source_id FROM sources WHERE name = ?", (outlet_name,)).fetchone()
        if row:
            outlet_source_id[outlet_name] = row[0]
            print(f"sources: {outlet_name!r} already registered (source_id={row[0]})")
            continue
        if args.dry_run:
            print(f"sources: would create {outlet_name!r}")
            outlet_source_id[outlet_name] = -1  # placeholder so the documents dry-run preview works
            continue
        cur = con.execute(
            "INSERT INTO sources (name, kind, reliability, base_confidence, notes) VALUES (?,?,?,?,?)",
            (outlet_name, "vendor", "secondary", PROPOSED_OUTLETS[outlet_name]["base_confidence"],
             "Secondary news source, added 2026-08-11 -- HANDOFF.md"))
        outlet_source_id[outlet_name] = cur.lastrowid
        print(f"sources: created {outlet_name!r} (source_id={cur.lastrowid})")

    # --- 2. news_outlets rows -------------------------------------------------
    for outlet_name, cfg in PROPOSED_OUTLETS.items():
        existing = con.execute(
            "SELECT outlet_id FROM news_outlets WHERE outlet_name = ?", (outlet_name,)).fetchone()
        if existing:
            print(f"news_outlets: {outlet_name!r} already registered")
            continue
        if args.dry_run:
            print(f"news_outlets: would create {outlet_name!r} tier={cfg['reliability_tier']}")
            continue
        con.execute(
            "INSERT INTO news_outlets (outlet_name, source_id, reliability_tier, base_confidence, "
            "covers_ngx_directly, notes) VALUES (?,?,?,?,?,?)",
            (outlet_name, outlet_source_id.get(outlet_name), cfg["reliability_tier"],
             cfg["base_confidence"], cfg["covers_ngx_directly"],
             "PROPOSED tier, 2026-08-11 -- confirm or correct, see module docstring"))
        print(f"news_outlets: created {outlet_name!r}")

    # --- 3. documents rows for the 26 staged articles --------------------------
    n_registered, n_skipped, n_missing_ticker = 0, 0, 0
    for fname in sorted(NEWS_TEXT_DIR.glob("*.txt")):
        local_path = str(fname.relative_to(ROOT))
        existing = con.execute("SELECT doc_id FROM documents WHERE local_path = ?",
                               (local_path,)).fetchone()
        if existing:
            n_skipped += 1
            continue
        ticker = FILE_TICKER_MAP.get(fname.name)
        if ticker is None:
            n_missing_ticker += 1
            print(f"documents: SKIPPED {fname.name} -- not in FILE_TICKER_MAP (never guessed)")
            continue
        text = fname.read_text(encoding="utf-8")
        meta = _parse_header(text)
        outlet_name = meta.get("Source")
        if outlet_name not in outlet_source_id:
            print(f"documents: SKIPPED {fname.name} -- unrecognized Source: {outlet_name!r}")
            continue
        filing_date = _to_iso_date(meta.get("Publication Date", "")) or datetime.now(
            timezone.utc).date().isoformat()
        if args.dry_run:
            print(f"documents: would register {fname.name} -> {ticker} ({outlet_name}, {filing_date})")
            n_registered += 1
            continue
        source_id = outlet_source_id[outlet_name]
        base_confidence = PROPOSED_OUTLETS[outlet_name]["base_confidence"]
        con.execute(
            "INSERT INTO documents (ticker, raw_symbol, doc_type, source_type, filing_date, "
            "retrieved_date, source_url, local_path, text_path, char_count, source_confidence, "
            "source_id, as_of_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ticker, ticker, "news", "news", filing_date,
             datetime.now(timezone.utc).date().isoformat(), meta.get("URL"), local_path, local_path,
             len(text), base_confidence, source_id, datetime.now(timezone.utc).date().isoformat()))
        n_registered += 1

    if not args.dry_run:
        con.commit()

    print(f"\ndocuments: {n_registered} registered this run, {n_skipped} already present "
          f"(idempotent skip), {n_missing_ticker} skipped for missing ticker mapping")
    if not args.dry_run:
        total_news_docs = con.execute(
            "SELECT COUNT(*) FROM documents WHERE doc_type = 'news'").fetchone()[0]
        print(f"documents: {total_news_docs} total doc_type='news' rows now in the database")
        print("\nNo extraction was run (no GEMINI_API_KEY configured) -- these documents are "
             "real, dated, ticker-mapped, and ready for extract_document() once a key is available.")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
