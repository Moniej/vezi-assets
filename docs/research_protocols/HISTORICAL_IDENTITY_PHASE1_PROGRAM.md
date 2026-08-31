# Historical Identity Reconstruction — Phase 1

This is an evidence and coverage program, not an automated identity backfill.
It answers which canonical instrument an exchange-qualified identifier denoted at
a historical decision date only when a historical assertion is supported by an
approved evidence chain.

## Temporal policy

`valid_from` and `valid_to` describe real-world identifier validity at the
precision actually evidenced. `recorded_at` is the actual Fund Alpha capture
time and is never backdated. `strict_system_vintage` requires
`recorded_at <= system_vintage`. The opt-in
`verified_historical_reconstruction` policy may use a later-recorded assertion
only when its historical interval is verified by an approved evidence chain;
the result is explicitly disclosed as a reconstruction. It is identity-only:
market inputs and H-024 predictors/outcomes remain under strict PIT policy.

## Evidence-first workflow

```text
approved historical source
  -> DocumentArtifact / DocumentVersion
  -> EvidenceItem with locator and Citation
  -> review candidate
  -> independently verified historical identifier assertion
  -> canonical IdentifierAlias interval (future controlled promotion)
```

`historical_identifier_assertions` references the existing `evidence` table;
it is not a parallel provenance system. A Tier 4 source can corroborate a
candidate but cannot produce a verified mapping. String similarity, current
ticker state, names, and model output can generate review work only.

## Phase 1 local-source finding

The locally available `data/reference/symbol_renames.csv` is retained as a
Tier 3 review input. Its four internally marked rows lack persisted
DocumentArtifact/EvidenceItem/Citation chains, so it produces only
`corroborated` review candidates. It creates zero verified historical aliases
and unlocks zero H-024 observations.

The corresponding migration is declared but deliberately not applied to the
live database during Phase 1: no reviewed evidence-backed assertion is ready
to persist.
