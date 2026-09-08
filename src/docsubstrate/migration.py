"""Migration contracts for Portable Institutional Packages.

A format migration may change encoding, profile mechanics, resource layout, or
representation details without silently changing institutional meaning. Semantic
changes must be declared explicitly and cannot masquerade as a format upgrade.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from docsubstrate.package import PortableInstitutionalPackage

MigrationChangeClass = Literal[
    "format",
    "representation",
    "resource",
    "semantic",
]


@dataclass(frozen=True, slots=True)
class MigrationChange:
    change_id: str
    change_class: MigrationChangeClass
    subject_ref: str
    description: str
    details: Mapping[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MigrationRecord:
    migration_id: str
    source_package_id: str
    source_format_version: str
    target_package_id: str
    target_format_version: str
    tool_ref: str | None = None
    occurred_at: str | None = None
    changes: Sequence[MigrationChange] = field(default_factory=tuple)

    @property
    def semantic_change_declared(self) -> bool:
        return any(item.change_class == "semantic" for item in self.changes)


def semantic_projection(package: PortableInstitutionalPackage) -> tuple[object, ...]:
    """Return the package fields that currently carry institutional graph meaning.

    The projection intentionally excludes physical resources, artifacts, profile
    mechanics, preservation claims, and opaque transport extensions. Those may
    evolve during preservation or interchange without changing the institutional
    graph. Representation identity/type is retained because changing what an
    object is expressed as can alter interpretation unless explicitly handled.
    """

    objects = tuple(
        sorted(
            (
                item.object_id,
                item.object_type,
                item.vocabulary_id,
            )
            for item in package.objects
        )
    )
    external_references = tuple(
        sorted(
            (
                item.reference_id,
                item.entity_type,
                item.vocabulary_id,
            )
            for item in package.external_references
        )
    )
    relations = tuple(
        sorted(
            (
                item.relation_id,
                item.source_id,
                item.predicate,
                item.target_id,
                item.vocabulary_id,
            )
            for item in package.relations
        )
    )
    representations = tuple(
        sorted(
            (
                item.representation_id,
                item.object_id,
                item.representation_type,
                item.vocabulary_id,
                item.schema,
                item.version,
                tuple(item.component_ids),
            )
            for item in package.representations
        )
    )
    vocabularies = tuple(
        sorted((item.vocabulary_id, item.version) for item in package.vocabularies)
    )
    occurrences = tuple(
        sorted(
            (
                item.occurrence_id,
                item.occurrence_type,
                item.outcome,
                item.basis,
                tuple(item.input_refs),
                tuple(item.output_refs),
                tuple(item.source_refs),
                item.actor_ref,
                item.action_ref,
                item.occurred_at,
                item.started_at,
                item.ended_at,
                tuple(sorted(item.details.items())),
                item.vocabulary_id,
            )
            for item in package.occurrences
        )
    )
    return objects, external_references, relations, representations, vocabularies, occurrences


def validate_migration(
    source: PortableInstitutionalPackage,
    target: PortableInstitutionalPackage,
    record: MigrationRecord,
) -> tuple[str, ...]:
    """Validate one migration record against source and target packages.

    Pure format/resource migrations must preserve the semantic projection. If the
    projection changes, an explicit semantic MigrationChange is required. The
    function returns stable error codes so independent tooling can enforce the
    same rule without importing an execution harness.
    """

    errors: list[str] = []
    if record.source_package_id != source.package_id:
        errors.append("migration-source-package-mismatch")
    if record.source_format_version != source.format_version:
        errors.append("migration-source-version-mismatch")
    if record.target_package_id != target.package_id:
        errors.append("migration-target-package-mismatch")
    if record.target_format_version != target.format_version:
        errors.append("migration-target-version-mismatch")

    changed = semantic_projection(source) != semantic_projection(target)
    if changed and not record.semantic_change_declared:
        errors.append("migration-semantic-change-undeclared")
    if not changed and record.semantic_change_declared:
        errors.append("migration-semantic-change-declared-but-not-observed")

    return tuple(errors)
