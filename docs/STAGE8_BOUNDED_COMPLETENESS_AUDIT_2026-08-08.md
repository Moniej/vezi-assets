# STAGE 8 — BOUNDED DATA-COMPLETENESS AUDIT

*2026-08-08. Real extraction (DEAPCAP only) and real archive search,
committed to `data/ngx.sqlite`. `configs/h011_size.toml`, `docs/
PREREG_H-011.md`, H-011's signal/construction, and all frozen
experiment records are unmodified. No hypothesis created. No
performance testing, no backtest.*

**Files changed**: 6 new `extracted_facts` rows (DEAPCAP, 2 periods).
No taxonomy or code change.

---

## 1. Executive Summary

**The question this stage exists to answer: is there enough fundamental
data inside H-011's universe to justify continuing the extraction
track? The evidence says no, not at present, and the shortfall is now
quantified rather than suspected.**

- **DEAPCAP's confirmed scanned document was fully processed.** It is
  real, legible (with effort), and internally consistent — and reveals
  a company in severe financial distress (negative equity of roughly
  -₦2.9bn against ~₦300m of assets, a ~10:1 liabilities-to-assets
  ratio). It adds 2 periods, not 3 — **DEAPCAP does not reach
  research-ready on its own, and no other document exists for it.**
- **The 11 previously-undetermined tickers were re-audited. 3 (REGALINS,
  RTBRISCOE, UNIVINSURE) now have strong, repeated, multi-year evidence
  of structural filing problems** — RTBRISCOE's evidence is the
  strongest found anywhere in this program: an archived 2021 notice
  states the company was **"In Receivership"** on its own letterhead, a
  formal insolvency status, corroborating a 2017 winding-up petition
  also found in the archive. **8 of 11 remain genuinely undetermined.**
- **The 6 delayed-filing names (Stage 7) were re-checked specifically
  for statements OUTSIDE their known delay notices. None were found —
  the archive holds nothing more for any of them.**
- **The MCNICHOLS 2014 fragment was investigated and correctly left
  unextracted** — the figures are real and traceable to MCNICHOLS' own
  AGM notice, but the revenue figure (₦431 billion) is implausible for
  the smallest-ranked name in the entire IRU, and the unit scale cannot
  be independently verified. Not written to the database.

**Final H-011-universe numbers: nominal overlap 3/20 (15%). Research-
ready overlap (≥3 periods): 0/20 (0%), unchanged.**

**Decision: C — MIXED, with the practically important qualifier that
the recoverable fraction is small and the confirmed-structural fraction
is now half the audited population.**

---

## 2. 8A — DEAPCAP: Full Processing of the Confirmed Document

The 35-page, 15.3MB scanned PDF (doc_id 9313) was rendered page-by-page
(pdfplumber, `to_image`) and visually scanned. **Page 10 (labeled page
"9" in the document) is the Statement of Financial Position as at 30
September 2024**, with a clean two-column (Sep-24 / Sep-23) layout.
Re-rendered at 300dpi for precise reading.

**Fields extracted** (only the bold, underlined, twice-cross-validated
TOTAL lines — sub-line items like the share-capital/deposit-for-shares
breakdown were legible with genuinely lower confidence and were
deliberately NOT extracted, per the instruction not to force ambiguous
OCR):

| field | Sep-2024 | Sep-2023 |
|---|---|---|
| Total Assets | ₦300,498,000 | ₦300,786,000 |
| Total Liabilities | ₦3,242,832,000 | ₦3,226,678,000 |
| Total Equity | **-₦2,942,332,000** | **-₦2,925,893,000** |

**Accounting identity check**: Sep-24: -2,942,332 + 3,242,832 =
300,500 (vs. stated 300,498 — 0.0007% rounding, immaterial). Sep-23:
-2,925,893 + 3,226,678 = 300,785 (vs. stated 300,786 — negligible).
**Both pass.** Cross-validated a second way: the document's own "Total
Equity and Liabilities" line independently repeats the Total Assets
figure exactly (300,498 / 300,786) — internal consistency confirmed
twice over.

