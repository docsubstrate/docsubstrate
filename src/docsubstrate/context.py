"""Universal document context shared by all source and rendering adapters.

No renderer owns document truth.  A DocumentContext carries coexisting
representations and their correspondence without forcing them into a single
linear IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from docsubstrate.ir import Document
from docsubstrate.relations import RepresentationGraph
from docsubstrate.semantics import SemanticGraph


@dataclass(frozen=True, slots=True)
class PresentationProfile:
    """Renderer-neutral presentation intent and constraints."""

    id: str = "default"
    values: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentContext:
    """Coexisting views of one document materialization request.

    ``semantic`` answers what the document means.
    ``structure`` answers what document constructs are present.
    ``presentation`` carries renderer-neutral appearance/layout intent.
    ``relations`` records typed correspondence among representation dimensions.

    Any representation may be absent when a source adapter cannot provide it;
    engine capability negotiation decides whether that context is sufficient.
    """

    kind: str
    semantic: SemanticGraph | None = None
    structure: Document | None = None
    presentation: PresentationProfile = field(default_factory=PresentationProfile)
    relations: RepresentationGraph = field(default_factory=RepresentationGraph)
    metadata: Mapping[str, Any] = field(default_factory=dict)
