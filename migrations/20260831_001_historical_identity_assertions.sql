CREATE TABLE historical_identifier_assertions (
    assertion_id TEXT PRIMARY KEY CHECK(length(assertion_id)=36 AND substr(assertion_id,15,1)='7'),
    alias_id TEXT REFERENCES identifier_aliases(alias_id),
    canonical_instrument_id TEXT NOT NULL REFERENCES instrument_listings(instrument_id),
    identifier_type TEXT NOT NULL CHECK(identifier_type IN ('ticker','symbol','isin','name')),
    identifier_value TEXT NOT NULL,
    exchange_code TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    validity_precision TEXT NOT NULL CHECK(validity_precision IN ('exact_date','month','year','observed_on_date_only','interval_verified')),
    verification_status TEXT NOT NULL CHECK(verification_status IN ('verified','corroborated','candidate','conflicting','unresolved')),
    verification_method TEXT NOT NULL,
    evidence_id INTEGER REFERENCES evidence(evidence_id),
    citation_reference TEXT,
    source_authority_tier TEXT NOT NULL CHECK(source_authority_tier IN ('tier1','tier2','tier3','tier4')),
    recorded_at TEXT NOT NULL,
    supersedes_assertion_id TEXT REFERENCES historical_identifier_assertions(assertion_id),
    CHECK(valid_to IS NULL OR valid_to >= valid_from),
    CHECK((verification_status <> 'verified') OR (evidence_id IS NOT NULL AND citation_reference IS NOT NULL AND source_authority_tier IN ('tier1','tier2','tier3')))
);
CREATE INDEX ix_historical_identity_lookup ON historical_identifier_assertions(identifier_type,identifier_value,exchange_code,verification_status,valid_from,valid_to);
CREATE INDEX ix_historical_identity_instrument ON historical_identifier_assertions(canonical_instrument_id,recorded_at);
CREATE TRIGGER historical_identity_assertions_no_update BEFORE UPDATE ON historical_identifier_assertions BEGIN SELECT RAISE(ABORT,'historical identity assertions are append-only'); END;
CREATE TRIGGER historical_identity_assertions_no_delete BEFORE DELETE ON historical_identifier_assertions BEGIN SELECT RAISE(ABORT,'historical identity assertions are append-only'); END;
