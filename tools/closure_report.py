"""Independent preservation-closure report for a physical DocSubstrate package.

This tool intentionally imports no ``docsubstrate`` modules. It evaluates declared
preservation claims from canonical JSON plus locally captured payload bytes and
reports which dependency roles remain independently satisfiable after the source
runtime disappears.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _load_envelope(package_dir: Path) -> dict[str, Any]:
    manifest = package_dir / "manifest.json"
    value = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("package"), dict):
        raise ValueError("invalid manifest")
    return value


def _physical_payloads(envelope: dict[str, Any]) -> dict[str, dict[str, Any]]:
    physical = envelope.get("physical_package")
    if not isinstance(physical, dict):
        return {}
    payloads = physical.get("payloads")
    if not isinstance(payloads, dict):
        return {}
    return {
        str(key): value
        for key, value in payloads.items()
        if isinstance(value, dict)
    }


def _resource_status(
    package_dir: Path,
    resource: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    resource_key = str(resource.get("resource_key"))
    materialization = resource.get("materialization") or {}
    kind = materialization.get("kind")
    integrity = materialization.get("integrity") or {}
    algorithm = integrity.get("algorithm")
    expected = integrity.get("value")

    status: dict[str, Any] = {
        "resource_key": resource_key,
        "kind": kind,
        "integrity_declared": bool(algorithm == "sha256" and expected),
        "captured": False,
        "integrity_verified": False,
        "immutable_local_capture": False,
    }

    if kind == "derived":
        status["reason"] = "derived-materialization-is-not-independent-closure"
        return status

    payload = payloads.get(resource_key)
    if payload is not None:
        relative = payload.get("path")
        if isinstance(relative, str):
            path = (package_dir / relative).resolve()
            if package_dir.resolve() not in path.parents:
                status["reason"] = "payload-path-escapes-package-root"
                return status
            if path.is_file():
                data = path.read_bytes()
                actual = hashlib.sha256(data).hexdigest()
                status["captured"] = True
                status["actual_sha256"] = actual
                status["physical_sha256"] = payload.get("sha256")
                status["physical_length"] = payload.get("length")
                status["integrity_verified"] = (
                    algorithm == "sha256"
                    and bool(expected)
                    and actual == expected
                    and actual == payload.get("sha256")
                )
                status["immutable_local_capture"] = status["integrity_verified"]

                declared_length = materialization.get("length")
                if declared_length is not None:
                    status["length_verified"] = (
                        len(data) == declared_length == payload.get("length")
                    )
                    status["byte_length"] = len(data)
                else:
                    status["length_verified"] = len(data) == payload.get("length")

                if not status["integrity_verified"]:
                    status["reason"] = "captured-payload-fixity-mismatch"
                elif status.get("length_verified") is False:
                    status["reason"] = "captured-payload-length-mismatch"
                return status

    if kind == "external":
        status["reason"] = "external-resource-not-captured-in-package"
    elif kind == "embedded":
        status["reason"] = "embedded-resource-payload-missing-or-unverifiable"
    else:
        status["reason"] = "materialization-missing-or-unknown"
    return status


def closure_report(package_dir: str | Path) -> dict[str, Any]:
    root = Path(package_dir)
    envelope = _load_envelope(root)
    package = envelope["package"]
    payloads = _physical_payloads(envelope)
    resources = {
        item.get("resource_key"): item
        for item in package.get("resources", [])
        if item.get("resource_key")
    }
    resource_status = {
        key: _resource_status(root, resource, payloads)
        for key, resource in resources.items()
    }

    claims_out: list[dict[str, Any]] = []
    missing_dependencies: list[dict[str, Any]] = []

    declared_entity_ids = {
        package.get("package_id"),
        *(item.get("object_id") for item in package.get("objects", [])),
        *(item.get("reference_id") for item in package.get("external_references", [])),
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

    for claim in package.get("preservation_claims", []):
        roles = set(claim.get("roles", []))
        role_failures: dict[str, list[dict[str, Any]]] = {role: [] for role in roles}
        root_failures: list[dict[str, Any]] = []
        root_refs = claim.get("root_refs", [])
        if not root_refs:
            root_failures.append({"reason": "preservation-claim-not-entity-rooted"})
        for root_ref in root_refs:
            if root_ref not in declared_entity_ids:
                root_failures.append(
                    {"root_ref": root_ref, "reason": "root-entity-not-declared"}
                )

        for requirement in claim.get("requirements", []):
            role = requirement.get("role")
            if role not in roles:
                continue
            resource_key = requirement.get("resource_key")
            status = resource_status.get(resource_key)
            failure: dict[str, Any] | None = None

            subject_ref = requirement.get("subject_ref")
            if not subject_ref:
                failure = {
                    "resource_key": resource_key,
                    "reason": "closure-requirement-not-entity-owned",
                }
            elif subject_ref not in declared_entity_ids:
                failure = {
                    "resource_key": resource_key,
                    "subject_ref": subject_ref,
                    "reason": "closure-requirement-subject-not-declared",
                }

            if failure is None and status is None:
                failure = {"resource_key": resource_key, "reason": "resource-not-declared"}
            elif failure is None and status.get("kind") == "derived":
                failure = {"resource_key": resource_key, "reason": status.get("reason")}
            elif failure is None and not status.get("captured"):
                failure = {
                    "resource_key": resource_key,
                    "reason": status.get("reason", "resource-not-captured"),
                }
            elif failure is None and requirement.get("require_integrity", True) and not status.get("integrity_verified"):
                failure = {
                    "resource_key": resource_key,
                    "reason": status.get("reason", "integrity-not-verified"),
                }
            elif failure is None and requirement.get("require_immutable_resolution", True) and not status.get("immutable_local_capture"):
                failure = {
                    "resource_key": resource_key,
                    "reason": "immutable-resolution-not-proven",
                }

            if failure is not None:
                role_failures.setdefault(str(role), []).append(failure)
                missing_dependencies.append(
                    {
                        "claim_id": claim.get("claim_id"),
                        "role": role,
                        **failure,
                    }
                )

        satisfied = sorted(role for role in roles if not role_failures.get(role))
        unsatisfied = sorted(role for role in roles if role_failures.get(role))
        claims_out.append(
            {
                "claim_id": claim.get("claim_id"),
                "ok": not unsatisfied and not root_failures,
                "root_refs": list(root_refs),
                "root_failures": root_failures,
                "satisfied_roles": satisfied,
                "unsatisfied_roles": unsatisfied,
                "failures_by_role": {k: v for k, v in sorted(role_failures.items()) if v},
            }
        )

    return {
        "package_id": package.get("package_id"),
        "source_environment_kill_ready": bool(claims_out) and all(
            item["ok"] for item in claims_out
        ),
        "claims": claims_out,
        "missing_dependencies": missing_dependencies,
        "resources": resource_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir")
    args = parser.parse_args()
    print(json.dumps(closure_report(args.package_dir), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
