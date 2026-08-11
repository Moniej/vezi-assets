# FRE-7A: Economic Peer Taxonomy Redesign — Report

**Date**: 2026-08-09
**Stage type**: Diagnostic/remediation (not a new valuation experiment).
**Trigger**: FRE-7's own pilot gate failed — 2/7 (29%) triangulated ranges bracketed
the reference market price, against a majority-required criterion
(`docs/fre_runs/fre7_valuation_activation_report.md` §5). The diagnosed root cause
named there: the only peer-grouping axis, `classify_company_type()`'s `company_type`,
is too coarse (19 of 26 real tickers collapse into one `"general"` bucket spanning
industrial goods, consumer goods, oil & gas, ICT, and conglomerates).

**Bottom line: the frozen, independently-built taxonomy does NOT pass the frozen
FRE-7 gate either — 0/1 computed pilot cases bracket (the other 5 pe cases correctly
report an explicit `DATA_GAP` under finer-grained peer requirements). Per the
governance rule, this report STOPS here. No automatic advance to an FRE-7 activation
review. The diagnosed remaining problem is a compound of insufficient peer data and
accounting-data-coverage breadth, NOT the coarseness of the taxonomy itself, NOT the
valuation formulas, and NOT the activation criterion.**

---

## 1. Current-taxonomy diagnosis

`classify_company_type()` (`src/ngxrot/fre/valuation_engine.py`, unmodified by this
stage) resolves every ticker through a 3-tier precedence: an owner-override config
(empty), `sector_company_type_mapping.derive_company_type_for_ticker()` (a
sector_ngx → 6-value lookup: `bank`/`insurance`/`holding_company`/`growth_company`/
`turnaround_company`/`general`), then `"general"` as the final fallback.
`configs/sector_company_type_mapping.toml`'s own `sector` table maps only
`FINANCIAL SERVICES` → conditionally `bank`/`insurance` (via a `sub_industry` check)
and `CONGLOMERATES` → `holding_company` — **every other NGX sector_ngx value
(`CONSUMER GOODS`, `INDUSTRIAL GOODS`, `OIL AND GAS`, `ICT`, `SERVICES`, `UTILITIES`,
`AGRICULTURE`, `NATURAL RESOURCES`, `CONSTRUCTION/REAL ESTATE`, `HEALTHCARE`,
`INVESTMENT`) falls through to `"general"`.** This was a deliberate, disclosed design
choice for `company_type` (a *valuation-method-eligibility* taxonomy — which methods
apply to a bank vs. an insurer vs. a holding company), never intended as a
peer-comparability taxonomy. `_peer_tickers()` (`valuation_engine.py`) then reused it
for that second purpose anyway, because no finer-grained alternative existed —
exactly the gap this stage closes.

Inspected before building anything new: `valuation_engine.py` (the adapters and their
existing peer logic), `extracted_facts`/`documents` (financial fact tables),
`securities`/`sector_ngx_provenance` (company metadata — confirmed the *only*
first-party structural data available: no business-description text, no filing-text
extraction, no revenue-mix data exists anywhere on this platform),
`pit_financial_memory.py` (the PIT-gating pattern this stage's own PIT safeguard
mirrors), and every existing FRE test script (to confirm none assert on
`company_type`'s current coarseness as a feature to be preserved for peer purposes —
none do; the coarseness was never load-bearing for anything other than method
eligibility).

## 2. New taxonomy

Two levels plus a `business_model` tag, per ticker:

- **Level 1** (broad economic sector): `Financials`, `Consumer`, `Industrials`,
  `Energy`, `ICT/Telecom`, `Healthcare`, `Real Estate`, `Utilities`, `Agriculture`,
  `Natural Resources`, `Other`. Extended beyond the illustrative 9-category list in
  the FRE-7A brief because the real NGX universe contains `AGRICULTURE` and
  `NATURAL RESOURCES` sectors whose economics (yield/weather risk, commodity-price
  extraction risk) do not fit `Consumer` or `Industrials` without blurring a real
  distinction.
- **Level 2** (subsector): 34 distinct values, built directly from NGX's own
  `sub_industry` label wherever it maps unambiguously to one; consolidated only where
  multiple NGX sub_industries are functionally the same asset-light service line
  (`Support and Logistics` + `Courier/Freight/Delivery` + `Road Transportation` +
  `Transport-Related Services` → one `Transportation & Logistics Services` bucket,
  disclosed and justified in the config's own `notes` field, since keeping them apart
  would produce four 1–2-constituent buckets with no genuine economic distinction to
  justify the fragmentation).
