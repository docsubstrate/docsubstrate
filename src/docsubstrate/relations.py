"""Relations between DocSubstrate representation dimensions.

DocSubstrate does not model semantics -> structure -> presentation as a lossy
linear compilation hierarchy.  The dimensions coexist.  Typed representation
relations record how semantic entities are expressed by structural nodes while
preserving identity and provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class RepresentationRef:
    """Stable reference to an entity in one representation dimension."""

    dimension: str
    id: str


@dataclass(frozen=True, slots=True)
class RepresentationRelation:
    """Typed correspondence between two representation entities.

    Common predicates include ``represented_by``, ``derived_from``,
    ``labels``, ``summarizes`` and ``evidences``.  The relation is deliberately
    not restricted to semantic -> structural mappings so future dimensions can
    participate without changing the core model.
    """

    source: RepresentationRef
    predicate: str
    target: RepresentationRef
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RepresentationGraph:
    relations: Sequence[RepresentationRelation] = field(default_factory=tuple)

    def from_ref(self, ref: RepresentationRef) -> tuple[RepresentationRelation, ...]:
        return tuple(relation for relation in self.relations if relation.source == ref)

    def to_ref(self, ref: RepresentationRef) -> tuple[RepresentationRelation, ...]:
        return tuple(relation for relation in self.relations if relation.target == ref)
