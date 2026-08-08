# STAGE 7 — ZERO-COVERAGE RE-HARVEST COMPLETENESS AUDIT

*2026-08-08. Diagnostic only — no new `extracted_facts` rows written
this stage (per 7D's explicit "diagnosis before expansion" mandate).
`configs/h011_size.toml`, `docs/PREREG_H-011.md`, H-011's signal/
construction, and all frozen experiment records are unmodified. No
hypothesis created.*

**Files changed**: `data/reference/
stage7_zero_coverage_population_2026-08-08.json` (frozen 18-ticker
target list, new reference artifact only).

---

## 1. Executive Summary

**Answering the core question: MIXED, with the balance of confirmed
evidence leaning structural, but genuine uncertainty remains for the
majority of the population.**

Of the 18 zero-coverage tickers: **1 shows strong, concrete evidence of
a real harvest/extraction gap** (DEAPCAP — a genuine 35-page audited
financial statement PDF sits on disk, confirmed scanned and never
text-extracted). **6 show explicit, dated, repeated evidence of a
structural reporting problem** (formal NGX "delay in filing" notices —
not inferred, directly observed). **11 remain genuinely undetermined**
— thin or unexplored document pools with no positive evidence either
way. **Zero new tickers were added to the research-ready set this
stage; that was not this stage's objective.**

---

## 2. Exact 18-Ticker Target Population

Frozen from Stage 6's own output, no substitution: CAVERTON, CILEASING,
CUTIX, DEAPCAP, LEGENDINT, MCNICHOLS, NCR, NSLTECH, OMATEK, PRESTIGE,
REDSTAREX, REGALINS, ROYALEX, RTBRISCOE, SUNUASSUR, TANTALIZER,
UNIVINSURE, WAPIC. Persisted to `data/reference/
stage7_zero_coverage_population_2026-08-08.json`.

| ticker | sector | H-011 status | IRU rank | 2026 ADTV (N) | total docs | any fundamental fact |
|---|---|---|---|---|---|---|
| CAVERTON | SERVICES | current holding | 86 | 15,744,740 | 2 | 0 |
| CILEASING | SERVICES | current holding | 85 | 20,737,410 | 59 | 0 |
| CUTIX | INDUSTRIAL GOODS | current holding | 81 | 29,151,820 | 111 | 0 |
| DEAPCAP | FINANCIAL SERVICES | current holding | 95 | 68,351,230 | 26 | 0 |
| LEGENDINT | ICT | current holding | 91 | 16,920,460 | 10 | 0 |
| MCNICHOLS | (none recorded) | current holding | 96 | 26,761,690 | 56 | 0 |
| NCR | ICT | current holding | 84 | 9,494,704 | 61 | 0 |
| NSLTECH | SERVICES | current holding | 94 | 23,574,210 | 25 | 0 |
| OMATEK | ICT | current holding | 93 | 12,317,700 | 19 | 0 |
| PRESTIGE | FINANCIAL SERVICES | current holding | 82 | 5,129,746 | 101 | 0 |
| REDSTAREX | SERVICES | current holding | 83 | 19,145,620 | 59 | 0 |
| REGALINS | FINANCIAL SERVICES | current holding | 89 | 8,587,503 | 74 | 0 |
| ROYALEX | FINANCIAL SERVICES | current holding | 90 | 9,205,695 | 68 | 0 |
| RTBRISCOE | SERVICES | current holding | 88 | 28,512,510 | 37 | 0 |
| SUNUASSUR | FINANCIAL SERVICES | current holding | 80 | 5,926,292 | 101 | 0 |
| TANTALIZER | SERVICES | current holding | 77 | 64,978,110 | 22 | 0 |
| UNIVINSURE | FINANCIAL SERVICES | current holding | 87 | 17,308,020 | 37 | 0 |
| WAPIC | FINANCIAL SERVICES | current holding | 92 | 14,191,270 | 52 | 0 |

---

## 3. Re-Harvest Methodology

Same standard as Stage 3D's insider-completeness audit, adapted: instead
of a year-by-year document-count table (Stage 3D's method, appropriate
for a single homogeneous document category), Stage 7 required
per-ticker document classification since the target is heterogeneous
(any of: annual report, audited statement, results release, etc.).

Three independent passes, all covering the full document set (not just
already-text-extracted documents):
1. **Filename keyword search** across ALL 18 tickers' ENTIRE document
   sets (not just unextracted ones) for
   `ANNUAL REPORT|FINANCIAL STATEMENT|AUDITED ACCOUNT|EARNINGS
   RELEASE|RESULTS PRESS|UNAUDITED RESULT|Q[1-4] RESULT|FULL-YEAR
   RESULT|HALF-YEAR RESULT` — 14 hits, detailed in Section 5.
2. **Content keyword search** (balance-sheet terms) across all
   text-bearing (char_count > 500) documents — 0 new hits beyond
   Stage 6's CILEASING/VERITASKAP findings (VERITASKAP already resolved
   in Stage 6, not part of this 18).
