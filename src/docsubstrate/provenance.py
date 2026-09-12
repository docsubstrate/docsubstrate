"""Artifact identity, provenance, and lineage for DocSubstrate.

Artifacts are materializations of logical documents. Artifact identity is
content-addressed; document identity is stable across renderers, locales, and
artifact versions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from docsubstrate.documents import DocumentIdentity
from docsubstrate.engines import EngineArtifact
from docsubstrate.materialization import MaterializationRequest


def artifact_digest(content: bytes) -> str:
    return sha256(content).hexdigest()


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    algorithm: str
    digest: str
    media_type: str

    @classmethod
    def from_artifact(cls, artifact: EngineArtifact) -> "ArtifactIdentity":
        return cls("sha256", artifact_digest(artifact.content), artifact.media_type)

    @property
    def uri(self) -> str:
        return f"urn:docsubstrate:artifact:{self.algorithm}:{self.digest}"


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    system: str
    model: str
    record_ids: Sequence[int | str]

    @classmethod
    def from_request(cls, request: MaterializationRequest) -> "SourceIdentity":
        return cls(request.source_system, request.source_model, tuple(request.source_record_ids))


@dataclass(frozen=True, slots=True)
class LineageStep:
    kind: str
    name: str
    input_digest: str | None = None
    output_digest: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArtifactProvenance:
    artifact: ArtifactIdentity
    document: DocumentIdentity
    source: SourceIdentity
    engine: str
    report_action: str | None = None
    semantic_digest: str | None = None
    parent_artifacts: Sequence[ArtifactIdentity] = field(default_factory=tuple)
    steps: Sequence[LineageStep] = field(default_factory=tuple)
    attributes: Mapping[str, Any] = field(default_factory=dict)

    @property
    def document_kind(self) -> str:
        return self.document.kind

    @property
    def lineage_key(self) -> str:
        return self.document.key


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    schema: str
    provenance: ArtifactProvenance

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _lineage_steps_from_metadata(metadata: Mapping[str, Any]) -> tuple[LineageStep, ...]:
    steps = []
    for item in metadata.get("artifact_lineage", ()):
        if not isinstance(item, Mapping):
            continue
        steps.append(
            LineageStep(
                kind="postprocess",
                name=str(item.get("processor", "unknown")),
                input_digest=item.get("input_digest"),
                output_digest=item.get("output_digest"),
                attributes={"stage": item.get("stage", "")},
            )
        )
    return tuple(steps)


def provenance_from_artifact(
    artifact: EngineArtifact,
    request: MaterializationRequest,
    *,
    semantic_digest: str | None = None,
    parent_artifacts: Sequence[ArtifactIdentity] = (),
    steps: Sequence[LineageStep] | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> ArtifactProvenance:
    resolved_steps = tuple(steps) if steps is not None else _lineage_steps_from_metadata(artifact.metadata)
    document = DocumentIdentity.from_request(request)
    return ArtifactProvenance(
        artifact=ArtifactIdentity.from_artifact(artifact),
        document=document,
        source=SourceIdentity.from_request(request),
        engine=artifact.engine,
        report_action=request.report_action,
        semantic_digest=semantic_digest,
        parent_artifacts=tuple(parent_artifacts),
        steps=resolved_steps,
        attributes=attributes or {},
    )


def manifest_from_artifact(
    artifact: EngineArtifact,
    request: MaterializationRequest,
    *,
    semantic_digest: str | None = None,
    parent_artifacts: Sequence[ArtifactIdentity] = (),
) -> ArtifactManifest:
    return ArtifactManifest(
        schema="docsubstrate.artifact-manifest/v3",
        provenance=provenance_from_artifact(
            artifact,
            request,
            semantic_digest=semantic_digest,
            parent_artifacts=parent_artifacts,
        ),
    )
