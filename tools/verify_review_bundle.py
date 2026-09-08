"""Verify a DocSubstrate A0 source-review bundle using only the stdlib."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import sys
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "A0-REVIEW-MANIFEST.json"
FORMAT_ID = "docsubstrate.a0-source-review-bundle"
FORMAT_VERSION = "2"
CLASSIFICATION = "A0-PUBLIC-CANDIDATE"
LICENSE_ID = "Apache-2.0"
COPYRIGHT_NOTICE = "Copyright 2026 DocSubstrate contributors"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FORBIDDEN_SEGMENTS = frozenset(
    {
        ".git",
        ".github",
        "benchmarks",
        "client",
        "clients",
        "customer",
        "customers",
        "deploy",
        "deployment",
        "integrations",
        "private",
        "production",
        "restricted",
        "secrets",
    }
)
FORBIDDEN_SUFFIXES = frozenset(
    {
        ".7z",
        ".db",
        ".doc",
        ".docx",
        ".env",
        ".gz",
        ".key",
        ".p12",
        ".pdf",
        ".pem",
        ".pfx",
        ".ppt",
        ".pptx",
        ".sqlite",
        ".sqlite3",
        ".tar",
        ".xls",
        ".xlsx",
        ".zip",
    }
)
ALLOWED_ROLES = frozenset(
    {
        "core-source",
        "dependency-source",
        "license",
        "project-metadata",
        "review-doc",
        "review-tool",
        "supporting-doc",
        "synthetic-test",
        "test-support",
    }
)


class BundleVerificationError(ValueError):
    """The review bundle violates its closed manifest or integrity contract."""


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def _validate_member_path(path: str) -> None:
    pure = PurePosixPath(path)
    if not path or path.startswith("/") or "\\" in path or pure.as_posix() != path:
        raise BundleVerificationError(f"non-canonical member path: {path!r}")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise BundleVerificationError(f"unsafe member path: {path!r}")
    lowered = {part.lower() for part in pure.parts}
    blocked = lowered & FORBIDDEN_SEGMENTS
    if blocked:
        raise BundleVerificationError(f"forbidden path segment in {path!r}: {sorted(blocked)}")
    if pure.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise BundleVerificationError(f"forbidden member suffix: {path!r}")


def _load_manifest(data: bytes) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleVerificationError("manifest is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict) or _canonical_json(value) != data:
        raise BundleVerificationError("manifest must be canonical JSON")
    if set(value) != {"artifact", "files", "integrity", "source"}:
        raise BundleVerificationError("manifest has unknown or missing top-level members")

    artifact = value.get("artifact")
    expected_artifact = {
        "classification": CLASSIFICATION,
        "copyright": COPYRIGHT_NOTICE,
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "intended_use": "external-technical-source-review",
        "license": LICENSE_ID,
        "not_a": ["frozen-api", "frozen-wire-profile", "release", "sdist", "wheel"],
    }
    if artifact != expected_artifact:
        raise BundleVerificationError("unexpected artifact scope or classification")
    if value.get("integrity") != {
        "algorithm": "sha256",
        "manifest_self_digest": "excluded-by-design",
    }:
        raise BundleVerificationError("unexpected integrity profile")
    source = value.get("source")
    if not isinstance(source, dict) or set(source) != {"commit"}:
        raise BundleVerificationError("invalid source descriptor")
    commit = source.get("commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise BundleVerificationError("source commit must be a full lowercase Git SHA")

    records = value.get("files")
    if not isinstance(records, list) or not records:
        raise BundleVerificationError("manifest files must be a non-empty list")
    by_path: dict[str, dict[str, object]] = {}
    ordered_paths: list[str] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "path",
            "role",
            "sha256",
            "size",
            "source_path",
        }:
            raise BundleVerificationError("invalid file record")
        path = record.get("path")
        role = record.get("role")
        digest = record.get("sha256")
        size = record.get("size")
        source_path = record.get("source_path")
        if not isinstance(path, str):
            raise BundleVerificationError("file path must be a string")
        _validate_member_path(path)
        if not isinstance(source_path, str):
            raise BundleVerificationError(f"source path must be a string: {path}")
        _validate_member_path(source_path)
        if path == MANIFEST_NAME or path in by_path:
            raise BundleVerificationError(f"duplicate or reserved manifest path: {path}")
        if role not in ALLOWED_ROLES:
            raise BundleVerificationError(f"unknown role for {path}: {role!r}")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise BundleVerificationError(f"invalid SHA-256 for {path}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise BundleVerificationError(f"invalid size for {path}")
        by_path[path] = record
        ordered_paths.append(path)
    if ordered_paths != sorted(ordered_paths):
        raise BundleVerificationError("manifest files are not sorted by path")
    return value, by_path


def _verify_members(members: Mapping[str, bytes]) -> dict[str, object]:
    if MANIFEST_NAME not in members:
        raise BundleVerificationError("missing manifest")
    for path in members:
        _validate_member_path(path)
    manifest, records = _load_manifest(members[MANIFEST_NAME])
    expected = set(records) | {MANIFEST_NAME}
    actual = set(members)
    if actual != expected:
        raise BundleVerificationError(
            f"member set differs from manifest: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    for path, record in records.items():
        payload = members[path]
        if len(payload) != record["size"]:
            raise BundleVerificationError(f"size mismatch: {path}")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise BundleVerificationError(f"SHA-256 mismatch: {path}")
    return {
        "classification": CLASSIFICATION,
        "file_count": len(records),
        "format": FORMAT_ID,
        "ok": True,
        "source_commit": manifest["source"]["commit"],
    }


def _canonical_archive_bytes(members: Mapping[str, bytes]) -> bytes:
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(members):
            info = zipfile.ZipInfo(path, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, members[path])
    return buffer.getvalue()


def verify_archive(path: str | Path) -> dict[str, object]:
    archive_path = Path(path)
    raw = archive_path.read_bytes()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            if archive.comment:
                raise BundleVerificationError("archive comments are forbidden")
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise BundleVerificationError("duplicate archive member")
            members: dict[str, bytes] = {}
            for info in infos:
                _validate_member_path(info.filename)
                mode = info.external_attr >> 16
                if info.is_dir() or not stat.S_ISREG(mode):
                    raise BundleVerificationError(f"non-regular archive member: {info.filename}")
                if info.date_time != FIXED_TIMESTAMP or info.compress_type != zipfile.ZIP_STORED:
                    raise BundleVerificationError(f"non-canonical archive metadata: {info.filename}")
                if info.flag_bits & 1:
                    raise BundleVerificationError(f"encrypted archive member: {info.filename}")
                members[info.filename] = archive.read(info)
    except zipfile.BadZipFile as exc:
        raise BundleVerificationError("invalid ZIP archive") from exc
    result = _verify_members(members)
    if _canonical_archive_bytes(members) != raw:
        raise BundleVerificationError("archive bytes are not canonical")
    result["container"] = "zip"
    return result


def verify_directory(path: str | Path) -> dict[str, object]:
    root = Path(path)
    if not root.is_dir() or root.is_symlink():
        raise BundleVerificationError("verification target must be a regular directory")
    members: dict[str, bytes] = {}
    directories: set[str] = set()
    for candidate in root.rglob("*"):
        relative = candidate.relative_to(root).as_posix()
        _validate_member_path(relative)
        if candidate.is_symlink():
            raise BundleVerificationError(f"symlink is forbidden: {candidate}")
        if candidate.is_file():
            members[relative] = candidate.read_bytes()
        elif candidate.is_dir():
            directories.add(relative)
        else:
            raise BundleVerificationError(f"non-regular filesystem member: {candidate}")
    result = _verify_members(members)
    expected_directories = {
        parent.as_posix()
        for member in members
        for parent in PurePosixPath(member).parents
        if parent.as_posix() != "."
    }
    if directories != expected_directories:
        raise BundleVerificationError(
            f"directory set differs from manifest-derived paths: "
            f"missing={sorted(expected_directories - directories)}, "
            f"extra={sorted(directories - expected_directories)}"
        )
    result["container"] = "directory"
    return result


def verify(path: str | Path) -> dict[str, object]:
    target = Path(path)
    if target.is_dir():
        return verify_directory(target)
    return verify_archive(target)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} BUNDLE.zip|EXTRACTED_DIRECTORY", file=sys.stderr)
        return 2
    try:
        result = verify(sys.argv[1])
    except (BundleVerificationError, OSError) as exc:
        print(f"review bundle verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
