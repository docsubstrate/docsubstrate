from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from docsubstrate.interchange_json import MetadataAssertion, dumps_canonical, loads_mapping
from docsubstrate.package import (
    OpaqueExtension,
    PackageArtifact,
    PackageObject,
    PackageRelation,
    PackageRepresentation,
    PortableInstitutionalPackage,
    VocabularyRef,
)
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor


def _package() -> PortableInstitutionalPackage:
    payload = b"future-extension"
    return PortableInstitutionalPackage(
        package_id="pkg-1",
        format_version="0.1",
        profile="general",
        capabilities=frozenset({"future.optional", "graph.basic"}),
        vocabularies=(VocabularyRef("test", "1"),),
        objects=(
            PackageObject("obj-b", "Thing", "test"),
            PackageObject("obj-a", "Thing", "test"),
        ),
        relations=(
            PackageRelation("relation:a-b", "obj-a", "relates-to", "obj-b", "test"),
        ),
        representations=(PackageRepresentation("rep-1", "obj-a", "application/test"),),
        artifacts=(PackageArtifact("art-1", "rep-1", "artifact:1"),),
        resources=(
            ResourceDescriptor(
                resource_key="artifact:1",
                resource_type="artifact",
                media_type="application/octet-stream",
                materialization=MaterializationRef(
                    kind="embedded",
                    media_type="application/octet-stream",
                    length=3,
                    integrity=IntegrityDigest("sha256", hashlib.sha256(b"abc").hexdigest()),
                ),
            ),
            ResourceDescriptor(
                resource_key="extension:1",
                resource_type="extension-payload",
                materialization=MaterializationRef(
                    kind="embedded",
                    length=len(payload),
                    integrity=IntegrityDigest("sha256", hashlib.sha256(payload).hexdigest()),
                ),
            ),
        ),
        extensions=(
            OpaqueExtension(
                extension_id="ext-1",
                extension_type="future-thing",
                capability="future.optional",
                resource_key="extension:1",
            ),
        ),
    )


def test_canonical_json_is_deterministic_and_metadata_basis_is_explicit() -> None:
    package = _package()
    metadata = (
        MetadataAssertion(
            metadata_id="m-2",
            subject_kind="object",
            subject_id="obj-a",
            key="classification",
            value="candidate",
            basis="inferred",
            producer_ref="agent:test",
        ),
        MetadataAssertion(
            metadata_id="m-1",
            subject_kind="artifact",
            subject_id="art-1",
            key="ingested",
            value=True,
            basis="observed",
        ),
    )

    first = dumps_canonical(package, metadata_assertions=metadata)
    second = dumps_canonical(package, metadata_assertions=tuple(reversed(metadata)))
    assert first == second

    envelope = loads_mapping(first)
    assert [item["metadata_id"] for item in envelope["metadata"]] == ["m-1", "m-2"]
    assert [item["object_id"] for item in envelope["package"]["objects"]] == ["obj-a", "obj-b"]
    assert envelope["metadata"][1]["basis"] == "inferred"


def test_stdlib_independent_reader_understands_graph_metadata_and_fixity() -> None:
    reader_path = Path(__file__).parents[1] / "tools" / "independent_reader.py"
    spec = importlib.util.spec_from_file_location("independent_reader", reader_path)
    assert spec and spec.loader
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)

    envelope = loads_mapping(
        dumps_canonical(
            _package(),
            metadata_assertions=(
                MetadataAssertion(
                    metadata_id="m-1",
                    subject_kind="object",
                    subject_id="obj-a",
                    key="source-status",
                    value="received",
                    basis="asserted",
                ),
            ),
        )
    )

    summary = reader.summarize(envelope)
    assert summary["package_id"] == "pkg-1"
    assert summary["object_count"] == 2
    assert summary["opaque_extensions"][0]["capability"] == "future.optional"

    graph = reader.graph(envelope)
    assert graph["edges"][0]["source_exists"] is True
    assert graph["edges"][0]["target_exists"] is True

    metadata = reader.metadata_by_basis(envelope)
    assert metadata["asserted"][0]["key"] == "source-status"

    valid = reader.verify_artifact_bytes(envelope, "artifact:1", b"abc")
    invalid = reader.verify_artifact_bytes(envelope, "artifact:1", b"abd")
    assert valid["ok"] is True
    assert invalid["ok"] is False


def test_independent_reader_recognizes_every_internal_relation_target_kind() -> None:
    reader_path = Path(__file__).parents[1] / "tools" / "independent_reader.py"
    spec = importlib.util.spec_from_file_location("independent_reader_entities", reader_path)
    assert spec and spec.loader
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)

    envelope = {
        "package": {
            "package_id": "package:synthetic",
            "protections": [{"protection_id": "protection:1"}],
            "key_envelopes": [{"envelope_id": "envelope:1"}],
            "extensions": [{"extension_id": "extension:1"}],
            "relations": [
                {
                    "relation_id": f"relation:{index}",
                    "source_id": "package:synthetic",
                    "target_id": target,
                }
                for index, target in enumerate(
                    ("protection:1", "envelope:1", "extension:1"), start=1
                )
            ],
        }
    }

    assert all(edge["target_exists"] for edge in reader.graph(envelope)["edges"])
