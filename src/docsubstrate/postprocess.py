"""Artifact post-processing pipeline for DocSubstrate.

Rendering and post-processing are intentionally separate concerns. Engines
materialize an artifact; post-processors may then enrich or transform that
artifact without owning document semantics or layout.

Post-processing order is part of the contract. Processors are sorted by stage
so byte-mutating operations happen before signatures and final delivery steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from hashlib import sha256
from typing import Any, Mapping, Protocol, Sequence

from docsubstrate.context import DocumentContext
from docsubstrate.engines import EngineArtifact
from docsubstrate.materialization import MaterializationRequest


class PostProcessStage(IntEnum):
    """Stable lifecycle order for artifact transformations."""

    ENRICH = 100
    CONFORM = 200
    SIGN = 300
    PROTECT = 400
    DELIVER = 500


@dataclass(frozen=True, slots=True)
class PostProcessContext:
    request: MaterializationRequest
    document: DocumentContext
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ArtifactPostProcessor(Protocol):
    name: str
    stage: PostProcessStage

    def supports(self, artifact: EngineArtifact, context: PostProcessContext) -> bool:
        ...

    def process(self, artifact: EngineArtifact, context: PostProcessContext) -> EngineArtifact:
        ...


@dataclass(frozen=True, slots=True)
class ArtifactPipeline:
    processors: Sequence[ArtifactPostProcessor] = field(default_factory=tuple)

    def run(self, artifact: EngineArtifact, context: PostProcessContext) -> EngineArtifact:
        current = artifact
        applied: list[tuple[str, str]] = []
        lineage: list[dict[str, str]] = []
        ordered = sorted(
            enumerate(self.processors),
            key=lambda item: (int(getattr(item[1], "stage", PostProcessStage.ENRICH)), item[0]),
        )
        for _, processor in ordered:
            if not processor.supports(current, context):
                continue
            input_digest = sha256(current.content).hexdigest()
            current = processor.process(current, context)
            output_digest = sha256(current.content).hexdigest()
            stage = PostProcessStage(getattr(processor, "stage", PostProcessStage.ENRICH))
            applied.append((processor.name, stage.name.lower()))
            lineage.append(
                {
                    "processor": processor.name,
                    "stage": stage.name.lower(),
                    "input_digest": input_digest,
                    "output_digest": output_digest,
                }
            )

        metadata = dict(current.metadata)
        metadata["postprocessors"] = tuple(name for name, _ in applied)
        metadata["postprocess_trace"] = tuple(applied)
        metadata["artifact_lineage"] = tuple(lineage)
        return EngineArtifact(
            content=current.content,
            media_type=current.media_type,
            engine=current.engine,
            metadata=metadata,
        )