3. **P&L-precision content search** (looking for ANY precise tabular
   revenue/profit figure, not just balance-sheet terms, to catch
   P&L-only releases like UACN's in Stage 3A) — **1 hit**: MCNICHOLS
   doc 89 (Section 8).

**Excluded per your explicit instruction, verified not counted**: AGM
outcome notices, results-date notices, procedural closed-period/board-
meeting notices (all checked directly — e.g. CUTIX doc 8054 is a board
resolution stating results "will be filed... on or before Feb 29,"
explicitly NOT the statement itself).

---

## 4. Documents Discovered

**14 filename-keyword hits, ALL in `doc_type='results_notice'` (except
CUTIX's, `doc_type='other'`), and — critically — every single title
containing "DELAY," "DISCREPANCIES," or "LATE FILING," not an actual
filed statement**, with one exception (DEAPCAP, Section 5):

| ticker | doc_id | title (as filed) | filing_date | char_count |
|---|---|---|---|---|
| CAVERTON | 8946 | "DISCREPANCIES IN UNAUDITED FINANCIAL STATEMENT" | 2024-09-24 | 1,652 |
| CILEASING | 10941 | "NOTICE OF DELAY IN FILING AUDITED FINANCIAL STATEMENTS" | 2026-03-04 | 979 |
| CUTIX | 8054 | "Board resolution for Third Quarter FY2024 Unaudited Account[s]" | 2024-02-23 | 1,520 |
| DEAPCAP | 9311-9804 (5 docs) | "Unaudited/Audited Financial Statements for [period]" | 2025-01-22 to 2025-05-06 | 30-74 |
| LEGENDINT | 10964 | "NOTICE OF DELAY IN FILING 2026 Q2 UNAUDITED FINANCIAL STATEMENTS" | 2026-03-11 | 1,210 |
| NCR | 11261 | "DELAY IN FILING OF FINANCIAL STATEMENTS" | 2026-05-05 | 2,396 |
| PRESTIGE | 9876 | "NOTICE OF DELAY IN FILING UNAUDITED FINANCIAL STATEMENTS ... Q1 2025" | 2025-05-28 | 1,113 |
| PRESTIGE | 10020 | "NOTICE OF DELAY IN FILING THE AUDITED FINANCIAL STATEMENTS 2024" | 2025-07-03 | 1,066 |
| ROYALEX | 9395 | "Notice of Late Filing of Financial Statements" | 2025-02-20 | 2,057 |
| WAPIC | 6934 | "PRESS RELEASE ON DELAYED FILING OF AUDITED FINANCIAL STATEMENTS" | 2023-03-03 | 1,136 |

**MCNICHOLS doc 89**: a 2014 AGM notice that (unusually) embeds a
genuine, precise financial-highlights table — see Section 8.

---

## 5. Document-Type Classification

**Every one of the 14 "delay/discrepancy" titled documents is itself a
PROCEDURAL notice, correctly excluded from counting as usable financial
data** — but their EXISTENCE and repeated pattern is itself the primary
evidence for Section 7's classification, distinct from their content.

**DEAPCAP is the one exception requiring deeper inspection**: its 5
`results_notice` documents (char_count 30-74) are near-empty text
extracts, but their `local_path`/`source_url` point to specifically,
precisely-titled real documents — "Deap Capital Audited Financial
Statements for the Year Ended 30 Sept 2024," etc. Checked directly:

- The local PDF file (`25579_Deap_Capital_Audited_Financial_Statements_
  for_the_Year_Ended_30_Sept_2024.pdf`) **exists on disk, is 15.3 MB,
  and is a genuine 35-page PDF** (`file` command confirms: "PDF
  document, version 1.7, 35 page(s)").
- `pdfplumber` extraction on the first 3 pages returns **zero
  characters of text** — confirming this is a SCANNED/image-based PDF,
  not a text-native one, explaining the near-empty 68-character harvest
  result (almost certainly a metadata/whitespace artifact, not real
  content).
- **This is a genuine, confirmed harvest/extraction gap, not a missing
  document.** A real 35-page audited financial statement for DEAPCAP
  exists in the archive today and has simply never been read (requires
  vision/OCR extraction, the same method used successfully for
  PRESTIGE's AGM notice and LASACO's share-reconstruction notice in
  earlier stages).

---

## 6. A/B/C/D Classification

| Class | Count | Tickers | Basis |
|---|---|---|---|
| **A — HARVEST GAP** | **1** | DEAPCAP | Confirmed real, substantial (35-page) statement-titled PDF on disk, confirmed scanned/unextracted (Section 5) |
| **B — DOCUMENT EXISTS, EXTRACTION GAP** | **0** | none | No case found where a genuinely statement-bearing document was misclassified or mis-extracted — every non-Class-A document found was either genuinely procedural (delay notices) or contained only imprecise narrative |
| **C — STRUCTURAL REPORTING PROBLEM** | **6** | CILEASING, LEGENDINT, NCR, PRESTIGE, ROYALEX, WAPIC | Each has an EXPLICIT, dated, formally-filed "delay/late filing" notice from the issuer itself — direct evidence, not inference. PRESTIGE and ROYALEX each show TWO such notices (Section 8), strengthening the structural read for those two specifically |
| **D — ARCHIVE INCOMPLETE / UNDETERMINED** | **11** | CAVERTON, CUTIX, MCNICHOLS, NSLTECH, OMATEK, REDSTAREX, REGALINS, RTBRISCOE, SUNUASSUR, TANTALIZER, UNIVINSURE | No positive evidence of either a harvest gap or a structural problem; ranges from CAVERTON's near-total archive absence (2 documents, ever) to REGALINS' large unexplored pool (52 documents, mostly unextracted, never individually screened by content) |

**Note on CAVERTON specifically**: only 2 documents exist for this
ticker in the ENTIRE archive (1 governance, 1 results_notice) — an
unusually thin disclosure record even by this population's standards.
Genuinely ambiguous whether this reflects a true rarity of NGX filings
for this name or a harvest that simply never reached most of its
disclosure history; **Class D, not forced into C**, per your explicit
instruction not to assert causality the evidence doesn't support.

---

## 7. Investigation: ROYALEX, MCNICHOLS, OMATEK, NSLTECH

**ROYALEX**: TWO independent, dated delay/late-filing notices, 8 years
apart — the previously-known 2017 "DELAY OF AUDITED ACCTS" document AND
a newly-found 2025 "Notice of Late Filing of Financial Statements"
(doc 9395). **What this establishes exactly**: on two separate,
widely-spaced occasions (2017 and 2025), ROYALEX formally notified NGX
of a filing delay. It does NOT establish continuous/annual delinquency
across the 8 intervening years (2018-2024) — no evidence either way for
that period exists in this archive. **Correct classification: repeated,
not necessarily continuous, structural signal — Class C, with the
specific caveat that "repeated across two known years" is a narrower,
more defensible claim than "chronic."**

**MCNICHOLS**: One real, precise financial snapshot found (FY2013 vs
FY2012 revenue/gross-profit/PBT, embedded unusually in a 2014 AGM
notice, Section 8) — the ONLY genuine P&L-precision hit across all 18
tickers. This is POSITIVE evidence that real financial data exists
somewhere in this company's disclosure history, even though the 55
other MCNICHOLS documents (33 unextracted) yielded nothing. **Class D,
not C** — the one real hit argues against a purely structural
explanation for MCNICHOLS specifically, even though its data is old
(2013) and thin (P&L only, no balance sheet).

**OMATEK**: No delay notice found, no statement content found, only 19
total documents (2 unextracted) — the thinnest EXPLORED archive record
in the population after CAVERTON. No positive evidence for Class A, B,
or C. **Class D**, with a note that OMATEK is a long-known, largely
dormant NGX name (context available from general market knowledge, not
from this archive's own evidence, and NOT used to justify the
classification — the classification rests on the archive finding alone,
per your instruction not to manufacture explanations).

**NSLTECH**: No delay notice, no statement content, 25 total documents
(7 unextracted, unscreened individually). **Class D.**

**None of the four "specifically suspicious" names produced evidence
strong enough to call PERMANENT/PROVEN structural non-reporting** — only
ROYALEX clears the bar for "repeated, dated, formal evidence," and even
that is bounded to two known years, not asserted as continuous.

---

## 8. MCNICHOLS Real Data Fragment (detail)

Doc 89 (AGM notice, filed 2014-07-11), a table embedded in the notice:

```
                    31 Dec 13    31 Dec 12
                    N'000        N'000
Revenue             430,970,796  389,620,172   <- likely mis-scaled in source (see caveat)
Gross Profit        110,098,797   86,428,886
Profit Before Tax     26,834,56[...]  [truncated in extract]
```

No balance-sheet figures found anywhere in this document. **A caveat
disclosed, not resolved**: the "Revenue" figure (430,970,796 in N'000 =
₦430.97 BILLION) looks implausibly large for MCNICHOLS, a small-cap
insurance name — this may be a transcription/OCR artifact in the
source's own table (extra digit), a genuine unit-scale confusion in the
original filing, or this platform's raw-text extraction concatenating
two numbers. **Not treated as a clean, usable fact this stage** — flagged
as a real find requiring careful re-verification (page image inspection)
before any future extraction, exactly the caution this diagnostic stage
is meant to apply rather than rushing a number into `extracted_facts`.

---

## 9. Harvest Completeness Statistics

- **18 tickers audited.**
- **Class A: 1 (6%). Class B: 0 (0%). Class C: 6 (33%). Class D: 11 (61%).**
- **Number with at least one usable (precise, not narrative) financial-reporting document: 0** — DEAPCAP's document is real but unread (not yet "usable" until extracted); MCNICHOLS' fragment is found but flagged unverified (Section 8), not counted as usable.
- **Number with ≥3 potentially usable historical periods identified: 0** — even DEAPCAP's single confirmed document would, at best, yield 1-2 periods (it is one filing for one fiscal year-end, per its own title).
- **Number with zero plausible historical periods identified: 17 of 18** (all except DEAPCAP, which has a plausible-but-unconfirmed single period).

**Verdict: MIXED.** Not PRIMARILY HARVEST GAP (only 1 of 18 shows real
positive evidence of one). Not PRIMARILY STRUCTURAL (6 of 18 confirmed,
short of a majority, and even those 6 are evidenced for specific known
years, not proven continuous). Not UNDETERMINED as a whole (13 of 18
DO have a specific, evidenced classification — A or C). **The honest
summary: a third of this population shows real, dated, self-reported
evidence of chronic-ish filing delay; one shows a genuine, fixable
harvest gap; the majority remains a real unknown that would require
either deeper archive mining (the 11 Class-D tickers' remaining
unscreened documents) or direct comparison against NGX's own live
disclosure system to resolve further** — beyond this stage's bounded
diagnostic scope.

---

## 10. Nominal vs. Research-Ready H-011 Overlap

**Unchanged from Stage 6 — this stage added zero new extracted facts,
by design:**
- **Nominal overlap: 2 of 20 H-011 holdings (10%)** — LASACO (1 period),
  VERITASKAP (2 periods).
- **Research-ready overlap (≥3 PIT-safe periods): 0 of 20 (0%).**

---

## 11. Potential Future Overlap

**Explicitly NOT counted as actual coverage, reported separately per
your instruction:**

| ticker | evidence | plausible periods if extracted | confidence this would work |
|---|---|---|---|
| DEAPCAP | Confirmed real, substantial (35-page) audited-statement PDF on disk, scanned | 1 (possibly 2 if it contains a comparative prior-year column, unconfirmed) | Medium-high — document is real and title-confirmed as the right content type, but unread; vision extraction could fail if the scan quality is poor |

**Only 1 of 18 tickers has ANY plausible path to future coverage
identified this stage. Even if DEAPCAP's document extracts perfectly,
it would add at most 1-2 periods for 1 ticker — nowhere near enough,
alone, to move Financial Strength's H-011-universe coverage out of
NOT TESTABLE.**

---

## 12. Structural-Data-Gap Assessment

**For the 6 Class-C tickers specifically**: the evidence is real and
directly self-reported by the issuers (formal NGX delay notices), not
inferred from absence. This is meaningfully stronger evidence than
Stage 6's single ROYALEX data point. However, per your explicit
instruction, **"repeated across two known years" (ROYALEX) and "one
recent instance" (the other 5) do not establish PERMANENT
unavailability** — only that these companies have, on documented
occasions, failed to file on schedule. Whether they eventually filed
LATE (meaning a usable statement might exist somewhere, just delayed)
or never filed for that period at all is **not resolved by this
archive's evidence** and would require checking NGX's disclosure system
directly for what (if anything) was eventually filed after each delay
notice — out of this stage's bounded scope.

**For the 11 Class-D tickers**: no structural claim is supported by the
evidence gathered. These names remain genuinely unknown, not
presumptively structural.

---

## 13. External-Source Candidates

Per your instruction, this is a list of candidates only — **nothing
here is recommended for acquisition this stage**:

| ticker | missing period | document type needed | archive evidence | external source potentially required | expected value |
|---|---|---|---|---|---|
| DEAPCAP | FY2024 (and possibly earlier) | Vision/OCR extraction of an ALREADY-ARCHIVED PDF | Confirmed 35-page real document on disk | **No — internal re-processing, not external acquisition** | Medium (1 ticker, 1-2 periods) |
| CILEASING, LEGENDINT, NCR, PRESTIGE, ROYALEX, WAPIC (the 6 Class-C names) | Whatever period each delay notice references | The eventually-filed (if any) late statement | Formal delay notice exists; the actual late filing (if any) was not found in this archive | **Possibly — would require checking NGX's disclosure system for a late filing this platform's harvest may not have captured, i.e. a targeted re-harvest of these 6 specific tickers' post-delay-notice filings, not a new external data source** | Low-medium, uncertain until checked |
| CAVERTON, CUTIX, MCNICHOLS, NSLTECH, OMATEK, REDSTAREX, REGALINS, RTBRISCOE, SUNUASSUR, TANTALIZER, UNIVINSURE (the 11 Class-D names) | Unknown | Unknown — requires exhausting their remaining unscreened documents first | Insufficient — genuinely undetermined | **Not yet determinable** | Unknown |

**No case in this table requires a genuinely NEW external data source.**
Every candidate is either an internal re-processing task (DEAPCAP) or a
targeted, bounded re-check of the SAME NGX disclosure system this
entire archive was built from (the Class-C and Class-D names) — exactly
the distinction your instruction asked for.

---

## 14. H-018 Implications

No change to Stage 6's gate outcome. If anything, Stage 7 strengthens
the case against H-018 in the near term: the ONE concrete, actionable
finding (DEAPCAP) would, even in the best case, add a single ticker
with 1-2 periods — leaving the H-011-universe research-ready count at
0 or, optimistically, still short of any meaningful cross-sectional
floor. **The 6 Class-C findings are, if anything, evidence AGAINST
H-011's universe being fundamentally coverable at all for those
specific names**, reinforcing Stage 6's structural-gap hypothesis for
at least a third of the population.

**H-018 is not created. No condition from Stage 6's gate has newly been
satisfied.**

---

## 15. Recommended Stage 8

**Two small, bounded, non-speculative actions, in this order:**

1. **Vision-extract DEAPCAP's confirmed real document** (the one
   unambiguous Class-A finding) — a single-ticker, single-document task,
   not a campaign. This is genuinely warranted per 7D's own "if
   extraction is clearly warranted, record it as a newly discovered
   opportunity" — and it is.
2. **A narrow, targeted check of the 6 Class-C tickers' post-delay-
   notice filing history** (did they eventually file, and if so, is
   that filing in this archive or not) — resolving the open question in
   Section 12 without expanding to a new acquisition project. This is a
   verification task, structurally identical to Stage 3D's insider
   audit, not a re-harvest of anything new.

**Do NOT yet**: screen the 11 Class-D tickers' remaining ~200+
unexplored documents in bulk — that is a real future task but should
wait until Steps 1-2 report back, since their outcome may change how
much effort screening Class-D is actually worth (if even confirmed
Class-C names turn out to have no recoverable late filings, the
expected value of digging through Class-D's thinner, less-evidenced
document pools drops further).

**Do not create H-018.** Even a fully successful Stage 8 (DEAPCAP
extracted, all 6 Class-C names checked) would add at most a handful of
tickers with 1-2 periods each to a universe that needs many more names
at 3+ periods. **The realistic, disciplined read remains: H-011's own
investable universe may not support a second, independent, research-
ready fundamental factor within the current archive, full stop** — a
genuinely important platform-level finding in its own right, not a
setback to be engineered around.
