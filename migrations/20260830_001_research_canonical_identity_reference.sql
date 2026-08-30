-- Stage 2C: immutable, opt-in canonical instrument references on the
-- existing Research OS query/request ledger.  Cross-database integrity is
-- deliberately application-validated; SQLite cannot enforce it here.
ALTER TABLE query_log ADD COLUMN canonical_instrument_id TEXT;
ALTER TABLE query_log ADD COLUMN canonical_resolution_status TEXT NOT NULL DEFAULT 'not_requested'
    CHECK (canonical_resolution_status IN ('resolved','unknown','ambiguous','temporally_unavailable','legacy_fallback','not_requested'));
ALTER TABLE query_log ADD COLUMN canonical_exchange TEXT;
ALTER TABLE query_log ADD COLUMN canonical_resolution_decision_time TEXT;
ALTER TABLE query_log ADD COLUMN canonical_resolution_system_vintage TEXT;
ALTER TABLE query_log ADD COLUMN canonical_availability_policy TEXT;
ALTER TABLE query_log ADD COLUMN canonical_resolver_version TEXT;
ALTER TABLE query_log ADD COLUMN canonical_reference_status TEXT NOT NULL DEFAULT 'not_applicable'
    CHECK (canonical_reference_status IN ('validated','unresolved','stale','missing_target','not_applicable'));
ALTER TABLE query_log ADD COLUMN canonical_resolution_reason TEXT;

CREATE INDEX IF NOT EXISTS ix_query_log_canonical_instrument
    ON query_log(canonical_instrument_id)
    WHERE canonical_instrument_id IS NOT NULL;
