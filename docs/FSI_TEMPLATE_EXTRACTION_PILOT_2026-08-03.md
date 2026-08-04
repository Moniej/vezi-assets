# Financial Statement Template Extraction — Manual Feasibility Pilot

*2026-08-03. Read-only investigation only. No extraction was performed,
no fact was written anywhere, no code was built, no database was
touched beyond read-only queries already used in
`docs/FSI_DEPTH_SCOPING_AUDIT_2026-08-03.md`. This document is a manual,
hand-read comparison of actual archived filing text across 5 companies
and 12 individual filings, undertaken specifically to test whether the
prior audit's "tabular comparison-table" finding is a genuine, reusable
pattern or an artifact of a small sample (its own adversarial review,
Quant Research Director's criticism, explicitly warned against exactly
this risk).*

## Companies and filings inspected

| Company | Sector | Format hypothesis (from prior audit) | Filings read |
|---|---|---|---|
| **UBA** | Bank | Tabular | 2021-11-17 (doc 5483), 2023-10-30 (doc 7793) |
| **ETI** (Ecobank) | Bank, pan-African | Tabular | 2021-07-26 (doc 5155), 2023-03-30 (doc 7074), 2026-04-28 (doc 11215) |
| **AIRTELAFRI** | Telecom | Tabular | 2020-07-24 (doc 3964), 2022-05-11 (doc 6126), 2025-05-08 (doc 9809) |
| **DANGCEM** | Industrial/cement | Narrative | 2025-07-25 H1 (doc 10098), 2026-02-28 FY (doc 10758) |
| **NASCON** | FMCG | Narrative | 2024-07-29 H1 (doc 8801), 2026-03-02 FY (doc 10929) |

5 companies, 3 sectors, 2 currency conventions (₦ and $), both format
hypotheses represented, at least one company (UBA) already touched in
the prior audit, four not previously read in depth. 12 individual
filings read in full or substantially.

---

## The single most important finding, stated up front

**The "narrative vs. tabular" split from the prior audit is a false
dichotomy.** Reading beyond the first ~2,000 characters of DANGCEM's and
NASCON's filings — which the prior audit's automated row-counter had
classified as pure "narrative Financial highlights" style — reveals that
**both also contain a clean, well-formed, deterministically-parseable
tabular block further into the same document**: DANGCEM's "Summary
Operating Review" table (Revenue/EBITDA/margins by region, PBT, tax,
net profit, EPS, all with current-vs-prior-period values) and NASCON's
"Summary of key performance indicators" table (a full mini income
statement: Revenue, Cost of sales, **Gross profit**, GP Margin, Other
income, Distribution costs, Administrative expenses, Operating profit,
EBITDA, EBITDA Margin, Interest received/paid). **Every one of the 5
companies inspected has SOME tabular block somewhere in its results
announcement — the prior audit's automated classifier simply missed
DANGCEM's and NASCON's because they occur later in the document than the
classifier's row-density check was tuned to expect on a first pass, or
because line-wrapping in those specific tables produced fewer
consecutive regex-matching lines than the 5-row threshold.** This is a
real limitation of the prior audit's automated method, now corrected by
manual reading, and it is a MORE optimistic finding than the prior audit
stated: **structured, extractable content is likely present in a much
larger share of `results_notice` filings than the 46% tabular-format
figure suggested — the real gating question is not "does a table exist"
but "how consistently is that table's surrounding text extracted."**

---

## Template Stability Analysis

### Rows always present (across ALL 12 filings read)

Every single filing, regardless of format hypothesis or sector, states:
**Revenue (or "Gross earnings"/"Net revenue" for banks/telcos), Profit
Before Tax, Profit After Tax, Earnings Per Share** — in some form, in
every one of the 12 filings. This is the one truly universal core.

### Rows usually, but not always, present

Total Assets (present in UBA, ETI, NASCON's detail table, DANGCEM's
narrative; not confirmed in the excerpt read for AIRTELAFRI, which
reports operating/cash-flow metrics more prominently than balance-sheet
items in its own highlights section). EBITDA (present in DANGCEM, NASCON,
AIRTELAFRI; present in ETI as "Pre-provision, pre-tax operating profit,"
a bank-specific relabeling, not a literal EBITDA line — confirming the
prior audit's own finding that banks structurally lack an EBIT/EBITDA
concept and substitute a different, bank-specific profitability line).
Dividend (present in DANGCEM, NASCON; not observed in UBA/ETI's
excerpts, though this may reflect where in the filing dividend
information sits, not its absence).

