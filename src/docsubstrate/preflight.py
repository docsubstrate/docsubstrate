"""Generic structured validation results shared by A0 contracts.

This module deliberately knows nothing about renderers, pages, devices, or
domain vocabularies.  More specific validators may attach their own locations
and details without promoting those concepts into the A0 semantic model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

IssueSeverity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class PreflightIssue:
    code: str
    message: str
    severity: IssueSeverity = "error"
    details: Mapping[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PreflightResult:
    issues: Sequence[PreflightIssue] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[PreflightIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[PreflightIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def extend(self, *others: PreflightResult) -> PreflightResult:
        merged = list(self.issues)
        for other in others:
            merged.extend(other.issues)
        return PreflightResult(tuple(merged))
