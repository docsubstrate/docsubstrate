"""Host-neutral document primitives for the first rendering milestone."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class PaperSpec:
    """Physical page intent independent of a rendering backend."""

    width_mm: float = 210.0
    height_mm: float = 297.0
    margin_top_mm: float = 10.0
    margin_right_mm: float = 10.0
    margin_bottom_mm: float = 10.0
    margin_left_mm: float = 10.0
    #: Odoo paperformats that disable wkhtmltopdf smart shrinking keep the
    #: CSS reference pixel at 96/in.  The host must carry that structural
    #: choice because CSS lengths are resolved before pagination.
    disable_shrinking: bool = False
    #: The paper kind supplied by the host. Named formats and ``custom``
    #: dimensions are distinct inputs to this package's page-box contract;
    #: retaining the distinction prevents a 57x32mm label from being
    #: quantised like named A4 paper. Synthetic boundary cases are executable
    #: in `tests/test_reportlab_canvas.py`.
    format_name: str = "A4"
    #: Printer resolution used to serialise a custom page box. This is not the
    #: CSS pixel scale above: Odoo supplies it independently as paperformat.dpi.
    dpi: int = 90


@dataclass(frozen=True, slots=True)
class RenderSource:
    """Evaluated source supplied by a host adapter.

    `kind` is deliberately explicit. The first Odoo adapter will use
    ``qweb-html``. Future adapters may supply a native DocSubstrate tree.
    """

    kind: str
    content: str
    base_url: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RenderRequest:
    source: RenderSource
    paper: PaperSpec = field(default_factory=PaperSpec)
    language: str | None = None
    document_id: str | None = None


@dataclass(frozen=True, slots=True)
class RenderResult:
    media_type: str
    content: bytes
    renderer: str
    warnings: Sequence[str] = ()