### Rows that are genuinely optional / company-specific

Bank-only rows with no non-bank equivalent: NPL ratio, NPL coverage
ratio, Cost-of-risk, Net interest margin, Customer deposits, Net loans,
CET1/Tier 1/Basel III capital ratios (UBA, ETI only). Telecom-only rows:
customer base, ARPU, data usage, mobile money metrics, capex guidance
(AIRTELAFRI only). Segment/regional breakdowns (Nigeria vs. Pan-Africa
for DANGCEM; UEMOA/Nigeria/AWA/CESA for ETI) — present in multi-country
operators, absent in single-market NASCON.

### Labels that change wording (confirmed, not assumed)

- "Profit after tax" (UBA, DANGCEM, NASCON) vs. "Profit available to ETI
  shareholders" (ETI) vs. "Profit after tax" used generically in
  AIRTELAFRI's GAAP column but "Underlying EBITDA" as a NON-GAAP
  alternative measure alongside the GAAP "Operating profit" — i.e., some
  companies (AIRTELAFRI) report BOTH a GAAP and a non-GAAP/"underlying"
  version of similar metrics side by side, a real complication a naive
  single-value-per-metric parser would need to disambiguate.
- "Total assets" (UBA) vs. no equivalent single line found in AIRTELAFRI's
  or ETI's inspected excerpts (ETI's own "Total assets" line was present
  in the earlier depth audit's UBA sample but not confirmed in this
  pilot's ETI excerpts specifically — a gap in this pilot's own coverage,
  not a confirmed absence).
- "Gross profit" (NASCON, and per the prior audit's 36-ticker keyword
  finding) has no equivalent concept anywhere in UBA's or ETI's bank
  income statement (structurally absent, not a wording difference).

### Which values move position

Within UBA's own single document, the SAME period's Total Assets value
appears in the compact highlights table (as "16,235,995") near the top
AND is implicitly reconcilable against the detailed Condensed Statement
further down (though Total Assets itself was not repeated verbatim in
the detailed excerpt read) — position is consistent WITHIN a company's
own template across the two periods inspected, but the compact-table
row ORDER differs between companies (UBA: Income-statement rows, then
Balance-sheet rows, then Profitability-metrics rows, in that fixed
order; ETI: Income Statement, then Balance Sheet, then Profitability
Metrics — the SAME conceptual order, but ETI additionally interleaves a
"Geographic Segments" block between Profitability Metrics and the
narrative text, which UBA does not have).

### Formatting differences that would break naive deterministic parsing — the central risk finding of this pilot

This is where the pilot's evidence diverges sharply from the prior
audit's optimism, and it is company-specific, not format-hypothesis
-specific:

1. **UBA (doc 7793, 2023)**: clean, properly column-aligned text. A
   naive `label + number + number + percent` regex would parse this
   correctly with minimal effort.
