# Stage 14 — Provenance Remediation

**Date:** 2026-08-08
**Scope:** narrow remediation of the two Round 4 provenance blockers only. No H-019, no backtest, no new scraping, no H-011 modification, no reopening of the GMC/CIR event/direction definitions in §14A/§14C. This document records exactly what was done, on top of the root-cause findings already established in `docs/STAGE14_ROUND4_BLOCKER_INVESTIGATION_2026-08-08.md`.

---

## 1. Root cause (recap, established by the prior investigation, re-confirmed here)

- **Blocker 1**: `source_id=16` covers both Nairametrics and MarketForces Africa — it was never designed to distinguish outlets and never has, since its first (disclosed-as-provisional) registration in Stage 10C. Outlet identity was never missing from the data; it lives in `source_url`'s domain, already 100% populated.
- **Blocker 2**: Stage 11 registered a `documents` row for all 12 of its articles; Stage 12 registered one only for its 4 numeric-fact articles, leaving its 4 event-shaped articles (`event_id` 178–181) with no document provenance. `event_pipeline.py` has no code path linking events to documents and never did — this is a structural property of the platform, not something Stage 14 introduced, but §14H had incorrectly asserted a completeness guarantee that was never mechanically backed.

## 2. Remediation performed

### A. §14D corrected — outlet derivation from `source_url`, not `source_id`

`docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md`, §14D, was amended (fifth correction, logged inline) to replace every use of "two different `source_id`s" as the cross-outlet test with a deterministic derivation from `source_url`'s domain. **No historical `source_id` value was touched** — this is a read-time rule for the dedup procedure only.

**Outlet-domain normalization procedure** (now frozen in §14D):
1. Take the candidate row's `source_url`.
2. `NULL`/empty/unparseable → outlet **UNKNOWN**, never merged, evaluated as its own unlinked observation.
3. Extract and lower-case the hostname.
4. Strip a leading `www.`.
5. Allow-list mapping: `nairametrics.com` or any `*.nairametrics.com` subdomain → `nairametrics`; `dmarketforces.com` or any `*.dmarketforces.com` subdomain → `marketforces_africa`; anything else → UNKNOWN (fails closed — never guessed as one of the two approved outlets).
6. Two rows are "different outlets" only if both resolve to different, non-UNKNOWN values.

**Traced against real data** (not merely asserted — executed):

| Input URL | Resolved outlet |
|---|---|
| `nairametrics.com/2026/08/05/caverton-posts...` | `nairametrics` |
| `dmarketforces.com/ngx-suspends-trading-in-3-insurance-firms...` | `marketforces_africa` |
| `stocks.nairametrics.com/tag/caverton-offshore...` (real subdomain observed in this corpus) | `nairametrics` |
| `www.nairametrics.com/some-article/` | `nairametrics` |
| `unknown-outlet.example.com/article/` | UNKNOWN |
| `None` / empty string | UNKNOWN |

**Test cases required by this remediation, all traced against the corrected rule**:
1. *Same event, same outlet* → both resolve to the same outlet value → never a corroboration candidate → falls to the unchanged within-source `validate_batch()` path (REJECT on identical payload, RESTATEMENT on changed payload).
2. *Same event, Nairametrics + MarketForces* → `nairametrics` vs. `marketforces_africa`, both non-UNKNOWN and different → **is now reachable** as `candidate_corroboration_unconfirmed` if ticker/type/date-window/identity-content also match (it was structurally unreachable before this fix, since `source_id` never varied).
3. *Different events, same ticker/event_type, close dates* → identity-content comparison (unchanged from the second correction) still governs; a date/ticker/type match with differing identity content is never auto-merged regardless of outlet.
4. *Missing/ambiguous identity or malformed URL* → falls to UNKNOWN-outlet handling (step 2) or the pre-existing identity-ambiguity rule → `candidate_corroboration_unconfirmed` or unlinked `primary`, never a guessed merge.
5. *Unknown domain* → resolves to UNKNOWN, excluded from cross-outlet matching entirely, consistent with §14A's restriction to only the two approved sources.

