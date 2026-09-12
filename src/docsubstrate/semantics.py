"""Semantic dimension primitives for DocSubstrate.

The semantic model describes what a document means independently of how that
meaning is represented structurally or rendered.  It is intentionally small:
domains such as commerce and medicine define vocabularies on top of these
primitives rather than extending the renderer model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class SemanticEntity:
    """A typed semantic entity participating in a document.

    Examples include ``party.customer``, ``commerce.line_item``,
    ``clinical.measurement`` and ``document.signature``.
    """

    id: str
    type: str
    value: Any = None
    attributes: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SemanticRelation:
    """A typed directed relation between semantic entities."""

    source: str
    predicate: str
    target: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SemanticGraph:
    """Backend-neutral semantic view of one document context."""

    entities: Sequence[SemanticEntity] = field(default_factory=tuple)
    relations: Sequence[SemanticRelation] = field(default_factory=tuple)

    def entity(self, entity_id: str) -> SemanticEntity:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        raise KeyError(entity_id)
