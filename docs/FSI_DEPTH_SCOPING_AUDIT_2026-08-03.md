# Financial Statement Depth Audit — Institutional Decision Paper

*2026-08-03. Read-only audit only — no extraction, no OCR, no parsing
beyond keyword/structural presence detection, no implementation, no
database write, no schema change, no new hypothesis. Directly executes
the highest-leverage next step the prior
`docs/FSI_COVERAGE_EXPANSION_DECISION_AUDIT_2026-08-03.md` recommended: a
depth-scoping pass over the already-archived native-text filings, before
any labor-allocation or OCR/vendor decision is made. Two new artifacts
were run, both verified read-only (`sqlite3.connect("file:...?mode=ro",
uri=True)` for the DB connection): `scripts/fre/fsi_depth_scoping.py`
(new, this audit) and a re-run of the existing
`scripts/fre/fsi_scope_candidates.py`. Neither writes to any table or
extracts any numeric fact.*

---

## 1. Current Field-Depth Coverage (re-verified, not assumed)

Measured via case-insensitive section-header/keyword detection across
**2,580 native-text documents** (`source_confidence>=0.8`, `char_count>3000`
— the same population `fsi_scope_candidates.py` uses as its own first-stage
filter, kept identical for comparability with the prior audit). This
measures **textual presence of a section indicator**, not confirmed
numeric extractability — stated explicitly and carried through the rest
of this document, since it is the single most important methodological
caveat here.

| Section | Documents | % of population | Distinct tickers |
|---|---:|---:|---:|
| Balance Sheet / Statement of Financial Position | 383 | 14.8% | 74 |
| Share-count information | 643 | 24.9% | 99 |
| Income Statement | 277 | 10.7% | 53 |
| Dividend information | 253 | 9.8% | 57 |
| Gross profit (explicit mention) | 203 | 7.9% | 36 |
| EBITDA (explicit mention) | 164 | 6.4% | 22 |
| Cash Flow Statement | 128 | 5.0% | 33 |
| Statement of Changes in Equity | 53 | 2.1% | 21 |
| Segment reporting | 39 | 1.5% | 17 |
| Notes to the financial statements | 24 | 0.9% | 17 |
| Five-year financial summary | 22 | 0.9% | 18 |

**By doc_type** (top volume categories): `doc_type='other'` (7,727 documents
platform-wide, the least-trusted category) alone carries 228 of the 383
balance-sheet hits and 139 of the 277 income-statement hits — the single
largest re-confirmation of Phase 1's own original finding that
`documents.doc_type` cannot reliably identify a financial-statement-bearing
filing; `results_notice` is a strong second (130 balance-sheet, 119
income-statement, 109 gross-profit hits) despite being a much smaller
category by volume.

**By reporting period — a real, previously unquantified pattern**: every
section type shows a sharp increase in absolute hit-count from
2019-2020 onward. Cash-flow-section hits: 1 (2015) → 5 (2018) → 13 (2020)
→ 21 (2022) → 14 (2025). Statement-of-changes-in-equity hits: 0 before
2019 → 2 (2019) → 6-12/year from 2020 onward. Segment-reporting and
five-year-summary hits are almost entirely 2019 or later.

**This pattern has two possible explanations, and this audit cannot
distinguish between them with the evidence gathered**: (a) NGX-listed
companies' actual disclosure completeness genuinely improved from
~2019-2020 onward (plausibly tied to IFRS-adoption maturity or NGX's own
evolving disclosure requirements), or (b) the document ARCHIVE itself is
more complete/higher-confidence for recent filings than older ones,
independent of what companies actually disclosed at the time. **Stated as
a real, measured pattern with an unresolved cause — not asserted as either
explanation without further investigation**, which this audit does not
attempt (it would require comparing archive completeness against an
independent filing-date census, out of scope here).

**Systematic gaps, confirmed**: Notes and segment reporting are rare
almost everywhere (0.9%/1.5% of the population) — these appear to be
disclosed in the FULL annual report PDF (likely still OCR-pending or not
separately archived as distinct text) rather than in the shorter
native-text-available filings this population draws from. This is
consistent with, not contradicting, the prior audit's OCR-gap finding.

