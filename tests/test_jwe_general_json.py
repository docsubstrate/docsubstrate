from __future__ import annotations

import base64
import builtins
import hashlib
import json
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jwcrypto import jwe as jwcrypto_jwe
from jwcrypto import jwk

import docsubstrate.jwe_general_json as jwe_profile
from docsubstrate.component_protection import (
    COMPONENT_BINDING_PROFILE,
    component_binding_bytes,
)
from docsubstrate.jwe_general_json import (
    JWE_GENERAL_JSON_PROFILE,
    JWE_MEDIA_TYPE,
    JweProfileError,
    decrypt_component,
    encrypt_component,
)
from docsubstrate.migration import semantic_projection
from docsubstrate.package import (
    ExternalReference,
    KeyEnvelope,
    PackageObject,
    PackageRepresentation,
    PortableInstitutionalPackage,
    ProtectionDescriptor,
)
from docsubstrate.physical_package import (
    PayloadSource,
    verify_reference_directory,
    write_reference_directory,
)
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor

PLAINTEXT = b'{"accounting_code":"SYNTHETIC-4100"}'


def _private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _package(*, envelope_version: str = "1") -> PortableInstitutionalPackage:
    resource = ResourceDescriptor(
        resource_key="resource:jwe",
        resource_type="protected-component",
        media_type=JWE_MEDIA_TYPE,
    )
    return PortableInstitutionalPackage(
        package_id="package:synthetic-jwe",
        format_version="0.3",
        profile="minimum-survivable-closure/0.1",
        objects=(PackageObject("object:record", "SyntheticRecord"),),
        external_references=(
            ExternalReference("recipient:alpha", "KeyRecipient"),
            ExternalReference("recipient:recovery", "KeyRecipient"),
            ExternalReference("wrapping-key:alpha", "WrappingKey"),
            ExternalReference("wrapping-key:recovery", "WrappingKey"),
        ),
        representations=(
            PackageRepresentation(
                "expression:record:v1",
                "object:record",
                "SyntheticExpression",
                version="1",
                component_ids=("component:protected",),
            ),
            PackageRepresentation(
                "component:protected",
                "object:record",
                "OpaqueProtectedComponent",
                version="1",
                resource_keys=("resource:jwe",),
                protection_mode="encrypted",
                protection_id="protection:component",
            ),
        ),
        protections=(
            ProtectionDescriptor(
                "protection:component",
                "component:protected",
                "resource:jwe",
                JWE_GENERAL_JSON_PROFILE,
                COMPONENT_BINDING_PROFILE,
            ),
        ),
        key_envelopes=(
            KeyEnvelope(
                "envelope:alpha",
                "protection:component",
                "recipient:alpha",
                "wrapping-key:alpha",
                JWE_GENERAL_JSON_PROFILE,
                "resource:jwe",
                envelope_version,
            ),
            KeyEnvelope(
                "envelope:recovery",
                "protection:component",
                "recipient:recovery",
                "wrapping-key:recovery",
                JWE_GENERAL_JSON_PROFILE,
                "resource:jwe",
                envelope_version,
            ),
        ),
        resources=(resource,),
    )


def _with_payload_fixity(
    package: PortableInstitutionalPackage,
    payload: bytes,
) -> PortableInstitutionalPackage:
    resource = replace(
        package.resources[0],
        materialization=MaterializationRef(
            kind="embedded",
            media_type=JWE_MEDIA_TYPE,
            length=len(payload),
            integrity=IntegrityDigest("sha256", hashlib.sha256(payload).hexdigest()),
        ),
    )
    return replace(package, resources=(resource,))


def _recipient_keys():
    private_keys = {
        "envelope:alpha": _private_key(),
        "envelope:recovery": _private_key(),
    }
    public_keys = {key: value.public_key() for key, value in private_keys.items()}
    return private_keys, public_keys


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


RFC_7520_PLAINTEXT_SIZE = 273
RFC_7520_PLAINTEXT_SHA256 = "f5c3e318a8c09ba078afdf853fcbb871e91844fa444ee8764bacf5dece5bc8b4"


