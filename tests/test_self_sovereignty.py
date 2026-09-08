from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import replace
from pathlib import Path

from docsubstrate.durable import ClosureRequirement, PreservationClaim
from docsubstrate.interchange_json import MetadataAssertion, dumps_canonical, loads_mapping
from docsubstrate.occurrence import OccurrenceRecord
from docsubstrate.package import (
    ExternalReference,
    PackageArtifact,
    PackageObject,
    PackageRelation,
    PackageRepresentation,
    PortableInstitutionalPackage,
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


def _survivable_package() -> PortableInstitutionalPackage:
    resources = (
        _resource("resource:vocabulary", "vocabulary", b"commerce vocabulary v1"),
        _resource("resource:expression", "semantic-content", b'{"total":"100.00"}'),
        _resource("resource:artifact", "document-artifact", b"%PDF example"),
        _resource("resource:source", "source-basis", b"issued source record"),
    )
    return PortableInstitutionalPackage(
        package_id="package:invoice-1",
        format_version="0.1",
        profile="minimum-survivable-closure/0.1",
        vocabularies=(
            VocabularyRef(
                "vocab:commerce",
                version="1",
                resource_key="resource:vocabulary",
            ),
        ),
        objects=(
            PackageObject("object:invoice-1", "Invoice", "vocab:commerce"),
        ),
        external_references=(
            ExternalReference("object:purchase-order-9", "PurchaseOrder", "vocab:commerce"),
            ExternalReference("party:issuer", "Organization", "vocab:commerce"),
        ),
        relations=(
            PackageRelation(
                "relation:invoice-order",
                "object:invoice-1",
                "respondsTo",
                "object:purchase-order-9",
                "vocab:commerce",
            ),
        ),
        representations=(
            PackageRepresentation(
                "expression:invoice-1:v1",
                "object:invoice-1",
                "InvoiceExpression",
                vocabulary_id="vocab:commerce",
                schema="schema:invoice:1",
                version="1",
                resource_keys=("resource:expression",),
            ),
        ),
        artifacts=(
            PackageArtifact(
                "artifact:invoice-1:v1:pdf",
                "expression:invoice-1:v1",
                "resource:artifact",
            ),
        ),
        occurrences=(
            OccurrenceRecord(
                occurrence_id="occurrence:issued-1",
                occurrence_type="issued",
                outcome="succeeded",
                basis="asserted",
                input_refs=("expression:invoice-1:v1",),
                output_refs=("artifact:invoice-1:v1:pdf",),
                source_refs=("resource:source",),
                actor_ref="party:issuer",
                occurred_at="2026-09-01T00:00:00Z",
                vocabulary_id="vocab:commerce",
            ),
        ),
        resources=resources,
        preservation_claims=(
            PreservationClaim(
                claim_id="claim:invoice-1",
                roles=frozenset({"interpretation", "evidentiary", "verification"}),
                requirements=(
                    ClosureRequirement(
                        "resource:vocabulary",
                        "interpretation",
                        subject_ref="object:invoice-1",
                    ),
                    ClosureRequirement(
                        "resource:expression",
                        "interpretation",
                        subject_ref="expression:invoice-1:v1",
                    ),
                    ClosureRequirement(
                        "resource:artifact",
                        "verification",
                        subject_ref="artifact:invoice-1:v1:pdf",
                    ),
                    ClosureRequirement(
                        "resource:source",
                        "evidentiary",
                        subject_ref="occurrence:issued-1",
                    ),
                ),
                root_refs=(
                    "object:invoice-1",
                    "expression:invoice-1:v1",
                    "relation:invoice-order",
                    "artifact:invoice-1:v1:pdf",
                    "occurrence:issued-1",
                ),
            ),
        ),
    )


def test_detached_entity_test() -> None:
    package = _survivable_package()
    assert validate_minimum_survivable_closure(package).ok


def test_kill_runtime_test() -> None:
    envelope = loads_mapping(dumps_canonical(_survivable_package()))
    assert envelope["package"]["package_id"] == "package:invoice-1"
    assert envelope["occurrences"][0]["occurrence_id"] == "occurrence:issued-1"


def test_kill_database_test() -> None:
    package = _survivable_package()
    assert not hasattr(package, "database_id")
    assert validate_minimum_survivable_closure(package).ok


def test_broken_reference_test() -> None:
    package = _survivable_package()
    assert package.external_references[0].reference_id == "object:purchase-order-9"
    assert package.validate_structure().ok
    assert validate_minimum_survivable_closure(package).ok


def test_vocabulary_survival_test() -> None:
    package = _survivable_package()
    broken = replace(package, vocabularies=(VocabularyRef("vocab:commerce"),))
    codes = {issue.code for issue in validate_minimum_survivable_closure(broken).errors}
    assert "survivability-vocabulary-version-missing" in codes
    assert "survivability-vocabulary-preservation-missing" in codes


def test_artifact_correspondence_test() -> None:
    package = _survivable_package()
    broken = replace(
        package,
        artifacts=(PackageArtifact("artifact:broken", "expression:missing", "resource:artifact"),),
    )
    codes = {issue.code for issue in validate_minimum_survivable_closure(broken).errors}
    assert "package-artifact-representation-missing" in codes


def test_no_hidden_status_test() -> None:
    package = _survivable_package()
    encoded = dumps_canonical(package)
    assert b'"status"' not in encoded
    assert validate_minimum_survivable_closure(package).ok


def test_independent_reader_test() -> None:
    reader_path = Path(__file__).parents[1] / "tools" / "independent_reader.py"
    spec = importlib.util.spec_from_file_location("independent_reader_self_sovereignty", reader_path)
    assert spec and spec.loader
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    summary = reader.summarize(loads_mapping(dumps_canonical(_survivable_package())))
    assert summary["package_id"] == "package:invoice-1"
    assert summary["occurrence_count"] == 1


def test_minimality_test() -> None:
    package = _survivable_package()
    expression = replace(package.representations[0], version=None)
    broken = replace(package, representations=(expression,))
    codes = {issue.code for issue in validate_minimum_survivable_closure(broken).errors}
    assert codes == {"survivability-representation-version-missing"}


def test_composition_test() -> None:
    package = _survivable_package()
    metadata = (
        MetadataAssertion(
            metadata_id="metadata:relation-basis",
            subject_kind="relation",
            subject_id="relation:invoice-order",
            key="basis",
            value="purchase-order-reference",
            basis="asserted",
            vocabulary_id="vocab:commerce",
            source_refs=("resource:source",),
        ),
    )
    assert validate_minimum_survivable_closure(
        package,
        metadata_assertions=metadata,
    ).ok


def test_resource_only_claim_cannot_masquerade_as_entity_survivability() -> None:
    package = PortableInstitutionalPackage(
        package_id="package:resource-only",
        format_version="0.1",
        profile="minimum-survivable-closure/0.1",
        resources=(_resource("resource:only", "opaque", b"bytes"),),
        preservation_claims=(
            PreservationClaim(
                "claim:resource-only",
                frozenset({"interpretation"}),
                (ClosureRequirement("resource:only", "interpretation"),),
            ),
        ),
    )
    codes = {issue.code for issue in validate_minimum_survivable_closure(package).errors}
    assert "survivability-claim-root-missing" in codes
    assert "survivability-requirement-subject-missing" in codes
