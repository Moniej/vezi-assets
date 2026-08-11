# Research OS -- Infrastructure Layer Report

**Date**: 2026-08-10
**Follows**: `docs/fre_runs/ngxpulse_data_foundation_gaps_report.md` (data-
foundation gaps closed, 61/61 tests passing).
**Explicitly out of scope, and none of it was done**: momentum features,
relative-strength features, sector rankings, alpha signals, factor
construction, portfolio construction, strategy discovery, predictive
modelling, alpha backtesting. No PostgreSQL migration, no parallel
database, no second provider abstraction, no second ingestion pipeline,
no backtest-engine rewrite.

---

## 1. What was built

### 1a. Research dataset access (`src/ngxrot/research_dataset.py`, new)

- `get_equity_dataset(con, start, end, tickers=..., universe_as_of=..., min_confidence=, vintage=, sources=)`
  and `get_index_dataset(...)` -- the clean query surface asked for:
  security/universe queries, date-range queries, PIT (`vintage`)
  queries, source/provenance retrieval. Built on two NEW read-only range
  readers added to `db.py` (`equity_prices_range`, `index_levels_range`)
  -- same PIT semantics (latest-capture-wins, `as_of_date <= vintage`)
  as the existing single-`sim_date` readers, just windowed for research
  use rather than a backtest's day-by-day walk.
- When `tickers` is omitted and `universe_as_of` is given, the ticker set
  comes from the **existing** `universe.iru_members()` (rule-based,
  versioned, point-in-time) -- no second universe concept invented.
- Every call returns a `ResearchDataset`: the DataFrame plus a
  `.manifest()` (query params, row count, deterministic content hash,
  code fingerprint, capture timestamp) and `.record_snapshot(reg)` to
  pin it for reproducibility (Section 1c).

### 1b. Data-quality visibility (`src/ngxrot/research_quality.py`, new)

`quality_report(con, tickers, start, end)` composes five checks into one
call: `quality_flags` (from `data_quality_log`), `missing_observations`
(vs. the NGXASI trading calendar), `source_conflicts` (multi-source
disagreement beyond tolerance), `identity_notes` (rename-chain presence,
reusing `instrument_identity.py`), `corporate_action_notes` (real facts
from both `corporate_actions` and `extracted_facts`). No new detection
logic -- this is composition of checks that already existed or were
added in the prior data-foundation-gaps pass, exposed as one callable
surface instead of one-off scripts.

### 1c. Reproducibility / dataset versioning (`schema/registry.sql` +
`research_dataset.py`/`research_experiment.py`)

Two new immutable tables added to the **existing** `data/registry.sqlite`
(no new database):

- `dataset_snapshots` -- pins exact query params, row count, a
  deterministic SHA256 content hash, universe version, and code
  fingerprint for any `ResearchDataset`.
- `research_runs` -- pins a free-text research question, the dataset
  snapshot(s) used, universe version, observation period,
  transformations applied (list, may be empty), analysis method, and
  results -- generic, not alpha-shaped (no `signal`/`portfolio`/`costs`
  columns, unlike the pre-existing `experiments` table).

Both follow the exact immutability discipline `experiments` already
established: insert-only, `UPDATE`/`DELETE` blocked by trigger.
`registry.record_experiment` (the alpha-backtest recorder) was not
touched.

**Real bug found and fixed while building this**: `schema/registry.sql`
had a pre-existing ordering defect -- the `no_experiments_on_frozen`
trigger referenced `hypothesis_experiments` roughly 30 lines before that
table was created. This only ever worked against an already-populated
`registry.sqlite` (table already existed from an earlier version of the
file); building a *fresh* registry database failed outright. Fixed by
moving the table definition earlier in the script (a `CREATE TABLE IF
NOT EXISTS` reorder, a no-op against any existing database -- verified
the real production `registry.sqlite`, with its 330 pre-existing
experiment rows, still opens and queries cleanly after the change).

### 1d. Experiment framework (`src/ngxrot/research_experiment.py`, new)

`ExperimentSpec`/`ExperimentResult` model exactly the shape requested:
`hypothesis -> dataset -> universe -> observation period ->
transformations -> analysis -> results -> reproducibility metadata`.
`record_research_run()`/`load_research_run()` write/read `research_runs`
rows. **Not populated with an alpha hypothesis anywhere.** The one
worked example (in `scripts/test_research_os.py` and Section 8 of the
architecture doc) is deliberately descriptive: "what does the CILEASING
data-quality profile look like for a given window" -- an infrastructure
smoke test, not a trading idea, with `transformations=[]`.

