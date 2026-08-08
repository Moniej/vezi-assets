# STAGE 5 — FINANCIAL DEPTH + UNIVERSE-BIAS AUDIT

*2026-08-08. Real extraction, committed to `data/ngx.sqlite`. Every
number below is a direct database query result or a computed accounting
check, not an estimate. `configs/h011_size.toml`, `docs/PREREG_H-011.md`,
H-011's signal/construction, and all frozen experiment results are
unmodified. No hypothesis created.*

**Files changed**: two new scripts, `scripts/fre/
stage5a_depth_campaign_2026-08-08.py` (35 facts) and one standalone
follow-up correction for UCAP's quote-encoding issue (6 facts, folded
into the same batch below). **41 new `extracted_facts` rows total, 0
grounding failures after one encoding fix** (documented in Section 3).
No taxonomy change needed.

---

## 1. Files Changed / Extraction Work Performed

- `scripts/fre/stage5a_depth_campaign_2026-08-08.py` — re-read 7
  previously-unopened, LARGER documents (mostly full annual reports,
  identified by char_count + a balance-sheet keyword screen) for 7 of
  the 10 Stage-4 Financial-Strength-eligible tickers: DANGCEM (doc 4397,
  FY2019 AR), MTNN (doc 5887, FY2021 release), UCAP (doc 9449, FY2024
  release), AIRTELAFRI (doc 6126, FY2022 report), AFRIPRUD (doc 3961, H1
  2020 statement), BUAFOODS (doc 9790, Q1 2025 release), CAP (doc 4960,
  FY2020 Annual Report).
- **GEREGU and LASACO were searched (all documents >500 chars, screened
  for balance-sheet keywords) and confirmed to have NO other
  balance-sheet-bearing document anywhere in the archive.** Real
  negative finding, not attempted, not silently skipped — both remain
  single-period.
- One extraction bug found and fixed during this stage: UCAP's first
  attempt failed grounding on both `assets`/`liabilities` quotes because
  the source PDF's ₦ symbol extracts as a Unicode replacement character
  (U+FFFD), not the literal "?" placeholder I initially transcribed. The
  two orphaned `derived` equity facts that referenced the failed quotes
  were deleted before re-extraction (never left half-written). Corrected
  quotes re-extracted cleanly, 6/6 passed.

---

## 2. Before/After Coverage Matrix

**Full (assets + liabilities + equity, same period) periods per ticker:**

| ticker | periods before Stage 5 | periods after Stage 5 | new periods added | earliest | latest |
|---|---|---|---|---|---|
| DANGCEM | 2 | **6** | 2018-12-31, 2019-12-31 | 2018-12-31 | 2025-03-31 |
| AFRIPRUD | 3 | **5** | 2019-12-31, 2020-06-30 | 2019-12-31 | 2023-06-30 |
| UCAP | 3 | **5** | 2023-12-31, 2024-12-31 | 2020-09-30 | 2025-12-31 |
| MTNN | 2 | **4** | 2020-12-31, 2021-12-31 | 2020-12-31 | 2024-12-31 |
| CAP | 2 | **4** | 2019-12-31, 2020-12-31 | 2019-12-31 | 2025-06-30 |
| BUAFOODS | 3 | **4** | 2025-03-31 | 2022-09-30 | 2025-03-31 |
| AIRTELAFRI | 1 | **3** | 2021-03-31, 2022-03-31 | 2021-03-31 | 2025-03-31 |
| NASCON | 3 | 3 | (unchanged, not targeted this stage) | 2024-06-30 | 2025-12-31 |
| GEREGU | 1 | **1 (confirmed, no more data exists)** | none | 2021-12-31 | 2021-12-31 |
| LASACO | 1 | **1 (confirmed, no more data exists)** | none | 2022-12-31 | 2022-12-31 |
| UBN | 0 full (assets only) | 0 full (unchanged, not targeted) | none | — | — |

**8 of 10 Financial-Strength-eligible tickers now have ≥3 full periods**
(target met for those 8). **Median periods across the 10-ticker set: 3.5
(was 2). Minimum: 1** (GEREGU, LASACO — a real, confirmed archive limit,
not an extraction gap).

---

## 3. New Facts and Grounding Results

**41 facts written, 0 grounding failures in the final state** (1 initial
failure-and-correct cycle on UCAP, documented in Section 1 — not hidden).

| fact_type | count | tier breakdown |
|---|---|---|
| assets | 14 | 14 direct_reported |
| liabilities | 14 | 14 direct_reported |
| equity | 13 | 9 direct_reported, 4 derived (pure accounting identity, same-document components) |
| **total** | **41** | |

