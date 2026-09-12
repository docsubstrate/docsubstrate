"""What `@font-face` says a family is, and how the host is asked for it.

A face reaches this engine as two separate facts that only the stylesheet can
join. The document says *which family* it wants -- through `font-family`, or
through the `font` shorthand that expands to it -- and `@font-face` says
*where that family's file lives*, as a list of URLs with formats. Neither
half is a path this code is allowed to know: hard-coding a module directory
ties the engine to one Odoo layout, and a family-to-path table is the same
mistake written as a dictionary.

So the rule here is that everything about which file to open comes from the
CSS, and everything about where a URL is on disk comes from the host. The
port between them is one callable and it is not font-specific in shape: it
answers "what can you serve from where this URL points".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: The formats ReportLab can register. It reads sfnt containers -- TrueType
#: and OpenType -- and nothing else. `woff` and `woff2` are the same glyphs
#: in a compressed wrapper it has no decoder for, so a face offered only in
#: those is a real capability gap and is reported as one rather than
#: approximated with a different font.
SFNT_SUFFIXES = (".ttf", ".otf", ".ttc")

_FONT_FACE = re.compile(r"@font-face\s*\{([^}]*)\}", re.IGNORECASE)
_DECLARATION = re.compile(r"([-a-zA-Z]+)\s*:\s*([^;]+)")
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
#: One `src` entry: a `url(...)` and the `format(...)` that may follow it.
_SOURCE = re.compile(
    r"""url\(\s*(?P<quote>['"]?)(?P<url>[^'")]+)(?P=quote)\s*\)"""
    r"""(?:\s*format\(\s*['"]?(?P<format>[^'")]+)['"]?\s*\))?""",
    re.IGNORECASE,
)


def unquote(text: str) -> str:
    """A CSS string or identifier as its bare value."""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


@dataclass(frozen=True)
class FontSource:
    url: str
    format: str | None = None


@dataclass(frozen=True)
class FontFace:
    """One `@font-face` block, reduced to what choosing a file needs."""

    family: str
    sources: tuple[FontSource, ...] = ()
    weight: str = "normal"
    style: str = "normal"


def parse_font_faces(css: str) -> tuple[FontFace, ...]:
    """Every `@font-face` in a stylesheet, in source order.

    Source order is kept because a later block for the same family replaces
    an earlier one for the same weight and style, exactly as a later rule
    replaces an earlier declaration.
    """
    faces: list[FontFace] = []
    for block in _FONT_FACE.finditer(_COMMENT.sub("", css)):
        body = block.group(1)
        declared = {
            name.strip().lower(): value.strip()
            for name, value in _DECLARATION.findall(body)
        }
        family = unquote(declared.get("font-family", ""))
        if not family:
            continue
        sources = tuple(
            FontSource(match.group("url").strip(),
                       (match.group("format") or "").lower() or None)
            for match in _SOURCE.finditer(declared.get("src", ""))
        )
        faces.append(FontFace(
            family=family,
            sources=sources,
            weight=declared.get("font-weight", "normal").lower(),
            style=declared.get("font-style", "normal").lower(),
        ))
    return tuple(faces)


def family_stack(value: str | None) -> tuple[str, ...]:
    """A `font-family` value as the list of families it actually names.

    Splitting on commas is enough here because a family name may be quoted
    but may not contain one. The generic families -- `serif`, `sans-serif`
    and the rest -- stay in the list; they simply never match an
    `@font-face`, which is what makes them fall through to the host's own
    faces rather than needing to be recognised.
    """
    if not value:
        return ()
    return tuple(
        name for name in (unquote(part) for part in value.split(",")) if name
    )


@dataclass
class FaceResolution:
    """Which file a family resolved to, or why it did not.

    The unresolved cases are kept apart because they mean different things.
    A family with no `@font-face` is a generic or host-installed name and is
    nobody's error; a family whose every source is a format this renderer
    cannot read is a capability gap that has to be reported.
    """

    family: str
    path: str | None = None
    reason: str | None = None
    considered: tuple[str, ...] = field(default_factory=tuple)

    @property
    def resolved(self) -> bool:
        return self.path is not None


def _basename(url: str) -> str:
    """The file a URL names, without the cache-buster or fragment."""
    target, _, _ = url.partition("?")
    target, _, _ = target.partition("#")
    return target.rsplit("/", 1)[-1]


#: `normal` and `400` are the same weight, and `bold` and `700` are the same
#: weight. A family that spells its `@font-face` one way and its rules the
#: other -- which Lato does, nine faces by number against a shorthand that
#: says `normal` -- would otherwise match none of them and fall back to
#: whichever came first. That is Lato Hairline.
_WEIGHT_ALIASES = {"normal": "400", "bold": "700"}


def _same_weight(left, right) -> bool:
    left, right = str(left).strip().lower(), str(right).strip().lower()
    return _WEIGHT_ALIASES.get(left, left) == _WEIGHT_ALIASES.get(right, right)


def _is_sfnt(path) -> bool:
    return str(path).lower().endswith(SFNT_SUFFIXES)


def resolve_face(family, faces, assets_for, *, weight="normal", style="normal"):
    """The file to register for `family`, asking the host where URLs point.

    `assets_for` is the port: given the URL an `@font-face` names, it returns
    the font files the host can serve from where that URL points, as paths.
    It is given the URL from the stylesheet and nothing else -- no family, no
    module, no format -- so neither this function nor the host can grow a
    table keyed by the name of a font.

    Sources are tried in the order the stylesheet lists them, which is the
    order a browser tries them, and the file each one *names* is what gets
    considered. Taking any readable font from the directory instead would
    resolve `Lato-Reg-webfont.woff` to whichever Lato sorted first, which is
    a different weight of the right family -- the kind of wrong answer that
    looks right.

    Only when no source names a container this renderer can read does it look
    beside them, and then only for the same file in another wrapper: same
    stem, readable extension. That is what recovers the icon faces, whose
    `@font-face` offers `woff2` and `woff` to a browser while the sfnt sits
    unlisted in the same directory.
    """
    matching = [f for f in faces if f.family.lower() == family.lower()]
    if not matching:
        return FaceResolution(family, reason="no @font-face declares this family")

    exact = [f for f in matching
             if _same_weight(f.weight, weight)
             and f.style.lower() == str(style).lower()]
    matching = exact or matching

    considered: list[str] = []
    for face in matching:
        for source in face.sources:
            considered.append(source.url)
            wanted = _basename(source.url)
            for path in assets_for(source.url) or ():
                if _basename(str(path)) == wanted and _is_sfnt(path):
                    return FaceResolution(family, path=str(path),
                                          considered=tuple(considered))

    for face in matching:
        for source in face.sources:
            stem = _basename(source.url).rsplit(".", 1)[0]
            for path in assets_for(source.url) or ():
                name = _basename(str(path))
                if name.rsplit(".", 1)[0] == stem and _is_sfnt(path):
                    return FaceResolution(family, path=str(path),
                                          considered=tuple(considered))

    return FaceResolution(
        family,
        reason="every source is a format this renderer cannot read, and no "
               f"sfnt sits beside them; it reads {', '.join(SFNT_SUFFIXES)}",
        considered=tuple(considered),
    )
