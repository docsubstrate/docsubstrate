from __future__ import annotations

from dataclasses import dataclass

from docsubstrate.durable import (
    ClosureRequirement,
    PreservationClaim,
    ResolutionProbe,
    validate_durable_closure,
)
from docsubstrate.resource_catalog import ResourceCatalog
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor


def _catalog(*resources: ResourceDescriptor) -> ResourceCatalog:
    catalog = ResourceCatalog()
    for resource in resources:
        catalog.add(resource)
    return catalog


def test_embedded_integrity_closes_declared_interpretation_dependency() -> None:
    vocabulary = ResourceDescriptor(
        resource_key="vocab:legal-v1",
        resource_type="vocabulary",
        media_type="application/ld+json",
        materialization=MaterializationRef(
            kind="embedded",
            locator="vocab/legal-v1.jsonld",
            integrity=IntegrityDigest("sha256", "abc123"),
        ),
    )
    claim = PreservationClaim(
        claim_id="court-order-meaning",
        roles=frozenset({"interpretation"}),
        requirements=(ClosureRequirement("vocab:legal-v1", "interpretation"),),
    )

    report = validate_durable_closure(claim, _catalog(vocabulary))

    assert report.ok
    assert report.satisfied_roles == frozenset({"interpretation"})
    assert not report.unsatisfied_roles


@dataclass
class ImmutableResolver:
    name: str = "cas"

    def probe(self, resource: ResourceDescriptor) -> ResolutionProbe:
        return ResolutionProbe(
            resolvable=True,
            immutable=True,
            integrity_verified=True,
            media_type=resource.media_type,
        )


def test_external_content_addressed_resource_can_close_without_embedding() -> None:
    evidence = ResourceDescriptor(
        resource_key="artifact:evidence-1",
        resource_type="artifact",
        media_type="application/pdf",
        materialization=MaterializationRef(
            kind="external",
            locator="sha256:deadbeef",
            resolver="cas",
            integrity=IntegrityDigest("sha256", "deadbeef"),
        ),
    )
    claim = PreservationClaim(
        claim_id="evidence-preserved",
        roles=frozenset({"evidentiary"}),
        requirements=(ClosureRequirement("artifact:evidence-1", "evidentiary"),),
    )

    report = validate_durable_closure(
        claim,
        _catalog(evidence),
        resolvers={"cas": ImmutableResolver()},
    )

    assert report.ok
    assert report.satisfied_roles == frozenset({"evidentiary"})


def test_external_runtime_reference_without_resolver_fails_durable_closure() -> None:
    font = ResourceDescriptor(
        resource_key="font:noto",
        resource_type="font",
        media_type="font/otf",
        materialization=MaterializationRef(
            kind="external",
            locator="/usr/share/fonts/noto.otf",
            resolver="filesystem",
        ),
    )
    claim = PreservationClaim(
        claim_id="reproduce-page",
        roles=frozenset({"reproduction"}),
        requirements=(ClosureRequirement("font:noto", "reproduction"),),
    )

    report = validate_durable_closure(claim, _catalog(font))

    assert not report.ok
    assert report.unsatisfied_roles == frozenset({"reproduction"})
    assert [issue.code for issue in report.preflight.errors] == ["durable-resolver-missing"]


def test_derived_qr_bitmap_does_not_close_dependency_by_itself() -> None:
    qr_bitmap = ResourceDescriptor(
        resource_key="derived:qr-bitmap",
        resource_type="image",
        media_type="image/png",
        materialization=MaterializationRef(kind="derived"),
    )
    claim = PreservationClaim(
        claim_id="qr-reproduction",
        roles=frozenset({"reproduction"}),
        requirements=(ClosureRequirement("derived:qr-bitmap", "reproduction"),),
    )

    report = validate_durable_closure(claim, _catalog(qr_bitmap))

    assert not report.ok
    assert report.preflight.errors[0].code == "derived-resource-not-closure"


def test_claim_can_be_durable_for_meaning_without_claiming_reproduction() -> None:
    vocabulary = ResourceDescriptor(
        resource_key="vocab:erp-v1",
        resource_type="vocabulary",
        materialization=MaterializationRef(
            kind="embedded",
            integrity=IntegrityDigest("sha256", "123"),
        ),
    )
    missing_font_requirement = ClosureRequirement("font:missing", "reproduction")
    claim = PreservationClaim(
        claim_id="institutional-meaning-only",
        roles=frozenset({"interpretation"}),
        requirements=(
            ClosureRequirement("vocab:erp-v1", "interpretation"),
            missing_font_requirement,
        ),
    )

    report = validate_durable_closure(claim, _catalog(vocabulary))

    assert report.ok
    assert report.satisfied_roles == frozenset({"interpretation"})
