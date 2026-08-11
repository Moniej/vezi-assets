# FRE-7B.2: Peer Coverage Recovery Feasibility

**Date**: 2026-08-09
**Stage type**: Feasibility assessment only. No document was extracted (no fact was
written to the database), no valuation was rerun, no formula, taxonomy, WACC,
terminal-growth, scenario rule, or bracketing criterion was touched. A small number
of candidate-peer documents were read (not extracted) purely to classify their
content — the same read-only diagnostic activity §2/§3 of this stage's own
authorization requires ("identify whether the document could realistically supply
net_profit and equity... from available metadata/text").

**Bottom line: STOP FRE-7 — DATA CONSTRAINT.** Every candidate peer identified for
the two groups nearest the threshold (Financials, Industrials) was checked directly
against the existing `results_notice` corpus. With one exception (DEAPCAP, blocked
by corrupted OCR text, not absence of a document), **every remaining candidate's
un-mined `results_notice` documents are administrative notices (filing delays or a
correction notice) containing zero extractable financial facts** — not a matter of
more reading effort, but of the documents genuinely not containing the numbers.
Consumer has one real, disclosed lead (NESTLE), but it requires stepping outside
this stage's authorized `results_notice`-only scope. See §7 for the reasoning and
§8 for exactly what would need separate authorization to pursue further.

---

## 1. Per-pilot-case bottleneck table

Applying the exact frozen FRE-7/FRE-7A requirement (a peer must have a currency-clean
NGN, FY-period, PIT-knowable, **positive** EPS or BVPS — not merely "any accounting
fact"):

| Pilot case | Peer group (level1) | Usable peers (self excluded) | Required min | Additional peers needed |
|---|---|---|---|---|
| UCAP (pe) | Financials | 1 (AFRIPRUD) | 2 | **1** |
| CAP (pe) | Industrials | 1 (DANGCEM) | 2 | **1** |
| BUAFOODS (pe) | Consumer | 1 (NASCON) | 2 | **1** |
| NASCON (pe) | Consumer | 1 (BUAFOODS) | 2 | **1** |
| OANDO (pe) | Energy | 0 | 2 | **2** (no candidates exist in the fact-bearing universe at all) |
| UBN (pe) | — | 0 (subject itself unclassified) | 2 | n/a — not a peer-count problem |
| CAP (dcf) | — (no peer dependency) | n/a | n/a | n/a — not in scope for this stage |

Note: UCAP's own candidate pool is now 6, not 7 (NEM was removed after FRE-7B.1's
`genuine_fact_universe.py` correction — NEM has no real financial-statement fact at
all, confirmed again in this stage).

## 2. Peer-group coverage table (candidates and their exact blocking reason)

### Financials (UCAP's group) — candidates beyond AFRIPRUD/UCAP themselves

| Candidate | Usable now? | Un-mined `results_notice` | With text | Without text | Content found |
|---|---|---|---|---|---|
| DEAPCAP | No | 3 | 3 | 1 (structurally distinct — corrupted, not absent) | **All 3 text-available documents are corrupted OCR** (page-number-only text, no real content) — confirmed directly (doc 9311, 9312, 9368 all identical garbage pattern) |
| LASACO | No (PE); Yes (PB) | 3 | 2 | 1 | **Both text-available documents are the identical "delay in filing AFS" notice** (docs 10869/10876) — zero net_profit content. Already known from FRE-7B.1, re-confirmed. |
| PRESTIGE | No | 2 | 2 | 0 | **Both documents are filing-delay notices** (docs 9876, 10020) — one cites NAICOM's ongoing review of the 2024 AFS. Zero extractable facts. |
| UNIVINSURE | No | 0 | 0 | 0 | No `results_notice` document exists for this ticker at all. |
| VERITASKAP | No | 1 | 1 | 0 | **The one document is a filing-delay notice** (doc 8166), citing IFRS 17 transition and NAICOM-approved extension — zero facts. |

**Zero of the 5 remaining Financials candidates yielded a single extractable fact
from their `results_notice` corpus.** This is not a sampling gap — every
text-available document in every candidate was read. DEAPCAP's is the only case
blocked by something other than document content (its text is corrupted, not
administrative).

### Industrials (CAP's group) — candidates beyond CAP/DANGCEM themselves

| Candidate | Usable now? | Un-mined `results_notice` | With text | Without text | Content found |
|---|---|---|---|---|---|
| CAVERTON | No | 1 | 1 | 0 | **A discrepancy-correction notice** (doc 8946) — the company disclosing and correcting an error in its own prior unaudited H1 2024 statement. Zero extractable facts. |
| CILEASING | No | 1 | 1 | 0 | **A filing-delay notice** (doc 10941), citing CBN and offshore-subsidiary audit delays. Zero facts. |
| CUTIX | No | 0 | 0 | 0 | No `results_notice` document exists for this ticker at all. |
| REDSTAREX | No | 0 | 0 | 0 | No `results_notice` document exists for this ticker at all. |

**Zero of the 4 remaining Industrials candidates yielded a single extractable fact.**
Same pattern as Financials: every available document was administrative, or no
document exists.

### Consumer (BUAFOODS/NASCON's group) — the one remaining candidate

| Candidate | Usable now? | Un-mined `results_notice` | With text | Content found |
|---|---|---|---|---|
| NESTLE | No (genuine losses, FY2023/FY2024) | 6 | 6 | Six real quarterly press releases (Q1/Q2/Q3/Q4-pattern filings, 2024-04-30 through 2026-04-30) — **not administrative notices**, but none is a full-year AUDITED results release; the most recent (doc 11240, Q1 2026) is a genuine quarterly report |

NESTLE's blocking issue is **not** a missing document in the ordinary sense — its
two stored `net_profit` facts (FY2023: −₦79.5bn; FY2024: −₦164.6bn) are real,
correctly extracted losses, not data gaps. But doc 11240 (already identified,
already has text) states: *"Nestlé Nigeria... sixth consecutive quarter of
profitability since our return to profit in Q4 2024"* and *"Total equity increased
from ₦12.9 billion at the end of December 2025 to ₦51.6 billion at the end of March
2026."* This is strong, real evidence that a genuine **FY2025 net_profit figure
would likely be positive** — but **no FY2025 full-year results document exists in
NESTLE's `results_notice` corpus** (its 6 un-mined documents are all quarterly). See
§7 for where that document appears to actually be.

### Energy (OANDO) / UBN — unchanged, structural

No new candidate exists in either case; re-confirmed directly, not re-litigated
(FRE-7B/FRE-7B.1 already established this and nothing in the `results_notice`
corpus changes it — Energy has exactly one real fact-bearing constituent
platform-wide; UBN has no `sector_ngx` classification and no authoritative source to
derive one from).

## 3. Recoverability summary

| Category | Cases |
|---|---|
| **Recoverable from existing text** | None identified among the candidates actually checked |
| **Recoverable only after re-fetch** (document has no stored text) | LASACO (1 doc), DEAPCAP (1 doc) — both low-confidence: the *other* documents for these same tickers, which DO have text, were administrative/corrupted, so there is no positive signal these missing ones would differ |
| **Potentially recoverable but requiring manual/OCR work** | DEAPCAP's 3 corrupted documents (would need re-OCR from original source, not a re-read of existing text) |
| **Structurally irrecoverable from `results_notice`** | UNIVINSURE, CUTIX, REDSTAREX (no document of this type exists at all); OANDO's and UBN's peer gaps (not a document problem) |
| **Outside this stage's authorized scope, but a real lead** | NESTLE — likely resolvable via `other`-doc_type documents (§7), not `results_notice` |

## 4. PIT constraints

No PIT issue was found or is relevant here — every document checked either
contained zero extractable facts (administrative notices) or was not opened for
extraction at all (`other`-doc_type documents, out of scope, not read). No
candidate was excluded on PIT grounds in this stage; the constraint here is content
availability, not knowability timing.

## 5. Irrecoverable gaps

- **DEAPCAP**: 3 corrupted-OCR documents (page numbers only) — the underlying PDF
  likely needs re-processing from source, not a re-read of the already-extracted
  text. A genuine acquisition/reprocessing gap, not an extraction-effort gap.
- **UNIVINSURE, CUTIX, REDSTAREX**: no `results_notice` document exists for any of
  them. Whatever financial-statement content they may have published was filed
  under a different `doc_type` (confirmed: all three have real `other`-tagged
  documents with text — 3, 30, and 8 respectively — but examining that bucket is
  outside this stage's authorized `results_notice`-only scope, per §7).
- **Energy, UBN**: unchanged structural gaps (§2).

## 6. Estimated extraction effort (if pursued further)

| Path | Documents | Estimated effort | Expected yield |
|---|---|---|---|
| Re-fetch LASACO's 1 missing-text document | 1 | Low (single re-fetch + read) | Low confidence — LASACO's other 2 documents were both administrative; no reason to expect this one differs |
| Re-OCR DEAPCAP's 3 corrupted documents | 3 | Medium (requires a re-processing step this session has no tool for) | Unknown — genuinely unexamined content |
| Open NESTLE's 2 candidate `other`-doc_type documents (10621, 55,255 chars; 10975, 18,230 chars, both filed Feb–Mar 2026 — exactly the FY2025-annual-report filing season) | 2 | Low (already located, already have text) | **High confidence** — filing timing and document size strongly suggest a full annual report, but this is outside this stage's authorized scope, not attempted here |
| Any further Financials/Industrials `results_notice` documents | 0 remaining unexamined | n/a | n/a — every identified candidate document in these two groups has already been read |

## 7. Feasibility classification

| Peer group | Classification | Basis |
|---|---|---|
| **Financials** (UCAP/AFRIPRUD's group) | **LOW FEASIBILITY** | Every one of 5 remaining candidates' `results_notice` corpus is exhausted (administrative notices or corrupted text); the only unexplored path (DEAPCAP re-OCR) has unknown, unquantifiable payoff |
| **Industrials** (CAP/DANGCEM's group) | **LOW FEASIBILITY** | Same pattern — 4 remaining candidates, zero recoverable facts identified, 2 have no document of this type at all |
| **Consumer** (BUAFOODS/NASCON's group) | **MEDIUM FEASIBILITY** | One real, credible lead exists (NESTLE's likely-positive FY2025 result), but it sits in the `other` doc_type bucket, outside this stage's authorized `results_notice`-only scope — recoverable, but not from what this stage was authorized to search |
| **Energy** (OANDO) | **STRUCTURAL SCARCITY** | Zero real candidates exist in the platform's entire fact-bearing universe; unchanged since FRE-7B |
| **UBN** (unclassified) | **STRUCTURAL SCARCITY** | Not a peer-count problem — a missing classification input with no available authoritative source (FRE-7B.1) |

## 8. Opportunity cost

The question this stage was asked to answer: is recovering enough additional usable
peers, from the `results_notice` corpus specifically, worth the cost relative to
FRE-7's activation value?

- **For Financials and Industrials — no, not from this corpus.** Every identified,
  readable candidate document has already been read (this stage read all of them,
  not a sample) and none contained a usable fact. The only remaining paths (DEAPCAP
  re-OCR, a single LASACO re-fetch) have low or unquantifiable expected yield for a
  real cost (OCR reprocessing is a different capability than this platform's
  existing hand-extraction workflow). Continuing to search `results_notice` for
  these two groups specifically is not a good use of further effort.
- **For Consumer — a real, low-cost, high-confidence lead exists, but it is out of
  this stage's authorized scope** (`other` doc_type, not `results_notice`). The
  documents are already located, already have text, and their filing timing/size
  strongly suggest they are exactly the missing FY2025 annual report. This is worth
  a **separately authorized**, narrowly-scoped follow-up — not a blanket "search
  everything" expansion.
- **For Energy/UBN — not applicable.** No extraction effort of any kind changes
  either gap.

Given that 2 of 3 active pilot groups are LOW feasibility from the authorized
corpus, and the one MEDIUM-feasibility case requires a scope change this stage was
not authorized to make, further `results_notice`-only extraction is not justified
by the evidence gathered here.

## 9. Recommended next action

**STOP FRE-7 — DATA CONSTRAINT.**

The `results_notice` corpus, as scoped for this feasibility check, has been
demonstrated — not assumed — to be exhausted for the two peer groups nearest the
activation threshold (Financials, Industrials): every remaining candidate's
available document was read and contained no extractable financial fact. Continuing
to pursue the frozen FRE-7 pilot via further `results_notice` extraction is not
supported by what was found. The one real, promising lead (NESTLE, Consumer group)
sits outside this stage's authorized scope and would require its own, separately
authorized, narrowly-targeted follow-up (specifically: reading 2 already-located
`other`-doc_type documents) — not a resumption of broad `results_notice` mining.

Per the explicit governance instruction, this stage does not proceed automatically
to any further extraction, any valuation rerun, or any scope expansion. No trading
hypothesis was registered, no backtest was run, and no change was made to
`valuation_engine.py`'s formulas, `economic_peer_taxonomy.py`'s peer-selection
rules, the WACC/terminal-growth assumptions, the scenario rules, or the frozen
FRE-7/FRE-7A bracketing criterion.
