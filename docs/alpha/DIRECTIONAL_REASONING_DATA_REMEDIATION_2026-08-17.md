# Directional Reasoning — Data Remediation (Period Metadata + VERITASKAP Currency)

*2026-08-17. Executes the two data repairs authorized in
`DIRECTIONAL_REASONING_DATA_READINESS_2026-08-17.md` §10 (1)–(2) — nothing else. New code:
`scripts/fre/remediate_period_currency_2026-08-17.py` (one-off, disclosed, dry-run-by-default). No
schema change. Only `extracted_facts.period_start`/`.period_end`/`.period_type` (17 rows) and
`extracted_facts.currency` (6 rows) were written. No V3, no expectations dataset, no new LLM calls, no
H-011/Alpha Engine change.*

---

## 1. Pre-remediation baseline (Phase 0)

| Check | Result |
|---|---|
| git HEAD | `c541e14` (unchanged throughout) |
| Protected Alpha Engine files | Zero diff, confirmed before and after |
| `REASONING_WEIGHT` | `0.0`, confirmed before and after |
| Production backup | `data/backups/ngx_backup_2026-08-17_pre_remediation.sqlite` (154MB), taken before any write; row counts verified identical to production at backup time (`extracted_facts`=495, `financial_reasoning_conclusions`=403, `investment_implications`=48, `documents`=11,589) |
| Backup/restore path verified | Yes, before proceeding (§4 has the full drill) |
| Affected fact IDs, recorded exactly | Period repairs: `439,440,441,453,454,442,443,451,452,446,447,448,449,456,458,459,460` (17 facts, 8 tickers). Currency repairs: `427,428,429,430,431,432` (6 VERITASKAP balance-sheet facts) |
| `extracted_facts` | 495 rows |
| `financial_reasoning_conclusions` | 403 rows |
| `investment_implications` | 48 rows |
| H-011 output | Unchanged from `docs/fre_runs/engine_status_2026-08-17.txt` — not re-run this pass, nothing touched it |

---

## 2. Exact facts repaired, with evidence (Phases 1–2)

All 17 period-repair facts come from `documents.doc_type='news_article'` filings. Every period was taken
**verbatim from the fact's own `description` field** — text already written at extraction time from the
article, not inferred from `filing_date` and not borrowed from any other filing.

