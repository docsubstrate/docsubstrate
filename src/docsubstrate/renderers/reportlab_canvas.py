"""ReportLab Canvas backend for resolved DocSubstrate page plans.

This backend is intentionally layout-blind.  It executes PagePlan commands and
never performs pagination or flow layout.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import math
import os
import zlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from io import BytesIO
from pathlib import Path

from docsubstrate.pageplan import (
    Circle,
    ImageRef,
    Line,
    Rect,
    ResolvedDocument,
    TextRun,
)
from docsubstrate.pageplan import (
    Path as PagePath,
)
from docsubstrate.render_baseline import matches_oracle
from docsubstrate.renderers.encoded_image_store import EncodedImageStore
from docsubstrate.svg_path import _ARC_K

MM_TO_PT = 72.0 / 25.4
# PDF transparency was standardised in PDF 1.4.  ReportLab upgrades a document
# lazily when ``setFillAlpha`` is called, but that otherwise makes this one
# renderer emit either 1.3 or 1.4 according to page content.  Its public output
# contract starts at the smallest version which can represent every PagePlan
# command it supports; this is a minimum, not a PDF 2.0 conformance claim.
_PDF_VERSION = (1, 4)
_logger = logging.getLogger(__name__)
_REGISTERED_FONT: str | None = None
_IMAGE_READER_CACHE_MAX = 32
_IMAGE_READER_CACHE_MAX_BYTES = 64 * 1024 * 1024
_IMAGE_READER_CACHE = OrderedDict()
_IMAGE_READER_CACHE_BYTES = 0
# ``encoded_image_cache_producer`` below still reports this: it documents
# what level ReportLab's own ``PDFImageXObject.loadImageFromSRC`` compresses
# at, for anything that logs or fingerprints render configuration. Nothing in
# this module calls zlib.compress itself.
_ENCODED_IMAGE_ZLIB_LEVEL = -1


def _clear_image_reader_cache() -> None:
    """Clear the decoded-image cache for cold measurements."""
    global _IMAGE_READER_CACHE_BYTES
    _IMAGE_READER_CACHE.clear()
    _IMAGE_READER_CACHE_BYTES = 0


def _pt(mm: float) -> float:
    return mm * MM_TO_PT


def _qt_round(value: float) -> int:
    """Round positive layout values half-up rather than ties-to-even."""
    return math.floor(value + 0.5)


def _page_pt(mm: float, *, paper_format: str, dpi: int) -> float:
    """Resolve a paper box through the configured printer pixel grid.

    A named format starts with the bounded compatibility contract's
    integral-point table. A custom size starts with the authored millimetres.
    Both then cross the printer's
    integer device-pixel grid and return to an integral-point MediaBox.

    This distinction is observable rather than cosmetic: custom 57x32mm at
    96dpi becomes 161x91pt, while custom 57x200mm at 90dpi becomes 162x567pt.
    Unconditionally rounding millimetres to points gets only the latter right.
    Content coordinates remain exact; this function serialises the box only.
    """
    points = mm * MM_TO_PT
    if not matches_oracle("page_box_whole_points"):
        return points
    if paper_format != "custom":
        points = float(_qt_round(points))
    device_pixels = _qt_round(points * dpi / 72.0)
    return float(_qt_round(device_pixels * 72.0 / dpi))


def _rounded_path(canvas, x, y, width, height, radii, *, stroke, fill):
    """A rectangle whose four corners round independently.

    ReportLab's `roundRect` takes one radius, and `boxed-rounded` needs four:
    the line table squares its bottom-right so the totals band tucks in, and
    the band rounds only its own bottom two.
    """
    top_left, top_right, bottom_right, bottom_left = (
        max(0.0, min(r, width / 2.0, height / 2.0)) for r in radii
    )
    right, top = x + width, y + height
    outline = canvas.beginPath()

    def arc(from_x, from_y, corner_x, corner_y, to_x, to_y, radius):
        """A quarter arc from one tangent point to the next, around a corner."""
        pull = radius * (1.0 - _ARC_K)
        outline.curveTo(
            from_x + (corner_x - from_x) * (pull / radius if radius else 0.0),
            from_y + (corner_y - from_y) * (pull / radius if radius else 0.0),
            to_x + (corner_x - to_x) * (pull / radius if radius else 0.0),
            to_y + (corner_y - to_y) * (pull / radius if radius else 0.0),
            to_x, to_y,
        )

    outline.moveTo(x + top_left, top)
    outline.lineTo(right - top_right, top)
    if top_right:
        arc(right - top_right, top, right, top, right, top - top_right, top_right)
    outline.lineTo(right, y + bottom_right)
    if bottom_right:
        arc(right, y + bottom_right, right, y, right - bottom_right, y, bottom_right)
    outline.lineTo(x + bottom_left, y)
    if bottom_left:
        arc(x + bottom_left, y, x, y, x, y + bottom_left, bottom_left)
    outline.lineTo(x, top - top_left)
    if top_left:
        arc(x, top - top_left, x, top, x + top_left, top, top_left)
    outline.close()
    canvas.drawPath(outline, stroke=stroke, fill=fill)


#: A face is accepted only if it can draw these. Filenames lie; glyphs do not.
_CJK_PROBE = "\u6f22\u5b57"  # 漢字

#: Where CJK text faces live once installed by a distro package. `.ttc`
#: collections carry several regional faces, so each is probed by index.
_FONT_CANDIDATES = (
    "~/.fonts/NotoSansTC-conv.ttf",
    # Noto Sans CJK is what wkhtml draws, but the distro ships it with
    # PostScript outlines that ReportLab cannot embed; this is the same
    # typeface converted to TrueType, installed with the appliance.
    "/usr/share/fonts/truetype/docsubstrate/NotoSansTC-conv.ttf",
    "~/.fonts/NotoSansCJKtc-Regular.otf",
    # Business documents want a sans face. WenQuanYi Zen Hei is the sans with
    # TrueType outlines -- ReportLab cannot embed the PostScript ones that
    # Noto CJK ships -- and AR PL UMing follows as a serif fallback with
    # Taiwanese glyph forms.
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/usr/share/fonts/truetype/arphic/ukai.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
)
_TTC_MAX_FACES = 8


def _draws_cjk(font) -> bool:
    """True when the registered face has glyphs for the probe characters."""
    mapping = getattr(getattr(font, "face", None), "charToGlyph", None)
    if not mapping:
        return False
    return all(mapping.get(ord(char)) for char in _CJK_PROBE)


#: A `.ttc` carries one face per regional glyph convention. These documents
#: are Taiwanese, so prefer the Taiwanese forms over the Simplified ones that
#: usually sit at index 0.
_FACE_PREFERENCE = ("TW", "HK", "TC", "JP")


def _face_rank(font) -> int:
    name = getattr(getattr(font, "face", None), "name", b"")
    if isinstance(name, bytes):
        name = name.decode("latin-1", "replace")
    upper = name.upper()
    for rank, marker in enumerate(_FACE_PREFERENCE):
        if marker in upper:
            return rank
    return len(_FACE_PREFERENCE)


def _register_cjk_ttf() -> str | None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    override = os.environ.get("DOCSUBSTRATE_TEXT_FONT")
    candidates = (override, *_FONT_CANDIDATES) if override else _FONT_CANDIDATES
    for entry in candidates:
        path = Path(entry).expanduser()
        if not path.is_file() or not os.access(path, os.R_OK):
            continue
        viable = []
        for index in (range(_TTC_MAX_FACES) if path.suffix.lower() == ".ttc" else (0,)):
            try:
                font = TTFont("DocSubstrateText", str(path), subfontIndex=index)
            except Exception:
                break  # index past the end of the collection
            if _draws_cjk(font):
                viable.append((_face_rank(font), index, font))
        if not viable:
            continue
        rank, index, font = min(viable, key=lambda item: (item[0], item[1]))
        pdfmetrics.registerFont(font)
        _logger.info(
            "DocSubstrate text font: %s face %d (%s)",
            path, index, getattr(font.face, "name", "?"),
        )
        _register_bold_beside(path, "DocSubstrateText", "DocSubstrateTextBold")
        return "DocSubstrateText"
    return None


#: Latin faces, in preference order. A host can provide Odoo's Lato face;
#: otherwise the renderer falls through to locally available public faces.
_LATIN_CANDIDATES = (
    "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
    "~/.fonts/Lato-Regular.ttf",
)

_REGISTERED_LATIN = None

#: Bold faces, registered beside their regular one and keyed by it. A face
#: with no bold companion stays absent rather than being faked: a synthesised
#: bold is a different shape from the one the source engine drew.
_BOLD_COMPANIONS: dict[str, str] = {}


def _register_bold_beside(regular_path, regular_name: str, name: str) -> None:
    """Register `<stem>-Bold` next to a regular face, when the file is there.

    Odoo ships Lato's weights side by side, and the appliance installs the
    converted Noto Sans TC the same way, so the bold file is found by name
    rather than configured separately.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    stem = Path(regular_path)
    for sibling in (
        stem.with_name(stem.stem + "-Bold" + stem.suffix),
        stem.with_name(stem.stem.replace("-Reg-", "-Bol-") + stem.suffix),
        stem.with_name(stem.stem.replace("-conv", "-conv-Bold") + stem.suffix),
    ):
        if sibling == stem or not sibling.is_file() or not os.access(sibling, os.R_OK):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, str(sibling)))
        except Exception:
            _logger.debug("ReportLab rejected bold face %s", sibling, exc_info=True)
            continue
        _BOLD_COMPANIONS[regular_name] = name
        _logger.info("DocSubstrate bold face for %s: %s", regular_name, sibling)
        return
    _logger.info("no bold face found beside %s; bold runs will draw regular", stem)


