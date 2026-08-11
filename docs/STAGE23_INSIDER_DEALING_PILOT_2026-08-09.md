# Stage 23 — Bounded Insider-Dealing Pilot

**Date:** 2026-08-09
**Status:** Pilot only. No hypothesis registered, no returns calculated, no factor built, no backtest.
No new scraping (all 163 filings were already-acquired PDFs from `ngx_xissuer_documents`). Scripts:
`scripts/stage23_extract_remaining_dealing_pdfs.py`, `scripts/stage23_insider_dealing_pilot.py`. Raw
output preserved at `data/staging/stage23/` (`all_filings_classified.csv`,
`genuine_transactions_with_dupkey.csv`). Zero writes to `ngx.sqlite` — all extraction cached to the
existing `data/staging/document_text/` convention only.

**Question:** do we have a sufficiently clean and independent insider-disclosure dataset to investigate
whether public disclosure creates persistent, executable repricing? Nothing beyond that.

---

## 1. Corpus extraction — a hard technical finding

All 40 previously-untexted PDFs were run through the existing pdfplumber pipeline. **All 40 returned 0–1
characters of native text.** Direct inspection (doc_id 3853) confirms why: single-page filings with 1
embedded image and 0 extractable characters — these are **scanned image PDFs, not native-text PDFs**,
unlike the 123 already-processed filings. Native extraction cannot recover these; OCR would be required.

Per instruction, the acquisition layer was not changed to work around this — OCR is a materially larger
capability (a new dependency, `tesseract`) that this project has already flagged elsewhere
(`docs/RESEARCH_ROADMAP_2026-07.md`, "Blocked... needs OCR — user-gated tesseract decision") as requiring
explicit owner sign-off, not something to fold in silently inside a bounded pilot. **These 40 filings
(25% of the corpus) remain unusable in this pass, blocked on that same pending decision, not on anything
specific to this pilot.**

## 2. Classification (all 163 filings)

| Classification | n |
|---|---|
| genuine insider PURCHASE | 83 |
| genuine insider SALE | 26 |
| vesting/non-trade (excluded, per instruction) | 6 |
| unusable/ambiguous | 48 |

Of the 48 unusable: 40 are the scanned-image PDFs from §1 (no text at all); 8 have native text but no
deterministically resolvable PURCHASE/SALE keyword dominance (both or neither present) — genuinely
ambiguous, correctly left unclassified rather than guessed.

**109 genuine, directional transaction disclosures** (83 purchase / 26 sale) is the base corpus for
everything below.

## 3. Null-ticker resolution — a structural database gap, not a parsing failure

**0/15 resolved** via `securities` table matching. Root cause, confirmed directly: `securities.name` is
identical to `securities.ticker` for **all 320 rows** (no full company name is stored anywhere), and
`securities.isin` is **NULL for all 320 rows** (0% populated). There is no company-name-to-ticker mapping
table anywhere on the platform — this made deterministic resolution via "existing securities/company
mappings" structurally impossible, not merely difficult.

However, the filing text itself (an allowed deterministic source per instruction) states the issuer name
plainly in all 15 cases: 14 say "Nigerian Breweries Plc," 1 says "Airtel Africa plc." Both NB and
AIRTELAFRI already appear elsewhere in this same corpus under their correct tickers, filed by the same
issuer — a strong, disclosed lead, not a guess. **Per instruction, these 15 remain explicitly quarantined
in every count below** (not folded into the "resolved" corpus) — this is reported as a finding for a
future stage to act on deliberately, not applied silently here.

## 4. Duplicate/reissue audit — two very different pictures depending on method

**Authoritative check (exact `source_url` match, independent of extraction quality):** exactly **one**
genuine duplicate pair — doc_id 5083/5084, an identical URL ingested twice. Everything else in the corpus
has a distinct source URL.

