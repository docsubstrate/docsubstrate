"""Acquire and normalize image payloads before page execution.

The source contract has two independent authorities:

* URL acquisition follows the evaluated ``src`` plus the host's report base
  URL.  Odoo's own ``ir.actions.report._get_report_url()`` supplies that base;
  the engine does not guess a tenant hostname.
* This engine's *paint* decoder follows payload bytes, not the declared MIME
  type. Failed-replaced-element sizing is a separate compatibility contract
  pinned by synthetic cases in ``tests/test_image_assets.py``. The exact
  external behavior revision and file locations used for review are recorded
  outside executable modules in ``CODE-PROVENANCE.json``. Which optional
  decoder plugin a particular binary loads is deliberately not generalized.

The bounded SVG contract covers generated rectangle codes and a simple
rectangle-plus-text avatar. An unsupported visible SVG element raises and
therefore becomes the planner's ordinary warned layout gap.
"""

from __future__ import annotations

import base64
import colorsys
import hashlib
import math
import re
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_TRANSFORM_RE = re.compile(r"([A-Za-z]+)\s*\(([^)]*)\)")
_NATURAL_SIZE_CACHE_MAX = 64
_NATURAL_SIZE_CACHE = OrderedDict()
_URL_PAYLOAD_CACHE_MAX = 32
_URL_PAYLOAD_CACHE_MAX_BYTES = 64 * 1024 * 1024
_URL_PAYLOAD_CACHE = OrderedDict()
_URL_PAYLOAD_CACHE_BYTES = 0


def _data_uri(media_type: str, payload: bytes) -> str:
    return (
        f"data:{media_type};base64,"
        + base64.b64encode(payload).decode("ascii")
    )


def _decode_data_uri(value: str) -> tuple[str, bytes]:
    header, separator, encoded = value.partition(",")
    if not separator or ";base64" not in header:
        raise ValueError("only base64 data-image URIs are supported")
    media_type = header[5:].split(";", 1)[0]
    return media_type, base64.b64decode(encoded)


def _is_svg(payload: bytes) -> bool:
    head = payload[:4096].lstrip()
    if head.startswith(b"<?xml"):
        end = head.find(b"?>")
        head = head[end + 2 :].lstrip() if end >= 0 else head
    if head.startswith(b"<!DOCTYPE"):
        end = head.find(b">")
        head = head[end + 1 :].lstrip() if end >= 0 else head
    return head.startswith(b"<svg")


