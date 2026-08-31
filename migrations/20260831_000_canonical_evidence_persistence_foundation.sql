CREATE TABLE canonical_sources (
    source_id TEXT PRIMARY KEY CHECK(length(source_id)=36 AND substr(source_id,15,1)='7'),
    source_name TEXT NOT NULL,
    authority_tier TEXT NOT NULL,
    reliability_policy_version TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK(is_synthetic IN (0,1)),
    retention_policy TEXT,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL,
    UNIQUE(source_name, authority_tier, reliability_policy_version, is_synthetic)
);

CREATE TABLE canonical_source_endpoints (
    endpoint_id TEXT PRIMARY KEY CHECK(length(endpoint_id)=36 AND substr(endpoint_id,15,1)='7'),
    source_id TEXT NOT NULL REFERENCES canonical_sources(source_id),
    canonical_uri TEXT NOT NULL,
    endpoint_kind TEXT NOT NULL,
    publication_time_policy TEXT,
    retention_policy TEXT,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL,
    UNIQUE(source_id, canonical_uri)
);

CREATE TABLE canonical_document_artifacts (
    artifact_id TEXT PRIMARY KEY CHECK(length(artifact_id)=36 AND substr(artifact_id,15,1)='7'),
    source_endpoint_id TEXT NOT NULL REFERENCES canonical_source_endpoints(endpoint_id),
    content_sha256 TEXT NOT NULL UNIQUE CHECK(length(content_sha256)=64),
    storage_uri TEXT NOT NULL UNIQUE,
    byte_size INTEGER NOT NULL CHECK(byte_size >= 0),
    media_type TEXT NOT NULL,
    acquisition_mode TEXT NOT NULL,
    original_filename TEXT,
    retrieved_at_value TEXT NOT NULL,
    retrieved_at_precision TEXT NOT NULL,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL,
    retention_restricted INTEGER NOT NULL DEFAULT 0 CHECK(retention_restricted IN (0,1))
);

CREATE TABLE canonical_document_versions (
    document_version_id TEXT PRIMARY KEY CHECK(length(document_version_id)=36 AND substr(document_version_id,15,1)='7'),
    artifact_id TEXT NOT NULL UNIQUE REFERENCES canonical_document_artifacts(artifact_id),
    document_type TEXT NOT NULL,
    published_at_value TEXT,
    published_at_precision TEXT,
    publication_time_verification TEXT,
    supersedes_document_version_id TEXT REFERENCES canonical_document_versions(document_version_id),
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL,
    CHECK((published_at_value IS NULL AND published_at_precision IS NULL) OR (published_at_value IS NOT NULL AND published_at_precision IS NOT NULL))
);

CREATE TABLE canonical_parsed_document_representations (
    representation_id TEXT PRIMARY KEY CHECK(length(representation_id)=36 AND substr(representation_id,15,1)='7'),
    document_version_id TEXT NOT NULL REFERENCES canonical_document_versions(document_version_id),
    parser_name TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    representation_uri TEXT,
    extracted_text TEXT NOT NULL,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL,
    UNIQUE(document_version_id, parser_name, parser_version, artifact_sha256)
);

CREATE TABLE canonical_evidence_locators (
    locator_id TEXT PRIMARY KEY CHECK(length(locator_id)=36 AND substr(locator_id,15,1)='7'),
    document_version_id TEXT NOT NULL REFERENCES canonical_document_versions(document_version_id),
    representation_id TEXT REFERENCES canonical_parsed_document_representations(representation_id),
    locator_text TEXT,
    quote TEXT,
    page_number INTEGER,
    section_title TEXT,
    paragraph_label TEXT,
    table_locator TEXT,
    char_start INTEGER,
    char_end INTEGER,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL,
    CHECK(char_end IS NULL OR char_start IS NULL OR char_end >= char_start)
);

CREATE TABLE canonical_evidence_items (
    evidence_id TEXT PRIMARY KEY CHECK(length(evidence_id)=36 AND substr(evidence_id,15,1)='7'),
    source_id TEXT NOT NULL REFERENCES canonical_sources(source_id),
    document_version_id TEXT NOT NULL REFERENCES canonical_document_versions(document_version_id),
    locator_id TEXT REFERENCES canonical_evidence_locators(locator_id),
    evidence_type TEXT NOT NULL,
    supporting_text TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    extraction_confidence REAL,
    verification_status TEXT NOT NULL,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL
);

CREATE TABLE canonical_citations (
    citation_id TEXT PRIMARY KEY CHECK(length(citation_id)=36 AND substr(citation_id,15,1)='7'),
    evidence_id TEXT NOT NULL REFERENCES canonical_evidence_items(evidence_id),
    source_url TEXT NOT NULL,
    authority_metadata_json TEXT NOT NULL,
    citation_metadata_json TEXT NOT NULL,
    citation_role TEXT NOT NULL DEFAULT 'supporting',
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL
);

CREATE TABLE canonical_retrieval_attempts (
    retrieval_attempt_id TEXT PRIMARY KEY CHECK(length(retrieval_attempt_id)=36 AND substr(retrieval_attempt_id,15,1)='7'),
    source_url TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('discovered_only','retrieval_failed','retrieved','archived','parsed','evidence_located','evidence_grade')),
    acquisition_mode TEXT NOT NULL,
    error_type TEXT,
    recorded_at_value TEXT NOT NULL,
    recorded_at_precision TEXT NOT NULL
);

CREATE INDEX ix_canonical_artifacts_endpoint ON canonical_document_artifacts(source_endpoint_id, recorded_at_value);
CREATE INDEX ix_canonical_document_versions_artifact ON canonical_document_versions(artifact_id);
CREATE INDEX ix_canonical_evidence_locator_version ON canonical_evidence_locators(document_version_id, page_number);
CREATE INDEX ix_canonical_evidence_items_document ON canonical_evidence_items(document_version_id, locator_id);
CREATE INDEX ix_canonical_citations_evidence ON canonical_citations(evidence_id);
