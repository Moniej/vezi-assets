# FRE Part 1 — Financial Ontology

*Design only. No code, no schema migration, no config file created. Part of
the Financial Reasoning Engine (FRE) architecture program — see
`docs/fre/00_fre_master_index.md` for scope and standing rules (repository
frozen, no implementation this pass).*

## Objective

Give every reasoning engine (`docs/REASONING_ENGINE_SPECIFICATION.md`'s
Financial/News/Macroeconomic/Industry engines, and this document's own
extensions) a **shared, explicit, versioned causal vocabulary** for how
Nigerian-equity financial concepts relate to each other — so that Step 3/8's
"recursive why" causal chain (`causal_chain_steps`) is built from a
consistent, auditable graph of named mechanisms, not reinvented ad hoc by
each LLM call. This is an ontology of **mechanisms**, not a glossary: every
edge answers "why does A move B," not "what is A."

## Rationale

Today, `causal_chain_steps` stores a free-text chain per fact
(`statement`, `inferred` flag, optional `evidence_id`) with no shared
structure across facts. Two consequences, both real risks the existing
self-critique gate's `unevidenced_inference` and
`ignored_alternative_explanation` questions (§12.1 of the reasoning spec)
were built to catch, but currently catch **only per-instance**, one call at
a time:

1. **No cross-fact consistency.** Two different documents about the same
   causal mechanism (e.g., "MPR hike → bank margins") could each get an
   independently-invented, possibly contradictory causal story from the
   model, with nothing to compare them against.
2. **No mechanical way to say "this mechanism was tested on NGX data and
   rejected."** `docs/FACTOR_REGISTRY.md` already contains hard-won negative
   evidence (H-004 oil lead-lag rejected, H-005 MPC-window effect rejected,
   H-008 low-vol rejected with a *specific regime explanation*) that the
   Macroeconomic Reasoning Engine is already required to cite (architecture
   doc §4.5) — but there is no structured place to attach that citation
   *to the mechanism itself* so every future call finds it automatically
   rather than depending on the model "remembering" to look it up.

An explicit ontology turns "the model asserts a mechanism" into "the model
cites a mechanism from a shared, versioned graph, and the self-critique gate
can mechanically check whether that edge exists, what its evidence status
is, and whether a contradicting NGX-specific finding is on record."

## Design: two edge classes, not one

The single most important structural decision in this ontology, motivated
directly by a failure mode visible in the owner's own example list (Revenue
→ Gross Profit → ... → EPS reads like a causal chain but is actually an
accounting identity):

| Edge class | Meaning | Example | Truth status |
|---|---|---|---|
| **`definitional`** | An accounting identity or ratio decomposition — always true by construction, no economic judgment involved | `Gross Profit = Revenue − COGS`; `EBITDA = EBIT + D&A`; `Assets = Liabilities + Equity` | Deterministic, never disputed, never regime-conditional |
| **`causal`** | An economic mechanism — one quantity moving another through real-world behavior, context- and regime-dependent, can be empirically tested and can be wrong | `Higher MPR → higher bank NIM (asset-sensitive balance sheet)`; `Receivables days↑ → FCF↓ (collection risk/working-capital drag)` | Probabilistic, sign can flip by sector/regime, carries an `evidence_status` |

Conflating these two (treating "Revenue drives EPS" as if it were the same
kind of claim as "an MPR hike drives bank margins") is precisely the kind of
vague causal talk the reasoning spec's Step 3 exists to prevent. Every edge
in this ontology is tagged one or the other; `causal_chain_steps` rows that
cite a `definitional` edge get `inferred=0` treatment (it is not really an
inference, it is arithmetic); rows citing a `causal` edge are always
`inferred=1` and must carry the edge's own `evidence_status` into their
`confidence_rationale`.

## Node taxonomy

Config-driven, mirroring `configs/event_taxonomy.toml`/`fact_taxonomy.toml`
— adding a node is a config change. Six node families:

| Family | Example nodes | Populated from |
|---|---|---|
| `income_statement` | revenue, cogs, gross_profit, opex, operating_profit, ebitda, ebit, interest_expense, tax, net_profit, eps | `extracted_facts` (once a financial-statements dataset exists, §10 of this program's Part 10) |
| `balance_sheet` | cash, receivables, inventory, ppe, total_assets, debt, payables, total_liabilities, equity | same |
| `cash_flow` | cfo, capex, fcf, dividends_paid, buybacks, rights_issue_proceeds, working_capital_change | same |
| `macro` | mpr (monetary policy rate), inflation_yoy, usd_ngx_rate, brent_price, government_policy_event | existing `macro_series`/`events` tables, unchanged |
| `corporate_action` | dividend_declaration, share_buyback, rights_issue, private_placement, bonus_issue, management_change | existing `fact_taxonomy.toml` leaves, reused verbatim, not re-typed |
| `sector_ratio` | bank: `nim`, `car`, `npl_ratio`, `cost_to_income`, `loan_to_deposit`; insurance: `combined_ratio`, `loss_ratio`, `solvency_margin`; general: `gross_margin`, `roe`, `roic` | derived, computed only where the source financial-statements dataset exists |
| `qualitative` | management_quality, corporate_governance_score, competitive_moat, capital_allocation_discipline | Financial Reasoning Engine's own qualitative judgments (§4.5 of the spec) — explicitly the *softest* node family, never given a numeric identity edge, see Risks below |

## Edge taxonomy and worked examples

| Edge type | Class | Worked example | Sector conditioning | Lag bucket (reuses `duration_bucket` vocabulary) |
|---|---|---|---|---|
| `component_of` | definitional | `cogs component_of gross_profit` (via subtraction) | none | immediate |
| `derived_from` | definitional | `eps derived_from (net_profit, shares_outstanding)` | none | immediate |
| `drives_positive` / `drives_negative` | causal | `mpr drives_positive bank.nim` (asset-sensitive) vs. `mpr drives_negative industrial.net_profit` (via interest_expense, for leveraged issuers) | **sector-conditioned — the SAME macro node has opposite-signed edges into different sector overlays; a universal, sector-blind edge is explicitly disallowed for macro→company edges** | `short` to `medium` |
| `offsets` | causal | `usd_ngx_rate(depreciation) offsets oil_gas.revenue_naira(import-cost pass-through)` for downstream fuel/energy names | sector-conditioned | `medium` |
| `proxies_for` | causal, weak | `corporate_governance_score proxies_for capital_allocation_discipline` | none | `structural` |
| `dilutes` | definitional + causal note | `rights_issue dilutes eps` (definitional on share count) but `rights_issue drives_negative short_term.market_reaction` (causal, sentiment-mediated, separate edge) | none | `very_short` (market reaction) / `permanent` (share count) |

**Worked full chain (the owner's explicit Revenue→EPS example, correctly
typed):** `revenue --[definitional: component_of]--> gross_profit
--[definitional]--> operating_profit --[definitional: + non-operating
items]--> ebt --[definitional: - tax]--> net_profit
--[definitional: derived_from]--> eps`. This is the accounting **skeleton**
— it is always true and carries no economic judgment. The *interesting*
reasoning happens on the **causal edges that feed the skeleton's inputs**:
`government_policy(fuel_subsidy_removal) drives_positive oil_gas.revenue`,
`inflation_yoy drives_negative consumer_goods.gross_margin (input-cost
pass-through lag)`, `mpr drives_negative industrial.net_profit (leveraged
balance sheet)` — each with its own `evidence_status`.

## Evidence status — the direct link to `docs/FACTOR_REGISTRY.md`

Every `causal` edge carries:

```toml
[[edge]]
subject = "mpr"
predicate = "drives_negative"
object = "industrial.net_profit"
sector_scope = ["industrial", "consumer_goods"]
mechanism = "Higher MPR raises interest expense on floating/short-tenor NGX corporate debt, compressing net profit with a short lag."
lag_bucket = "short"
evidence_status = "theoretical"          # theoretical | ngx_confirmed | ngx_rejected | ngx_mixed
evidence_ref = null                      # a docs/FACTOR_REGISTRY.md hypothesis ID, once tested
```

`evidence_status = "ngx_rejected"` is a first-class, expected value — not an
error state. Two ontology edges are **pre-populated at `ngx_rejected`** on
day one, directly from the existing factor registry, because the platform
already has the evidence:

- `brent_price drives_positive oil_gas.equity_return (short lag)` —
  `evidence_ref = "H-004"`, rejected (near-miss, p=0.079); mechanism
  disclosed as unconfirmed, not false, per the registry's own honest
  framing.
- `mpr_decision_window drives_volatility ngxbnk.returns` —
  `evidence_ref = "H-005"`, rejected.
- `low_volatility proxies_for defensive_quality` (as a return driver) —
  `evidence_ref = "H-008"`, rejected with the specific regime explanation
  (NGX 2016-2026's violent regime transitions rewarded risk-taking over
  calm-backdrop defensiveness) — this is exactly the kind of nuance a bare
  "rejected" flag would lose; `mechanism` text must carry the regime
  caveat, not just the verdict.

This makes the Macro Reasoning Engine's existing citation requirement
(architecture doc §4.5: "must explicitly cite that rejection history as a
caveat") **mechanically enforceable**: a reasoning call that invokes an
edge with `evidence_status='ngx_rejected'` and does *not* surface that
status in `confidence_rationale` fails a new, addable self-critique check
(a ninth question, or folded into the existing
`ignored_alternative_explanation` question) — same "mechanical check
alongside the model's own report" pattern as every other §12.1 question.

## Alternatives considered

1. **No explicit ontology; rely on each LLM call's own world knowledge.**
   Rejected. Unauditable (can't diff two calls' mechanisms), can't encode
   NGX-specific rejections, can't be checked mechanically by the
   self-critique gate, and drifts silently if the model or prompt changes.
2. **A formal ontology language (OWL/RDF, a graph database).** Rejected as
   over-engineering for this platform's scale and conventions. The platform
   has never needed more than 2-3 hop SQL joins (Knowledge Graph design,
   architecture doc §5) and deliberately avoids new infrastructure
   dependencies (Unsloth/local-only registries in the LIM architecture is
   the same instinct). A TOML config table plus one additive SQLite table
   for the versioned, queryable edge list is consistent with every other
   taxonomy on this platform.
3. **Hardcode mechanisms in Python (e.g., inside `reasoning.py`).**
   Rejected — would make every new mechanism a code change and a redeploy,
   breaking the "adding a taxonomy leaf is a config change" convention this
   platform has used since `event_taxonomy.toml`.
4. **One universal (non-sector-conditioned) macro→company edge set.**
   Rejected explicitly — demonstrably wrong for at least one real pair
   (MPR's opposite effect on bank NIM vs. leveraged-industrial net profit).
   A sector-blind ontology would be actively misleading, not merely
   incomplete.

## Trade-offs

- **Curation cost is real and ongoing.** Someone (owner, or eventually an
  analyst-reviewed queue) must write and maintain edges — this is not
  free, and a wrong edge asserted with unearned authority is worse than no
  edge (the LLM falls back to its own reasoning, which is at least
  self-disclosed as unstructured). Mitigation: ship a **small, high-confidence
  core** first (the accounting skeleton, which is definitional and requires
  no judgment call) and add `causal` edges only as they're actually needed
  by a real reasoning call, evidence-status-tagged from day one.
- **An ontology can ossify.** A rejected-then-later-true mechanism (regime
  change) needs `evidence_status` to be revisable, append-only-versioned
  like everything else on this platform — not a silent overwrite.
- **Sector conditioning multiplies edge count.** Seven sector overlays
  (Banking, Insurance, Industrial, Consumer Goods, Agriculture, Oil & Gas,
  Telecom, Utilities, Healthcare — nine per the owner's list) each need
  their own macro-sensitivity edges; this is deliberately deferred (Part 12
  roadmap) rather than attempted all at once.

## Risks

- **Qualitative nodes (`management_quality`, `corporate_governance_score`)
  are the ontology's softest, most overfit-prone corner** — there is no
  accounting identity to anchor them, and "proxies_for" edges from them are
  inherently weak. These nodes are explicitly flagged: any
  `investment_implications` row whose causal chain rests primarily on a
  qualitative-node edge should carry a lower `confidence` band by
  construction (a policy for the Financial Reasoning Engine to enforce, not
  the ontology's own job) and remains a strong candidate for the
  self-critique gate's `ignored_alternative_explanation` question.
- **A confirmed edge could still be a spurious correlation restated as
  causation** if the underlying hypothesis test (H-XXX) itself had a false
  positive — the ontology inherits, not eliminates, the research engine's
  own error rate. This is disclosed, not solved, here.
- **Ontology edges could be used to smuggle in a shortcut around
  pre-registration** — e.g., citing an edge as if it were itself a
  validated trading signal. Explicitly forbidden: an ontology edge, even at
  `ngx_confirmed`, is evidence for a reasoning *narrative*, never a
  substitute for the pre-registration/placebo/walk-forward gauntlet before
  anything becomes a portfolio input (same non-negotiable as the
  architecture doc's §11 governance table).

## Future extensions

- **Multi-exchange overlays.** The node/edge core (accounting identities,
  general macro mechanisms) is market-agnostic by construction; NGX-specific
  facts (which macro edges are `ngx_confirmed`/`ngx_rejected`, which sector
  overlays exist) live in a market-scoped config layer — the same extension
  pattern as `DocumentProvider` (architecture doc §10).
- **Edge-level backtestable predictions.** Once a financial-statements
  dataset exists, `causal` edges with numeric endpoints (e.g., `mpr
  drives_negative industrial.net_profit`) become directly testable as new
  hypotheses in the existing research engine — the ontology becomes a
  **hypothesis-generation surface**, feeding `docs/HYPOTHESIS_DISCOVERY_DESIGN.md`'s
  scanner exactly like any other candidate, never bypassing it.

## Dependencies

- `securities.sector_ngx` population (today 0/320 — a known, disclosed gap
  in `company_intelligence.py`'s `UNAVAILABLE_FIELDS`). Sector-conditioned
  edges cannot be *applied* to a specific company until this resolves,
  though the ontology itself can be authored without it.
- A financial-statements dataset (not yet acquired — the same blocker the
  Reasoning Engine Specification's §13 non-goals section already discloses
  for numeric intrinsic-value output). Blocks `sector_ratio` and most
  `income_statement`/`balance_sheet`/`cash_flow` node population; does not
  block authoring the ontology's structure.
- `docs/FACTOR_REGISTRY.md` as the living source for `evidence_status` —
  this creates a **process dependency**: every future hypothesis verdict
  should, going forward, prompt an ontology edge update (a checklist item
  proposed in Part 12's roadmap, not built here).
- `configs/fact_taxonomy.toml` / `configs/event_taxonomy.toml` naming
  conventions, reused verbatim for node identifiers so `causal_chain_steps`
  rows can reference ontology nodes and existing fact/event types with one
  shared vocabulary, not two parallel ones.