| fact_id | ticker | fact_type | period_start | period_end | period_type | evidence (from the fact's own description) |
|---|---|---|---|---|---|---|
| 439 | CAVERTON | revenue | 2024-01-01 | 2024-12-31 | FY | "...for the year ended 31st December 2024..." |
| 440 | CAVERTON | revenue | 2026-01-01 | 2026-06-30 | H1 | "...revenue of ₦14.68 billion for H1 2026..." |
| 441 | CAVERTON | net_profit | 2026-01-01 | 2026-06-30 | H1 | "...net loss of ₦8.69 billion for H1 2026..." |
| 453 | CILEASING | revenue | 2026-01-01 | 2026-03-31 | Q1 | "...gross earnings of ₦12.78 billion in Q1 2026..." |
| 454 | CILEASING | net_profit | 2026-01-01 | 2026-03-31 | Q1 | "...post-tax profit of ₦500.41 million in Q1 2026..." |
| 442 | CUTIX | revenue | 2025-05-01 | 2026-04-30 | **None** (see below) | "...for the full year ended April 30, 2026..." |
| 443 | CUTIX | net_profit | 2025-05-01 | 2026-04-30 | **None** (see below) | same |
| 451 | MCNICHOLS | revenue | 2025-01-01 | 2025-12-31 | FY | "...reported 2025 revenue of ₦6.21 billion..." |
| 452 | MCNICHOLS | net_profit | 2025-01-01 | 2025-12-31 | FY | "...profit after tax of ₦346 million for 2025..." |
| 446 | NCR | revenue | 2025-01-01 | 2025-12-31 | FY | "...generated ₦3.081 billion in revenue for 2025..." |
| 447 | NCR | net_profit | 2025-01-01 | 2025-12-31 | FY | "...profit after tax of ₦196 million in 2025..." |
| 448 | PRESTIGE | revenue | 2026-01-01 | 2026-06-30 | H1 | "...insurance revenue of ₦12.56 billion for H1 2026..." |
| 449 | PRESTIGE | net_profit | 2026-01-01 | 2026-06-30 | H1 | "...profit after tax of ₦1.05 billion for H1 2026..." |
| 456 | REDSTAREX | revenue | 2025-04-01 | 2025-06-30 | Q2 | "...Q2 2025 turnover of ₦5.8 billion..." |
| 458 | REDSTAREX | net_profit | 2025-04-01 | 2025-06-30 | Q2 | "...doubled its Q2 2025 net profit..." |
| 459 | VERITASKAP | revenue | 2026-01-01 | 2026-03-31 | Q1 | "...Q1 2026 insurance revenue of ₦5.3 billion..." |
| 460 | VERITASKAP | net_profit | 2026-01-01 | 2026-03-31 | Q1 | "...Q1 2026 post-tax profit of ₦1.5 billion..." |

**CUTIX, disclosed not hidden**: its own evidence explicitly states a fiscal year ending **April 30**,
not December 31 — a genuine non-calendar NGX fiscal year. `period_start`/`period_end` were still set
from this explicit evidence (2025-05-01 → 2026-04-30). `period_type` was derived by calling the
platform's own **existing, unmodified** `period_normalization.classify_period_type()` — which correctly
returns `None` for this span (it only recognizes calendar-aligned Q1–Q4/H1/H2/9M/FY shapes, per its own
documented design). Per Phase 1's explicit instruction not to use judgment where deterministic evidence
already establishes the period, `period_type` was left `None` rather than hand-labeling it `"FY"` myself
— that would have silently overridden the platform's own classifier's real answer.

VERITASKAP's 6 currency repairs, all identical evidence pattern:

| fact_id | fact_type | period | evidence |
|---|---|---|---|
| 427 | assets | FY2020 | `description`: "...(table N'000 x1000)" |
| 428 | liabilities | FY2020 | same |
| 429 | equity | FY2020 | same, plus "Cross-checked: 14,221,929-4,717,955=9,503,974, matches exactly" (accounting identity holds) |
| 430 | assets | FY2019 (comparative) | "...(comparative column, N'000 x1000)..." |
| 431 | liabilities | FY2019 (comparative) | same |
| 432 | equity | FY2019 (comparative) | same |

Every one of these facts' own `description` (written at extraction time from the source table) states
the table's unit label as **"N'000"** — the Naira thousands convention used identically across every
other NGN-denominated fact on this platform. This is the source explicitly establishing the currency,
not an inference from VERITASKAP being a Nigerian-listed company — per Phase 2's explicit instruction,
no fact was set to NGN on nationality/ticker grounds alone. No `CURRENCY_UNRESOLVED` cases arose — all 6
had this explicit textual evidence.

---

## 3. Validation results (Phase 3)

All run against the live, now-repaired production database:

| Check | Result |
|---|---|
| `extracted_facts` row count | 495 — unchanged (no rows created or deleted) |
| Duplicate `fact_id`s | None |
| Repaired facts' `numeric_value`/`description`/`evidence_id` | Unchanged — spot-checked directly, e.g. fact 439's `numeric_value=40,100,000,000.0` and full description text byte-identical to pre-repair |
| PIT validity | `period_end` never later than the source document's `filing_date`, checked for all 17 repaired facts — zero violations |
| `check_db_safety.py` | PASS |
| `scripts/fre/test_numeric_consistency.py` | 12/12 PASS |
| `scripts/fre/test_data_quality_monitoring.py` | 12/12 PASS |
| Existing `data_quality_monitoring.py` real checks (`check_duplicate_facts`, `check_conflicting_facts`, `check_pit_violations`, `check_missing_periods`) run live against production | Zero alerts touch any of the 23 repaired facts. `check_missing_periods` correctly no longer flags any of the 17 period-repaired facts (it still flags 125 other, out-of-scope rows platform-wide, unaffected by this pass) |
| Full FRE regression | `test_directional_reasoning_v2.py` 23/23, `test_reaction_check.py` 12/16, `test_valuation_engine.py` 79/81, `test_company_memory.py` 16/16, `test_reasoning_pipeline.py` ALL PASS — the 12/16 and 79/81 are the **same pre-existing, disclosed staleness** from the prior two reports (stale hardcoded row-counts predating recent data growth), not new failures caused by this repair |

---

## 4. Restore-test results (Phase 4)

1. Backup exists: `data/backups/ngx_backup_2026-08-17_pre_remediation.sqlite`, confirmed present and
   opens cleanly.
2. Restore drill performed: copied the backup to a scratch path and opened it independently.
   `PRAGMA integrity_check` = `ok`.
3. Confirmed the **restored (pre-repair) copy** shows the *original* NULL state for the repaired facts
   (e.g. fact 439: `period_start=None, period_end=None`), while **production** correctly shows the
   repaired state (`2024-01-01, 2024-12-31, FY`) — proving the backup is a faithful, independently
   restorable pre-repair snapshot, and that production remains fully recoverable to that exact state at
   any time.
4. Confirmed unaffected facts (spot-checked fact_ids 1, 100, 200 — outside the 23 repaired) are
   byte-identical between the backup and current production.

Production remains recoverable.

---

## 5. Post-remediation coverage & before/after comparison (Phase 5)

| metric | before | after | changed? |
|---|---|---|---|
| Period-metadata coverage (17 targeted facts) | 0/17 populated | **17/17** `period_start`/`period_end` populated; **15/17** resolve to a real `period_type` (CUTIX's 2 facts correctly left `None` — non-calendar FYE, §2) | ✅ improved |
| Currency coverage (6 targeted VERITASKAP facts) | 0/6 `NGN` | **6/6** `NGN` | ✅ improved |
| Market-cap coverage (H-011 sleeve) | 10/10 | 10/10 | unchanged (already complete before this pass) |
| Dividend-yield coverage (H-011 sleeve) | 2/10 (CILEASING, MCNICHOLS) | 2/10 | unchanged — no dividend facts were touched |
| **P/E coverage (H-011 sleeve, full ratio computable)** | **0/10** (LASACO had its own EPS computable but the ratio itself failed on peer sparsity) | **2/10 — NCR (29.86x), MCNICHOLS (25.42x)**, both genuinely new, real, computed ratios | ✅ **improved, verified** |
| P/B coverage (H-011 sleeve) | 0/10 | 0/10 (still) — **but VERITASKAP's own BVPS now computes (₦0.6854/share) for the first time**, blocked one step later by the same insurance-peer-sparsity issue LASACO already had, not by currency anymore | ✅ partially improved, disclosed precisely |
| EV/EBITDA coverage | 0/10, permanent (no debt/cash fact_type exists) | 0/10 | unchanged — out of this pass's scope |
| Implication-generation coverage | 48/321 eligible facts (~15%) | 48/321 (~15%) | unchanged — not touched this pass |
| Multi-fact filing coverage | 50 documents | 50 documents | unchanged |
| Genuine contradiction count (same-filing) | 1 (VERITASKAP) | 1 | unchanged — no new implications were generated |
| Genuine contradiction count (flag-based, PIT) | 6 fired / 31 insufficient-data / 37 checked | 6 fired / 31 insufficient-data / 37 checked | **unchanged** — see note below |
| Shadow-event count | 8 unique ticker-events | 8 | unchanged — realized returns/directions are untouched by a metadata fix |

**Why the flag-based conflict count didn't move**: `financial_health_flags.py`'s rules read from
`financial_reasoning_conclusions` (pre-computed trend/ratio rows), not from `extracted_facts` directly.
This pass fixed the underlying facts but **did not re-run** `financial_ratios.py`/`trend_classification.py`
to regenerate conclusions from them — that would be a third action beyond the two explicitly authorized
here, and is correctly out of scope for this task. This is the direct, mechanical reason §6's identified
next bottleneck is what it is.

**No alpha claim is made from any of the above.** Two more tickers having a computable P/E, or one
ticker having a computable BVPS, is a data-quality fact, not a predictive-value claim — nothing in this
pass touched `reaction_check()`'s realized outcomes, the shadow dataset, or `REASONING_WEIGHT`.

---

## 6. Remaining bottleneck (Phase 6 — identification only, not solved here)

**Result: B — implication-generation (and its downstream conclusion-generation) coverage is now the
binding blocker**, not period/currency data quality.

Reasoning: this pass fixed real, disclosed, fixable data-quality gaps and produced measurable,
verified valuation-coverage improvement (§5) — option A's "period/currency remediation materially
improves reasoning readiness" is genuinely true, but only in a narrow, mechanical sense (2 more
tickers' P/E, 1 ticker's BVPS). It did **not** move the two numbers that actually gate whether the
directional-reasoning question can be fairly tested: the contradiction sample (still 7, still far
below the 25-case minimum) and the shadow-event count (still 8). Both of those are gated by
implication-generation coverage (still 15%) and conclusion-generation coverage (still the same
31-of-37-insufficient split found in the prior audit) — neither of which this pass touched, by design.

EV/EBITDA (C) and expectations (D) remain real, named, unaddressed gaps, but neither is the
**binding** one — even if both were magically solved tomorrow, the contradiction sample would still be
capped by how few facts have ever had an implication generated from them. Coverage, not a missing data
*type*, is what's constraining the next real test.

---

## 7. Should the next task address implication-generation coverage?

**Yes — this is the identified next bottleneck, per Phase 6's own instruction to identify but not
solve it here.** Any future authorization to close it should be scoped narrowly and explicitly
(how many of the 50 known multi-fact documents to run, what "coverage completion" means operationally,
whether conclusion-generation is in scope alongside implication-generation) — none of that scoping is
decided or implied by this document.

---

## 8. Explicit confirmations

- **Alpha Engine**: zero diff on `alpha_engine.py`, `engine_full.py`, `runner.py`, `registry.py`,
  confirmed via `git diff --stat` before and after this pass.
- **H-011**: not run, not touched, not referenced by any write in this pass.
- **`REASONING_WEIGHT`**: `0.0`, confirmed before and after — unchanged.
- **No alpha claim was made.** This document reports data-quality repairs and their measured effect on
  *coverage* metrics only. No predictive-value, hit-rate, or performance claim is made anywhere in this
  report.

**Stopping here, as instructed** — no automatic continuation into implication-generation coverage work.