**Grounding**: `grounding_check = 'not_run'` on all 6 facts — NOT
because verification was skipped, but because this platform's automated
text-substring check cannot run against a document with no text layer
(`pdfplumber` returns 0 characters on every page). This is disclosed
explicitly in each fact's `description` field, distinguishing "visually
verified against a rendered page image" from "no verification
performed." `extraction_confidence = 0.85` (not 1.0), reflecting
genuine, disclosed scan-quality degradation.

**PIT**: filing_date 2025-01-22. Sep-2024 period: lag 114 days, PASS.
Sep-2023 period (comparative column): lag 480 days, PASS, conservative-
dating caveat disclosed per this program's standing convention.

**Does DEAPCAP become Financial-Strength eligible? Yes — code-eligible
(assets+liabilities+equity present).** **Does it create research-ready
overlap with H-011? No — 2 periods, not 3, and no third document exists
anywhere in the archive for this ticker** (confirmed in Stage 6/7's
exhaustive search).

---

## 3. 8B — The 11 Undetermined Tickers: Re-Audit

Beyond Stage 7's content-keyword search, this stage ran a BROADER
filename search (`REPORT|ACCOUNT|STATEMENT|RESULT|PRESS RELEASE|
EARNINGS`) across **every** document (not just unextracted ones) for
all 11 tickers.

**Result: 19 filename hits, overwhelmingly NCCG (Nigerian Code of
Corporate Governance) compliance reports** — real, substantial
documents (30-58K characters) but governance/board-composition content,
verified by direct keyword re-check to contain **zero** financial
figures (spot-checked CUTIX's largest, 44,685 chars — no
assets/liabilities/revenue/profit hits).

**The one genuine break in this pattern**: unextracted-document filename
screening (a check Stage 7 had only applied narrowly) surfaced explicit,
repeated **delay/default-filing notices** for 3 tickers that Stage 7 had
left undetermined:

### RTBRISCOE — reclassified to **STRUCTURALLY SPARSE** (strongest evidence in this program)
- 2017: "DELAY IN FILING ACCTS," "LATE FILING OF Q1 ACCT," AND a
  **"WINDING UP PETITION"** document (a formal insolvency-proceeding
  filing).
- A document titled "FILING_OF_2020_AUDITED_FINA[NCIALS]" was
  investigated directly (the most promising lead in this whole audit —
  see below): it is in fact **another delay notice**, dated 1 March
  2021, and — independently, decisively — **the company's own
  letterhead on that document reads "R.T. Briscoe (Nigeria) PLC (In
  Receivership)."** Formal receivership is a stronger, more concrete
  structural signal than any delay notice alone.
- 2022: a further "NOTICE OF DELAY IN FILING OF 2022 END YEAR AFS."
- **Four confirmed, dated instances spanning 2017-2022, corroborated by
  an independent formal insolvency-status statement.** This is not an
  inference from absence — it is the company's own repeated, signed
  disclosure.

### UNIVINSURE — reclassified to **STRUCTURALLY SPARSE**
- **Seven** separate late/delayed-filing notices found: "LATE FILING OF
  2020 Q1 UFS" (2020), "LATE FILING OF AFS 2020" (2020), "LATE FILING OF
  2021 AFS" (2021), "LATE FILING OF 2022 Q1 UFS" (2022), "NOTICE OF
  DELAY IN FILING AFS 2023" (2023), "LATE FILING OF AFS 2024" (2025),
  "NOTIFICATION OF LATE FILING OF 2025 AFS AND 2026 Q1 UFS" (2026).
  **Essentially annual, for six consecutive reporting cycles (2020-2026)
  — the most temporally consistent pattern found in this program.**

