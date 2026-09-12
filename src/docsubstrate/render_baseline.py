"""Small rendering contracts owned by the public alpha.

The module contains three explicit policies used by the packaged renderer:
a fail-closed set of compatibility choices, descriptive metadata for fixed
profile values, and the CSS adjacent-margin operation.  It has no discovery
or environment-dependent branches.
"""

from __future__ import annotations

import math
from collections.abc import Callable

#: The only behaviours this alpha's packaged call sites still name. Anything
#: else reaching `matches_oracle` is an undocumented branch and raises.
_BEHAVIOURS = frozenset(
    {
        "page_box_whole_points",
        "layout_advances_in_whole_pixels",
        "thead_never_repeats",
    }
)

_compatibility_provider: Callable[[str], bool] | None = None


def _register_compatibility_provider(provider: Callable[[str], bool]) -> None:
    """Let an unbundled research layer drive the same named switches."""
    global _compatibility_provider
    _compatibility_provider = provider


def matches_oracle(name: str) -> bool:
    """Whether this engine currently imitates wkhtmltopdf in the named way.

    Raising on an unnamed behaviour keeps this an explicit, reviewed set
    instead of silently extending the rendering contract.
    """
    if _compatibility_provider is not None:
        return _compatibility_provider(name)
    if name not in _BEHAVIOURS:
        raise KeyError(f"render_baseline: unknown rendering behaviour {name!r}")
    return True


def collapse_margins(*values: float | None) -> float:
    """Collapse adjacent margins the way CSS 2.1 section 8.3.1 does.

    Not a sum: two touching margins produce the larger of the positive
    values present plus the smaller (most negative) of the negative ones.
    """
    positive = 0.0
    negative = 0.0
    for value in values:
        number = 0.0 if value is None else float(value)
        if not math.isfinite(number):
            raise ValueError("margin values must be finite")
        if number > positive:
            positive = number
        elif number < negative:
            negative = number
    return positive + negative
