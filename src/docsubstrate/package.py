"""Minimal Portable Institutional Package model.

This module is deliberately an interchange envelope, not a universal ontology.
It binds stable institutional identities, typed relations, representations,
material artifacts, resources, vocabularies, profiles/capabilities, declared
preservation claims, and opaque extension envelopes without teaching the core
domain meanings such as invoice, approval, evidence, authority, or clinical
statement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from docsubstrate.durable import PreservationClaim
from docsubstrate.occurrence import OccurrenceRecord
from docsubstrate.preflight import PreflightIssue, PreflightResult
from docsubstrate.resource_catalog import ResourceCatalog
from docsubstrate.resources import ResourceDescriptor


@dataclass(frozen=True, slots=True)
class VocabularyRef:
    vocabulary_id: str
    version: str | None = None
    resource_key: str | None = None


@dataclass(frozen=True, slots=True)
class PackageObject:
    """Stable institutional identity carried by the package.

    Domain-specific descriptive claims intentionally do not live here as an
    untyped key/value escape hatch. They belong in declared vocabularies,
    typed relations, or provenance-bearing interchange metadata.
    """

    object_id: str
    object_type: str
    vocabulary_id: str | None = None


@dataclass(frozen=True, slots=True)
class PackageRelation:
    relation_id: str
    source_id: str
    predicate: str
    target_id: str
    vocabulary_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExternalReference:
    """Declared identity stub for an entity intentionally outside the package.

    The stub makes a broken or temporarily unavailable target explicit without
    copying the target graph or pretending that a locator owns its identity.
    """

    reference_id: str
    entity_type: str
    vocabulary_id: str | None = None


@dataclass(frozen=True, slots=True)
class PackageRepresentation:
    """One expression/representation of an institutional object."""

    representation_id: str
    object_id: str
    representation_type: str
    vocabulary_id: str | None = None
    schema: str | None = None
    version: str | None = None
    resource_keys: Sequence[str] = field(default_factory=tuple)
    component_ids: Sequence[str] = field(default_factory=tuple)
    protection_mode: Literal["clear", "encrypted"] = "clear"
    protection_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProtectionDescriptor:
    """Cryptographic posture for one encrypted semantic component.

    The descriptor binds ciphertext to a Representation but delegates the
    cryptographic encoding to a named external profile. It contains no key and
    grants no authority. ``binding_profile`` identifies the AAD/manifest
    canonicalization contract used to bind institutional identity to ciphertext.
    """

    protection_id: str
    representation_id: str
    ciphertext_resource_key: str
    encryption_profile: str
    binding_profile: str


@dataclass(frozen=True, slots=True)
class KeyEnvelope:
    """One independently replaceable access path to a component content key.

    Several envelopes may reference the same protection descriptor. Recipient
    and wrapping-key references identify the intended key domain; they are not
    an authorization decision or durable authority assertion.
    """

    envelope_id: str
    protection_id: str
    recipient_ref: str
    wrapping_key_ref: str
    key_management_profile: str
    resource_key: str
    version: str


@dataclass(frozen=True, slots=True)
class PackageArtifact:
    """Concrete material instance of a representation.

    The referenced ResourceDescriptor owns materialization and fixity metadata.
    An artifact therefore remains distinct from the abstract representation even
    when both happen to use the same media type.
    """

    artifact_id: str
    representation_id: str
    resource_key: str


@dataclass(frozen=True, slots=True)
class OpaqueExtension:
    """Transport envelope for an optional/future construct the core need not understand.

    The payload is always carried through a declared resource. ``capability``
    names the interpretation contract. Readers that do not implement a
    non-critical extension may preserve it opaquely; unknown critical extensions
    make full interpretation impossible and must never be silently reinterpreted.
    """

    extension_id: str
    extension_type: str
    capability: str
    resource_key: str
    version: str | None = None
    critical: bool = False
    metadata: Mapping[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PortableInstitutionalPackage:
    package_id: str
    format_version: str
    profile: str
    capabilities: frozenset[str] = frozenset()
    vocabularies: Sequence[VocabularyRef] = field(default_factory=tuple)
    objects: Sequence[PackageObject] = field(default_factory=tuple)
    external_references: Sequence[ExternalReference] = field(default_factory=tuple)
    relations: Sequence[PackageRelation] = field(default_factory=tuple)
    representations: Sequence[PackageRepresentation] = field(default_factory=tuple)
    protections: Sequence[ProtectionDescriptor] = field(default_factory=tuple)
    key_envelopes: Sequence[KeyEnvelope] = field(default_factory=tuple)
    artifacts: Sequence[PackageArtifact] = field(default_factory=tuple)
    occurrences: Sequence[OccurrenceRecord] = field(default_factory=tuple)
    resources: Sequence[ResourceDescriptor] = field(default_factory=tuple)
    preservation_claims: Sequence[PreservationClaim] = field(default_factory=tuple)
    extensions: Sequence[OpaqueExtension] = field(default_factory=tuple)

    def resource_catalog(self) -> ResourceCatalog:
        catalog = ResourceCatalog()
        for resource in self.resources:
            catalog.add(resource)
        return catalog

    def validate_structure(self) -> PreflightResult:
        """Validate package graph integrity without interpreting domain meaning."""

        issues: list[PreflightIssue] = []

        def index_unique(items, key, kind: str):
            result = {}
            for item in items:
                value = key(item)
                if value in result:
                    issues.append(
                        PreflightIssue(
                            code="package-duplicate-id",
                            message=f"duplicate {kind} id: {value}",
                            details={"kind": kind, "id": value},
                        )
                    )
                else:
                    result[value] = item
            return result

        vocabulary_by_id = index_unique(
            self.vocabularies, lambda item: item.vocabulary_id, "vocabulary"
        )
        object_by_id = index_unique(self.objects, lambda item: item.object_id, "object")
        external_by_id = index_unique(
            self.external_references, lambda item: item.reference_id, "external-reference"
        )
        relation_by_id = index_unique(
            self.relations, lambda item: item.relation_id, "relation"
        )
        representation_by_id = index_unique(
            self.representations, lambda item: item.representation_id, "representation"
        )
        protection_by_id = index_unique(
            self.protections, lambda item: item.protection_id, "protection"
        )
        envelope_by_id = index_unique(
            self.key_envelopes, lambda item: item.envelope_id, "key-envelope"
        )
        artifact_by_id = index_unique(self.artifacts, lambda item: item.artifact_id, "artifact")
        occurrence_by_id = index_unique(
            self.occurrences, lambda item: item.occurrence_id, "occurrence"
        )
        extension_by_id = index_unique(self.extensions, lambda item: item.extension_id, "extension")

        try:
            catalog = self.resource_catalog()
        except ValueError as exc:
            issues.append(
                PreflightIssue(code="package-resource-collision", message=str(exc))
            )
            catalog = ResourceCatalog()

        declared_vocabularies = set(vocabulary_by_id)

        entity_ids = {
            self.package_id,
            *object_by_id,
            *external_by_id,
            *relation_by_id,
            *representation_by_id,
            *protection_by_id,
            *envelope_by_id,
            *artifact_by_id,
            *occurrence_by_id,
            *extension_by_id,
            *(item.resource_key for item in self.resources),
            *(item.claim_id for item in self.preservation_claims),
        }

        def require_vocabulary(vocabulary_id: str | None, owner: str) -> None:
            if vocabulary_id is not None and vocabulary_id not in declared_vocabularies:
                issues.append(
                    PreflightIssue(
                        code="package-vocabulary-undeclared",
                        message=f"undeclared vocabulary {vocabulary_id!r} used by {owner}",
                        details={"vocabulary_id": vocabulary_id, "owner": owner},
                    )
                )

        for vocabulary in self.vocabularies:
            if vocabulary.resource_key and catalog.get(vocabulary.resource_key) is None:
                issues.append(
                    PreflightIssue(
                        code="package-resource-missing",
                        message=f"vocabulary resource missing: {vocabulary.resource_key}",
                        details={"resource_key": vocabulary.resource_key},
                    )
                )

        for obj in self.objects:
            require_vocabulary(obj.vocabulary_id, f"object:{obj.object_id}")

        for reference in self.external_references:
            require_vocabulary(
                reference.vocabulary_id,
                f"external-reference:{reference.reference_id}",
            )

        for relation in self.relations:
            if relation.source_id not in entity_ids:
                issues.append(
                    PreflightIssue(
                        code="package-relation-source-missing",
                        message=f"relation source missing: {relation.source_id}",
                    )
                )
            if relation.target_id not in entity_ids:
                issues.append(
                    PreflightIssue(
                        code="package-relation-target-missing",
                        message=f"relation target missing: {relation.target_id}",
                    )
                )
            require_vocabulary(
                relation.vocabulary_id,
                f"relation:{relation.relation_id}",
            )

        for representation in self.representations:
            if representation.object_id not in object_by_id:
                issues.append(
                    PreflightIssue(
                        code="package-representation-object-missing",
                        message=f"representation object missing: {representation.object_id}",
                    )
                )
            require_vocabulary(
                representation.vocabulary_id,
                f"representation:{representation.representation_id}",
            )
            for resource_key in representation.resource_keys:
                if catalog.get(resource_key) is None:
                    issues.append(
                        PreflightIssue(
                            code="package-resource-missing",
                            message=f"representation resource missing: {resource_key}",
                            details={
                                "resource_key": resource_key,
                                "representation_id": representation.representation_id,
                            },
                        )
                    )
            for component_id in representation.component_ids:
                component = representation_by_id.get(component_id)
                if component is None:
                    issues.append(
                        PreflightIssue(
                            code="package-representation-component-missing",
                            message=f"representation component missing: {component_id}",
                            details={
                                "representation_id": representation.representation_id,
                                "component_id": component_id,
                            },
                        )
                    )
                elif component.object_id != representation.object_id:
                    issues.append(
                        PreflightIssue(
                            code="package-representation-component-object-mismatch",
                            message=(
                                f"representation component {component_id!r} belongs to a "
                                "different institutional object"
                            ),
                            details={
                                "representation_id": representation.representation_id,
                                "component_id": component_id,
                            },
                        )
                    )
            if representation.protection_mode not in {"clear", "encrypted"}:
                issues.append(
                    PreflightIssue(
                        code="package-representation-protection-mode-invalid",
                        message=(
                            "representation protection mode must be clear or encrypted: "
                            f"{representation.representation_id}"
                        ),
                    )
                )
            if representation.protection_mode == "clear" and representation.protection_id:
                issues.append(
                    PreflightIssue(
                        code="package-clear-representation-has-protection",
                        message=(
                            "clear representation cannot reference an encryption descriptor: "
                            f"{representation.representation_id}"
                        ),
                    )
                )
            if representation.protection_mode == "encrypted" and not representation.protection_id:
                issues.append(
                    PreflightIssue(
                        code="package-encrypted-representation-protection-missing",
                        message=(
                            "encrypted representation has no protection descriptor: "
                            f"{representation.representation_id}"
                        ),
                    )
                )
            elif (
                representation.protection_mode == "encrypted"
                and representation.protection_id not in protection_by_id
            ):
                issues.append(
                    PreflightIssue(
                        code="package-representation-protection-missing",
                        message=(
                            "representation references missing protection descriptor: "
                            f"{representation.protection_id}"
                        ),
                    )
                )
            elif (
                representation.protection_mode == "encrypted"
                and protection_by_id[representation.protection_id].representation_id
                != representation.representation_id
            ):
                issues.append(
                    PreflightIssue(
                        code="package-representation-protection-mismatch",
                        message=(
                            f"representation {representation.representation_id!r} references "
                            "a protection descriptor bound to a different representation: "
                            f"{representation.protection_id}"
                        ),
                    )
                )

        for protection in self.protections:
            representation = representation_by_id.get(protection.representation_id)
            if representation is None:
                issues.append(
                    PreflightIssue(
                        code="package-protection-representation-missing",
                        message=(
                            "protection descriptor references missing representation: "
                            f"{protection.representation_id}"
                        ),
                    )
                )
            elif representation.protection_id != protection.protection_id:
                issues.append(
                    PreflightIssue(
                        code="package-protection-binding-mismatch",
                        message=(
                            f"protection {protection.protection_id!r} is not selected by "
                            f"representation {protection.representation_id!r}"
                        ),
                    )
                )
            if catalog.get(protection.ciphertext_resource_key) is None:
                issues.append(
                    PreflightIssue(
                        code="package-protection-ciphertext-missing",
                        message=(
                            "protection descriptor references missing ciphertext resource: "
                            f"{protection.ciphertext_resource_key}"
                        ),
                    )
                )
            elif representation is not None and (
                protection.ciphertext_resource_key not in representation.resource_keys
            ):
                issues.append(
                    PreflightIssue(
                        code="package-protection-ciphertext-unowned",
                        message=(
                            f"ciphertext {protection.ciphertext_resource_key!r} is not owned by "
                            f"representation {protection.representation_id!r}"
                        ),
                    )
                )

        for envelope in self.key_envelopes:
            if envelope.protection_id not in protection_by_id:
                issues.append(
                    PreflightIssue(
                        code="package-key-envelope-protection-missing",
                        message=(
                            "key envelope references missing protection descriptor: "
                            f"{envelope.protection_id}"
                        ),
                    )
                )
            for reference, role in (
                (envelope.recipient_ref, "recipient"),
                (envelope.wrapping_key_ref, "wrapping-key"),
            ):
                if reference not in entity_ids:
                    issues.append(
                        PreflightIssue(
                            code="package-key-envelope-reference-missing",
                            message=f"key envelope {role} reference is missing: {reference}",
                            details={"envelope_id": envelope.envelope_id, "role": role},
                        )
                    )
            resource = catalog.get(envelope.resource_key)
            if resource is None:
                issues.append(
                    PreflightIssue(
                        code="package-key-envelope-resource-missing",
                        message=f"key envelope resource missing: {envelope.resource_key}",
                    )
                )
            elif resource.materialization is None or resource.materialization.integrity is None:
                issues.append(
                    PreflightIssue(
                        code="package-key-envelope-fixity-missing",
                        message=f"key envelope lacks fixity: {envelope.resource_key}",
                    )
                )

        for artifact in self.artifacts:
            if artifact.representation_id not in representation_by_id:
                issues.append(
                    PreflightIssue(
                        code="package-artifact-representation-missing",
                        message=f"artifact representation missing: {artifact.representation_id}",
                    )
                )
            resource = catalog.get(artifact.resource_key)
            if resource is None:
                issues.append(
                    PreflightIssue(
                        code="package-artifact-resource-missing",
                        message=f"artifact resource missing: {artifact.resource_key}",
                    )
                )
            elif resource.materialization is None or resource.materialization.kind == "derived":
                issues.append(
                    PreflightIssue(
                        code="package-artifact-not-material",
                        message=(
                            "artifact must reference embedded/external materialization: "
                            f"{artifact.resource_key}"
                        ),
                    )
                )
            elif resource.materialization.integrity is None:
                issues.append(
                    PreflightIssue(
                        code="package-artifact-fixity-missing",
                        message=f"artifact lacks fixity: {artifact.resource_key}",
                    )
                )

        for occurrence in self.occurrences:
            require_vocabulary(
                occurrence.vocabulary_id,
                f"occurrence:{occurrence.occurrence_id}",
            )
            refs = (
                *occurrence.input_refs,
                *occurrence.output_refs,
                *occurrence.source_refs,
                *((occurrence.actor_ref,) if occurrence.actor_ref else ()),
                *((occurrence.action_ref,) if occurrence.action_ref else ()),
            )
            for reference in refs:
                if reference not in entity_ids:
                    issues.append(
                        PreflightIssue(
                            code="package-occurrence-reference-missing",
                            message=(
                                f"occurrence {occurrence.occurrence_id!r} references "
                                f"undeclared entity: {reference}"
                            ),
                            details={
                                "occurrence_id": occurrence.occurrence_id,
                                "reference": reference,
                            },
                        )
                    )
        for claim in self.preservation_claims:
            for root_ref in claim.root_refs:
                if root_ref not in entity_ids:
                    issues.append(
                        PreflightIssue(
                            code="package-claim-root-missing",
                            message=(
                                f"preservation claim {claim.claim_id!r} references missing "
                                f"root entity: {root_ref}"
                            ),
                            details={"claim_id": claim.claim_id, "root_ref": root_ref},
                        )
                    )
            for requirement in claim.requirements:
                if catalog.get(requirement.resource_key) is None:
                    issues.append(
                        PreflightIssue(
                            code="package-claim-resource-missing",
                            message=(
                                f"preservation claim {claim.claim_id!r} references missing "
                                f"resource: {requirement.resource_key}"
                            ),
                            details={
                                "claim_id": claim.claim_id,
                                "resource_key": requirement.resource_key,
                            },
                        )
                    )
                if requirement.subject_ref and requirement.subject_ref not in entity_ids:
                    issues.append(
                        PreflightIssue(
                            code="package-claim-subject-missing",
                            message=(
                                f"preservation claim {claim.claim_id!r} requirement references "
                                f"missing subject: {requirement.subject_ref}"
                            ),
                            details={
                                "claim_id": claim.claim_id,
                                "subject_ref": requirement.subject_ref,
                            },
                        )
                    )

        for extension in self.extensions:
            if extension.capability not in self.capabilities:
                issues.append(
                    PreflightIssue(
                        code="package-extension-capability-undeclared",
                        message=(
                            f"extension {extension.extension_id!r} uses undeclared capability: "
                            f"{extension.capability}"
                        ),
                        details={
                            "extension_id": extension.extension_id,
                            "capability": extension.capability,
                        },
                    )
                )
            if catalog.get(extension.resource_key) is None:
                issues.append(
                    PreflightIssue(
                        code="package-extension-resource-missing",
                        message=(
                            f"extension {extension.extension_id!r} references missing resource: "
                            f"{extension.resource_key}"
                        ),
                        details={
                            "extension_id": extension.extension_id,
                            "resource_key": extension.resource_key,
                        },
                    )
                )

        return PreflightResult(tuple(issues))