### B. Four orphaned documents backfilled

**Mapping, verified one-to-one before any write** (exact URL match against the corresponding `events` row, confirmed no pre-existing `documents` row for any of the four, confirmed the original fetched article text file still exists on disk for each):

| event_id | ticker | source_url | backfill source text | new doc_id |
|---|---|---|---|---|
| 178 | SUNUASSUR | `nairametrics.com/2026/04/11/sunu-assurances-announces-board-changes-...` | `data/staging/news_text/sunuassur_board_change.txt` (fetched live in Stage 12, on disk unmodified since) | **11552** |
| 179 | UNIVINSURE | `nairametrics.com/2025/01/17/universal-insurance-appoints-japhet-ogueri-duru-as-new-md-ceo/` | `data/staging/news_text/univinsure_ceo_appointment.txt` | **11553** |
| 180 | VERITASKAP | `nairametrics.com/2025/11/03/veritas-kapital-shareholders-elect-babatunde-irukera-as-chairman/` | `data/staging/news_text/veritaskap_chairman_election.txt` | **11554** |
| 181 | SUNUASSUR | `nairametrics.com/2026/02/11/sunu-assurances-board-targets-n9-33-billion-raise-via-rights-issue-outlines-structure/` | `data/staging/news_text/sunuassur_rights_issue.txt` | **11555** |

Every field written was either read directly from the existing `events` row (`ticker`, `source_url`, `filing_date = events.announced_date`) or is the real, already-fetched article text saved to disk during Stage 12's own `WebFetch` step — nothing was invented. `source_id=16`, `doc_type='news_article'`, `source_confidence=0.5` — identical pattern to the other 18 documents already in this corpus. The insert script re-verified, immediately before writing, that no document with the target URL existed and that the target event row's `ticker`/`source_url` matched the mapping exactly — an abort-on-mismatch guard, not a best-effort insert.

### C. Recurrence-prevention guard added

