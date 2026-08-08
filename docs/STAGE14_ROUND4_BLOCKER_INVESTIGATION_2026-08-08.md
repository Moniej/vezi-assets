# Stage 14 Round 4 — Blocker Investigation (Provenance Layer)

**Date:** 2026-08-08
**Nature of this document: investigation only.** No file was edited, no database row was inserted/updated/deleted, no schema was changed, no document was retroactively created, no new `sources` row was added. This report establishes root cause and scope for both Round 4 blockers so that a deliberate, informed remediation decision can be made — it does not perform that remediation.

---

## 1. Exact database queries performed

All queries below were run read-only against `data/ngx.sqlite` via `sqlite3`/Python. Full output is reproduced inline, not summarized, so the evidence is auditable.

**Query 1 — full `sources` table:**
```sql
SELECT * FROM sources ORDER BY source_id
```
Result (16 rows, reproduced in full in §2 below). Relevant row:
```
(16, 'stage10c_news_pilot', 'web_archive', None, 'secondary', 0.5,
 "PROVISIONAL pilot registration, Stage 10C (2026-08-08). kind='web_archive' is
 the closest existing schema.sql CHECK-constraint value to 'news_outlet' (not
 itself a valid kind); base_confidence=0.5 is a placeholder, NOT an
 owner-confirmed news_outlets.reliability_tier (that table does not exist yet,
 per Stage 10A's own finding). Do not treat this confidence as final.")
```

**Query 2 — `documents` table, all `news_article` rows, with `source_url`:**
```sql
SELECT doc_id, ticker, source_id, source_url FROM documents
WHERE doc_type='news_article' ORDER BY doc_id
```
18 rows returned, `source_id=16` on every row, `source_url` populated on every row. Domain breakdown: 16 rows `nairametrics.com`, 2 rows `dmarketforces.com` (doc_id 11535 = REGALINS suspension article, doc_id 11541 = NCR turnaround article).

**Query 3 — all GMC/CIR `events` rows:**
```sql
SELECT event_id, ticker, event_type, source_id, source_url FROM events
WHERE event_type IN ('management_change','corporate_restructuring','merger','ownership_change')
ORDER BY event_id
```
6 rows: event_id 171 (DEAPCAP, corporate_restructuring), 172 (LEGENDINT, merger), 173 (ROYALEX, ownership_change), 178 (SUNUASSUR, management_change), 179 (UNIVINSURE, management_change), 180 (VERITASKAP, management_change). All `source_id=16`. All have a populated `source_url`, all `nairametrics.com`.

**Query 4 — exact-URL join, every GMC/CIR event's `source_url` against `documents.source_url`:**
```python
for eid, url in events_rows:
    match = con.execute("SELECT doc_id FROM documents WHERE source_url=?", (url,)).fetchall()
```
Result: 171→`[(11538,)]`, 172→`[(11540,)]`, 173→`[(11543,)]` (all matched); 178→`[]`, 179→`[]`, 180→`[]` (all **zero matches**).

**Query 5 — full-scope sweep, every news event regardless of family, same exact-URL join:**
```sql
SELECT event_id, ticker, event_type, announced_date, source_url FROM events WHERE source_id=16
```
13 rows (event_id 168, 169, 171–181), each checked against `documents.source_url`. Result:

| event_id | ticker | event_type | doc-linked? |
|---|---|---|---|
| 168 | REGALINS | regulatory_action | linked (doc 11535) |
| 169 | UNIVINSURE | regulatory_action | linked (doc 11535) |
| 171 | DEAPCAP | corporate_restructuring | linked (doc 11538) |
| 172 | LEGENDINT | merger | linked (doc 11540) |
| 173 | ROYALEX | ownership_change | linked (doc 11543) |
| 174 | RTBRISCOE | capital_raise | linked (doc 11544) |
| 175 | TANTALIZER | regulatory_action | linked (doc 11545) |
| 176 | REGALINS | capital_raise | linked (doc 11546) |
| 177 | LASACO | capital_raise | linked (doc 11539) |
| **178** | **SUNUASSUR** | **management_change** | **NOT LINKED** |
| **179** | **UNIVINSURE** | **management_change** | **NOT LINKED** |
| **180** | **VERITASKAP** | **management_change** | **NOT LINKED** |
| **181** | **SUNUASSUR** | **capital_raise** | **NOT LINKED** |

