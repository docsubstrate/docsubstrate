from __future__ import annotations

from dataclasses import replace

from docsubstrate.migration import MigrationChange, MigrationRecord, validate_migration
from docsubstrate.occurrence import OccurrenceRecord
from docsubstrate.package import (
    ExternalReference,
    PackageObject,
    PackageRelation,
    PortableInstitutionalPackage,
)


def _package(*, version: str, predicate: str = "relatesTo") -> PortableInstitutionalPackage:
    return PortableInstitutionalPackage(
        package_id="pkg-1",
        format_version=version,
        profile="general",
        objects=(PackageObject("a", "Document"), PackageObject("b", "Party")),
        relations=(PackageRelation("relation:a-b", "a", predicate, "b"),),
    )


def test_format_upgrade_can_preserve_institutional_meaning() -> None:
    source = _package(version="0.1")
    target = _package(version="0.2")
    record = MigrationRecord(
        migration_id="m-1",
        source_package_id="pkg-1",
        source_format_version="0.1",
        target_package_id="pkg-1",
        target_format_version="0.2",
        changes=(
            MigrationChange("c-1", "format", "package:pkg-1", "upgrade encoding"),
        ),
    )

    assert validate_migration(source, target, record) == ()


def test_semantic_change_cannot_hide_inside_format_migration() -> None:
    source = _package(version="0.1", predicate="relatesTo")
    target = _package(version="0.2", predicate="approvedBy")
    record = MigrationRecord(
        migration_id="m-2",
        source_package_id="pkg-1",
        source_format_version="0.1",
        target_package_id="pkg-1",
        target_format_version="0.2",
        changes=(MigrationChange("c-1", "format", "package:pkg-1", "upgrade encoding"),),
    )

    assert validate_migration(source, target, record) == (
        "migration-semantic-change-undeclared",
    )


def test_declared_semantic_change_is_explicitly_distinct_from_upgrade() -> None:
    source = _package(version="0.1", predicate="relatesTo")
    target = _package(version="0.2", predicate="approvedBy")
    record = MigrationRecord(
        migration_id="m-3",
        source_package_id="pkg-1",
        source_format_version="0.1",
        target_package_id="pkg-1",
        target_format_version="0.2",
        changes=(
            MigrationChange("c-1", "format", "package:pkg-1", "upgrade encoding"),
            MigrationChange(
                "c-2",
                "semantic",
                "relation:a:approvedBy:b",
                "replace relation according to declared domain migration",
            ),
        ),
    )

    assert validate_migration(source, target, record) == ()


def test_semantic_change_declaration_must_not_be_noise() -> None:
    source = _package(version="0.1")
    target = _package(version="0.2")
    record = MigrationRecord(
        migration_id="m-4",
        source_package_id="pkg-1",
        source_format_version="0.1",
        target_package_id="pkg-1",
        target_format_version="0.2",
        changes=(
            MigrationChange("c-1", "semantic", "object:a", "claimed semantic rewrite"),
        ),
    )

    assert validate_migration(source, target, record) == (
        "migration-semantic-change-declared-but-not-observed",
    )


def test_occurrence_change_cannot_hide_inside_format_migration() -> None:
    source = replace(
        _package(version="0.1"),
        occurrences=(
            OccurrenceRecord(
                "occurrence:issued",
                "issued",
                "succeeded",
                "observed",
                input_refs=("a",),
                actor_ref="b",
                occurred_at="2026-09-01T00:00:00Z",
            ),
        ),
    )
    target = replace(source, format_version="0.2", occurrences=())
    record = MigrationRecord("m-5", "pkg-1", "0.1", "pkg-1", "0.2")

    assert validate_migration(source, target, record) == (
        "migration-semantic-change-undeclared",
    )


def test_external_reference_change_cannot_hide_inside_format_migration() -> None:
    source = replace(
        _package(version="0.1"),
        external_references=(ExternalReference("external:party", "Party"),),
        relations=(PackageRelation("relation:a-party", "a", "relatesTo", "external:party"),),
    )
    target = replace(
        source,
        format_version="0.2",
        external_references=(ExternalReference("external:party", "Regulator"),),
    )
    record = MigrationRecord("m-6", "pkg-1", "0.1", "pkg-1", "0.2")

    assert validate_migration(source, target, record) == (
        "migration-semantic-change-undeclared",
    )