New file: `scripts/test_event_document_provenance.py` — a standalone assertion script (matching this project's existing test convention, e.g. `scripts/fre/test_periods_overlap.py`), not a schema change. It queries every ticker-scoped `events` row whose `source_id` belongs to a `sources` row with `kind='web_archive'`, and asserts a `documents` row exists with the exact same `source_url`. Scoped narrowly to `web_archive`-kind sources specifically (not all events) because non-news sources — CBN/MPC events, for example — legitimately never touch the `documents`/FSI layer at all, and a blanket rule would produce false failures there.

Run:
```
PYTHONPATH=src python scripts/test_event_document_provenance.py
```
Result (post-backfill): `3 passed, 0 failed` — 13 ticker-scoped web_archive events checked, all now linked. Before the backfill, this exact script (logically — it did not exist yet, but its query was the same one used in the Round 4 investigation) would have reported exactly the 4 orphans found. This is the smallest guard that directly targets the actual failure mode (event ingested, no document registered) without a broader architectural rewrite, per the explicit instruction to prefer a validation test over a schema change.

## 3. Before/after database counts

| Table | Before | After | Delta |
|---|---|---|---|
| `events` | 171 | 171 | 0 |
| `documents` | 11,551 | 11,555 | **+4** (exactly the 4 backfilled) |
| `extracted_facts` | 461 | 461 | 0 |
| `sources` | 16 | 16 | 0 (no new source row created) |

## 4. Integrity verification

- **The 4 previously orphaned events now have document provenance**: `scripts/test_event_document_provenance.py` — `3 passed, 0 failed`.
- **All Stage 11/12 news events have valid document linkage**: same script, 13/13 ticker-scoped web_archive events matched (the 9 from Stage 11 that were already linked, plus the 4 just backfilled).
- **Outlet identity can be derived from existing URLs**: demonstrated in §2A's traced table against 8 real and edge-case inputs, including a real subdomain (`stocks.nairametrics.com`) actually present in this corpus.
- **Cross-outlet matching is actually reachable**: demonstrated — a real Nairametrics URL and a real MarketForces URL from this corpus resolve to two different, non-UNKNOWN outlet values under the corrected rule, which was never true under the old `source_id`-based test.
- **Ambiguous cases fail closed**: unknown domains, missing URLs, and identity-content mismatches all resolve to UNKNOWN/`candidate_corroboration_unconfirmed`/unlinked-`primary` per §2A, never a guessed merge.
- **Stage 10E event dedup regression suite still passes**: all 8 tests re-run, identical accept/reject counts and messages to every prior run in this project (Test 3's NULL-safe identical-payload check included) — zero writes performed by the suite itself (`validate_batch()` is read-only).
- **Historical MPC correction remains intact**: `event_id` 154 (30.00%, original, unmodified), 156 (12.00%, original, unmodified), 170 (the Stage 10E data-quality correction) — all three read back byte-identical to their known values.
- **No unrelated events/documents were modified**: spot-checked event_id 1, 83, 93, 168, 169, 171–177 — all headlines/content identical to pre-remediation state; `events` row count unchanged at 171 confirms nothing was added, removed, or altered at the event layer.
- **H-011 remains untouched**: `configs/h011_size.toml` and `docs/PREREG_H-011.md` file modification timestamps unchanged (2026-07-22, both files, matching every prior check across this entire project).
- **No H-019 exists**: confirmed, no file matching `*h019*`/`*H-019*` anywhere in the repository.

## 5. Exact sections of Stage 14 amended

- `docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md`, §14D only — the "fifth correction" block (outlet-domain normalization procedure, corrected ingestion-time and dataset-build-time matching rules, five traced test cases). No other section (§14A, §14B, §14C, §14E, §14F, §14G, §14H, §14I, §14J) was touched by this remediation. §14H's `source_document_id` field description was **not** edited in this pass — see limitations below.

## 6. Remaining limitations (explicitly not addressed by this narrow remediation)

- **§14H's `source_document_id` field description was not updated to reflect the backfill.** It still doesn't state that 3 of 3 GMC events previously lacked document provenance — this is now moot for the *current* data (all 4 are backfilled), but the field's documented behavior for a *future* GMC/CIR ingestion that again skips document registration is not restated. The new §14C recurrence-prevention test (`scripts/test_event_document_provenance.py`) would catch a future recurrence operationally, but the spec text itself was not re-worded. Left as an open, disclosed item rather than folded into this remediation, since the user's instructions scoped this pass to A–D above and did not ask for a further §14H text edit beyond what A/B required.
- **The ±3-calendar-day cross-outlet window remains provisional**, unchanged by this remediation — no genuine cross-outlet duplicate pair has yet arisen in this corpus to calibrate it against (all 13 news events, including the 4 just backfilled, are single-outlet; there is still no live example of the same event reported by both Nairametrics and MarketForces to test the corrected mechanism against real duplicate data, only the synthetic trace in §2A above).
- **The "identity content agreement" human-judgment point** (disclosed in the prior review round) is unaffected by this remediation and remains a documented, non-mechanical step.
- **This remediation did not re-verify the MINOR findings** from Round 4 (the unscoped `acquisition` taxonomy leaf, the "11 GMC/CIR-type events" citation) — out of the explicit scope of this pass.

## 7. Zero-write guarantee outside the two authorized backfill inserts

No `INSERT`/`UPDATE`/`DELETE` was executed against any table other than `documents`, and there only for the 4 specifically mapped and pre-verified rows. No `sources` row was created. No `events` row was modified. `configs/h011_size.toml`, `docs/PREREG_H-011.md` untouched. No H-019 file created. No backtest run. No external source scraped.

---

## Gate

**PROVENANCE REMEDIATION COMPLETE — READY FOR ANOTHER INDEPENDENT REVIEW.**
