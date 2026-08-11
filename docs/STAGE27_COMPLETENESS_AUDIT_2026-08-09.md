# Stage 27 — Final Data-Completeness and Adversarial Audit (Insider-PURCHASE Track)

**Date:** 2026-08-09
**Status:** Completeness audit + re-run of the frozen Stage 24/25/26 diagnostic. No hypothesis, no H-024,
no signal-rule changes, no backtest. Zero DB writes — all recovered data lives in
`data/staging/stage27/`. Frozen spec unchanged throughout: PURCHASE only, k=20 primary horizon,
PIT = first session strictly after `filing_date`, NGXASI benchmark, 3.79% round-trip cost floor
(`cost_schedule`, unmodified), insider×ticker×direction×month aggregation, 5/95% winsorization.

**Question:** is the 24.5%-of-corpus OCR gap now closed, materially reduced, or still disqualifying —
and does insider-PURCHASE remain CONDITIONAL GO once it is addressed?

---

## 1–3. Recovery method and result — a disclosed methodological substitution

No system OCR engine (`tesseract`) exists in this environment, and installing it plus Python bindings
stalled during this session. Rather than block on that, the 40 scanned-image PDFs' embedded JPEG streams
were extracted directly (byte-level, reusing `pdfplumber`/`pypdf` — the same tooling already used
platform-wide, no new acquisition layer) and **every one of the 40 images was read and transcribed
directly**, not sampled. This exceeds the instruction's "representative sample" requirement — the full
population was hand-verified, eliminating sampling risk entirely. Two images required a `pypdf` fallback
after `pdfplumber` reported 0 pages on malformed PDF structures (4139, 4216, 4287, 7943) — a distinct,
minor technical finding, resolved without altering any classification rule.

**Classification of all 40 (frozen Stage 23/24 rules applied throughout, unmodified):**

| Category | n | Detail |
|---|---|---|
| Genuine PURCHASE | 19 | FLOURMILL(6), NESTLE(5), WAPIC(2), OKOMUOIL(2), MBENEFIT(1), VITAFOAM(1), ABCTRANS(1), MCNICHOLS(1) |
| Genuine SALE | 3 | NPFMCRFBK(1), MBENEFIT(1), VITAFOAM(1) |
| Vesting (excluded) | 5 | ACCESSCORP(2), FIDELITYBK(3) — all carry explicit "not a purchase or sale" disclaimers |
| Cross-deal (correctly unclassified — no PURCHASE/SALE keyword match) | 3 | MBENEFIT — "Cross Deal", "Sales by cross dealing", "Cross deal by sales" |
| Not a dealing notice at all | 1 | Fidelity Bank press release *denying* an insider-trading allegation (doc_id 9861) — mentions "share purchase" but is not a transaction disclosure |
| Genuinely unreadable | 9 | 1 (GTCO, doc_id 4203) — extremely faint/corrupted scan, unreadable even after contrast enhancement; 8 (all NESTLE, Nov–Dec 2020) — **byte-identical corrupted embedded image** (verified MD5 hash `04f7d4a2...` across all 8), a genuine source-level data-loss artifact, not an extraction bug |

**Field extraction**: ticker, insider name/role, transaction type, transaction date, and shares/price were
recovered for all 22 genuine transactions with no inference — where a filing's own aggregate line gave
the authoritative total (e.g. doc_id 4001's 32-line-item purchase, confirmed on page 2: 1,254,950 units
at avg N0.50), that figure was used rather than a partial manual sum.

**One duplicate found and flagged, not silently collapsed**: doc_id 4322 (filed 2020-11-12) is a
byte-different PDF but reports the *identical* underlying transaction as doc_id 4141 (filed 2020-09-15) —
same insider (NESTLE S.A.), same date (11 Sept 2020), same 229,697 units at N1,249.65. This is a genuine
republished/reissued disclosure of one transaction under a new document ~2 months later. Per instruction,
it was **not silently collapsed** — it is excluded from the independent-event count below with this exact
reasoning on record, and preserved in the raw audit trail.

**Gap status: materially reduced, not fully closed.** 31 of the original 40 blocked filings (77.5%) were
successfully resolved. 9 remain genuinely unrecoverable — 5.5% of the full original 163-filing corpus —
and this is now a *characterized*, source-level data-loss finding (confirmed corrupted at the document
repository, not a extraction-tooling limitation), not an unknown black box.

## 4. With vs. without OCR-recovered data — the decisive comparison

| | Without OCR-recovered (Stage 24/25/26) | With OCR-recovered (complete) |
|---|---|---|
| Filings | 109 | 130 (163 − 9 unreadable − 24 excluded non-genuine, minus 1 flagged duplicate) |
| Aggregated events | 67 (14 tickers, 53 insiders) | 82 (22 tickers, 64 insiders) |
| PURCHASE events, k=20 | 53 | 65 |
| Mean excess return | +5.74% | **+4.59%** |
| Median excess return | +5.15% | +5.15% (unchanged) |
| % positive | 77.4% | 69.2% |
| Ticker-clustered p-value | 0.0009 | **0.0537** |
| Exact sign-permutation p-value (G tickers) | 0.0156 | **0.6019** |
| Equal-ticker-weighted mean | +5.79% | +5.35% |

