# FSI Depth Pilot — Execution and Owner Decision

*2026-08-04. This document reports on REAL execution — the pilot
specified in `docs/FSI_OWNER_DECISION_PACKAGE_2026-08-03.md` was
actually run, not audited from a distance. Database was backed up to
`data/ngx.sqlite.pre_fsi_depth_pilot_backup_2026-08-04` before any
write. 19 facts were written to `extracted_facts`, all with real
grounding checks run against the actual source documents (17/17 direct
quotes passed; 2 derived facts, correctly marked, not grounded against
a quote). Script: `scripts/fre/fsi_depth_pilot_2026-08-04.py`. The
question this pilot answers is narrow and specific, per instruction:
**can the platform reliably produce validated three-statement
financial data at a quality and cost that justifies scaling FSI** —
not how many tickers can be covered.*

---

## Owner Decision (read this first)

**1. Is FSI expansion justified?**

**Yes, conditionally — the pilot's own evidence supports a scoped
depth-first expansion, not a breadth-first one.** Two of three
candidates reached usable three-statement depth on the first attempt,
with zero grounding failures and clean internal arithmetic
cross-checks. The one candidate that did NOT get written was blocked
by a genuine, previously-undiscovered schema gap (currency handling),
not a text-quality or extraction-difficulty problem — a different, and
more encouraging, failure profile than earlier pilots found (no
character-corruption was encountered in any of the three candidates).

**2. What measurable evidence supports that conclusion?**

- **Extraction accuracy**: 17/17 (100%) of directly-quoted facts passed
  exact-substring grounding on the first attempt — no retries, no
  corrections needed after the fact.
- **Achievable field depth**: GEREGU reached 12/12 (100%) of the
  platform's own `financial_statements` fact taxonomy — the deepest
  single-filing extraction in this platform's history, exceeding every
  ticker in the existing 10-ticker set. LASACO reached 7/12 (58%),
  limited by a real sector-structural reason (see below), not text
  quality.
- **Internal cross-check validation**: both written candidates' cash-
  flow statements were independently verified by summing
  CFO+CFI+CFF and confirming it matches the filing's own stated change
  in cash — both passed exactly.
- **Reproducibility**: the same grep-then-read-then-ground workflow was
  applied identically to both successful candidates with no iteration
  required — a real, if small-n (n=2), positive signal.
- **A genuine, disclosed negative finding**: AIRTELAFRI, despite being
  the cleanest and most complete filing of the three (all four
  statements present, zero text corruption), could not be safely
  written because the platform's `extracted_facts` schema has no
  currency field and every other extracted company reports in NGN —
  writing AIRTELAFRI's USD figures into the same column would have
  silently corrupted every downstream consumer. This is disclosed, not
  worked around.

**3. What should the first production milestone be?**