def registered_latin_font(path: str | None = None) -> str | None:
    """A Latin text face, or None to fall back on the CJK one for everything.

    Han glyphs are full-width in every CJK face, so CJK advances already
    agree with the source engine to within 0.2%. Latin does not: that is
    where a single-font renderer loses its width fidelity.
    """
    global _REGISTERED_LATIN
    if _REGISTERED_LATIN is not None:
        return _REGISTERED_LATIN or None
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    override = os.environ.get("DOCSUBSTRATE_LATIN_FONT")
    for entry in (path, override, *_LATIN_CANDIDATES):
        if not entry:
            continue
        candidate = Path(entry).expanduser()
        if not candidate.is_file() or not os.access(candidate, os.R_OK):
            continue
        try:
            pdfmetrics.registerFont(TTFont("DocSubstrateLatin", str(candidate)))
        except Exception:
            _logger.debug("ReportLab rejected Latin font %s", candidate, exc_info=True)
            continue
        _logger.info("DocSubstrate Latin font: %s", candidate)
        _register_bold_beside(candidate, "DocSubstrateLatin", "DocSubstrateLatinBold")
        _REGISTERED_LATIN = "DocSubstrateLatin"
        return _REGISTERED_LATIN
    _REGISTERED_LATIN = ""
    return None


