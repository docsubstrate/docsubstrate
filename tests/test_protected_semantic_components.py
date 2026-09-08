from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import fields, replace
from pathlib import Path

from docsubstrate.component_protection import component_binding_bytes
from docsubstrate.durable import ClosureRequirement, PreservationClaim
from docsubstrate.interchange_json import dumps_canonical, loads_mapping
from docsubstrate.migration import semantic_projection
from docsubstrate.package import (
    ExternalReference,
    KeyEnvelope,
    PackageObject,
    PackageRepresentation,
    PortableInstitutionalPackage,
    ProtectionDescriptor,
    VocabularyRef,
)
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor
from docsubstrate.self_sovereignty import validate_minimum_survivable_closure


def _resource(key: str, resource_type: str, payload: bytes) -> ResourceDescriptor:
    return ResourceDescriptor(
        resource_key=key,
        resource_type=resource_type,
        materialization=MaterializationRef(
            kind="embedded",
            length=len(payload),
            integrity=IntegrityDigest("sha256", hashlib.sha256(payload).hexdigest()),
        ),
    )


def _protected_package() -> PortableInstitutionalPackage:
    resources = (
        _resource("resource:vocabulary", "vocabulary", b"commerce vocabulary v1"),
        _resource("resource:public", "semantic-content", b'{"invoice":"INV-1"}'),
        _resource("resource:accounting-ciphertext", "ciphertext", b"ciphertext"),
        _resource("resource:finance-envelope", "key-envelope", b"wrapped CEK for finance"),
        _resource("resource:recovery-envelope", "key-envelope", b"wrapped CEK for recovery"),
    )
    representations = (
        PackageRepresentation(
            "expression:invoice:v1",
            "object:invoice",
            "InvoiceExpression",
            vocabulary_id="vocab:commerce",
            version="1",
            component_ids=("component:public", "component:accounting"),
        ),
        PackageRepresentation(
            "component:public",
            "object:invoice",
            "PublicComponent",
            vocabulary_id="vocab:commerce",
            version="1",
            resource_keys=("resource:public",),
            protection_mode="clear",
        ),
        PackageRepresentation(
            "component:accounting",
            "object:invoice",
            "OpaqueProtectedComponent",
            vocabulary_id="vocab:commerce",
            version="1",
            resource_keys=("resource:accounting-ciphertext",),
            protection_mode="encrypted",
            protection_id="protection:accounting",
        ),
    )
    return PortableInstitutionalPackage(
        package_id="package:invoice",
        format_version="0.1",
        profile="minimum-survivable-closure/0.1",
        vocabularies=(
            VocabularyRef("vocab:commerce", "1", "resource:vocabulary"),
        ),
        objects=(PackageObject("object:invoice", "Invoice", "vocab:commerce"),),
        external_references=(
            ExternalReference("key-domain:finance", "KeyDomain", "vocab:commerce"),
            ExternalReference("key:finance-kek", "WrappingKey", "vocab:commerce"),
            ExternalReference("key-domain:recovery", "KeyDomain", "vocab:commerce"),
            ExternalReference("key:recovery-kek", "WrappingKey", "vocab:commerce"),
        ),
        representations=representations,
        protections=(
            ProtectionDescriptor(
                "protection:accounting",
                "component:accounting",
                "resource:accounting-ciphertext",
                "urn:ietf:params:jose:jwe",
                "docsubstrate.semantic-component-binding/0.1",
            ),
        ),
        key_envelopes=(
            KeyEnvelope(
                "envelope:finance",
                "protection:accounting",
                "key-domain:finance",
                "key:finance-kek",
                "urn:ietf:params:jose:jwe",
                "resource:finance-envelope",
                "1",
            ),
            KeyEnvelope(
                "envelope:recovery",
                "protection:accounting",
                "key-domain:recovery",
                "key:recovery-kek",
                "urn:ietf:params:cose:encrypt",
                "resource:recovery-envelope",
                "1",
            ),
        ),
        resources=resources,
        preservation_claims=(
            PreservationClaim(
                "claim:invoice",
                frozenset({"interpretation", "verification"}),
                tuple(
                    ClosureRequirement(
                        resource.resource_key,
                        "interpretation",
                        subject_ref=subject_ref,
                    )
                    for resource, subject_ref in (
                        (resources[0], "object:invoice"),
                        (resources[1], "component:public"),
                        (resources[2], "component:accounting"),
                        (resources[3], "component:accounting"),
                        (resources[4], "component:accounting"),
                    )
                ),
                root_refs=(
                    "object:invoice",
                    "expression:invoice:v1",
                    "component:public",
                    "component:accounting",
                ),
            ),
        ),
    )


