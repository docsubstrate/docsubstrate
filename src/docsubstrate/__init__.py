"""DocSubstrate public package (A2 public-alpha narrow packaging closure).

The top-level API is intentionally minimal for this alpha: it exposes only
substrate primitives whose own source files are on the exact public core
wheel allowlist (see ``pyproject.toml``'s ``[tool.hatch.build.targets.wheel]``
and ``public-alpha/a2-package-import-closure-manifest.json``). Institutional
act/relation/authority/evidence primitives
(``docsubstrate.institutional``/``docsubstrate.assertion_ontology``) are real
modules in this source tree but are not yet cleared for the public alpha, so
they are deliberately not imported or re-exported here. Import them directly
from their own module if you have a reason to reach past this alpha's
boundary; this file's job is only to keep ``import docsubstrate`` itself from
transitively loading anything off the allowlist.
"""

import os

if os.environ.get("DOCSUBSTRATE_PROFILE_BOOTSTRAP"):
    # Offline profile compilation imports individual cascade modules from an
    # archive where the generated runtime profile is intentionally absent.
    # Do not pull the public engine facade (and its generated-profile import)
    # into that compiler bootstrap.
    __all__ = []
else:
    from docsubstrate.commerce import AddressData, CommercialDocumentData, CommercialLineData
    from docsubstrate.content import content_digest
    from docsubstrate.documents import DocumentIdentity
    from docsubstrate.engine_adapters.reportlab import ReportLabEngine, render_sale_order_pdf
    from docsubstrate.model import PaperSpec, RenderRequest, RenderResult, RenderSource
    from docsubstrate.snapshots import DocumentSnapshot

    __all__ = [
        "AddressData", "CommercialDocumentData", "CommercialLineData",
        "DocumentIdentity", "DocumentSnapshot", "PaperSpec", "RenderRequest",
        "RenderResult", "RenderSource", "ReportLabEngine", "content_digest",
        "render_sale_order_pdf",
    ]
