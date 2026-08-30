# Stage 1 migration enablement

This stage adds contracts, fixtures, and a migration runtime only. It does
not migrate existing records or change consumer behavior.

## Contract ownership

Investment OS owns `CompanyIssuer`, `InstrumentListing`, `IdentifierAlias`,
`Source`, `SourceEndpoint`, document artifacts/versions/representations,
evidence, facts, events, corporate actions, relationships, coverage, and
temporal query context. FRE owns reasoning coverage and critique outcomes;
Alpha owns formal test/recommendation objects; Research OS owns research
workflow records; Dataset Factory owns derived training artifacts.

`CompanyIssuer.company_id` and `InstrumentListing.instrument_id` are UUIDv7
identities. Symbols are `IdentifierAlias` records, never company identity.
Document identity is artifact UUID plus immutable SHA-256 content identity;
`storage_uri` is an opaque storage abstraction and never a Windows-path domain
contract. `LocalImmutableArchive` implements the first storage adapter using
content-addressed files and opaque `fund-alpha-archive://sha256/...` URIs;
future S3/MinIO/R2/Azure adapters satisfy the same boundary. `RawDocument.raw_bytes`
remains an acquisition DTO only.

## Temporal semantics

`TemporalValue` carries source precision (`date`, `minute`, or `second`). A
date-only source stays date-only. `published_at` establishes public
availability, `recorded_at` establishes Fund Alpha capture vintage,
`retrieved_at` records fetch, `event_time` records occurrence,
`effective_time` records legal/economic effect, financial periods use
`period_start`/`period_end`, and relationship/listing applicability uses
`valid_from`/`valid_to`.

`TemporalQueryContext(decision_time, system_vintage, availability_policy,
min_source_confidence)` replaces ambiguous `as_of`/`knowledge_at`. Strict
mode requires both published by decision time and recorded by system vintage.
Verified reconstruction additionally requires explicit auditable historical
publication verification; absent publication timing is unavailable.

## Fact and confidence rules

`FactAssertion.validation_status`, `evidence_status`, and `record_status`
are independent. A superseded evidence-grade fact remains reconstructable;
a retracted fact remains auditable. Evidence-grade promotion needs grounded
evidence. Authority tier, source/data confidence, extraction confidence,
evidence status, coverage, and reasoning confidence are typed separate values
and may not be averaged.

## Migration policy

IDs are `YYYYMMDD_NNN_domain_slug`; the ledger is append-only and contains
target, checksum, pre/post version, applied time, and verified backup-manifest
hash. The first explicit migration is a pre-consolidation baseline, not a
fictional replay of historic ALTER statements. Production-class runs require a
verified snapshot manifest, assert expected pre-version, use a SQLite
transaction where supported, fail closed, and use forward corrective
migrations rather than destructive down migrations. Existing `db.init_db()`
remains untouched during Stage 1.

## Fixtures and verification

`fixtures/stage1/minimal.json` and `adversarial.json` are explicitly
`synthetic_non_evidence`; they cannot support research or Alpha verdicts.
Frozen regression fixtures are owner-safe derived recipes/manifests. CI must
run `python scripts/stage1/verify_stage1.py` and must not use mutable live
databases.

The executable frozen fixture comprises `ngx_regression.sqlite`,
`registry_regression.sqlite`, and `manifest.json`. It is a deterministic,
selected regression subset with retained documented financial values, source
baseline hashes and commit, schema/baseline versions, counts, hashes, and
expected query outputs. It is explicitly `synthetic_non_evidence=true` even
where a representative value originated from a production observation.
