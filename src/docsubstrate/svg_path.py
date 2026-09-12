"""Read the `d` of an SVG path, so page art can be generated rather than copied.

Odoo states each layout's page art as an inline `<svg>` in its template --
Bubble a circle and a wave, Wave two waves, Folder a rectangle and an angled
corner. Those are geometry, not images, so a vector engine can draw them; and
copying their numbers by hand is the same mistake as hand-carving a
table skin, only harder to check.

This reads the subset those templates actually use: ``M``, ``L``, ``H``,
``V``, ``C``, ``S`` and ``Z``, absolute and relative. Anything else raises,
because a path this cannot read is one it would otherwise draw wrongly and
silently.
"""

from __future__ import annotations

import re

__all__ = ["UnsupportedPath", "circle_path", "parse_path", "transform_path"]

#: A quarter circle drawn as one cubic Bezier needs its control points this
#: far along each tangent: ``4/3 * (sqrt(2) - 1)``.  SVG ``circle`` page art
#: and ReportLab's independently rounded rectangle corners must use the same
#: geometric approximation; keeping the value here prevents those two vector
#: paths from drifting apart.
_ARC_K = 0.5522847498307936

#: Every letter is captured, not just the supported ones -- a command this
#: reader skipped silently would leave its coordinates to be consumed as an
#: implicit lineto, drawing something plausible and wrong.
_TOKENS = re.compile(r"[A-Za-z]|-?\d*\.?\d+(?:[eE][+-]?\d+)?")
#: The commands the stock layouts use. `A`, `Q` and `T` are absent from all
#: seven, so they raise rather than being approximated.
_SUPPORTED = set("MmLlHhVvCcSsZz")


class UnsupportedPath(ValueError):
    """A path command this reader declines to guess at."""


def circle_path(cx: float, cy: float, radius: float):
    """Return an SVG circle as four cubic Bezier segments.

    The SVG basic shape has an exact centre and radius but the PageArt IR has
    one general vector primitive.  Four standard quarter-circle cubics keep
    that IR general without rasterising the shape or inventing a Bubble-only
    drawing command.
    """
    tangent = radius * _ARC_K
    return (
        ("m", cx + radius, cy),
        ("c", cx + radius, cy + tangent, cx + tangent, cy + radius, cx, cy + radius),
        ("c", cx - tangent, cy + radius, cx - radius, cy + tangent, cx - radius, cy),
        ("c", cx - radius, cy - tangent, cx - tangent, cy - radius, cx, cy - radius),
        ("c", cx + tangent, cy - radius, cx + radius, cy - tangent, cx + radius, cy),
        ("z",),
    )


def parse_path(d: str):
    """`d` to a flat list of `("m"|"l"|"c"|"z", *coords)` in user units.

    Curves are always emitted as cubic `c` with both control points, so the
    consumer needs one curve primitive rather than four.
    """
    tokens = _TOKENS.findall(d or "")
    out: list[tuple] = []
    index = 0
    command = None
    x = y = 0.0
    start_x = start_y = 0.0
    previous_control: tuple[float, float] | None = None

    def number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            if token not in _SUPPORTED:
                raise UnsupportedPath(f"unsupported path command {token!r}")
            command = token
            index += 1
        elif command is None:
            raise UnsupportedPath(f"path data starts with {token!r}")
        elif index + 1 >= len(tokens) and command.lower() in "mlc":
            raise UnsupportedPath(f"path data ends mid-command: {d!r}")
        elif command in "Mm":
            # A repeated pair after a moveto is an implicit lineto.
            command = "L" if command == "M" else "l"
        if command is None:
            raise UnsupportedPath(d)

        lower = command.lower()
        relative = command.islower()
        if lower == "z":
            out.append(("z",))
            x, y = start_x, start_y
            previous_control = None
            continue
        if lower == "m":
            dx, dy = number(), number()
            x, y = (x + dx, y + dy) if relative else (dx, dy)
            start_x, start_y = x, y
            out.append(("m", x, y))
            previous_control = None
        elif lower == "l":
            dx, dy = number(), number()
            x, y = (x + dx, y + dy) if relative else (dx, dy)
            out.append(("l", x, y))
            previous_control = None
        elif lower == "h":
            dx = number()
            x = x + dx if relative else dx
            out.append(("l", x, y))
            previous_control = None
        elif lower == "v":
            dy = number()
            y = y + dy if relative else dy
            out.append(("l", x, y))
            previous_control = None
        elif lower == "c":
            x1, y1, x2, y2, dx, dy = (number() for _ in range(6))
            if relative:
                x1, y1, x2, y2, dx, dy = x + x1, y + y1, x + x2, y + y2, x + dx, y + dy
            out.append(("c", x1, y1, x2, y2, dx, dy))
            previous_control = (x2, y2)
            x, y = dx, dy
        elif lower == "s":
            x2, y2, dx, dy = (number() for _ in range(4))
            if relative:
                x2, y2, dx, dy = x + x2, y + y2, x + dx, y + dy
            if previous_control is None:
                x1, y1 = x, y
            else:
                x1, y1 = 2 * x - previous_control[0], 2 * y - previous_control[1]
            out.append(("c", x1, y1, x2, y2, dx, dy))
            previous_control = (x2, y2)
            x, y = dx, dy
        else:
            raise UnsupportedPath(f"unsupported path command {command!r}")
    return out


def transform_path(segments, *, scale_x, scale_y, offset_x, offset_y, height_mm):
    """Map user units onto the sheet, flipping to a bottom-left origin.

    SVG measures y downwards from the box's top; a PDF measures it upwards
    from the paper's bottom. `offset_y` is the box's top edge, in
    millimetres from the top of the page.
    """
    out = []
    for segment in segments:
        name, coords = segment[0], segment[1:]
        moved = []
        for index in range(0, len(coords), 2):
            moved.append(offset_x + coords[index] * scale_x)
            moved.append(height_mm - (offset_y + coords[index + 1] * scale_y))
        out.append((name, *moved))
    return out