The gap is not scattered — it is **exactly** the 4 events (178–181) ingested in one specific batch, and **zero** of the other 9 news events (168–177) are affected.

**Query 6 — schema/code inspection for any enforced events↔documents relationship:**
```bash
grep -n "documents\|doc_id" src/ngxrot/event_pipeline.py   # zero matches
grep -n "FOREIGN KEY\|REFERENCES documents" schema/schema.sql
```
`event_pipeline.py` contains **no reference to `documents` or `doc_id` anywhere in the file** — confirmed by a full-file grep returning nothing. `schema.sql`'s `events` table definition (line 211 onward) has **no `doc_id` column and no foreign key to `documents`** — unlike the FSI-layer tables (`extracted_facts`, `evidence`, `causal_chain_steps`, `investment_implications`), which all declare `doc_id INTEGER NOT NULL REFERENCES documents(doc_id)`.

## 2. Current provenance architecture (as it actually exists, not as §14D/§14H assumed)

- **`sources`** is a *registration-level* table — one row per ingestion pipeline/method, not per outlet or per publication. Its own `source_id=16` row is explicitly self-documented as "PROVISIONAL... Do not treat this confidence as final," disclosed at the moment it was created in Stage 10C, long before Stage 14 existed. It was never intended to distinguish Nairametrics from MarketForces Africa, and it doesn't.
- **`documents.source_url`** (and, identically, **`events.source_url`**) is a free-text column populated at ingestion time with the article's actual URL. This is where outlet identity *actually* lives today — the domain (`nairametrics.com` vs. `dmarketforces.com`) is present and 100% populated across every relevant row checked (Query 2, Query 3). Neither column has a `UNIQUE`, `FOREIGN KEY`, or `NOT NULL` constraint enforcing this, but as-populated data is complete for every GMC/CIR row.
- **`events` and `documents` are architecturally independent tables with no schema-level or code-level link between them.** `event_pipeline.py` (the only code that writes to `events`) never touches `documents`. The only place a `documents` row for a news article was ever created was a manual, ad hoc step taken outside `event_pipeline.py`/`validate_batch()` during this project's own Stage 11 and Stage 12 execution — not a platform-enforced guarantee.

## 3. Root cause — Blocker 1 (cross-outlet corroboration unreachable)

**Root cause**: `sources.source_id` was never designed, at any point in this project's history, to represent "which outlet." It represents "which ingestion registration," and exactly one such registration (`source_id=16`) has ever been created for news, covering both approved outlets simultaneously since its first use in Stage 10C. §14D's cross-outlet mechanism was specified assuming `source_id` would vary by outlet — an assumption that was never true and is disclosed as never having been true, in the very row §14D depends on.

**Where outlet identity actually, deterministically exists today**: the **domain component of `source_url`**, on both `events` and `documents`. Confirmed 100% populated across all 13 news `events` rows and all 18 news `documents` rows checked. No historical row lacks this field. This means outlet identity **can** be deterministically derived from already-stored data, **without** modifying any historical provenance and **without** inventing new source rows — a URL-domain read is a query-time derivation, not a data change.

**What remediation would require** (stated for the record, not performed): a future correction to §14D would need to redefine its "different source" test from `source_id != source_id` to `urlparse(source_url).netloc != urlparse(source_url).netloc` (or equivalent domain extraction) — a **specification-only change**, not a schema or code change to the platform itself, since the field already exists and is already populated. This is explicitly not being done in this document, per the instruction to investigate only.

