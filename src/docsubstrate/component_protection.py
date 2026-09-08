"""Canonical identity binding for protected semantic components.

This module performs no encryption and manages no keys. It produces the stable
Additional Authenticated Data input that an external JWE, COSE, CMS, or other
profile can integrity-bind to ciphertext.
"""

from __future__ import annotations

import json
from typing import Any

from docsubstrate.package import PortableInstitutionalPackage

COMPONENT_BINDING_PROFILE = "docsubstrate.semantic-component-binding/0.1"


def component_binding_mapping(
    package: PortableInstitutionalPackage,
    representation_id: str,
) -> dict[str, Any]:
    """Return institutional identity context for one protected component.

    Access envelopes and physical resource locations are deliberately absent:
    changing a recipient, KMS, or package layout must not change the semantic
    identity that the ciphertext authenticates.
    """

    representation_by_id = {
        item.representation_id: item for item in package.representations
    }
    component = representation_by_id.get(representation_id)
    if component is None:
        raise ValueError(f"unknown component representation: {representation_id}")
    object_by_id = {item.object_id: item for item in package.objects}
    owner = object_by_id.get(component.object_id)
    if owner is None:
        raise ValueError(f"component owner is missing: {component.object_id}")
    vocabulary_versions = {
        item.vocabulary_id: item.version for item in package.vocabularies
    }

    def semantic_identity(representation) -> dict[str, Any]:
        return {
            "representation_id": representation.representation_id,
            "representation_type": representation.representation_type,
            "version": representation.version,
            "vocabulary_id": representation.vocabulary_id,
            "vocabulary_version": vocabulary_versions.get(representation.vocabulary_id),
            "schema": representation.schema,
        }

    containers = sorted(
        (
            semantic_identity(candidate)
            for candidate in package.representations
            if representation_id in candidate.component_ids
        ),
        key=lambda item: str(item["representation_id"]),
    )
    return {
        "binding_profile": COMPONENT_BINDING_PROFILE,
        "object": {
            "object_id": owner.object_id,
            "object_type": owner.object_type,
            "vocabulary_id": owner.vocabulary_id,
            "vocabulary_version": vocabulary_versions.get(owner.vocabulary_id),
        },
        "component": semantic_identity(component),
        "containing_expressions": containers,
    }


def component_binding_bytes(
    package: PortableInstitutionalPackage,
    representation_id: str,
) -> bytes:
    """Encode the component binding deterministically for use as external AAD."""

    mapping = component_binding_mapping(package, representation_id)
    return (
        json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