#: Scripts a CJK face must draw: ideographs, kana, and full-width forms.
def _needs_cjk_face(char: str) -> bool:
    code = ord(char)
    return (
        0x2E80 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0xFE30 <= code <= 0xFE4F
        or 0xFF00 <= code <= 0xFF60
        or 0xFFE0 <= code <= 0xFFE6
    )


@dataclass(frozen=True, slots=True)
class FontSet:
    """One face per script, the way the browser resolves a font stack.

    ReportLab has no font fallback: split a run before measuring or drawing so
    each script uses its selected face.
    """

    cjk: str
    latin: str | None = None
    #: Faces a stylesheet declared through `@font-face`, already registered,
    #: keyed by the family name the document asks for. Empty when the host
    #: offered no way to resolve them, which is every caller that has only
    #: the two script faces -- so a run that names nothing behaves exactly as
    #: it did before this existed.
    declared: Mapping[str, str] = field(default_factory=dict)

    def font_for(self, char: str, family: str | None = None) -> str:
        """The face to draw one character in.

        A declared family wins outright when it resolved, because the
        stylesheet named it and the script heuristic below is a fallback for
        runs that name nothing. It has to: the icon glyphs live at private-use
        codepoints, which are not CJK by any test, so the script rule would
        hand them to the Latin face -- the one face guaranteed not to have
        them.
        """
        if family:
            face = self.declared.get(family)
            if face:
                return face
        if self.latin and not _needs_cjk_face(char):
            return self.latin
        return self.cjk

    def vertical_metrics(self) -> tuple[float, float]:
        """The primary face's ascent and descent, in ems, both positive.

        CSS puts the first baseline of a block at half-leading plus the
        ascent, not a whole line-height down, so a planner that cannot ask
        the font how tall it is has to guess -- and guessed about 2mm long
        on every block that starts with text.
        """
        from reportlab.pdfbase import pdfmetrics

        face = pdfmetrics.getFont(self.latin or self.cjk).face
        ascent = (face.ascent or 718) / 1000.0
        descent = abs(face.descent or -207) / 1000.0
        return (ascent, descent)

    def segments(self, text: str, family: str | None = None) -> tuple[tuple[str, str], ...]:
        """Split into the longest runs that share a face."""
        if not text:
            return ()
        if family and self.declared.get(family):
            return ((text, self.declared[family]),)
        if not self.latin:
            return ((text, self.cjk),)
        runs = []
        start = 0
        current = self.font_for(text[0], family)
        for index in range(1, len(text)):
            face = self.font_for(text[index], family)
            if face != current:
                runs.append((text[start:index], current))
                start, current = index, face
        runs.append((text[start:], current))
        return tuple(runs)

    def width_pt(self, text: str, size_pt: float, family: str | None = None) -> float:
        from reportlab.pdfbase.pdfmetrics import stringWidth

        return sum(
            stringWidth(run, face, size_pt)
            for run, face in self.segments(text, family)
        )

    def bold(self, face: str) -> str:
        """The bold companion of a face, or the face itself if it has none.

        Returning the face unchanged is what silently dropped every bold run
        in production: the stylesheet asks for weight 500 on a table header
        and `bolder` on a total, and both came out regular because only
        Helvetica had a mapping here.
        """
        if face == "Helvetica":
            return "Helvetica-Bold"
        return _BOLD_COMPANIONS.get(face) or face


