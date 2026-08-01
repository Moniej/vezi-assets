# FRE Part 2 — Financial Knowledge Graph Expansion

*Design only. Extends, never forks, `entities`/`entity_relationships`/
`entity_mentions` (architecture doc §5/§8, additive, currently mostly
unpopulated). See `docs/fre/00_fre_master_index.md` for standing rules.*

## Objective

Turn the Knowledge Graph from a flat entity/mention store into a
**time-aware, typed relationship graph** capable of answering the owner's
list directly: who competes with whom, who supplies/buys from whom, what a
company's ownership and management lineage looks like, how a name maps
across a corporate action (merger, demerger, rename), and how a macro
variable or commodity connects to the companies it exposes — all without
adding a new storage engine, per the architecture doc's existing §5
decision that plain SQL joins are sufficient at this platform's scale.

## Rationale — a real gap found by cross-referencing two existing documents

Two facts, each individually documented elsewhere, combine into a concrete,
previously-unstated gap:

1. `docs/AI_INTELLIGENCE_LAYER_ARCHITECTURE.md` §8's DDL restricts
   `entities.entity_type` to exactly `('company','executive',
   'competitor_mention','regulator','sector')`. Yet the same document's §4.5
   `effect_chains` design (superseded in detail by the reasoning spec, but
   the underlying `entities` table is unchanged) describes
   `affected_entity_id` as pointing at "company/sector/commodity/macro
   variable — all already modeled as `entities` rows." **Commodity and
   macro-variable are not, in fact, in the `entity_type` CHECK constraint.**
   This is a real, disclosed inconsistency between two design documents,
   not yet a bug in running code (no commodity/macro entity rows exist
   yet) — but it will become one the first time `industry_reasoning.py` or
   a Macro Reasoning Engine call tries to link an implication to "Brent
   crude" or "MPR" as a first-class graph node.
2. `HANDOFF.md`'s Phase F report discloses that `entity_relationships
   .relation_type` today only ever holds the literal string
   `affects_order_N` (an artifact of `effect_chains`' own order-tagging,
   copied over when Phase F wired `record_relationship()`), **not** a
   genuinely classified relation like `competitor_of`/`supplier_of`. Phase
   F's own propagation logic works around this with a no-op filter on
   `entity_type='competitor_mention'` rather than a real relation-type
   check — explicitly flagged in that report as "a no-op filter today, real
   once entity typing gets more precise." This document is that "once."

Both gaps are additive fixes, not schema breaks: widen the `entity_type`
CHECK constraint, and introduce a genuinely populated `relation_type`
taxonomy alongside (not replacing) the existing `affects_order_N` values,
which remain valid for effect-chain-sourced rows.

## Node type expansion (additive `entity_type` values)

| New `entity_type` | Purpose | Populated from |
|---|---|---|
| `commodity` | Brent crude, PMS/AGO fuel prices, cocoa, etc. — closes the architecture doc §4.5 vs §8 gap above | `macro_series`, config-seeded (small, fixed list) |
| `macro_variable` | MPR, USD/NGN rate, inflation YoY, GDP growth | `macro_series`/`events`, config-seeded |
| `subsidiary` | A named subsidiary distinct from its parent's own ticker (e.g., a bank's insurance arm) | filing-derived entity extraction |
| `index` | NGX index membership as a graph node (NGXBNK, NGX30, ...) — lets "which index is this company in, and when" be a graph edge instead of a separate lookup | `indices`/`index_membership` (existing quant tables), read-only join, never duplicated |

`company`, `executive`, `competitor_mention`, `regulator`, `sector` are
unchanged. This is a pure additive widen of the CHECK constraint — zero
existing rows affected.

## Relationship type taxonomy (new, config-driven — `configs/relation_taxonomy.toml`)

Same pattern as every other taxonomy on this platform: adding a relation
type is a config change.

```toml
[corporate_structure]
types = ["subsidiary_of", "parent_of", "jv_partner_of", "merged_into", "demerged_from", "renamed_from"]

[commercial]
types = ["competitor_of", "supplier_of", "customer_of", "distributor_for"]

[governance]
types = ["regulated_by", "audited_by", "board_member_of", "executive_of", "major_shareholder_of"]

[macro_exposure]
types = ["exposed_to_commodity", "exposed_to_fx", "exposed_to_policy"]

