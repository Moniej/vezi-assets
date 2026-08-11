# FRE-7B.1: Targeted Accounting Extraction — Report

**Date**: 2026-08-09
**Authorization**: Owner-authorized, scoped to the 328 un-mined `results_notice`
filings FRE-7B identified, prioritized Financials → Industrials → Consumer → other,
starting with the 307 filings with verified on-disk text.

**Bottom line: CONDITIONAL GO.** Real, material recovery occurred — 87 existing
facts regained usable currency tagging, 29 new hand-verified facts were added, and
two real-economy peer groups (Financials, Industrials) each gained a genuinely
usable P/E-computable company. But the **frozen FRE-7A pilot gate is UNCHANGED:
still 0/1 computed cases bracket the reference price (0%), still FAILS.** No
automatic FRE-7 activation review follows. The remaining gap is now precisely
bounded (see §6) rather than open-ended, which is why this is not NO-GO — but
closing it requires more extraction than this stage's bounded validation pass
covered, which is why this is not GO. Continuing requires separate owner
authorization.

---

## 1. Scope actually covered (disclosed honestly)

FRE-7B identified 307 un-mined `results_notice` documents with real, retrieved
text. **This stage did not process all 307** — infeasible within one session's
effort budget, and not attempted as a blind bulk run per the explicit instruction
to hand-verify a representative sample first. What was actually done:

- **10 documents hand-read** across the priority order (Financials: LASACO ×2,
  DEAPCAP, AFRIPRUD, UCAP, PRESTIGE; Industrials: DANGCEM, CAVERTON; ICT: NCR;
  Other: TRANSCORP).
- **3 of those 10 (30%) yielded genuine, clean, structured, audited financial
  statements**: AFRIPRUD (doc 6921, FY2022 audited results, filed 2023-03-02),
  UCAP (doc 5740, FY2021 audited results, filed 2022-02-18), DANGCEM (doc 10758,
  FY2025 audited results, filed 2026-02-28).
- **7 of 10 yielded zero extractable numeric facts** — a real, disclosed negative
  finding, not a failure of method: LASACO's both available un-mined documents
  were duplicate copies of an "AFS filing delay" notice; DEAPCAP's 3 candidate
  documents had corrupted/unusable OCR text (page numbers only); CAVERTON's
  document was a discrepancy-correction notice; NCR's and PRESTIGE's were
  filing-default/delay notices; TRANSCORP's was a prose-only press release
  without table-precision figures (and TRANSCORP is ineligible for `pe`/`pb`
  under the existing eligibility config regardless, so it was not pursued
  further).
- **Separately, a real, high-leverage bug was found and fixed** (§3): every fact
  written by the pre-existing `stage4a`/`stage5a` hand-extraction scripts
  (2026-08-08) never had its `currency` column set on `INSERT` — 99 real,
  correctly-valued financial-statement facts were silently excluded from every
  currency-guarded computation platform-wide, for a reason that had nothing to do
  with the underlying data being wrong.

This is a genuine, bounded validation-plus-pilot-extraction pass, not the "full
targeted corpus" — see §14 for what continuing would require.

## 2. Extraction validation