class _DeclaredFaces(Mapping):
    """Faces named by `@font-face`, registered the first time one is asked for.

    Lazy because a bundle declares 74 of them and a document draws at most a
    couple. Negative answers are cached too: a family with no readable file
    must not send the host back to the filesystem once per run.

    A family that does not resolve is simply absent, so `FontSet.font_for`
    falls through to the script rule -- the same behaviour every caller had
    before any of this existed.
    """

    def __init__(self, assets_for, faces=None):
        from docsubstrate.font_faces import FontFace, FontSource

        if faces is None:
            from docsubstrate.odoo_report_profile import FONT_FACE_RULES

            faces = tuple(
                FontFace(family, tuple(FontSource(u, f) for u, f in sources),
                         weight, style)
                for family, sources, weight, style in FONT_FACE_RULES
            )
        self._assets_for = assets_for
        self._faces = faces
        self._resolved: dict[str, str | None] = {}

    def _register(self, family: str) -> str | None:
        from docsubstrate.font_faces import resolve_face

        found = resolve_face(family, self._faces, self._assets_for)
        if not found.resolved:
            if found.reason and "no @font-face" not in found.reason:
                _logger.info(
                    "no drawable file for declared family %r: %s (tried %s)",
                    family, found.reason, ", ".join(found.considered) or "nothing",
                )
            return None
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # A stable digest, not `hash()`: string hashing is randomised per
        # process, and a font name that changes between runs makes the same
        # document produce a different PDF every time.
        digest = hashlib.sha256(family.encode("utf-8")).hexdigest()[:12]
        name = f"DocSubstrateFace-{digest}"
        try:
            pdfmetrics.registerFont(TTFont(name, found.path))
        except Exception:
            _logger.debug("ReportLab rejected %s for %r", found.path, family,
                          exc_info=True)
            return None
        _logger.info("declared face %r -> %s", family, found.path)
        return name

    def __getitem__(self, family):
        if family not in self._resolved:
            self._resolved[family] = self._register(family)
        found = self._resolved[family]
        if found is None:
            raise KeyError(family)
        return found

    def get(self, family, default=None):
        try:
            return self[family]
        except KeyError:
            return default

    def __iter__(self):
        return iter(name for name, face in self._resolved.items() if face)

    def __len__(self):
        return sum(1 for face in self._resolved.values() if face)