**Secondary, exploratory check (exact match on extracted ticker+date+name+shares+type):** initially
flagged 9 "duplicate" groups covering 27 filings. Hand inspection of every group found these are **false
positives** caused by incomplete field extraction — e.g. the flagged "5-way AIRTELAFRI duplicate" is
actually 5 *distinct* filings on 4 different dates (2024-03-26 ×2, 03-27 ×2, 04-03) by the same recurring
institutional insider, not one transaction reported five times; the "4-way CUTIX duplicate" is 4 filings
whose own filenames encode 4 different underlying transaction dates (241221, 311221, 050122, 070122),
batch-disclosed on a single filing date. **This is reported honestly as a limitation of the extraction,
not as evidence of real duplication** — the true duplicate count is the one confirmed above, not 27.

## 5. Format-variety audit — confirms Stage 22's warning, empirically

Hand-verification across the corpus (not the original 2 documents) found **at least three distinct date
formats** in live use: `"14 JANUARY 2020"` (plain), `"26th June, 2020"` (ordinal suffix), `"Tuesday,
September 22, 2020"` (weekday-prefixed) — and **two distinct field-layout variants** for the insider-name
field (label and value on separate lines vs. same line). The parser was extended twice during this pilot
to cover variants found by hand-reading actual failures, and **still leaves 71/109 (65%) of genuine
transactions with an unresolved `transaction_date_raw`** (marked UNKNOWN, not guessed). This confirms
Stage 22's explicit warning: **the parser does not fully generalize from a small sample, and each new
template discovered required bespoke handling** — a real, bounded-but-nonzero engineering cost for any
future full build, not a one-time template match.

Important qualifier: this UNKNOWN rate applies to `transaction_date` (when the insider actually traded),
**not** to `disclosure_date`/`filing_date` (when the information became public) — see §7. The field that
actually matters for PIT-safe signal construction is intact.

## 6. Concentration analysis (cleaned corpus: 109 genuine, ticker-resolved subset)

| Metric | Value |
|---|---|
| Total filings | 163 |
| Genuine transactions | 109 (83 purchase / 26 sale) |
| Unique resolved tickers | 15 (+15 quarantined unresolved) |
| Top 3 tickers' share | UCAP(35)+INITSPLC(14)+FCMB(9)... wait see below = 64/109 = **58.7%** |
| Top 5 tickers' share | 81/109 = **74.3%** |
| Transactions/ticker | median well under mean; UCAP alone = 35 (32% of the whole corpus) |
| Transactions/year | 2020: 70 (64%); 2021: 21; 2022: 5; 2024: 8; 2025: 4; 2026: 1 |

**This corpus is severely concentrated on two independent axes at once**: by ticker (top 3 names carry
59% of all observations; effective cross-sectional breadth is closer to 5–6 names than 15) and by time
(nearly two-thirds of all observations come from a single year, 2020, with a thin, uneven tail through
2026 — cause not established; could be a real 2020-specific disclosure wave or an acquisition-completeness
artifact of this specific document source, not distinguished here). Both facts directly bear on whether
future observations would be *independent* in any meaningful sense — they are not evenly distributed
across names or time, and any future diagnostic must treat this as a small, clustered sample, not 109
independent draws.

## 7. PIT/provenance audit — the hard gate, and it holds