**Not a ticker-count target.** Per this pilot's own evidence, the
right first milestone is: **resolve the currency-handling gap (a
small, additive schema/methodology decision, not large-scale work),
then re-attempt AIRTELAFRI as the fourth pilot candidate** — since it
is already fully read, fully verified as clean, and blocked by exactly
one well-understood, narrow issue. This is a smaller, cheaper next step
than expanding to new tickers, and it directly tests whether the
pilot's methodology generalizes to dual-listed, foreign-currency NGX
names, a real and recurring category (Seplat, seen elsewhere in this
platform's own documentation, is another).

**4. What should explicitly not be attempted yet?**

- **Breadth expansion to the remaining candidate pool.** This pilot
  deliberately tested 3 filings, not more, and the evidence it produced
  is about DEPTH achievability and cost, not how many more tickers can
  be added — extrapolating a ticker-count plan from n=3 would violate
  this pilot's own "do not generalize beyond what the evidence
  supports" instruction.
- **A general-purpose deterministic parser.** Nothing in this pilot
  attempted or validates one — every fact here was hand-read and
  hand-transcribed, consistent with every prior FSI phase's own
  methodology.
- **A bulk fix of the 399 null-ticker documents.** The investigation
  below found this is very likely cheap and mostly mechanical — but
  executing it was out of scope for this pilot and is not done here.
- **Extraction of `pbt`/`eps`.** Both were visible and cleanly
  recoverable in every one of the three filings read (see Section 4)
  but are not yet valid `fact_type` values in
  `configs/fact_taxonomy.toml` — adding them is a real, low-cost future
  action, not attempted in this pilot since it wasn't part of the
  explicit instruction for this execution.

---

## 1. What was actually done

Per the Owner Decision Package's own specification, adapted to this
task's explicit "minimize effort while maximizing evidence" and
"do not optimize for throughput" instructions:

1. **Ticker-attribution investigation** (read-only diagnosis, Section 2).
2. **Hybrid deterministic + human-verification extraction** on 3
   previously-identified high-quality candidates (Section 3-4) — the
   highest tabular-row-count `results_notice` filings from
   `docs/FSI_DEPTH_SCOPING_AUDIT_2026-08-03.md`'s own Section 6.2
   finding, none previously in the extracted 10-ticker set (chosen
   specifically to test genuinely NEW depth, not re-verify known
   tickers).
3. **19 facts written**, each individually grounded against the real
   source text, database backed up first.

The `pbt`/`eps` schema addition named in the FSI Owner Decision
Package's own §3.4 was **not** executed — this task's instructions did
not list it among the four numbered execution requirements, and it is
named here only as a disclosed, evidence-supported future option
(Section 4).

---

## 2. Ticker-attribution investigation (read-only)

Per the Coverage Expansion Decision Audit's own Data Engineering Lead
critique ("investigate before assuming cheap"), the 399 documents with
`ticker IS NULL` (source `ngx_xissuer_documents`, 3.5% of that
source's 11,533 total documents — not a systematic source-wide
failure) were investigated directly:

- **All 399 (100%) have a non-empty, recoverable `raw_symbol` value**
  — this is not a lost-cause population; every document carries the
  information needed to attribute it correctly.
- **132 (33%) are trivially fixable** by case-insensitive exact
  matching against `securities.ticker` alone (e.g., `raw_symbol='Caverton'`
  → `CAVERTON`, confirming and resolving the specific case named in the
  prior audit).
- **A further ~130 (up to 63% cumulative)** are fixable with a small,
  well-understood set of normalization rules — e.g., `raw_symbol='NB Plc'`
  (104 documents alone) needs only a "strip trailing PLC" rule to match
  ticker `NB`.
- **The remaining ~140 (≈37%)** require individual investigation —
  some (`UHREIT`, `UPDC REIT`) are REIT-type instruments the IRU
  deliberately excludes by pattern; others (`Vetiva`) appear to be an
  investment-firm name, not a security ticker at all; `RONCHESS` (43
  documents) may reference a security not currently in `securities`.

**Conclusion: this is a genuine, mostly mechanical, bulk-fixable data-
quality issue, not a scattered one** — a materially more encouraging
finding than the prior audit's own cautious "don't assume cheap"
framing, now backed by a real breakdown rather than a single anecdote.
**Not fixed in this pilot** (out of scope for the depth-quality
question this pilot exists to answer) but the investigation itself
directly resolves the open question the prior audit left unanswered.

---

## 3. Candidate selection

| Ticker | Doc ID | Filing | Char count | Tabular rows (heuristic) | In existing 10-ticker set? |
|---|---:|---|---:|---:|---|
| AIRTELAFRI | 9809 | FY2025 results (year ended 31 Mar 2025) | 171,336 | 243 | No |
| LASACO | 7194 | FY2022 annual report | 291,947 | 598 | No |
| GEREGU | 6555 | FY2021 annual report | 143,248 | 292 | No |

All three were selected specifically because they are large,
comprehensive filings (closer to full annual reports than short
results notices) — a deliberate choice to test the platform's own
prior finding that `results_notice`-classified documents sometimes
contain full statement depth despite the doc_type label suggesting
otherwise.

---

## 4. Per-candidate results

### AIRTELAFRI — read, verified clean, NOT written (currency blocker)

All four statements located and read directly (Consolidated Statement
of Comprehensive Income, Statement of Financial Position, Statement of
Changes in Equity, Statement of Cash Flows) — genuinely the cleanest
text of any filing examined across this entire FSI audit series, zero
character-spacing or column-interleaving corruption. Revenue,
operating profit (EBIT), profit before tax, profit for the year, total
assets, total liabilities, total equity, CFO, CFI, CFF, and capex were
all directly visible and would have been extractable with the same
confidence as GEREGU's below. **[Estimate, not executed]**: had
currency handling existed, this candidate would very likely have
reached 12/12 (100%) field depth, matching GEREGU.

**Why it was not written**: `extracted_facts.numeric_value` has no
currency field, and every other extracted company on this platform
(UBA, ETI, DANGCEM, NASCON, UCAP, BUAFOODS, AFRIPRUD, CAP, MTNN, UBN,
OANDO, NESTLE, and now LASACO/GEREGU) reports in NGN. Airtel Africa plc
is UK-incorporated and dual-listed (LSE/NGX), reporting in US$
millions. Writing its raw USD figures into `numeric_value` alongside
every NGN figure would silently corrupt any downstream ratio or
cross-ticker comparison — a real, previously invisible schema gap this
pilot surfaced specifically by attempting real extraction rather than
reading excerpts or counting rows.

### LASACO — written, 7/12 fields (58%)

Balance sheet, cash flow statement, and net profit all clean, direct,
and grounded on the first attempt. **`revenue`, `ebit`, `ebitda` not
extracted** — not a text-quality failure: LASACO Assurance Plc is an
**insurance underwriting company**, and its income statement has no
single "Revenue" line (the closest analogues, "Gross premium written"
₦13.9bn and "Net premium income" ₦9.5bn, are genuinely different,
non-interchangeable constructs) and no EBIT/EBITDA concept at all —
**the same structural pattern previously found for banks (no EBIT/
EBITDA line), now confirmed to extend to insurance companies as a
second, distinct sector-structural gap.** `capex` and `fcf` were not
located within the sections read (would require a deeper notes-section
search, not attempted here per the "minimize effort" instruction).

### GEREGU — written, 12/12 fields (100%)

Every field in the platform's `financial_statements` taxonomy
recovered: revenue, net_profit, assets, liabilities, equity, cfo, cfi,
cff, capex, and ebit were all directly stated and grounded; `fcf`
(cfo − capex) and `ebitda` (operating profit + depreciation +
amortization) were both **derived**, not independently stated as a
single line — correctly marked `confidence_tier='derived'`, extending
the same convention `configs/fact_taxonomy.toml` already applies to
`fcf` to `ebitda` as well for this filing, disclosed here rather than
silently treated as directly reported. Both cash-flow and balance-sheet
identities cross-checked exactly (CFO+CFI+CFF = stated Δcash; both
years' closing cash balances matched to the naira). **This is the
deepest, cleanest single-filing extraction anywhere in this platform's
history** — a materially stronger result than any of the original
10-ticker set achieved, including on metrics (EBIT) those tickers
often lack entirely.

---

## 5. Aggregate pilot metrics

| Metric | Result |
|---|---|
| Candidates attempted | 3 |
| Candidates successfully written | 2 (67%) |
| Facts written | 19 |
| Grounding pass rate (direct-quote facts) | 17/17 (100%) |
| Derived facts (correctly marked) | 2 |
| Combined field-recovery rate (written candidates only) | 19/24 = 79% |
| Combined field-recovery rate (incl. AIRTELAFRI's estimated depth) | ~31/36 ≈ 86% **[estimate]** |
| Internal arithmetic cross-checks attempted | 2 (both candidates' cash-flow statements) |
| Internal arithmetic cross-checks passed | 2/2 (100%) |
| New failure modes discovered | 2 (currency-denomination gap; EBITDA-requires-derivation pattern) |
| New sector-structural gap confirmed | 1 (insurance companies lack Revenue/EBIT/EBITDA — extends the bank finding) |
| Text-corruption incidents | 0 of 3 (a different, more favorable profile than the ETI/UBA corruption found in earlier pilots) |

---

## 6. Failure modes, explicitly separated from throughput

*Per instruction: "do not optimize for throughput" — these are
reported because they bound what the platform can reliably promise,
not because they reduce a ticker count.*

1. **Currency denomination** (AIRTELAFRI): a genuine, structural,
   schema-level gap — not fixable by better reading or more effort on
   this filing specifically. Affects any dual-listed, foreign-currency-
   reporting NGX name (a real, if currently small, category).
2. **Sector-structural field absence** (LASACO, insurance): revenue and
   EBIT/EBITDA concepts do not exist for underwriting businesses — not
   an extraction failure, a genuine absence of the concept in the
   source. Confirms this is a real, recurring pattern (banks, now
   insurers) rather than a one-off.
3. **EBITDA sometimes requires two-statement derivation** (GEREGU):
   not every filing states EBITDA as a single line; deriving it
   correctly requires combining the income statement's operating
   profit with the cash-flow statement's depreciation/amortization
   lines — a real, generalizable extraction-complexity pattern, not
   previously documented.

**No character-level text corruption was found in any of the three
candidates** — a genuinely different, more favorable result than the
Template Pilot's own finding (ETI's two distinct corruption modes) or
the Time-and-Motion Study's finding (UBA's own balance sheet corrupted).
**[Judgment]**: this may reflect that all three candidates here are
comprehensive, full-annual-report-scale filings rather than short
results notices — comprehensive filings may be sourced from
higher-fidelity original documents, though this pilot's n=3 cannot
establish that as a general rule.

---

## 7. What this pilot does and does not establish

**Establishes**: on a small, deliberately non-random sample of 3
previously-flagged high-quality candidates, the hybrid hand-verification
methodology reliably produces validated, fully-grounded three-statement
data, at a real per-filing cost (a small number of targeted reads, not
a full sequential read of a 150-300K-character document) meaningfully
lower than the earlier single-document time-and-motion study's own
measured cost.

**Does not establish**: what fraction of the remaining ~40 candidate
tickers would behave like GEREGU (100% depth) versus LASACO (58%,
sector-limited) versus a text-corrupted case like ETI — n=3 is not a
representative sample of that population, and this document does not
claim it is.