### REGALINS — reclassified to **STRUCTURALLY SPARSE**
- Four instances: "NOTICE OF DEFAULT FILING" (2023-04), "NOTICE OF
  DEFAULT FILING" (2023-07), "DEFAULT FILING" (2024-03), "NOTICE OF
  DELAY IN FILING 2024 AFS" (2025).

**The remaining 8 (CAVERTON, CUTIX, MCNICHOLS, NSLTECH, OMATEK,
REDSTAREX, SUNUASSUR, TANTALIZER) show no positive evidence of either
type** (neither a real statement document nor a formal delay/default
notice) despite, for several, substantial document pools (SUNUASSUR 101
total documents, CUTIX 111, REDSTAREX 59). **Correctly left
UNDETERMINED AFTER AUDIT** — per your explicit instruction, absence of
found evidence is not proof of a structural problem; it may simply mean
these companies' genuine statement filings exist on NGX's disclosure
system but were never part of this platform's harvest. TANTALIZER's
single 2017 delay notice was found but is explicitly NOT treated as
sufficient for a structural classification (one isolated instance,
consistent with your instruction not to infer chronic problems from
isolated notices).

---

## 4. 8C — Six Delayed-Filing Names: Anything Beyond the Delay Notices?

Re-checked CILEASING, LEGENDINT, NCR, PRESTIGE, ROYALEX, WAPIC —
specifically their UNEXTRACTED document pools (Stage 7 had only checked
text-bearing documents for these 6).

| ticker | unextracted docs | filename hits (report/account/statement/result keywords) |
|---|---|---|
| CILEASING | 6 | 0 |
| LEGENDINT | 0 | n/a |
| NCR | 10 | 0 |
| PRESTIGE | 37 | 0 |
| ROYALEX | 41 | 1 (an NCCG governance report, same non-financial pattern as Section 3) |
| WAPIC | 22 | 0 |

**Answer: No.** The archive does not contain usable financial
statements outside the identified delayed filings for any of these 6
names. This was a genuine, not perfunctory, search — 116 additional
documents screened across the 6 tickers, zero statement-bearing hits.

---

## 5. 8D — MCNICHOLS Fragment: Investigated, Left Unextracted

**Source located precisely**: doc_id 89, MCNICHOLS CONSOLIDATED PLC's
own 9th Annual General Meeting notice, dated 7 May 2014, referencing
"the Statement of Financial Position as at 31st December 2013." A
financial-highlights table is embedded directly in the notice text:

```
                     31-Dec-13    31-Dec-12
                     N'000        N'000
Revenue              430,970,796  389,620,172
Gross Profit         110,098,797   86,428,886
Profit Before Tax     26,834,567   11,965,500
Profit After Tax      23,407,456    6,019,255
```

**This IS genuinely MCNICHOLS' own reported table** — the document
context is unambiguous (the company's own AGM notice, referencing its
own accounts). **It cannot be independently grounded or reconciled
under this platform's standard**: the stated Revenue figure (₦430.97
BILLION at face value) is implausible for MCNICHOLS — currently ranked
**96th of 96** (the smallest) in the entire IRU by market cap. No
balance-sheet figures accompany this table (no total assets/liabilities/
equity anywhere in the document) — even if the scale were resolved, this
alone would not create Financial Strength coverage. **No independent
means exists in this session to verify the true unit scale** (no
original-document page image was rendered for this specific table since
it is text-native, not scanned, and there is no second source to
cross-check against).

**Left unextracted. Not written to `extracted_facts`.** MCNICHOLS
remains UNDETERMINED — a real data point exists somewhere in this
company's history, but not one this platform can currently use, exactly
the outcome your instruction requires rather than "using an implausible
number simply because it increases coverage."

---

## 6. 8E — Final Coverage Audit

Computed directly against H-011's own live, unmodified signal code
(20-name holding list, unchanged from Stage 6).

| ticker | full FS periods |
|---|---|
| DEAPCAP | **2 (new this stage)** |
| LASACO | 1 (unchanged) |
| VERITASKAP | 2 (unchanged, from Stage 6) |
| all other 17 | 0 |

