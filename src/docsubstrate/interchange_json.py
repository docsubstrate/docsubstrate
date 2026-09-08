"""Canonical JSON reference encoding for Portable Institutional Packages.

This is a reference interchange experiment, not a frozen wire standard. The
encoding is deterministic for the current package model and intentionally uses
only JSON data types so independent readers need not import DocSubstrate.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from docsubstrate.occurrence import OccurrenceRecord
from docsubstrate.package import PortableInstitutionalPackage

ENCODING_ID = "docsubstrate.canonical-json"
ENCODING_VERSION = "0.3"
MetadataBasis = Literal["asserted", "observed", "derived", "inferred"]
MetadataSubjectKind = Literal[
    "package",
    "object",
    "relation",
    "representation",
    "artifact",
    "resource",
    "extension",
    "preservation-claim",
    "occurrence",
]


@dataclass(frozen=True, slots=True)
class MetadataAssertion:
    """Explicit interpretation context carried alongside the package graph.

    Metadata is deliberately kept at the interchange boundary while its
    first-class/core status is being falsified. ``basis`` separates source or
    machine-observed facts from derived/inferred interpretation so a future
    reader never has to guess which statements came from the source system and
    which were produced by an agent.
    """

    metadata_id: str
    subject_kind: MetadataSubjectKind
    subject_id: str
    key: str
    value: str | int | float | bool
    basis: MetadataBasis
    vocabulary_id: str | None = None
    source_refs: Sequence[str] = field(default_factory=tuple)
    producer_ref: str | None = None
    timestamp: str | None = None


def _sorted_records(records: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    return sorted(records, key=lambda item: tuple(str(item.get(key, "")) for key in keys))


def _json_ready(value: Any) -> Any:
    """Recursively project dataclass output into deterministic JSON data types."""

    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        normalized = [_json_ready(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    return value


def package_to_mapping(
    package: PortableInstitutionalPackage,
    *,
    metadata_assertions: Sequence[MetadataAssertion] = (),
    occurrences: Sequence[OccurrenceRecord] = (),
) -> dict[str, Any]:
    """Project a package into a deterministic, runtime-independent JSON mapping."""

    raw = _json_ready(asdict(package))
    raw["capabilities"] = sorted(package.capabilities)
    raw["vocabularies"] = _sorted_records(raw["vocabularies"], "vocabulary_id")
    raw["objects"] = _sorted_records(raw["objects"], "object_id")
    raw["external_references"] = _sorted_records(
        raw["external_references"], "reference_id"
    )
    raw["relations"] = _sorted_records(raw["relations"], "relation_id")
    raw["representations"] = _sorted_records(raw["representations"], "representation_id")
    raw["protections"] = _sorted_records(raw["protections"], "protection_id")
    raw["key_envelopes"] = _sorted_records(raw["key_envelopes"], "envelope_id")
    raw["artifacts"] = _sorted_records(raw["artifacts"], "artifact_id")
    raw["resources"] = _sorted_records(raw["resources"], "resource_key")
    raw["preservation_claims"] = _sorted_records(raw["preservation_claims"], "claim_id")
    raw["extensions"] = _sorted_records(raw["extensions"], "extension_id")

    metadata = [_json_ready(asdict(item)) for item in metadata_assertions]
    metadata = _sorted_records(metadata, "metadata_id")
    package_occurrences = raw.pop("occurrences")
    occurrence_records = package_occurrences + [
        _json_ready(asdict(item)) for item in occurrences
    ]
    occurrence_records = _sorted_records(occurrence_records, "occurrence_id")
    occurrence_ids = [item["occurrence_id"] for item in occurrence_records]
    if len(occurrence_ids) != len(set(occurrence_ids)):
        raise ValueError("duplicate occurrence id across package and compatibility argument")

    return {
        "encoding": {"id": ENCODING_ID, "version": ENCODING_VERSION},
        "metadata": metadata,
        "occurrences": occurrence_records,
        "package": raw,
    }


def dumps_canonical(
    package: PortableInstitutionalPackage,
    *,
    metadata_assertions: Sequence[MetadataAssertion] = (),
    occurrences: Sequence[OccurrenceRecord] = (),
) -> bytes:
    """Serialize with stable UTF-8 bytes suitable for hashing and fixture comparison."""

    mapping = package_to_mapping(
        package,
        metadata_assertions=metadata_assertions,
        occurrences=occurrences,
    )
    text = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


def loads_mapping(data: bytes | str):
    """Parse JSON without constructing DocSubstrate runtime classes."""

    if isinstance(data, bytes):
        data = data.decode("utf-8")
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("canonical package root must be a JSON object")
    encoding = value.get("encoding")
    if not isinstance(encoding, dict) or encoding.get("id") != ENCODING_ID:
        raise ValueError("unsupported or missing canonical encoding id")
    if not isinstance(value.get("package"), dict):
        raise ValueError("canonical package must contain a package object")
    if not isinstance(value.get("metadata", []), list):
        raise ValueError("canonical package metadata must be a list")
    if not isinstance(value.get("occurrences", []), list):
        raise ValueError("canonical package occurrences must be a list")
    return value