2. **AIRTELAFRI (docs 3964, 6126)**: clean, but with a real structural
   twist — TWO side-by-side sub-tables ("Alternative performance
   measures" and "GAAP Measures") sharing the same row of column
   headers, meaning a naive single-table parser would need to be aware
   there are two independent label/value column PAIRS per line, not one.
3. **DANGCEM/NASCON (docs 10098, 8801, etc.)**: clean tabular block once
   located, but it occurs AFTER a substantial narrative preamble of
   variable length (board-change announcements, macro commentary,
   conference-call logistics) — meaning the parser cannot assume a fixed
   character offset or line number; it must SEARCH for the table's own
   start marker (e.g., "Summary Operating Review" / "Summary of key
   performance indicators") first.
4. **ETI (docs 7074, 11215) — the most serious finding of this pilot**:
   the SAME conceptual table ("Group-wide Financial Summary") is
   rendered in the archived text as **severely corrupted, single-letter
   -spaced text** — e.g. `"G r o u p -w id e F in a n c ia l S u m m a r y"`
   and numeric values similarly corrupted (`"1 ,8 6 2 1 ,7 5 7"` instead
   of `"1,862 1,757"`). This is not a one-off: it recurs across BOTH
   ETI filings from 2023 and 2026 sampled in this pilot, a full three
   years apart — confirming it is a systematic property of Ecobank's own
   PDF-generation/export process (plausibly a font-kerning or
   character-spacing artifact from the specific PDF tool Ecobank's IR
   department uses), not a random one-time corruption. **A separate,
   earlier ETI filing (2021, doc 5155) shows a DIFFERENT failure mode
   entirely — not character-spacing corruption, but column-interleaving,
   where the PDF's original two-column page layout (financial table on
   the left, narrative commentary on the right) was serialized into
   text as alternating fragments on the same line** (e.g., `"Net revenue
   (operating income) 825 771 resilience in our performance, which is
   indicative of..."` — the trailing text is narrative bleeding in from
   the opposite page column, not part of the financial table at all).
   **ETI, on its own, exhibits TWO DIFFERENT extraction-corruption
   patterns across three sampled filings — meaning even a single
   company's own disclosure format has not been stable enough, at the
   TEXT-EXTRACTION level, to assume one company-specific template would
   reliably work across its own filing history.**

### Would a normalization dictionary solve these differences?

**For label-wording variance (synonyms like "Profit available to ETI
shareholders" vs. "Profit after tax")**: yes, plausibly — this is exactly
the kind of problem Phase 13's own config-driven synonym table was
already built to solve, and nothing in this pilot contradicts that.

**For ETI's character-spacing corruption**: **not with a synonym
dictionary — this requires a DIFFERENT kind of normalization (a
text-reflow/de-kerning pass that detects and collapses single-character
-separated runs before any label matching can even begin)**. This has
never been built or attempted anywhere in this platform's FSI work. It
is a real, additional, non-trivial pre-processing step, not covered by
"just add more synonyms."

**For ETI's column-interleaving corruption (2021 filing)**: **no
dictionary or reflow pass solves this — this requires re-deriving the
original page layout from PDF coordinate data (if available) or
discarding text-only extraction for this specific filing entirely.**
This is a structurally harder problem than either of the other two,
and this pilot did not attempt to assess whether the underlying PDF
retains extractable coordinate/layout metadata that could resolve it
(out of scope for a text-file-based pilot).

---

## Cross-Company Consistency

| Metric | UBA | ETI | AIRTELAFRI | DANGCEM | NASCON |
|---|---|---|---|---|---|
| Revenue label | "Interest income"/"Gross earnings" (bank-specific) | "Net revenue (operating income)" | "Revenue" | "Group revenue" | "Revenue" |
| PBT/PAT present | Yes, both | Yes, both (PAT as "Profit available to shareholders") | Yes, both | Yes, both | Yes, both |
| EPS present | Yes | Yes | Yes | Yes | Yes |
| EBITDA/equivalent | N/A (bank) | "Pre-provision, pre-tax operating profit" (bank equivalent) | Yes, "Underlying EBITDA" | Yes | Yes |
| Gross profit | N/A (bank) | N/A (bank) | Not observed in excerpt | Not observed at highlights level (product-level, not disclosed at group level in samples read) | **Yes, explicit, with COGS and margin %** |
| Total assets | Yes | Not confirmed in this pilot's excerpts | Not observed in highlights (telecom operating-metric focus) | Not observed in the two excerpts read (may appear in the detailed table beyond what was read) | Yes (narrative only, not in the detail table excerpt captured) |
| Currency | ₦ (Naira) | $ (US Dollar) | $ (US Dollar) | ₦ (Naira) | ₦ (Naira) |
| Text extraction quality | Clean | **Inconsistent — clean-ish narrative, but corrupted tables in 2 of 3 filings, via 2 DIFFERENT corruption modes** | Clean | Clean | Clean |

**Conclusion on cross-company consistency**: labels are conceptually
recognizable across companies (every company states SOME form of
revenue/PBT/PAT/EPS), and this supports the idea of a shared CONCEPTUAL
schema — but the pilot found **real, structural, sector-driven
differences** (banks substitute NIM/CIR/NPL-based profitability metrics
for EBITDA; telecoms report customer/ARPU metrics with no
non-telecom equivalent) that mean a SINGLE universal row-template
covering every company's exact row set is not realistic. **A shared
template is realistic only at the "core 4" level (Revenue, PBT, PAT,
EPS) — everything past that requires either sector-specific template
variants (bank template, telecom template, industrial/FMCG template) or
company-specific handling.**

**A real, additional structural observation, not previously
documented**: DANGCEM and NASCON — both Dangote Group companies — show
near-identical narrative phrasing conventions ("Financial highlights"
bullet list, "X, [Title], said:" quote block, "About [Company]"
boilerplate section) across TWO DIFFERENT tickers. This suggests **shared
templates may cluster by CORPORATE GROUP / shared IR department or
service provider, not purely by sector** — a genuinely useful, previously
unstated organizing principle for any future template-design effort: a
"per parent-group template family" approach (Dangote Group, UBA Group,
Ecobank Group, etc.) may be more tractable than either one universal
template or fully bespoke per-ticker templates.

---

## Extraction Feasibility Assessment

**Overall: Moderate feasibility, NOT "Highly feasible" — a real downgrade
from the prior audit's more optimistic framing, with specific,
evidenced reasons.**

- **UBA, DANGCEM, NASCON**: individually, **highly feasible** — clean
  text, a locatable tabular block (once a start-marker search is used,
  not a fixed offset), consistent structure across the periods sampled.
- **AIRTELAFRI**: **highly feasible for its own dual-table structure**,
  once a parser explicitly handles the two-side-by-side-tables pattern —
  not a simple single-column parser, but a well-defined, learnable
  variant.
- **ETI**: **low feasibility as currently archived**, specifically
  because of the text-extraction corruption found in 2 of 3 sampled
  filings, via 2 different corruption modes within the SAME company's
  own filing history. This is not a labeling problem a synonym
  dictionary fixes — it requires new, unbuilt pre-processing.

**This pilot cannot generalize a single feasibility rating to "the
tabular-format 19-ticker population" as a whole**, because ETI (one of
the highest-row-count tickers identified in the prior audit, per its own
51-69-row documents) turned out to be among the LEAST reliably
extractable on manual inspection — directly contradicting the assumption
that a high automated row-count is a good proxy for extraction ease.
**Row count measures table-LIKE structure; it does not measure text
-extraction fidelity, and this pilot found the two can diverge sharply.**

---

## Risks (confirmed by direct observation, not hypothesized)

- **Formatting drift within a single company's own history** — confirmed
  directly: ETI showed two DIFFERENT corruption modes across its own
  2021/2023/2026 filings. A parser built and validated against ETI's
  2023 filing would likely fail silently or loudly on its 2021 filing,
  and possibly on future filings too, since no pattern of WHEN each
  corruption mode occurs was identified in this small sample.
- **Character-level text corruption** (ETI) — a new risk category this
  pilot surfaced, distinct from anything documented in Phase 1/2/13's
  own error taxonomy (which covered document/company/metric/numeric/
  period/unit errors, but never a text-extraction-quality category).
- **Column-interleaving from multi-column PDF layouts** (ETI 2021) — a
  second, distinct new risk category.
- **Dual GAAP/non-GAAP reporting** (AIRTELAFRI's "Underlying EBITDA" vs.
  GAAP "Operating profit") — a real risk of silently extracting the
  WRONG version of a metric if a parser isn't explicitly aware which
  column is GAAP-consistent, directly relevant to this platform's own
  "no fabricated/no inferred financial facts" rule (which already
  required Phase 13 to exclude non-statutory "adjusted" MTNN/NESTLE
  figures) — this same discipline would need to extend to AIRTELAFRI's
  GAAP-vs-underlying split.
- **Sector-specific row sets** (banks vs. telecoms vs. industrials) —
  confirmed, not hypothesized; would require sector-aware template
  variants, not one universal schema.
- **Table position variability within a document** (DANGCEM/NASCON's
  tabular block appears after a variable-length narrative preamble) —
  confirmed; rules out any fixed-offset parsing approach.
- **Merged/split cells**: not directly observed in this pilot's samples
  (none of the 12 filings showed an obviously merged-cell artifact), but
  this pilot's sample is small and this risk category from the user's
  own list should not be treated as ruled out.

---

## Engineering Estimate

**Measured** (from this pilot, not estimated): 12 filings across 5
companies were read manually in roughly one focused investigative pass;
concrete, reproducible corruption patterns were found in 2 of those 12
(both from the same company, ETI).

**Estimated, explicitly labeled**:
- A parser handling the "clean" cases (UBA/DANGCEM/NASCON/AIRTELAFRI
  style) is a moderate, not large, engineering effort — reusing the same
  additive-schema/grounding-check pattern already built for Phase 1/2/13,
  plus a start-marker search instead of a fixed offset, plus a
  dual-sub-table handler for AIRTELAFRI's specific layout.
- A parser handling ETI's corruption modes is a SEPARATE, harder,
  not-yet-scoped effort, plausibly comparable in difficulty to the DOL
  EPS/P.E. parser's own two failed attempts (both of which also fought
  PDF-to-text layout/positional problems) — this is a real, evidenced
  analogy, not a guess, given the structural similarity of the problem
  class (recovering meaning from PDF-derived text where visual layout
  information was lost).
