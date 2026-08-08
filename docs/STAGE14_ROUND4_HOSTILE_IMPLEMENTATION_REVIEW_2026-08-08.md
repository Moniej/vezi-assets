# Stage 14 — Round 4 Hostile Implementation Review

**Date:** 2026-08-08
**Scope:** `docs/STAGE14_NEWS_FACTOR_SPECIFICATION_2026-08-08.md` (as amended through §14M).
**Method:** read-only investigation only. No file under review was modified. No H-019 was built. No backtest was run. All database queries below are `SELECT`-only, run against the live `data/ngx.sqlite`.
**Posture:** adversarial. Rounds 1-3 each found and fixed one genuine, previously-missed defect (§14K/§14L/§14M). This round's job was to find a fourth, verifying everything from scratch rather than trusting the amendment logs.

**Result: a fourth defect was found — in fact two independent BLOCKING defects, plus two further SIGNIFICANT issues, none of which were caught in rounds 1-3.**

---

## A. PIT chain attack

Traced `source timestamp → knowledge_timestamp → §14E calendar lookup → eligible_from → dataset join`.

- Live query confirms `index_levels.confidence` distribution: `(0.0, 24624)`, `(0.4, 1)`, `(0.5, 22361)` rows; **3,578 distinct `trade_date` values reach `confidence>=0.5`** — this exactly matches the number cited in §14E/§14M, so the round-3 fix still holds against current data.
- `MIN(trade_date)` at `confidence>=0.5` = `2012-01-30`; **`MAX(trade_date)` at `confidence>=0.5` = `2026-07-15`**. Today's date in this environment is 2026-08-08, i.e. the high-confidence calendar's own tail is already ~3.5 weeks stale relative to "now." Any GMC/CIR event whose `knowledge_timestamp` falls on or after 2026-07-15 would correctly resolve to `eligible_from = UNKNOWN` per step 4 — this is the *intended* fail-closed behavior, not a bug, but it is worth stating plainly: **the calendar coverage gap is real and current**, not a hypothetical edge case invented for this review. All 6 GMC/CIR events currently in `events` have `announced_date <= 2026-04-11`, safely inside the calendar, so no live event is currently affected — but the next news-pilot batch easily could be, and the spec does not flag that this condition is presently live/near.
- Per-year distinct trade-date counts (2012-2026) show no anomalous gaps; the calendar is dense and continuous within the covered range.
- Constructed counterexamples from §14A/§14E text (same-day publication, post-close publication, weekend/holiday dates, missing/malformed timestamp, `effective_date < announced_date`, `effective_date > announced_date`, two-outlet timing divergence): the algorithm as written in §14E resolves all of these correctly and deterministically **given a `knowledge_timestamp`** — the "conservative next trading session" construction is sound and matches the real, gapless calendar. No new defect found in the algorithm's arithmetic itself.
- The one real counterexample the current corpus already contains — `effective_date < announced_date` — is correctly handled by §14E/§14I (`eligible_from` is keyed off `knowledge_timestamp`/`announced_date`, never `effective_date`). However, see finding **F1** below: the specific statistic §14I cites to justify this instruction ("3 of the 4 GMC events... had effective_date < announced_date") does not match what a live query of the real corpus shows.

