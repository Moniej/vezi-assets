# STAGE 9 — FINAL FUNDAMENTAL-DATA TRACK CLOSURE

*2026-08-08. Diagnostic only. Zero new `extracted_facts` rows this
stage (none of the 8 audited tickers qualified as HARVEST GAP).
`configs/h011_size.toml`, `docs/PREREG_H-011.md`, H-011's signal/
construction, and all frozen experiment records are unmodified. No
hypothesis created. No performance test, backtest, portfolio
construction, optimization, or preregistration was run.*

---

## 1. Executive Summary

**Answering the one question this stage exists to answer: No — H-011's
actual investable universe cannot, with the data currently in this
archive, support a research-ready fundamental factor.**

Four stages of increasingly targeted searching (Stage 6: initial
targeted extraction; Stage 7: bounded completeness audit; Stage 8:
deeper re-audit with page-level document processing; Stage 9: final
structural-evidence and trading-activity check) have converged on the
same number: **research-ready H-011 overlap is 0 of 20 (0%), and it has
been 0% at every single checkpoint.** The evidence gathered along the
way did not fail to find data — it found, with increasing specificity,
*why* the data mostly isn't there.

**Decision: NO-GO.**

---

## 2. Final Evidence Table — The 8 Remaining Undetermined Tickers

| ticker | total docs | new evidence this stage | trading activity (since 2020) | final classification |
|---|---|---|---|---|
| CAVERTON | 2 | No structural-keyword hits (RECEIVERSHIP/WINDING-UP/PETITION/LIQUIDAT/SUSPEND/DELIST/DELAY/DEFAULT searched across all docs) | 1,588 trading days, continuously traded through 2026-07-21 | **UNDETERMINED AFTER FINAL AUDIT** |
| CUTIX | 111 | No structural-keyword hits despite the largest-but-one document pool in this population | 1,593 trading days, continuous | **UNDETERMINED AFTER FINAL AUDIT** |
| MCNICHOLS | 56 | No new hits; the Stage 8 2014 fragment remains unusable (unverifiable scale) | 1,003 trading days, continuous | **UNDETERMINED AFTER FINAL AUDIT** |
| NSLTECH | 25 | One isolated 2017 "DELAY IN FILING ACCT" notice (already known) — insufficient alone per the no-single-instance rule | 860 trading days, continuous | **UNDETERMINED AFTER FINAL AUDIT** |
| OMATEK | 19 | No structural-keyword hits | 961 trading days, continuous | **UNDETERMINED AFTER FINAL AUDIT** |
| REDSTAREX | 59 | No structural-keyword hits despite a substantial document pool | 1,575 trading days, continuous | **UNDETERMINED AFTER FINAL AUDIT** |
| SUNUASSUR | 101 | No structural-keyword hits despite the largest document pool in this population | 1,244 trading days, continuous | **UNDETERMINED AFTER FINAL AUDIT** |
| TANTALIZER | 22 | **A SECOND delay-type notice found**: "TANTILIZERS - DELAY IN HOLDING AGM FOR 2023" (filed 2024-12-13), joining the previously-known 2017 "DELAY IN FILING ACCT" notice — two instances, 7 years apart | 979 trading days, continuous | **RECLASSIFIED: STRUCTURALLY SPARSE** |

**Method**: (1) a structural-distress filename search (`RECEIVERSHIP|
WINDING.?UP|PETITION|LIQUIDAT|SUSPENSION|SUSPENDED|DELISTING|DELIST|
INSOLVEN|DELAY|DEFAULT|LATE.?FILING`) across **every** document (not
just unextracted ones) for all 8, closing the one search angle prior
stages had applied unevenly; (2) an `equity_prices` trading-activity
check (2020-present) as corroborating evidence, since a company in
genuine distress often also shows suspended/thin trading.

**A genuinely informative negative finding from the trading-activity
check**: all 8 tickers show continuous, active, apparently normal
trading through 2026 — none show the trading-suspension signature that
corroborated RTBRISCOE's receivership finding in Stage 8. This is
disclosed as a real data point that argues AGAINST severe structural
distress for these specific 7 remaining names (TANTALIZER now
reclassified), not toward it — consistent with treating them as
"genuinely unknown" rather than reaching for a structural explanation
the evidence doesn't support.

