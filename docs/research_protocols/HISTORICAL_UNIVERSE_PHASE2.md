# Historical Universe Reconstruction — Phase 2

`HistoricalMarketSeries` is a deterministic source-series record derived from
archived NGX market artifacts. It records what the available source published;
it is neither a canonical security nor a historical IdentifierAlias.

`first_observed_in_available_source` and `last_observed_in_available_source`
are observational bounds only. They never populate listing or delisting dates.

## Continuity review

An apparent source-series handoff is classified independently from canonical
identity. Without verified primary evidence it remains `unresolved`. A
holding-company reorganization is `issuer_reorganization_uncertain`, not a
ticker alias. Only verified simple ticker-renaming evidence can recommend one
instrument plus temporally bounded aliases; a verified security replacement
recommends two instruments connected by a successor relationship.

## Proposed future mapping contract

`MarketSeriesIdentityMapping` is justified but is not persisted in Phase 2.

| Field | Semantics |
|---|---|
| `mapping_id` | Immutable mapping assertion ID |
| `source_provider`, `source_dataset`, `source_series_id` | Source-series lineage |
| `published_symbol` | Label used by that source |
| `canonical_instrument_id` | Proposed/verified owner, when supported |
| `mapping_semantics` | `as_traded_exchange_series`, `provider_normalized_series`, `fund_alpha_normalized_series`, or `composite_or_merged_series` |
| `valid_source_range` | Range within the provider/dataset, not exchange alias validity |
| `verification_status`, `evidence_reference`, `recorded_at` | Evidence and capture-vintage controls |

A series-ownership mapping must never automatically create an IdentifierAlias
or merge InstrumentListings. For as-traded NGX series, the same primary
evidence may later support both assertions, but they remain distinct,
append-only records.
