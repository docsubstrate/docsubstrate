"""Generate a self-contained synthetic package for independent A0 review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from docsubstrate.durable import ClosureRequirement, PreservationClaim
from docsubstrate.occurrence import OccurrenceRecord
from docsubstrate.package import (
    ExternalReference,
    PackageArtifact,
    PackageObject,
    PackageRelation,
    PackageRepresentation,
    PortableInstitutionalPackage,
    VocabularyRef,
)
from docsubstrate.physical_package import PayloadSource, write_reference_directory
from docsubstrate.resources import IntegrityDigest, MaterializationRef, ResourceDescriptor
from docsubstrate.self_sovereignty import validate_minimum_survivable_closure

SYNTHETIC_PAYLOAD = b"DocSubstrate A0 synthetic review payload.\n"
SYNTHETIC_VOCABULARY = b'{"id":"vocab:synthetic-review","version":"1"}\n'


def _embedded_resource(
    resource_key: str,
    resource_type: str,
    media_type: str,
    payload: bytes,
) -> ResourceDescriptor:
    return ResourceDescriptor(
        resource_key=resource_key,
        resource_type=resource_type,
        media_type=media_type,
        materialization=MaterializationRef(
            kind="embedded",
            media_type=media_type,
            length=len(payload),
            integrity=IntegrityDigest("sha256", hashlib.sha256(payload).hexdigest()),
        ),
    )


def generate_review_fixture(destination: str | Path) -> Path:
    """Write one synthetic, independently verifiable package to a new directory."""

    root = Path(destination)
    if root.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {root}")

    content = _embedded_resource(
        "resource:synthetic-text",
        "synthetic-review-evidence",
        "text/plain",
        SYNTHETIC_PAYLOAD,
    )
    vocabulary = _embedded_resource(
        "resource:synthetic-vocabulary",
        "vocabulary",
        "application/json",
        SYNTHETIC_VOCABULARY,
    )
    package = PortableInstitutionalPackage(
        package_id="package:synthetic-a0-review",
        format_version="0.3",
        profile="minimum-survivable-closure/0.1",
        vocabularies=(
            VocabularyRef(
                "vocab:synthetic-review",
                version="1",
                resource_key="resource:synthetic-vocabulary",
            ),
        ),
        objects=(
            PackageObject(
                "object:synthetic-record",
                "SyntheticRecord",
                "vocab:synthetic-review",
            ),
        ),
        external_references=(
            ExternalReference(
                "actor:synthetic-reviewer",
                "SyntheticActor",
                "vocab:synthetic-review",
            ),
        ),
        relations=(
            PackageRelation(
                "relation:synthetic-review",
                "object:synthetic-record",
                "synthetic-review-reference",
                "actor:synthetic-reviewer",
                "vocab:synthetic-review",
            ),
        ),
        representations=(
            PackageRepresentation(
                "expression:synthetic-record:v1",
                "object:synthetic-record",
                "SyntheticTextExpression",
                vocabulary_id="vocab:synthetic-review",
                version="1",
                resource_keys=("resource:synthetic-text",),
            ),
        ),
        artifacts=(
            PackageArtifact(
                "artifact:synthetic-text:v1",
                "expression:synthetic-record:v1",
                "resource:synthetic-text",
            ),
        ),
        occurrences=(
            OccurrenceRecord(
                occurrence_id="occurrence:synthetic-generation",
                occurrence_type="SyntheticGeneration",
                outcome="succeeded",
                basis="observed",
                input_refs=("object:synthetic-record",),
                output_refs=("artifact:synthetic-text:v1",),
                actor_ref="actor:synthetic-reviewer",
                occurred_at="2000-01-01T00:00:00Z",
                vocabulary_id="vocab:synthetic-review",
            ),
        ),
        resources=(content, vocabulary),
        preservation_claims=(
            PreservationClaim(
                claim_id="claim:synthetic-survivability",
                roles=frozenset({"evidentiary", "interpretation"}),
                requirements=(
                    ClosureRequirement(
                        "resource:synthetic-vocabulary",
                        "interpretation",
                        subject_ref="object:synthetic-record",
                    ),
                    ClosureRequirement(
                        "resource:synthetic-text",
                        "evidentiary",
                        subject_ref="artifact:synthetic-text:v1",
                    ),
                    ClosureRequirement(
                        "resource:synthetic-text",
                        "interpretation",
                        subject_ref="expression:synthetic-record:v1",
                    ),
                ),
                root_refs=(
                    "object:synthetic-record",
                    "relation:synthetic-review",
                    "expression:synthetic-record:v1",
                    "artifact:synthetic-text:v1",
                    "occurrence:synthetic-generation",
                ),
            ),
        ),
    )

    structure = package.validate_structure()
    survivability = validate_minimum_survivable_closure(package)
    if not structure.ok or not survivability.ok:
        codes = [issue.code for issue in (*structure.issues, *survivability.issues)]
        raise RuntimeError(f"synthetic review fixture violates A0 contracts: {codes}")

    payload_dir = root / "payload"
    payload_dir.mkdir(parents=True)
    content_digest = hashlib.sha256(SYNTHETIC_PAYLOAD).hexdigest()
    content_path = payload_dir / f"sha256-{content_digest}.txt"
    content_path.write_bytes(SYNTHETIC_PAYLOAD)
    vocabulary_digest = hashlib.sha256(SYNTHETIC_VOCABULARY).hexdigest()
    vocabulary_path = payload_dir / f"sha256-{vocabulary_digest}.json"
    vocabulary_path.write_bytes(SYNTHETIC_VOCABULARY)
    return write_reference_directory(
        package,
        root,
        payload_sources=(
            PayloadSource("resource:synthetic-text", content_path),
            PayloadSource("resource:synthetic-vocabulary", vocabulary_path),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination")
    args = parser.parse_args()
    manifest = generate_review_fixture(args.destination)
    print(
        json.dumps(
            {
                "data_classification": "synthetic",
                "manifest": str(manifest),
                "package_id": "package:synthetic-a0-review",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