- **Manual verification burden**: per this program's own unbroken
  discipline, EVERY deterministically-parsed value would still need the
  same internal same-document cross-check Phase 1/2/13 already apply —
  this pilot does not find a basis for skipping that step, only for
  possibly reducing (not eliminating) the manual READING burden for the
  "clean" cases.
- **Maintenance burden**: genuinely elevated versus a single fixed
  parser, because this pilot's own evidence shows format is not stable
  even within one company's filing history (ETI) — any deterministic
  parser would need per-filing validation/fallback-to-hand-verification
  logic, not a "build once, run forever" assumption.
- **Scalability across the archive**: **plausible for a "clean-template"
  subset (UBA-like, DANGCEM/NASCON-like, AIRTELAFRI-like), NOT
  demonstrated for the archive as a whole** — this pilot's single
  clearest finding is that the population is heterogeneous at the
  text-extraction level in a way the prior audit's row-count screening
  could not detect, and a production system would need its own
  per-company or per-filing QUALITY GATE (does this specific document's
  text look clean or corrupted?) before attempting deterministic
  parsing on it at all.

---

## Decision

1. **A deterministic template extractor is justified — but only as a
   TARGETED, quality-gated pilot on the subset of companies/filings
   confirmed clean (UBA, DANGCEM, NASCON, AIRTELAFRI-style), not as a
   general-purpose parser assumed to work archive-wide.**