- **Financial-Strength code-eligible tickers (H-011 universe): 3 of 20 (15%).**
- **Tickers with ≥2 periods: 3 of 20 (15%)** — DEAPCAP, LASACO... wait,
  LASACO has only 1; **corrected: 2 of 20 (10%)** have ≥2 periods
  (DEAPCAP, VERITASKAP).
- **Tickers with ≥3 periods (research-ready): 0 of 20 (0%).**
- **Median historical depth (of the 3 eligible): 2.0. Minimum: 1**
  (LASACO).
- **H-011 current-universe overlap (nominal, ≥1 period): 3 of 20 (15%).**
- **Research-ready overlap: 0 of 20 (0%).**
- **Market-cap rank**: all 3 eligible names rank in the bottom quintile
  of the IRU (LASACO 79, VERITASKAP 78, DEAPCAP 95) — consistent with
  H-011's own construction, not a large-cap-selection artifact this
  time (unlike Stages 3-5's original large-cap-skewed set).
- **Liquidity**: all 3 are low-ADTV names, consistent with the rest of
  H-011's universe (Section 2 of Stage 6's report).
- **Sector**: FINANCIAL SERVICES (LASACO, DEAPCAP), FINANCIAL SERVICES
  (VERITASKAP) — 3 of 3 in the same sector, a real, small-sample
  concentration (not evaluated further given n=3).
- **Classification tally across all 18 zero-coverage tickers audited
  in Stages 7+8**: **HARVEST GAP: 1 (DEAPCAP, now resolved/extracted).
  STRUCTURALLY SPARSE: 9 (6 from Stage 7 + 3 new: RTBRISCOE, REGALINS,
  UNIVINSURE) — 50% of the audited population.
  UNDETERMINED: 8** (CAVERTON, CUTIX, MCNICHOLS, NSLTECH, OMATEK,
  REDSTAREX, SUNUASSUR, TANTALIZER).

**Raw overlap (15%) is NOT reported as progress toward H-018-readiness
— research-ready overlap is the number that matters, and it remains
0%,** per your explicit instruction.

---

## 7. Structural-Data-Gap Assessment

**Half of the 18-ticker audited population (9/18, 50%) now has
concrete, dated, self-disclosed, repeated evidence of a structural
reporting problem** — up from 6/18 (33%) after Stage 7. The strongest
individual piece of evidence in this entire program is RTBRISCOE's own
"(In Receivership)" letterhead — not an inference, a direct corporate
self-statement of insolvency status. UNIVINSURE's near-annual delay
pattern (6 consecutive cycles) is similarly hard to read as anything
but a genuine, ongoing filing-capacity problem.

**This is evidence, not proof, of permanence** — per your standing
instruction, a delay notice states a problem existed at specific
documented times, not that it has continued unbroken to today or will
persist going forward. But the CONCENTRATION of this evidence — 9 of 18
names, spanning insurance, distribution/receivership, and technology
sectors — is now a real, quantified pattern, not a single anecdote
(ROYALEX alone, as it stood after Stage 6).

---

## 8. External-Source Candidates

Per your instruction, a list only — nothing recommended for acquisition:

| ticker | missing period | document type needed | archive evidence | external source required? | expected value |
|---|---|---|---|---|---|
| 8 UNDETERMINED names (CAVERTON, CUTIX, MCNICHOLS, NSLTECH, OMATEK, REDSTAREX, SUNUASSUR, TANTALIZER) | Unknown, genuinely | Any audited/unaudited statement | None found after exhaustive search of both extracted and unextracted documents | **Possibly — but this remains an NGX-disclosure-system re-harvest question, not a new external source, since every document checked so far came from the same `doclib.ngxgroup.com` origin** | Unknown until a direct NGX-system check is done |
| 9 STRUCTURALLY SPARSE names | Whatever periods, if any, exist between delay notices | Any late-but-eventually-filed statement | Formal delay/default notices exist; no evidence of what (if anything) was eventually filed | Same as above — internal re-check, not external | Low — even if found, evidence suggests genuine reporting gaps in the underlying company history, not just harvest gaps |