def test_parallel_clear_and_encrypted_components_with_multiple_envelopes() -> None:
    package = _protected_package()
    assert validate_minimum_survivable_closure(package).ok
    accounting_envelopes = [
        item for item in package.key_envelopes
        if item.protection_id == "protection:accounting"
    ]
    assert len(accounting_envelopes) == 2


def test_envelope_change_does_not_change_expression_semantics() -> None:
    package = _protected_package()
    changed_access = replace(package, key_envelopes=package.key_envelopes[1:])
    assert semantic_projection(package) == semantic_projection(changed_access)
    assert component_binding_bytes(package, "component:accounting") == (
        component_binding_bytes(changed_access, "component:accounting")
    )


def test_component_binding_changes_with_expression_version() -> None:
    package = _protected_package()
    changed_expression = replace(package.representations[0], version="2")
    changed = replace(
        package,
        representations=(changed_expression, *package.representations[1:]),
    )
    assert component_binding_bytes(package, "component:accounting") != (
        component_binding_bytes(changed, "component:accounting")
    )


def test_independent_reader_reconstructs_identical_component_binding() -> None:
    reader_path = Path(__file__).parents[1] / "tools" / "independent_reader.py"
    spec = importlib.util.spec_from_file_location("independent_protection_reader", reader_path)
    assert spec and spec.loader
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)

    package = _protected_package()
    envelope = loads_mapping(dumps_canonical(package))

    assert reader.component_binding_bytes(envelope, "component:accounting") == (
        component_binding_bytes(package, "component:accounting")
    )


def test_encrypted_component_requires_at_least_one_access_or_recovery_path() -> None:
    package = replace(_protected_package(), key_envelopes=())
    codes = {issue.code for issue in validate_minimum_survivable_closure(package).errors}
    assert "survivability-key-envelope-missing" in codes


def test_protection_descriptor_cannot_be_reused_by_another_component() -> None:
    package = _protected_package()
    alias = replace(
        package.representations[2],
        representation_id="component:accounting-alias",
    )
    broken = replace(package, representations=(*package.representations, alias))

    codes = {issue.code for issue in broken.validate_structure().errors}

    assert "package-representation-protection-mismatch" in codes


def test_encrypted_component_cannot_hide_a_nested_component_graph() -> None:
    package = _protected_package()
    accounting = replace(
        package.representations[2],
        component_ids=("component:public",),
    )
    broken = replace(
        package,
        representations=(*package.representations[:2], accounting),
    )
    codes = {issue.code for issue in validate_minimum_survivable_closure(broken).errors}
    assert "survivability-encrypted-composition-not-flat" in codes


def test_public_manifest_exposes_posture_and_ciphertext_fixity_without_keys() -> None:
    mapping = loads_mapping(dumps_canonical(_protected_package()))
    assert mapping["encoding"]["version"] == "0.3"
    accounting = next(
        item for item in mapping["package"]["representations"]
        if item["representation_id"] == "component:accounting"
    )
    assert accounting["protection_mode"] == "encrypted"
    assert mapping["package"]["protections"][0]["ciphertext_resource_key"] == (
        "resource:accounting-ciphertext"
    )
    assert "content_key" not in dumps_canonical(_protected_package()).decode()


def test_key_envelope_is_not_an_authority_or_grant_record() -> None:
    envelope_fields = {item.name for item in fields(KeyEnvelope)}
    assert "authority" not in envelope_fields
    assert "grant" not in envelope_fields
    assert {"recipient_ref", "wrapping_key_ref", "key_management_profile"} <= envelope_fields