**Conclusion for A:** the PIT algorithm itself is sound and re-verified against live data (round 3's fix holds). No new PIT-arithmetic defect found. One factual-citation defect found and reported under F1/the findings table.

## B. Cross-outlet identity attack — the section where this round's primary defects live

Constructed the task's listed counterexamples (chairman resignation vs. unrelated director appointment same company/window; CEO vs. chairman appointment; two stake acquisitions; two restructurings within ±3 days; same event different wording; incomplete identity fields; different publication dates; three-way ambiguity) against §14D's stated procedure. The *stated* procedure (ticker + event_type + ±3-day window + identity-content match, fail-closed to `candidate_corroboration_unconfirmed` on ambiguity, manual resolution required) is logically coherent as prose and does correctly cover 2-way and describes itself as extending to N-way ("more than one row matches... resolve manually" — this reads as N-way inclusive, not narrowly 2-way).

**The real defect is not in the prose logic — it is that the prose procedure is not reachable from the real schema and real pipeline code, which the document does not check.**

**Finding B1 (BLOCKING) — `source_id` cannot distinguish the two approved outlets, so the "two different source_ids" trigger in §14D can never fire, and the pipeline's actual same-source logic runs on a different identity than §14D assumes.**

Live query of `sources`:
```
source_id=16, name='stage10c_news_pilot', kind='web_archive', reliability='secondary', base_confidence=0.5
```
This is the **only** source row used for any GMC/CIR event currently in the database. Confirmed:
```sql
SELECT DISTINCT source_id FROM events WHERE event_type IN
  ('management_change','corporate_restructuring','merger','ownership_change');
-- -> [(16,)]
```
Both Nairametrics and MarketForces Africa articles are ingested under this **same** `source_id`. This is not an ingestion accident — it is documented as the platform's deliberate convention: `docs/STAGE10E_EVENT_IDENTITY_AND_NEWS_INGESTION_INTEGRITY_2026-08-08.md` line 63 states explicitly, for a MarketForces Africa article: `source_id | 16 (stage10c_news_pilot) | 16 | Same source, correctly shared (one article, one source record).` Line 12 of the same document confirms the MFA article in question is `stage10d`'s founding ticker-scoped submission. So the real, intentional architecture is: **outlet identity (Nairametrics vs. MarketForces Africa) is never captured at the `sources`/`source_id` level at all** — only at the free-text `documents.source_url` / `events.source_url` level (verified: `source_url LIKE '%marketforces%'` → 2 rows; `LIKE '%nairametrics%'` → 16 rows, all under the one shared `source_id=16`).

§14D's dataset-build-time reconciliation rule reads: *"Any pair of rows matching on all four components, from two different `source_id`s... is flagged `duplicate_status = candidate_corroboration_unconfirmed`."* Given the real, intentional schema convention just verified, **this condition is structurally unsatisfiable for the two outlets this specification is scoped to** — a genuine Nairametrics/MarketForces Africa corroborating pair will never have two different `source_id`s, so the flag can never trigger, and the entire "fallback, dataset-build-time" safety net §14D relies on is dead on arrival against the real data model.

It is worse than a missed flag. Read `src/ngxrot/event_pipeline.py:150-209` (the exact function §14D cites as authoritative and unmodified): the `same_src` branch is
```python
same_src = m[m.src == r.get("_source_name", "")]
```
`_source_name` is set in `ingest_events()` (`src/ngxrot/ingest.py`) to `provider.info.name` — the **ingestion batch/provider's own registered name** (e.g. `"stage10c_news_pilot"`), not the news outlet byline inside the article. Since both approved outlets are ingested through the same provider/source registration, a genuine **second-outlet submission of the same real-world event** will hit `same_src` (true), not the `CONFLICT` branch §14D's own correction narrative describes as the only pre-existing protection. From there the code either (a) `REJECT`s it outright ("already ingested from this source (no uid to restate against)" or "uid-less priors cannot be superseded"), silently dropping a genuinely independent corroborating article before it ever reaches the `events` table — meaning it never becomes a row for the dataset-build-time reconciliation pass to even see — or (b) treats a differing payload as a same-source `RESTATEMENT`, auto-appending under whatever `event_uid` was supplied with **no human identity-content comparison step**, bypassing §14D's disclosed judgment procedure entirely rather than routing through it. Either path defeats the fail-closed guarantee §14D and §14J item 4 claim.

Consequence for §14H: the derived `source` field is defined as "joined `sources.name` via `events.source_id`" — given the real data, this field would read `"stage10c_news_pilot"` for **every** GMC/CIR row regardless of which of the two approved outlets actually published it, making it impossible to verify from the dataset itself that the "Eligible sources: Nairametrics, MarketForces Africa. No other source" rule (§14I) is being honored by anything mechanical — that check can currently only be done by hand-inspecting `source_url` text, a step never named as a required verification anywhere in §14A-14J.

This is a genuine, concrete, previously-uncaught defect: rounds 1-3 all treated "two different `source_id`s" as an adequate, checkable signal for cross-outlet detection without ever querying whether the real `sources` table actually assigns different `source_id`s to the two approved outlets. It does not.

## C. Direction rule attack

Re-derived §14C's worked examples from the rule table against the real `events` rows (not the document's own restatement of them):