---

## 2. Existing Archive Potential

### 2.1 The strict, keyword-verified candidate pool (re-confirmed exactly)

Re-running `fsi_scope_candidates.py` today reproduces the prior audit's
own figures exactly: **50 distinct tickers, 349 documents**, all 10
currently-extracted tickers included, **40 tickers remaining unextracted**.

### 2.2 New finding: core-statement section presence among the 40 remaining

Cross-referencing those 40 tickers against the section-header detection in
§1:

- **21 of 40 (52.5%)** have income statement + balance sheet + cash flow
  ALL detected in at least one archived document: `ABCTRANS, ACCESSCORP,
  AIICO, AIRTELAFRI, ARADEL, CHELLARAM, ELLAHLAKES, ETI, FIDELITYBK,
  FTNCOCOA, GEREGU, LASACO, MECURE, NB, NIDF, NOTORE, PZ, UACN, UNILEVER,
  VERITASKAP, VFDGROUP`.
- **19 of 40 (47.5%)** have partial coverage (some but not all three core
  sections detected): `BETAGLAS, CILEASING, CORNERST, DANGSUGAR, FCMB,
  GUINNESS, INFINITY, JBERGER, MRS, NGXGROUP, NPFMCRFBK, PRESCO, SEPLAT,
  TRANSCOHOT, TRANSCORP, TRANSPOWER, UBA, WAPCO, ZENITHBANK`.
- **0 of 40** show no section header at all — every one of the 40 has SOME
  structural financial-statement signal beyond the bare revenue/profit
  keywords that originally qualified it.

**This is a materially more optimistic starting point than the prior
audit could state** (which correctly labeled per-ticker depth-yield an
"Unknown" because no depth-scoping pass had yet been run). It is **not**
a claim that these 21 tickers are ready for extraction — Phase 2's own
finding (33% of filings lacking a cash-flow section despite plausibly
warranting one) means header presence is a necessary, not sufficient,
screening signal. The correct reading: **the 40 remaining tickers are not
a uniform pool of unknown depth-risk — just over half show real,
measured evidence of full-statement content, and the rest show at least
partial evidence.** No ticker in this pool is a confirmed dead end at the
header-presence level.

**A real, mixed pattern on bank coverage, not a clean rule**: three banks
(`FCMB`, `ZENITHBANK`, `UBA`) fall in the PARTIAL bucket, while one bank
(`FIDELITYBK`) falls in the FULL bucket. This does not support a clean
"banks systematically lack full statement disclosure" rule — the more
likely explanation, unverified here, is that each company's specific
BEST-available native-text filing happens to vary in completeness (some
of a bank's most detailed filings may be OCR-pending rather than
native-text), not a structural sector effect on disclosure content itself.

### 2.3 Which companies require OCR or another source

Not directly measurable from this audit (native-text-only by construction)
— but the same **184 tickers appearing ONLY among OCR-pending documents**
(re-confirmed count, unchanged since the prior audit) remain the population
that cannot be assessed at all without the OCR/vendor decision.

### 2.4 Maximum research capability obtainable from the existing archive alone

Unchanged from the prior audit's own hard ceiling: **44 of the current
100 IRU members** are inside the 50-ticker strict candidate pool. This
audit adds precision to WHAT KIND of data those 44 could plausibly yield:
based on §2.2, roughly half could plausibly reach full three-statement
depth (pending actual per-filing verification), and all 40 remaining show
at least some structural signal beyond bare keywords.

---

## 3. Factor Readiness Audit