def registered_font_set(latin_path: str | None = None, font_assets=None) -> FontSet:
    return FontSet(
        cjk=registered_text_font(),
        latin=registered_latin_font(latin_path),
        declared=_DeclaredFaces(font_assets) if font_assets else {},
    )


def registered_text_font() -> str:
    """Resolve a text face that can actually draw CJK.

    Helvetica cannot, and a report that silently falls back to it prints
    every Chinese character as a box -- which looks like a rendering bug
    rather than a missing font. So the face is chosen by probing its glyph
    coverage, and the fallback is logged loudly enough to be found.
    """
    global _REGISTERED_FONT
    if _REGISTERED_FONT:
        return _REGISTERED_FONT

    name = _register_cjk_ttf()
    if name:
        _REGISTERED_FONT = name
        return _REGISTERED_FONT

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont("MHei-Medium"))
        _REGISTERED_FONT = "MHei-Medium"
        return _REGISTERED_FONT
    except Exception:
        _logger.debug("ReportLab CID font MHei-Medium unavailable", exc_info=True)

    _logger.warning(
        "No CJK-capable text font found; falling back to Helvetica, so CJK will "
        "render as empty boxes. Install a Noto CJK package or set "
        "DOCSUBSTRATE_TEXT_FONT to a font path."
    )
    _REGISTERED_FONT = "Helvetica"
    return _REGISTERED_FONT


def _image_source(value: str):
    global _IMAGE_READER_CACHE_BYTES
    if not value.startswith("data:image/"):
        return value
    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise ValueError("only base64 data-image URIs are supported")
    media_type = header[5:].split(";", 1)[0]
    if media_type == "image/svg+xml":
        raise ValueError("SVG must be resolved to a Canvas-compatible asset before execution")
    from reportlab.lib.utils import ImageReader

    payload = base64.b64decode(encoded)
    # ImageReader lazily opens and decodes its payload.  The report article's
    # company-selected background is byte-identical on every page and every
    # document in a worker, so constructing a fresh reader here made the same
    # PNG pay that cost for every render.  Content is the authority: the URI,
    # attachment id and declared media type may differ while the bytes remain
    # identical.  A bounded SHA-256 keyed cache therefore reuses only the
    # decoded content it actually identifies, without retaining every report
    # image for the lifetime of an Odoo worker.
    checksum = hashlib.sha256(payload).digest()
    cached = _IMAGE_READER_CACHE.get(checksum)
    if cached is not None:
        _IMAGE_READER_CACHE.move_to_end(checksum)
        return cached[0]
    reader = ImageReader(BytesIO(payload))
    # Open enough of the source to establish dimensions, but do not expand its
    # RGB/alpha planes yet -- eagerly decoding here would retain most of the
    # cold-start cost this cache exists to avoid, for images this worker
    # never actually draws again.
    reader.getSize()
    decoded_size = len(payload)
    # A 16 MiB compressed response can expand far beyond that size.  Bound
    # retained decoded pixels by bytes as well as entry count, and simply
    # decline to cache an individual image larger than the whole allowance.
    if decoded_size <= _IMAGE_READER_CACHE_MAX_BYTES:
        _IMAGE_READER_CACHE[checksum] = (reader, decoded_size)
        _IMAGE_READER_CACHE_BYTES += decoded_size
        _IMAGE_READER_CACHE.move_to_end(checksum)
        while (
            len(_IMAGE_READER_CACHE) > _IMAGE_READER_CACHE_MAX
            or _IMAGE_READER_CACHE_BYTES > _IMAGE_READER_CACHE_MAX_BYTES
        ):
            _discarded, weight = _IMAGE_READER_CACHE.popitem(last=False)[1]
            _IMAGE_READER_CACHE_BYTES -= weight
    return reader