def _sniff_media_type(payload: bytes, declared: str = "") -> str:
    if _is_svg(payload):
        return "image/svg+xml"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if payload[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if declared.startswith("image/"):
        return declared
    raise ValueError("response is not a recognized image payload")


def _resolved_url(src: str, base_url: str | None) -> str:
    parsed = urlsplit(src)
    if not parsed.scheme:
        if not base_url:
            raise ValueError("relative image URL has no host report base URL")
        target = urljoin(base_url.rstrip("/") + "/", src)
    elif parsed.scheme in {"http", "https"}:
        target = src
        # Odoo may emit its public origin into an absolute /report URL while
        # `_get_report_url()` deliberately points wkhtmltopdf at localhost.
        # The route is the same authoritative source; use the host-provided
        # access origin instead of hairpinning through the public hostname.
        if base_url and parsed.path.startswith("/report/"):
            access = urlsplit(base_url)
            target = urlunsplit((
                access.scheme, access.netloc, parsed.path, parsed.query, ""
            ))
    else:
        raise ValueError(f"unsupported external image URL scheme {parsed.scheme!r}")
    return target


def _clear_url_payload_cache() -> None:
    """Clear the process-local acquisition cache (tests/measurement only)."""
    global _URL_PAYLOAD_CACHE_BYTES
    _URL_PAYLOAD_CACHE.clear()
    _URL_PAYLOAD_CACHE_BYTES = 0


def _cached_url_payload(target: str) -> tuple[str, bytes] | None:
    """Return a verified cached response for the exact access URL.

    URL acquisition and payload decoding are separate cache layers.  The
    complete resolved URL (including origin and query) is authoritative for
    acquisition.  A payload checksum cannot be the lookup key here: obtaining
    that checksum would first require repeating the network request this cache
    exists to avoid.
    """
    global _URL_PAYLOAD_CACHE_BYTES
    cached = _URL_PAYLOAD_CACHE.get(target)
    if cached is None:
        return None
    declared, payload, checksum = cached
    if hashlib.sha256(payload).digest() != checksum:
        _URL_PAYLOAD_CACHE.pop(target)
        _URL_PAYLOAD_CACHE_BYTES -= len(payload)
        return None
    _URL_PAYLOAD_CACHE.move_to_end(target)
    return declared, payload


def _store_url_payload(target: str, declared: str, payload: bytes) -> None:
    global _URL_PAYLOAD_CACHE_BYTES
    size = len(payload)
    if size > _URL_PAYLOAD_CACHE_MAX_BYTES:
        return
    previous = _URL_PAYLOAD_CACHE.pop(target, None)
    if previous is not None:
        _URL_PAYLOAD_CACHE_BYTES -= len(previous[1])
    _URL_PAYLOAD_CACHE[target] = (
        declared,
        payload,
        hashlib.sha256(payload).digest(),
    )
    _URL_PAYLOAD_CACHE_BYTES += size
    while (
        len(_URL_PAYLOAD_CACHE) > _URL_PAYLOAD_CACHE_MAX
        or _URL_PAYLOAD_CACHE_BYTES > _URL_PAYLOAD_CACHE_MAX_BYTES
    ):
        _unused_target, (_declared, evicted, _checksum) = (
            _URL_PAYLOAD_CACHE.popitem(last=False)
        )
        _URL_PAYLOAD_CACHE_BYTES -= len(evicted)


def _fetch_url(src: str, base_url: str | None, *, opener=urlopen):
    target = _resolved_url(src, base_url)
    cached = _cached_url_payload(target)
    if cached is not None:
        declared, payload = cached
        return target, declared, payload

    response = opener(Request(target, headers={"User-Agent": "DocSubstrate/1"}), timeout=10)
    try:
        payload = response.read(16 * 1024 * 1024 + 1)
        if len(payload) > 16 * 1024 * 1024:
            raise ValueError("image response exceeds 16 MiB")
        headers = getattr(response, "headers", None)
        declared = ""
        if headers is not None:
            if hasattr(headers, "get_content_type"):
                declared = headers.get_content_type()
            else:
                declared = (headers.get("Content-Type") or "").split(";", 1)[0]
        _store_url_payload(target, declared, payload)
        return target, declared, payload
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


def resolve_image_source(
    src: str, base_url: str | None = None, *, opener=urlopen
) -> str:
    """Return a Canvas-compatible data URI, sniffing before decoding."""
    if src.startswith("data:image/"):
        declared, payload = _decode_data_uri(src)
    else:
        _target, declared, payload = _fetch_url(src, base_url, opener=opener)
    actual = _sniff_media_type(payload, declared)
    if actual == "image/svg+xml":
        payload = rasterize_svg(payload)
        actual = "image/png"
    return _data_uri(actual, payload)


def svg_payload(src: str, base_url: str | None = None, *, opener=urlopen) -> bytes | None:
    """The SVG bytes behind a source, or None if it is not an SVG.

    Exists so the planner can try drawing an SVG before deciding to
    photograph it. Decoding and content sniffing stay here rather than being
    repeated at the call site, because `resolve_image_source` already learned
    that a declared MIME type is not the payload's own opinion of itself.
    """
    if src.startswith("data:image/"):
        declared, payload = _decode_data_uri(src)
    else:
        _target, declared, payload = _fetch_url(src, base_url, opener=opener)
    if _sniff_media_type(payload, declared) != "image/svg+xml":
        return None
    return payload


#: Fixed intrinsic size used by the bounded failed-image contract. Synthetic
#: controls exercise the resource and padding dimensions; the external public
#: behavior reference is recorded in ``CODE-PROVENANCE.json``.
_FAILED_IMAGE_PADDING_PX = 4
_FAILED_IMAGE_BROKEN_ICON_SIZE_PX = (16, 16)
FAILED_IMAGE_INTRINSIC_SIZE_PX = (
    _FAILED_IMAGE_PADDING_PX + _FAILED_IMAGE_BROKEN_ICON_SIZE_PX[0],
    _FAILED_IMAGE_PADDING_PX + _FAILED_IMAGE_BROKEN_ICON_SIZE_PX[1],
)


def _is_svg_mislabelled_as_bitmap(declared: str, actual: str) -> bool:
    """Whether the pinned engine would route this payload to its bitmap
    decoder rather than its native SVG engine. The bounded contract selects
    native SVG handling only when the response's *declared* MIME type reads
    exactly `image/svg+xml`; every other declared type takes the bitmap path.

    Whether `BitmapImage`'s own `QImageReader` decoder could still recover
    such a payload by sniffing its content is a separate, build-dependent
    question, so "no SVG plugin at all" is not a claim this module makes.
    The bounded failed-image behavior is fixed by generated payloads in
    `tests/test_image_assets.py`.

    A correctly labelled `image/svg+xml` source is unaffected regardless:
    it reaches the native SVG engine and decodes normally, which is what
    this engine's own rasterization already reproduces for that case."""
    return actual == "image/svg+xml" and declared != "image/svg+xml"


def is_failed_replaced_element(src: str) -> bool:
    """Whether `image_natural_size_px` returns the fixed failed-image size
    for this source rather than the payload's own real dimensions.

    The failed-resource branch uses fixed intrinsic dimensions rather than
    scaling an unstated dimension from the declared width. The public
    synthetic contract pins that distinction.
    """
    if not src.startswith("data:image/"):
        return False
    try:
        declared, payload = _decode_data_uri(src)
        actual = _sniff_media_type(payload, declared)
        return _is_svg_mislabelled_as_bitmap(declared, actual)
    except Exception:
        return False


def image_natural_size_px(src: str) -> tuple[int, int] | None:
    """Read an embedded payload's own dimensions after content sniffing.

    Natural size belongs to the payload, not its declared MIME type --
    with one deliberate exception. `resolve_image_source` sniffs content
    over the declared type when *painting*, because trusting a producer's
    mislabelled `image/png` for an actual SVG payload routes that content to
    a bitmap decoder and can fail before the SVG renderer sees it.
    The bounded compatibility contract instead picks native SVG handling only
    when the response's *declared* MIME type reads exactly `image/svg+xml`;
    everything else -- a `data:image/png` source included -- takes the bitmap
    path before payload decoding. Whether that bitmap path can recover the
    real content through the optional SVG `QImageReader` plugin is a
    build-dependent question, not a general claim made here. The bounded
    synthetic contract models the failed branch with a fixed used size. This
    is intentionally limited to embedded data: an external image is acquired
    by the planner, where the host's authoritative report base URL is
    available.
    """
    if not src.startswith("data:image/"):
        return None
    try:
        declared, payload = _decode_data_uri(src)
        # The declared type is now part of the answer, not just the
        # payload: the *same* SVG bytes, mislabelled `image/png` in one
        # place and correctly labelled `image/svg+xml` in another. Including
        # the declaration prevents one label from contaminating later uses of
        # the same payload bytes.
        checksum = (hashlib.sha256(payload).digest(), declared == "image/svg+xml")
        if checksum in _NATURAL_SIZE_CACHE:
            _NATURAL_SIZE_CACHE.move_to_end(checksum)
            return _NATURAL_SIZE_CACHE[checksum]
        actual = _sniff_media_type(payload, declared)
        if _is_svg_mislabelled_as_bitmap(declared, actual):
            size = FAILED_IMAGE_INTRINSIC_SIZE_PX
        elif actual == "image/svg+xml":
            root = ET.fromstring(payload)
            view = [float(value) for value in _NUMBER_RE.findall(root.get("viewBox") or "")]
            width = _length(root.get("width")) or (view[2] if len(view) == 4 else None)
            height = _length(root.get("height")) or (view[3] if len(view) == 4 else None)
            size = (round(width), round(height)) if width and height else None
        else:
            from PIL import Image

            with Image.open(BytesIO(payload)) as image:
                size = image.size
        _NATURAL_SIZE_CACHE[checksum] = size
        _NATURAL_SIZE_CACHE.move_to_end(checksum)
        while len(_NATURAL_SIZE_CACHE) > _NATURAL_SIZE_CACHE_MAX:
            _NATURAL_SIZE_CACHE.popitem(last=False)
        return size
    except Exception:
        return None


def _length(value: str | None) -> float | None:
    match = _NUMBER_RE.match((value or "").strip())
    return float(match.group(0)) if match else None


def _multiply(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (
        a * g + c * h,
        b * g + d * h,
        a * i + c * j,
        b * i + d * j,
        a * k + c * l + e,
        b * k + d * l + f,
    )


def _transform(value: str | None):
    matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, arguments in _TRANSFORM_RE.findall(value or ""):
        numbers = [float(item) for item in _NUMBER_RE.findall(arguments)]
        if name == "matrix" and len(numbers) == 6:
            part = tuple(numbers)
        elif name == "translate" and numbers:
            part = (1.0, 0.0, 0.0, 1.0, numbers[0], numbers[1] if len(numbers) > 1 else 0.0)
        elif name == "scale" and numbers:
            part = (numbers[0], 0.0, 0.0, numbers[1] if len(numbers) > 1 else numbers[0], 0.0, 0.0)
        else:
            raise ValueError(f"unsupported SVG transform {name!r}")
        matrix = _multiply(matrix, part)
    return matrix


def _point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return (a * x + c * y + e, b * x + d * y + f)


def _styles(element, inherited):
    values = dict(inherited)
    for declaration in (element.get("style") or "").split(";"):
        name, separator, value = declaration.partition(":")
        if separator:
            values[name.strip()] = value.strip()
    for name in ("fill", "font-size", "font-family", "text-anchor"):
        if element.get(name) is not None:
            values[name] = element.get(name)
    return values


def _colour(value: str | None):
    text = (value or "black").strip().lower()
    if text in {"none", "transparent"}:
        return None
    if text.startswith("#"):
        raw = text[1:]
        if len(raw) == 3:
            raw = "".join(channel * 2 for channel in raw)
        if len(raw) == 6:
            return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4)) + (255,)
    match = re.fullmatch(r"rgb\(([^)]*)\)", text)
    if match:
        channels = []
        for piece in match.group(1).split(","):
            piece = piece.strip()
            channels.append(round(float(piece[:-1]) * 2.55) if piece.endswith("%") else round(float(piece)))
        return tuple(channels[:3]) + (255,)
    match = re.fullmatch(r"hsl\(([^,]+),\s*([^,]+)%,\s*([^,]+)%\)", text)
    if match:
        hue, saturation, lightness = map(float, match.groups())
        red, green, blue = colorsys.hls_to_rgb(
            (hue % 360) / 360.0, lightness / 100.0, saturation / 100.0
        )
        return tuple(round(channel * 255) for channel in (red, green, blue)) + (255,)
    raise ValueError(f"unsupported SVG colour {value!r}")


