"""Project-owned geometry for horizontal rows and inline runs.

The functions in this module operate only on the public IR fields and the
planner's declared CSS-pixel scale.  They intentionally contain no renderer-
specific source transcription: they are the executable invariants that both
measurement and placement consume.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any


def _finite(name: str, value: float, *, nonnegative: bool = False) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if nonnegative and number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _pixel_size(css_px_per_inch: float) -> float:
    scale = _finite("CSS pixels per inch", css_px_per_inch)
    if scale <= 0.0:
        raise ValueError("CSS pixels per inch must be positive")
    return 25.4 / scale


def _whole_pixels(length_mm: float, pixel_mm: float) -> int:
    if length_mm <= 0.0:
        return 0
    ratio = math.nextafter(length_mm / pixel_mm, math.inf)
    return max(0, math.floor(ratio))


def _nearest_pixels(length_mm: float, pixel_mm: float) -> int:
    if length_mm <= 0.0:
        return 0
    complete, remainder = divmod(length_mm, pixel_mm)
    return int(complete) + int(remainder >= pixel_mm / 2.0)


def _row_extent_mm(cells: Sequence[Any], widths: Sequence[float], gap_mm: float) -> float:
    if len(cells) != len(widths):
        raise ValueError("horizontal cell and width counts must agree")
    gap = _finite("horizontal gap", gap_mm, nonnegative=True)
    extent = gap * max(0, len(cells) - 1)
    for index, (cell, width) in enumerate(zip(cells, widths)):
        extent += _finite(f"cell {index} width", width, nonnegative=True)
        extent += _finite(f"cell {index} left margin", cell.margin_left_mm)
        extent += _finite(f"cell {index} right margin", cell.margin_right_mm)
    return extent


def allocate_horizontal_widths(
    cells: Sequence[Any],
    row_width_mm: float,
    gap_mm: float,
    css_px_per_inch: float,
    intrinsic_width: Callable[[Any, float], float | None],
    warn_unmeasurable: Callable[[Any], None],
) -> tuple[float, ...]:
    """Resolve bases, then distribute only complete remaining CSS pixels."""
    row_width = _finite("row width", row_width_mm, nonnegative=True)
    gap = _finite("horizontal gap", gap_mm, nonnegative=True)
    pixel_mm = _pixel_size(css_px_per_inch)
    if not cells:
        return ()

    margins = 0.0
    for index, cell in enumerate(cells):
        margins += _finite(f"cell {index} left margin", cell.margin_left_mm)
        margins += _finite(f"cell {index} right margin", cell.margin_right_mm)
    content_budget = max(
        0.0,
        row_width - margins - gap * max(0, len(cells) - 1),
    )

    preferred: list[float] = []
    growth: list[float] = []
    for index, cell in enumerate(cells):
        grow = _finite(f"cell {index} growth", cell.flex_grow, nonnegative=True)
        growth.append(grow)
        if cell.width_mm is not None:
            base = _finite(f"cell {index} stated width", cell.width_mm, nonnegative=True)
        elif cell.width_fraction is not None:
            fraction = _finite(
                f"cell {index} width fraction",
                cell.width_fraction,
                nonnegative=True,
            )
            base = row_width * fraction
        else:
            measured = intrinsic_width(cell, row_width)
            if measured is None:
                warn_unmeasurable(cell)
                base = content_budget / len(cells)
            else:
                base = _finite(
                    f"cell {index} intrinsic width",
                    measured,
                    nonnegative=True,
                )
        if cell.min_width_mm is not None:
            minimum = _finite(
                f"cell {index} minimum width",
                cell.min_width_mm,
                nonnegative=True,
            )
            base = max(base, minimum)
        preferred.append(base)

    free_mm = content_budget - sum(preferred)
    grow_total = sum(growth)
    units = _whole_pixels(free_mm, pixel_mm)
    if units == 0 or grow_total == 0.0:
        return tuple(preferred)

    additions = [0] * len(cells)
    eligible = [index for index, weight in enumerate(growth) if weight > 0.0]
    cumulative = 0.0
    assigned = 0
    for position, index in enumerate(eligible):
        cumulative += growth[index]
        target = (
            units if position == len(eligible) - 1 else math.floor(units * cumulative / grow_total)
        )
        additions[index] = target - assigned
        assigned = target
    return tuple(base + extra * pixel_mm for base, extra in zip(preferred, additions))


def inline_alignment_offset(
    *,
    cells: Sequence[Any],
    widths: Sequence[float],
    gap_mm: float,
    row_width_mm: float,
    inline_run: bool,
    align: str | None,
) -> float:
    """Return one continuous line-box shift; never synthesize trailing gap."""
    row_width = _finite("row width", row_width_mm, nonnegative=True)
    if not inline_run or not cells:
        return 0.0
    extent = _row_extent_mm(cells, widths, gap_mm)
    spare = max(0.0, row_width - extent)
    if align in {"center", "-webkit-center"}:
        return spare / 2.0
    if align in {"right", "end", "-webkit-right"}:
        return spare
    return 0.0


def packed_offsets(
    *,
    cells: Sequence[Any],
    widths: Sequence[float],
    gap_mm: float,
    row_width_mm: float,
    css_px_per_inch: float,
    pack: str | None,
) -> tuple[float, ...]:
    """Distribute one measured whole-pixel remainder across a row."""
    row_width = _finite("row width", row_width_mm, nonnegative=True)
    pixel_mm = _pixel_size(css_px_per_inch)
    extent = _row_extent_mm(cells, widths, gap_mm)
    count = len(cells)
    if count == 0:
        return ()
    zeros = (0.0,) * count
    units = _nearest_pixels(row_width - extent, pixel_mm)
    if units == 0:
        return zeros
    if pack == "end":
        return (units * pixel_mm,) * count
    if pack == "center":
        shift = (units // 2) * pixel_mm
        return (shift,) * count
    if pack == "justify" and count > 1:
        slots = count - 1
        return tuple(math.floor(units * index / slots) * pixel_mm for index in range(count))
    return zeros
