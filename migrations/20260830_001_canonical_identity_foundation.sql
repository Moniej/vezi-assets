CREATE TABLE company_issuers (
    company_id TEXT PRIMARY KEY CHECK(length(company_id)=36 AND substr(company_id,15,1)='7'),
    legal_name TEXT,
    display_name TEXT,
    domicile_country TEXT,
    issuer_status TEXT NOT NULL DEFAULT 'unknown' CHECK(issuer_status IN ('active','inactive','unknown')),
    recorded_at TEXT NOT NULL
);
CREATE INDEX ix_company_issuers_legal_name ON company_issuers(legal_name);

CREATE TABLE instrument_listings (
    instrument_id TEXT PRIMARY KEY CHECK(length(instrument_id)=36 AND substr(instrument_id,15,1)='7'),
    company_id TEXT REFERENCES company_issuers(company_id),
    exchange_code TEXT,
    instrument_type TEXT NOT NULL CHECK(instrument_type IN ('equity','fund','bond','other')),
    listing_status TEXT NOT NULL DEFAULT 'unknown' CHECK(listing_status IN ('active','delisted','suspended','unknown')),
    listing_date TEXT,
    delisting_date TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX ix_instrument_listings_company ON instrument_listings(company_id);
CREATE INDEX ix_instrument_listings_exchange ON instrument_listings(exchange_code, listing_status);

CREATE TABLE identifier_aliases (
    alias_id TEXT PRIMARY KEY CHECK(length(alias_id)=36 AND substr(alias_id,15,1)='7'),
    subject_type TEXT NOT NULL CHECK(subject_type IN ('company','instrument')),
    subject_id TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    exchange_code TEXT,
    valid_from TEXT,
    valid_to TEXT,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('verified','candidate','unresolved')),
    recorded_at TEXT NOT NULL,
    CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from),
    UNIQUE(subject_type,subject_id,identifier_type,identifier_value,exchange_code,recorded_at)
);
CREATE INDEX ix_identifier_aliases_resolver ON identifier_aliases(identifier_type,identifier_value,exchange_code,subject_type,recorded_at);
CREATE INDEX ix_identifier_aliases_subject ON identifier_aliases(subject_type,subject_id);

CREATE TABLE legacy_identity_mappings (
    mapping_id TEXT PRIMARY KEY CHECK(length(mapping_id)=36 AND substr(mapping_id,15,1)='7'),
    legacy_namespace TEXT NOT NULL,
    legacy_value TEXT NOT NULL,
    canonical_subject_type TEXT NOT NULL CHECK(canonical_subject_type IN ('company','instrument')),
    canonical_subject_id TEXT NOT NULL,
    mapping_status TEXT NOT NULL CHECK(mapping_status IN ('active','superseded','retracted')),
    evidence_reference TEXT,
    supersedes_mapping_id TEXT REFERENCES legacy_identity_mappings(mapping_id),
    recorded_at TEXT NOT NULL,
    UNIQUE(legacy_namespace,legacy_value,canonical_subject_type,canonical_subject_id,recorded_at)
);
CREATE INDEX ix_legacy_identity_mappings_lookup ON legacy_identity_mappings(legacy_namespace,legacy_value,mapping_status,recorded_at);
CREATE TRIGGER legacy_identity_mappings_no_update BEFORE UPDATE ON legacy_identity_mappings BEGIN SELECT RAISE(ABORT,'legacy identity mappings are append-only'); END;
CREATE TRIGGER legacy_identity_mappings_no_delete BEFORE DELETE ON legacy_identity_mappings BEGIN SELECT RAISE(ABORT,'legacy identity mappings are append-only'); END;