def encoded_image_cache_producer() -> str:
    """Return every implementation input that can change encoded streams.

    ReportLab owns the RGB/alpha-to-XObject algorithm, Pillow owns source
    decoding, and zlib owns Flate output. Kept for callers (the Odoo host's
    ``docsubstrate.render.cache``) that still tag stored rows with it; this
    module itself no longer builds or persists an encoded-image cache -- see
    ``_draw_image`` below and
    ``docs/reportlab-xobject-cache-public-api-compat.md``.
    """
    import PIL
    import reportlab
    from reportlab import rl_config

    parts = {
        "codec": "docsubstrate-reportlab-xobject-1",
        "pillow": PIL.__version__,
        "reportlab": reportlab.Version,
        "use_a85": int(bool(rl_config.useA85)),
        "zlib_build": zlib.ZLIB_VERSION,
        "zlib_level": _ENCODED_IMAGE_ZLIB_LEVEL,
        "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
    }
    return ";".join(f"{key}={parts[key]}" for key in sorted(parts))


def _draw_image(
    canvas,
    image,
    x,
    y,
    *,
    width,
    height,
    preserve_aspect_ratio=False,
    mask="auto",
):
    """Draw an image through ReportLab's own public, documented entry point.

    ``Canvas.drawImage`` is not a thinner alternative to what this module used
    to do by hand -- reading its source (``reportlab.pdfgen.canvas.Canvas.
    drawImage``) shows it performs exactly the same steps this file's
    previous ``_prime_encoded_image``/``_draw_primed_image`` reimplemented:
    hash the decoded planes, look the name up in ``self._doc.idToObject``,
    build a ``pdfdoc.PDFImageXObject`` and register it via ``self.
    _setXObjects``/``self._doc.Reference``/``self._doc.addForm`` on a miss,
    handle ``_smask``, then append the ``Do`` operator to ``self._code`` and
    track ``self._formsinuse``. Calling the public method instead of
    reimplementing its private internals gets the identical per-canvas
    dedup (a repeated image within one document still costs one compress,
    not one per draw) for free, and stays correct across ReportLab releases
    that are free to change those private names without notice.

    What it does not do, because no documented ReportLab API exposes it, is
    accept an already-compressed XObject stream produced by an earlier
    Canvas/process and register it without recompressing. That optimization
    -- this module's old persistent ``EncodedImageStore`` path -- has no
    public-API equivalent and is not reimplemented here; see
    ``docs/reportlab-xobject-cache-public-api-compat.md`` for the
    counterexample and ``ReportLabCanvasRenderer.__init__``'s warning for the
    caller-visible consequence.
    """
    return canvas.drawImage(
        image,
        x,
        y,
        width=width,
        height=height,
        mask=mask,
        preserveAspectRatio=preserve_aspect_ratio,
    )


