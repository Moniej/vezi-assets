# vwap_inconsistent triage — 2026-07-21

Triage of the 469 `vwap_inconsistent` warns logged by
`scripts/run_equity_diagnostics.py` (D4b: value/volume outside [0.25, 4]x
close). Method: extracted the archived source PDFs from
`data/archive/pricelist_zips` and compared the printed VOLUME/VALUE columns
against the ingested `ngx_pricelist_v1` rows.

## Verdict: zero parse errors. No restatement warranted.

Every checked row matches the exchange PDF verbatim. The warns split into
three classes:

### 1. Whole-day source outages — 2015-05-28 (108 warns) and 2017-07-12 (110)

The exchange's own PRICES1.pdf printed a broken VALUE column those days:

- **2015-05-28**: 110 of 111 rows print `VALUE = 0.00` despite positive
  volume. The single nonzero row (FO: 5,283,300.00 on 400,882 shares at
  ~176) implies VWAP 13.2 — also garbage. The entire column is unusable.
- **2017-07-12**: 81 of 113 rows print `0.00`; the 32 nonzero prints are
  also implausible (7UP: 66,470.00 on 49,224 shares at ~87-89, implied
  VWAP 1.35). The entire column is unusable.

Parser output cross-checked against raw `extract_text`: every nonzero VALUE
in the PDFs matches the DB to the kobo (one absence: NEWGOLD 2017-07-12,
an ETC not ingested with a value). This is an NGX reporting-system glitch,
not a parse error, so per PIT convention there is nothing to restate — the
vintage faithfully records what the exchange published.

**Recommendation**: treat `value_traded` as untrusted (effectively NULL)
for source `ngx_pricelist_v1` on these two dates in any VWAP/liquidity
consumer. Candidate mechanism: day-level `data_quality_log` entry
(severity `error`, day scope) that consumers can join against, rather than
mutating rows.

### 2. FGN bonds / sukuk / ETFs — 245 warns, 58 tickers, false positives

`FG*`, `FGS*`, `FGSUK*`, `*BOND*`, `*ETF*`, NEWGOLD (gold ETC),
VSPBONDETF, MERVALUE (fund). Fixed-income consideration is computed on
face/accrued-interest terms, not price-times-units, so the D4b
vwap-vs-close band is meaningless for them. Heaviest: FGSUK2027S3 (32),
FGSUK2031S4 (25).

**Recommendation**: exempt non-equity instruments from D4b (ticker-pattern
filter or an instrument-type flag on `securities`, which currently has no
board/type populated for these auto-ingested tickers).

### 3. Genuine off-market crosses — 6 warns, 4 equity tickers

All printed verbatim in the source PDFs; large negotiated/cross trades at
prices far from the on-market close:

| ticker | date | close | volume | value | implied VWAP |
|---|---|---|---|---|---|
| INTENEGINS | 2022-07-27 | 0.38 | 637,105,004 | 1,019,367,708.80 | 1.60 |
| INTENEGINS | 2022-09-13 | 0.38 | 12,768,257 | 20,429,211.20 | 1.60 |
| MERVALUE | 2024-02-20 | 2,000.00 | 67 | 25,464.26 | 380 (PDF LOW 301.02, HIGH 2,000) |
| ETRANZACT | 2025-12-03 | 14.00 | 1,847,592,419 | 5,547,972,227.55 | 3.00 |
| ETRANZACT | 2026-03-18 | 19.60 | 5,170,555,952 | 24,289,757,348.45 | 4.70 |
| PREMPAINTS | 2026-06-08 | 33.75 | 61,037,441 | 135,263,148.10 | 2.22 |

These are real prints (e.g. both INTENEGINS blocks cross at exactly 1.60 —
a negotiated deal price). Data is correct; the warn is doing its job of
flagging that VWAP != close for these rows. No action needed beyond
awareness that `value_traded/volume` is not an on-market VWAP proxy on
block-trade days.
