"""Document-scoped binding of stable resource descriptors and requirements."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from docsubstrate.preflight import PreflightIssue, PreflightResult
from docsubstrate.resources import ResourceDescriptor, ResourceRequirement


@dataclass(slots=True)
class ResourceCatalog:
    descriptors: dict[str, ResourceDescriptor] = field(default_factory=dict)

    def add(self, descriptor: ResourceDescriptor) -> None:
        current = self.descriptors.get(descriptor.resource_key)
        if current is None:
            self.descriptors[descriptor.resource_key] = descriptor
            return
        if current != descriptor:
            raise ValueError(
                f"resource key collision: {descriptor.resource_key!r} has conflicting descriptors"
            )

    def get(self, resource_key: str) -> ResourceDescriptor | None:
        return self.descriptors.get(resource_key)

    def validate_requirements(
        self,
        requirements: Iterable[ResourceRequirement],
        *,
        context: Mapping[str, str | int | float | bool] | None = None,
    ) -> PreflightResult:
        issues: list[PreflightIssue] = []
        for requirement in requirements:
            if not requirement.required:
                continue
            if requirement.resource_key not in self.descriptors:
                details: dict[str, str | int | float | bool] = dict(context or {})
                details["purpose"] = requirement.purpose
                issues.append(
                    PreflightIssue(
                        code="unresolved-resource",
                        message=f"unresolved resource: {requirement.resource_key}",
                        details=details,
                    )
                )
        return PreflightResult(tuple(issues))