2. **Company-specific (or more precisely, template-FAMILY-specific,
   per the Dangote-Group-clustering observation) handling would be
   required** — a single universal template is not supported by this
   pilot's evidence; sector-driven row-set differences (bank/telecom/
   industrial) and text-quality differences (ETI's corruption) both
   independently rule it out.
3. **A hybrid deterministic + human-verification workflow is the
   correct near-term choice, not a stepping stone to be discarded** —
   every extracted value still needs the same internal cross-check
   Phase 1/2/13 already perform; this pilot's contribution is
   potentially reducing how much of a filing a human must READ before
   verifying, not removing the human verification step itself.
4. **The idea should NOT be abandoned** — the "clean" subset (at
   minimum UBA, DANGCEM, NASCON, AIRTELAFRI, and plausibly other
   companies sharing their template families) shows real, consistent,
   deterministically-recognizable structure across multiple periods
   each. But it should proceed narrower and more cautiously than the
   prior audit's framing suggested, with an explicit text-quality
   screening step as its own first, separate deliverable — not folded
   silently into "build the parser."

---

## Institutional Review

### Financial Statement Specialist

**Criticism**: "You've confirmed 'Revenue, PBT, PAT, EPS' as universal
across your 5 companies, but that's exactly the same narrow scope Phase
1/13 already extract today. What does this pilot actually ADD if the
only guaranteed-universal fields are ones already covered? Where's the
NEW data — balance sheet, cash flow — in your cross-company table?"

**Response**: A fair challenge to the practical payoff. The pilot's
cross-company table (§"Cross-Company Consistency") does show Total
Assets confirmed for 2 of 5 companies and Gross Profit confirmed for 1
of 5 (NASCON) — genuinely NEW fields relative to what's in
`extracted_facts` for these specific tickers today (none of UBA, ETI,
AIRTELAFRI, DANGCEM's non-NASCON entities are in the current 10-ticker
extracted set at all) — so the incremental value is real breadth
(new tickers) plus, for NASCON specifically, a genuinely new field
(gross_profit, which has NO fact_type on this platform at all). The
criticism is right that this pilot did not confirm NEW depth (cash
flow, full balance sheet) for the SPECIFIC companies inspected here
beyond what the prior audit's keyword screen already suggested was
present — that remains unverified and should not be overstated as a
win of this pilot.

### Data Engineering Lead

**Criticism**: "Your 'engineering estimate' section still has no
concrete number anywhere — you've replaced 'Unknown' with a slightly
more educated 'Unknown, but plausible.' At what point does this program
stop producing more audits and just spend one day actually TIMING how
long it takes to hand-verify one of these tabular filings end-to-end?"

**Response**: This is a completely fair, sharp criticism and should not
be deflected. Every audit in this sequence (Coverage Expansion, Depth
Scoping, this Pilot) has correctly avoided inventing a number where none
exists — but the CORRECT next step, which none of the three documents
has actually done, is a timed trial: hand-verify ONE tabular filing (a
strong candidate: UBA's doc 7793, already the cleanest example found)
completely, with a clock running, and report the real number. This
pilot did not do that, and should have — it is flagged here as the
single most concrete, cheap, immediately actionable next step, more
specific than this document's own "Decision" section states.

### Quant Research Director

**Criticism**: "Your ETI finding is interesting, but ETI isn't even in
the current IRU-relevant candidate set in the same way as, say,
AIRTELAFRI or UBA — how much does one bank's corrupted PDFs actually
matter for the platform's real research priorities? Are you letting an
interesting anomaly distract from the companies that actually matter?"

**Response**: A reasonable proportionality check. ETI (Ecobank
Transnational Incorporated) IS a real NGX-listed, IRU-eligible ticker
(confirmed present in the 100-member IRU per the depth-scoping audit's
own candidate-pool cross-reference), so it is not an irrelevant edge
case — but the reviewer is right that this pilot spent disproportionate
space on ETI's corruption relative to its one company's weight in the
overall research question. Restated with proper weight: **4 of the 5
companies piloted (UBA, AIRTELAFRI, DANGCEM, NASCON) showed clean,
usable text**; ETI is the one clear negative case in this small sample,
useful as a concrete illustration of a REAL risk category (text
corruption) that a production quality-gate would need to check for
broadly, not evidence that this risk affects most of the archive. The
correct generalization is "build a quality gate," not "expect most
filings to look like ETI's."

### Database Architect

**Criticism**: "You keep citing 'doc 7793' and similar IDs throughout
this report as if they're stable, permanent references — but this
entire pilot was read directly off `text_path` files on disk, not
through any versioned or content-hashed reference. If that file changes
or the archive is re-scraped, does anything in this report remain
verifiable?"

**Response**: A legitimate reproducibility concern. This pilot's own
citations (doc_id plus the `documents` table's existing fields) are
exactly as stable as every other citation in this platform's FSI
documentation (Phase 1/2/13 cite doc_ids the same way) — this is
consistent with existing practice, not a new weakness introduced here,
but the reviewer's underlying point generalizes: nothing in this
platform's current schema content-hashes the actual `text_path` file
contents, so a silent re-scrape WOULD break traceability for every FSI
document ever cited, not just this pilot's. This is named here as a
real, standing gap worth flagging to the Data Engineering Lead as its
own small, separate finding — not something this pilot can or should
fix, but worth surfacing rather than silently assuming permanence.

---

*This pilot recommends, as its single most concrete next step, a timed
hand-verification of one clean tabular filing (UBA doc 7793) to produce
the first-ever real per-filing effort number for this program — cheaper
and more informative than any further audit-level document, and still
not an extraction commitment.*
