#!/usr/bin/env python3
"""Compile the bundle's flex-container rules, selectors intact.

The parser derives layout rules from the bundle's cascade. Selectors and CSS
units remain intact, while unresolved custom values are passed to runtime
matching. This tool emits the deterministic property slices consumed by the
layout planner.

Usage::

    python tools/derive_layout_rules.py --emit    # print the constant
    python tools/derive_layout_rules.py           # check the shipped one

Scope is every rule that makes an element a flex container, plus the
properties that describe how that container lays out. Deliberately not
"the rules one document happens to need": a selector set fitted to one deployment
is too narrow, and the whole point of keeping
selectors is that matching stays the runtime's job.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

os.environ.setdefault("DOCSUBSTRATE_PROFILE_BOOTSTRAP", "1")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from importlib import import_module

from docsubstrate.font_faces import parse_font_faces

_expand_shorthand = import_module("docsubstrate." + "report_css")._expand_shorthand

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "data"
#: In the order `web.minimal_layout` links them, which is the order the
#: cascade resolves ties in. **pdf first.** It carries a CSS reset that puts
#: `font-size: 100%` on h1-h6 among many others; common carries the
#: Bootstrap that gives them back. Derived the other way round the reset
#: wins every tie and every heading collapses to body size -- which is what
#: the type slice did on its first run, resolving `h1` to `100%`.
BUNDLES = (
    "web." + "report_assets_pdf.min.css",
    "web." + "report_assets_common.min.css",
)

#: What makes an element a flex container. The `-webkit-` spellings matter:
#: the bundle emits them alongside the standard one and wkhtmltopdf's WebKit
#: is what reads them.
FLEX_DISPLAYS = frozenset({"flex", "inline-flex", "-webkit-box", "-webkit-flex"})

#: Properties that describe the resulting layout. Kept together with the
#: display that triggers them so a rule arrives whole.
LAYOUT_PROPERTIES = (
    "display", "flex-direction", "flex-wrap", "flex-flow",
    "justify-content", "align-items", "align-content",
    "gap", "column-gap", "row-gap",
)

#: What the bundle says about a flex *item* rather than its container. The
#: target compatibility engine has no CSS3 flexbox at all -- its
#: EDisplay carries BOX/INLINE_BOX and no FLEX -- so `flex: 1` is dropped and
#: `-webkit-box-flex: 1` is the declaration that actually grows a child. The
#: standard spellings are kept beside it because they are what a reader
#: recognises, and because a future engine would obey them instead.
#:
#: `min-width`/`max-width` travel with it: the box algorithm clamps a child's
#: pass-1 width to them before any growth is distributed, so a slice without
#: them would describe half the rule.
FLEX_ITEM_PROPERTIES = (
    "-webkit-box-flex", "-webkit-box-flex-group", "-webkit-box-ordinal-group",
    "flex", "-webkit-flex", "flex-grow", "flex-basis", "order",
    "min-width", "max-width", "width",
)

_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_DECL_RE = re.compile(r"([-a-zA-Z]+)\s*:\s*([^;]+)")
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _rules(css: str):
    """Every `selector { body }` pair, with comments removed first.

    Removing them first rather than rejecting selectors that contain one.
    `_RULE_RE` captures everything between one rule's `}` and the next `{`,
    so a comment sitting between two rules lands *inside* the second one's
    selector. Comments are removed before matching to keep the selector
    stream stable across minified and expanded inputs.
    """
    for match in _RULE_RE.finditer(_COMMENT_RE.sub("", css)):
        yield " ".join(match.group(1).split()), match.group(2)


def _declarations(body: str, properties=None):
    """The declarations a slice keeps, with shorthands already expanded.

    Filtering by property name before expanding drops every shorthand that
    states a kept property indirectly. `.fa` says the icon face through
    `font: normal normal normal 14px/1 FontAwesome` and never through
    `font-family`, so a compiler that only recognises longhands compiled that
    rule down to `font-size: inherit` and threw the face away -- after which
    the runtime cascade, which does expand it, had nothing left to expand.

    The expansion is `report_css._expand_shorthand`, the same function the
    cascade uses, so the compiled profile and the runtime cannot disagree
    about what a shorthand means.
    """
    properties = properties or LAYOUT_PROPERTIES
    for name, value in _DECL_RE.findall(body):
        name = name.strip().lower()
        important = "!important" in value
        value = value.replace("!important", "").strip()
        for expanded_name, expanded_value in _expand_shorthand(name, value) or [(name, value)]:
            if expanded_name in properties:
                yield expanded_name, expanded_value, important


#: Selectors that cannot describe a printed element and must not enter a
#: compiled slice.
#:
#: A keyframe step (`0%`, `from`) is not a selector at all -- it is a stop
#: inside an `@keyframes` block, and this file's rule regex sees the block's
#: contents rather than the block. An interactive pseudo-class describes a
#: state paper does not have. Both would otherwise match by tag or by
#: nothing, which is the worst kind of stray rule: one that applies widely.
_KEYFRAME_STEP = re.compile(r"^(?:from|to|\d+(?:\.\d+)?%)$", re.IGNORECASE)
_INTERACTIVE = (":hover", ":focus", ":active", ":visited", ":focus-visible")

# The public alpha exposes only the sale-order route.  Product label sheets
# are a separate report family and must not be compiled into that profile,
# even though ``sale_stock`` installs the public ``product`` module whose
# global report bundle contributes those selectors.
def _sale_only_excluded_selector_fragments() -> tuple[str, ...]:
    """Read the sale-profile selector boundary from its independent spec."""
    import json

    spec = ROOT / "public-alpha" / "sale-profile-transform.json"
    if not spec.exists():
        return ("label_sheet",)
    value = json.loads(spec.read_text(encoding="utf-8"))
    return tuple(value["selector_exclude_fragments"])


def _is_printable_selector(selector: str) -> bool:
    if not selector or selector.startswith("@"):
        return False
    parts = [part.strip() for part in selector.split(",")]
    if all(_KEYFRAME_STEP.match(part) for part in parts if part):
        return False
    if any(fragment in selector for fragment in _sale_only_excluded_selector_fragments()):
        return False
    return not any(state in selector for state in _INTERACTIVE)


#: `accept=ANY_VALUE` keeps every value of the trigger property, which is
#: what a property with no interesting subset needs. Distinct from `None`,
#: which still means "use the flex displays": overloading one sentinel for
#: both silently turned the flex slice from 75 rules into 274, because every
#: `display: block` in Bootstrap started qualifying as a flex container.
ANY_VALUE = object()


def derive(trigger="display", accept=None, properties=None, *, drop_variables=False):
    """Rules in the bundle that declare `trigger`, in compiled-profile shape.

    `accept` filters the trigger's values -- flex containers are the rules
    whose `display` is one of the flex spellings -- and `properties` says what
    else to keep from a matching rule, so a row arrives whole. Pass
    `ANY_VALUE` to keep every value.

    `drop_variables` discards declarations whose value contains `var()`.
    The target compatibility parser does not implement custom properties and throws the
    whole declaration away, so for the properties where that changes the
    answer -- colour, most of all -- a compiled profile that kept them would
    be handing the runtime a value the target engine never uses. That is a compiler
    decision and it belongs here rather than in a consumer; see
    so the compiler drops those declarations before runtime.
    """
    accept = FLEX_DISPLAYS if accept is None else accept
    properties = properties or LAYOUT_PROPERTIES
    triggers = (trigger,) if isinstance(trigger, str) else tuple(trigger)
    rules = []
    dropped = 0
    for bundle in BUNDLES:
        path = DATA / bundle
        if not path.exists():
            continue
        for selector, body in _rules(path.read_text(encoding="utf-8")):
            if not _is_printable_selector(selector):
                continue
            declarations = tuple(_declarations(body, properties))
            if drop_variables:
                before = len(declarations)
                declarations = tuple(
                    (name, value, important)
                    for name, value, important in declarations
                    if "var(" not in value
                )
                dropped += before - len(declarations)
            if not declarations:
                continue
            if accept is ANY_VALUE:
                if not any(
                    name in triggers for name, _value, _important in declarations
                ):
                    continue
            elif not any(
                name in triggers and value in accept
                for name, value, _important in declarations
            ):
                continue
            rules.append((selector, declarations))
    derive.dropped_variable_declarations = dropped
    return tuple(rules)


#: Text-transform declarations are retained with their selectors so the
#: cascade can resolve them at runtime.
TRANSFORM_VALUES = frozenset({"uppercase", "lowercase", "capitalize"})

#: Type declarations are retained with their selectors and resolved by the
#: same cascade used for the other property families.
TYPE_PROPERTIES = ("color", "font-size", "font-family")

#: ``font-family`` is retained because generated glyphs use the face carried
#: by their element. Other font longhands use their existing paths.

#: Box-size declarations are retained by property, including rules that state
#: only a minimum or maximum.
BOX_PROPERTIES = ("width", "max-width", "min-width")

#: Every margin the bundles state, on all four sides, values verbatim.
#:
#: This began as a slice filtered to `auto`, because `auto` is the only margin
#: value that *places* a box and the IR already had `margin_start_auto`. The
#: numeric ones were supplied instead by a class predicate over Bootstrap's
#: spacer scale, which is the same substitution `GRID_COLUMNS` was making for
#: `col-*`: it agrees with the bundle wherever both speak -- `.mt-3` is
#: `margin-top: 16px` and the predicate computes 1rem, the same 3.6124mm --
#: and it is silent everywhere else. Every declaration is retained regardless
#: of whether a class utility also expresses the same value.
#:
#: So the filter is gone and the slice is the whole property. `auto` is
#: included rather than kept apart, so one sheet answers for a margin however
#: it is written; `_box_sides(..., allow_auto=True)` already reads that value.
MARGIN_PROPERTIES = (
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
)

#: Clockwise, the order a one-to-four-value shorthand expands into.
MARGIN_SIDES = ("margin-top", "margin-right", "margin-bottom", "margin-left")


def expand_margins(rules):
    """Rewrite every rule's declarations as the four longhands.

    A cascade that resolves per property name cannot resolve a shorthand
    against a longhand, and margins need it to. `.m-0{margin:0 !important}`
    and `p{margin-bottom:1rem}` both survive as separate entries, and a
    consumer that applies the shorthand and then the longhand gives the
    paragraph 1rem -- where the `!important` utility should have won on every
    side.

    So the expansion happens here, in the compiler, before anything cascades:
    each rule's shorthand becomes its four sides in place, later declarations
    in the same rule overwrite earlier ones as CSS says, and importance
    travels with each side. `_box_sides` still reads the result, and now
    every rule speaks only in sides.
    """
    expanded = []
    for selector, declarations in rules:
        sides: dict[str, tuple[str, bool]] = {}
        for name, value, important in declarations:
            if name == "margin":
                parts = value.split()
                if not parts or len(parts) > 4:
                    # Not a shorthand this can expand; keep it verbatim so the
                    # consumer sees exactly what the bundle said.
                    sides["margin"] = (value, important)
                    continue
                if len(parts) == 1:
                    four = parts * 4
                elif len(parts) == 2:
                    four = [parts[0], parts[1], parts[0], parts[1]]
                elif len(parts) == 3:
                    four = [parts[0], parts[1], parts[2], parts[1]]
                else:
                    four = parts
                for side, side_value in zip(MARGIN_SIDES, four):
                    sides[side] = (side_value, important)
            else:
                sides[name] = (value, important)
        expanded.append((
            selector,
            tuple((name, value, important) for name, (value, important) in sides.items()),
        ))
    return tuple(expanded)


def emit(rules, constant="LAYOUT_STYLE_RULES") -> str:
    lines = [f"{constant} = ("]
    for selector, declarations in rules:
        lines.append(f"    (\n        {selector!r},")
        lines.append("        (")
        for name, value, important in declarations:
            lines.append(f"            ({name!r}, {value!r}, {important!r}),")
        lines.append("        ),")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines)


#: What a generated box needs, beyond the content itself. `display` decides
#: whether it exists at all; `position`, `float` and `clear` decide whether
#: this engine can place it; the type properties decide how its text looks;
#: the borders decide whether it paints. Kept together so the runtime is not
#: left inferring a box from the one property that triggered the rule.
PSEUDO_PROPERTIES = (
    "content", "display", "position", "float", "clear",
    "top", "right", "bottom", "left", "width", "height",
    "font-family", "font-size", "font-style", "font-weight", "line-height",
    "color", "white-space", "vertical-align",
    "border-top-width", "border-right-width",
    "border-bottom-width", "border-left-width",
    "border-top-style", "border-right-style",
    "border-bottom-style", "border-left-style",
    "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding-top", "padding-right", "padding-bottom", "padding-left",
)

_PSEUDO_SUFFIX = re.compile(r"::?(before|after)\b")


#: The four physical paddings, under their own CSS names. `padding` itself is
#: not here: `_declarations` expands every shorthand before it filters, so a
#: rule stating the shorthand arrives as the four longhands and a fifth name
#: would only be a second way to say the same thing.
PADDING_PROPERTIES = (
    "padding-top", "padding-right", "padding-bottom", "padding-left",
)


#: `float` and `clear`, under their own CSS names and with their own CSS
#: values. One slice each, and they are derived together because they are one
#: capability: every float is a real element and every clear is
#: a generated box, so a slice that carried only one would place boxes nothing
#: could contain.
FLOAT_PROPERTIES = ("float",)
CLEAR_PROPERTIES = ("clear",)

#: How a legacy box distributes the space its children do not fill.
#:
#: `justify-content` is deliberately **not** here. The string does not appear
#: anywhere in the compatibility parser, so its parser
#: drops the declaration before the cascade sees it -- `!important` and all --
#: and compiling it would put a property in the profile that the parser
#: cannot read. `-webkit-box-pack` is the one it obeys
#: sets the legacy box-pack value from it and from nothing else.
#:
#: Derived by property rather than by a flex `display` on the same rule.
#: Bootstrap states this one on `.justify-content-between`, which declares no
#: display at all, so a display-triggered slice never sees it -- the compiler
#: defect `docs/flex-row-packing-2026-09-05.md` names, here fixed the way
#: that document proposed: the trigger is the property the slice keeps.
BOX_PACK_PROPERTIES = ("-webkit-box-pack",)

#: How a block aligns the content of its line boxes.
#:
#: Derived by property, so a rule that states one without stating a display
#: enters the slice -- `div.o_employee_cv .o_sidebar .o_profile` among them,
#: which is the CV's own contributed stylesheet and the reason the sidebar's
#: two headings were drawn flush left.
#:
#: Values outside `ETextAlign` are dropped here rather than at the consumer.
#: The compatibility value set lists ten and no more, so the parser's
#: parser refuses anything else *before* the cascade sees it -- and the
#: bundle writes `th { text-align: inherit; text-align: -webkit-match-parent }`,
#: where keeping the second would hand `th` a value the parser never had
#: instead of leaving the `inherit` that survives there.
#: A box's edges, under their own CSS names.
#:
#: Derived by property for the same reason padding is: the table slice
#: carries border only incidentally -- eleven selectors of table chrome --
#: so a cell whose edge is stated by any other rule reached nothing.
#: `.o_table_bold table:not(.o_ignore_layout_styling) tbody tr:last-child td`
#: is one, and its 3px is the whole of bold's difference from the other
#: layouts in the totals-to-terms distance.
BORDER_PROPERTIES = tuple(
    f"border-{side}-{part}"
    for side in ("top", "right", "bottom", "left")
    for part in ("width", "style", "color")
)

#: What kind of box an element makes, under its own CSS name.
#:
#: Derived by property so the slice is complete by construction. Asking a
#: partial one is how `.d-block` came to be invisible: `INLINE_LEVEL_RULES`
#: keeps only the rules whose display is an inline spelling, so a rule that
#: turns an inline element into a block was in no slice at all, and a
#: `<span class="d-block">` still looked like an inline box.
DISPLAY_PROPERTIES = ("display",)
#: Values accepted for `display` by the compatibility parser:
#:
#:     inline | block | list-item | run-in | inline-block | table |
#:     inline-table | table-row-group | table-header-group |
#:     table-footer-group | table-row | table-column-group | table-column |
#:     table-cell | table-caption | box | inline-box | none | inherit
#:
#: The display model carries no FLEX, no
#: INLINE_FLEX and no GRID at all -- `BOX` and `INLINE_BOX` are the legacy
#: spellings, and they are what the autoprefixed bundle emits alongside the
#: modern ones the engine cannot read.
#:
#: `inherit` and `initial` are handled before the switch (`:772-782`) and are
#: the only CSS-wide keywords this parser knows: `unset` and `revert` are
#: later CSS and are refused like any other unknown value.
DISPLAY_VALUES = frozenset({
    "inline", "block", "list-item", "run-in", "inline-block",
    "table", "inline-table", "table-row-group", "table-header-group",
    "table-footer-group", "table-row", "table-column-group",
    "table-column", "table-cell", "table-caption",
    "-webkit-box", "-webkit-inline-box", "none",
    "inherit", "initial",
})


def derive_display():
    """`derive_by_property('display')`, then the engine's own value filter.

    The filter has to run here, before anything picks a winner. Bootstrap's
    `.d-flex` states three displays in one rule -- `-webkit-box`,
    `-webkit-flex`, `flex` -- and the target parser refuses the last two,
    so what survives there is `-webkit-box`. A cascade that keeps all three
    and takes the last hands back `flex`, a value that engine has no
    `EDisplay` for. `.d-inline-flex` is the same shape and matters more: its
    surviving value is `-webkit-inline-box`, which is **inline-level**, and
    reading `inline-flex` instead loses that.

    A rule left with no surviving declaration is dropped whole, which is what
    `.d-grid` becomes -- so an inline element carrying it keeps the role its
    element type gives it, rather than being turned into a block by a
    declaration the target parser never applied.
    """
    kept = []
    for selector, declarations in derive_by_property(DISPLAY_PROPERTIES):
        surviving = tuple(
            (name, value, important)
            for name, value, important in declarations
            if value.strip().lower() in DISPLAY_VALUES
        )
        if surviving:
            kept.append((selector, surviving))
    return tuple(kept)

TEXT_ALIGN_PROPERTIES = ("text-align",)
#: `ETextAlign`, plus the two that state no alignment of their own and must
#: still reach the cascade to be resolved or inherited through.
TEXT_ALIGN_VALUES = frozenset({
    "auto", "left", "right", "center", "justify",
    "-webkit-left", "-webkit-right", "-webkit-center", "start", "end",
    "inherit",
})


def derive_text_align():
    """`derive_by_property`, then the engine's own value filter.

    A declaration the compatibility parser refuses is not a declaration the
    cascade weighs, so dropping it here is the difference between
    compiling the sheet and compiling a sheet the renderer never had. A rule
    left with no surviving declaration is dropped whole.
    """
    kept = []
    for selector, declarations in derive_by_property(TEXT_ALIGN_PROPERTIES):
        surviving = tuple(
            (name, value, important)
            for name, value, important in declarations
            if value.strip().lower() in TEXT_ALIGN_VALUES
            or value.strip().lower().startswith("var(")
        )
        if surviving:
            kept.append((selector, surviving))
    return tuple(kept)


def derive_by_property(properties):
    """Every rule stating one of `properties` on a real element, in order.

    A selector list is split and its pseudo parts dropped. `.clearfix::after`
    states the only `clear` in the supported inputs, and it belongs to the pseudo
    slices, which carry it already: keeping it here as well would put the
    same declaration in two places and let a reader believe a native element
    somewhere states one.
    """
    rules = []
    for bundle in BUNDLES:
        path = DATA / bundle
        if not path.exists():
            continue
        for selector, body in _rules(path.read_text(encoding="utf-8")):
            declarations = tuple(_declarations(body, properties))
            if not declarations:
                continue
            kept = [
                part.strip() for part in selector.split(",")
                if part.strip() and not _PSEUDO_SUFFIX.search(part)
                and _is_printable_selector(part.strip())
            ]
            if kept:
                rules.append((", ".join(kept), declarations))
    return tuple(rules)


def derive_padding():
    """Every rule that states a padding, by property and not by trigger.

    A block's padding had one route before this: `box_spacing(classes)`,
    which matches Bootstrap's spacing utility names with a regular
    expression. A padding stated by any other selector reached nothing --
    The inclusion predicate is the property set, so a rule that says nothing
    but a padding is kept. This replaces the former class-name predicate for
    a block rather than being added beside it.
    """
    rules = []
    for bundle in BUNDLES:
        path = DATA / bundle
        if not path.exists():
            continue
        for selector, body in _rules(path.read_text(encoding="utf-8")):
            if not _is_printable_selector(selector):
                continue
            declarations = tuple(_declarations(body, PADDING_PROPERTIES))
            if declarations:
                rules.append((selector, declarations))
    return tuple(rules)


def derive_flex_items():
    """Every rule that states something about a flex item, by property.

    The inclusion predicate is the slice's own property set: a rule is kept
    when it declares any one of them. Not a trigger property plus companions,
    which is how `.w-50 { width: 50% !important }` -- a rule that says
    nothing but a width -- stayed out of the slice that exists to carry
    widths, while the same width sat in the box slice the flex-item consumer
    does not read.

    It keeps rules that have nothing to do with flex, and that is correct
    rather than tolerated: the consumer asks this sheet only about elements
    that *are* flex items, so a `width` on a table cell can enter and never
    be reached. Filtering by what looks flex-shaped is filtering by selector,
    which is the mistake this replaces.
    """
    rules = []
    for bundle in BUNDLES:
        path = DATA / bundle
        if not path.exists():
            continue
        for selector, body in _rules(path.read_text(encoding="utf-8")):
            if not _is_printable_selector(selector):
                continue
            declarations = tuple(_declarations(body, FLEX_ITEM_PROPERTIES))
            if declarations:
                rules.append((selector, declarations))
    return tuple(rules)


def derive_pseudo_content():
    """Rules declaring `content` on a pseudo element, split by which pseudo.

    The pseudo suffix is stripped from the selector so the ordinary cascade
    can match what is left against a real element and its ancestors, which is
    the whole reason this is a slice and not a lookup: `.o_report_layout_striped
    .fa` means nothing without the chain above it, and a class census cannot
    see it at all.

    A selector list is split first. `.a::before, .b` declares content on one
    pseudo and on nothing else, and keeping the list whole would generate
    content for `.b` as well.
    """
    out = {"before": [], "after": []}
    for bundle in BUNDLES:
        path = DATA / bundle
        if not path.exists():
            continue
        for selector, body in _rules(path.read_text(encoding="utf-8")):
            if not _is_printable_selector(selector):
                continue
            declarations = tuple(_declarations(body, PSEUDO_PROPERTIES))
            if not any(name == "content" for name, _v, _i in declarations):
                continue
            for part in selector.split(","):
                part = part.strip()
                found = _PSEUDO_SUFFIX.search(part)
                if not found:
                    continue
                base = _PSEUDO_SUFFIX.sub("", part).strip()
                if not base or not _is_printable_selector(base):
                    continue
                out[found.group(1)].append((base, declarations))
    return {side: tuple(rules) for side, rules in out.items()}


def derive_font_faces():
    """Every `@font-face` in the bundles, in the order they are linked.

    Not a `derive` call: `@font-face` has no selector and never matches an
    element, so it cannot live in a rule slice. It is the other half of what
    a face needs -- the cascade says which family, this says where that
    family's file is -- and without it in the compiled profile the runtime
    would have to parse the 450KB bundle to find out.
    """
    faces = []
    for bundle in BUNDLES:
        path = DATA / bundle
        if not path.exists():
            continue
        for face in parse_font_faces(path.read_text(encoding="utf-8")):
            faces.append((
                face.family,
                tuple((source.url, source.format) for source in face.sources),
                face.weight,
                face.style,
            ))
    return tuple(faces)


def emit_font_faces(faces, constant="FONT_FACE_RULES") -> str:
    lines = [f"{constant} = ("]
    for family, sources, weight, style in faces:
        lines.append(f"    (\n        {family!r},")
        lines.append("        (")
        for url, fmt in sources:
            lines.append(f"            ({url!r}, {fmt!r}),")
        lines.append("        ),")
        lines.append(f"        {weight!r},")
        lines.append(f"        {style!r},")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true")
    arguments = parser.parse_args()

    rules = derive()
    transforms = derive(
        trigger="text-transform",
        accept=TRANSFORM_VALUES,
        properties=("text-transform",),
    )
    colours = derive(
        trigger="color", accept=ANY_VALUE, properties=TYPE_PROPERTIES,
        drop_variables=True,
    )
    dropped_colour = derive.dropped_variable_declarations
    sizes = derive(
        trigger="font-size", accept=ANY_VALUE, properties=TYPE_PROPERTIES,
        drop_variables=True,
    )
    families = derive(
        trigger="font-family", accept=ANY_VALUE, properties=TYPE_PROPERTIES,
        drop_variables=True,
    )
    # A rule declaring more than one of these is reached by more than one
    # trigger, so the union is de-duplicated rather than concatenated.
    #
    # The concatenation is *not* bundle order: it puts every colour rule
    # ahead of every size rule ahead of every family rule, wherever the
    # bundle actually put them. `derive` now takes a tuple of triggers and
    # one pass would order this slice correctly -- but doing that here moves
    # 15613 pairs of already-shipped rules relative to each other, which is
    # its own change with its own compatibility contract. It is left as it was
    # so that this one adds the face and nothing else.
    seen = set()
    types = []
    for rule in colours + sizes + families:
        if rule in seen:
            continue
        seen.add(rule)
        types.append(rule)
    types = tuple(types)
    boxes = []
    seen = set()
    for trigger in BOX_PROPERTIES:
        for rule in derive(
            trigger=trigger, accept=ANY_VALUE, properties=BOX_PROPERTIES,
            drop_variables=True,
        ):
            if rule in seen:
                continue
            seen.add(rule)
            boxes.append(rule)
    dropped_box = derive.dropped_variable_declarations
    boxes = tuple(boxes)
    margins = []
    seen = set()
    for trigger in MARGIN_PROPERTIES:
        for rule in derive(
            trigger=trigger, accept=ANY_VALUE, properties=MARGIN_PROPERTIES,
            drop_variables=True,
        ):
            if rule in seen:
                continue
            seen.add(rule)
            margins.append(rule)
    dropped_margin = derive.dropped_variable_declarations
    margins = expand_margins(margins)
    if arguments.emit:
        print(emit(rules))
        print()
        print(emit(transforms, "TEXT_TRANSFORM_RULES"))
        print()
        print(emit(types, "TYPE_STYLE_RULES"))
        print()
        print(emit(boxes, "BOX_STYLE_RULES"))
        print()
        print(emit(margins, "MARGIN_STYLE_RULES"))
        print()
        print(emit_font_faces(derive_font_faces()))
        print()
        print(emit(derive_flex_items(), "FLEX_ITEM_RULES"))
        print()
        print(emit(derive_padding(), "PADDING_STYLE_RULES"))
        print()
        print(emit(derive_by_property(FLOAT_PROPERTIES), "FLOAT_RULES"))
        print()
        print(emit(derive_by_property(CLEAR_PROPERTIES), "CLEAR_RULES"))
        print()
        print(emit(derive_by_property(BOX_PACK_PROPERTIES), "BOX_PACK_RULES"))
        print()
        print(emit(derive_text_align(), "TEXT_ALIGN_RULES"))
        print()
        print(emit(derive_by_property(BORDER_PROPERTIES), "BORDER_STYLE_RULES"))
        print()
        print(emit(derive_display(), "DISPLAY_RULES"))
        print()
        print(emit(derive_by_property(("opacity",)), "OPACITY_RULES"))
        pseudo = derive_pseudo_content()
        print()
        print(emit(pseudo["before"], "PSEUDO_BEFORE_RULES"))
        print()
        print(emit(pseudo["after"], "PSEUDO_AFTER_RULES"))
        return 0
    print(
        f"type slice: {len(types)} rules, {dropped_colour} var()-valued "
        f"declarations dropped"
    )
    print(
        f"box slice: {len(boxes)} rules, {dropped_box} var()-valued "
        f"declarations dropped"
    )
    print(
        f"margin slice: {len(margins)} rules, {dropped_margin} var()-valued "
        f"declarations dropped"
    )

    try:
        from docsubstrate.odoo_report_profile import (
            BOX_STYLE_RULES,
            LAYOUT_STYLE_RULES,
            MARGIN_STYLE_RULES,
            TEXT_TRANSFORM_RULES,
            TYPE_STYLE_RULES,
        )
    except ImportError:
        print("the compiled rules are not shipped yet; run with --emit")
        return 1
    shipped = {
        "flex-container": (tuple(LAYOUT_STYLE_RULES), rules),
        "text-transform": (tuple(TEXT_TRANSFORM_RULES), transforms),
        "type": (tuple(TYPE_STYLE_RULES), types),
        "box": (tuple(BOX_STYLE_RULES), boxes),
        "margin": (tuple(MARGIN_STYLE_RULES), margins),
    }
    drifted = {
        name: (len(have), len(want))
        for name, (have, want) in shipped.items() if have != want
    }
    if not drifted:
        print(
            f"{len(rules)} flex-container, {len(transforms)} text-transform, "
            f"{len(types)} type, {len(boxes)} box and {len(margins)} "
            f"margin rules; shipped profile matches the bundle"
        )
        return 0
    for name, (have, want) in drifted.items():
        print(f"drift in {name}: bundle has {want} rules, profile has {have}.")
    print("Re-run with --emit and update the profile.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
