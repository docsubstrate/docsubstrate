"""Reference physical packaging experiment for Portable Institutional Packages.

This module deliberately defines a directory transport, not the DocSubstrate wire
standard. Logical identity remains in the canonical manifest. Physical pathnames
are content-addressed materialization locators and must never become institutional
identity.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from docsubstrate.interchange_json import MetadataAssertion, OccurrenceRecord, package_to_mapping
from docsubstrate.package import PortableInstitutionalPackage

PHYSICAL_PACKAGE_ID = "docsubstrate.reference-directory"
PHYSICAL_PACKAGE_VERSION = "0.1"
MANIFEST_NAME = "manifest.json"
PAYLOAD_DIR = "payload"


@dataclass(frozen=True, slots=True)
class PayloadSource:
    """Bytes supplied for one resource declared by the logical package."""

    resource_key: str
    source_path: Path


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            length += len(chunk)
    return digest.hexdigest(), length


def write_reference_directory(
    package: PortableInstitutionalPackage,
    destination: Path,
    *,
    payload_sources: Sequence[PayloadSource] = (),
    metadata_assertions: Sequence[MetadataAssertion] = (),
    occurrences: Sequence[OccurrenceRecord] = (),
) -> Path:
    """Write a self-describing reference directory using content-addressed payloads."""

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    payload_dir = destination / PAYLOAD_DIR
    payload_dir.mkdir(exist_ok=True)

    declared = {resource.resource_key: resource for resource in package.resources}
    physical_payloads: dict[str, dict[str, object]] = {}

    for source in payload_sources:
        resource = declared.get(source.resource_key)
        if resource is None:
            raise ValueError(f"payload resource is not declared: {source.resource_key}")
        source_path = Path(source.source_path)
        digest, length = _sha256_file(source_path)

        materialization = resource.materialization
        expected = materialization.integrity if materialization is not None else None
        if expected is not None:
            if expected.algorithm != "sha256":
                raise ValueError(f"unsupported integrity algorithm: {expected.algorithm}")
            if expected.value.lower() != digest:
                raise ValueError(f"payload fixity mismatch: {source.resource_key}")
        if (
            materialization is not None
            and materialization.length is not None
            and materialization.length != length
        ):
            raise ValueError(f"payload length mismatch: {source.resource_key}")

        suffix = source_path.suffix.lower()
        filename = f"sha256-{digest}{suffix}"
        target = payload_dir / filename
        if not target.exists():
            shutil.copyfile(source_path, target)

        physical_payloads[source.resource_key] = {
            "path": f"{PAYLOAD_DIR}/{filename}",
            "sha256": digest,
            "length": length,
        }

    manifest = package_to_mapping(
        package,
        metadata_assertions=metadata_assertions,
        occurrences=occurrences,
    )
    manifest["physical_package"] = {
        "id": PHYSICAL_PACKAGE_ID,
        "version": PHYSICAL_PACKAGE_VERSION,
        "payloads": {key: physical_payloads[key] for key in sorted(physical_payloads)},
    }
    manifest_path = destination / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def verify_reference_directory(root: Path) -> Mapping[str, str]:
    """Verify physical payload paths/fixity without resolving domain semantics."""

    root = Path(root)
    manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    physical = manifest.get("physical_package")
    if not isinstance(physical, dict) or physical.get("id") != PHYSICAL_PACKAGE_ID:
        raise ValueError("not a supported reference physical package")
    payloads = physical.get("payloads", {})
    if not isinstance(payloads, dict):
        raise ValueError("physical package payloads must be an object")

    result: dict[str, str] = {}
    for resource_key, entry in payloads.items():
        if not isinstance(entry, dict):
            raise ValueError(f"invalid payload entry: {resource_key}")
        relative = entry.get("path")
        expected_digest = entry.get("sha256")
        expected_length = entry.get("length")
        if not isinstance(relative, str) or not isinstance(expected_digest, str):
            raise ValueError(f"invalid payload locator: {resource_key}")
        path = (root / relative).resolve()
        if root.resolve() not in path.parents:
            raise ValueError(f"payload escapes package root: {resource_key}")
        digest, length = _sha256_file(path)
        if digest != expected_digest or length != expected_length:
            raise ValueError(f"physical payload verification failed: {resource_key}")
        result[resource_key] = digest
    return result