- **`business_model`**: a short descriptive tag per Level 2 bucket (e.g.
  `financial_intermediation`, `insurance_underwriting`,
  `consumer_staples_manufacturing`, `industrial_services`, `integrated_energy`,
  `regulated_utility`, `diversified_holding`).

Two Level 2 buckets are explicitly disclosed as **too heterogeneous to trust as a
same-subsector peer match** even though they resolve cleanly:
`Other Financial Services` (NGX's own catch-all — known to span share registrars,
asset managers, and investment banks) and `Specialty (Unclassified)` /
`Diversified Conglomerate` (no single business model by construction). These fall
straight through to the sector-level tier or `NOT_READY`, never treated as a clean
subsector comparable set.

## 3. Data sources used

- `securities.sector_ngx` + `sector_ngx_provenance.sub_industry` — NGX's own official
  Daily Official List classification (FSI Phase 23/26), the *only* first-party
  structural reference data on this platform. Single retrieval snapshot,
  `retrieval_date = 2026-08-02`, for all 136 classified tickers (out of 320 total).
- No business description, filing-text extraction, revenue-mix, or index-membership
  data exists anywhere on this platform. Where NGX's own sub_industry is a genuine
  catch-all (`Other Financial Institutions`, `Specialty`), this is disclosed via a
  `confidence: "low"` field and a `notes` field explaining exactly why — never
  silently resolved with outside/general knowledge not present in the platform's own
  data. This is also why `MCNICHOLS` and `UBN` (both real, fact-bearing tickers with
  no `sector_ngx` on record) remain classified `UNKNOWN` here, even though their
  economic sector is knowable from public information — using that outside knowledge
  would have introduced an unauditable evidence source this report could not trace
  back to a real row in this platform's own database.

## 4. Classification methodology

`src/ngxrot/fre/economic_peer_taxonomy.py`, `classify_ticker(con, ticker, as_of_date)`:
a pure `(sector_ngx, sub_industry) → (level1, level2, business_model, confidence)`
lookup against the static `configs/economic_peer_taxonomy.toml` table (47 rows — one
per real `(sector_ngx, sub_industry)` pair observed across all 136 classified
tickers, confirmed by direct query to have zero gaps). Returns `classified=False`
(every taxonomy field `None`) whenever: no `sector_ngx` is on record, no
`sub_industry` provenance row exists, the pair is somehow absent from the config, or
the reference data's own `retrieval_date` is after the requested `as_of_date` (PIT
gate — see §8). Deterministic and ticker-agnostic: the mapping is a pure function of
the `(sector_ngx, sub_industry)` pair, never a ticker-specific carve-out — verified
directly by test (§9).

**Governance note (hard rule 6)**: this taxonomy was built and frozen using only the
47 real `(sector_ngx, sub_industry)` pairs and their plain economic meaning — never by
cross-referencing which of the original 7 pilot tickers did or didn't bracket their
market price. No ticker-specific rule exists anywhere in `economic_peer_taxonomy.toml`
or `economic_peer_taxonomy.py`; every classification decision applies uniformly to
every ticker sharing that sector/sub-industry pair, auditable independent of any
valuation outcome.

## 5. Full company mapping (26 real fact-bearing tickers, as of 2026-08-09)

| Ticker | Level 1 | Level 2 (subsector) | Business model | Confidence | Peer tier | Candidate peers |
|---|---|---|---|---|---|---|
| AFRIPRUD | Financials | Other Financial Services | financial_intermediation | low | sector | 7 |
| AIRTELAFRI | ICT/Telecom | Telecom Services | telecom_network_services | high | sector | 2 |
| BUAFOODS | Consumer | Food Products | consumer_staples_manufacturing | high | sector | 2 |
| CAP | Industrials | Building Materials | industrial_manufacturing | high | sector | 5 |
| CAVERTON | Industrials | Transportation & Logistics Services | industrial_services | medium | **subsector** | 2 |
| CILEASING | Industrials | Transportation & Logistics Services | industrial_services | medium | **subsector** | 2 |
| CUTIX | Industrials | Electrical & Electronic Products | industrial_manufacturing | high | sector | 5 |
| DANGCEM | Industrials | Building Materials | industrial_manufacturing | high | sector | 5 |
| DEAPCAP | Financials | Other Financial Services | financial_intermediation | low | sector | 7 |
| GEREGU | Utilities | Power Generation | regulated_utility | high | **none** | 0 |
| LASACO | Financials | Insurance | insurance_underwriting | high | **subsector** | 4 |
| MCNICHOLS | **UNKNOWN** | — | — | — | none | 0 |
| MTNN | ICT/Telecom | Telecom Services | telecom_network_services | high | sector | 2 |
| NASCON | Consumer | Food Products | consumer_staples_manufacturing | high | sector | 2 |
| NCR | ICT/Telecom | IT Services | it_services | high | sector | 2 |
| NEM | Financials | Insurance | insurance_underwriting | high | **subsector** | 4 |
| NESTLE | Consumer | Food Products - Diversified | consumer_staples_manufacturing | high | sector | 2 |
| OANDO | Energy | Integrated Oil & Gas | integrated_energy | high | **none** | 0 |
| PRESTIGE | Financials | Insurance | insurance_underwriting | high | **subsector** | 4 |
| REDSTAREX | Industrials | Transportation & Logistics Services | industrial_services | medium | **subsector** | 2 |
| TRANSCORP | Other | Diversified Conglomerate | diversified_holding | high | **none** | 0 |
| UACN | Other | Diversified Conglomerate | diversified_holding | high | **none** | 0 |
| UBN | **UNKNOWN** | — | — | — | none | 0 |
| UCAP | Financials | Other Financial Services | financial_intermediation | low | sector | 7 |
| UNIVINSURE | Financials | Insurance | insurance_underwriting | high | **subsector** | 4 |
| VERITASKAP | Financials | Insurance | insurance_underwriting | high | **subsector** | 4 |