**No new external data source is recommended.** Consistent with every
prior stage's finding.

---

## 9. H-018 Implications

No condition from the Stage 6/7 gate is newly satisfied. Research-ready
overlap remains exactly 0%. **DEAPCAP's real, hard-won extraction — a
genuine success in isolation — moved the needle from 2 to 3 nominally-
eligible names and changed nothing about research-readiness.** The
Stage 8 findings, on balance, make the STRUCTURAL explanation more
credible than it was after Stage 6 (50% of the audited population now
carries direct evidence, not inference), which if anything strengthens
rather than weakens the case against continuing to chase H-018 via
extraction alone.

---

## 10. Decision: C — MIXED (with a specific, quantified qualifier)

**Not A.** Only 1 of 18 audited zero-coverage tickers (DEAPCAP, 6%)
showed a genuine, actionable harvest gap, and even fully processing it
did not create research-ready coverage.

**Not B, in the strict sense** — 8 of 18 (44%) remain genuinely
undetermined, not confirmed structurally absent, so "the universe
cannot be covered" is not yet fully proven.

**C, with this precise quantification**: **9 of 18 (50%) are now
confirmed structurally sparse with direct, repeated, self-disclosed
evidence. 1 of 18 (6%) was a real, now-resolved harvest gap that still
fell short of research-ready. 8 of 18 (44%) remain genuinely unknown.**
Even in the best realistic case — every one of the 8 undetermined names
turning out to be a full harvest gap recoverable to 3+ periods — that
would raise research-ready H-011 overlap to at most 8/20 (40%), and
that is the OPTIMISTIC ceiling, not the expected outcome, since this
program's own repeated experience (Stages 3-6) is that most "no
document found" cases resolve to genuine absence, not hidden treasure.

**Practical recommendation, stated directly per your instruction to
recommend concretely under Path C**: the remaining structural
limitation is large enough (50% confirmed, against a realistic ceiling
of 40% even in the best case for the rest) that **continuing a full-
scale extraction campaign against the remaining 8 undetermined names is
not justified as the primary next step.** A small, final, bounded check
— NOT a new stage of extraction — is warranted: a direct comparison of
these 8 tickers against NGX's live disclosure system (not a new
external source, the same system this archive was built from) to
settle harvest-completeness definitively, sized as a single verification
task, not a campaign.

---

## 11. Recommended Stage 9

1. **One bounded verification task**: check the 8 UNDETERMINED tickers
   directly against NGX's disclosure system for any audited/unaudited
   statement this platform's harvest may have missed — sized and scoped
   identically to this stage's own filename-search method, not a new
   acquisition project. If this returns further real documents,
   process them with the same rigor as DEAPCAP. If it returns nothing,
   **all 18 zero-coverage tickers will have a final, defensible
   classification**, and the Financial-Strength-inside-H-011 track
   should be formally closed with that record preserved.
2. **Do not create H-018** regardless of Step 1's outcome unless
   research-ready overlap reaches a level that would support genuine
   cross-sectional testing (this program's own code floor is 10; H-011
   itself only has 20 names total, so even a "full" recovery scenario
   caps out well below what any other confirmed family on this platform
   has needed).
3. **If Step 1 confirms the ceiling estimated in Section 10** (at best
   ~40% research-ready overlap, likely less): **formally document that
   H-011's own investable universe — by the nature of the names it
   selects — may not support a second, independent, research-ready
   fundamental factor within this platform's current data environment.**
   This is a legitimate, disciplined platform-level finding, consistent
   with every instruction across Stages 6-8 not to manufacture a result
   the data doesn't support. Redirect research effort toward a
   different information source or factor family at that point, not
   toward more extraction inside the same exhausted universe.