- SUNUASSUR / Bakare: resignation, no adverse reason stated in `headline`/`notes` → NEUTRAL. Correct per rule.
- SUNUASSUR / Adaramola: appointment, no controversy → NEUTRAL. Correct per rule (but see **finding B2/§F below** — this "event" is not actually a separate row in `events`; see below).
- UNIVINSURE / Duru: CEO confirmation → NEUTRAL. Correct.
- VERITASKAP / Irukera: chairman election → NEUTRAL. Correct.
- DEAPCAP: rename + disclosed N1bn capital injection from Banklink Africa (confirmed in `notes`/`headline`) → POSITIVE per the CIR rule table's second row. Correct, matches doc.
- LEGENDINT/Spectranet: "targeting N80 billion combined capital base" stated in headline → this is a **stated target**, not an unambiguous "stated increase... as stated in the article" versus LEGENDINT's own prior standalone value. The headline says "targeting," i.e. an aspirational/planned figure, not a confirmed realized increase. A careful second reader could plausibly call this NEUTRAL or even UNKNOWN ("increase" not yet confirmed, deal "pending FCCPC/NCC regulatory clearance as of publication," per the event's own `notes`) rather than POSITIVE. This is a real, borderline case exactly of the kind the task asked me to hunt for in §14C — not a new defect (the document itself discloses in §14J item 2 that two readers "should converge in the great majority of cases but are not mathematically guaranteed to"), so it does not rise above what §14J item 2 already honestly discloses. Flagged as confirmation the existing disclosure is accurate, not as a new gap.
- ROYALEX/Nexamont: "has not yet disclosed its strategic intentions" → NEUTRAL. Correct, matches doc.

No sentiment back-door found: `investment_implications.direction` is never referenced in the §14H field mapping, and no field derived from it appears anywhere in §14C/§14F. Missing fields correctly default to UNKNOWN in the rule tables, never to NEUTRAL/BULLISH/BEARISH.

**No new defect found in C** beyond confirming the disclosed judgment-boundary risk is real (as the document itself already says).

## D. Independence attack

Verified the three-way distinction the task named:
1. **Mechanical independence** — §14G's table is checked against `backtest_xs.py`'s actual `size_scores()` inputs; the claim ("no personnel field exists anywhere in H-011's signal construction") is a structural claim about what columns that function reads, and is consistent with what the schema shows H-011 can access. This is the one leg the document actually establishes with evidence.
2. **Statistical independence** (correlation of realized signal values) — correctly **not** claimed anywhere; the document is explicit that there isn't enough data to test this yet.
3. **Economic/common-cause independence** — correctly named as an open risk in §14G's correction and gated as §14J item 10, not run, not claimed satisfied.

