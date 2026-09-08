"""Minimum survivable closure conformance profile.

The package model stays permissive enough for general interchange experiments.
This module applies the stronger entity-rooted contract: a producer may claim
semantic survivability only when durable entities own enough local identity,
version, vocabulary, content, basis, and reference information to survive the
source runtime.  It deliberately does not define domain ontology or fetch data.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from docsubstrate.interchange_json import MetadataAssertion
from docsubstrate.package import PortableInstitutionalPackage
from docsubstrate.preflight import PreflightIssue, PreflightResult


def _issue(code: str, message: str, **details: str) -> PreflightIssue:
    return PreflightIssue(code=code, message=message, details=details)


def validate_minimum_survivable_closure(
    package: PortableInstitutionalPackage,
    *,
    metadata_assertions: Sequence[MetadataAssertion] = (),
) -> PreflightResult:
    """Validate the strong, entity-rooted survivability profile.

    This does not replace structural, domain, cryptographic, or resolver
    validation.  It detects hidden semantic dependencies that the permissive
    package structure intentionally cannot reject.
    """

    issues = list(package.validate_structure().issues)

    internal_by_kind = {
        "package": {package.package_id},
        "object": {item.object_id for item in package.objects},
        "relation": {item.relation_id for item in package.relations},
        "representation": {item.representation_id for item in package.representations},
        "protection": {item.protection_id for item in package.protections},
        "key-envelope": {item.envelope_id for item in package.key_envelopes},
        "artifact": {item.artifact_id for item in package.artifacts},
        "resource": {item.resource_key for item in package.resources},
        "extension": {item.extension_id for item in package.extensions},
        "preservation-claim": {item.claim_id for item in package.preservation_claims},
        "occurrence": {item.occurrence_id for item in package.occurrences},
    }
    internal_ids = set().union(*internal_by_kind.values())
    external_ids = {item.reference_id for item in package.external_references}
    declared_ids = internal_ids | external_ids

    durable_entity_ids = set().union(
        internal_by_kind["object"],
        internal_by_kind["relation"],
        internal_by_kind["representation"],
        internal_by_kind["artifact"],
        internal_by_kind["occurrence"],
    )
    claimed_roots = {
        root_ref
        for claim in package.preservation_claims
        for root_ref in claim.root_refs
    }
    if durable_entity_ids and not package.preservation_claims:
        issues.append(
            _issue(
                "survivability-preservation-claim-missing",
                "package contains durable entities but declares no preservation claim",
            )
        )
    for entity_id in sorted(durable_entity_ids - claimed_roots):
        issues.append(
            _issue(
                "survivability-entity-root-unclaimed",
                f"durable entity is not owned by any preservation claim: {entity_id}",
                entity_id=entity_id,
            )
        )

    identity_counts = Counter(
        entity_id
        for ids in internal_by_kind.values()
        for entity_id in ids
    )
    identity_counts.update(external_ids)
    for entity_id, count in identity_counts.items():
        if count > 1:
            issues.append(
                _issue(
                    "survivability-ambiguous-entity-id",
                    f"entity id is reused across package entity kinds: {entity_id}",
                    entity_id=entity_id,
                )
            )

    used_vocabularies = {
        vocabulary_id
        for vocabulary_id in (
            *(item.vocabulary_id for item in package.objects),
            *(item.vocabulary_id for item in package.external_references),
            *(item.vocabulary_id for item in package.relations),
            *(item.vocabulary_id for item in package.representations),
            *(item.vocabulary_id for item in package.occurrences),
            *(item.vocabulary_id for item in metadata_assertions),
        )
        if vocabulary_id is not None
    }
    vocabulary_by_id = {item.vocabulary_id: item for item in package.vocabularies}
    resource_by_key = {item.resource_key: item for item in package.resources}
    representation_by_id = {
        item.representation_id: item for item in package.representations
    }
    protection_by_id = {item.protection_id: item for item in package.protections}
    envelopes_by_protection: dict[str, list[object]] = {}
    for envelope in package.key_envelopes:
        envelopes_by_protection.setdefault(envelope.protection_id, []).append(envelope)
    for vocabulary_id in sorted(used_vocabularies):
        vocabulary = vocabulary_by_id.get(vocabulary_id)
        if vocabulary is None:
            continue  # structural validation already owns this error
        if not vocabulary.version:
            issues.append(
                _issue(
                    "survivability-vocabulary-version-missing",
                    f"used vocabulary has no durable version: {vocabulary_id}",
                    vocabulary_id=vocabulary_id,
                )
            )
        if not vocabulary.resource_key:
            issues.append(
                _issue(
                    "survivability-vocabulary-preservation-missing",
                    f"used vocabulary has no preserved resource: {vocabulary_id}",
                    vocabulary_id=vocabulary_id,
                )
            )
        elif vocabulary.resource_key in resource_by_key:
            materialization = resource_by_key[vocabulary.resource_key].materialization
            if materialization is None or materialization.integrity is None:
                issues.append(
                    _issue(
                        "survivability-vocabulary-integrity-missing",
                        f"vocabulary resource lacks fixity: {vocabulary.resource_key}",
                        vocabulary_id=vocabulary_id,
                        resource_key=vocabulary.resource_key,
                    )
                )

    for obj in package.objects:
        if not obj.object_type:
            issues.append(
                _issue(
                    "survivability-object-type-missing",
                    f"object has no entity/type identity: {obj.object_id}",
                    object_id=obj.object_id,
                )
            )
        if not obj.vocabulary_id:
            issues.append(
                _issue(
                    "survivability-object-vocabulary-missing",
                    f"object type has no declared vocabulary: {obj.object_id}",
                    object_id=obj.object_id,
                )
            )

    for representation in package.representations:
        if not representation.version:
            issues.append(
                _issue(
                    "survivability-representation-version-missing",
                    f"representation has no version: {representation.representation_id}",
                    representation_id=representation.representation_id,
                )
            )
        if not representation.vocabulary_id:
            issues.append(
                _issue(
                    "survivability-representation-vocabulary-missing",
                    f"representation type has no vocabulary: {representation.representation_id}",
                    representation_id=representation.representation_id,
                )
            )
        if not (representation.resource_keys or representation.component_ids):
            issues.append(
                _issue(
                    "survivability-representation-content-missing",
                    f"representation carries no preserved content: {representation.representation_id}",
                    representation_id=representation.representation_id,
                )
            )
        if len(representation.component_ids) != len(set(representation.component_ids)):
            issues.append(
                _issue(
                    "survivability-representation-component-duplicate",
                    f"representation repeats a semantic component: {representation.representation_id}",
                    representation_id=representation.representation_id,
                )
            )
        if representation.protection_mode == "encrypted":
            if representation.component_ids:
                issues.append(
                    _issue(
                        "survivability-encrypted-composition-not-flat",
                        "encrypted representation cannot conceal another component graph: "
                        f"{representation.representation_id}",
                        representation_id=representation.representation_id,
                    )
                )
            protection = protection_by_id.get(representation.protection_id or "")
            if protection is not None:
                if not protection.encryption_profile:
                    issues.append(
                        _issue(
                            "survivability-encryption-profile-missing",
                            f"protection has no external encryption profile: {protection.protection_id}",
                            protection_id=protection.protection_id,
                        )
                    )
                if not protection.binding_profile:
                    issues.append(
                        _issue(
                            "survivability-component-binding-profile-missing",
                            f"protection has no identity binding profile: {protection.protection_id}",
                            protection_id=protection.protection_id,
                        )
                    )
                ciphertext = resource_by_key.get(protection.ciphertext_resource_key)
                if ciphertext is not None and (
                    ciphertext.materialization is None
                    or ciphertext.materialization.integrity is None
                ):
                    issues.append(
                        _issue(
                            "survivability-ciphertext-fixity-missing",
                            "encrypted semantic component lacks ciphertext fixity: "
                            f"{representation.representation_id}",
                            representation_id=representation.representation_id,
                        )
                    )
                if not envelopes_by_protection.get(protection.protection_id):
                    issues.append(
                        _issue(
                            "survivability-key-envelope-missing",
                            "encrypted semantic component has no declared access or recovery path: "
                            f"{representation.representation_id}",
                            representation_id=representation.representation_id,
                        )
                    )

    # Composition may be hierarchical for clear expressions, but cycles make
    # detached interpretation impossible. Encryption is restricted to leaves
    # above, so protected components remain parallel rather than nested.
    def visit(representation_id: str, path: frozenset[str]) -> None:
        if representation_id in path:
            issues.append(
                _issue(
                    "survivability-representation-component-cycle",
                    f"representation component graph contains a cycle: {representation_id}",
                    representation_id=representation_id,
                )
            )
            return
        representation = representation_by_id.get(representation_id)
        if representation is None:
            return
        next_path = path | {representation_id}
        for component_id in representation.component_ids:
            visit(component_id, next_path)

    for representation_id in representation_by_id:
        visit(representation_id, frozenset())

    for envelope in package.key_envelopes:
        if not envelope.version:
            issues.append(
                _issue(
                    "survivability-key-envelope-version-missing",
                    f"key envelope has no version: {envelope.envelope_id}",
                    envelope_id=envelope.envelope_id,
                )
            )
        if not envelope.key_management_profile:
            issues.append(
                _issue(
                    "survivability-key-management-profile-missing",
                    f"key envelope has no external key-management profile: {envelope.envelope_id}",
                    envelope_id=envelope.envelope_id,
                )
            )

    for relation in package.relations:
        if not relation.vocabulary_id:
            issues.append(
                _issue(
                    "survivability-relation-vocabulary-missing",
                    f"relation does not own a vocabulary-defined meaning: {relation.relation_id}",
                    relation_id=relation.relation_id,
                )
            )

    for occurrence in package.occurrences:
        if not occurrence.vocabulary_id:
            issues.append(
                _issue(
                    "survivability-occurrence-vocabulary-missing",
                    f"occurrence type has no vocabulary: {occurrence.occurrence_id}",
                    occurrence_id=occurrence.occurrence_id,
                )
            )
        if not (occurrence.occurred_at or occurrence.started_at):
            issues.append(
                _issue(
                    "survivability-occurrence-time-missing",
                    f"occurrence has no point or interval time: {occurrence.occurrence_id}",
                    occurrence_id=occurrence.occurrence_id,
                )
            )
        if occurrence.basis == "asserted" and not occurrence.source_refs:
            issues.append(
                _issue(
                    "survivability-occurrence-source-basis-missing",
                    f"asserted occurrence has no source basis: {occurrence.occurrence_id}",
                    occurrence_id=occurrence.occurrence_id,
                )
            )
        if occurrence.basis == "observed" and not occurrence.actor_ref:
            issues.append(
                _issue(
                    "survivability-occurrence-observer-missing",
                    f"observed occurrence has no observing actor: {occurrence.occurrence_id}",
                    occurrence_id=occurrence.occurrence_id,
                )
            )

    for claim in package.preservation_claims:
        if not claim.root_refs:
            issues.append(
                _issue(
                    "survivability-claim-root-missing",
                    f"preservation claim is resource-scoped but not entity-rooted: {claim.claim_id}",
                    claim_id=claim.claim_id,
                )
            )
        for root_ref in claim.root_refs:
            if root_ref in external_ids:
                issues.append(
                    _issue(
                        "survivability-external-root-not-owned",
                        f"package cannot claim closure for an external stub: {root_ref}",
                        claim_id=claim.claim_id,
                        root_ref=root_ref,
                    )
                )
        for requirement in claim.requirements:
            if requirement.subject_ref is None:
                issues.append(
                    _issue(
                        "survivability-requirement-subject-missing",
                        f"closure dependency is not assigned to an entity: {requirement.resource_key}",
                        claim_id=claim.claim_id,
                        resource_key=requirement.resource_key,
                    )
                )

    for assertion in metadata_assertions:
        expected_ids = internal_by_kind.get(assertion.subject_kind, set())
        if assertion.subject_id not in expected_ids:
            issues.append(
                _issue(
                    "survivability-metadata-subject-missing",
                    f"metadata assertion subject is not declared: {assertion.subject_id}",
                    metadata_id=assertion.metadata_id,
                    subject_id=assertion.subject_id,
                )
            )
        if assertion.basis in {"asserted", "observed"} and not assertion.source_refs:
            issues.append(
                _issue(
                    "survivability-metadata-source-basis-missing",
                    f"{assertion.basis} metadata has no source basis: {assertion.metadata_id}",
                    metadata_id=assertion.metadata_id,
                )
            )
        if assertion.basis in {"derived", "inferred"} and not assertion.producer_ref:
            issues.append(
                _issue(
                    "survivability-metadata-producer-missing",
                    f"{assertion.basis} metadata has no producer: {assertion.metadata_id}",
                    metadata_id=assertion.metadata_id,
                )
            )
        for reference in assertion.source_refs:
            if reference not in declared_ids:
                issues.append(
                    _issue(
                        "survivability-metadata-source-missing",
                        f"metadata source reference is undeclared: {reference}",
                        metadata_id=assertion.metadata_id,
                        source_ref=reference,
                    )
                )

    return PreflightResult(tuple(issues))