### 1e. Documentation (`docs/RESEARCH_OS_ARCHITECTURE.md`, new)

Covers the full pipeline, each layer's module and responsibility, data
contracts (unchanged, pointed at `contracts.py`), the identity model, the
lineage model, the data-quality-visibility model, the reproducibility
workflow (including how a future researcher actually reproduces a past
result step by step), a worked descriptive example, and an explicit
"what this layer deliberately does NOT do" section.

## 2. Architecture changes

- `db.py`: two new read-only functions (`equity_prices_range`,
  `index_levels_range`). No existing function modified.
- `schema/registry.sql`: two new tables + four new triggers (additive);
  one pre-existing table definition reordered (bug fix, no-op on
  existing databases, verified).
- No changes to `ingest.py`, `contracts.py`, any provider, or the
  backtest engine (`backtest_lite.py`/`backtest_xs.py`/`engine_full.py`
  untouched).

## 3. Tests

`scripts/test_research_os.py`, **19/19 passing**, covering: real-data
dataset queries, deterministic content hashing, IRU-universe resolution,
snapshot recording and immutability (trigger-verified), all five
quality-report sections against real tickers/findings from the prior
pass, and a full descriptive experiment-run record/load round trip with
immutability verified.

**Regression** (prior test suites re-run, unaffected):

| Suite | Result |
|---|---|
| `scripts/test_instrument_identity.py` | 20/20 |
| `scripts/test_lineage.py` | 10/10 |
| `scripts/test_ngxpulse_provider.py` | 31/31 |
| `scripts/test_research_os.py` (new) | 19/19 |
| **Total** | **80/80** |

## 4. Files changed

New:
- `src/ngxrot/research_dataset.py`
- `src/ngxrot/research_quality.py`
- `src/ngxrot/research_experiment.py`
- `scripts/test_research_os.py`
- `docs/RESEARCH_OS_ARCHITECTURE.md`
- `docs/fre_runs/research_os_infrastructure_report.md` (this file)

Modified:
- `src/ngxrot/db.py` (two new functions added, nothing removed/changed)
- `schema/registry.sql` (two new tables/triggers added; one existing
  table definition moved earlier, fixing a real ordering bug)

## 5. Remaining limitations (disclosed, not resolved this pass)

- `instrument_identity.py`'s entity-graph-based rename resolution and
  `universe.py`'s older CSV-based `rename_chain()` are two independent
  mechanisms, not merged.
- `corporate_actions` (quant layer, synthetic-only) and
  `extracted_facts` (FRE layer, has real bonus/rights data) remain
  unsynchronized -- `research_quality.corporate_action_notes` surfaces
  both side by side rather than reconciling them.
- `source_conflicts` and `missing_observations` are cheap, generic
  detectors -- they do not carry the deeper investigation the 2026-08-10
  cross-validation report did for the two specific root causes found
  there (stale-price carryforward, date-attribution drift); they will
  flag those cases again on any window that includes them, which is
  correct behavior, not a new bug.
- No UI/notebook front-end was built -- everything above is a Python
  API. Building an actual interactive notebook environment was not
  requested and would be new infrastructure weight beyond what this pass
  asked for.

## 6. How a future researcher uses this system

1. Decide a universe/ticker set and window; call `get_equity_dataset()`/
   `get_index_dataset()`.
2. Call `research_quality.quality_report()` on the same set/window
   *before* trusting it -- read `quality_flags` and
   `corporate_action_notes` especially, since prices are raw/unadjusted.
3. Call `.record_snapshot(reg)` on the dataset to pin it.
4. Do the actual analysis (still entirely up to the researcher -- this
   layer does not do it).
5. Wrap the question, snapshot id(s), transformations applied, and
   results into an `ExperimentSpec`/`ExperimentResult` and call
   `record_research_run()`. This is optional but is how a result becomes
   independently reproducible later, per Section 7 of the architecture
   doc.
6. Anyone revisiting the result re-runs the same query with the same
   `vintage` and compares `content_hash` before trusting it.

---

## STOP

This closes the requested Research OS infrastructure layer. **No alpha
research was started.** The next phase should only begin after an
explicit decision that the Research OS is ready for actual research.