Combining this audit's new section-presence evidence with the prior
audit's confirmed fact-count table (`docs/FACTOR_CANDIDATE_REGISTRY.md
§B`, re-verified unchanged today):

| Family | Required fields | Currently extracted (tickers) | Section-presence signal, 40-remaining pool | Testable using ONLY the existing archive? |
|---|---|---:|---|---|
| Value (earnings yield/B2M) | net_profit, equity | 10, 5 | 21 tickers show balance-sheet signal | **Plausible, unverified** — would need per-filing confirmation that equity is a clean, extractable line for those 21 |
| Value (cash-flow yield) | cfo, fcf | 2, 1 | Only 33 tickers total (of 2,580-doc population) show ANY cash-flow section | **Unlikely at fair breadth** — even optimistically, cash-flow depth is the narrowest signal measured |
| Quality (profitability composite) | net_profit, revenue, equity | 10, 10, 5 | Same 21-ticker signal as Value | **Plausible, unverified** |
| Growth (revenue/earnings, MULTI-PERIOD) | revenue, net_profit, ≥2 periods per ticker | 10, 10 | Not separately measured — this audit did not verify multi-period depth per ticker, a real gap carried forward | **Cannot state without further checking** — explicitly Unknown |
| Profitability (operating margin) | ebit/ebitda, revenue | 7/6, 10 | ebitda_mention detected in 22 tickers total (broader pop.) | **Plausible for a subset**, unverified at the fair-breadth bar |
| Gross Profitability | gross_profit (no fact_type exists) | 0 | **203 documents, 36 distinct tickers explicitly mention "gross profit"** — a genuinely new finding | **The most promising unexplored family in this audit** — see §6 |
| Investment/Asset Growth | assets, multi-period | 5 | Same balance-sheet signal as Value (74 tickers, broader pop.) | Plausible for breadth; multi-period depth unverified |
| Earnings Quality (accrual gap) | net_profit, cfo | 10, 2 | cfo bottleneck unchanged — cash-flow is the narrowest signal in this entire audit | **No material change** — still the hardest-blocked family |
| Cash Flow Quality | cfo, cff, cfi | 2, 2, 1 | Same narrow cash-flow signal | **No material change** |
| Financial Strength (Piotroski) | assets, liabilities, equity | 5, 5, 5 | 21-ticker full-statement signal plausibly helps | **Plausible, unverified**, same caveat as Value |
| Accruals | net_profit, cfo | 10, 2 | Same cfo bottleneck | **No material change** |
| Asset Turnover | revenue, assets | 10, 5 | Balance-sheet signal from 74 tickers (broader pop.) | Plausible for breadth |

**Minimum additional work required, for every "plausible, unverified" row**:
a per-filing check (not a bulk keyword scan) confirming the section header
is followed by an actual, complete, extractable numeric table — exactly
the kind of check Phase 1/2/13 already do by hand, just not yet applied to
these specific 21+19 tickers.

---

## 4. Coverage Bottleneck Analysis

Ranked by the evidence gathered across both audits:

1. **Financial-statement DEPTH for the currently-extracted tickers** — still
   the single most measurable, unambiguous bottleneck: cfo/cff at 2
   tickers, cfi/capex/fcf at 1, unchanged since Phase 2 (2026-08-01),
   despite 25 subsequent phases and one ticker-breadth expansion.
2. **Missing financial sections in a real, disclosed share of filings** —
   Phase 2's own 33% (5/15) cash-flow-absent finding, now given more
   texture by this audit: cash-flow section-header presence across the
   FULL native-text population is only 5.0% of documents / 33 tickers —
   confirming this is a genuinely scarce section type archive-wide, not
   just for the 5 originally hand-checked tickers.
3. **Manual verification effort** — unchanged; still the dominant real
   cost of any expansion, per the prior audit's own finding that no
   per-ticker time estimate exists anywhere.
4. **Company breadth** — **demoted, not eliminated, as a bottleneck**. This
   audit reduces uncertainty about breadth: 40 of 50 already-scoped
   candidates show SOME structural signal, and 21 show full-statement
   signal — breadth expansion within the existing pool is evidenced to be
   more promising than the prior audit could state, but remains capped at
   44/100 IRU coverage regardless.
5. **OCR availability** — unchanged, still the only path beyond the 44/100
   ceiling; a separate decision from anything measured in this audit.
6. **Validation effort** — unchanged; every fact extracted to date has been
   validated internally-only, never externally — this audit does not add
   new evidence here.
7. **A newly surfaced bottleneck this audit specifically identifies**:
   **ticker-ATTRIBUTION data quality**. 319 native-text documents
   platform-wide have `ticker IS NULL`; 107 of those are in the
   >3000-char population; **30 of those 107 pass the full revenue/profit/
   money keyword filter** (exactly reproducing the prior audit's own
   flagged figure) — and at least one, **CAVERTON** (a real, currently
   tracked security per `securities.ticker='CAVERTON'`), recurs across
   multiple documents with a clearly identifiable company name in the raw
   text (`"CAVERTON OFFSHORE SUPPORT GROUP PLC"`) that simply never got
   written to `documents.ticker`. This is a **concrete, cheap, zero-
   extraction-labor fix** that could recover at least one additional
   candidate ticker (and possibly recover ADDITIONAL documents for
   already-covered tickers — one unresolved document's first line reads
   `"BUA Foods PLC"`, suggesting even an ALREADY-extracted ticker has
   some of its own documents miscategorized).

**Overall verdict**: field depth (specifically cash-flow/balance-sheet
JOINT completeness) remains the primary bottleneck for MOST blocked
families, confirming the prior audit's central conclusion — but this
audit narrows the uncertainty considerably and surfaces the
ticker-attribution bug as a genuinely separate, smaller, and cheaper
opportunity that should be resolved first regardless of any larger
decision.

---

## 5. Expansion Scenarios

| | **A — Breadth only** | **B — Depth for existing tickers** | **C — Hybrid (depth-first, then breadth)** |
|---|---|---|---|
| Research unlocked | A Growth-style factor at up to 44/100 IRU breadth; nothing else, per §3's finding that breadth alone doesn't fill balance-sheet/cash-flow gaps | Potentially unlocks Financial Strength/Cash Flow Quality/Accruals at a narrow (~10-ticker) breadth — still below the platform's own reasoned 20-35 floor | Best of both if the 21-ticker full-statement-signal group (§2.2) converts to real extractable data — a materially better-evidenced bet than the prior audit could make |
| Engineering effort | None (schema/consumers already built) | None | None |
| Manual (verification) effort | Highest raw ticker-count, per-filing labor (40 tickers × unknown filings/ticker) | Lower ticker count but must chase the SAME hard-to-find cash-flow sections Phase 2 already found scarce | Front-loaded: a per-filing verification pass on the 21-ticker signal group first (smaller, targeted), before deciding how far to extend breadth |
| Validation effort | Same internal-only method as every prior phase; no new validation risk | Same | Same |
| Long-term scalability | Repeats Phase 13's own already-observed pattern (breadth without depth) — a known, not a hypothetical, risk | Bounded by the same 33%-filings-lack-cash-flow ceiling regardless of which tickers are chosen | Better-sequenced, but still ultimately bounded by the same real disclosure-gap ceiling |
| Risks | Highest risk of repeating a documented non-result (tickers added, no depth gained) | Smallest overall labor commitment, but smallest overall unlock too | Requires discipline not to slide back into breadth-first once depth work starts feeling slow (a real, human-factors risk, not a technical one) |
| Expected return on research effort | **Lower**, per this audit's own new evidence (§2.2, §4) | **Uncertain but more targeted** — 10 tickers is a real breadth-ceiling risk even if depth succeeds | **Highest, conditionally** — but only if the depth-first verification step is actually respected before any breadth work resumes |

---

## 6. Hidden Opportunities

### 6.1 The "Financial highlights" bullet block — real, common, NOT yet exploited as a template

Manually inspected `results_notice` filings for NASCON, DANGCEM, and others
show a recurring, compact **"Financial highlights"** bullet section
stating Revenue, Gross Profit, EBITDA (with margin), PBT, PAT, EPS, Total
Assets, and proposed dividend **in one place**, phrased consistently
("`<Metric> up/down X% to/at ₦Y`"). Phase 1/2/13 never built a template
parser against this specific block — they always hand-read full filings
line by line. **This is a real, previously unexploited, moderate-effort
target**: a single templated parser for this one recurring block could
plausibly recover revenue, gross profit, EBITDA, PBT, PAT, EPS, and total
assets simultaneously for every company using this format, without
touching the harder, less-regular detailed statement tables at all.

### 6.2 A genuinely tabular comparison-table format exists in a meaningful share of `results_notice` filings — the single most promising finding of this audit

Structural detection (a "label + two numeric fields + optional %" repeating
row pattern) across 244 native-text `results_notice` documents found:

- **112 documents (46%), spanning 19 distinct tickers**, contain 5 or more
  such rows — i.e., a genuine, repeating, LABEL-VALUE-VALUE-%CHANGE
  tabular block, not free narrative prose. UBA's own filing (manually
  inspected, doc_id 7793) shows this cleanly: a "Statement of
  Comprehensive Income" block and a separate "Statement of Financial
  Position" block, EACH with current-period, prior-period, and %-change
  columns, for line items including Gross earnings, Interest income,
  Operating income, PBT, PAT, EPS, Total assets, Net loans, Customer
  deposits, and Shareholders' funds — **plus the company's own pre-computed
  profitability/efficiency ratios (Cost-to-Income, Cost-of-Risk,
  Net Interest Margin, Return on Average Equity, Return on Average
  Asset)**, all in one compact, repeating structure.
- The highest-row-count tickers found (`LASACO`: 262 rows in one document;
  `GEREGU`: 112; `AIRTELAFRI`: 53-75 across multiple filings; `ETI`: 51-69)
  are candidates for the most immediately promising hybrid-extraction
  pilot — none of these is currently in the 10-ticker extracted set.
- **This directly resolves a specific gap the prior audit's own Software
  Architect adversarial review flagged**: a hybrid deterministic-extraction
  -with-human-verification approach was named as "never attempted or
  evaluated" for FSI. This audit finds real, structural evidence (not
  proof of success, but a genuine, measurable candidate) that such an
  approach has a concrete target to aim at, specifically for this tabular
  `results_notice` subset — a narrower, more tractable target than
  attempting to template the full, much less regular annual-report
  detailed statements.
- **A real caution, stated directly**: a bank's self-reported ratios
  (Cost-to-Income, RoAE, etc.) are the COMPANY'S OWN computed figures, not
  independently re-derived — using them directly would substitute the
  company's own methodology for the platform's, a genuine, disclosed
  construct-validity question for any future hypothesis relying on them,
  not resolved here.

### 6.3 Explicit "gross profit" disclosure — a real, previously unaddressed opportunity

**203 documents, 36 distinct tickers**, explicitly state a "gross profit"
figure — despite **no `gross_profit` fact_type existing anywhere in
`extracted_facts`** (confirmed absent in both this and the prior audit).
This is the single largest gap between "data that appears to exist in
the archive" and "data the platform has ever attempted to extract" found
in this audit. Gross Profitability (Novy-Marx 2013) is currently the
worst-off blocked family (§1 of the prior audit: "no fact_type exists at
all, worse than the others") — this finding suggests that assessment may
be too pessimistic **specifically for the subset of companies that
disclose it in a highlights/tabular block**, though whether the 36
tickers' gross-profit mentions are consistently well-formed numeric
statements (vs. narrative mentions without a clean number) was not
verified per-document in this pass.

### 6.4 The "five-year financial summary" — exists, but rarer than hoped

**22 documents, 18 distinct tickers** show a five-year-summary mention —
a real, positive signal for the Growth/multi-period problem named as an
open gap in §3, but a smaller population than the tabular-format finding
above, and NOT separately verified for whether the actual 5-year table
(not just the section title) is present and complete in each case.

### 6.5 Consistent reporting formats, more broadly

Share-count information is the single broadest section signal in this
entire audit (643 documents, 99 distinct tickers, 24.9% of the population)
— far broader than any financial-statement section. This was not the
subject of this audit's factor-readiness mapping (no currently-blocked
family in `docs/FACTOR_CANDIDATE_REGISTRY.md` names share-count as its
primary requirement) but is flagged as a genuinely under-exploited,
very-broad signal worth a dedicated look in a future pass, particularly
given the platform's own standing, separately-tracked gap around
free-float/shares-outstanding data (per
`docs/FREE_DATA_SOURCE_AUDIT_2026-08-02.md`'s NGX X-Compliance Report
discussion).

### 6.6 Existing metadata not yet utilized

`document_processing_status` (a separate, much smaller table — 23 rows
total, mostly dividend-event pilots per the earlier H-016-adjacent audit
trail) tracks `fact_count`/`implication_count` per document but has never
been used at the scale this depth audit operates at — not itself a
missed extraction opportunity, but a reminder that a production depth
pass would want its own tracking table, not a re-purposing of this
narrow pilot one.

**Nothing above was extracted. Every figure in this section is a
presence/count measurement only.**

---

## 7. Decision Matrix

| Option | Benefits | Risks | Dependencies | Research unlocked | Opportunity cost |
|---|---|---|---|---|---|
| **Continue with H-017 immediately** | Zero cost, fully ready, independent of every FSI question | Modest research ceiling even if confirmed; real construct-validity risk (may proxy Size) | None | Second validated factor (if it confirms) — the platform's single largest architectural gap | None — this audit finds no reason for H-017 to wait on anything here |
| **Depth-first extraction program** (the 21-ticker full-signal group + existing 10 tickers' remaining gaps) | Best-evidenced path to a genuinely new, broader-than-5-ticker factor family test, per §2.2/§6 | Still bounded by the real, measured 5%/33-ticker cash-flow scarcity archive-wide; per-filing verification still required, not shortcut by this audit's keyword screen | A per-filing verification pass on the 21-ticker signal group (cheap relative to full extraction, not yet done) | Potentially Value/Quality/Financial Strength at ~15-25 ticker breadth — still below the platform's own reasoned floor, but a real improvement over 5 | Delays a pure-breadth Growth-style test by however long the depth-first pass takes |
| **Another breadth expansion** (all 40 remaining, Phase 13's own prior pattern) | Reaches the 44/100 IRU ceiling for Growth-style testing | Repeats a documented non-result (Phase 13 added breadth, gained no depth) — this is now the SECOND audit to flag this specific risk | None beyond labor | A Growth-style factor at fair-ish breadth; nothing else | The clearest opportunity cost in this matrix: labor spent here is evidenced to NOT unlock Value/Quality/Financial Strength/Cash Flow Quality/Accruals |
| **Wait for OCR/vendor approval** | Only path beyond the 44/100 ceiling; unlocks 184 additional tickers | Vendor/cost decision unresolved since 2026-07-16, unchanged by either audit; unknown yield even if approved | Owner OCR-engine/vendor selection — outside this audit's scope | Unknown until resolved | Every week of delay is a week the 44/100 ceiling remains the practical maximum, regardless of any hand-extraction decision |
| **Hybrid strategy** (§5's "Option C" plus §6.2's tabular-template pilot) | Best evidenced expected return of any option in this matrix — combines depth-first sequencing with a genuinely new, previously-unevaluated extraction METHOD (templated tabular parsing) on the 19-ticker tabular-format subset | Requires discipline to actually run the depth-verification and template-pilot steps before committing to large-scale labor; a template parser could still fail the way the DOL EPS/P.E. parser did (2 prior documented failures on a related PDF-parsing problem) | A small, cheap pilot (attempt the tabular template on 3-5 of the 19 tabular-format tickers, hand-verify results) — not yet done | Broadest possible, IF the pilot succeeds; same as depth-first, IF it does not | Modest — the pilot itself is cheap and informative even on failure, per this program's own standing "a negative result is a valid result" discipline |

---

## 8. Final Recommendation

### Is field depth now the true bottleneck?

**Yes, confirmed and sharpened, not merely reaffirmed.** This audit adds
real precision the prior one could not: field depth (specifically JOINT
cash-flow/balance-sheet completeness) is scarce ARCHIVE-WIDE (5.0%/33
tickers for cash flow, out of 2,580 documents), not just among the 5
originally hand-checked tickers — this generalizes Phase 2's own
narrow finding to the full population for the first time.

### Should breadth expansion be postponed?

**Postponed in its Phase-13-style pure form (Scenario A), yes — but not
indefinitely, and not without qualification.** This audit found real,
positive evidence (21 of 40 remaining candidates show full three-statement
section signal) that breadth expansion is LESS purely wasteful than the
prior audit's "Unknown" framing suggested — but the core finding stands:
breadth alone, applied the way Phase 13 applied it, does not reliably
convert into the joint depth most blocked families need.

### Is a depth-first strategy justified?

**Yes, specifically Scenario C (hybrid, depth-first) — the strongest,
best-evidenced recommendation either audit has been able to make.** The
evidence for this is new and specific to this pass: a genuinely
promising, never-attempted extraction METHOD (§6.2's tabular-template
approach) has real, measurable structural support (112 documents, 19
tickers) and directly answers the Software Architect's own unresolved
challenge from the prior audit's adversarial review.

### Should H-017 proceed immediately?

**Yes, unconditionally, per both audits.** Nothing in this depth-scoping
pass changes that conclusion in either direction.

### What should the next owner decision be?

1. **Approve a small, cheap pilot** (not a commitment to full extraction):
   (a) hand-verify whether the §6.2 tabular-template pattern can be
   deterministically parsed for 3-5 of the 19 tabular-format tickers, and
   (b) fix the ticker-attribution bug for at least the confirmed CAVERTON
   case (a data-quality correction, not new extraction, recovering at
   least one candidate for zero labor cost).
2. **Defer** a full-scale breadth-only expansion decision until the pilot
   above reports back.
3. **Do not** treat this audit's more optimistic 21-ticker section-presence
   finding as equivalent to confirmed extractability — every one of those
   21 tickers still needs the same per-filing hand-verification Phase 1/2/13
   already do, just applied to a better-targeted subset than "all 40
   remaining, breadth-first."

---

## Institutional Adversarial Review

### Quant Research Director

**Criticism**: "The tabular-format finding in §6.2 is exciting, but you're
citing row-COUNT (262 for LASACO) as if more rows automatically means more
research value. A company with 262 tabular rows in one filing might just
have a very long, granular disclosure with mostly immaterial line items —
have you checked whether the KEY metrics (revenue, PAT, total assets) are
actually among those rows, not just SOME numeric-looking rows?"

**Response**: A fair, direct challenge to an implicit overclaim. The
row-count detector is a STRUCTURAL proxy (a line matching the label+2
numbers+% pattern) — it does not verify that any specific economically
important metric appears among those rows. UBA's manually-inspected
example (§6.2) DOES show Gross earnings, PBT, PAT, EPS, Total assets,
and Shareholders' funds among its rows — confirmed by direct reading, not
inferred from row-count alone — but LASACO's 262-row document and
GEREGU's 112-row document were NOT manually read in this pass, and their
row counts should not be read as a proxy for research value without that
same manual confirmation. This is now stated directly: **row count
identifies WHERE a tabular structure exists; it does not confirm WHAT is
in it. Any pilot (§8's own recommendation) must start with manual reading
of the specific candidate documents, not just their row-count ranking.**

### Financial Statement Specialist

**Criticism**: "Your SECTION_PATTERNS regex for 'cash_flow' just looks for
the phrase 'statement of cash flows.' Nigerian companies filing abridged
results sometimes present cash-flow information under a DIFFERENT heading,
or embed a condensed cash position note without ever using that exact
phrase. Your 5.0%/33-ticker cash-flow figure could be a real
under-count purely from the keyword's narrowness, not a true scarcity."

**Response**: This is a real, direct methodological limitation, and it
should not be minimized. The keyword-based approach used throughout this
audit (and the prior one) can only detect what it is told to look for;
it was not validated against a labeled sample of filings KNOWN to
contain a cash-flow statement under an alternative heading. **The 5.0%
figure should be read as a conservative, keyword-bound floor, not a
precise population estimate — the true proportion of filings with SOME
cash-flow information could be higher.** This limitation is now stated
explicitly rather than left implicit in the numbers; it does not overturn
the audit's core conclusion (cash-flow depth is scarcer than
income-statement/balance-sheet depth, which shows the same directional
gap even allowing for keyword imprecision), but the exact magnitude
should be treated with real uncertainty, not false precision.

### Data Engineering Lead

**Criticism**: "You found the CAVERTON ticker-attribution bug and called
it 'cheap to fix,' but you didn't check WHY it's null — is this a
systematic bug in one ingestion batch (fixable in bulk), or 319 separate,
unrelated failures (not actually cheap at all)? Also, doc 3679's garbled
text ('11,, PPrriinnccee KKaayyooddee...') suggests a text-extraction
quality problem INSIDE the 'native-text, source_confidence>=0.8' population
— doesn't that undermine trust in every section-presence count in this
whole document?"

**Response**: Both are real, unresolved gaps this audit should not paper
over. On the ticker-attribution bug: this audit did not investigate
WHETHER the 319 null-ticker documents share a common ingestion batch,
source, or date range that would make a bulk fix genuinely cheap, versus
being scattered failures needing individual triage — "cheap to fix" was
an overstatement not yet earned by evidence, and is corrected here to
"a real, concrete, INVESTIGATE-BEFORE-ASSUMING-CHEAP opportunity." On the
garbled-text finding: this is a genuine, freshly-surfaced concern — if
`source_confidence>=0.8` includes documents with visible character-level
corruption (letter-doubling, as seen in doc 3679), the population this
entire audit measures against may itself contain a meaningful share of
degraded text that would silently fail BOTH the keyword detectors used
here AND any future extraction attempt, without being flagged as
low-confidence. **This should be treated as an open, unquantified risk
to every percentage in §1 and §2 — this audit did not measure how common
this corruption pattern is across the 2,580-document population, and
that measurement should precede any further reliance on these specific
figures for resource planning.**

### Database Architect

**Criticism**: "Your Part 3 analysis initially conflated two different
candidate populations (the broad >3000-char set vs. the strict
keyword-filtered 50-ticker pool) before you caught and fixed it mid-audit.
That's a real error that made it into an intermediate script run. How do
I know there isn't a SECOND such conflation still sitting uncaught
somewhere in this document?"

**Response**: This is accurate — the initial script run of
`fsi_depth_scoping.py` did produce a "159 remaining tickers" figure from
an unintentionally broader population before being corrected to the
consistent 40-ticker figure, and that error is disclosed here rather than
quietly discarded, precisely because the reviewer's underlying concern
(silent population-mismatch errors are easy to make and hard to catch)
is legitimate and generalizable. A direct audit of this document's own
population labeling: §1/§6 explicitly and consistently use the "2,580
native-text, char_count>3000" population; §2.2/§3/§4/§7 explicitly use
the STRICT "50-ticker keyword-verified" population; §4's ticker-attribution
finding explicitly separates the 319 (all null-ticker native-text), 107
(char-count-filtered subset), and 30 (strict-keyword-filtered subset)
figures rather than using them interchangeably. No further conflation was
found on this re-check, but the reviewer's broader point stands as a
standing risk for any future extension of this analysis, not a
one-time-fixed issue to consider closed.

### Skeptical Portfolio Manager

**Criticism**: "You keep saying 'section header detected' is not the same
as 'extractable number confirmed' — fine, I believe you. But then your
Decision Matrix (§7) still describes the depth-first and hybrid options
using confident-sounding language ('best-evidenced path,' 'genuinely
promising') that reads, to a P&L-focused reader skimming this document,
as much more certain than a bare keyword-presence count actually
supports. Isn't the honest bottom line just 'we still don't know if any
of this converts into real, tradeable data' — and shouldn't that be
stated more starkly, right at the top, not buried in section 8?"

**Response**: This is the single most important critique in this review,
and it is accepted directly rather than argued against. The qualifying
language throughout this document ("plausible, unverified," "a necessary,
not sufficient, screening signal") is real and was written carefully, but
the reviewer is right that a skimming reader could still walk away with
more confidence than the evidence supports, especially from section
headers using words like "promising" and "the strongest recommendation."
**Stated as starkly as this critique demands: nothing in this audit
confirms that ANY additional financial-statement fact will actually be
extracted, at any ticker, from any document identified here. Every
number in this document is a count of TEXTUAL PRESENCE of a keyword or
structural pattern — not a verified, hand-checked, or cross-validated
financial fact. The entire value of this audit is narrowing WHERE to
look next and by roughly how much, not confirming that looking there will
succeed.** This caveat is added here, adjacent to the final
recommendation, specifically so it cannot be skimmed past the way the
reviewer correctly warns it could be.

---

*This document makes no recommendation to begin extraction. Its own
recommended next step (§8) is itself a small, cheap, still-non-extraction
pilot — reading a handful of specific documents by hand to confirm or
refute this audit's structural findings — before any labor-allocation
decision is made.*
