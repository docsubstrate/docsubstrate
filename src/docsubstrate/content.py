"""Immutable content identity.

Storage backends belong to a later phase. Host adapters (for example Odoo
``ir.attachment``) stamp this digest onto their own index records.
"""

from __future__ import annotations

import hashlib


def content_digest(payload: bytes) -> str:
    """SHA-256 hex digest of a content blob.

    Digests are of bytes, never of host record ids. The same PDF from two
    invoices must not share an identity unless the bytes are identical.
    """
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError("content digest requires bytes")
    return hashlib.sha256(bytes(payload)).hexdigest()
