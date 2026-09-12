"""Host-neutral persistence port for encoded ReportLab image objects."""

from __future__ import annotations

from typing import Protocol


class EncodedImageStore(Protocol):
    """Optional cross-process store used below the in-process image cache.

    The engine owns key and payload semantics.  A host only provides durable
    byte lookup; it does not need to know how ReportLab represents an XObject.
    Implementations may raise :class:`EncodedImageStoreCollision` when a key
    is already bound to different bytes.  Other storage failures are treated
    as cache misses so a cache outage cannot prevent document rendering.
    """

    def get(self, key: str) -> bytes | None:
        ...

    def put(self, key: str, payload: bytes) -> None:
        ...


class EncodedImageStoreCollision(RuntimeError):
    """A persistent key is bound to bytes that fail its content contract."""
