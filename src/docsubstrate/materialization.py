"""Materialization intent shared by source adapters and document engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class MaterializationRequest:
    """A request to materialize one institutional document artifact.

    This is deliberately source- and renderer-neutral.  Odoo's Print action,
    an API call, an agent, or another application can all create the same
    request shape.
    """

    document_kind: str
    source_system: str
    source_model: str
    source_record_ids: Sequence[int | str]
    output_media_type: str = "application/pdf"
    language: str | None = None
    company_id: int | str | None = None
    report_action: str | None = None
    policy: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
