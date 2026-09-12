"""Rendering backend contract."""

from __future__ import annotations

from typing import Protocol

from docsubstrate.model import RenderRequest, RenderResult


class UnsupportedDocumentFeature(RuntimeError):
    """Raised when a backend cannot safely render the requested semantics."""


class Renderer(Protocol):
    name: str

    def supports(self, request: RenderRequest) -> bool:
        """Return whether the backend can safely attempt this request."""
        ...

    def render(self, request: RenderRequest) -> RenderResult:
        """Render a request or raise UnsupportedDocumentFeature."""
        ...
