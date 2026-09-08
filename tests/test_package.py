from __future__ import annotations

from dataclasses import fields

from docsubstrate.durable import ClosureRequirement, PreservationClaim
from docsubstrate.package import (
    PackageArtifact,
    PackageObject,
    PackageRelation,
    PackageRepresentation,
    PortableInstitutionalPackage,
    VocabularyRef,
)
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor


def _pdf_resource(key: str = "artifact:quote-pdf") -> ResourceDescriptor:
    return ResourceDescriptor(
        resource_key=key,
        resource_type="artifact",
        media_type="application/pdf",
        materialization=MaterializationRef(
            kind="embedded",
            locator=f"artifacts/{key.split(':')[-1]}.pdf",
            media_type="application/pdf",
            integrity=IntegrityDigest("sha256", "abc123"),
        ),
    )


def test_object_and_relation_do_not_expose_untyped_attribute_escape_hatches() -> None:
    assert [field.name for field in fields(PackageObject)] == [
        "object_id",
        "object_type",
        "vocabulary_id",
    ]
    assert [field.name for field in fields(PackageRelation)] == [
        "relation_id",
        "source_id",
        "predicate",
        "target_id",
        "vocabulary_id",
    ]


def test_minimal_package_validates_without_domain_primitives() -> None:
    package = PortableInstitutionalPackage(
        package_id="pkg-001",
        format_version="0.1",
        profile="general",
        capabilities=frozenset({"relations.typed", "artifacts.fixity"}),
        vocabularies=(VocabularyRef("commerce", version="1"),),
        objects=(
            PackageObject("quote-001", "Quotation", vocabulary_id="commerce"),
            PackageObject("customer-001", "Customer", vocabulary_id="commerce"),
        ),
        relations=(
            PackageRelation(
                "relation:quote-customer",
                "quote-001",
                "customer",
                "customer-001",
                vocabulary_id="commerce",
            ),
        ),
        representations=(
            PackageRepresentation(
                "quote-001:pdf",
                "quote-001",
                "document/pdf",
                resource_keys=("artifact:quote-pdf",),
            ),
        ),
        artifacts=(
            PackageArtifact("quote-001:pdf:artifact", "quote-001:pdf", "artifact:quote-pdf"),
        ),
        resources=(_pdf_resource(),),
        preservation_claims=(
            PreservationClaim(
                "claim-meaning",
                frozenset({"interpretation"}),
                (ClosureRequirement("artifact:quote-pdf", "interpretation"),),
            ),
        ),
    )

    assert package.validate_structure().ok


def test_package_rejects_undeclared_vocabulary_and_broken_relation() -> None:
    package = PortableInstitutionalPackage(
        package_id="pkg-002",
        format_version="0.1",
        profile="general",
        objects=(PackageObject("doc-1", "CourtDocument", vocabulary_id="legal"),),
        relations=(PackageRelation("relation:broken", "doc-1", "relatesTo", "missing"),),
    )

    result = package.validate_structure()

    assert not result.ok
    assert {issue.code for issue in result.errors} == {
        "package-vocabulary-undeclared",
        "package-relation-target-missing",
    }


def test_artifact_requires_material_identity_and_fixity() -> None:
    derived = ResourceDescriptor(
        resource_key="render:qr",
        resource_type="derived-render",
        media_type="image/png",
        materialization=MaterializationRef(kind="derived"),
    )
    package = PortableInstitutionalPackage(
        package_id="pkg-003",
        format_version="0.1",
        profile="general",
        objects=(PackageObject("doc-1", "Document"),),
        representations=(PackageRepresentation("rep-1", "doc-1", "qr-preview"),),
        artifacts=(PackageArtifact("artifact-1", "rep-1", "render:qr"),),
        resources=(derived,),
    )

    result = package.validate_structure()

    assert not result.ok
    assert [issue.code for issue in result.errors] == ["package-artifact-not-material"]


def test_claim_cannot_reference_resource_absent_from_package_catalog() -> None:
    package = PortableInstitutionalPackage(
        package_id="pkg-004",
        format_version="0.1",
        profile="durable",
        preservation_claims=(
            PreservationClaim(
                "claim-evidence",
                frozenset({"evidentiary"}),
                (ClosureRequirement("evidence:missing", "evidentiary"),),
            ),
        ),
    )

    result = package.validate_structure()

    assert not result.ok
    assert [issue.code for issue in result.errors] == ["package-claim-resource-missing"]
