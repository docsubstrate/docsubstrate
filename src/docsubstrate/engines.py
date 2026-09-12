"""Capability contract for universal DocSubstrate document engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from docsubstrate.context import DocumentContext


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """What representations and execution features an engine can consume."""

    semantic: bool = False
    structure: bool = False
    presentation: bool = False
    page_execution: bool = False
    paginated_output: bool = False
    output_media_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EngineSupport:
    supported: bool
    reason: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineArtifact:
    content: bytes
    media_type: str
    engine: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class DocumentEngine(Protocol):
    """Common contract. Engines may choose different internal execution IRs."""

    name: str
    capabilities: EngineCapabilities

    def supports(self, context: DocumentContext) -> EngineSupport:
        ...

    def materialize(self, context: DocumentContext) -> EngineArtifact:
        ...
