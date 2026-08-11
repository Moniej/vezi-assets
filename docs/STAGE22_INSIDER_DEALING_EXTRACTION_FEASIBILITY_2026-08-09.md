# Stage 22 — Insider Dealing-Notice Extraction Feasibility Scoping

**Date:** 2026-08-09
**Status:** Feasibility scoping only. No extraction pipeline built, no fields parsed at scale, no
hypothesis registered, no factor/backtest. This assesses whether the mechanism Stage 20 rated **A**
(insider/substantial-shareholder "dealing" notices — the second-priority candidate after the now-closed
illiquidity/staleness track) is worth building.

---

## Corpus size and composition

163 `documents` rows with `doc_type='dealing'`, all sourced from `ngx_xissuer_documents` (first-party,
confidence 0.85), 2020-02-27 to 2026-07-10. Two important corrections to Stage 20's initial framing:

- **Not all 163 are open-market transactions.** Filename inspection: 141 contain "DEALING," 12 contain
  "VESTING." Text inspection of the readable subset confirms the distinction is real and stated by NGX
  itself — a sampled Access Holdings filing (doc_id 10402, 651 employees, restricted-share vesting) reads
  verbatim: *"Please note that the vesting of shares is not a purchase or sale transaction."* Vesting
  notices must be **excluded** from any directional insider-trading signal; they are compensation events,
  not discretionary trades. This shrinks the usable corpus to roughly 141–150 filings before any other
  filter is applied.
- **Heavy concentration.** 29 distinct tickers, but UCAP alone accounts for 35 filings (21% of the total
  corpus); the top 3 tickers (UCAP, INITSPLC, NESTLE) account for 62 filings (38%). Many tickers have
  exactly 1 filing. Any future analysis would be dominated by a handful of names unless explicitly
  addressed.
- **15 filings have `ticker IS NULL`** — an unresolved ticker-identity gap (e.g. a sampled Airtel Africa
  filing, doc_id 10233, has no ticker assigned despite being a real, dated, first-party notice). These
  are unusable until resolved and are a real, disclosed gap, not silently dropped from the count.

## Extractability — the core feasibility question

**Strong, on the open-market subset.** The standard "Notification of Share Dealing by Insiders" form
(sampled directly: doc_id 3317, UNIONDAC, 2020-02-27) is a structured NGX/SEC-mandated disclosure with
labeled fields extractable by deterministic regex/keyword parsing — no LLM judgment required, satisfying
the platform's standing no-LLM-signal rule:

```
Nature of the transaction: SALE
Price(s) and volume(s): 14 JANUARY 2020 — 340,000,000 UNITS @ N0.21 / 17 JANUARY 2020 — 8,000,000 UNITS @N0.21
Aggregate volume: 348,000,000 UNITS
Date of Transaction: 14 AND 17 JANUARY 2020
```

Across the 123 filings with extracted text (see gap below): 108 (88%) contain an explicit "Nature of the
transaction" field, and 107 (87%) contain an ISIN identification code — both strong, standardized anchors
for a deterministic parser. A crude keyword scan found "SALE" in 6 and "PURCHASE" in 38 of the readable
filings (imprecise — not a rigorous count, since the words can appear in boilerplate — but directionally
consistent with a real skew toward reported purchases, a substantive detail worth confirming once a real
parser exists, not concluded here).

## Data-completeness gaps (disclosed, not worked around)

- **Text extraction incomplete: 123/163 (75%)** have a populated `text_path`; the remaining 40 are
  PDF-only. Filling this gap reuses the existing `pdfplumber` extraction pipeline already used for the
  X-Compliance reports (Stage 18) — no new scraping, no new tooling, just running the existing process
  against already-acquired PDFs.
- **Ticker identity: 15/163 (9%) unresolved** (`ticker IS NULL`), as above.
- **Format variety unverified at scale.** Only two document shapes were directly sampled here (a
  single-insider SALE notice, and a 651-employee vesting table). NGX's disclosure forms are known from
  other stages (X-Compliance, corporate actions) to vary in layout across issuers and years; a real parser
  would need to handle multiple template variants, and this has not yet been characterized across the
  full 123-document text set — a concrete next step, not yet done.
- **Multi-transaction / multi-employee filings complicate "one filing = one signal."** The sampled vesting
  notice alone contains 651 separate name/quantity rows in one document; the UNIONDAC sale notice contains
  two separate dated transactions in one filing. Any extraction design needs a clear unit of observation
  (per-transaction-line, not per-document) decided before parsing, not after.

## Frequency / statistical power (a real concern, not glossed over)

After excluding vesting notices (~12–15) and unresolved-ticker rows (15, with some overlap likely), the
usable open-market dealing-notice corpus is on the order of **~130–140 filings across 29 tickers, 2020–
2026**, heavily concentrated in 3 names. This is a materially larger sample than H-019's n=11 (2
executable), but still thin by any standard, and the concentration means effective cross-sectional breadth
is much smaller than the raw filing count suggests. This should be stated up front in any future
preregistration, not discovered after building a factor — consistent with this project's own standing
discipline about small-n event studies.

## Survivorship

None of the 29 tickers in the dealing-notice corpus are flagged `delisting_date IS NOT NULL` in
`securities`, and all have price coverage in `equity_prices`. This is **not** strong evidence of clean
survivorship, however — `securities.delisting_date` is NULL platform-wide (the same gap noted in Stage 19
§5), so an absence of a delisting flag proves nothing either way. This remains genuinely unresolved, not
positively confirmed.

## PIT / provenance

`filing_date` is the real, first-party disclosure timestamp (`ngx_xissuer_documents`, confidence 0.85) —
clean, matches the pattern already used platform-wide, and could be covered by the same kind of
provenance guard as `scripts/test_event_document_provenance.py` (extending it to `doc_type='dealing'`
would be a small, mechanical addition, not a new mechanism).

## Verdict: **feasible, but as a bounded pilot, not a direct build**

Extraction of the core fields (ticker, insider name/position, nature=buy/sell, date, quantity, price) from
the ~130–140 open-market filings is technically straightforward — deterministic, no LLM judgment, no new
data acquisition, reuses existing pipeline components. It should **not** be scoped as "parse all 163 and
go" — the vesting-notice exclusion, the 15 null-ticker rows, the 40 missing-text filings, and the
unverified format variety across the full set are all real, named blockers to a clean full-corpus parse,
not hypotheticals.

**Recommended next step, if authorized:** a bounded pilot — complete text extraction for the remaining 40
PDFs (mechanical, existing tooling), resolve or explicitly mark the 15 null-ticker rows, hand-verify a
larger sample (10–15, not 2) across different issuers/years to characterize format variety, and only then
build the deterministic parser against the full, now-characterized corpus. This mirrors the same
bounded-pilot-before-scale-build discipline used for the X-Compliance/regulatory corpus in Stages 11–14
and 18–19. No hypothesis, factor, or backtest follows from this scoping — that remains gated on the
pilot's own results, exactly as Stage 20 already anticipated.
