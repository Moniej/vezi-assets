"""Local immutable document archive behind an object-storage-compatible boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from .contracts import DocumentArtifact, SourceEndpoint, TemporalValue


class ArtifactStorage(Protocol):
    """Storage uses opaque URIs so changing to object storage preserves identity."""

    def put(self, raw_bytes: bytes, *, media_type: str, source_endpoint: SourceEndpoint,
            retrieved_at: TemporalValue, recorded_at: TemporalValue) -> DocumentArtifact: ...


class LocalImmutableArchive:
    """Content-addressed local archive; files are never overwritten after hash verification."""

    def __init__(self, root: Path, *, uri_namespace: str = "fund-alpha-archive") -> None:
        self.root = root
        self.uri_namespace = uri_namespace.rstrip(":/")

    def put(self, raw_bytes: bytes, *, media_type: str, source_endpoint: SourceEndpoint,
            retrieved_at: TemporalValue, recorded_at: TemporalValue) -> DocumentArtifact:
        if source_endpoint.retention_policy == "prohibited":
            raise PermissionError("source endpoint policy prohibits artifact retention")
        digest = hashlib.sha256(raw_bytes).hexdigest()
        destination = self.root / digest[:2] / digest
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                raise RuntimeError("immutable archive path contains content with a different hash")
        else:
            destination.write_bytes(raw_bytes)
            destination.chmod(0o444)
        return DocumentArtifact(
            sha256=digest,
            storage_uri=f"{self.uri_namespace}://sha256/{digest}",
            byte_size=len(raw_bytes),
            media_type=media_type,
            source_endpoint_id=source_endpoint.endpoint_id,
            retrieved_at=retrieved_at,
            recorded_at=recorded_at,
            retention_restricted=source_endpoint.retention_policy == "restricted",
        )