[graph_provenance]
types = ["affects_order_1", "affects_order_2", "affects_order_3"]   # UNCHANGED — the existing
                                                                      # effect_chains-derived values,
                                                                      # kept as their own family so a
                                                                      # future query can distinguish
                                                                      # "a real classified relation"
                                                                      # from "an order-tagged effect
                                                                      # propagation artifact"
```

Every relation carries the schema's existing `valid_from`/`valid_to`
columns (already in the architecture doc's §8 DDL, unused until now) — this
is the mechanism for **time-awareness**: "who was CEO of company X on date
Y" is `entity_relationships` filtered to `relation_type='executive_of' AND
valid_from <= Y AND (valid_to IS NULL OR valid_to > Y)`, no new column
needed, just real population.

## Entity resolution and lineage — the hardest, most disclosed-risk part

**Ticker/company lineage** (renames, mergers, demergers) is not a new
problem for this platform — the quant Data Layer already resolves 4
verified renames via `data/reference/symbol_renames.csv` (Phase A's
document-ingestion report: "11,134 tickers resolved via the 4 verified
renames, 399 unresolved"). This document's contribution is **reusing that
existing, owner-verified mapping as the seed for `renamed_from` edges**,
not building a second, competing resolution mechanism:

```
entity(company, "Access Holdings Plc") --[renamed_from]--> entity(company, "Access Bank Plc")
```

with `valid_from` = the effective rename date already in
`symbol_renames.csv`. A merger/demerger, by contrast, has no existing
deterministic source — it must come from filing-derived entity extraction
(architecture doc §4.2), and inherits that pipeline's existing
human-review queue: **a new `merged_into`/`demerged_from` edge is never
auto-created at high confidence; it always lands in the same
entity-resolution merge queue Phase C already built, unchanged.**

**Management lineage** (who was CEO/CFO when) is populated the same way as
any other AI-detected event: an `executive_of` relationship with
`valid_from`/`valid_to`, sourced from a `management_change` fact (already
an existing leaf in `fact_taxonomy.toml`'s `[corporate_events]` group) —
zero new extraction machinery, this is a **relationship-graph projection of
an event type that already exists**, not a new pipeline.

**Ownership** (major shareholders) is the one genuinely new extraction
target on this list — NGX filings disclose substantial shareholding
notices, but no existing extractor or fact type covers this today. Proposed
new `fact_taxonomy.toml` leaf: `[ownership] types = ["substantial_shareholding_notice",
"insider_dealing_notice"]`, feeding `major_shareholder_of` edges with a
`confidence`-scored ownership percentage in the edge's evidence text (not a
new numeric column — percentage-of-float is exactly the kind of "float
-adjusted size" data point `HANDOFF.md`'s backlog already flags as not yet
acquired; this document does not invent it, it notes the dependency, §10 of
this program covers dataset acquisition).

## Cross-company and cross-sector relationships

Two distinct query shapes, both plain 2-3-hop SQL joins per the architecture
doc's existing §5 decision — no graph database needed:

1. **Direct** (1 hop): `entity_relationships` rows with
   `relation_type IN commercial ∪ corporate_structure`. This is exactly
   what Phase F's Industry Reasoning Engine already walks — this document
   only upgrades the *quality* of what it walks (real relation types
   instead of the `affects_order_N` no-op filter).
2. **Sector-mediated** (2 hop, company → sector → company): once
   `securities.sector_ngx` is populated (still 0/320, the same blocker Part
   1 flags), a "same-sector peer" query is `entity(company) →
   entities.entity_type='sector' → entity(company)`, distinct from a
   *disclosed* competitor relationship — the graph should never conflate
   "same sector" with "named competitor" (same-sector is a much weaker,
   purely structural signal, and any implication propagated across it must
   be labeled `sector_peer_inference`, a new, more heavily discounted
   confidence tier than Phase F's existing `propagated_from_implication_id`
   discount for a *named* competitor).

## Macro relationships

`exposed_to_commodity`/`exposed_to_fx`/`exposed_to_policy` edges connect a
`company`/`sector` node to a `commodity`/`macro_variable` node — this is
the graph-level anchor point for Part 1's ontology `causal` edges (the
ontology says *how* MPR affects industrial net profit in the abstract; the
knowledge graph's `exposed_to_policy` edge says *which specific companies*
that abstract mechanism applies to, evidence-sourced per company rather
than assumed sector-wide). A company's exposure edge is itself an
extraction target (a filing disclosing "40% of costs are USD-denominated"),
not inferred purely from sector membership — sector membership alone is a
weak prior, not evidence.

## Alternatives considered

1. **A dedicated graph database (Neo4j, etc.).** Rejected for the same
   reason the original architecture doc rejected it: no query on this
   platform yet needs more than 2-3 hops, and adding a new datastore
   duplicates the provenance/PIT/confidence machinery `db.py` already owns
   for everything else — a new engine would need its own append-only,
   `as_of_date`-aware discipline built from scratch.
2. **Treat `affects_order_N` as good enough and skip real relation
   typing.** Rejected — Phase F's own completion report already disclosed
   this as a temporary no-op, explicitly flagged for a future pass; this
   document is the owner-directed occasion to close it, not a
   rediscovery.
3. **Infer relation types automatically from co-mention frequency (no
   extraction, pure statistics).** Rejected as a primary mechanism — a
   purely statistical co-mention signal cannot distinguish "competitor" from
   "regulator" from "the article happened to discuss both," and would
   reintroduce exactly the unevidenced-inference risk the self-critique
   gate exists to catch. Could be a *candidate-generation* aid for the
   human entity-resolution queue (flag frequently-co-mentioned pairs for
   review) — noted as a future extension, not built as ground truth.

## Trade-offs

- Real relation typing requires real extraction work (a prompt asking the
  model to classify the relationship, not just note that two entities
  co-occur) — more LLM calls, more self-critique-gated review load, versus
  the current free `affects_order_N` byproduct of effect-chain extraction.
- Widening `entity_type` is a zero-risk additive CHECK constraint change,
  but every new type needs its own resolution logic eventually (a
  `commodity` entity doesn't need human-reviewed fuzzy-name merging the way
  a `company`/`executive` does — commodities are a small, fixed, config
  -seeded list, not an open extraction target) — the resolution-queue design
  should branch by `entity_type`, not treat all types identically.

## Risks

- **Ownership-percentage extraction is financially sensitive and
  error-prone** (a wrong "major shareholder" claim is a reputationally
  risky mistake for an institutional research product) — this is exactly
  the kind of claim that should never leave `unvalidated_ai_interpretation`
  status without a human review pass, more so than most fact types; flagged
  for a stricter review bar in Part 11's evaluation framework.
- **Merger/demerger detection risk of silently double-counting a company**
  in downstream Company Intelligence or ranking if the lineage edge isn't
  correctly walked — mitigated by the existing "the resolution queue is
  human-reviewed before two entities are silently merged" rule (architecture
  doc §4.2), restated here as non-negotiable for lineage edges specifically,
  since a wrong merge here corrupts historical time series, not just a
  single fact.

## Future extensions

- Co-mention-frequency-based candidate suggestions for the human merge
  queue (noted above, not built).
- A `board_member_of` / `major_shareholder_of` overlap query — "which
  companies share a board member or major shareholder" — a genuinely new
  analytical capability once both edge types are populated, useful for
  related-party-transaction risk flagging (a Corporate Governance use case
  the owner's ontology list names directly).
- Multi-exchange: `entity`/`entity_relationships` carry no exchange column
  by construction (same design already noted in the architecture doc §10),
  so a future NYSE/LSE company's lineage graph works identically once a new
  `DocumentProvider` exists.

## Dependencies

- `securities.sector_ngx` population (Part 1's same blocker) — required for
  sector-mediated 2-hop queries, not for direct 1-hop relations.
- The existing entity-resolution human-review queue (architecture doc
  §4.2) — this document adds volume and new edge types to that queue's
  workload, not a new queue.
- `data/reference/symbol_renames.csv` (existing, quant-engine-owned,
  owner-verified) as the seed for `renamed_from` edges — read-only reuse,
  never duplicated into a second source of truth.
- A financial-statements/shares-outstanding dataset for
  `major_shareholder_of` edges to carry a real float-adjusted percentage —
  not required for the edge to exist qualitatively, but required before any
  ownership-concentration *ranking* could be built on top of it.