**Is this fixable without a schema/code/data change?** Yes, for the specification layer — outlet identity is recoverable today by query, from data already in hand. **Whether the underlying `sources` table should eventually be split into per-outlet rows is a separate, larger architectural question** (it would touch how confidence/reliability is tracked per outlet, which this platform has explicitly deferred — see `source_id=16`'s own notes: "not an owner-confirmed `news_outlets.reliability_tier` (that table does not exist yet)"). That is a bigger decision than fixing §14D's matching logic, and is out of scope for this investigation, per the explicit instruction not to create new source rows without understanding the historical implications first.

## 4. Root cause — Blocker 2 (GMC document-provenance claim false)

**Where did events 178–181 actually originate, and what evidence exists?** Traced via Query 5: all four were ingested in one batch, `data/events_news/events/stage12_news_events_2026-08-08.csv` (Stage 12's event CSV), through the standard `event_pipeline.ingest_events()` path — the same, correctly-functioning mechanism used for every other event in this corpus. **The event rows themselves are not corrupted or fabricated** — each carries a real `source_url`, a real `headline` quoting the source article, a real `announced_date`/`effective_date`, and passed `validate_batch()`'s taxonomy/chronology/dedup checks cleanly (0 rejections, 0 issues, per Stage 12's own ingestion report). The **evidence for reconstructing the article exists in the event row's own `source_url` and `notes` fields** — the underlying article was genuinely fetched and read during Stage 12 (its content is quoted in `notes`), it was simply never separately registered as a `documents` row.

**Why does `documents.source_url` not match?** Because no `documents` row was ever created for these 4 articles. This is confirmed, not inferred: Query 5 shows the *identical* Stage 12 batch's other numeric-fact articles (CILEASING, REDSTAREX, VERITASKAP's earnings piece, UNIVINSURE's capital-raise piece — a separate set of 4 articles from the same stage) **do** have `documents` rows (doc_id 11548–11551), created via a dedicated registration step. **The 4 event-only articles from that same stage never went through an equivalent registration step.** This is a scope inconsistency in how Stage 12 was executed relative to Stage 11 (which registered `documents` rows uniformly for all 12 of its articles, both fact- and event-shaped) — not a mysterious external failure, and not a pipeline defect in the sense of `event_pipeline.py` doing something wrong. It did exactly what it was asked to do; it was simply never asked to also create a `documents` row, because nothing requires it to.

**Are the URLs normalized differently, causing an match failure that looks like "no document" but isn't?** No — checked directly: the `source_url` values in the 4 orphaned `events` rows are well-formed, real, non-truncated URLs with no formatting inconsistency versus the ones that *do* match. The mismatch is a true absence, not a string-comparison artifact.

**Does the event pipeline permit this provenance gap?** Yes, structurally — confirmed by Query 6: there is no code path in `event_pipeline.py` and no schema constraint in `schema.sql`'s `events` table definition that requires, checks for, or creates a corresponding `documents` row. This is not a bug introduced by Stage 14's specification — it is a pre-existing structural property of the platform (events and the FSI/documents layer are, and always have been, independent tracks — appropriate for the pipeline's original CBN/MPC use case, where no `documents` layer was ever involved at all). What *is* new is that §14H asserted a completeness guarantee ("all Stage 11/12 GMC/CIR events... have one") that was never actually backed by this mechanism — the guarantee was true by coincidence for Stage 11's execution discipline and false for Stage 12's.

## 5. Scope of each problem

| Problem | Scope |
|---|---|
| Blocker 1 (source_id can't distinguish outlets) | **Universal** — every single news `events`/`documents` row ever ingested (Stage 10C onward) shares `source_id=16`. This affects the entire news corpus, not just GMC/CIR. |
| Blocker 2 (missing document links) | **Confined to exactly 4 rows**: `events` 178, 179, 180, 181 — all and only the event-shaped half of Stage 12's batch. All 9 Stage 11 news events are unaffected; Stage 12's numeric-fact articles are unaffected too (they produced `extracted_facts` rows, which correctly carry `doc_id NOT NULL REFERENCES documents(doc_id)` per schema — a different, unaffected mechanism). Within the two families this specification covers: **within GMC specifically, 3 of 3 confirmed GMC events (100%) are affected; within CIR, 0 of 3 confirmed CIR events (0%) are affected.** |

## 6. Can existing data support a deterministic fix, and what would remediation require?

**Blocker 1**: yes, fully, from existing data — see §3. A specification-level redefinition of "different outlet" from `source_id` to `source_url` domain is sufficient; no schema/code/data change to the platform is required to make this workable, only a correction to how §14D's matching rule reads the already-complete `source_url` field.

**Blocker 2**: partially. The **evidence to reconstruct the 4 missing documents is real and already captured** — the exact source URL and (per Stage 12's own ingestion notes) quoted article content already exist in the `events` rows themselves. A `documents` row *could* be deterministically backfilled for these 4 articles **without fabricating anything**, because the source material was genuinely fetched and read at the time, and its provenance (URL, ticker, date) is already on record — this would not be "creating documents retroactively to make §14H true" in the sense of inventing content, since nothing about the underlying facts would be asserted that wasn't already true and recorded. **This document does not perform that backfill** — per the explicit instruction, it only establishes that such a backfill is *possible without dishonesty*, leaving the decision of whether/how to do it to a deliberate future step, not an incidental fix inside an investigation.

Whether such a backfill is the *right* remediation (versus, say, §14H being corrected to honestly state that GMC events currently lack document backing and are evidenced only via the `events` row's own `notes`/`source_url` fields, without a `documents` row at all) is a design choice this report deliberately leaves open rather than pre-deciding.

## 7. Can historical provenance be preserved?

Yes, for both blockers, under either resolution path considered:
- Blocker 1's fix (redefine outlet detection to use `source_url` domain) touches **zero** historical rows — it is a read-time rule change only.
- Blocker 2's possible backfill path, if chosen, would **add** 4 new `documents` rows dated with today's actual retrieval context, not alter any existing `events` row — consistent with this platform's append-only, never-overwrite convention used throughout (see Stage 10E's remediation precedent). No historical record would need to be rewritten under this path.

## 8. Explicit impact on §14D and §14H

- **§14D** (cross-outlet identity/dedup): its core logical structure (ticker + event_type + date window + identity-content agreement, fail-closed on ambiguity) is not shown to be wrong by this investigation — what's wrong is the specific field it uses to detect "a different outlet" (`source_id`), which cannot vary given how ingestion has actually been done. The mechanism's *policy* stands; its *implementation detail* does not match reality and must be corrected before the mechanism can ever fire.
- **§14H**: the `source_document_id` field's stated completeness guarantee is false for the entire confirmed GMC sample (3 of 3 rows). Any dataset built today per §14H's field mapping would need `source_document_id` to be genuinely nullable for these rows (which the mapping does not currently disclose as a possibility) or the underlying gap must be closed first.
- Neither §14A, §14C, §14E, §14F, §14G, nor §14I's substantive content (event definitions, direction rules, PIT algorithm, cross-sectional design, independence argument) is implicated by either blocker — this is confined to the provenance/dedup layer, consistent with Round 4's own finding.

## 9. Recommended minimum remediation (stated, not performed)

1. Correct §14D to define "different outlet" via `source_url` domain extraction rather than `source_id`, since the latter is confirmed structurally incapable of the distinction this project has ever made between outlets.
2. Correct §14H's `source_document_id` claim to state accurately that 3 of 3 confirmed GMC events currently lack a linked `documents` row, and either (a) explicitly define `source_document_id` as nullable with `source_url`/`notes` on the `events` row itself serving as the fallback evidence trail for such cases, or (b) perform a disclosed, non-fabricated backfill of the 4 missing `documents` rows from their already-known, already-fetched source content, per §6 above — a decision for the requester, not this document.
3. Before either fix is written into the specification, re-run the full document-link check (Query 5's method) across the entire news corpus one more time as a final confirmation, since this investigation found the gap to be stage-batch-aligned and it is worth confirming no other batch has a similar undetected gap before declaring the provenance layer complete.

## 10. Zero-write verification

Row counts, checked immediately before and confirmed unchanged after this entire investigation (no write operation was executed at any point):

| Table | Count |
|---|---|
| `events` | 171 |
| `documents` | 11,551 |
| `extracted_facts` | 461 |
| `sources` | 16 |

`configs/h011_size.toml` and `docs/PREREG_H-011.md`: file modification timestamps unchanged (2026-07-22, both files) versus every prior check in this project's history. No file matching `*h019*`/`*H-019*` exists anywhere in the repository. No `INSERT`/`UPDATE`/`DELETE`/`CREATE` statement was executed against `data/ngx.sqlite` in the course of this investigation — every query above was a `SELECT`.

---

## Decision

Per the stated decision rule, and because both provenance problems remain factually unresolved (only investigated, not remediated, per explicit instruction):

**NOT READY — PROVENANCE LAYER BLOCKS H-019.**

No further independent review should be scheduled until the provenance model in §14D/§14H is corrected to match the architecture documented in §2-§4 above, and that correction is itself re-verified against a live query rather than assumed correct on inspection — consistent with the lesson every prior round of this process has already demonstrated the hard way.