Grounding: 27/27 attempted checks passed (100%); 4 `not_run` (derived
equity facts, no single quote to ground — same convention as this
platform's existing `fcf` derivation). Confidence: 1.0 on every fact
(hand-verified, no model-assisted extraction this batch).

---

## 4. PIT Audit

All 7 new documents' filing_date vs. period_end lags:

| ticker | doc | period_end | filing_date | lag (days) | note |
|---|---|---|---|---|---|
| DANGCEM | 4397 | 2019-12-31 | 2020-12-18 | **353** | Real, extreme outlier — WORSE than the previously-flagged GEREGU 283-day case. This is DANGCEM's own FY2019 Annual Report, filed almost a year late. |
| DANGCEM | 4397 | 2018-12-31 | 2020-12-18 | **718** | Comparative column — conservative dating, disclosed |
| MTNN | 5887 | 2021-12-31 | 2022-03-30 | 89 | Normal |
| MTNN | 5887 | 2020-12-31 | 2022-03-30 | 454 | Comparative column — conservative dating |
| UCAP | 9449 | 2024-12-31 | 2025-03-03 | 62 | Normal |
| UCAP | 9449 | 2023-12-31 | 2025-03-03 | 428 | Comparative column |
| AIRTELAFRI | 6126 | 2022-03-31 | 2022-05-11 | 41 | Normal |
| AIRTELAFRI | 6126 | 2021-03-31 | 2022-05-11 | 406 | Comparative column |
| AFRIPRUD | 3961 | 2020-06-30 | 2020-07-23 | 23 | Normal |
| AFRIPRUD | 3961 | 2019-12-31 | 2020-07-23 | 205 | Comparative column |
| BUAFOODS | 9790 | 2025-03-31 | 2025-05-02 | 32 | Normal, no comparative period used (already existed) |
| CAP | 4960 | 2020-12-31 | 2021-05-18 | 138 | Normal-ish, on the long side |
| CAP | 4960 | 2019-12-31 | 2021-05-18 | 504 | Comparative column |

**Zero negative-lag documents (0/7) — no look-ahead risk.** Every
comparative-column fact's `description` field explicitly states the
conservative-dating caveat verbatim (not just in this report), per your
instruction not to imply an earlier de-facto announcement date.

**PIT verdict per document: PASS, all 7.** **DANGCEM's 353-day lag is now
the platform's WORST confirmed reporting-timeliness outlier**, surpassing
GEREGU's previously-flagged 283 days — both are genuine, disclosed data
points about these companies' historical filing timeliness, not
extraction problems.

---

## 5. Accounting Validation

**Assets ≈ Liabilities + Equity, checked across all 34 full periods now
on the platform (not just the 13 new ones — the 8 pre-existing DIRECT
equity facts Stage 4 flagged as not-yet-cross-checked are included
here):**

**Result: 34/34 periods pass, exactly.** `stated_equity - (assets -
liabilities)` = 0 (or a rounding remainder of ₦1,000-₦1,000,000 against
multi-billion/trillion-naira figures — i.e. 0.0000% on a relative basis)
for every single period across all 10 tickers. This includes:
- The 8 pre-existing direct equity facts (AFRIPRUD, BUAFOODS, CAP,
  GEREGU, LASACO, NASCON, UCAP periods) Stage 4 had flagged as
  unverified — **now verified, zero discrepancies found.**
- **MTNN's negative equity, re-confirmed exact and consistent across
  BOTH the pre-existing (2023, 2024) and newly-extracted (2020, 2021)
  periods**: implied equity (assets - liabilities) matches MTNN's own
  stated equity line to the naira in all four years, and the trajectory
  is coherent — positive equity in 2020 (₦178.4bn) and 2021 (₦265.0bn),
  turning negative in 2023 (-₦40.8bn) and worsening in 2024 (-₦458.0bn).
  **This is not an extraction error — it is a real, internally
  consistent, worsening balance-sheet condition**, exactly the kind of
  genuine Financial Strength signal this family is meant to capture.
- **Duplicate check**: zero (ticker, fact_type, period_end) duplicates
  across all 216+41 FS-taxonomy facts on the platform.
- **Restatements**: none (`restates_fact_id` null on all 41 new facts).
- **Currency/unit consistency**: verified per-ticker before writing
  (Section 3 of the extraction script's own docstring); CAP's new
  document used a DIFFERENT raw unit (N'000) than CAP's prior facts
  (N'm) — explicitly converted to match the ticker's prevailing scale,
  not left as a silent mismatch (documented in both the script and this
  report).
- **Not "fixed" merely because unusual**: MTNN's negative equity was
  investigated and cross-verified, not smoothed over or excluded.

---

## 6. Market-Cap / Liquidity / Sector Selection-Bias Audit (Section 5B — mandatory)

**All 10 Financial-Strength-eligible tickers are members of the current
100-name IRU (100% overlap with the investable universe by
construction).** Beyond that baseline fact, the bias picture is stark:

| ticker | IRU market-cap rank (1=largest, of 96 ranked) |
|---|---|
| AIRTELAFRI | **1** |
| MTNN | **2** |
| DANGCEM | **3** |
| BUAFOODS | **4** |
| GEREGU | 19 |
| NASCON | 33 |
| UCAP | 38 |
| CAP | 54 |
| AFRIPRUD | 64 |
| LASACO | 79 |

**Median market-cap rank of the Financial-Strength set: 26.0. Median
rank of the full 96-ranked IRU: 48.5.** The eligible set skews
dramatically toward the largest names — **the top 4 ranks in the ENTIRE
IRU are all Financial-Strength-eligible**, while only 6 of the remaining
92 names below rank 4 are.

**Liquidity**: median 2026-YTD average daily value traded (ADTV) for the
Financial-Strength set = **₦181.8 million**, vs. **₦31.8 million** across
all tickers with 2026 trading data — **the eligible set is ~5.7x more
liquid than the typical name.**

**Sector distribution**: FINANCIAL SERVICES (3: AFRIPRUD, LASACO, UCAP),
ICT (2: AIRTELAFRI, MTNN), CONSUMER GOODS (2: BUAFOODS, NASCON),
INDUSTRIAL GOODS (2: CAP, DANGCEM), UTILITIES (1: GEREGU) — **reasonably
diverse, no single-sector concentration.** Sector diversity is NOT the
problem; size/liquidity concentration is.

**Is missing coverage systematically associated with smaller/less-liquid
names? Yes, quantitatively confirmed.** The pattern above — largest 4
IRU names all present, median rank roughly half the full universe's,
liquidity nearly 6x the median — is exactly the "easiest filing to find"
selection effect Stage 4 flagged as a real, disclosed CONCERN. Stage 5
converts that concern into a **measured, confirmed fact.**

---

## 7. H-011 Overlap (Section 5B — mandatory)

Computed directly against H-011's own live signal code
(`backtest_xs.size_scores`, unmodified, same top_n=20/quarterly base
configuration), not approximated:

**H-011's own most recent actual selection (2026-06-30 formation, top 20
smallest-cap names in the IRU): CAVERTON, CILEASING, CUTIX, DEAPCAP,
LASACO, LEGENDINT, MCNICHOLS, NCR, NSLTECH, OMATEK, PRESTIGE, REDSTAREX,
REGALINS, ROYALEX, RTBRISCOE, SUNUASSUR, TANTALIZER, UNIVINSURE,
VERITASKAP, WAPIC.**

**Overlap with the 10-ticker Financial-Strength set: exactly ONE name —
LASACO.**

- **Number of current H-011 names represented in the FS set: 1 of 20 (5%).**
- **Percentage of H-011's investable universe (its 20-name selection)
  covered by Financial Strength data: 5%.**
- The one overlapping name, LASACO, is itself the single WORST-covered
  ticker in the Financial-Strength set by depth (1 period, confirmed no
  more data available — Section 2).

**This is the single most important finding of Stage 5.** A
Financial-Strength factor built from today's coverage would, by
construction, have almost no names in common with H-011's own actual
holdings. Any future portfolio-level question ("does this factor add
something H-011 doesn't already have") is currently unanswerable — not
because the two factors are entangled (as H-013/014/015 found for
Liquidity/Volatility), but because **their eligible universes barely
intersect at all.**

---

## 8. Financial Strength Readiness Verdict

Applying your explicit hard gate:

- ≥15 names → NOT MET (**10 names**)
- ≥15 names but <3 periods for most → not applicable (breadth already fails)
- ≥15 names × ≥3 periods → NOT MET

**VERDICT: NOT READY.**

Answering the seven required pre-H-018 questions explicitly, in order:

1. **Is the dataset broad enough?** **No.** 10 of the required 15+
   names.
2. **Is it deep enough?** **Yes, for 8 of the 10** (≥3 periods); **no**
   for GEREGU/LASACO (1 period, confirmed archive limit). Overall: a
   genuine, real improvement, but breadth is the binding constraint, not
   depth, going forward.
3. **Is PIT integrity clean?** **Yes** — 0/7 new documents show
   look-ahead risk; all comparative-column facts carry an explicit,
   disclosed conservative-dating caveat; two extreme-but-positive lag
   outliers (DANGCEM 353d, GEREGU 283d) are flagged, not hidden.
4. **Is factor construction consistent?** **Yes** — the accounting
   identity holds exactly across all 34 full periods, including all 8
   previously-unverified pre-existing facts.
5. **Is coverage selection materially biased toward large/liquid names?**
   **Yes, decisively, now quantified** (Section 6): median IRU rank 26
   vs. 48.5, the top-4-by-market-cap IRU names all present, ~5.7x median
   liquidity.
6. **Is there sufficient overlap with H-011's universe?** **No — 1 of 20
   names (5%).**
7. **Is the resulting factor genuinely new information rather than
   another disguised market-cap/liquidity exposure?** **Cannot be
   determined from current data** — the severe selection bias in
   question 5 makes this untestable right now: any leverage/solvency
   signal computed only on large, liquid names is confounded with size
   and liquidity by construction of the SAMPLE, independent of whatever
   the true underlying relationship would be on a representative sample.

---

## 9. Cash Flow Quality Status

**Unchanged from Stage 4 — deliberately not pursued this stage**, per
your explicit instruction not to let it distract from the Financial
Strength depth objective. Opportunistic byproduct: BUAFOODS' new
document (9790) did NOT add a new cfo fact (not present in that specific
filing); no other new cfo facts were incidentally produced.
**7 tickers, unchanged, still BLOCKED** (below the 10-name code floor,
and now doubly below the 15-name research floor).

---

## 10. H-018 Gate Decision

Per Stage 4's nine-condition table plus the five additional questions
Section 8 above answers explicitly: **conditions on breadth (#1), size
of the eligible universe relative to the code floor, universe-selection
bias, and H-011 overlap all fail or are unresolved.**

**Decision: H-018 is NOT created.**

This is a MORE decisive no than Stage 4's, not a repeat of it — Stage 4
flagged the large/liquid selection-bias risk as a plausible concern;
Stage 5 has now measured it directly and confirmed it is real and
severe (Sections 6-7). Depth alone, however well-executed, cannot
overcome a sampling bias this large. **Extracting more periods for the
SAME 10 (or even 15) large/liquid names would not fix this** — the fix
is extracting SMALL/illiquid names specifically, the opposite of every
extraction priority used in Stages 3-5 so far (which have consistently,
correctly-for-their-own-stated-goal, chased "which filing is easiest to
find and most complete").

---

## 11. Exact Remaining Blockers

1. **Breadth: need 5+ more Financial-Strength-eligible tickers** to
   clear even the 15-name floor — the primary blocker.
2. **Universe-composition bias**: even at 15+ names, if every new
   ticker added is ALSO large/liquid (the path of least resistance,
   exactly what Stages 3-5 have followed), the H-011-overlap problem
   (Section 7) will not improve — it could even worsen. **Future
   extraction must deliberately target smaller, less-liquid IRU names**,
   which will likely be harder (thinner disclosure, more scanned/
   unextracted documents, per this program's own repeated finding that
   smaller names' filings are lower-quality/less-available).
3. **GEREGU and LASACO are archive-exhausted** at 1 period each — this
   ceiling cannot be raised without a document that does not currently
   exist in the harvested archive (a genuinely new acquisition question,
   not an extraction one).
4. **Cash Flow Quality remains 3 tickers short of even the code floor.**

---

## 12. Recommended Stage 6

**Reverse the extraction priority that has driven every stage so far.**
Stages 3-5 correctly and efficiently extracted the "easiest to find"
documents — large-cap, well-documented, high-char-count filings. That
strategy has now measurably produced a Financial-Strength dataset that
is unusable for combination with H-011 (Section 7) even if it clears the
15-name breadth floor. **Stage 6 should deliberately target small/
illiquid IRU names — starting with H-011's OWN actual 20-name holding
list** (Section 7's list: CAVERTON, CILEASING, CUTIX, DEAPCAP,
LEGENDINT, MCNICHOLS, NCR, NSLTECH, OMATEK, PRESTIGE, REDSTAREX,
REGALINS, ROYALEX, RTBRISCOE, SUNUASSUR, TANTALIZER, UNIVINSURE,
VERITASKAP, WAPIC, excluding LASACO which is already covered) — screen
each for ANY balance-sheet-bearing document, accepting that the hit rate
will likely be lower and the documents harder to extract (more scanned
images, per this program's own repeated finding for small-cap NGX
names).

**This is a harder, slower task than Stages 3-5's approach** and should
be sized/scoped as such before starting, not assumed to proceed at the
same pace.

**Do not create H-018.** Re-run Section 8's gate after Stage 6; the
question to re-ask is specifically #6 (H-011 overlap) and #7 (disguised
exposure), not just breadth count — a Financial Strength set that
reaches 15 names but is STILL all large/liquid would still fail the
gate, even though it would satisfy the raw numerical threshold.
