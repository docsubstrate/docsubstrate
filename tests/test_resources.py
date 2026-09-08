from __future__ import annotations

from docsubstrate.resources import (
    IntegrityDigest,
    MaterializationRef,
    ResourceDescriptor,
)


def test_content_address_comes_from_integrity_not_locator() -> None:
    resource = ResourceDescriptor(
        resource_key="schema:example",
        resource_type="schema",
        media_type="application/schema+json",
        materialization=MaterializationRef(
            kind="external",
            locator="https://example.invalid/schema/1",
            integrity=IntegrityDigest("sha256", "abc123"),
            resolver="uri",
        ),
    )

    assert resource.content_address() == "sha256:abc123"


def test_derived_resource_need_not_claim_material_bytes_as_ground_truth() -> None:
    resource = ResourceDescriptor(
        resource_key="index:record-123",
        resource_type="derived-index",
        semantic_type="search-index/1",
        materialization=MaterializationRef(kind="derived"),
    )

    assert resource.materialization is not None
    assert resource.materialization.kind == "derived"
    assert resource.content_address() is None


def test_embedded_resource_can_carry_length_and_integrity() -> None:
    resource = ResourceDescriptor(
        resource_key="evidence:synthetic",
        resource_type="evidence",
        media_type="application/octet-stream",
        materialization=MaterializationRef(
            kind="embedded",
            locator="resources/evidence.bin",
            length=1234,
            integrity=IntegrityDigest("sha256", "deadbeef"),
        ),
    )

    assert resource.materialization is not None
    assert resource.materialization.length == 1234
    assert resource.content_address() == "sha256:deadbeef"
