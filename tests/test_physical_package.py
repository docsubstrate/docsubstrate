from __future__ import annotations

import hashlib
import importlib.util
import shutil
from pathlib import Path

from docsubstrate.package import (
    PackageArtifact,
    PackageObject,
    PackageRepresentation,
    PortableInstitutionalPackage,
)
from docsubstrate.physical_package import (
    PayloadSource,
    verify_reference_directory,
    write_reference_directory,
)
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor


def _load_independent_reader(repo_root: Path):
    path = repo_root / "tools" / "independent_reader.py"
    spec = importlib.util.spec_from_file_location("independent_reader", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_reference_directory_survives_move_and_independent_reader(tmp_path: Path) -> None:
    payload = tmp_path / "sample.pdf"
    payload.write_bytes(b"%PDF-1.7\nreference payload\n")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    length = payload.stat().st_size

    resource = ResourceDescriptor(
        resource_key="artifact:sample",
        resource_type="document-artifact",
        media_type="application/pdf",
        materialization=MaterializationRef(
            kind="embedded",
            media_type="application/pdf",
            length=length,
            integrity=IntegrityDigest("sha256", digest),
        ),
    )
    package = PortableInstitutionalPackage(
        package_id="package:test",
        format_version="0.1",
        profile="general",
        objects=(PackageObject("object:1", "example"),),
        representations=(PackageRepresentation("representation:1", "object:1", "pdf"),),
        artifacts=(PackageArtifact("artifact:1", "representation:1", "artifact:sample"),),
        resources=(resource,),
    )

    root = tmp_path / "bundle-a"
    write_reference_directory(
        package,
        root,
        payload_sources=(PayloadSource("artifact:sample", payload),),
    )
    assert verify_reference_directory(root) == {"artifact:sample": digest}

    moved = tmp_path / "renamed-and-moved-bundle"
    shutil.move(str(root), moved)
    assert verify_reference_directory(moved) == {"artifact:sample": digest}

    repo_root = Path(__file__).resolve().parents[1]
    reader = _load_independent_reader(repo_root)
    envelope = reader.load_package(moved)
    result = reader.verify_physical_package(moved, envelope)
    assert result["ok"] is True
    assert result["payloads"]["artifact:sample"]["logical_fixity_ok"] is True


def test_writer_rejects_payload_that_disagrees_with_manifest_fixity(tmp_path: Path) -> None:
    payload = tmp_path / "sample.bin"
    payload.write_bytes(b"wrong bytes")
    resource = ResourceDescriptor(
        resource_key="resource:1",
        resource_type="opaque",
        materialization=MaterializationRef(
            kind="embedded",
            length=len(b"expected bytes"),
            integrity=IntegrityDigest("sha256", hashlib.sha256(b"expected bytes").hexdigest()),
        ),
    )
    package = PortableInstitutionalPackage(
        package_id="package:test",
        format_version="0.1",
        profile="general",
        resources=(resource,),
    )

    try:
        write_reference_directory(
            package,
            tmp_path / "bundle",
            payload_sources=(PayloadSource("resource:1", payload),),
        )
    except ValueError as exc:
        assert "fixity mismatch" in str(exc) or "length mismatch" in str(exc)
    else:
        raise AssertionError("writer must reject mismatched payload bytes")