def _assert_rfc_7520_plaintext(payload: bytes) -> None:
    """Check the public vector without redistributing its literary plaintext."""

    assert len(payload) == RFC_7520_PLAINTEXT_SIZE
    assert hashlib.sha256(payload).hexdigest() == RFC_7520_PLAINTEXT_SHA256


def test_missing_jwe_dependency_names_artifact_extra(monkeypatch) -> None:
    original_import = builtins.__import__

    def reject_cryptography(name, *args, **kwargs):
        if name.startswith("cryptography"):
            raise ImportError("synthetic missing optional dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_cryptography)

    with pytest.raises(RuntimeError, match=r"docsubstrate-a0-review\[jwe\]"):
        jwe_profile._cryptography()


def test_general_json_authorized_reader_round_trip_is_physically_portable(tmp_path) -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    jwe = encrypt_component(
        package,
        "component:protected",
        PLAINTEXT,
        recipient_public_keys=public_keys,
    )
    package = _with_payload_fixity(package, jwe)
    assert package.validate_structure().ok
    assert len(json.loads(jwe)["recipients"]) == 2

    payload = tmp_path / "synthetic.jwe.json"
    payload.write_bytes(jwe)
    root = tmp_path / "bundle"
    manifest_path = write_reference_directory(
        package,
        root,
        payload_sources=(PayloadSource("resource:jwe", payload),),
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stored_path = root / manifest["physical_package"]["payloads"]["resource:jwe"]["path"]
    assert verify_reference_directory(root)["resource:jwe"] == hashlib.sha256(jwe).hexdigest()

    for envelope_id, private_key in private_keys.items():
        assert decrypt_component(
            package,
            "component:protected",
            stored_path.read_bytes(),
            envelope_id=envelope_id,
            recipient_private_key=private_key,
        ) == PLAINTEXT


@pytest.mark.parametrize("target", ["object", "expression", "component"])
def test_component_binding_tampering_fails_closed(target: str) -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    jwe = encrypt_component(
        package,
        "component:protected",
        PLAINTEXT,
        recipient_public_keys=public_keys,
    )
    if target == "object":
        tampered = replace(
            package,
            objects=(replace(package.objects[0], object_type="TamperedRecord"),),
        )
    elif target == "expression":
        tampered = replace(
            package,
            representations=(
                replace(package.representations[0], version="tampered"),
                package.representations[1],
            ),
        )
    else:
        tampered = replace(
            package,
            representations=(
                package.representations[0],
                replace(package.representations[1], version="tampered"),
            ),
        )

    with pytest.raises(JweProfileError, match="JWE validation failed"):
        decrypt_component(
            tampered,
            "component:protected",
            jwe,
            envelope_id="envelope:alpha",
            recipient_private_key=private_keys["envelope:alpha"],
        )


def test_envelope_and_key_rotation_do_not_change_semantic_projection() -> None:
    source = _package(envelope_version="1")
    source_private_keys, source_public_keys = _recipient_keys()
    source_jwe = encrypt_component(
        source,
        "component:protected",
        PLAINTEXT,
        recipient_public_keys=source_public_keys,
    )

    rotated = _package(envelope_version="2")
    rotated_private_keys, rotated_public_keys = _recipient_keys()
    rotated_jwe = encrypt_component(
        rotated,
        "component:protected",
        PLAINTEXT,
        recipient_public_keys=rotated_public_keys,
    )

    assert semantic_projection(source) == semantic_projection(rotated)
    assert source_jwe != rotated_jwe
    assert decrypt_component(
        rotated,
        "component:protected",
        rotated_jwe,
        envelope_id="envelope:alpha",
        recipient_private_key=rotated_private_keys["envelope:alpha"],
    ) == PLAINTEXT
    with pytest.raises(JweProfileError, match="JWE validation failed"):
        decrypt_component(
            rotated,
            "component:protected",
            rotated_jwe,
            envelope_id="envelope:alpha",
            recipient_private_key=source_private_keys["envelope:alpha"],
        )


def test_successful_decryption_does_not_return_an_authorization_claim() -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    jwe = encrypt_component(
        package,
        "component:protected",
        PLAINTEXT,
        recipient_public_keys=public_keys,
    )

    result = decrypt_component(
        package,
        "component:protected",
        jwe,
        envelope_id="envelope:alpha",
        recipient_private_key=private_keys["envelope:alpha"],
    )

    assert result == PLAINTEXT
    assert isinstance(result, bytes)


def test_missing_declared_recipient_fails_closed() -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    jwe = json.loads(
        encrypt_component(
            package,
            "component:protected",
            PLAINTEXT,
            recipient_public_keys=public_keys,
        )
    )
    jwe["recipients"] = jwe["recipients"][:1]

    with pytest.raises(JweProfileError, match="JWE validation failed"):
        decrypt_component(
            package,
            "component:protected",
            jwe,
            envelope_id="envelope:alpha",
            recipient_private_key=private_keys["envelope:alpha"],
        )


def test_profile_writer_is_readable_by_jwcrypto() -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    document = encrypt_component(
        package,
        "component:protected",
        PLAINTEXT,
        recipient_public_keys=public_keys,
    )

    for private_key in private_keys.values():
        token = jwcrypto_jwe.JWE()
        token.deserialize(document.decode())
        token.decrypt(jwk.JWK.from_pyca(private_key))
        assert token.payload == PLAINTEXT


def test_jwcrypto_general_json_writer_is_readable_by_profile() -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    token = jwcrypto_jwe.JWE(
        plaintext=PLAINTEXT,
        protected={"alg": "RSA-OAEP-256", "enc": "A256GCM"},
        aad=component_binding_bytes(package, "component:protected"),
        flattened=False,
    )
    for envelope_id in sorted(public_keys):
        token.add_recipient(
            jwk.JWK.from_pyca(public_keys[envelope_id]),
            header={"kid": envelope_id},
        )
    document = token.serialize(compact=False)

    assert set(json.loads(document)) == {
        "aad",
        "ciphertext",
        "iv",
        "protected",
        "recipients",
        "tag",
    }
    for envelope_id, private_key in private_keys.items():
        assert decrypt_component(
            package,
            "component:protected",
            document,
            envelope_id=envelope_id,
            recipient_private_key=private_key,
        ) == PLAINTEXT


def test_valid_jwe_with_extra_shared_header_is_outside_profile() -> None:
    package = _package()
    private_keys, public_keys = _recipient_keys()
    token = jwcrypto_jwe.JWE(
        plaintext=PLAINTEXT,
        protected={"alg": "RSA-OAEP-256", "enc": "A256GCM"},
        unprotected={"typ": "application/synthetic-test"},
        aad=component_binding_bytes(package, "component:protected"),
        flattened=False,
    )
    for envelope_id in sorted(public_keys):
        token.add_recipient(
            jwk.JWK.from_pyca(public_keys[envelope_id]),
            header={"kid": envelope_id},
        )
    document = token.serialize(compact=False)

    independent_reader = jwcrypto_jwe.JWE()
    independent_reader.deserialize(document)
    independent_reader.decrypt(jwk.JWK.from_pyca(private_keys["envelope:alpha"]))
    assert independent_reader.payload == PLAINTEXT
    with pytest.raises(JweProfileError, match="JWE validation failed"):
        decrypt_component(
            package,
            "component:protected",
            document,
            envelope_id="envelope:alpha",
            recipient_private_key=private_keys["envelope:alpha"],
        )


def test_rfc_7520_a256gcm_content_encryption_vector() -> None:
    """RFC 7520 section 5.2, Figures 72, 85, 86, 89, 90, and 91."""

    cek = _base64url_decode("mYMfsggkTAm0TbvtlFh2hyoXnbEzJQjMxmgLN3d8xXA")
    iv = _base64url_decode("-nBoKLH0YkLZPSI9")
    protected = (
        "eyJhbGciOiJSU0EtT0FFUCIsImtpZCI6InNhbXdpc2UuZ2FtZ2VlQGhv"
        "YmJpdG9uLmV4YW1wbGUiLCJlbmMiOiJBMjU2R0NNIn0"
    )
    ciphertext = _base64url_decode(
        "o4k2cnGN8rSSw3IDo1YuySkqeS_t2m1GXklSgqBdpACm6UJuJowOHC5ytjqYgR"
        "L-I-soPlwqMUf4UgRWWeaOGNw6vGW-xyM01lTYxrXfVzIIaRdhYtEMRBvBWbEw"
        "P7ua1DRfvaOjgZv6Ifa3brcAM64d8p5lhhNcizPersuhw5f-pGYzseva-TUaL8"
        "iWnctc-sSwy7SQmRkfhDjwbz0fz6kFovEgj64X1I5s7E6GLp5fnbYGLa1QUiML"
        "7Cc2GxgvI7zqWo0YIEc7aCflLG1-8BboVWFdZKLK9vNoycrYHumwzKluLWEbSV"
        "maPpOslY2n525DxDfWaVFUfKQxMF56vn4B9QMpWAbnypNimbM8zVOw"
    )
    tag = _base64url_decode("UCGiqJxhBI3IFVdPalHHvA")

    plaintext = AESGCM(cek).decrypt(
        iv,
        ciphertext + tag,
        protected.encode("ascii"),
    )
    _assert_rfc_7520_plaintext(plaintext)


def test_rfc_7520_external_aad_construction_vector() -> None:
    """RFC 7520 section 5.10, Figures 72 and 174-181."""

    cek = _base64url_decode("75m1ALsYv10pZTKPWrsqdg")
    iv = _base64url_decode("veCx9ece2orS7c_N")
    protected = (
        "eyJhbGciOiJBMTI4S1ciLCJraWQiOiI4MWIyMDk2NS04MzMyLTQzZDktYTQ2OC"
        "04MjE2MGFkOTFhYzgiLCJlbmMiOiJBMTI4R0NNIn0"
    )
    aad = (
        "WyJ2Y2FyZCIsW1sidmVyc2lvbiIse30sInRleHQiLCI0LjAiXSxbImZuIix7fS"
        "widGV4dCIsIk1lcmlhZG9jIEJyYW5keWJ1Y2siXSxbIm4iLHt9LCJ0ZXh0Iixb"
        "IkJyYW5keWJ1Y2siLCJNZXJpYWRvYyIsIk1yLiIsIiJdXSxbImJkYXkiLHt9LC"
        "J0ZXh0IiwiVEEgMjk4MiJdLFsiZ2VuZGVyIix7fSwidGV4dCIsIk0iXV1d"
    )
    ciphertext = _base64url_decode(
        "Z_3cbr0k3bVM6N3oSNmHz7Lyf3iPppGf3Pj17wNZqteJ0Ui8p74SchQP8xygM1"
        "oFRWCNzeIa6s6BcEtp8qEFiqTUEyiNkOWDNoF14T_4NFqF-p2Mx8zkbKxI7oPK"
        "8KNarFbyxIDvICNqBLba-v3uzXBdB89fzOI-Lv4PjOFAQGHrgv1rjXAmKbgkft"
        "9cB4WeyZw8MldbBhc-V_KWZslrsLNygon_JJWd_ek6LQn5NRehvApqf9ZrxB4a"
        "q3FXBxOxCys35PhCdaggy2kfUfl2OkwKnWUbgXVD1C6HxLIlqHhCwXDG59weHr"
        "RDQeHyMRoBljoV3X_bUTJDnKBFOod7nLz-cj48JMx3SnCZTpbQAkFV"
    )
    tag = _base64url_decode("vOaH_Rajnpy_3hOtqvZHRA")
    authenticated_data = f"{protected}.{aad}".encode("ascii")

    plaintext = AESGCM(cek).decrypt(
        iv,
        ciphertext + tag,
        authenticated_data,
    )
    _assert_rfc_7520_plaintext(plaintext)