**No ticker qualified as HARVEST GAP this stage — zero new facts were
extracted**, correctly, per 9B's instruction to extract only if a
genuine harvest gap is found.

---

## 3. Final Classification Tally (all 18 originally zero-coverage tickers, Stages 6-9 combined)

| Classification | Count | Tickers |
|---|---|---|
| **HARVEST GAP (resolved)** | 1 | DEAPCAP — extracted (Stage 8), 2 periods, still short of research-ready |
| **STRUCTURALLY SPARSE** | **10** | CILEASING, LEGENDINT, NCR, PRESTIGE, ROYALEX, WAPIC (Stage 7) + RTBRISCOE, REGALINS, UNIVINSURE (Stage 8) + **TANTALIZER (Stage 9)** |
| **UNDETERMINED AFTER FINAL AUDIT** | **7** | CAVERTON, CUTIX, MCNICHOLS, NSLTECH, OMATEK, REDSTAREX, SUNUASSUR |

**More than half (10/18, 56%) of the audited population now carries
direct, dated, self-disclosed evidence of a structural reporting
problem** — delay notices, default notices, or (in RTBRISCOE's case)
formal receivership status stated on the company's own letterhead. This
is the final, settled figure for this track; no further structural
evidence is expected to be found by continued archive searching, since
the methods applied (content search, P&L-precision search, filename
search across both extracted and unextracted documents, structural-
keyword search, trading-activity cross-check) have now been exhausted
across four stages.

---

## 4. Final Coverage / Readiness Matrix

Computed live against H-011's own unmodified signal code (2026-06-30
formation, unchanged from Stage 6):

| ticker | full FS periods | IRU mkt-cap rank | sector |
|---|---|---|---|
| DEAPCAP | 2 | 95 | FINANCIAL SERVICES |
| VERITASKAP | 2 | 78 | FINANCIAL SERVICES |
| LASACO | 1 | 79 | FINANCIAL SERVICES |
| all other 17 | 0 | 77-96 | mixed |

- **Financial Strength code-eligible tickers (H-011 universe): 3 of 20 (15%).**
- **≥2-period tickers: 2 of 20 (10%)** — DEAPCAP, VERITASKAP.
- **≥3-period (research-ready) tickers: 0 of 20 (0%).**
- **Median historical depth (of the 3 eligible): 2.0. Minimum: 1.**
- **Sector distribution (of the 3 eligible): 3 of 3 in FINANCIAL SERVICES** — a real, notable concentration at this small sample size (not further analyzed given n=3, consistent with the "do not manufacture statistical significance from a tiny sample" instruction carried from Stage 6).
- **Market-cap rank distribution (of the 3 eligible): 78, 79, 95** — all in the bottom quintile of the IRU, consistent with H-011's own construction (unlike the original Stage 4/5 large-cap-skewed set).
- **Harvest gaps: 1 (resolved). Structurally sparse: 10. Undetermined: 7.**
- **Maximum theoretically achievable research-ready overlap, if every one of the 7 undetermined names turned out fully recoverable to 3+ periods: 10 of 20 (50%).** Stated as a ceiling, not an expectation — this program's own repeated experience across Stages 6-9 is that the great majority of "not found" cases resolve to genuine absence or, at best, thin (1-2 period) recovery, not full 3+-period depth. A more realistic expectation, extrapolating from DEAPCAP's own outcome (the one confirmed harvest gap, which yielded 2 periods, not 3), is that even a fully successful recovery of all 7 remaining names would likely still fall short of the 3-period bar for most of them.

---

## 5. Nominal vs. Research-Ready H-011 Overlap — The Critical Distinction

- **Nominal overlap (≥1 period): 3 of 20 (15%).**
- **Research-ready overlap (≥3 PIT-safe periods): 0 of 20 (0%).**

**Research-ready overlap has been 0% at every checkpoint in this
program**: Stage 5 (0%), Stage 6 (0%), Stage 7 (0%), Stage 8 (0%), Stage
9 (0%). Nominal overlap moved from 5% (Stage 5) to 10% (Stage 6) to 15%
(Stage 8, holding through Stage 9) — a real, honestly-earned increase in
raw coverage — **but it has never once translated into a single
research-ready name.** This is the decision variable, and it has not
moved.