def rasterize_svg(payload: bytes) -> bytes:
    """Rasterize the SVG subset exercised by the public synthetic contract."""
    from PIL import Image, ImageDraw, ImageFont

    root = ET.fromstring(payload)
    tag = root.tag.rsplit("}", 1)[-1]
    if tag != "svg":
        raise ValueError("SVG payload has no svg root")
    view = [float(value) for value in _NUMBER_RE.findall(root.get("viewBox") or "")]
    width = _length(root.get("width")) or (view[2] if len(view) == 4 else None)
    height = _length(root.get("height")) or (view[3] if len(view) == 4 else None)
    if not width or not height:
        raise ValueError("SVG root has no resolved natural dimensions")
    pixel_width = max(1, round(width))
    pixel_height = max(1, round(height))
    image = Image.new("RGBA", (pixel_width, pixel_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    if len(view) == 4:
        root_matrix = (
            pixel_width / view[2], 0.0, 0.0, pixel_height / view[3],
            -view[0] * pixel_width / view[2], -view[1] * pixel_height / view[3],
        )
    else:
        root_matrix = (pixel_width / width, 0.0, 0.0, pixel_height / height, 0.0, 0.0)

    def visit(element, matrix, inherited, *, clipped=False):
        name = element.tag.rsplit("}", 1)[-1]
        if name in {"title", "desc"}:
            return
        if name == "clipPath":
            return
        matrix = _multiply(matrix, _transform(element.get("transform")))
        style = _styles(element, inherited)
        if name == "rect" and not clipped:
            x = _length(element.get("x")) or 0.0
            y = _length(element.get("y")) or 0.0
            w = _length(element.get("width")) or 0.0
            h = _length(element.get("height")) or 0.0
            fill = _colour(style.get("fill"))
            if fill is not None and w > 0 and h > 0:
                draw.polygon([
                    _point(matrix, x, y), _point(matrix, x + w, y),
                    _point(matrix, x + w, y + h), _point(matrix, x, y + h),
                ], fill=fill)
        elif name == "text" and not clipped:
            text = "".join(element.itertext())
            x = _length(element.get("x")) or 0.0
            y = _length(element.get("y")) or 0.0
            px, py = _point(matrix, x, y)
            size = _length(style.get("font-size")) or 16.0
            scale = math.sqrt(abs(matrix[0] * matrix[3] - matrix[1] * matrix[2]))
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", max(1, round(size * scale)))
            except OSError:
                font = ImageFont.load_default()
            anchor = "ms" if style.get("text-anchor") == "middle" else "ls"
            draw.text((px, py), text, fill=_colour(style.get("fill")), font=font, anchor=anchor)
        elif name not in {"svg", "g"}:
            raise ValueError(f"unsupported visible SVG element {name!r}")
        for child in element:
            visit(child, matrix, style, clipped=clipped or name == "clipPath")

    visit(root, root_matrix, {"fill": "black"})
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()

class UnvectorisableSvg(ValueError):
    """This SVG could be drawn, but uses something the plan cannot express.

    Distinct from a malformed or sizeless SVG, which is not a vectorisation
    gap at all -- that image is unusable by either path, and the raster
    fallback already reports it. Conflating the two produced two warnings for
    one broken payload, which is how a warning list stops being read.
    """


@dataclass(frozen=True, slots=True)
class SvgText:
    """A `<text>` kept as text, in SVG user units.

    `anchor` stays under SVG's own name because resolving it needs the width
    of the string in the font that will actually draw it, which this module
    does not have and the planner does. Deciding it here would mean guessing
    a metric, and a guessed metric standing in for a real one is the defect
    this engine keeps rediscovering.
    """

    x: float
    y: float
    text: str
    font_size: float
    fill_rgb: tuple[float, float, float] | None
    #: SVG's `text-anchor`: "start" or "middle".
    anchor: str = "start"


@dataclass(frozen=True, slots=True)
class SvgRect:
    """An axis-aligned filled rectangle, in SVG user units."""

    x: float
    y: float
    width: float
    height: float
    fill_rgb: tuple[float, float, float] | None


#: How far a transform may depart from axis-aligned before a rect stops being
#: expressible as one. Rounding noise in a scale matrix is not rotation.
_AXIS_ALIGNED_EPSILON = 1e-9


def vectorize_svg(payload: bytes):
    """Draw the SVG rather than photograph it.

    Rectangle and text elements remain vector drawing operations, so text is
    not irreversibly baked into a bitmap for downstream consumers.

    Returns the intrinsic size and the shapes in SVG user units. Placement is
    the caller's: it knows the box the image was given and the font metrics
    that `text-anchor` needs.

    Raises `ValueError` for anything it cannot express, which is deliberate.
    A silent fall back to raster would reproduce exactly today's situation
    with no signal that it had happened -- the caller is meant to catch this,
    rasterise, and record that it did.
    """
    root = ET.fromstring(payload)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError("SVG payload has no svg root")
    view = [float(value) for value in _NUMBER_RE.findall(root.get("viewBox") or "")]
    width = _length(root.get("width")) or (view[2] if len(view) == 4 else None)
    height = _length(root.get("height")) or (view[3] if len(view) == 4 else None)
    if not width or not height:
        raise ValueError("SVG has no intrinsic size")

    shapes: list[SvgRect | SvgText] = []

    def visit(element, matrix, inherited, *, clipped=False):
        name = element.tag.rsplit("}", 1)[-1]
        if name in {"title", "desc"}:
            return
        if name == "clipPath":
            return
        matrix = _multiply(matrix, _transform(element.get("transform")))
        style = _styles(element, inherited)
        if name == "rect" and not clipped:
            x = _length(element.get("x")) or 0.0
            y = _length(element.get("y")) or 0.0
            w = _length(element.get("width")) or 0.0
            h = _length(element.get("height")) or 0.0
            fill = _colour(style.get("fill"))
            if fill is not None and w > 0 and h > 0:
                if abs(matrix[1]) > _AXIS_ALIGNED_EPSILON or abs(matrix[2]) > _AXIS_ALIGNED_EPSILON:
                    # A rotated or skewed rect is not an axis-aligned box, and
                    # emitting one anyway would draw the wrong shape quietly.
                    raise UnvectorisableSvg(
                        "rotated or skewed rect cannot be a Rect"
                    )
                x0, y0 = _point(matrix, x, y)
                x1, y1 = _point(matrix, x + w, y + h)
                shapes.append(SvgRect(
                    min(x0, x1), min(y0, y1),
                    abs(x1 - x0), abs(y1 - y0),
                    tuple(channel / 255.0 for channel in fill[:3]),
                ))
        elif name == "text" and not clipped:
            text = "".join(element.itertext())
            x = _length(element.get("x")) or 0.0
            y = _length(element.get("y")) or 0.0
            px, py = _point(matrix, x, y)
            size = _length(style.get("font-size")) or 16.0
            scale = math.sqrt(abs(matrix[0] * matrix[3] - matrix[1] * matrix[2]))
            fill = _colour(style.get("fill"))
            if text.strip():
                shapes.append(SvgText(
                    px, py, text, size * scale,
                    None if fill is None else tuple(c / 255.0 for c in fill[:3]),
                    (style.get("text-anchor") or "start").strip().lower(),
                ))
        elif name not in {"svg", "g"}:
            raise UnvectorisableSvg(f"unsupported visible SVG element {name!r}")
        for child in element:
            visit(child, matrix, style, clipped=clipped or name == "clipPath")

    root_matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    if len(view) == 4 and view[2] and view[3]:
        root_matrix = (
            width / view[2], 0.0, 0.0, height / view[3],
            -view[0] * width / view[2], -view[1] * height / view[3],
        )
    visit(root, root_matrix, {})
    return (width, height), tuple(shapes)