`Other Financial Services` and `Diversified Conglomerate` rows show a "sector" tier
even where a subsector group technically exists, because both Level 2 buckets are
flagged unreliable for peer-matching (§2) — the tier column always reflects the tier
actually *used*, not merely available.

## 6. Unknown/unclassified companies

`MCNICHOLS` and `UBN` — the two real, fact-bearing tickers with no `sector_ngx` row
in `securities` at all. Per this stage's own evidence-only discipline (§3), they stay
`UNKNOWN` rather than being classified from outside knowledge. This is a real,
disclosed platform-data gap (FSI Phase 23's sector-ngx sourcing did not cover these
two names), not a taxonomy design defect — a future data-acquisition pass to add
their real `sector_ngx`/`sub_industry` from NGX's own Daily Official List would close
this gap without touching the classification logic itself.

## 7. Peer-selection rules

Deterministic hierarchy, `economic_peer_taxonomy.select_peers()`:

1. **Same Level 2 subsector** (excluding self, excluding any subsector flagged
   unreliable-for-matching) — used if it reaches `min_peers` (default 2).
2. **Same Level 1 broad sector** — used only as a disclosed fallback when tier 1
   doesn't reach `min_peers`, or when the subject's own subsector is flagged
   unreliable.
3. **`NOT_READY`** (`tier="none"`) — if neither tier reaches `min_peers`. This module
   never forces a ticker into an economically unsuitable peer group merely because a
   valuation needs one (per the explicit instruction) — confirmed for real: `OANDO`
   (the platform's only real Energy-sector fact-bearing ticker), `GEREGU` (only
   Utilities), and `TRANSCORP`/`UACN` (Other/conglomerate) all correctly report zero
   peers rather than being folded into an unrelated bucket.

This function returns *candidates* only — it does not decide whether a candidate's
own EPS/BVPS is actually computable (currency-clean, positive, PIT-knowable). That
filtering still happens exactly where it always did, downstream in the pilot rerun
(§10) — mirroring `PEAdapter`/`PBAdapter`'s own original logic precisely, unmodified.

## 8. PIT safeguards

`sector_ngx_provenance.retrieval_date` (a real column, single value `2026-08-02`
across all 136 rows) is treated as the date NGX's own Daily Official List snapshot
became knowable — mirroring `pit_financial_memory.py`'s filing-date gate, applied
here to structural/reference data instead of financial facts. `classify_ticker()`
returns `classified=False, pit_valid=False` for any `as_of_date` before that
retrieval date (verified by direct test: CAP classifies as `False` on `2026-08-01`,
`True` on `2026-08-02` and after — the exact same ticker, only the `as_of_date`
differs). No classification is ever back-dated to before it was actually retrieved,
and no future information is used relative to any valuation date this taxonomy is
queried against.

## 9. Tests and results

