"""Independent stdlib-only reader for DocSubstrate interchange experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ENCODING_ID = "docsubstrate.canonical-json"
PHYSICAL_PACKAGE_ID = "docsubstrate.reference-directory"
COMPONENT_BINDING_PROFILE = "docsubstrate.semantic-component-binding/0.1"


def _manifest_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate / "manifest.json" if candidate.is_dir() else candidate


def load_package(path: str | Path) -> dict[str, Any]:
    value = json.loads(_manifest_path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("root must be an object")
    encoding = value.get("encoding")
    if not isinstance(encoding, dict) or encoding.get("id") != ENCODING_ID:
        raise ValueError("unsupported encoding")
    if not isinstance(value.get("package"), dict):
        raise ValueError("missing package object")
    if not isinstance(value.get("metadata", []), list):
        raise ValueError("metadata must be a list")
    if not isinstance(value.get("occurrences", []), list):
        raise ValueError("occurrences must be a list")
    return value


def summarize(envelope: Mapping[str, Any]) -> dict[str, Any]:
    package = envelope["package"]
    extensions = package.get("extensions", [])
    physical = envelope.get("physical_package") or {}
    return {
        "package_id": package.get("package_id"),
        "format_version": package.get("format_version"),
        "profile": package.get("profile"),
        "capabilities": list(package.get("capabilities", [])),
        "vocabularies": [item.get("vocabulary_id") for item in package.get("vocabularies", [])],
        "object_count": len(package.get("objects", [])),
        "external_reference_count": len(package.get("external_references", [])),
        "relation_count": len(package.get("relations", [])),
        "representation_count": len(package.get("representations", [])),
        "protected_component_count": sum(
            item.get("protection_mode", "clear") == "encrypted"
            for item in package.get("representations", [])
        ),
        "protection_count": len(package.get("protections", [])),
        "key_envelope_count": len(package.get("key_envelopes", [])),
        "artifact_count": len(package.get("artifacts", [])),
        "metadata_count": len(envelope.get("metadata", [])),
        "occurrence_count": len(envelope.get("occurrences", [])),
        "physical_package": physical.get("id"),
        "physical_payload_count": len(physical.get("payloads", {})) if isinstance(physical, dict) else 0,
        "opaque_extensions": [
            {"extension_id": item.get("extension_id"), "capability": item.get("capability"), "critical": bool(item.get("critical", False)), "resource_key": item.get("resource_key")}
            for item in extensions
        ],
    }


def graph(envelope: Mapping[str, Any]) -> dict[str, Any]:
    package = envelope["package"]
    objects = {item["object_id"]: item for item in package.get("objects", [])}
    external_references = {
        item["reference_id"]: item for item in package.get("external_references", [])
    }
    entity_ids = {
        package.get("package_id"),
        *objects,
        *external_references,
        *(item.get("relation_id") for item in package.get("relations", [])),
        *(item.get("representation_id") for item in package.get("representations", [])),
        *(item.get("protection_id") for item in package.get("protections", [])),
        *(item.get("envelope_id") for item in package.get("key_envelopes", [])),
        *(item.get("artifact_id") for item in package.get("artifacts", [])),
        *(item.get("resource_key") for item in package.get("resources", [])),
        *(item.get("extension_id") for item in package.get("extensions", [])),
        *(item.get("claim_id") for item in package.get("preservation_claims", [])),
        *(item.get("occurrence_id") for item in envelope.get("occurrences", [])),
    }
    edges = [
        {
            "relation_id": relation.get("relation_id"),
            "source": relation.get("source_id"),
            "predicate": relation.get("predicate"),
            "target": relation.get("target_id"),
            "source_exists": relation.get("source_id") in entity_ids,
            "target_exists": relation.get("target_id") in entity_ids,
            "source_external": relation.get("source_id") in external_references,
            "target_external": relation.get("target_id") in external_references,
        }
        for relation in package.get("relations", [])
    ]
    return {
        "objects": objects,
        "external_references": external_references,
        "edges": edges,
    }


def metadata_by_basis(envelope: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in envelope.get("metadata", []):
        result.setdefault(str(item.get("basis", "unknown")), []).append(dict(item))
    return result


def occurrences(envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in envelope.get("occurrences", [])]


def component_binding_mapping(
    envelope: Mapping[str, Any],
    representation_id: str,
) -> dict[str, Any]:
    """Reconstruct protected-component identity binding without DocSubstrate."""

    package = envelope["package"]
    representations = {
        item["representation_id"]: item
        for item in package.get("representations", [])
    }
    component = representations.get(representation_id)
    if component is None:
        raise ValueError(f"unknown component representation: {representation_id}")
    objects = {item["object_id"]: item for item in package.get("objects", [])}
    owner = objects.get(component.get("object_id"))
    if owner is None:
        raise ValueError(f"component owner is missing: {component.get('object_id')}")
    vocabulary_versions = {
        item.get("vocabulary_id"): item.get("version")
        for item in package.get("vocabularies", [])
    }

    def semantic_identity(representation: Mapping[str, Any]) -> dict[str, Any]:
        vocabulary_id = representation.get("vocabulary_id")
        return {
            "representation_id": representation.get("representation_id"),
            "representation_type": representation.get("representation_type"),
            "version": representation.get("version"),
            "vocabulary_id": vocabulary_id,
            "vocabulary_version": vocabulary_versions.get(vocabulary_id),
            "schema": representation.get("schema"),
        }

    containers = sorted(
        (
            semantic_identity(candidate)
            for candidate in representations.values()
            if representation_id in candidate.get("component_ids", [])
        ),
        key=lambda item: str(item["representation_id"]),
    )
    owner_vocabulary_id = owner.get("vocabulary_id")
    return {
        "binding_profile": COMPONENT_BINDING_PROFILE,
        "object": {
            "object_id": owner.get("object_id"),
            "object_type": owner.get("object_type"),
            "vocabulary_id": owner_vocabulary_id,
            "vocabulary_version": vocabulary_versions.get(owner_vocabulary_id),
        },
        "component": semantic_identity(component),
        "containing_expressions": containers,
    }


def component_binding_bytes(
    envelope: Mapping[str, Any],
    representation_id: str,
) -> bytes:
    """Encode the independently reconstructed identity binding as canonical bytes."""

    mapping = component_binding_mapping(envelope, representation_id)
    return (
        json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def verify_artifact_bytes(envelope: Mapping[str, Any], resource_key: str, data: bytes) -> dict[str, Any]:
    package = envelope["package"]
    resource = next((item for item in package.get("resources", []) if item.get("resource_key") == resource_key), None)
    if resource is None:
        return {"ok": False, "reason": "resource-not-found"}
    materialization = resource.get("materialization") or {}
    integrity = materialization.get("integrity") or {}
    algorithm = integrity.get("algorithm")
    expected = integrity.get("value")
    if algorithm != "sha256" or not expected:
        return {"ok": False, "reason": "unsupported-or-missing-fixity"}
    actual = hashlib.sha256(data).hexdigest()
    return {"ok": actual == expected, "algorithm": algorithm, "expected": expected, "actual": actual}


def verify_physical_package(path: str | Path, envelope: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(path)
    if not root.is_dir():
        return {"present": False, "ok": True, "payloads": {}}
    physical = envelope.get("physical_package")
    if not isinstance(physical, dict) or physical.get("id") != PHYSICAL_PACKAGE_ID:
        return {"present": False, "ok": False, "reason": "unsupported-physical-package", "payloads": {}}
    payloads = physical.get("payloads", {})
    if not isinstance(payloads, dict):
        return {"present": True, "ok": False, "reason": "invalid-payload-map", "payloads": {}}
    verified: dict[str, Any] = {}
    all_ok = True
    resolved_root = root.resolve()
    for resource_key, entry in payloads.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            verified[resource_key] = {"ok": False, "reason": "invalid-entry"}; all_ok = False; continue
        payload_path = (root / entry["path"]).resolve()
        if resolved_root not in payload_path.parents:
            verified[resource_key] = {"ok": False, "reason": "path-escapes-package"}; all_ok = False; continue
        try:
            data = payload_path.read_bytes()
        except OSError:
            verified[resource_key] = {"ok": False, "reason": "payload-unreadable"}; all_ok = False; continue
        physical_digest = hashlib.sha256(data).hexdigest()
        physical_ok = physical_digest == entry.get("sha256") and len(data) == entry.get("length")
        logical = verify_artifact_bytes(envelope, resource_key, data)
        ok = physical_ok and bool(logical.get("ok"))
        verified[resource_key] = {"ok": ok, "physical_ok": physical_ok, "logical_fixity_ok": bool(logical.get("ok")), "path": entry["path"]}
        all_ok = all_ok and ok
    return {"present": True, "ok": all_ok, "payloads": verified}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("package"); args = parser.parse_args()
    envelope = load_package(args.package)
    output = {"summary": summarize(envelope), "graph": graph(envelope), "metadata_by_basis": metadata_by_basis(envelope), "occurrences": occurrences(envelope), "physical_verification": verify_physical_package(args.package, envelope)}
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if output["physical_verification"].get("ok", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
