"""Writer/reader compliance contracts for Portable Institutional Packages.

Compliance is profile-scoped. Writers may generate a legal declared subset;
readers that claim a profile must support its mandatory contract. Unknown
optional extensions may remain opaque, but unknown critical semantics must never
be silently reinterpreted.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from docsubstrate.package import PortableInstitutionalPackage
from docsubstrate.preflight import PreflightIssue, PreflightResult


@dataclass(frozen=True, slots=True)
class InterchangeProfile:
    profile_id: str
    format_versions: frozenset[str]
    mandatory_capabilities: frozenset[str] = frozenset()
    allowed_capabilities: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class WriterConformance:
    """Capabilities a writer is authorized/implemented to emit."""

    supported_profiles: Mapping[str, frozenset[str]]
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ReaderConformance:
    """Capabilities/vocabularies a reader claims it can interpret."""

    supported_profiles: Mapping[str, frozenset[str]]
    capabilities: frozenset[str] = frozenset()
    vocabularies: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ReaderReport:
    preflight: PreflightResult
    fully_interpretable: bool
    opaque_extension_ids: frozenset[str] = frozenset()
    unsupported_capabilities: frozenset[str] = frozenset()
    unsupported_vocabularies: frozenset[str] = frozenset()

    @property
    def readable(self) -> bool:
        return self.preflight.ok


def validate_writer(
    package: PortableInstitutionalPackage,
    *,
    writer: WriterConformance,
    profile: InterchangeProfile,
) -> PreflightResult:
    """Validate that a writer produced a legal declared subset.

    Structural validity is included because a conforming writer must not emit an
    internally incoherent package. The writer may support more capabilities than
    the package uses, but every declared package capability must be implemented
    by the writer and allowed by the selected profile.
    """

    issues = list(package.validate_structure().issues)

    versions = writer.supported_profiles.get(package.profile)
    if versions is None:
        issues.append(
            PreflightIssue(
                code="writer-profile-unsupported",
                message=f"writer does not support profile: {package.profile}",
            )
        )
    elif package.format_version not in versions:
        issues.append(
            PreflightIssue(
                code="writer-format-version-unsupported",
                message=(
                    f"writer does not support format version {package.format_version!r} "
                    f"for profile {package.profile!r}"
                ),
            )
        )

    if package.profile != profile.profile_id:
        issues.append(
            PreflightIssue(
                code="writer-profile-definition-mismatch",
                message=(
                    f"package declares profile {package.profile!r}, validator received "
                    f"{profile.profile_id!r}"
                ),
            )
        )

    if package.format_version not in profile.format_versions:
        issues.append(
            PreflightIssue(
                code="profile-format-version-invalid",
                message=(
                    f"format version {package.format_version!r} is not valid for "
                    f"profile {profile.profile_id!r}"
                ),
            )
        )

    missing_mandatory = profile.mandatory_capabilities - package.capabilities
    for capability in sorted(missing_mandatory):
        issues.append(
            PreflightIssue(
                code="profile-mandatory-capability-missing",
                message=f"mandatory profile capability not declared: {capability}",
                details={"capability": capability},
            )
        )

    undeclared_by_writer = package.capabilities - writer.capabilities
    for capability in sorted(undeclared_by_writer):
        issues.append(
            PreflightIssue(
                code="writer-capability-unsupported",
                message=f"writer emitted unsupported capability: {capability}",
                details={"capability": capability},
            )
        )

    if profile.allowed_capabilities is not None:
        disallowed = package.capabilities - profile.allowed_capabilities
        for capability in sorted(disallowed):
            issues.append(
                PreflightIssue(
                    code="profile-capability-disallowed",
                    message=f"capability is not allowed by profile: {capability}",
                    details={"capability": capability},
                )
            )

    return PreflightResult(tuple(issues))


def inspect_reader(
    package: PortableInstitutionalPackage,
    *,
    reader: ReaderConformance,
    profile: InterchangeProfile,
) -> ReaderReport:
    """Determine whether a reader can safely consume a package.

    Unknown non-critical extension capabilities do not make the package
    unreadable; the reader must preserve those extension envelopes/resources
    opaquely. Unknown critical extensions do make safe interpretation fail.
    Unknown vocabularies are reported explicitly rather than guessed.
    """

    issues = list(package.validate_structure().issues)
    opaque: set[str] = set()

    versions = reader.supported_profiles.get(package.profile)
    if versions is None:
        issues.append(
            PreflightIssue(
                code="reader-profile-unsupported",
                message=f"reader does not support profile: {package.profile}",
            )
        )
    elif package.format_version not in versions:
        issues.append(
            PreflightIssue(
                code="reader-format-version-unsupported",
                message=(
                    f"reader does not support format version {package.format_version!r} "
                    f"for profile {package.profile!r}"
                ),
            )
        )

    if package.profile != profile.profile_id:
        issues.append(
            PreflightIssue(
                code="reader-profile-definition-mismatch",
                message=(
                    f"package declares profile {package.profile!r}, validator received "
                    f"{profile.profile_id!r}"
                ),
            )
        )

    unsupported_capabilities = package.capabilities - reader.capabilities
    missing_reader_mandatory = profile.mandatory_capabilities - reader.capabilities
    for capability in sorted(missing_reader_mandatory):
        issues.append(
            PreflightIssue(
                code="reader-mandatory-capability-unsupported",
                message=f"reader lacks mandatory profile capability: {capability}",
                details={"capability": capability},
            )
        )

    extension_caps = {extension.capability for extension in package.extensions}
    unsupported_non_extension = unsupported_capabilities - extension_caps
    for capability in sorted(unsupported_non_extension):
        issues.append(
            PreflightIssue(
                code="reader-capability-unsupported",
                message=f"reader cannot interpret declared capability: {capability}",
                details={"capability": capability},
            )
        )

    for extension in package.extensions:
        if extension.capability in reader.capabilities:
            continue
        if extension.critical:
            issues.append(
                PreflightIssue(
                    code="reader-critical-extension-unsupported",
                    message=(
                        f"reader cannot interpret critical extension: "
                        f"{extension.extension_id}"
                    ),
                    details={
                        "extension_id": extension.extension_id,
                        "capability": extension.capability,
                    },
                )
            )
        else:
            opaque.add(extension.extension_id)

    declared_vocabularies = {v.vocabulary_id for v in package.vocabularies}
    unsupported_vocabularies = declared_vocabularies - reader.vocabularies

    fully_interpretable = (
        not issues
        and not opaque
        and not unsupported_capabilities
        and not unsupported_vocabularies
    )

    return ReaderReport(
        preflight=PreflightResult(tuple(issues)),
        fully_interpretable=fully_interpretable,
        opaque_extension_ids=frozenset(opaque),
        unsupported_capabilities=frozenset(unsupported_capabilities),
        unsupported_vocabularies=frozenset(unsupported_vocabularies),
    )
