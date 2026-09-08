"""Durable-profile dependency closure contracts.

Durability is evaluated against an explicit preservation claim.  The core does
not fetch HTTP resources, open files, or copy objects into an archive.  It only
models what must remain independently resolvable/verifiable and reports gaps.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

from docsubstrate.preflight import PreflightIssue, PreflightResult
from docsubstrate.resource_catalog import ResourceCatalog
from docsubstrate.resources import ResourceDescriptor

ClosureRole = Literal[
    "interpretation",
    "evidentiary",
    "verification",
    "reproduction",
    "contextual",
]


@dataclass(frozen=True, slots=True)
class ResolutionProbe:
    """Non-materializing answer from a resolver.

    A resolver may prove that a resource can be located and, when possible,
    provide immutable identity/integrity metadata.  Returning a probe must not
    imply that the resource has been embedded or copied into a durable package.
    """

    resolvable: bool
    immutable: bool = False
    integrity_verified: bool = False
    media_type: str | None = None
    details: Mapping[str, str | int | float | bool] = field(default_factory=dict)


class ResourceResolver(Protocol):
    """Capability boundary for external resource resolution.

    Implementations may use filesystems, object stores, HTTP, databases, or
    other mechanisms.  DocSubstrate core deliberately defines only this probe
    interface and contains no transport-specific resolver.
    """

    name: str

    def probe(self, resource: ResourceDescriptor) -> ResolutionProbe:
        ...


@dataclass(frozen=True, slots=True)
class ClosureRequirement:
    """One resource dependency required by a declared preservation claim."""

    resource_key: str
    role: ClosureRole
    require_integrity: bool = True
    require_immutable_resolution: bool = True
    subject_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PreservationClaim:
    """What this package claims it can preserve independently.

    Roles are explicit so a package can claim interpretation/evidence closure
    without falsely claiming exact future reproduction when that dependency set
    has not been captured.
    """

    claim_id: str
    roles: frozenset[ClosureRole]
    requirements: Sequence[ClosureRequirement] = field(default_factory=tuple)
    root_refs: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ClosureReport:
    claim: PreservationClaim
    preflight: PreflightResult
    satisfied_roles: frozenset[ClosureRole]
    unsatisfied_roles: frozenset[ClosureRole]

    @property
    def ok(self) -> bool:
        return self.preflight.ok and not self.unsatisfied_roles


def validate_durable_closure(
    claim: PreservationClaim,
    catalog: ResourceCatalog,
    *,
    resolvers: Mapping[str, ResourceResolver] | None = None,
) -> ClosureReport:
    """Validate resource closure for a declared preservation claim.

    Embedded resources are locally closed when required integrity metadata is
    present.  External resources are acceptable only when a declared resolver
    can prove the required immutable/integrity properties.  Derived resources
    do not satisfy a closure requirement by themselves; the canonical inputs
    they depend on must instead appear as requirements.
    """

    resolver_map = resolvers or {}
    issues: list[PreflightIssue] = []
    failed_roles: set[ClosureRole] = set()

    for requirement in claim.requirements:
        if requirement.role not in claim.roles:
            continue

        resource = catalog.get(requirement.resource_key)
        if resource is None:
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="durable-resource-missing",
                    message=f"durable dependency missing: {requirement.resource_key}",
                    details={"role": requirement.role, "resource_key": requirement.resource_key},
                )
            )
            continue

        materialization = resource.materialization
        if materialization is None:
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="durable-materialization-missing",
                    message=f"no materialization declared for: {requirement.resource_key}",
                    details={"role": requirement.role, "resource_key": requirement.resource_key},
                )
            )
            continue

        if materialization.kind == "derived":
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="derived-resource-not-closure",
                    message=f"derived materialization cannot close dependency: {requirement.resource_key}",
                    details={"role": requirement.role, "resource_key": requirement.resource_key},
                )
            )
            continue

        if materialization.kind == "embedded":
            if requirement.require_integrity and materialization.integrity is None:
                failed_roles.add(requirement.role)
                issues.append(
                    PreflightIssue(
                        code="durable-integrity-missing",
                        message=f"embedded durable resource lacks integrity: {requirement.resource_key}",
                        details={"role": requirement.role, "resource_key": requirement.resource_key},
                    )
                )
            continue

        resolver_name = materialization.resolver
        resolver = resolver_map.get(resolver_name or "")
        if resolver is None:
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="durable-resolver-missing",
                    message=f"no resolver available for external durable dependency: {requirement.resource_key}",
                    details={
                        "role": requirement.role,
                        "resource_key": requirement.resource_key,
                        "resolver": resolver_name or "",
                    },
                )
            )
            continue

        probe = resolver.probe(resource)
        if not probe.resolvable:
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="durable-resource-unresolvable",
                    message=f"external durable dependency is not resolvable: {requirement.resource_key}",
                    details={"role": requirement.role, "resource_key": requirement.resource_key},
                )
            )
            continue

        if requirement.require_immutable_resolution and not probe.immutable:
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="durable-resolution-mutable",
                    message=f"external durable dependency is not immutably resolved: {requirement.resource_key}",
                    details={"role": requirement.role, "resource_key": requirement.resource_key},
                )
            )

        if requirement.require_integrity and not probe.integrity_verified:
            failed_roles.add(requirement.role)
            issues.append(
                PreflightIssue(
                    code="durable-integrity-unverified",
                    message=f"external durable dependency integrity is unverified: {requirement.resource_key}",
                    details={"role": requirement.role, "resource_key": requirement.resource_key},
                )
            )

    satisfied = frozenset(role for role in claim.roles if role not in failed_roles)
    failed = frozenset(failed_roles)
    return ClosureReport(
        claim=claim,
        preflight=PreflightResult(tuple(issues)),
        satisfied_roles=satisfied,
        unsatisfied_roles=failed,
    )