---

## 6. Final H-018 Decision: **NO-GO**

Per your explicit framing: this is not a case for CONDITIONAL. There is
no concrete, demonstrated recoverable data that would materially change
the gate. The evidence supports NO-GO directly:

1. **Research-ready overlap is 0% and has never been otherwise**,
   across five independent checkpoints spanning three stages of
   targeted, increasingly rigorous search.
2. **56% of the originally-unresolved population now carries direct,
   dated, self-disclosed evidence of structural reporting problems** —
   not inferred, not assumed, read directly off the companies' own
   filed notices (and in RTBRISCOE's case, off the company's own
   letterhead stating receivership).
3. **The one genuine harvest-gap success (DEAPCAP) still fell short** —
   real, substantial, correctly-extracted data that nonetheless
   produced only 2 periods, one short of the research floor, with no
   further document available anywhere in the archive to close that gap.
4. **The realistic ceiling, even under the most optimistic assumption
   about the 7 remaining undetermined names, is 50% nominal overlap** —
   and nominal overlap has never once converted to research-ready
   overlap in this program's actual experience.

**The limiting factor is not extraction quality. It is the intersection
between H-011's small-cap investable universe and the availability/
depth of reliable fundamental data.** Stated plainly, per your
instruction: continuing to search the same archive for the same 7
remaining names is very unlikely to change this conclusion, and doing
so would repeat — at further cost — a pattern this program has now
observed consistently across four stages.

---

## 7. Formal Closure

**The Financial-Strength-inside-H-011's-universe fundamental-data track
is formally closed as of this stage.** No further extraction effort
should be directed at completing Financial Strength (or, by direct
implication given the shared field/document requirements established in
Stage 4, Cash Flow Quality, Quality, Value, Profitability, Asset
Turnover, or Gross Profitability) for H-011's specific 20-name universe
using this archive. This is recorded as a legitimate, disciplined
research finding — the platform now has a rigorous, well-evidenced
answer to a real question, not an open-ended pursuit that was simply
abandoned.

**What remains true and unaffected by this closure**: the LARGE-CAP-
skewed Financial Strength dataset built in Stages 3-5 (10-11 tickers,
8 with 3+ periods, clean accounting validation throughout) remains a
real, usable asset for any FUTURE hypothesis that does not require
H-011-universe overlap — it was never invalidated, only shown to be the
wrong tool for combining with H-011 specifically.

---

## 8. Recommended Next Research Track

Per your own explicit criteria for what should come next — high
coverage across H-011's actual holdings, sufficient historical depth,
reliable PIT availability, low dependence on large-cap/liquid names,
and genuinely different information from H-011's market-cap signal —
**fundamental/financial-statement data is now a poor candidate by
demonstrated fact, not assumption.** Two candidates from this program's
own prior audits fit your stated criteria better and have NOT yet been
exhausted:

1. **Insider/substantial-shareholder dealing data** (Stage 3D/Stage 2
   Section 5): 163 archived disclosures, standardized form, clean
   transaction-date/filing-date fields — genuinely different information
   from a market-cap signal (transaction-based, not statement-based).
   **Still gated on its own unresolved completeness question** (the
   2021+ coverage collapse Stage 3D flagged as likely a harvest gap, not
   a real decline) — that audit, not fundamentals, is the next
   defensible step.
2. **Corporate-action / bonus-scrip data** (Stage 3C): already
   demonstrated real, extractable, standardized disclosures for several
   H-011-adjacent names (CILEASING, LASACO both directly resolved with
   real ratios). This is a data-integrity improvement, not a new alpha
   source, but it directly protects H-011's own return series and has a
   demonstrated, not hypothetical, extraction success rate inside names
   near H-011's universe.

**Do not restart fundamental extraction for H-011's universe without
new evidence that would change Section 6's conclusion** — specifically,
evidence that NGX's live disclosure system holds statements this
platform's harvest never captured for the 7 remaining undetermined
names, which is itself the one open question this stage did not (and,
per its bounded scope, should not) resolve.