`scripts/fre/test_economic_peer_taxonomy.py` — **37/37 checks passed**, covering:
architectural isolation (neither `economic_peer_taxonomy.py` nor `valuation_engine.py`
imports the other — verified via actual import statements, not docstring mentions),
deterministic classification (repeat calls identical; every one of the 47 real
`(sector_ngx, sub_industry)` pairs covered with zero gaps), `UNKNOWN`-stays-`UNKNOWN`
for `MCNICHOLS`/`UBN`/a nonexistent ticker, PIT correctness (the CAP before/on/after
retrieval-date check above), classification consistency (identical `(sector_ngx,
sub_industry)` pairs always yield an identical taxonomy result, checked across all 26
real tickers), sector/subsector mapping spot-checks against 9 real tickers, peer
eligibility hierarchy (subsector-tier vs. sector-fallback vs. `none`, including the
`AFRIPRUD`/`Other Financial Services` unreliable-subsector fallback case),
insufficient-peer/exclusion handling (`OANDO`/`GEREGU`/`TRANSCORP`/`UACN` all
correctly report `tier='none'`), a `min_peers` boundary check, and a direct
**regression** against `valuation_engine.py`'s own original, unmodified FRE-7 output
(CAP's `pe`/`dcf` point estimates and CAP's original peer set are byte-identical to
the FRE-7 report's own recorded numbers).

Also re-run as a final regression check: `test_valuation_engine.py` (78/78, unchanged),
`test_pit_financial_memory.py` (15/15, unchanged), `test_sector_company_type_mapping.py`
(18/18, unchanged). Zero database writes occurred across any of this stage's test runs
(`documents` row count verified unchanged before/after in every script).

## 10. Original FRE-7 result: 2/7 (29%)

Per `docs/fre_runs/fre7_valuation_activation_report.md` §5 — reproduced here as the
frozen baseline this rerun compares against, unmodified:

| Ticker | Method | Point | Range | Reference | Brackets? |
|---|---|---|---|---|---|
| UCAP | pe | 24.58 | [10.61, 86.51] | 18.00 | **Yes** |
| NASCON | pe | 142.82 | [84.20, 686.46] | 195.00 | **Yes** |
| BUAFOODS | pe | 175.83 | [103.66, 240.07] | 845.10 | No |
| CAP | pe | 15.87 | [9.35, 21.66] | 115.45 | No |
| OANDO | pe | 82.80 | [60.64, 291.46] | 35.75 | No |
| UBN | pe | 21.16 | [15.50, 74.48] | 6.65 | No |
| CAP | dcf | 8.33 | [7.37, 9.57] | 115.45 | No |

## 11. FRE-7A rerun result

Run exactly once (`scripts/fre/fre7a_rerun_pilot.py`), no parameter retuned after
seeing the output:

| Ticker | Method | FRE-7A peer tier | Candidates | Usable peers | Result |
|---|---|---|---|---|---|
| UCAP | pe | sector (Financials) | 7 | **0** | `DATA_GAP` |
| BUAFOODS | pe | sector (Consumer) | 2 | 1 | `DATA_GAP` |
| NASCON | pe | sector (Consumer) | 2 | 1 | `DATA_GAP` |
| CAP | pe | sector (Industrials) | 5 | **0** | `DATA_GAP` |
| OANDO | pe | none (Energy has 0 candidates) | 0 | — | `DATA_GAP` |
| UBN | pe | none (subject unclassified) | — | — | `DATA_GAP` |
| CAP | dcf | n/a (no peer dependency) | — | — | point=8.33, range=[7.37, 9.57] (**identical to original — unaffected by taxonomy**) |

**5 of the original 6 `pe` cases now report an explicit `DATA_GAP`** — not because
their peer *groups* got smaller in a trivial sense, but because the finer-grained
peer candidates (real companies in the same subsector/sector) mostly lack a
currency-clean, positive, FY `net_profit` fact at all. This was checked directly, not
assumed: `AFRIPRUD`/`DEAPCAP`/`LASACO`/`NEM`/`PRESTIGE`/`UNIVINSURE`/`VERITASKAP` (the
7 candidate Financials peers for UCAP) all return `None` from the exact same,
unmodified `_eps()` extraction CAP/UCAP itself uses — none has a usable net_profit
fact, only some have equity facts (which is why they appear in `list_tickers()` at
all). The **1 case that remains computable** (CAP's `dcf`, which has no peer
dependency at all) is unaffected by this stage by construction and reproduces the
original result exactly.

## 12. Per-ticker valuation ranges

See §11's table — every `pe` case that would have produced a range under FRE-7A
instead produced an explicit `DATA_GAP` (no fabricated range from an insufficient
peer set). CAP's `dcf` range is unchanged: `[7.37, 9.57]`.

## 13. Bracketing result

**0/1 computed cases bracket** the reference market price (CAP's `dcf`, unchanged
from the original, does not bracket — same as before). The other 6 original pilot
cases are no longer computable at all under the finer-grained taxonomy, so they
contribute neither a bracket nor a miss — they contribute an honest absence of a
number.

**Gate requires a majority (>50%) of pilot cases to bracket. 0/1 = 0%. GATE FAILS.**

## 14. Comparison with the original result

| | Original FRE-7 (`company_type`) | FRE-7A (economic taxonomy) |
|---|---|---|
| Computable pilot cases | 7/7 | 1/7 |
| Cases bracketing reference price | 2/7 (29%) | 0/1 (0%) |
| Gate | FAILS | FAILS |

The finer-grained taxonomy did not fix the bracketing problem — it could not even be
tested on 6 of the 7 original cases, because requiring genuine subsector/sector
comparability (rather than the coarse `"general"` bucket) exposed how thin the
underlying `net_profit`/EPS extraction actually is *within* any single economically
coherent peer group. The original taxonomy's coarseness had been *masking* this
data-coverage gap by pooling unrelated companies together, which happened to produce
enough raw peer count to clear the `min_peers=2` bar — with numbers that, per §10,
still failed to bracket reality in 5 of 7 cases anyway.

## 15. Remaining weaknesses

Per the FRE-7A brief's own diagnostic categories:

- **Insufficient peer data — confirmed, primary cause.** Within real, economically
  coherent subsector/sector buckets, most candidate peers lack a usable `net_profit`
  fact. This is not a classification problem (the buckets are correct) — it is a
  *extraction-breadth* problem: FSI's `net_profit` coverage is broad enough across
  *unrelated* companies to have supported the old coarse bucketing, but not broad
  enough *within* any single narrow, real economic peer group to support genuine
  comparables analysis.
- **Accounting-data limitations — confirmed, contributing cause.** Related to the
  above: several real Financials-sector tickers (AFRIPRUD, DEAPCAP, LASACO, NEM,
  PRESTIGE, UNIVINSURE, VERITASKAP) have *some* financial-statement facts (enough to
  appear in `list_tickers()`) but not the specific `net_profit` line item needed for
  a P/E comparable — a gap in extraction depth, not breadth.
- **Company-classification limitations — not a significant cause here.** The
  taxonomy itself classified 24/26 real tickers with `medium`+ confidence and
  produced internally consistent, auditable, non-ticker-specific groupings (§9's
  regression and consistency tests both pass). The two `UNKNOWN`s (MCNICHOLS, UBN)
  are a real data gap (§6), not a taxonomy defect.
- **Valuation-model limitations — ruled out by construction.** The DCF/P-E/P-B
  formulas, WACC/terminal-growth handling, and the activation criterion itself are
  byte-for-byte unchanged (verified directly, §9's regression test) — none of them
  caused this outcome.
- **Unsuitable activation criterion — not diagnosed as the cause.** The bracket-vs-
  market-price criterion is a legitimate sanity check; the problem here is that too
  few cases were computable to evaluate it meaningfully at all, not that the
  criterion itself is wrong.
- **A structural ceiling worth naming explicitly**: even with perfect data coverage,
  several real NGX sectors on this platform have only 1–2 fact-bearing constituents
  (Energy: only OANDO; Utilities: only GEREGU; ICT sub-buckets: 2 each). A
  peer-comparables method fundamentally cannot triangulate a single-constituent
  sector — no taxonomy redesign changes that; it requires either a broader universe
  of extracted facts (more tickers per sector) or a non-comparables method for those
  names.

## 16. Whether FRE-7 activation should proceed

**No. STOP.** The frozen, independently-built economic taxonomy does not pass the
frozen FRE-7 gate (0/1 computed cases bracket; 0% < required majority). Per the
explicit governance instruction, no further taxonomy modification is attempted to
chase a pass, and no automatic advance to an FRE-7 activation review occurs.

The diagnosed path forward, in the order the evidence above supports, requires
separate owner authorization before any further implementation:

1. **Deepen `net_profit` (and `equity`, for P/B) extraction breadth specifically
   within the Financials and Consumer sectors' real subsector peer groups** — this is
   the single highest-leverage fix (§15), independent of any further taxonomy work.
2. Re-run this exact pilot (not a larger one) once that extraction work lands, before
   FRE-7 is considered for activation.
3. Separately and only if the owner wants it: expand the fact-bearing universe within
   thin single-constituent sectors (Energy, Utilities) — comparables cannot work
   there under any taxonomy without more real constituents.

No trading hypothesis was registered. No backtest was run. No financial fact was
fabricated. `valuation_engine.py`'s formulas, WACC/terminal-growth handling, and the
original FRE-7 pilot's own recorded results are all confirmed unmodified (§9).
