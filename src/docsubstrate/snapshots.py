"""Canonical document facts snapshots for semantic identity and signing.

Snapshots capture the institutional facts asserted by a logical document at one
observation/materialization point. They are renderer-neutral and canonicalized
before hashing so semantic integrity is independent from PDF/DOCX/HTML bytes.

Source revision metadata records where an observation came from, but it is not
part of semantic identity. The same institutional facts observed from two ERP
revisions therefore retain the same semantic digest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Any, Mapping

from docsubstrate.documents import DocumentIdentity


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return _canonical_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported canonical fact value: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    normalized = _canonical_value(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    document: DocumentIdentity
    facts: Mapping[str, Any]
    schema: str = "docsubstrate.document-snapshot/v1"
    source_revision: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    @property
    def canonical_payload(self) -> bytes:
        """Return the canonical semantic payload.

        Only identity-bearing institutional facts belong here. ``source_revision``
        and ``attributes`` describe the observation/provenance of this snapshot;
        changing them must not create a new semantic state.
        """
        return canonical_json(
            {
                "schema": self.schema,
                "document_uri": self.document.uri,
                "facts": self.facts,
            }
        )

    @property
    def semantic_digest(self) -> str:
        return sha256(self.canonical_payload).hexdigest()

    @property
    def semantic_uri(self) -> str:
        return f"urn:docsubstrate:semantic:sha256:{self.semantic_digest}"


def snapshot_from_dataclass(
    document: DocumentIdentity,
    facts: Any,
    *,
    source_revision: str | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> DocumentSnapshot:
    if not is_dataclass(facts):
        raise TypeError("snapshot_from_dataclass requires a dataclass instance")
    return DocumentSnapshot(
        document=document,
        facts=asdict(facts),
        source_revision=source_revision,
        attributes=attributes or {},
    )