- **`disclosure_date` (= `documents.filing_date`)**: populated for all 163 filings (100%), a real
  first-party NGX timestamp — this is the correct anchor for signal construction per the instruction's own
  framing ("based on when the information became publicly knowable — not when the insider actually
  transacted"). This field is clean regardless of the transaction_date extraction gap in §5.
- **`transaction_date`**: successfully extracted for 38/109 (35%) of genuine transactions; the remaining
  65% are marked UNKNOWN rather than guessed, per instruction. This is a real gap for any analysis that
  wants to know the transaction-to-disclosure lag itself, but is **not fatal** to PIT-safety of the
  eventual signal, since the signal's own timestamp would be `disclosure_date`, not `transaction_date`.
- No intraday disclosure timestamp exists anywhere in this corpus — only a filing date. Per instruction,
  the conservative trading-session boundary (treat the disclosure as known no earlier than the next NGX
  session after `filing_date`) is the correct convention for any future stage, not attempted or refined
  here since no returns are being examined in this pilot.

## 8. Survivorship audit

No ticker in the resolved 15-name corpus was found missing from `equity_prices` entirely — a clean
positive check, as far as it goes. But consistent with Stage 19 §5 and Stage 22's own finding,
**`securities.delisting_date IS NULL` platform-wide cannot be read as evidence of survival** — the
database has no way to positively confirm none of these tickers were ever delisted; it can only confirm
price data exists through whatever the ticker's own history covers. This limitation is unresolved, as
instructed, not glossed over.

## 9. H-011 independence — structural, not performance-based

**Mechanical dependency: none.** `size_scores()` (`src/ngxrot/backtest_xs.py:319`, re-confirmed) consumes
only `panel["mcap"]` and price-panel IRU eligibility — nothing from `documents`, `events`, or any
dealing-notice-derived field. There is no code path by which this corpus could contaminate or be
contaminated by H-011's inputs.

**Possible common-cause correlation: real and substantial, not dismissed.** Cross-referencing the 18
distinct tickers appearing anywhere in the dealing-notice corpus (genuine + quarantined) against the
latest available `market_cap_nm` in `market_cap_panel.csv`: **16/18 (89%) sit above the platform-wide
median market cap**, and the corpus includes several of the platform's single largest names by market
cap (AIRTELAFRI, MTNN, DANGCEM, SEPLAT). This is very likely a **governance/compliance-culture
common-cause effect**: larger, more heavily-regulated, often cross-listed issuers (Seplat and Airtel
Africa both use UK/EU-style "PDMR" — Person Discharging Managerial Responsibilities — terminology in
their filings, consistent with dual-listing compliance obligations) file insider-dealing notices more
reliably than smaller NGX-only names, independent of any actual trading signal. **This means the corpus
is not a representative cross-section — it is a large-cap-skewed sample by construction**, and any future
diagnostic must orthogonalize against size at least as rigorously as the (now-closed) illiquidity work
did, or risk mistaking a governance/size effect for an insider-information effect.

---

## Verdict: **CONDITIONAL GO**

The underlying data source is real, first-party, and PIT-safe at the disclosure-date level (§7) — that
gate holds cleanly. Extraction genuinely works, is deterministic (no LLM used anywhere in this pilot),
and generalizes across at least three real template variants once hand-corrected, though not perfectly
(§5). Duplication risk is low once measured correctly (§4) — the initial alarming 27-filing "duplicate"
signal was a parser artifact, not a real problem, and that distinction matters for the verdict.

But this is not a clean GO: the corpus's effective breadth is far smaller than its raw count suggests
(§6 — concentrated in ~5–6 names, two-thirds from a single year), 25% of filings remain fully blocked on
an already-flagged, pending OCR decision (§1), 15 filings (9%) have no resolvable ticker via any database
mechanism and must stay quarantined (§3), and there is a real, unaddressed, plausible common-cause
confound with size/governance quality (§9) that has not been — and per this pilot's scope, could not be —
tested against returns.

**Named conditions before a return diagnostic would be justified:**
1. Resolve the OCR/scanned-PDF question (owner decision, already pending elsewhere) — or explicitly accept
   the smaller, native-text-only corpus and disclose the exclusion.
2. Formally resolve or permanently exclude the 15 quarantined null-ticker filings (the filing-text leads
   in §3 are a strong starting point, not yet acted on).
3. Any future diagnostic must explicitly orthogonalize against market cap given the 89% large-cap skew
   found in §9 — treating this as an independent, non-size-driven signal without that control would not
   be credible given what this pilot found.
4. The severe ticker/time concentration (§6) must be stated up front as a standing power caveat, exactly
   as this project has done for every small-n event study to date (H-019, the suspension-lift track) —
   this is not 109 independent observations.

None of these are contamination findings that kill the track — they are bounded, nameable prerequisites,
which is what distinguishes this from a NO-GO.