class ReportLabCanvasRenderer:
    """Execute resolved pages directly through reportlab.pdfgen.canvas.Canvas."""

    name = "reportlab-canvas"

    def __init__(self, *, encoded_image_store: EncodedImageStore | None = None):
        # Accepted for API compatibility with existing callers (the Odoo host
        # passes ``OdooEncodedImageStore``), but never read from or written
        # to: no documented ReportLab API can register an already-compressed
        # XObject stream from an earlier Canvas/process without recompressing
        # it, so there is nothing sound to persist here. This is an explicit
        # alpha limitation, not a silently dropped optimization -- see
        # docs/reportlab-xobject-cache-public-api-compat.md.
        if encoded_image_store is not None:
            _logger.warning(
                "ReportLabCanvasRenderer: encoded_image_store is configured but "
                "unused in this alpha -- no documented ReportLab public API can "
                "persist or restore a pre-compressed image XObject stream "
                "across Canvas instances; every image now renders through the "
                "public Canvas.drawImage(). See "
                "docs/reportlab-xobject-cache-public-api-compat.md."
            )
        self.encoded_image_store = encoded_image_store

    def render_bytes(self, document: ResolvedDocument) -> bytes:
        try:
            from reportlab.pdfgen.canvas import Canvas
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "ReportLab Canvas backend requires the 'reportlab' package"
            ) from exc

        output = BytesIO()
        if not document.pages:
            return b""

        first = document.pages[0]
        canvas = Canvas(
            output,
            pagesize=(
                _page_pt(
                    first.width_mm,
                    paper_format=first.paper_format,
                    dpi=first.dpi,
                ),
                _page_pt(
                    first.height_mm,
                    paper_format=first.paper_format,
                    dpi=first.dpi,
                ),
            ),
            pdfVersion=_PDF_VERSION,
            # ReportLab's default trailer ``/ID`` (``pdfdoc.PDFDocument.ID``,
            # "unless in invariant mode") is not a pure function of the
            # PagePlan: it folds in the wall-clock time the canvas was built,
            # so the same resolved document renders to different bytes on
            # every call. ``invariant`` is a documented public constructor
            # parameter that removes exactly that source of randomness;
            # nothing else about drawn content changes.
            invariant=1,
        )

        for page_index, page in enumerate(document.pages):
            if page_index:
                canvas.setPageSize((
                    _page_pt(page.width_mm, paper_format=page.paper_format, dpi=page.dpi),
                    _page_pt(page.height_mm, paper_format=page.paper_format, dpi=page.dpi),
                ))

            for command in page.commands:
                if isinstance(command, TextRun):
                    if command.fill_rgb:
                        canvas.setFillColorRGB(*command.fill_rgb)
                    else:
                        canvas.setFillColorRGB(0, 0, 0)
                    canvas.setFont(command.font_name, command.font_size_pt)
                    if command.char_space_pt:
                        text = canvas.beginText(_pt(command.x_mm), _pt(command.y_mm))
                        text.setFont(command.font_name, command.font_size_pt)
                        text.setCharSpace(command.char_space_pt)
                        text.textOut(command.text)
                        canvas.drawText(text)
                    else:
                        canvas.drawString(_pt(command.x_mm), _pt(command.y_mm), command.text)
                elif isinstance(command, Line):
                    canvas.setStrokeColorRGB(*(command.stroke_rgb or (0, 0, 0)))
                    canvas.setLineWidth(command.width_pt)
                    canvas.setDash(command.dash_array_pt or [])
                    canvas.line(
                        _pt(command.x1_mm),
                        _pt(command.y1_mm),
                        _pt(command.x2_mm),
                        _pt(command.y2_mm),
                    )
                    canvas.setDash()
                elif isinstance(command, PagePath):
                    if command.fill_rgb:
                        canvas.setFillColorRGB(*command.fill_rgb)
                    translucent = command.fill_alpha != 1.0
                    if translucent:
                        canvas.setFillAlpha(command.fill_alpha)
                    try:
                        outline = canvas.beginPath()
                        for segment in command.segments:
                            name = segment[0]
                            if name == "m":
                                outline.moveTo(_pt(segment[1]), _pt(segment[2]))
                            elif name == "l":
                                outline.lineTo(_pt(segment[1]), _pt(segment[2]))
                            elif name == "c":
                                outline.curveTo(*(_pt(v) for v in segment[1:]))
                            elif name == "z":
                                outline.close()
                        canvas.drawPath(outline, stroke=0, fill=1)
                    finally:
                        if translucent:
                            canvas.setFillAlpha(1.0)
                elif isinstance(command, Circle):
                    if command.fill_rgb:
                        canvas.setFillColorRGB(*command.fill_rgb)
                    translucent = command.fill_alpha != 1.0
                    if translucent:
                        canvas.setFillAlpha(command.fill_alpha)
                    try:
                        canvas.circle(
                            _pt(command.cx_mm), _pt(command.cy_mm), _pt(command.radius_mm),
                            stroke=0, fill=1,
                        )
                    finally:
                        if translucent:
                            canvas.setFillAlpha(1.0)
                elif isinstance(command, Rect):
                    if command.fill_rgb:
                        canvas.setFillColorRGB(*command.fill_rgb)
                    if command.stroke_rgb:
                        canvas.setStrokeColorRGB(*command.stroke_rgb)
                    else:
                        canvas.setStrokeColorRGB(0, 0, 0)
                    canvas.setLineWidth(command.line_width_pt)
                    canvas.setDash(command.dash_array_pt or [])
                    # A translucent fill (a CSS colour with real alpha, e.g.
                    # a table stripe) must actually blend with whatever the
                    # page already holds beneath it -- page art is painted
                    # before the body -- rather than paint as opaque.
                    translucent = command.fill_alpha != 1.0
                    if translucent:
                        canvas.setFillAlpha(command.fill_alpha)
                    try:
                        corners = command.corner_radii_mm
                        if corners and len(set(corners)) > 1:
                            _rounded_path(
                                canvas,
                                _pt(command.x_mm), _pt(command.y_mm),
                                _pt(command.width_mm), _pt(command.height_mm),
                                [_pt(r) for r in corners],
                                stroke=int(command.stroke),
                                fill=int(command.fill or bool(command.fill_rgb)),
                            )
                            canvas.setDash()
                            continue
                        draw_rect = canvas.rect
                        if corners:
                            command = replace(command, radius_mm=corners[0])
                        if command.radius_mm > 0:
                            def draw_rect(x, y, w, h, stroke, fill, _r=command.radius_mm):
                                canvas.roundRect(x, y, w, h, _pt(_r), stroke=stroke, fill=fill)
                        draw_rect(
                            _pt(command.x_mm),
                            _pt(command.y_mm),
                            _pt(command.width_mm),
                            _pt(command.height_mm),
                            stroke=int(command.stroke),
                            fill=int(command.fill or bool(command.fill_rgb)),
                        )
                        canvas.setDash()
                    finally:
                        if translucent:
                            canvas.setFillAlpha(1.0)
                elif isinstance(command, ImageRef):
                    source = _image_source(command.path)
                    _draw_image(
                        canvas,
                        source,
                        _pt(command.x_mm),
                        _pt(command.y_mm),
                        width=_pt(command.width_mm),
                        height=_pt(command.height_mm),
                        preserve_aspect_ratio=command.preserve_aspect_ratio,
                        # A logo is a PNG with an alpha channel. Without a
                        # mask ReportLab paints those pixels black, which
                        # reads as a black plate behind the logo rather than
                        # as the transparency the source engine honours.
                        mask="auto",
                    )
                else:  # pragma: no cover - protects future command additions
                    raise TypeError(f"Unsupported page command: {type(command)!r}")

            canvas.showPage()

        canvas.save()
        return output.getvalue()