The point estimate (mean) still nominally clears the 3.79% cost floor. **The statistical evidence does
not.** The exact permutation test — the most conservative, small-G-appropriate method used throughout
this program, and the one Stage 26 relied on most — collapses from p=0.0156 (clearly significant) to
p=0.60 (indistinguishable from chance). This is not noise from a marginal change; it is the central
finding of this stage.

## 5. Why: one extreme observation is now doing the work

Isolating the 8 new tickers introduced by the recovered data (22 events) shows a stark, decisive pattern:

| Ticker | Insider | Excess return (k=20) |
|---|---|---|
| **MCNICHOLS** | Chimaraoke Nwokoma Ekpe (CEO) | **+101.6%** |
| NESTLE | NESTLE S.A. | -3.6% |
| NESTLE | NESTLE S.A. | -4.7% |
| VITAFOAM | Dr. B.O. Makanjuola | -5.6% |
| MBENEFIT | Ebube Ezeagwula | -5.7% |
| OKOMUOIL | SOCFINAF S.A. | -8.2% |
| NESTLE | NESTLE S.A. | -10.9% |
| WAPIC | United Alliance Co. | -12.0% |
| OKOMUOIL | SOCFINAF S.A. | -13.5% |
| ABCTRANS | Rapido Ventures Ltd | -19.2% |

**Every single newly-recovered event except one is negative.** The lone exception — a CEO purchase in
MCNICHOLS, a micro-cap penny stock, December 2023 — returned +101.6%, an extreme outlier by any standard.

- **Excluding MCNICHOLS alone**: mean drops to **+3.07%**, below the 3.79% cost floor.
- **Winsorizing the complete with-OCR set** (the same 5%/95% treatment used throughout this program):
  mean drops to **+2.99%**, also below the cost floor.

Both of the program's own standard adversarial safeguards — single-extreme-observation removal and
winsorization — independently show the completed corpus's PURCHASE effect **fails to clear transaction
costs**. Only the untreated, non-robust point estimate survives, and it survives by a shrinking margin
propped up almost entirely by one micro-cap outlier.

## 6. Systematic-difference test — the missingness was not random

- The 22 recovered genuine transactions are **91% concentrated in 2020** (20/22), reinforcing rather than
  diluting the corpus's existing temporal concentration (Stage 23 §6).
- **8 new tickers** were introduced (ABCTRANS, MCNICHOLS, NESTLE, VITAFOAM, NPFMCRFBK, MBENEFIT, OKOMUOIL,
  WAPIC) that had zero prior representation in the readable corpus — a real broadening of breadth, but
  see above: broadening the sample is exactly what exposed the fragility.
- **Direction and outcome were not random**: excluding the single outlier, every recovered PURCHASE
  observation is negative — the previously-inaccessible data was systematically *less* supportive of the
  effect than the already-readable corpus, not a neutral or confirmatory addition. This is precisely the
  scenario the task's own instruction ("do not assume missingness is random") warned against, now
  confirmed empirically rather than assumed.

## 7. Leave-one-ticker-out on the completed corpus

Two tickers, when excluded, now drop the mean below the cost floor — up from zero in Stage 25's version
of this test:

| Ticker excluded | Resulting mean | Clears cost? |
|---|---|---|
| MCNICHOLS (n=1 removed) | +3.07% | **NO** |
| UCAP (n=20 removed) | +3.09% | **NO** |
| All other 15 tickers | +4.28% to +5.12% | YES |

MCNICHOLS breaking the cost floor on the removal of a *single* observation is the sharpest, most direct
confirmation that the completed corpus's headline mean is not "materially supported by the distribution"
— the exact standard Stage 25 used to distinguish a real effect from an extreme-observation artifact.

---

## Verdict: **NO-GO** — downgraded from CONDITIONAL GO

This reverses Stages 24–26's read, on the strength of genuinely new, previously-inaccessible evidence,
not a change in method or standard. Applying the same adversarial tests this program has used
consistently throughout (winsorization, single-extreme-observation removal, exact small-G permutation
inference) to the **completed** corpus — not the 66%-complete one Stages 24–26 worked with — shows the
insider-PURCHASE-at-k≈20 effect does not survive. The point estimate technically still clears the cost
floor, but every one of this program's own robustness checks says that number is not trustworthy: it is
carried by one micro-cap outlier, it loses its statistical significance under exact inference, and the
median, while stable, was never enough on its own to justify a GO under this program's standing
discipline (Stage 21C treated an analogous mean/median divergence as decisive against a track).

**Direct answer to the completeness question**: the 24.5% gap is **materially reduced** (77.5% of it
recovered, hand-verified in full) but **not fully closed** — 9 filings (5.5% of the original corpus)
remain genuinely unrecoverable due to source-level document corruption, confirmed rather than assumed.
Closing that gap further is not the reason for this stage's verdict, however — the recovered majority of
the gap is what produced the disconfirming evidence. This closes the insider-dealing mechanism-discovery
track. No hypothesis was ever registered; none is warranted now.
