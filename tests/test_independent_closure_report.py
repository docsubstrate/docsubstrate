from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from docsubstrate.durable import ClosureRequirement, PreservationClaim
from docsubstrate.package import ExternalReference, PackageObject, PortableInstitutionalPackage
from docsubstrate.physical_package import PayloadSource, write_reference_directory
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor


def _load_closure_tool(repo_root: Path):
    path = repo_root / "tools" / "closure_report.py"
    spec = importlib.util.spec_from_file_location("closure_report", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_independent_closure_report_distinguishes_roles(tmp_path: Path) -> None:
    evidence_bytes = b"evidence bytes"
    evidence_path = tmp_path / "evidence.bin"
    evidence_path.write_bytes(evidence_bytes)
    evidence_digest = hashlib.sha256(evidence_bytes).hexdigest()

    evidence = ResourceDescriptor(
        resource_key="resource:evidence",
        resource_type="evidence-artifact",
        materialization=MaterializationRef(
            kind="embedded",
            length=len(evidence_bytes),
            integrity=IntegrityDigest("sha256", evidence_digest),
        ),
    )
    vocabulary = ResourceDescriptor(
        resource_key="resource:vocabulary",
        resource_type="vocabulary",
        materialization=MaterializationRef(
            kind="external",
            resolver="https",
            integrity=IntegrityDigest("sha256", "0" * 64),
        ),
    )
    claim = PreservationClaim(
        claim_id="claim:1",
        roles=frozenset({"evidentiary", "interpretation"}),
        requirements=(
            ClosureRequirement(
                "resource:evidence", "evidentiary", subject_ref="object:record"
            ),
            ClosureRequirement(
                "resource:vocabulary", "interpretation", subject_ref="object:record"
            ),
        ),
        root_refs=("object:record",),
    )
    package = PortableInstitutionalPackage(
        package_id="package:closure-test",
        format_version="0.1",
        profile="durable",
        objects=(PackageObject("object:record", "Record"),),
        resources=(evidence, vocabulary),
        preservation_claims=(claim,),
    )

    root = tmp_path / "bundle"
    write_reference_directory(
        package,
        root,
        payload_sources=(PayloadSource("resource:evidence", evidence_path),),
    )

    tool = _load_closure_tool(Path(__file__).resolve().parents[1])
    report = tool.closure_report(root)

    assert report["source_environment_kill_ready"] is False
    assert report["claims"][0]["satisfied_roles"] == ["evidentiary"]
    assert report["claims"][0]["unsatisfied_roles"] == ["interpretation"]
    assert report["missing_dependencies"] == [
        {
            "claim_id": "claim:1",
            "role": "interpretation",
            "resource_key": "resource:vocabulary",
            "reason": "external-resource-not-captured-in-package",
        }
    ]


def test_independent_closure_report_can_be_fully_kill_ready(tmp_path: Path) -> None:
    payload_bytes = b"closed dependency"
    payload = tmp_path / "closed.bin"
    payload.write_bytes(payload_bytes)
    digest = hashlib.sha256(payload_bytes).hexdigest()

    resource = ResourceDescriptor(
        resource_key="resource:closed",
        resource_type="vocabulary",
        materialization=MaterializationRef(
            kind="embedded",
            length=len(payload_bytes),
            integrity=IntegrityDigest("sha256", digest),
        ),
    )
    claim = PreservationClaim(
        claim_id="claim:closed",
        roles=frozenset({"interpretation"}),
        requirements=(
            ClosureRequirement(
                "resource:closed", "interpretation", subject_ref="object:record"
            ),
        ),
        root_refs=("object:record",),
    )
    package = PortableInstitutionalPackage(
        package_id="package:closed",
        format_version="0.1",
        profile="durable",
        objects=(PackageObject("object:record", "Record"),),
        resources=(resource,),
        preservation_claims=(claim,),
    )

    root = tmp_path / "bundle"
    write_reference_directory(
        package,
        root,
        payload_sources=(PayloadSource("resource:closed", payload),),
    )

    tool = _load_closure_tool(Path(__file__).resolve().parents[1])
    report = tool.closure_report(root)

    assert report["source_environment_kill_ready"] is True
    assert report["claims"][0]["ok"] is True
    assert report["missing_dependencies"] == []


def test_independent_closure_report_recognizes_external_subject(tmp_path: Path) -> None:
    payload_bytes = b"synthetic external-reference evidence"
    payload = tmp_path / "external-reference.bin"
    payload.write_bytes(payload_bytes)
    digest = hashlib.sha256(payload_bytes).hexdigest()

    resource = ResourceDescriptor(
        resource_key="resource:external-reference",
        resource_type="reference-evidence",
        materialization=MaterializationRef(
            kind="embedded",
            length=len(payload_bytes),
            integrity=IntegrityDigest("sha256", digest),
        ),
    )
    claim = PreservationClaim(
        claim_id="claim:external-reference",
        roles=frozenset({"evidentiary"}),
        requirements=(
            ClosureRequirement(
                "resource:external-reference",
                "evidentiary",
                subject_ref="external:party",
            ),
        ),
        root_refs=("object:record",),
    )
    package = PortableInstitutionalPackage(
        package_id="package:external-reference",
        format_version="0.1",
        profile="durable",
        objects=(PackageObject("object:record", "Record"),),
        external_references=(ExternalReference("external:party", "Party"),),
        resources=(resource,),
        preservation_claims=(claim,),
    )

    root = tmp_path / "bundle"
    write_reference_directory(
        package,
        root,
        payload_sources=(PayloadSource("resource:external-reference", payload),),
    )

    tool = _load_closure_tool(Path(__file__).resolve().parents[1])
    report = tool.closure_report(root)

    assert report["claims"][0]["ok"] is True
    assert report["missing_dependencies"] == []