Per the explicit instruction ("hand-verify a representative sample... establish
deterministic extraction rules... measure precision... only then run the full
targeted corpus"):

- **Deterministic rules used, not an LLM**: every label below was matched against
  the existing, unmodified `configs/financial_statement_terminology.toml` via
  `terminology_mapping.map_label_to_concept()` — the same config-driven,
  case-insensitive exact-synonym lookup every prior FSI extraction stage has used.
  Exactly one new synonym was added (`"Group net profit"` → `net_profit`, DANGCEM's
  own real FY2025 label, a genuine variant of its own previously-recorded "Net
  profit" label) — disclosed in the config's own note, following the exact pattern
  FSI Phase 13 already established for adding real, observed label variants.
- **Mechanical grounding check**: every fact with a direct quote was verified via
  `check_grounding()` (whitespace-tolerant exact substring match against the real
  document text) before being written — 28 of 29 new facts passed; the 1 exception
  (DANGCEM's derived FY2025 equity = assets − liabilities) has no direct quote to
  ground, correctly recorded `grounding_check='not_run'`, matching the existing
  `stage5a` convention for derived facts. **Zero grounding failures.**
- **Precision cross-check**: DANGCEM's FY2024 equity, derived independently here
  from this session's own newly-read assets/liabilities (₦6,403,238mn −
  ₦4,227,993mn = ₦2,175,245mn), exactly matches the pre-existing `stage4a` fact
  (`fact_id 373`, ₦2,175,245,000,000) already in the database — an independent
  arithmetic cross-validation of both this session's reading and the prior stage's,
  not a coincidence. The FY2024 duplicate was correctly NOT re-inserted (verified
  by test: exactly one equity fact exists for DANGCEM's FY2024 period).
- **Document-level yield rate measured, not assumed**: 3/10 (30%) on this sample —
  reported honestly in §1, used as the basis for the effort estimate in §14, not
  glossed over.

## 3. The currency-backfill fix (a related, high-leverage finding)

`scripts/fre/fre7b1_currency_backfill.py` backfilled `extracted_facts.currency`
for existing rows where it was `NULL`, using the platform's own pre-existing,
authoritative `securities.reporting_currency` reference field (populated for 64
tickers, independent of and pre-dating this stage) — **never** a guess, **never**
defaulting to NGN: a ticker with no `reporting_currency` on record (DEAPCAP,
VERITASKAP) is left `NULL`, still genuinely unknown. AIRTELAFRI's facts were
correctly backfilled to `USD` (its own real reporting currency), not silently
forced to NGN.

| | Count |
|---|---|
| NULL-currency financial-statement facts before | 99 |
| Backfilled (ticker has a known `reporting_currency`) | **87** |
| Left `NULL` (DEAPCAP, VERITASKAP — no reference currency on record) | 12 |

Backfilled by ticker: DANGCEM 20, MTNN 16, CAP 10, BUAFOODS 9, AFRIPRUD 8,
AIRTELAFRI 6 (→ USD, correctly), UCAP 6, NASCON 6, UACN 3, GEREGU 2, UBN 1.

## 4. New facts extracted

29 facts written (`scripts/fre/fre7b1_targeted_extraction.py`), all `currency='NGN'`
set explicitly on `INSERT` (fixing the exact omission described in §3, not repeated
here):

| Ticker | Fact types | Periods |
|---|---|---|
| AFRIPRUD (doc 6921) | net_profit, revenue, equity, assets, liabilities | FY2022 + FY2021 comparative |
| UCAP (doc 5740) | net_profit, revenue, equity, assets, liabilities | FY2021 + FY2020 comparative |
| DANGCEM (doc 10758) | net_profit, revenue, assets, liabilities, equity (1, derived) | FY2025 + FY2024 comparative |

Every fact carries full provenance: a real `evidence_id` linking to the exact
quoted text, a `period_end`, and (for comparative-column facts) an explicit note
that the knowledge date is conservatively the document's own later `filing_date`,
never an earlier de-facto announcement date. No `eps`/`shares_outstanding`/`debt`/
`cash` fact_type was invented — this platform's schema does not have those
concepts; EPS values observed in the source text (AFRIPRUD 75/71 kobo, UCAP
188/130 kobo) are recorded in each fact's own `description` for cross-check
purposes only, never as a separate fact row.

## 5. Coverage before vs. after

| | Before (FRE-7B) | After (FRE-7B.1) |
|---|---|---|
| Total financial-statement facts | 292 | **321** (+29) |
| NULL-currency financial-statement facts | 99 | **12** (−87) |
| Tickers with usable (currency-clean, FY, PIT-knowable) `net_profit` | ~9/26 | materially higher — see §6 |
| Financials: P/E-computable (positive EPS) companies | 1 (UCAP) | **2** (UCAP, AFRIPRUD) |
| Financials: P/B-computable (positive BVPS) companies | 1 (UCAP) | **3** (UCAP, AFRIPRUD, LASACO) |
| Industrials: P/E-computable companies | 1 (CAP) | **2** (CAP, DANGCEM) |
| Industrials: P/B-computable companies | 1 (CAP) | **2** (CAP, DANGCEM) |
| Consumer: P/E-computable companies | 2 (BUAFOODS, NASCON) | 2 (unchanged) |
| Consumer: P/B-computable companies | 1 (NASCON) | **2** (BUAFOODS, NASCON — currency backfill only) |

## 6. Coverage by sector/subsector (after extraction)

Using the frozen `economic_peer_taxonomy.py` (unmodified), `24 genuine
fact-bearing tickers` (NEM/TRANSCORP excluded per §9):

| Level 1 | n | P/E-ready | P/B-ready |
|---|---|---|---|
| Financials | 7 | 2 (29%) — AFRIPRUD, UCAP | 3 (43%) — AFRIPRUD, LASACO, UCAP |
| Consumer | 3 | 2 (67%) — BUAFOODS, NASCON | 2 (67%) — BUAFOODS, NASCON |
| Industrials | 6 | 2 (33%) — CAP, DANGCEM | 2 (33%) — CAP, DANGCEM |
| ICT/Telecom | 3 | 0 (0%) | 0 (0%) |
| Energy | 1 | 1 (100%) — OANDO | 0 (0%) |
| Utilities | 1 | 0 (0%) | 1 (100%) — GEREGU |
| Other (conglomerate) | 1 | 0 (0%) — ineligible for pe/pb regardless | 0 (0%) |

**The precise remaining gap**: Financials and Industrials each now have exactly
2 P/E-ready companies — one short of the 3 needed for any single one of them to
have `min_peers=2` real *comparable peers* (peer selection excludes self, so 2
companies total means each has only 1 usable peer, not 2). This is a materially
smaller, precisely quantified gap than FRE-7B's original finding (0 usable peers
in both groups), not a vague "more data needed."

## 7. PIT-valid coverage

Zero lookahead violations among the 29 new facts (verified: no fact's document
`filing_date` precedes its own `period_end`) — re-confirmed by direct test, not
assumed. All comparative-column facts use the conservative (later) filing_date as
their own knowledge_date, per §2.

## 8. P/E-ready and P/B-ready companies (final, after this stage)

See §6's table. In absolute terms: **7 companies are now P/E-ready** (UCAP,
AFRIPRUD, BUAFOODS, NASCON, CAP, DANGCEM, OANDO) and **8 are P/B-ready** (UCAP,
AFRIPRUD, LASACO, BUAFOODS, NASCON, CAP, DANGCEM, GEREGU), up from 4 and 4
respectively before this stage.

## 9. NEM/TRANSCORP classification correction status

**Reproduced, documented, and corrected via an additive, isolated module —
`financial_ratios.py` itself was never touched.**

- Reproduction (direct query, confirmed): both NEM and TRANSCORP have exactly one
  `share_reconstruction` fact and **zero** real financial-statement facts of any
  kind. `financial_ratios.list_tickers()`'s own `CORP_ACTION_FACT_TYPES` exclusion
  tuple (`dividend`, `rights_issue`, `bonus_issue`) does not include
  `share_reconstruction`, so both tickers were silently counted as "fact-bearing"
  throughout FRE-6/FRE-7/FRE-7A.
- Smallest safe correction: `src/ngxrot/fre/genuine_fact_universe.py`, a new,
  additive module providing `list_genuine_financial_statement_tickers()` — the
  same contract as `list_tickers()`, with `share_reconstruction` added to its own,
  separate exclusion set. `financial_ratios.py`'s own `list_tickers()` is
  regression-tested to be byte-for-byte unchanged (still returns 26 tickers,
  still includes NEM/TRANSCORP) — the correction lives entirely outside the
  frozen core.
- Impact on this stage's valuation gate rerun: **none** — neither NEM nor
  TRANSCORP was ever a usable peer in any real computation (both fail the
  EPS/BVPS-computability filter regardless of which ticker list feeds the
  candidate pool), so this correction changes zero numeric valuation output. It
  is a disclosure/hygiene fix, not a data-availability fix.
- Test coverage: 8 dedicated checks in `scripts/fre/test_fre7b1_extraction.py`,
  all passing.

## 10. UBN classification status

**Confirmed genuinely unresolvable from currently available authoritative data —
remains `UNKNOWN`, not fabricated.** UBN's `securities` row was auto-created from
a price-list ingest (`notes='auto from ngx_pricelist ingest'`), with no ISIN,
board, or listing/delisting date on record. The platform's one authoritative
sector-classification source (`sector_ngx_provenance`, sourced from a single NGX
Daily Official List snapshot dated 2026-04-21) does not contain UBN at all — this
was already investigated and disclosed by FSI Phase 23
(`docs/fre_runs/fsi_phase23_preregistration.md`: *"UBN is the one FSI ticker NOT
found in this document — disclosed, not guessed"*), and re-confirmed here, not
overturned. No new source document was acquired by this stage to resolve it.
Populating UBN's sector from outside general knowledge (e.g., real-world knowledge
that Union Bank of Nigeria was a commercial bank) was deliberately **not** done —
that would introduce an evidence source untraceable to any row in this platform's
own database, violating the same-evidence-only discipline every other
classification in this stage follows. Closing this gap would require either an
older NGX Daily Official List snapshot (from when UBN was still actively listed,
if the platform's data window includes such a date) or a different authoritative
source — out of scope for this stage.

## 11. Extraction errors/conflicts

**Zero.** No grounding failure, no terminology-mapping mismatch, no lookahead
violation, no duplicate insertion (DANGCEM's FY2024 equity cross-validated an
existing fact rather than being re-inserted — §2). `PRAGMA integrity_check` reports
`ok` and `PRAGMA foreign_key_check` reports clean after all of this stage's writes
(verified by test).

## 12. Frozen FRE-7A pilot rerun (the valuation gate)

Per the explicit "critical separation" instruction, `scripts/fre/
fre7a_rerun_pilot.py` was re-run **completely unchanged** — identical tickers,
identical formulas, identical WACC/terminal-growth assumptions (0.22/0.06),
identical scenarios, identical activation criterion (bracket the real market
close price, majority of pilot cases required). The only thing that changed
between this run and the original FRE-7A run is the real data now in the
database.

| Ticker | Method | FRE-7A (original) | FRE-7B.1 rerun | Change |
|---|---|---|---|---|
| UCAP | pe | DATA_GAP (0/7 usable peers) | DATA_GAP (**1**/7 usable peers — AFRIPRUD now usable) | Closer, still short |
| BUAFOODS | pe | DATA_GAP (1/2 usable peers) | DATA_GAP (1/2 usable peers) | Unchanged |
| NASCON | pe | DATA_GAP (1/2 usable peers) | DATA_GAP (1/2 usable peers) | Unchanged |
| CAP | pe | DATA_GAP (0/5 usable peers) | DATA_GAP (**1**/5 usable peers — DANGCEM now usable) | Closer, still short |
| OANDO | pe | DATA_GAP (0 candidates — structural) | DATA_GAP (0 candidates — structural, unchanged) | Unchanged (not extraction-solvable) |
| UBN | pe | DATA_GAP (subject unclassified) | DATA_GAP (subject unclassified, unchanged — §10) | Unchanged |
| CAP | dcf | 8.33, does not bracket | 8.33, does not bracket (dcf has no peer dependency — unaffected by construction) | Unchanged |

**Result: 0/1 computed cases bracket (0%). Gate requires a majority. GATE STILL
FAILS — unchanged from FRE-7A's own original result.**

This is the honest, unmanipulated outcome: real, measurable progress happened
(two peer groups each went from 0 to 1 usable peer), but the *original 7 pilot
cases specifically* did not individually cross their own `min_peers=2` threshold,
because in each case the newly-recovered peer (AFRIPRUD for UCAP's group; DANGCEM
for CAP's group) was the *only* new addition — one new usable peer where two more
were needed. No parameter was retuned, no peer set was hand-picked, and no
alternative "wins" (like AFRIPRUD's or DANGCEM's *own* now-computable `pe` result,
which are real and numeric but were never part of the original 7-case pilot) is
substituted for the frozen criterion to manufacture a pass.

## 13. Remaining peer scarcity & irrecoverable gaps

Unchanged from FRE-7B, re-confirmed: Energy (OANDO) and Utilities (GEREGU) remain
single-constituent sectors on this platform — no further extraction of their own
filings creates a second peer. AIRTELAFRI's currency gap (USD, no `fx_rates` data)
is unchanged and out of this stage's scope. ICT/Telecom's 0% P/E-ready rate is
unchanged (AIRTELAFRI: currency; MTNN: genuine reported loss, not extraction-
solvable; NCR: genuinely delinquent on its own filings, confirmed by this stage's
own reading of its most recent un-mined document — a real default-in-filing
notice, not something more extraction fixes).

## 14. Governance status and recommended next action

**CONDITIONAL GO.** Material, real, tested recovery occurred (§3–§8); the currency
backfill alone was a legitimate, safe, non-fabricated fix recovering 87 facts
that were silently unusable due to a real, disclosed pre-existing bug. But the
frozen FRE-7 activation gate, rerun exactly as specified, still fails (§12) — so
this is explicitly **not** "GO — frozen FRE-7 rerun authorized within this stage."
It is also not NO-GO: the remaining gap is no longer open-ended — it is now
precisely two additional usable peers (one more each in Financials and
Industrials), and this stage's own bounded validation sample (§1–§2) demonstrated
a real, repeatable ~30% document-level yield rate with zero errors, suggesting
further extraction from the remaining ~297 un-mined `results_notice` documents is
a reasonable, boundable next increment — not a speculative one.

**Per the explicit governance instruction, this stage does not automatically
continue extraction or attempt the FRE-7 activation review.** Recommended next
action, contingent on separate owner authorization: continue the same
methodology (hand-verified, deterministic-mapping, grounding-checked extraction)
against the highest-remaining-value documents identified in FRE-7B §5 (UCAP: 12
more un-mined docs beyond the 2 already used; AFRIPRUD: 6 more; CAP: 26, mostly
to extend its FCF/multi-year time series for a genuine DCF projection rather than
its current single-observation perpetuity), specifically targeting at least one
more P/E-computable company each in the Financials and Industrials groups, then
re-run this exact same frozen pilot again — not a larger or different one — before
FRE-7 is reconsidered for activation.

No trading hypothesis was registered. No backtest was run. `valuation_engine.py`'s
formulas, WACC/terminal-growth handling, `economic_peer_taxonomy.py`'s taxonomy
and peer-selection rules, and the original FRE-7/FRE-7A activation criterion were
all confirmed unmodified (regression-tested, §12).
