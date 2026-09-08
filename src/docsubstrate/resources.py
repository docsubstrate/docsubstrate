"""Resource identity and materialization contracts.

A resource is something a portable representation depends on. Resource identity,
integrity, and materialization policy are separate from runtime caches. The core
does not resolve locators, decode formats, or decide archive closure; those
concerns belong to resolvers, profiles, and execution backends.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

MaterializationKind = Literal["embedded", "external", "derived"]
IntegrityAlgorithm = Literal["sha256"]


@dataclass(frozen=True, slots=True)
class IntegrityDigest:
    algorithm: IntegrityAlgorithm
    value: str


@dataclass(frozen=True, slots=True)
class MaterializationRef:
    """How bytes or content for a resource may be obtained.

    `embedded` means the containing representation/package owns the bytes.
    `external` means a resolver is required. `derived` means the material form is
    reproducible from canonical inputs and therefore is not itself the portable
    ground truth (for example a generated search index).
    """

    kind: MaterializationKind
    locator: str | None = None
    media_type: str | None = None
    length: int | None = None
    integrity: IntegrityDigest | None = None
    resolver: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceDescriptor:
    """Stable envelope for a resource used by a document representation."""

    resource_key: str
    resource_type: str
    media_type: str | None = None
    semantic_type: str | None = None
    schema: str | None = None
    version: str | None = None
    materialization: MaterializationRef | None = None
    metadata: Mapping[str, str | int | float | bool] = field(default_factory=dict)

    def content_address(self) -> str | None:
        materialization = self.materialization
        if materialization is None or materialization.integrity is None:
            return None
        digest = materialization.integrity
        return f"{digest.algorithm}:{digest.value}"


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    """One representation/package dependency on a stable resource identity.

    `purpose` explains why the resource is needed, such as interpretation,
    verification, evidence, or reproduction. Resolution and caching remain
    outside this model.
    """

    resource_key: str
    purpose: str
    required: bool = True
