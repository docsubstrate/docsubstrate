"""A small CSS cascade over the stylesheet wkhtmltopdf actually reads.

Odoo compiles every report's styling into one attachment,
``web.report_assets_common.min.css`` (450 KB on Odoo 19), and hands it to
wkhtmltopdf along with the evaluated HTML.  A renderer that skips it is
guessing at answers the source engine looks up: it re-derives Bootstrap from
memory, hand-carves one "skin" per document layout, and gets the layouts the
deployment does not use exactly as wrong as the one it does.

So this module reads the stylesheet instead.  It is a *small* cascade, not a
browser: selector matching, specificity, ``!important``, source order,
inheritance, and enough value parsing to answer the questions a paginating
engine asks -- what colour, what border, what padding, what alignment.  There
is no layout, no box model, no scripting.  The engine still decides where
boxes go; the stylesheet decides what they look like.

Three properties of Odoo's pipeline shape what is here, and each one is easy
to get wrong in a way that produces a plausible-looking wrong answer:

* **The media type is ``screen``, not ``print``.**  Odoo never passes
  ``--print-media-type`` to wkhtmltopdf (see ``_build_wkhtmltopdf_args`` in
  ``base/models/ir_actions_report.py``), so ``@media print`` blocks in the
  bundle are dead code in the PDF path and ``@media screen`` blocks are live.
  Reading the bundle as if it were print media inverts both.
* **The viewport is the paper.**  ``set_viewport_size`` defaults to ``False``,
  so wkhtmltopdf lays out at the page width rather than at a browser width.
  That decides which Bootstrap breakpoints fire -- A4 lands above the ``md``
  breakpoint and below ``lg``, so ``.col-md-*`` applies and ``.col-lg-*`` does
  not.
* **The company writes CSS.**  ``asset_styles_company_report.scss`` is
  generated per company, so rules like
  ``.o_company_1_layout.o_report_layout_bubble thead th { background-color: … }``
  exist only in that database's bundle.  They come last, so they win ties --
  which is how a company colour reaches a table header at full strength
  rather than as the tint an engine would guess.

The stylesheet is data; its review metadata lives outside this runtime module
in the generated public review map. Runtime imports stay limited to cascade
and paint behavior.

``tinycss2`` is an optional dependency (extra ``css``).  The core stays
dependency-free and every entry point degrades to the hand-carved fallbacks
in :mod:`docsubstrate.odoo_report_theme` when the parser is absent -- but it
degrades *loudly*, via :attr:`Stylesheet.available`, because a silent
fallback to guessed chrome is the failure mode this module exists to end.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from docsubstrate.odoo_report_theme import Fill, TableSkin

__all__ = [
    "CSS_BUNDLE_NAMES",
    "ComputedStyle",
    "Element",
    "MediaContext",
    "Stylesheet",
    "build_element",
    "parse_colour",
    "parse_colour_alpha",
    "parse_length_px",
    "table_skin_from_css",
]

# --- the environment the bundle is read in -----------------------------

#: Two different "pixels per inch", and conflating them is a bug I made once.
#:
#: :data:`CSS_PX_PER_INCH` is how CSS relates its *own* absolute units to each
#: other -- ``1in == 96px``, ``1pt == 96/72 px`` -- and it is 96 by
#: specification, everywhere, forever. Use it to read a length.
#:
#: :data:`PX_PER_INCH` is how many of those pixels wkhtmltopdf then puts in an
#: inch of paper, and it is **112.5** here. Use it to put a length
#: on the page. Reading with 112.5 makes ``1in`` come out as 112.5px, which
#: CSS never says; writing with 96 makes every millimetre 17% too long.
CSS_PX_PER_INCH = 96.0
PX_PER_INCH = 112.5
MM_PER_PX = 25.4 / PX_PER_INCH
PT_PER_PX = 72.0 / PX_PER_INCH

#: Bootstrap's root font size, which every ``rem`` in the bundle is relative
#: to. Odoo does not override the browser default.
ROOT_FONT_SIZE_PX = 16.0

#: The width wkhtmltopdf lays out at: A4 with Odoo's zero-margin paperformat.
#: Only the Bootstrap breakpoints depend on it, and at 930px it still sits
#: above `md` (768) and below `lg` (992) -- the same answer the wrong 794px
#: gave, which is why the breakpoint conclusion survived the bridge being
#: wrong.
VIEWPORT_WIDTH_PX = 210.0 / MM_PER_PX

#: Which attachments make up the styling wkhtmltopdf sees, **in the order it
#: sees them**, per ``web.minimal_layout`` in ``web/views/report_templates.xml``:
#: the PDF bundle first, then the common one.
#:
#: The order is not cosmetic. ``report_assets_pdf`` carries a CSS *reset* that
#: zeroes `font-size` on every element including ``h1``-``h6``; the common
#: bundle carries the Bootstrap rules that give them a size again. Read in the
#: wrong order the reset wins, every heading collapses to body size, and the
#: document title comes out half its width -- which then lands it 25mm to the
#: right of where wkhtmltopdf puts it, because it is right-aligned.
CSS_BUNDLE_NAMES = (
    "web.report_assets_pdf.min.css",
    "web.report_assets_common.min.css",
)

def _tinycss2():
    """Import the parser on use, so the core package keeps zero dependencies."""
    try:
        import tinycss2
    except ImportError as error:  # pragma: no cover - exercised by absence
        raise RuntimeError(
            "report_css needs tinycss2 to read the Odoo report stylesheet; "
            "install the 'css' extra. The 450 KB minified bundle uses "
            "selectors like `.table > :not(caption) > * > *`, which a regular "
            "expression cannot read correctly."
        ) from error
    return tinycss2


# --- media queries -----------------------------------------------------

_MIN_WIDTH_RE = re.compile(r"min-width\s*:\s*([\d.]+)px")
_MAX_WIDTH_RE = re.compile(r"max-width\s*:\s*([\d.]+)px")


@dataclass(frozen=True, slots=True)
class MediaContext:
    """The conditions the bundle is evaluated under.

    The defaults are wkhtmltopdf's, as Odoo invokes it. They are not the
    defaults a browser would give you, which is the point.
    """

    media_type: str = "screen"
    width_px: float = VIEWPORT_WIDTH_PX
    #: wkhtmltopdf expresses no motion preference, so `reduce` never matches.
    prefers_reduced_motion: bool = False

    def matches(self, query: str) -> bool:
        """True when a comma-separated media query list selects this context."""
        return any(self._matches_one(part) for part in query.split(","))

    def _matches_one(self, query: str) -> bool:
        text = query.strip().lower()
        if not text:
            return True
        negated = text.startswith("not ")
        if negated:
            text = text[4:].strip()
        result = self._evaluate(text)
        return not result if negated else result

    def _evaluate(self, text: str) -> bool:
        for word in ("screen", "print", "speech"):
            if re.match(rf"^{word}\b", text) and word != self.media_type:
                return False
        if "prefers-reduced-motion" in text:
            wants_reduce = "reduce" in text
            if wants_reduce != self.prefers_reduced_motion:
                return False
        for found in _MIN_WIDTH_RE.finditer(text):
            if self.width_px < float(found.group(1)):
                return False
        for found in _MAX_WIDTH_RE.finditer(text):
            if self.width_px > float(found.group(1)):
                return False
        # An unrecognised feature is treated as satisfied rather than as a
        # reason to drop the block: dropping rules silently loses styling,
        # while keeping them at worst applies a rule a browser also would.
        return True


# --- the element tree --------------------------------------------------


@dataclass(eq=False)
class Element:
    """One node, carrying only what a selector can ask about.

    This is deliberately not the document IR: selectors need parents,
    siblings and positions, which a flattened block list has thrown away by
    the time it reaches the planner.
    """

    tag: str = "div"
    element_id: str | None = None
    classes: frozenset[str] = frozenset()
    attrs: dict[str, str] = field(default_factory=dict)
    #: Inline declarations already separated and shorthand-expanded by the
    #: evaluated-HTML host. Runtime selector matching consumes these triples
    #: directly; it must not reload tinycss2 merely because one table cell
    #: carries ``style=``.
    inline_declarations: tuple[tuple[str, str, bool], ...] = ()
    parent: Element | None = None
    children: list[Element] = field(default_factory=list)
    #: Resolved styles, cached per pseudo-element. It lives on the node
    #: rather than on the stylesheet because a cache keyed by ``id(node)``
    #: hands one tree's answers to the next one: CPython reuses the id of a
    #: collected object, and probe trees are built and dropped in a loop.
    _styles: dict = field(default_factory=dict, repr=False, compare=False)

    def add(self, spec: str = "div", **attrs) -> Element:
        """Append a child written in selector shorthand: ``td.text-end``."""
        child = build_element(spec, **attrs)
        child.parent = self
        self.children.append(child)
        return child

    # -- position among siblings ---------------------------------------
    @property
    def siblings(self) -> list[Element]:
        return self.parent.children if self.parent is not None else [self]

    @property
    def index(self) -> int:
        siblings = self.siblings
        for position, node in enumerate(siblings):
            if node is self:
                return position
        return 0

    @property
    def previous_sibling(self) -> Element | None:
        position = self.index
        return self.siblings[position - 1] if position > 0 else None

    def type_index(self) -> int:
        """1-based position among siblings sharing this tag."""
        count = 0
        for node in self.siblings:
            if node.tag == self.tag:
                count += 1
            if node is self:
                return count
        return count or 1

    def type_count(self) -> int:
        return sum(1 for node in self.siblings if node.tag == self.tag) or 1

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        text = self.tag
        if self.element_id:
            text += f"#{self.element_id}"
        for name in sorted(self.classes):
            text += f".{name}"
        return f"<{text}>"


_SPEC_RE = re.compile(r"(?P<tag>^[\w-]+)?(?P<rest>(?:[#.][\w-]+)*)$")


def dom_path(element: Element | None) -> str | None:
    """One node's structural address in its own tree.

    This exists so a text anchor in a rendered PDF can be traced back to the
    element that authored it. It is deliberately built from the parse tree --
    tag names and position among same-tag siblings -- and never from anything
    the renderer produced, because an identity derived from coordinates or
    from the text itself cannot distinguish two blocks that say the same
    thing, which is exactly the case it has to survive.

    The shape is XPath-like: ``/html[0]/body[0]/div[2]/table[0]/tr[1]/td[0]``.
    A node's index counts only earlier siblings sharing its tag, so adding an
    unrelated element beside it does not renumber it.

    Stable during parsing: a node's earlier siblings are all appended before
    its own character data arrives, and later siblings cannot change its
    index.
    """
    if element is None:
        return None
    parts: list[str] = []
    node: Element | None = element
    while node is not None:
        parent = node.parent
        if parent is None:
            parts.append(f"{node.tag}[0]")
            break
        index = 0
        for sibling in parent.children:
            if sibling is node:
                break
            if sibling.tag == node.tag:
                index += 1
        parts.append(f"{node.tag}[{index}]")
        node = parent
    return "/" + "/".join(reversed(parts))


def build_element(spec: str = "div", **attrs) -> Element:
    """``'div#total.row.mt-n3'`` to an :class:`Element`.

    Shorthand only; anything richer is built by assigning fields, because a
    parser for arbitrary markup belongs in the HTML adapter, not here.
    """
    found = _SPEC_RE.match(spec.strip())
    if found is None:
        raise ValueError(f"cannot read element shorthand {spec!r}")
    classes: set[str] = set()
    element_id = None
    for token in re.findall(r"[#.][\w-]+", found.group("rest") or ""):
        if token[0] == "#":
            element_id = token[1:]
        else:
            classes.add(token[1:])
    style = attrs.pop("style", None)
    node = Element(
        tag=(found.group("tag") or "*").lower(),
        element_id=element_id,
        classes=frozenset(classes),
        attrs={name: str(value) for name, value in attrs.items()},
    )
    if style:
        node.attrs["style"] = style
    return node


# --- selectors ---------------------------------------------------------

_IDENT_RE = re.compile(r"[\w-]+")
_TAG_RE = re.compile(r"\*|[a-zA-Z][\w-]*")

#: Single-colon spellings that are really pseudo-*elements*.
_PSEUDO_ELEMENTS = frozenset({
    "before", "after", "first-line", "first-letter", "marker",
    "placeholder", "selection", "backdrop", "file-selector-button",
})

#: Interactive states a static print rendering never enters. Naming them is
#: how ``:hover`` rules stay out of a PDF without being mistaken for
#: selectors we failed to parse.
_NEVER_IN_PRINT = frozenset({
    "hover", "focus", "focus-visible", "focus-within", "active", "visited",
    "link", "any-link", "target", "checked", "indeterminate", "disabled",
    "enabled", "placeholder-shown", "user-invalid", "invalid", "valid",
    "required", "optional", "autofill", "defined", "popover-open",
})

_MATCHES_ANY = frozenset({"is", "where", "matches", "any", "-webkit-any"})


class UnsupportedSelector(ValueError):
    """A selector this cascade declines to model, rather than mis-model."""


@dataclass(slots=True)
class _Simple:
    """One compound selector: everything between two combinators."""

    tag: str | None = None
    element_id: str | None = None
    classes: set[str] = field(default_factory=set)
    attrs: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    pseudos: list[tuple[str, str | None]] = field(default_factory=list)
    pseudo_element: str | None = None

    def specificity(self) -> tuple[int, int, int]:
        ids = 1 if self.element_id else 0
        classes = len(self.classes) + len(self.attrs)
        types = 1 if self.tag and self.tag != "*" else 0
        types += 1 if self.pseudo_element else 0
        for name, argument in self.pseudos:
            if name in {"not", *_MATCHES_ANY} and argument:
                # :not() and :is() take the specificity of their argument.
                inner = max(
                    (selector.specificity for selector in _parse_selector_list(argument)),
                    default=(0, 0, 0),
                )
                ids += inner[0]
                classes += inner[1]
                types += inner[2]
            elif name == "where":
                pass  # :where() contributes nothing, by definition.
            else:
                classes += 1
        return (ids, classes, types)

    def matches(self, node: Element) -> bool:
        if self.tag and self.tag != "*" and node.tag != self.tag:
            return False
        if self.element_id and node.element_id != self.element_id:
            return False
        if not self.classes <= node.classes:
            return False
        for name, operator, value in self.attrs:
            if not _attribute_matches(node, name, operator, value):
                return False
        return all(_pseudo_matches(node, name, arg) for name, arg in self.pseudos)


def _attribute_matches(node: Element, name: str, operator: str | None, value: str | None) -> bool:
    present = node.attrs.get(name)
    if present is None:
        return False
    if operator is None:
        return True
    if operator == "=":
        return present == value
    if operator == "~=":
        return value in present.split()
    if operator == "|=":
        return present == value or present.startswith(f"{value}-")
    if operator == "^=":
        return present.startswith(value or "")
    if operator == "$=":
        return present.endswith(value or "")
    if operator == "*=":
        return (value or "") in present
    return False


def _pseudo_matches(node: Element, name: str, argument: str | None) -> bool:
    if name == "not":
        return not any(
            selector.matches(node) for selector in _parse_selector_list(argument or "")
        )
    if name in _MATCHES_ANY:
        return any(selector.matches(node) for selector in _parse_selector_list(argument or ""))
    if name == "root":
        return node.parent is None
    if name == "empty":
        return not node.children
    if name == "first-child":
        return node.index == 0
    if name == "last-child":
        return node.index == len(node.siblings) - 1
    if name == "only-child":
        return len(node.siblings) == 1
    if name == "first-of-type":
        return node.type_index() == 1
    if name == "last-of-type":
        return node.type_index() == node.type_count()
    if name == "only-of-type":
        return node.type_count() == 1
    if name == "nth-child":
        return _nth_matches(argument, node.index + 1)
    if name == "nth-last-child":
        return _nth_matches(argument, len(node.siblings) - node.index)
    if name == "nth-of-type":
        return _nth_matches(argument, node.type_index())
    if name == "nth-last-of-type":
        return _nth_matches(argument, node.type_count() - node.type_index() + 1)
    if name in _NEVER_IN_PRINT:
        return False
    # Unknown pseudo-classes do not match. Guessing would be worse: a rule
    # applied on a guess is indistinguishable from one the stylesheet meant.
    return False


_NTH_RE = re.compile(r"^\s*(?:(?P<a>[+-]?\d*)n\s*(?P<b>[+-]\s*\d+)?|(?P<only>[+-]?\d+))\s*$")


def _nth_matches(argument: str | None, position: int) -> bool:
    text = (argument or "").strip().lower()
    if text == "odd":
        return position % 2 == 1
    if text == "even":
        return position % 2 == 0
    found = _NTH_RE.match(text)
    if found is None:
        return False
    if found.group("only") is not None:
        return position == int(found.group("only"))
    raw_a = (found.group("a") or "").strip()
    step = 1 if raw_a in {"", "+"} else -1 if raw_a == "-" else int(raw_a)
    offset = int((found.group("b") or "0").replace(" ", ""))
    if step == 0:
        return position == offset
    remainder = position - offset
    return remainder % step == 0 and remainder // step >= 0


@dataclass(slots=True)
class Selector:
    """A full selector: compounds joined by combinators."""

    #: ``(combinator, compound)``; the first combinator is always ``None``.
    parts: tuple[tuple[str | None, _Simple], ...]
    specificity: tuple[int, int, int]
    pseudo_element: str | None
    text: str

    def matches(self, node: Element, pseudo_element: str | None = None) -> bool:
        if self.pseudo_element != pseudo_element:
            return False
        last = len(self.parts) - 1
        if not self.parts[last][1].matches(node):
            return False
        return self._match_rest(last, node)

    def _match_rest(self, index: int, node: Element) -> bool:
        if index == 0:
            return True
        combinator = self.parts[index][0]
        previous = self.parts[index - 1][1]
        if combinator == " ":
            ancestor = node.parent
            while ancestor is not None:
                if previous.matches(ancestor) and self._match_rest(index - 1, ancestor):
                    return True
                ancestor = ancestor.parent
            return False
        if combinator == ">":
            parent = node.parent
            return (
                parent is not None
                and previous.matches(parent)
                and self._match_rest(index - 1, parent)
            )
        if combinator == "+":
            sibling = node.previous_sibling
            return (
                sibling is not None
                and previous.matches(sibling)
                and self._match_rest(index - 1, sibling)
            )
        if combinator == "~":
            sibling = node.previous_sibling
            while sibling is not None:
                if previous.matches(sibling) and self._match_rest(index - 1, sibling):
                    return True
                sibling = sibling.previous_sibling
            return False
        return False

    @property
    def key(self) -> tuple[str, str]:
        """The index bucket this selector belongs in.

        Keyed off the *rightmost* compound, because that is the one that has
        to match the element being styled; the rest only has to match its
        ancestors, which is a question we ask only after the bucket hits.
        """
        last = self.parts[-1][1]
        if last.element_id:
            return ("id", last.element_id)
        if last.classes:
            return ("class", min(last.classes))
        if last.tag and last.tag != "*":
            return ("tag", last.tag)
        return ("*", "")


_SELECTOR_CACHE: dict[str, tuple[Selector, ...]] = {}


def _parse_selector_list(text: str) -> tuple[Selector, ...]:
    cached = _SELECTOR_CACHE.get(text)
    if cached is not None:
        return cached
    parsed = []
    for part in _split_commas(text):
        try:
            parsed.append(_parse_selector(part))
        except UnsupportedSelector:
            continue
    result = tuple(parsed)
    _SELECTOR_CACHE[text] = result
    return result


def _split_commas(text: str) -> list[str]:
    """Split a selector list, ignoring commas inside ``:not(a, b)``."""
    parts, depth, start = [], 0, 0
    for position, char in enumerate(text):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(text[start:position])
            start = position + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def _parse_selector(text: str) -> Selector:
    text = text.strip()
    if not text:
        raise UnsupportedSelector(text)
    sequence: list[tuple[str | None, _Simple]] = []
    combinator: str | None = None
    current: _Simple | None = None
    position, length = 0, len(text)

    def begin() -> _Simple:
        nonlocal current, combinator
        if current is None:
            current = _Simple()
            sequence.append((combinator, current))
            combinator = None
        return current

    while position < length:
        char = text[position]
        if char.isspace():
            ahead = position
            while ahead < length and text[ahead].isspace():
                ahead += 1
            if ahead >= length:
                break
            if text[ahead] in ">+~":
                combinator, position = text[ahead], ahead + 1
            elif combinator is None:
                combinator, position = " ", ahead
            else:
                # The space after an explicit combinator is padding, not a
                # descendant combinator: overwriting here turned every
                # `a > b` into `a b`, which matches strictly more elements
                # and so is invisible until something relies on the
                # difference.
                position = ahead
            current = None
            continue
        if char in ">+~":
            combinator, position, current = char, position + 1, None
            continue
        if char == ".":
            found = _IDENT_RE.match(text, position + 1)
            if found is None:
                raise UnsupportedSelector(text)
            begin().classes.add(found.group())
            position = found.end()
            continue
        if char == "#":
            found = _IDENT_RE.match(text, position + 1)
            if found is None:
                raise UnsupportedSelector(text)
            begin().element_id = found.group()
            position = found.end()
            continue
        if char == "[":
            end = text.find("]", position)
            if end < 0:
                raise UnsupportedSelector(text)
            begin().attrs.append(_parse_attribute(text[position + 1 : end]))
            position = end + 1
            continue
        if char == ":":
            is_element = text.startswith("::", position)
            found = _IDENT_RE.match(text, position + (2 if is_element else 1))
            if found is None:
                raise UnsupportedSelector(text)
            name, position = found.group().lower(), found.end()
            argument = None
            if position < length and text[position] == "(":
                depth, scan = 0, position
                while scan < length:
                    if text[scan] == "(":
                        depth += 1
                    elif text[scan] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    scan += 1
                if depth != 0:
                    raise UnsupportedSelector(text)
                argument, position = text[position + 1 : scan], scan + 1
            node = begin()
            if is_element or name in _PSEUDO_ELEMENTS:
                node.pseudo_element = name
            else:
                node.pseudos.append((name, argument))
            continue
        found = _TAG_RE.match(text, position)
        if found is None:
            raise UnsupportedSelector(text)
        begin().tag = found.group().lower()
        position = found.end()
        continue

    if not sequence:
        raise UnsupportedSelector(text)
    # A pseudo-element is only meaningful on the subject of the selector.
    pseudo_element = sequence[-1][1].pseudo_element
    for _combinator, simple in sequence[:-1]:
        if simple.pseudo_element:
            raise UnsupportedSelector(text)
    specificity = (0, 0, 0)
    for _combinator, simple in sequence:
        part = simple.specificity()
        specificity = (
            specificity[0] + part[0],
            specificity[1] + part[1],
            specificity[2] + part[2],
        )
    return Selector(tuple(sequence), specificity, pseudo_element, text)


_ATTR_RE = re.compile(
    r"^\s*(?P<name>[\w-]+)\s*(?:(?P<op>[~|^$*]?=)\s*(?P<value>.+?)\s*)?(?:\s+[iIsS])?\s*$"
)


def _parse_attribute(text: str) -> tuple[str, str | None, str | None]:
    found = _ATTR_RE.match(text)
    if found is None:
        raise UnsupportedSelector(f"[{text}]")
    value = found.group("value")
    if value and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1]
    return (found.group("name").lower(), found.group("op"), value)


# --- values ------------------------------------------------------------

_LENGTH_RE = re.compile(
    r"^([+-]?(?:\d+\.?\d*|\.\d+))\s*(px|rem|em|mm|cm|in|pt|pc|q|%)?$", re.IGNORECASE
)
#: CSS's internal unit relationships, which are fixed by the specification.
#: The page scale lives in :data:`MM_PER_PX`, not here.
_PX_PER_UNIT = {
    "px": 1.0,
    "in": CSS_PX_PER_INCH,
    "pt": CSS_PX_PER_INCH / 72.0,
    "pc": CSS_PX_PER_INCH / 6.0,
    "mm": CSS_PX_PER_INCH / 25.4,
    "cm": CSS_PX_PER_INCH / 2.54,
    "q": CSS_PX_PER_INCH / 101.6,
}

_NAMED_COLOURS = {
    "black": (0.0, 0.0, 0.0),
    "silver": (0.75, 0.75, 0.75),
    "gray": (0.5, 0.5, 0.5),
    "grey": (0.5, 0.5, 0.5),
    "white": (1.0, 1.0, 1.0),
    "maroon": (0.5, 0.0, 0.0),
    "red": (1.0, 0.0, 0.0),
    "purple": (0.5, 0.0, 0.5),
    "fuchsia": (1.0, 0.0, 1.0),
    "green": (0.0, 0.5, 0.0),
    "lime": (0.0, 1.0, 0.0),
    "olive": (0.5, 0.5, 0.0),
    "yellow": (1.0, 1.0, 0.0),
    "navy": (0.0, 0.0, 0.5),
    "blue": (0.0, 0.0, 1.0),
    "teal": (0.0, 0.5, 0.5),
    "aqua": (0.0, 1.0, 1.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "orange": (1.0, 0.647, 0.0),
}

_RGB_RE = re.compile(r"^rgba?\(([^)]*)\)$", re.IGNORECASE)


def parse_length_px(
    value: str,
    *,
    font_size_px: float = ROOT_FONT_SIZE_PX,
    root_font_size_px: float = ROOT_FONT_SIZE_PX,
    percent_base_px: float | None = None,
) -> float | None:
    """A CSS length to reference pixels, or ``None`` when it is not one.

    ``em`` and ``%`` need context the caller has and this function does not,
    so they are parameters rather than assumptions.
    """
    found = _LENGTH_RE.match((value or "").strip())
    if found is None:
        return None
    amount = float(found.group(1))
    unit = (found.group(2) or "").lower()
    if not unit:
        return amount if amount == 0.0 else None
    if unit == "rem":
        return amount * root_font_size_px
    if unit == "em":
        return amount * font_size_px
    if unit == "%":
        if percent_base_px is None:
            return None
        return amount * percent_base_px / 100.0
    return amount * _PX_PER_UNIT[unit]


_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")


#: A CSS escape: a backslash, one to six hex digits, and one optional
#: whitespace character that terminates the digits rather than being part of
#: the value.
_CSS_ESCAPE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})[ \t\n\f\r]?|(.))", re.DOTALL)


def decode_css_string(value: str) -> str | None:
    """A quoted CSS string as the characters it stands for.

    ``None`` when the value is not a string at all, which is how the caller
    tells `content: "\\f095"` -- a glyph -- from `content: attr(href)`, a
    capability, without a second predicate deciding the same thing.

    The escape is the reason this exists. Every icon in the report inputs is written
    `"\\f095"`, a codepoint in the private use area, and reading it literally
    prints a backslash and four letters.
    """
    text = value.strip()
    if len(text) < 2 or text[0] != text[-1] or text[0] not in "\"'":
        return None

    def replace(found: re.Match) -> str:
        digits, literal = found.group(1), found.group(2)
        if digits is None:
            # `\n` in a CSS string is a line continuation, not a newline.
            return "" if literal == "\n" else literal
        point = int(digits, 16)
        # CSS says a zero or an out-of-range escape becomes the replacement
        # character rather than an error.
        if point == 0 or point > 0x10FFFF or 0xD800 <= point <= 0xDFFF:
            return "\ufffd"
        return chr(point)

    return _CSS_ESCAPE.sub(replace, text[1:-1])


#: The kinds of `content` this engine can turn into something drawn. Anything
#: else is a capability it does not have, and saying so is the point: a
#: silently skipped `counter()` looks exactly like a correct render.
_CONTENT_FUNCTIONS = ("attr(", "counter(", "counters(", "url(", "image(",
                      "linear-gradient(", "var(", "element(")
_CONTENT_KEYWORDS = {
    "open-quote", "close-quote", "no-open-quote", "no-close-quote",
}


def content_kind(value: str | None) -> str:
    """What sort of generated content a `content` value is.

    `none` and `normal` are kept apart from the empty string on purpose. The
    first two mean the pseudo does not exist; the third means it exists,
    takes its display, and draws no ink -- which is a different thing to get
    wrong.
    """
    if value is None:
        return "absent"
    text = value.strip()
    lowered = text.lower()
    if lowered in ("none", "normal", "inherit", "initial", "unset"):
        return lowered if lowered in ("none", "normal") else "none"
    if text in ('""', "''"):
        return "empty-string"
    for function in _CONTENT_FUNCTIONS:
        if function in lowered:
            return function.rstrip("(")
    if lowered in _CONTENT_KEYWORDS:
        return lowered
    if decode_css_string(text) is not None:
        return "string"
    return "unknown"


def substitute_vars(value: str, properties: dict[str, str], _depth: int = 0) -> str:
    """Replace ``var(--x, fallback)`` with what the cascade resolved for it.

    Bootstrap 5 states its grid entirely in custom properties -- ``.row``
    carries ``--gutter-x: 32px`` and its columns ask for
    ``calc(var(--gutter-x) * .5)`` -- so a value layer that cannot follow a
    ``var()`` answers ``None`` for the most common spacing in the bundle.
    """
    if "var(" not in value or _depth > 8:
        return value

    def replace(found: re.Match) -> str:
        name, fallback = found.group(1), found.group(2)
        resolved = properties.get(name)
        if resolved is None:
            return (fallback or "").strip()
        return resolved

    return substitute_vars(_VAR_RE.sub(replace, value), properties, _depth + 1)


_CALC_TOKEN_RE = re.compile(
    r"\s*(?:(?P<number>[+-]?(?:\d+\.?\d*|\.\d+)\s*(?:px|rem|em|mm|cm|in|pt|pc|q|%)?)"
    r"|(?P<paren>[()])"
    r"|(?P<operator>[*/+-]))"
)


class _CalcError(ValueError):
    pass


def evaluate_calc(
    expression: str,
    *,
    font_size_px: float = ROOT_FONT_SIZE_PX,
    root_font_size_px: float = ROOT_FONT_SIZE_PX,
    percent_base_px: float | None = None,
) -> float | None:
    """Evaluate the ``calc()`` subset the report bundle uses, in pixels.

    Lengths become pixels as they are read and unitless numbers stay
    scalars, which is enough for Bootstrap's ``calc(var(--gutter-x) * .5)``
    and ``calc(-1 * var(--gutter-y))``. Anything richer -- mixed units that
    need layout to resolve, ``min()``/``max()``/``clamp()`` -- returns
    ``None`` rather than a number that would be indistinguishable from a
    real reading.
    """
    text = expression.strip()
    if text.lower().startswith("calc(") and text.endswith(")"):
        text = text[5:-1]
    tokens: list[str] = []
    position = 0
    while position < len(text):
        found = _CALC_TOKEN_RE.match(text, position)
        if found is None:
            if text[position].isspace():
                position += 1
                continue
            return None
        tokens.append((found.group("number") or found.group("paren")
                       or found.group("operator")).strip())
        position = found.end()
    if not tokens:
        return None

    index = 0

    def peek() -> str | None:
        return tokens[index] if index < len(tokens) else None

    def expression_() -> float:
        nonlocal index
        value = term()
        while peek() in {"+", "-"}:
            operator = tokens[index]
            index += 1
            right = term()
            value = value + right if operator == "+" else value - right
        return value

    def term() -> float:
        nonlocal index
        value = factor()
        while peek() in {"*", "/"}:
            operator = tokens[index]
            index += 1
            right = factor()
            if operator == "/" and right == 0:
                raise _CalcError("division by zero")
            value = value * right if operator == "*" else value / right
        return value

    def factor() -> float:
        nonlocal index
        token = peek()
        if token is None:
            raise _CalcError("expression ended early")
        index += 1
        if token == "(":
            value = expression_()
            if peek() != ")":
                raise _CalcError("unbalanced parentheses")
            index += 1
            return value
        if token in {"+", "-"}:
            return factor() if token == "+" else -factor()
        pixels = parse_length_px(
            token,
            font_size_px=font_size_px,
            root_font_size_px=root_font_size_px,
            percent_base_px=percent_base_px,
        )
        if pixels is not None:
            return pixels
        try:
            # A unitless number is a scalar multiplier, not a length.
            return float(token)
        except ValueError as error:
            raise _CalcError(token) from error

    try:
        result = expression_()
    except _CalcError:
        return None
    return None if index != len(tokens) else result


def _parse_colour_channels(
    value: str,
) -> tuple[tuple[float, float, float], float] | None:
    """Channels and alpha exactly as CSS states them, before compositing.

    Shared by :func:`parse_colour` (which flattens the result against an
    assumed backdrop) and :func:`parse_colour_alpha` (which does not) so the
    two can never drift on what counts as a colour.
    """
    text = (value or "").strip().lower()
    if not text or text in {"transparent", "none", "inherit", "initial", "currentcolor"}:
        return None
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) in {3, 4}:
            digits = "".join(char * 2 for char in digits)
        if len(digits) in {6, 8}:
            try:
                channels = tuple(
                    int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4)
                )
                opacity = int(digits[6:8], 16) / 255.0 if len(digits) == 8 else 1.0
            except ValueError:
                return None
            return channels, opacity
        return None
    found = _RGB_RE.match(text)
    if found is not None:
        pieces = [piece.strip() for piece in re.split(r"[,/\s]+", found.group(1)) if piece.strip()]
        if len(pieces) < 3:
            return None
        try:
            channels = []
            for piece in pieces[:3]:
                if piece.endswith("%"):
                    channels.append(float(piece[:-1]) / 100.0)
                else:
                    channels.append(float(piece) / 255.0)
            opacity = 1.0
            if len(pieces) >= 4:
                alpha = pieces[3]
                opacity = float(alpha[:-1]) / 100.0 if alpha.endswith("%") else float(alpha)
        except ValueError:
            return None
        return tuple(channels), opacity
    named = _NAMED_COLOURS.get(text)
    return (named, 1.0) if named is not None else None


def parse_colour(
    value: str, *, over: tuple[float, float, float] = (1.0, 1.0, 1.0)
) -> tuple[float, float, float] | None:
    """A CSS colour to a 0..1 RGB triple; ``None`` when it paints nothing.

    Transparent and fully transparent ``rgba()`` return ``None`` rather than
    white: "no fill" and "a white fill" are different commands to a renderer,
    and conflating them is how a page grows opaque boxes it should not have.

    A partly transparent colour is composited over ``over``, which defaults
    to paper. Odoo's striped rows are ``rgba(231, 233, 237, 0.5)``, and a
    renderer with no alpha that takes the RGB at face value prints them
    twice as dark as the source engine does.

    This bakes the colour flat, so it is only correct when ``over`` really is
    everything that will end up beneath the paint. A fill a renderer can draw
    with true alpha -- a PDF ``ca`` graphics state -- should use
    :func:`parse_colour_alpha` instead, so the backdrop is whatever the page
    actually holds there (paper, or a layout's watermark art) rather than a
    guess made at CSS-resolution time.
    """
    raw = _parse_colour_channels(value)
    if raw is None:
        return None
    channels, opacity = raw
    return _composite(channels, opacity, over)


def parse_colour_alpha(value: str) -> tuple[tuple[float, float, float], float] | None:
    """A CSS colour's channels and alpha, left uncomposited.

    ``None`` for the same "paints nothing" cases as :func:`parse_colour`.
    The channels are clamped to ``0..1`` the same way; the alpha is not
    flattened against any assumed backdrop, so the caller can hand both to a
    renderer capable of real compositing.
    """
    raw = _parse_colour_channels(value)
    if raw is None:
        return None
    channels, opacity = raw
    if opacity <= 0.0:
        return None
    clamped = tuple(min(1.0, max(0.0, channel)) for channel in channels)
    return clamped, min(1.0, opacity)


def _composite(
    channels: tuple[float, float, float],
    opacity: float,
    over: tuple[float, float, float],
) -> tuple[float, float, float] | None:
    if opacity <= 0.0:
        return None
    clamped = tuple(min(1.0, max(0.0, channel)) for channel in channels)
    if opacity >= 1.0:
        return clamped
    return tuple(
        backdrop + (channel - backdrop) * opacity
        for channel, backdrop in zip(clamped, over)
    )


# --- declarations ------------------------------------------------------

_SIDES = ("top", "right", "bottom", "left")
_BORDER_STYLES = frozenset({
    "none", "hidden", "solid", "dashed", "dotted", "double", "groove",
    "ridge", "inset", "outset",
})
_BORDER_WIDTH_WORDS = {"thin": "1px", "medium": "3px", "thick": "5px"}

#: Properties a child takes from its parent when it says nothing itself.
INHERITED = frozenset({
    "color", "font-family", "font-size", "font-style", "font-weight",
    "font-variant", "letter-spacing", "line-height", "text-align",
    "text-indent", "text-transform", "visibility", "white-space",
    "word-spacing", "direction", "list-style-type",
})

#: What a property means before any rule speaks. Only the ones this cascade
#: is asked about; an absent property simply reads as ``None``.
INITIAL = {
    "color": "#000000",
    "font-size": "1rem",
    "font-weight": "400",
    "text-align": "start",
    "text-transform": "none",
    "background-color": "transparent",
}


def _css_components(text: str, *, stop_before: str | None = None) -> list[str]:
    """Split a CSS value at top-level whitespace, never inside a function.

    CSS component values already have the boundary this code needs.  In
    ``rgba(var(--dark-rgb), var(--border-opacity))`` the entire ``rgba`` is
    one function block; the whitespace after its comma is not the separator
    between two sides of ``border-color``.  Asking tinycss2 for those blocks
    keeps shorthand expansion on the same grammar as the cascade instead of
    approximating it with :meth:`str.split`.

    ``stop_before`` handles the top-level slash in ``border-radius``.  A slash
    inside ``calc()`` remains inside its function block and therefore cannot
    terminate the horizontal radii by accident.
    """
    tinycss2 = _tinycss2()
    groups: list[str] = []
    current = []

    def flush() -> None:
        if current:
            groups.append(tinycss2.serialize(current).strip())
            current.clear()

    for token in tinycss2.parse_component_value_list(text, skip_comments=True):
        if stop_before is not None and token.type == "literal" and token.value == stop_before:
            break
        if token.type == "whitespace":
            flush()
        else:
            current.append(token)
    flush()
    return groups


#: What `font` covers, and therefore what it resets. CSS 2.1 §15.8: the
#: shorthand sets *every* one of these, including the ones its value leaves
#: out, which then take their initial value. Expanding only the parts that
#: were written is the half-expansion that inverts a cascade.
_FONT_LONGHANDS = (
    "font-style", "font-variant", "font-weight", "font-stretch",
    "font-size", "line-height", "font-family",
)

#: The initial value of each, for the ones the grammar allows to be omitted.
#: `font-size` and `font-family` are required, so a value missing either is
#: invalid rather than defaulted.
_FONT_RESET = {
    "font-style": "normal",
    "font-variant": "normal",
    "font-weight": "normal",
    "font-stretch": "normal",
    "line-height": "normal",
}

_FONT_STYLES = frozenset({"normal", "italic", "oblique"})
_FONT_VARIANTS = frozenset({"normal", "small-caps"})
_FONT_WEIGHTS = frozenset({
    "normal", "bold", "bolder", "lighter",
    "100", "200", "300", "400", "500", "600", "700", "800", "900",
})
_FONT_STRETCHES = frozenset({
    "normal", "ultra-condensed", "extra-condensed", "condensed",
    "semi-condensed", "semi-expanded", "expanded", "extra-expanded",
    "ultra-expanded",
})

#: `font: caption` and friends take their longhands from a platform value
#: this cascade has no way to read. Guessing one, or expanding the shorthand
#: partially and leaving the rest inherited, would both put a wrong face in
#: front of the renderer, so the declaration is left whole and unread.
_SYSTEM_FONTS = frozenset({
    "caption", "icon", "menu", "message-box", "small-caption", "status-bar",
})


def _read_font_shorthand(text: str) -> list[tuple[str, str]]:
    """`font` to its longhands, or an empty list when it is not expandable.

    Grammar: an optional run of style/variant/weight/stretch in any order and
    at most one each, then the size, then an optional `/ line-height`, then
    the family. Anything else -- a system font, a missing size or family --
    returns nothing, which leaves the declaration in place as a property this
    cascade never reads. That is what an ignored declaration does anyway, and
    it is the only outcome that cannot silently invert the comparison between
    a declared face and an inherited one.
    """
    parts = _css_components(text)
    if not parts:
        return []

    lowered_all = " ".join(parts).lower()
    if lowered_all in _SYSTEM_FONTS:
        return []
    if lowered_all in {"inherit", "unset"}:
        # Every longhand `font` covers is an inherited property, so `unset`
        # and `inherit` come to the same thing for all of them.
        return [(name, "inherit") for name in _FONT_LONGHANDS]
    if lowered_all == "initial":
        return [
            (name, _FONT_RESET.get(name, "medium" if name == "font-size" else "initial"))
            for name in _FONT_LONGHANDS
        ]

    out = dict(_FONT_RESET)
    index = 0
    claimed: set[str] = set()
    while index < len(parts):
        word = parts[index].lower()
        for prefix, vocabulary in (
            ("font-style", _FONT_STYLES), ("font-variant", _FONT_VARIANTS),
            ("font-weight", _FONT_WEIGHTS), ("font-stretch", _FONT_STRETCHES),
        ):
            if word in vocabulary and prefix not in claimed:
                # `normal` belongs to all four vocabularies and so identifies
                # none of them. It consumes one slot and leaves every unset
                # longhand at its initial value, which is `normal` regardless.
                if word != "normal":
                    out[prefix] = parts[index]
                claimed.add(prefix)
                break
        else:
            break
        index += 1

    if index >= len(parts):
        return []

    # The size, and the line height the slash may attach to it. CSS allows
    # whitespace on either side of that slash, so it arrives as one token,
    # two, or three.
    size_parts: list[str] = []
    while index < len(parts):
        chunk = parts[index]
        size_parts.append(chunk)
        index += 1
        joined = "".join(size_parts)
        if "/" not in joined:
            if index < len(parts) and parts[index].startswith("/"):
                continue
            break
        if not joined.endswith("/"):
            break

    size, slash, height = "".join(size_parts).partition("/")
    if not size:
        return []
    out["font-size"] = size
    if slash:
        if not height:
            return []
        out["line-height"] = height

    family = " ".join(parts[index:]).strip()
    if not family:
        return []
    out["font-family"] = family
    return [(name, out[name]) for name in _FONT_LONGHANDS if name in out]


def _expand_shorthand(name: str, value: str) -> list[tuple[str, str]]:
    """Rewrite the shorthands this cascade reads into longhands.

    Only the ones the bundle actually uses on report chrome. A shorthand left
    unexpanded is a property the engine will never find, so the list is
    short on purpose rather than incidentally.
    """
    name = name.lower()
    text = value.strip()
    lowered = text.lower()

    if name == "font":
        return _read_font_shorthand(text)

    if name in {"margin", "padding"}:
        parts = _css_components(text)
        if not 1 <= len(parts) <= 4:
            return []
        top, right, bottom, left = _box_sides(parts)
        return [
            (f"{name}-top", top),
            (f"{name}-right", right),
            (f"{name}-bottom", bottom),
            (f"{name}-left", left),
        ]

    if name == "border" or (name.startswith("border-") and name[7:] in _SIDES):
        sides = _SIDES if name == "border" else (name[7:],)
        width, style, colour = _read_border_shorthand(lowered)
        out = []
        for side in sides:
            out.append((f"border-{side}-width", width))
            out.append((f"border-{side}-style", style))
            if colour is not None:
                out.append((f"border-{side}-color", colour))
        return out

    if name in {"border-width", "border-style", "border-color"}:
        suffix = name.split("-")[1]
        parts = _css_components(text)
        if not 1 <= len(parts) <= 4:
            return []
        top, right, bottom, left = _box_sides(parts)
        return [
            (f"border-top-{suffix}", top),
            (f"border-right-{suffix}", right),
            (f"border-bottom-{suffix}", bottom),
            (f"border-left-{suffix}", left),
        ]

    if name == "background":
        # Only the colour half is meaningful to a page planner; a gradient or
        # an image is a decoration this engine does not draw.
        colour = parse_colour(lowered)
        if colour is not None or lowered in {"transparent", "none"}:
            return [("background-color", text)]
        return []

    if name == "border-radius":
        parts = _css_components(lowered, stop_before="/")
        if not parts:
            return []
        corners = _box_sides(parts) if 1 <= len(parts) <= 4 else None
        if corners is None:
            return []
        return [
            ("border-top-left-radius", corners[0]),
            ("border-top-right-radius", corners[1]),
            ("border-bottom-right-radius", corners[2]),
            ("border-bottom-left-radius", corners[3]),
        ]

    return []


def _box_sides(parts: list[str]) -> tuple[str, str, str, str]:
    if len(parts) == 1:
        return (parts[0],) * 4
    if len(parts) == 2:
        return (parts[0], parts[1], parts[0], parts[1])
    if len(parts) == 3:
        return (parts[0], parts[1], parts[2], parts[1])
    return (parts[0], parts[1], parts[2], parts[3])


def _read_border_shorthand(text: str) -> tuple[str, str, str | None]:
    """``1px solid #374151`` to (width, style, colour).

    An omitted colour is reported as ``None`` -- CSS says it defaults to
    ``currentColor``, which the cascade can only resolve once it knows the
    element's ``color``.

    An omitted style stays ``none``, which is the initial value and the
    reason ``border: 1px`` draws nothing: the width is not what makes a
    border visible.
    """
    width, style, colour = "medium", "none", None
    for token in _css_components(text):
        if token in _BORDER_STYLES:
            style = token
        elif token in _BORDER_WIDTH_WORDS:
            width = _BORDER_WIDTH_WORDS[token]
        elif _LENGTH_RE.match(token):
            width = token
        else:
            colour = token
    return (width, style, colour)


# --- the stylesheet ----------------------------------------------------


#: Parsed bundles, keyed by content. A bundle costs ~2.8 MB parsed, so this
#: is deliberately small: a process serves one Odoo database, which has one
#: asset bundle, and the spare slots are for the moment after a recompile.
_PARSED_BUNDLES: dict[tuple, Stylesheet] = {}
_PARSED_BUNDLE_LIMIT = 3


@dataclass(frozen=True, slots=True)
class _Rule:
    selector: Selector
    declarations: tuple[tuple[str, str, bool], ...]
    order: int


@dataclass
class ComputedStyle:
    """The resolved value of every property this cascade tracks."""

    properties: dict[str, str]
    font_size_px: float

    def get(self, name: str) -> str | None:
        return self.properties.get(name)

    def colour(self, name: str) -> tuple[float, float, float] | None:
        value = self.properties.get(name)
        if value is None:
            return None
        # Colours go through `var()` as often as lengths do -- Bootstrap
        # writes links as `rgba(var(--link-color-rgb), var(--link-opacity))`
        # -- and substituting only in `length_px` left every one of those
        # reading as "no colour", which is indistinguishable from inheriting.
        value = substitute_vars(value, self.properties)
        if value.strip().lower() == "currentcolor":
            return parse_colour(substitute_vars(self.properties.get("color", ""), self.properties))
        return parse_colour(value)

    def fill(self, name: str) -> Fill | None:
        """Resolve a background without flattening CSS alpha."""
        value = self.properties.get(name)
        if value is None:
            return None
        value = substitute_vars(value, self.properties)
        parsed = parse_colour_alpha(value)
        if parsed is None:
            return None
        rgb, alpha = parsed
        return Fill(rgb, alpha)

    def length_px(self, name: str, *, percent_base_px: float | None = None) -> float | None:
        value = self.properties.get(name)
        if value is None:
            return None
        value = substitute_vars(value, self.properties)
        if "calc(" in value.lower():
            return evaluate_calc(
                value, font_size_px=self.font_size_px, percent_base_px=percent_base_px
            )
        return parse_length_px(
            value, font_size_px=self.font_size_px, percent_base_px=percent_base_px
        )

    def length_mm(self, name: str, *, percent_base_px: float | None = None) -> float | None:
        pixels = self.length_px(name, percent_base_px=percent_base_px)
        return None if pixels is None else pixels * MM_PER_PX

    def edge(
        self, side: str, *, px_per_inch: float = PX_PER_INCH
    ) -> tuple[float, tuple[float, float, float]] | None:
        """A drawn border on one side, as ``(width_pt, rgb)``.

        ``None`` when nothing is drawn -- no style, ``none``/``hidden``, or a
        zero width. The three are different in CSS and identical on paper.
        """
        style = (self.properties.get(f"border-{side}-style") or "none").lower()
        if style in {"none", "hidden"}:
            return None
        width = self.length_px(f"border-{side}-width")
        if width is None:
            width = 3.0 if self.properties.get(f"border-{side}-width") is None else 0.0
        if width <= 0.0:
            return None
        colour = self.colour(f"border-{side}-color")
        if colour is None:
            colour = parse_colour(self.properties.get("color", "")) or (0.0, 0.0, 0.0)
        return (width * 72.0 / px_per_inch, colour)

    def inset_fill(self) -> tuple[tuple[float, float, float], float] | None:
        """The colour and true alpha of Bootstrap's full-cell inset shadow.

        Bootstrap 5 implements table stripes as a 9999px inset box shadow,
        not as ``background-color``.  The report inputs use exactly that
        full-cell form; other box shadows remain outside this small cascade's
        paint contract rather than being approximated.

        The alpha is returned uncomposited (see :func:`parse_colour_alpha`):
        a stripe drawn with real alpha still lets whatever the page already
        holds beneath it -- paper, or a layout's watermark art -- show
        through, which is what a browser's own compositor does with the same
        ``rgba()`` value.
        """
        value = substitute_vars(self.properties.get("box-shadow", ""), self.properties)
        if not value.lower().startswith("inset 0 0 0 9999px "):
            return None
        return parse_colour_alpha(value[len("inset 0 0 0 9999px "):])

    @property
    def uppercase(self) -> bool:
        return (self.properties.get("text-transform") or "").lower() == "uppercase"

    @property
    def bold(self) -> bool:
        weight = (self.properties.get("font-weight") or "").lower()
        if weight in {"bold", "bolder"}:
            return True
        try:
            return int(weight) >= 600
        except ValueError:
            return False


class Stylesheet:
    """A parsed report bundle, indexed for lookup by element.

    ``Stylesheet()`` with nothing to parse is legal and answers every query
    with "the stylesheet said nothing", so callers that have no CSS to hand
    take exactly one code path.
    """

    def __init__(self, rules: list[_Rule] | None = None, *, available: bool = True):
        self._rules = rules or []
        self._index: dict[tuple[str, str], list[_Rule]] = {}
        self.available = available and bool(self._rules)
        #: Derived table chrome, keyed by what it was derived from. The
        #: derivation is a pure function of four strings and this sheet, and
        #: a report renders the same two tables on every document, so
        #: without this the same answer is recomputed per PDF forever.
        self._skins: dict[tuple, TableSkin] = {}
        #: Set by `record_matches` while a measurement is running; `None`
        #: the rest of the time, which is every render nobody is measuring.
        self._recording: set | None = None
        for rule in self._rules:
            self._index.setdefault(rule.selector.key, []).append(rule)

    def __len__(self) -> int:
        return len(self._rules)

    @property
    def selectors(self) -> tuple[str, ...]:
        return tuple(rule.selector.text for rule in self._rules)

    # -- construction --------------------------------------------------
    @classmethod
    def empty(cls) -> Stylesheet:
        """The stylesheet a caller has when the host handed it none."""
        return cls([], available=False)

    @classmethod
    def from_compiled(cls, rules) -> Stylesheet:
        """Build a runtime cascade from already-tokenised rule data.

        A host must not parse Odoo's 450KB asset bundle for every PDF, but
        dropping the selectors while compiling it forces the renderer to
        invent replacement predicates.  Compiled profiles therefore retain
        selector text plus expanded CSS property names.  This constructor
        performs only the dependency-free selector parse; CSS tokenisation
        remains an offline build step.

        ``rules`` is an ordered iterable of ``(selector, declarations)``.
        Declarations are ``(name, value, important)`` triples, exactly the
        representation emitted by :meth:`parse`.
        """
        compiled: list[_Rule] = []
        order = 0
        for selector_text, declarations in rules:
            normalised = tuple(
                (str(name).lower(), str(value), bool(important))
                for name, value, important in declarations
            )
            for selector in _parse_selector_list(str(selector_text)):
                compiled.append(_Rule(selector, normalised, order))
                order += 1
        return cls(compiled)

    @classmethod
    def cached(cls, *sources: str, media: MediaContext | None = None) -> Stylesheet:
        """:meth:`parse`, but once per bundle per process.

        Parsing the bundle costs about 400 ms, two thirds of it inside
        ``tinycss2`` tokenising 450 KB. That is fine once and absurd per
        PDF, and the bundle only changes when Odoo recompiles its assets --
        so it is keyed by the content itself and simply reused. Odoo runs
        one of these per worker process, which is where the memory below
        gets multiplied.
        """
        key = (media, tuple(hash(source) for source in sources))
        found = _PARSED_BUNDLES.get(key)
        if found is None:
            found = cls.parse(*sources, media=media)
            if len(_PARSED_BUNDLES) >= _PARSED_BUNDLE_LIMIT:
                _PARSED_BUNDLES.pop(next(iter(_PARSED_BUNDLES)))
            _PARSED_BUNDLES[key] = found
        return found

    @classmethod
    def parse(
        cls,
        *sources: str,
        media: MediaContext | None = None,
    ) -> Stylesheet:
        """Parse one or more bundles, in the order wkhtmltopdf reads them."""
        tinycss2 = _tinycss2()
        media = media or MediaContext()
        rules: list[_Rule] = []
        counter = 0

        def collect(nodes) -> None:
            nonlocal counter
            for node in nodes:
                if node.type == "at-rule":
                    keyword = (node.lower_at_keyword or "").lower()
                    if keyword != "media" or node.content is None:
                        continue
                    if not media.matches(tinycss2.serialize(node.prelude)):
                        continue
                    collect(
                        tinycss2.parse_stylesheet(
                            tinycss2.serialize(node.content),
                            skip_comments=True,
                            skip_whitespace=True,
                        )
                    )
                    continue
                if node.type != "qualified-rule":
                    continue
                declarations = _read_declarations(tinycss2, node.content)
                if not declarations:
                    continue
                for selector in _parse_selector_list(tinycss2.serialize(node.prelude)):
                    rules.append(_Rule(selector, declarations, counter))
                    counter += 1

        for source in sources:
            if not source:
                continue
            collect(
                tinycss2.parse_stylesheet(source, skip_comments=True, skip_whitespace=True)
            )
        return cls(rules)

    @classmethod
    def from_paths(cls, *paths, media: MediaContext | None = None) -> Stylesheet:
        texts = []
        for path in paths:
            with open(path, encoding="utf-8") as handle:
                texts.append(handle.read())
        return cls.parse(*texts, media=media)

    # -- lookup --------------------------------------------------------
    def _candidates(self, node: Element) -> list[_Rule]:
        found: list[_Rule] = []
        if node.element_id:
            found += self._index.get(("id", node.element_id), ())
        for name in node.classes:
            found += self._index.get(("class", name), ())
        found += self._index.get(("tag", node.tag), ())
        found += self._index.get(("*", ""), ())
        return found

    @contextmanager
    def record_matches(self, into: set | None = None):
        """Record which selectors match, until the context closes.

        A compiled slice is matched against every element of every report, so
        "did this change reach anything outside the reports I re-rendered" is
        a question about which of its rules fired -- and answering it by
        judgement is how a subset run comes to stand in for evidence it does
        not have.

        Deliberately opt-in and off by default: this is a measurement hook,
        and a render that nobody is measuring should not pay for a set
        insertion per matched rule.
        """
        recorded = set() if into is None else into
        previous = self._recording
        self._recording = recorded
        try:
            yield recorded
        finally:
            self._recording = previous

    def declarations_for(
        self, node: Element, pseudo_element: str | None = None
    ) -> dict[str, str]:
        """Every declaration that wins its property for this element.

        Ordering is the cascade's: ``!important`` first, then specificity,
        then source order. The last one standing is the answer.
        """
        winners: dict[str, tuple[bool, tuple[int, int, int], int, str]] = {}

        def offer(name: str, value: str, important: bool, spec, order: int) -> None:
            key = (important, spec, order)
            current = winners.get(name)
            if current is None or (current[0], current[1], current[2]) <= key:
                winners[name] = (important, spec, order, value)

        for rule in self._candidates(node):
            if not rule.selector.matches(node, pseudo_element):
                continue
            if self._recording is not None:
                self._recording.add(rule.selector.text)
            for name, value, important in rule.declarations:
                offer(name, value, important, rule.selector.specificity, rule.order)

        if pseudo_element is None and node.inline_declarations:
            for name, value, important in node.inline_declarations:
                offer(name, value, important, (1, 0, 0, 0), 1 << 30)
        elif pseudo_element is None and "style" in node.attrs:
            # An inline style outranks every selector in the sheet; Odoo's
            # templates use them for company-specific one-offs.
            inline = _parse_inline_style(node.attrs["style"])
            for name, value, important in inline:
                offer(name, value, important, (1, 0, 0, 0), 1 << 30)

        return {name: entry[3] for name, entry in winners.items()}

    def computed(self, node: Element, pseudo_element: str | None = None) -> ComputedStyle:
        cache_key = (id(self), pseudo_element)
        cached = node._styles.get(cache_key)
        if cached is not None:
            return cached

        if pseudo_element is not None:
            # A pseudo-element inherits from the element that generates it.
            parent = self.computed(node)
        else:
            parent = self.computed(node.parent) if node.parent is not None else None
        declared = self.declarations_for(node, pseudo_element)

        properties: dict[str, str] = {}
        inherited_from = parent.properties if parent is not None else {}
        for name in INHERITED:
            if name in inherited_from:
                properties[name] = inherited_from[name]
        # Custom properties inherit by definition, and Bootstrap relies on it:
        # `--gutter-x` is declared on `.row` and read on its columns.
        for name, value in inherited_from.items():
            if name.startswith("--"):
                properties[name] = value
        for name, value in INITIAL.items():
            properties.setdefault(name, value)
        for name, value in declared.items():
            if value.strip().lower() == "inherit":
                if name in inherited_from:
                    properties[name] = inherited_from[name]
                continue
            properties[name] = value

        parent_font_px = parent.font_size_px if parent is not None else ROOT_FONT_SIZE_PX
        font_size_px = _resolve_font_size(properties.get("font-size"), parent_font_px)
        properties["font-size"] = f"{font_size_px}px"

        style = ComputedStyle(properties, font_size_px)
        node._styles[cache_key] = style
        return style


def _resolve_font_size(value: str | None, parent_px: float) -> float:
    if value is None:
        return parent_px
    text = value.strip().lower()
    if text in {"inherit", "medium"}:
        return parent_px
    if text.endswith("%"):
        try:
            return parent_px * float(text[:-1]) / 100.0
        except ValueError:
            return parent_px
    pixels = parse_length_px(
        text, font_size_px=parent_px, root_font_size_px=ROOT_FONT_SIZE_PX
    )
    return parent_px if pixels is None else pixels


def _read_declarations(tinycss2, content) -> tuple[tuple[str, str, bool], ...]:
    parser = getattr(tinycss2, "parse_blocks_contents", None) or tinycss2.parse_declaration_list
    out: list[tuple[str, str, bool]] = []
    for node in parser(content, skip_comments=True, skip_whitespace=True):
        if node.type != "declaration":
            continue
        name = node.lower_name
        value = tinycss2.serialize(node.value).strip()
        expanded = _expand_shorthand(name, value)
        if expanded:
            out.extend((longhand, text, node.important) for longhand, text in expanded)
        else:
            out.append((name, value, node.important))
    return tuple(out)


def _parse_inline_style(text: str) -> list[tuple[str, str, bool]]:
    out: list[tuple[str, str, bool]] = []
    for chunk in text.split(";"):
        if ":" not in chunk:
            continue
        name, _, value = chunk.partition(":")
        name, value = name.strip().lower(), value.strip()
        important = value.lower().endswith("!important")
        if important:
            value = value[: -len("!important")].rstrip()
        expanded = _expand_shorthand(name, value)
        if expanded:
            out.extend((longhand, item, important) for longhand, item in expanded)
        elif name and value:
            out.append((name, value, important))
    return out


# --- deriving table chrome from the stylesheet -------------------------

#: How many body rows the probe table carries. Three is the fewest that lets
#: `:first-child`, `:nth-child(odd)` and `:last-child` all be distinct.
PROBE_BODY_ROWS = 3
#: How many columns, for the same reason on the horizontal axis.
PROBE_COLUMNS = 3


def _probe_article(layout: str, table_theme: str, company_class: str | None) -> Element:
    classes = ["article", f"o_report_layout_{layout}", f"o_table_{table_theme}"]
    if company_class:
        classes.append(company_class)
    return build_element("div." + ".".join(classes))


def _probe_lines_table(article: Element) -> tuple[Element, Element, list[list[Element]]]:
    """The stock `o_main_table`, as `sale.report_saleorder` emits it.

    The ``tbody`` is here even though the QWeb template omits it: an HTML
    parser inserts one, and ``.o_table_striped … tbody tr:nth-child(odd) td``
    is written against the parsed tree, not the source.
    """
    page = article.add("div.page")
    table = page.add("table.o_has_total_table.table.o_main_table.table-borderless")
    head = table.add("thead")
    header_row = head.add("tr")
    headers = [header_row.add("th") for _ in range(PROBE_COLUMNS)]
    body = table.add("tbody")
    rows = []
    for _ in range(PROBE_BODY_ROWS):
        row = body.add("tr")
        cells = [row.add("td") for _ in range(PROBE_COLUMNS - 1)]
        cells.append(row.add("td.o_price_total"))
        rows.append(cells)
    return (table, headers[0], rows)


def _probe_totals_table(
    article: Element,
) -> tuple[Element, list[list[Element]], list[Element], list[Element]]:
    """The stock `o_total_table`, inside the `#total` row it always sits in."""
    page = article.add("div.page")
    wrapper = page.add("div.clearfix").add("div#total.row.mt-n3").add("div.col-6.ms-auto")
    table = wrapper.add("table.o_total_table.table.table-borderless")
    body = table.add("tbody")
    rows = []
    for _ in range(PROBE_BODY_ROWS):
        row = body.add("tr.o_subtotal")
        rows.append([row.add("td") for _ in range(2)])
    taxes = body.add("tr.o_taxes")
    taxes_row = [taxes.add("td") for _ in range(2)]
    total = body.add("tr.o_total")
    total_row = [total.add("td") for _ in range(2)]
    return table, rows, taxes_row, total_row


def table_skin_from_css(
    sheet: Stylesheet,
    *,
    layout: str = "standard",
    table_theme: str | None = None,
    company_class: str | None = None,
    kind: str = "lines",
    fallback: TableSkin | None = None,
) -> TableSkin:
    """Read one table's chrome out of the stylesheet instead of guessing it.

    ``layout`` and ``table_theme`` are two settings, not one. Odoo writes
    ``o_report_layout_bubble`` and ``o_table_boxed-rounded`` onto the same
    element, and an engine that treats the table theme as a synonym for the
    document layout draws the wrong table on any company that changed one
    without the other -- which is the default, since the pickers are separate.

    Returns ``fallback`` unchanged when there is no stylesheet to read, so
    this is safe to call unconditionally. Note the default fallback states
    *nothing*, not "the stock look": this function is the compiler behind
    ``odoo_report_theme.TABLE_SKINS``, and a compiler that quietly supplies
    a house style would hide exactly the drift it exists to report.

    The answer is memoised on the stylesheet: it depends on nothing but this
    sheet and the four arguments, and a deployment has one or two
    combinations of them for the life of the process.
    """
    if fallback is None:
        fallback = TableSkin()
    if not sheet.available:
        return fallback

    cache_key = (layout, table_theme, company_class, kind, fallback)
    memoised = sheet._skins.get(cache_key)
    if memoised is not None:
        return memoised

    theme = (table_theme or layout or "standard").strip() or "standard"
    article = _probe_article(layout or "standard", theme, company_class)

    if kind == "totals":
        table, striped_rows, taxes_row, total_row = _probe_totals_table(article)
        header_cell = None
        all_body_rows = [*striped_rows, taxes_row, total_row]
    else:
        table, header_cell, body_rows = _probe_lines_table(article)
        striped_rows, total_row = body_rows, None
        taxes_row = None
        all_body_rows = striped_rows

    # The outer box comes from a generated `::before` that is inset to the
    # table's edges -- `boxed` draws its frame there precisely so that it
    # sits over the cell grid rather than joining it. A border on the table
    # element itself is a different thing (the rule `standard` puts above
    # its totals band), so the two are read separately.
    frame_style = sheet.computed(table, "before")
    # Any side, not just the top. `boxed-rounded` gives the totals band a
    # `::before` with `border-top: none` -- it tucks under the line table --
    # so probing the top alone reports no frame and loses the rounded bottom
    # the band is supposed to have. The line table's own bottom border sits
    # exactly where the band's absent top would, so drawing the frame closed
    # is the same picture.
    frame = next(
        (edge for side in ("top", "left", "bottom", "right")
         if (edge := frame_style.edge(side)) is not None),
        None,
    )
    _CORNERS = (
        "border-top-left-radius", "border-top-right-radius",
        "border-bottom-right-radius", "border-bottom-left-radius",
    )
    frame_corners = tuple(frame_style.length_mm(name) or 0.0 for name in _CORNERS)
    table_top_rule = sheet.computed(table).edge("top")

    def edge_of(cells: list[Element], side: str):
        """A border on a row: on the cells if the stylesheet put it there,
        otherwise on the ``tr``. Both spellings are in the bundle."""
        return sheet.computed(cells[0]).edge(side) or sheet.computed(cells[0].parent).edge(side)

    header_fill = header_text = header_rule = header_top_rule = None
    header_vertical_rule = None
    header_corners = (0.0, 0.0, 0.0, 0.0)
    uppercase = False
    if header_cell is not None:
        head = header_cell.parent.parent
        header_style = sheet.computed(header_cell)
        header_fill = header_style.fill("background-color")
        header_text = header_style.colour("color")
        uppercase = header_style.uppercase or sheet.computed(head).uppercase
        header_rule = header_style.edge("bottom") or sheet.computed(head).edge("bottom")
        header_top_rule = header_style.edge("top") or sheet.computed(head).edge("top")
        header_vertical_rule = header_style.edge("right")
        # `th:first-child` and `th:last-child` round the outer top corners,
        # so the fill follows the frame instead of squaring off outside it.
        row = header_cell.parent
        first, last = row.children[0], row.children[-1]
        header_corners = (
            sheet.computed(first).length_mm("border-top-left-radius") or 0.0,
            sheet.computed(last).length_mm("border-top-right-radius") or 0.0,
            0.0, 0.0,
        )

    # A rule between body rows, on whichever side the stylesheet chose:
    # `striped` puts it on `tr` border-top, `boxed` on `td` border-bottom.
    inner_rule = None
    if len(striped_rows) > 1:
        inner_rule = edge_of(striped_rows[1], "top") or edge_of(striped_rows[0], "bottom")
    bottom_rule = edge_of(all_body_rows[-1], "bottom") if all_body_rows else None
    vertical_rule = sheet.computed(striped_rows[0][0]).edge("right") if striped_rows else None
    price_total_fill = None
    if striped_rows:
        ordinary_fill = sheet.computed(striped_rows[0][0]).fill("background-color")
        candidate_fill = sheet.computed(striped_rows[0][-1]).fill("background-color")
        # A row stripe colours both cells equally.  Only a different answer
        # on the authored o_price_total probe is a cell-scoped fill.
        if candidate_fill != ordinary_fill:
            price_total_fill = candidate_fill

    # A stripe is an *alternation*, so it has to be read as one. A single
    # filled row is a highlight -- `o_line_section`, `o_total` -- and paints
    # every other row when mistaken for a stripe.
    fills = [sheet.computed(cells[0]).fill("background-color") for cells in striped_rows]
    filled = {index for index, fill in enumerate(fills) if fill is not None}
    stripe_fill = None
    if filled in ({index for index in range(len(fills)) if index % 2 == 0},
                  {index for index in range(len(fills)) if index % 2 == 1}):
        stripe_fill = next(fill for fill in fills if fill is not None)

    total_fill = total_text = total_rule = None
    if total_row is not None:
        total_style = sheet.computed(total_row[0])
        total_fill = total_style.fill("background-color")
        total_text = total_style.colour("color")
        total_rule = edge_of(total_row, "top")
    taxes_fill = (
        sheet.computed(taxes_row[0]).fill("background-color")
        if taxes_row is not None else None
    )

    # A full grid needs rules on both axes; anything less is row rules, and
    # drawing a grid for it is what made every non-boxed layout look wrong.
    cell_borders = bool(vertical_rule and (inner_rule or bottom_rule))

    rule_rgb = next(
        (
            edge[1]
            for edge in (
                header_rule, inner_rule, bottom_rule, frame,
                header_top_rule, table_top_rule, total_rule,
            )
            if edge is not None
        ),
        fallback.rule_rgb,
    )

    skin = replace(
        fallback,
        cell_borders=cell_borders,
        header_rule=header_rule is not None,
        header_rule_pt=header_rule[0] if header_rule else 0.0,
        header_rule_rgb=header_rule[1] if header_rule else None,
        header_vertical_rule_pt=(
            header_vertical_rule[0] if header_vertical_rule else 0.0
        ),
        header_vertical_rule_rgb=(
            header_vertical_rule[1] if header_vertical_rule else None
        ),
        header_top_rule_pt=header_top_rule[0] if header_top_rule else 0.0,
        bottom_rule=bottom_rule is not None,
        bottom_rule_pt=bottom_rule[0] if bottom_rule else 0.0,
        row_rules=bool(inner_rule) and not cell_borders,
        row_rule_pt=inner_rule[0] if inner_rule else 0.0,
        row_rule_rgb=inner_rule[1] if inner_rule else None,
        vertical_rule_pt=vertical_rule[0] if vertical_rule else 0.0,
        vertical_rule_rgb=vertical_rule[1] if vertical_rule else None,
        header_fill=header_fill,
        header_text_rgb=header_text,
        stripe_fill=stripe_fill,
        header_uppercase=uppercase,
        rule_rgb=rule_rgb,
        frame_rule=frame is not None,
        frame_rule_pt=frame[0] if frame else 0.0,
        frame_rgb=frame[1] if frame else None,
        frame_corners_mm=frame_corners if frame else (0.0, 0.0, 0.0, 0.0),
        header_corners_mm=header_corners,
        table_top_rule_pt=table_top_rule[0] if table_top_rule else 0.0,
        total_row_fill=total_fill,
        total_row_text_rgb=total_text,
        total_row_rule_pt=total_rule[0] if total_rule else 0.0,
        price_total_fill=price_total_fill,
        taxes_row_fill=taxes_fill,
    )
    sheet._skins[cache_key] = skin
    return skin
