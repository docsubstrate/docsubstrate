"""Logical document identity and document-level relationships.

A DocumentIdentity identifies an institutional document independently from any
particular rendered artifact or materialization route. Business objects may project
into documents; documents may then materialize into one or more artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping, Protocol, Sequence

from docsubstrate.materialization import MaterializationRequest


@dataclass(frozen=True, slots=True)
class DocumentIdentity:
    kind: str
    source_system: str
    source_model: str
    source_record_ids: Sequence[int | str]
    # report_action is retained as materialization context for adapters that need it,
    # but it is deliberately excluded from key/uri. A route is not institutional
    # identity: the same invoice rendered through two report actions is still the
    # same logical document.
    report_action: str | None = None

    @classmethod
    def from_request(cls, request: MaterializationRequest) -> "DocumentIdentity":
        return cls(
            kind=request.document_kind,
            source_system=request.source_system,
            source_model=request.source_model,
            source_record_ids=tuple(request.source_record_ids),
            report_action=request.report_action,
        )

    @property
    def key(self) -> str:
        raw = "|".join(
            [
                self.kind,
                self.source_system,
                self.source_model,
                ",".join(map(str, self.source_record_ids)),
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()

    @property
    def uri(self) -> str:
        return f"urn:docsubstrate:document:{self.key}"


@dataclass(frozen=True, slots=True)
class DocumentRelation:
    source_uri: str
    predicate: str
    target_uri: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


class DocumentGraph(Protocol):
    def register(self, document: DocumentIdentity) -> None:
        ...

    def relate(self, relation: DocumentRelation) -> None:
        ...

    def get(self, document_uri: str) -> DocumentIdentity | None:
        ...

    def outgoing(self, document_uri: str, predicate: str | None = None) -> Sequence[DocumentRelation]:
        ...

    def incoming(self, document_uri: str, predicate: str | None = None) -> Sequence[DocumentRelation]:
        ...


class InMemoryDocumentGraph:
    def __init__(self) -> None:
        self._documents: dict[str, DocumentIdentity] = {}
        self._relations: list[DocumentRelation] = []

    def register(self, document: DocumentIdentity) -> None:
        self._documents[document.uri] = document

    def relate(self, relation: DocumentRelation) -> None:
        if relation not in self._relations:
            self._relations.append(relation)

    def get(self, document_uri: str) -> DocumentIdentity | None:
        return self._documents.get(document_uri)

    def outgoing(self, document_uri: str, predicate: str | None = None) -> Sequence[DocumentRelation]:
        return tuple(
            relation
            for relation in self._relations
            if relation.source_uri == document_uri and (predicate is None or relation.predicate == predicate)
        )

    def incoming(self, document_uri: str, predicate: str | None = None) -> Sequence[DocumentRelation]:
        return tuple(
            relation
            for relation in self._relations
            if relation.target_uri == document_uri and (predicate is None or relation.predicate == predicate)
        )