Exploratory-only diagnostic (not a substitute for §14J item 10's gate, and explicitly not run as any kind of authorized check): all 6 current GMC/CIR event tickers (DEAPCAP, UNIVINSURE, VERITASKAP, SUNUASSUR, LEGENDINT, ROYALEX) fall inside the 20-name H-011 universe (`data/reference/stage6_h011_universe_2026-08-08.json`), which itself skews toward small/thinly-traded names (CAVERTON, CILEASING, CUTIX, NSLTECH, OMATEK, RTBRISCOE, TANTALIZER, etc.). With n=6 events across 20 names, no decile-level or statistically meaningful size/distress check is possible from this sample; I did not attempt one. **This observation is descriptive only, is not a completed run of §14G/§14J item 10's named diagnostic, and does not satisfy that gate** — the gate explicitly requires a deliberate, documented run as part of a future authorized stage, and this hostile review does not count as that, per the task's own instruction.

**No new defect found in D**; the document's own framing of what is/isn't established holds up.

## E. Real-database compatibility

This is where **finding B1** (above) and **finding E1** (below) live; both are real-database-compatibility failures of exactly the kind Round 3 warned future reviewers to keep hunting for.

**Finding E1 (BLOCKING) — §14H's `source_document_id` completeness claim ("all Stage 11/12 GMC/CIR events do have one") is false for the real corpus; the entire GMC family currently has no linked document.**

Live query: joining each GMC/CIR event's `source_url` against `documents.source_url` (exact match):

| event_id | ticker | event_type | `source_url` matches a `documents` row? |
|---|---|---|---|
| 171 | DEAPCAP | corporate_restructuring | Yes — doc_id 11538 |
| 172 | LEGENDINT | merger | Yes — doc_id 11540 |
| 173 | ROYALEX | ownership_change | Yes — doc_id 11543 |
| 178 | SUNUASSUR | management_change | **No match** |
| 179 | UNIVINSURE | management_change | **No match** |
| 180 | VERITASKAP | management_change | **No match** |

All 3 CIR events resolve; **all 3 GMC events do not** — none of the three GMC source articles (`sunu-assurances-announces-board-changes-as-olajumoke-bakare-resigns`, `universal-insurance-appoints-japhet-ogueri-duru-as-new-md-ceo`, `veritas-kapital-shareholders-elect-babatunde-irukera-as-chairman`) appear anywhere in `documents`. The 18 rows actually stored under `source_id=16` (the pilot source) are a **different** set of articles per ticker — mostly earnings/capital-raise pieces (e.g. VERITASKAP's Q1-profit article, doc_id 11550; UNIVINSURE's capital-raise-seeking article, doc_id 11551) that happen to share a ticker with a GMC event but are not that event's own source document.

This is not merely a missing-optional-field problem. It directly contradicts §14H's explicit, unqualified claim, and it creates a live risk beyond a simple NULL: real, on-topic NGX primary-source filings **do** exist in `documents` for the same tickers around the same dates — e.g. doc_id 11152, `SUNU_ASSURANCES_NIGERIA_PLC-BOARD_CHANGES_CORPORATE_ACTIONS_APRIL_2026.pdf`, filed 2026-04-08, three days before event 178's `announced_date` of 2026-04-11, and literally titled "BOARD_CHANGES." An implementer trusting §14H's "all... do have one" claim and writing a fuzzy ticker+date-proximity join to backfill `source_document_id` (rather than discovering, only by testing, that the exact-URL join silently returns nothing for 50% of the GMC/CIR corpus) could plausibly link event 178 to this NGX filing instead of the actual Nairametrics article the event's own fields describe — silently substituting one document's evidentiary chain for another's. Nothing in §14A-14J flags that this join can go empty, despite the task's own instruction to hunt for exactly this ("any join that could silently go empty").

## F. Document consistency sweep

Grepped the full document for every concept named in the task (PIT, eligible_from, knowledge_timestamp, effective_date, cross-outlet, event_uid, duplicate_status, candidate_corroboration_unconfirmed, deterministic, human adjudication, confidence, independence, confound, H-019). All current-section mentions (§14A-14J) agree with each other in substance; §14I's consolidated bullets now do track §14A-14H's detailed versions (the round-2 staleness bug is genuinely fixed). §14K/§14L/§14M read unambiguously as historical logs; no language there could be mistaken for a current, conflicting instruction.

One factual-citation defect survived this sweep, not caught by rounds 1-3 because it requires a live count, not a re-read of the prose:

**Finding F1 (SIGNIFICANT) — §14I's "3 of the 4 GMC events... had effective_date < announced_date" does not match the real corpus.**

There are exactly **3** `management_change` rows in `events` (178, 179, 180), not 4. All **3 of 3** have `effective_date < announced_date`:
- 179 UNIVINSURE: effective 2025-01-10 < announced 2025-01-17
- 180 VERITASKAP: effective 2025-10-31 < announced 2025-11-03
- 178 SUNUASSUR: effective 2026-04-01 < announced 2026-04-11

The true fraction is 100% (3/3), not the 75% ("3 of the 4") §14I states. The "4" appears to come from treating SUNUASSUR's single row as covering two named individuals (Bakare + Adaramola, see F2 below) for the purposes of this specific sentence, while every other part of the document (and the underlying `events` table) treats SUNUASSUR as one event. Whichever way it is counted, "3 of 4" is not a value a live query of the real corpus produces. This is exactly the class of unverified, stale-sounding statistic Round 3 identified as the recurring failure mode in §14I — a citation that reads as fact-checked but was not re-verified against a live query at the time it was written. It does not change the correctness of the underlying instruction (still correct to use `knowledge_timestamp`, not `event_date`, as the join key) — but it is a factual error in a section explicitly billed as "frozen" and fact-cited.

**Finding F2 (SIGNIFICANT) — the real SUNUASSUR row conflates two structurally distinct GMC actions into one event, contradicting §14A's own canonical key and §14F's simultaneous-events rule.**

`events` row 178's `headline` is: *"SUNU Assurances: Olajumoke Bakare resigns as Independent Non-Executive Director effective 2026-04-01; Olayinka Adaramola appointed Executive Director Technical Operations"* — two different named individuals, two different roles, two different structural actions (a resignation and a separate appointment), reported in one article and ingested as **one** `events` row with **one** `event_uid`, **one** `direction` value, **one** `canonical_event_id`.

§14A's own GMC canonical key is `(ticker, event_type='management_change', effective_date_or_announced_date, named_individual_role)` — the fourth component differs between Bakare and Adaramola, so by the specification's own key definition these are two distinct canonical events. §14F is explicit: *"Simultaneous events (two different qualifying events for the same ticker on the same `announced_date`): both are retained as separate rows with distinct `canonical_event_id`s... never merged or averaged."* The real, already-ingested data does not honor this — it is a single merged row. §14C's own worked-example table implicitly treats them as two items ("SUNUASSUR's Bakare resignation... → NEUTRAL. Adaramola's appointment → NEUTRAL.") while the underlying row they are drawn from is one. A dataset-build process reading `events` directly, as §14H instructs, gets **3** GMC rows where the specification's own logic implies **4** distinct named-individual observations should exist. In this specific case both halves happen to resolve to the same direction (NEUTRAL), so the disclosed "all in-sample GMC events resolve to NEUTRAL" headline finding is not falsified by this — but nothing in §14A-14J states a rule for detecting or splitting an already-ingested row that bundles two distinct qualifying disclosures, and nothing flags that this specific, real row needs it.

**Finding F3 (MINOR) — an unscoped taxonomy leaf creates a live classification ambiguity for future CIR ingestion.**

`configs/event_taxonomy.toml`'s `[corporate]` category includes a distinct `acquisition` leaf, separate from `merger`/`ownership_change`/`corporate_restructuring`. §14A's CIR qualifying-content language — *"an externally-disclosed acquisition of a substantial shareholding"* — describes exactly the kind of disclosure that a future ingesting analyst could reasonably tag `event_type='acquisition'` rather than `ownership_change`, since both are valid, semantically overlapping taxonomy leaves and no rule in §14A says which one governs a stake acquisition. §14I's "Eligible event families" list (`corporate_restructuring`, `merger`, `ownership_change`) would silently exclude any future disclosure tagged `acquisition`, with no warning that this is even possible. No `acquisition`-typed rows exist in the database today, so this has not yet manifested as a real exclusion — but it is a live, checkable gap in the taxonomy-to-scope mapping, not a hypothetical.

**Finding F4 (MINOR) — §14D's "11 GMC/CIR-type events" Stage 12 citation overstates the real corpus.**

§14D states: *"re-confirmed working correctly via Stage 12's real production ingestion of 11 GMC/CIR-type events with 0 false rejections and 0 false collisions."* `docs/STAGE12_NEWS_INFORMATION_ECONOMICS_VALIDATION_2026-08-08.md` line 222 does document "11/11 events accepted" for that stage's batch — but that batch's own line 56 shows only 2 of those 11 were tagged "corporate action" (DEAPCAP, LEGENDINT) in that stage's own breakdown, and the current `events` table shows only 6 GMC/CIR-type rows exist in total across Stages 11-13 combined, not 11. The "11" figure appears to be the count of all events (mixed types, including e.g. the REGALINS/UNIVINSURE regulatory-action suspension) accepted in that batch, not a count of GMC/CIR-typed events specifically. The underlying substantive point (within-source dedup worked correctly, 0 false rejections/collisions) is plausible and not contradicted by anything found here — but the specific number cited to back it is not what a live count of GMC/CIR-typed rows supports.

## G. Zero-write guarantee

- `SELECT COUNT(*) FROM events` — before: **171**; after: **171**.
- `SELECT COUNT(*) FROM extracted_facts` — before: **461**; after: **461**.
- `SELECT COUNT(*) FROM documents` — before: **11551**; after: **11551**.
- `configs/h011_size.toml` — mtime `Jul 22 09:08`, md5 `fecc0e99279068675346cf898f16a627`, unchanged before/after.
- `docs/PREREG_H-011.md` — mtime `Jul 22 09:07`, md5 `de84a066ff3fafe6cb665710d4de1fc5`, unchanged before/after.
- No file matching `*H-019*`/`*h019*` exists anywhere in the repository (recursive search, excluding `.git`).
- No INSERT/UPDATE/DELETE/CREATE was issued against `data/ngx.sqlite` at any point in this review; only `SELECT` queries were run, via read-only Python `sqlite3` connections.

All zero-write guarantees hold.

---

## Findings table

| Severity | Section | Failure mode | Concrete example | Can silently corrupt dataset? | Recommended remediation (not implemented) |
|---|---|---|---|---|---|
| **BLOCKING** | §14D (cross-outlet linkage) | The "two different `source_id`s" trigger that both the ingestion-time and dataset-build-time corroboration procedures depend on is structurally unsatisfiable: the real `sources` table assigns the **same** `source_id=16` to both approved outlets by deliberate, documented convention (`STAGE10E...md` line 63: "Same source, correctly shared"). Worse, `event_pipeline.validate_batch()`'s actual `same_src` check (`event_pipeline.py:157`) keys on `provider.info.name` (the ingestion batch identity), so a genuine second-outlet submission is auto-routed to `REJECT`/`RESTATEMENT` before ever reaching the `CONFLICT` path or a human identity-content comparison. | A MarketForces Africa report of an event already ingested from Nairametrics, submitted through the same `stage10c_news_pilot` provider, is silently dropped (`REJECT`) or silently appended as a same-source restatement (`RESTATEMENT`) — never flagged `candidate_corroboration_unconfirmed`, never reviewed by a human. §14H's `source` field would read `"stage10c_news_pilot"` for every row, not the actual outlet name. | **Yes** — either loses a genuine corroborating observation entirely, or silently merges/overwrites two distinct outlets' reports under one `event_uid` without the disclosed human judgment step ever running. | Register a distinct `source_id` per outlet (or add an outlet field derived from `source_url`/byline that both the pipeline's `same_src` check and §14D's matching query key on instead of `source_id`), and re-verify against a live query — not by re-reading the pipeline code in isolation, per the lesson §14E's own correction already states. |
| **BLOCKING** | §14H (`source_document_id`) | The claim "all Stage 11/12 GMC/CIR events do have one [`documents` row]" is false: all 3 current `management_change` (GMC) events have no matching `documents` row by exact `source_url` join; only the 3 CIR events resolve. | Events 178 (SUNUASSUR), 179 (UNIVINSURE), 180 (VERITASKAP) — `source_url` values do not appear anywhere in `documents`. A real, on-topic NGX primary filing (`doc_id=11152`, titled `SUNU_ASSURANCES...BOARD_CHANGES...`, filed 2026-04-08) exists in `documents` for the same ticker three days before event 178's `announced_date`, but is not linked to it. | **Yes** — a naive ticker/date-proximity backfill (the natural workaround once the exact-URL join is found to return nothing) risks silently attaching the wrong document's evidentiary chain to a GMC event. | State explicitly that `source_document_id` is NULL for the current GMC family, do not claim completeness, and either backfill the missing `documents` rows for the 3 GMC source articles or specify that a dataset-build process must tolerate/flag NULL `source_document_id` rather than assume a join will resolve. |
| **SIGNIFICANT** | §14I | "3 of the 4 GMC events processed through the real pipeline in Stage 12 had effective_date < announced_date" does not match a live query: there are only 3 `management_change` rows in `events`, and all 3 (100%, not 75%) show `effective_date < announced_date`. | Rows 178, 179, 180 — every one has `effective_date < announced_date`. | No (the underlying instruction — use `knowledge_timestamp`, not `event_date`, as the join key — remains correct; the cited statistic supporting it is simply wrong). | Re-derive and correct the statistic from a live query before treating §14I as frozen, per the exact discipline §14E's own round-3 correction already models. |
| **SIGNIFICANT** | §14A / §14C / §14F | The real SUNUASSUR row (`event_id=178`) bundles two distinct named-individual GMC actions (Bakare resignation, Adaramola appointment) into one `events` row/`event_uid`/`direction` value, contradicting §14A's own canonical key (differentiated by `named_individual_role`) and §14F's explicit "simultaneous events... retained as separate rows" rule. | `events.headline` for id 178 names two different people in two different roles undergoing two different actions on the same `announced_date`, stored as a single row. §14C's own worked-example table treats them as two separate items despite this. | Not in this specific instance (both halves happen to resolve to the same NEUTRAL direction) — but the general case is unhandled: two conflated actions with *different* objectively-correct directions would silently produce one wrong/blended direction value with no mechanism to catch it. | Specify a rule for detecting and splitting an already-ingested row that bundles more than one qualifying disclosure sharing a ticker/event_type/date but differing identity fields, before such a dataset-build process trusts one row = one event. |
| MINOR | §14A / taxonomy | `configs/event_taxonomy.toml`'s `[corporate]` category has a distinct `acquisition` leaf, semantically overlapping with CIR's in-scope `ownership_change`, with no rule in §14A for which leaf a stake-acquisition disclosure should be tagged under. | §14A's own language "an externally-disclosed acquisition of a substantial shareholding" is equally consistent with `event_type='acquisition'` as with `'ownership_change'`. No `acquisition`-typed rows exist yet. | Yes, prospectively — a future acquisition disclosure tagged `acquisition` would be silently excluded from CIR by §14I's event-family filter with no warning. | Add an explicit disambiguation rule (or explicitly fold `acquisition` into CIR's scope) before the next batch of CIR-candidate articles is ingested. |
| MINOR | §14D | "Stage 12's real production ingestion of 11 GMC/CIR-type events" overstates the real corpus — only 6 GMC/CIR-typed rows exist in `events` currently; the "11" figure traces to a mixed-type batch count, not a GMC/CIR-specific one. | `STAGE12...md` line 222 ("11/11 events accepted") vs. live `events` query (6 GMC/CIR rows total across all stages). | No (the underlying dedup-reliability point is plausible and not contradicted) — but it is an unverified citation. | Correct the citation to the actual GMC/CIR-typed count, or cite the mixed-type figure accurately as such. |

---

## NOT READY — STOP BEFORE H-019.

Two BLOCKING defects were found (§14D's cross-outlet corroboration mechanism is unreachable against the real `sources`/pipeline architecture; §14H's `source_document_id` completeness claim is false for the entire current GMC family), plus two further SIGNIFICANT defects (a wrong statistic in the "frozen" §14I; a real, already-ingested event row that violates the specification's own canonical-key and simultaneous-events rules). Per this round's explicit brief, these are not rounded up or softened to MINOR. H-019 construction remains correctly blocked. These findings should be corrected and this document should go through a further review round — ideally one that, per the pattern in every prior round, re-verifies live rather than trusting this round's log either.
