"""Provisional JWE General JSON physical profile for protected components.

RFC 7516 owns the serialization and AAD construction. RFC 7518 owns
``RSA-OAEP-256`` and ``A256GCM``. This adapter only binds those mechanisms to
DocSubstrate's existing logical protection and key-envelope records. Successful
decryption proves possession of suitable key material, not institutional
authorization.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from typing import Any

from docsubstrate.component_protection import (
    COMPONENT_BINDING_PROFILE,
    component_binding_bytes,
)
from docsubstrate.package import (
    KeyEnvelope,
    PortableInstitutionalPackage,
    ProtectionDescriptor,
)

JWE_GENERAL_JSON_PROFILE = (
    "docsubstrate.jwe-general-json/rsa-oaep-256+a256gcm/0.1"
)
JWE_MEDIA_TYPE = "application/jose+json"
JWE_KEY_ALGORITHM = "RSA-OAEP-256"
JWE_CONTENT_ALGORITHM = "A256GCM"


class JweProfileError(ValueError):
    """The physical JWE does not satisfy this profile or authenticate."""


def _cryptography():
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # pragma: no cover - exercised by packaging environments
        raise RuntimeError(
            "JWE support requires the 'jwe' extra: "
            "pip install docsubstrate-a0-review[jwe]"
        ) from exc
    return hashes, padding, rsa, AESGCM


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: object) -> bytes:
    if not isinstance(value, str) or "=" in value:
        raise JweProfileError("JWE validation failed")
    try:
        encoded = value.encode("ascii")
        padding = b"=" * (-len(encoded) % 4)
        return base64.b64decode(encoded + padding, altchars=b"-_", validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise JweProfileError("JWE validation failed") from exc


def _json_object(value: bytes | str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise JweProfileError("JWE validation failed")
            result[key] = item
        return result

    try:
        decoded = value.decode("utf-8") if isinstance(value, bytes) else value
        result = json.loads(decoded, object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise JweProfileError("JWE validation failed") from exc
    if not isinstance(result, dict):
        raise JweProfileError("JWE validation failed")
    return result


def _profile_records(
    package: PortableInstitutionalPackage,
    representation_id: str,
) -> tuple[ProtectionDescriptor, dict[str, KeyEnvelope]]:
    representation = next(
        (
            item
            for item in package.representations
            if item.representation_id == representation_id
        ),
        None,
    )
    if (
        representation is None
        or representation.protection_mode != "encrypted"
        or not representation.protection_id
    ):
        raise JweProfileError("representation is not a protected component")
    protection = next(
        (
            item
            for item in package.protections
            if item.protection_id == representation.protection_id
            and item.representation_id == representation_id
        ),
        None,
    )
    if (
        protection is None
        or protection.encryption_profile != JWE_GENERAL_JSON_PROFILE
        or protection.binding_profile != COMPONENT_BINDING_PROFILE
    ):
        raise JweProfileError("protected component does not declare this JWE profile")
    envelopes = {
        item.envelope_id: item
        for item in package.key_envelopes
        if item.protection_id == protection.protection_id
    }
    if not envelopes or any(
        item.key_management_profile != JWE_GENERAL_JSON_PROFILE
        for item in envelopes.values()
    ):
        raise JweProfileError("key envelopes do not declare this JWE profile")
    return protection, envelopes


def encrypt_component(
    package: PortableInstitutionalPackage,
    representation_id: str,
    plaintext: bytes,
    *,
    recipient_public_keys: Mapping[str, object],
) -> bytes:
    """Encrypt synthetic or caller-supplied bytes into General JWE JSON.

    The mapping keys are declared ``KeyEnvelope.envelope_id`` values. Key
    generation, custody, release policy, and authorization remain outside this
    adapter.
    """

    hashes, asymmetric_padding, rsa, AESGCM = _cryptography()
    _, envelopes = _profile_records(package, representation_id)
    if set(recipient_public_keys) != set(envelopes):
        raise JweProfileError("recipient keys must exactly match declared key envelopes")

    protected_header = {
        "alg": JWE_KEY_ALGORITHM,
        "enc": JWE_CONTENT_ALGORITHM,
    }
    protected = _base64url_encode(
        json.dumps(
            protected_header,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    aad = _base64url_encode(component_binding_bytes(package, representation_id))
    authenticated_data = f"{protected}.{aad}".encode("ascii")
    cek = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    encrypted = AESGCM(cek).encrypt(iv, plaintext, authenticated_data)
    ciphertext, tag = encrypted[:-16], encrypted[-16:]

    recipients: list[dict[str, object]] = []
    for envelope_id in sorted(envelopes):
        public_key = recipient_public_keys[envelope_id]
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
            raise JweProfileError("RSA-OAEP-256 recipients require RSA keys of 2048+ bits")
        encrypted_key = public_key.encrypt(
            cek,
            asymmetric_padding.OAEP(
                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        recipients.append(
            {
                "header": {"kid": envelope_id},
                "encrypted_key": _base64url_encode(encrypted_key),
            }
        )

    document = {
        "protected": protected,
        "recipients": recipients,
        "aad": aad,
        "iv": _base64url_encode(iv),
        "ciphertext": _base64url_encode(ciphertext),
        "tag": _base64url_encode(tag),
    }
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def decrypt_component(
    package: PortableInstitutionalPackage,
    representation_id: str,
    document: bytes | str | Mapping[str, Any],
    *,
    envelope_id: str,
    recipient_private_key: object,
) -> bytes:
    """Authenticate and decrypt one recipient path, failing closed.

    A successful result is a cryptographic fact only. It is not a Grant,
    Authority, policy decision, or proof that key release was lawful.
    """

    hashes, asymmetric_padding, rsa, AESGCM = _cryptography()
    _, envelopes = _profile_records(package, representation_id)
    if envelope_id not in envelopes:
        raise JweProfileError("JWE validation failed")
    if (
        not isinstance(recipient_private_key, rsa.RSAPrivateKey)
        or recipient_private_key.key_size < 2048
    ):
        raise JweProfileError("JWE validation failed")

    try:
        value = _json_object(document)
        if set(value) != {
            "protected",
            "recipients",
            "aad",
            "iv",
            "ciphertext",
            "tag",
        }:
            raise JweProfileError("JWE validation failed")
        protected = value["protected"]
        aad = value["aad"]
        protected_header = json.loads(_base64url_decode(protected))
        if protected_header != {
            "alg": JWE_KEY_ALGORITHM,
            "enc": JWE_CONTENT_ALGORITHM,
        }:
            raise JweProfileError("JWE validation failed")

        expected_aad = _base64url_encode(
            component_binding_bytes(package, representation_id)
        )
        if not isinstance(aad, str) or aad != expected_aad:
            raise JweProfileError("JWE validation failed")

        recipients = value["recipients"]
        if not isinstance(recipients, list) or not recipients:
            raise JweProfileError("JWE validation failed")
        recipients_by_id: dict[str, dict[str, Any]] = {}
        for item in recipients:
            if not isinstance(item, dict) or set(item) != {"header", "encrypted_key"}:
                raise JweProfileError("JWE validation failed")
            header = item.get("header")
            if not isinstance(header, dict) or set(header) != {"kid"}:
                raise JweProfileError("JWE validation failed")
            recipient_id = header.get("kid")
            if not isinstance(recipient_id, str) or recipient_id in recipients_by_id:
                raise JweProfileError("JWE validation failed")
            _base64url_decode(item.get("encrypted_key"))
            recipients_by_id[recipient_id] = item
        if set(recipients_by_id) != set(envelopes):
            raise JweProfileError("JWE validation failed")
        recipient = recipients_by_id[envelope_id]

        cek = recipient_private_key.decrypt(
            _base64url_decode(recipient["encrypted_key"]),
            asymmetric_padding.OAEP(
                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        if len(cek) != 32:
            raise JweProfileError("JWE validation failed")
        authenticated_data = f"{protected}.{aad}".encode("ascii")
        iv = _base64url_decode(value["iv"])
        tag = _base64url_decode(value["tag"])
        if len(iv) != 12 or len(tag) != 16:
            raise JweProfileError("JWE validation failed")
        ciphertext_and_tag = _base64url_decode(value["ciphertext"]) + tag
        return AESGCM(cek).decrypt(
            iv,
            ciphertext_and_tag,
            authenticated_data,
        )
    except JweProfileError:
        raise
    except Exception as exc:
        raise JweProfileError("JWE validation failed") from exc
