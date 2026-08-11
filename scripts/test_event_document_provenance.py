"""Standalone assertion-script test: every ticker-scoped `events` row that is
either (a) sourced from a `sources.kind='web_archive'` pipeline, or (b) has a
`source_url` on one of the two approved news-outlet domains, must have a
corresponding `documents` row with the same `source_url`.

Root cause this guards against (Stage 14 Round 4 + provenance investigation,
2026-08-08, docs/STAGE14_ROUND4_BLOCKER_INVESTIGATION_2026-08-08.md): the
event and document pipelines are architecturally independent -- nothing in
event_pipeline.py or schema.sql's `events` table requires or creates a
`documents` row when an event is ingested. Stage 11's news batch registered
documents for every article uniformly; Stage 12's news batch did so only for
its numeric-fact articles, silently leaving 4 event-shaped articles
(event_id 178-181, since backfilled -- see
docs/STAGE14_PROVENANCE_REMEDIATION_2026-08-08.md) without any document
provenance. This test makes that class of gap visible immediately rather
than requiring another manual audit to find it.

Two independent detection paths, deliberately: a round-6 review found that
scoping solely to `sources.kind='web_archive'` is bypassable -- nothing
requires a future news source to be registered with that specific kind value
(the platform's own `investing_com` source, non-news, already uses
`kind='vendor'`). Path (b), the domain allow-list, mirrors
docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md's Sec. 14D outlet-
normalization rule exactly (including using `.hostname`, not `.netloc`, for
the same port-number reason documented there) so a news article is still
caught by URL alone even if its source_id's `kind` is ever set incorrectly.

Deliberately a standalone check, not a schema constraint: `events` and
`documents` legitimately have no FK relationship for non-news sources (e.g.
CBN/MPC events, which never touch the documents/FSI layer at all), so this
is scoped narrowly to news-outlet rows, not a blanket rule.

  PYTHONPATH=src python scripts/test_event_document_provenance.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

# Same allow-list as STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md Sec. 14D.
_APPROVED_OUTLET_SUFFIXES = ("nairametrics.com", "dmarketforces.com")
# First-party regulator domains, added Stage 18 (2026-08-08) alongside the
# ngx_xcompliance_regco source (source_id=17, sources.kind='regulator') --
# same detection principle as the news-outlet allow-list above, not a second
# parallel mechanism.
_APPROVED_REGULATOR_SUFFIXES = ("ngxgroup.com",)

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if condition:
        passed += 1
    else:
        failed += 1


def _domain_in(source_url: str | None, suffixes: tuple[str, ...]) -> bool:
    if not source_url:
        return False
    host = urlparse(source_url).hostname
    if not host:
        return False
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == suf or host.endswith("." + suf) for suf in suffixes)


def is_approved_news_domain(source_url: str | None) -> bool:
    return _domain_in(source_url, _APPROVED_OUTLET_SUFFIXES)


def is_approved_regulator_domain(source_url: str | None) -> bool:
    return _domain_in(source_url, _APPROVED_REGULATOR_SUFFIXES)


def main() -> int:
    global passed, failed
    con = sqlite3.connect(ROOT / "data" / "ngx.sqlite")

    web_archive_source_ids = [
        r[0] for r in con.execute(
            "SELECT source_id FROM sources WHERE kind='web_archive'").fetchall()
    ]
    check("at least one web_archive source is registered (sanity check the "
          "test itself isn't vacuously trivial)", len(web_archive_source_ids) > 0,
          f"found source_ids={web_archive_source_ids}")

    regulator_source_ids = [
        r[0] for r in con.execute(
            "SELECT source_id FROM sources WHERE kind='regulator'").fetchall()
    ]

    all_ticker_events = con.execute(
        "SELECT event_id, ticker, event_type, source_id, source_url FROM events "
        "WHERE scope='ticker' AND source_url IS NOT NULL").fetchall()

    news_rows = [
        (event_id, ticker, event_type, source_url)
        for event_id, ticker, event_type, source_id, source_url in all_ticker_events
        if source_id in web_archive_source_ids or source_id in regulator_source_ids
        or is_approved_news_domain(source_url) or is_approved_regulator_domain(source_url)
    ]

    check("at least one ticker-scoped news-outlet/regulator event exists to check",
          len(news_rows) > 0, f"found {len(news_rows)} rows")

    orphans = []
    for event_id, ticker, event_type, source_url in news_rows:
        match = con.execute(
            "SELECT doc_id FROM documents WHERE source_url=?", (source_url,)
        ).fetchall()
        if not match:
            orphans.append((event_id, ticker, event_type, source_url))

    check(
        f"every ticker-scoped news-outlet/regulator event ({len(news_rows)} checked, "
        f"via kind='web_archive'/'regulator' OR approved-domain match) has a matching "
        f"documents row by exact source_url",
        len(orphans) == 0,
        f"{len(orphans)} orphaned event(s): {orphans}",
    )

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
