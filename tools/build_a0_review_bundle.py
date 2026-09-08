"""Build a deterministic, allowlist-only DocSubstrate A0 review archive."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import posixpath
import re
import stat
import subprocess
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

FILE_ROLES = {
    "LICENSE": "license",
    "NOTICE": "license",
    "README.md": "review-doc",
    "SECURITY.md": "review-doc",
    "pyproject.toml": "project-metadata",
    "docs/a0-review-guide.md": "review-doc",
    "docs/architecture.md": "review-doc",
    "docs/adr/0006-interchange-and-durability-profiles.md": "supporting-doc",
    "docs/adr/0032-semantic-self-sovereignty.md": "review-doc",
    "docs/adr/0033-protected-semantic-components.md": "review-doc",
    "docs/adr/0034-jwe-general-json-physical-profile.md": "review-doc",
    "docs/architecture/core-primitive-audit.md": "review-doc",
    "docs/architecture/interchange-profiles.md": "review-doc",
    "docs/architecture/jwe-general-json-promotion-gate.md": "review-doc",
    "docs/architecture/semantic-model.md": "supporting-doc",
    "docs/architecture/semantic-self-sovereignty-audit.md": "review-doc",
    "docs/architecture/standards-subtraction-matrix.md": "review-doc",
    "src/docsubstrate/compliance.py": "core-source",
    "src/docsubstrate/__init__.py": "core-source",
    "src/docsubstrate/component_protection.py": "core-source",
    "src/docsubstrate/durable.py": "core-source",
    "src/docsubstrate/interchange_json.py": "core-source",
    "src/docsubstrate/jwe_general_json.py": "core-source",
    "src/docsubstrate/migration.py": "core-source",
    "src/docsubstrate/occurrence.py": "core-source",
    "src/docsubstrate/package.py": "core-source",
    "src/docsubstrate/physical_package.py": "core-source",
    "src/docsubstrate/preflight.py": "core-source",
    "src/docsubstrate/resource_catalog.py": "core-source",
    "src/docsubstrate/resources.py": "core-source",
    "src/docsubstrate/self_sovereignty.py": "core-source",
    "tests/conftest.py": "test-support",
    "tests/test_a0_review_bundle.py": "synthetic-test",
    "tests/test_compliance.py": "synthetic-test",
    "tests/test_durable_closure.py": "synthetic-test",
    "tests/test_independent_closure_report.py": "synthetic-test",
    "tests/test_interchange_json.py": "synthetic-test",
    "tests/test_jwe_general_json.py": "synthetic-test",
    "tests/test_migration.py": "synthetic-test",
    "tests/test_package.py": "synthetic-test",
    "tests/test_physical_package.py": "synthetic-test",
    "tests/test_preflight.py": "synthetic-test",
    "tests/test_protected_semantic_components.py": "synthetic-test",
    "tests/test_resource_catalog.py": "synthetic-test",
    "tests/test_resources.py": "synthetic-test",
    "tests/test_review_fixture.py": "synthetic-test",
    "tests/test_self_sovereignty.py": "synthetic-test",
    "tools/build_a0_review_bundle.py": "review-tool",
    "tools/closure_report.py": "review-tool",
    "tools/generate_review_fixture.py": "review-tool",
    "tools/independent_reader.py": "review-tool",
    "tools/verify_review_bundle.py": "review-tool",
}

# The public repository already stores every allowlisted input at its archive
# path. Private-monorepo source remapping deliberately does not cross the
# fresh-history publication boundary.
SOURCE_PATHS: dict[str, str] = {}

SOURCE_SEEDS = frozenset(
    {
        "docsubstrate.compliance",
        "docsubstrate.component_protection",
        "docsubstrate.durable",
        "docsubstrate.interchange_json",
        "docsubstrate.jwe_general_json",
        "docsubstrate.migration",
        "docsubstrate.occurrence",
        "docsubstrate.package",
        "docsubstrate.physical_package",
        "docsubstrate.preflight",
        "docsubstrate.resource_catalog",
        "docsubstrate.resources",
        "docsubstrate.self_sovereignty",
    }
)
ALLOWED_THIRD_PARTY_IMPORTS = frozenset({"cryptography", "jwcrypto", "pytest"})


class BundleBuildError(ValueError):
    """The requested source tree does not satisfy the closed review scope."""


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def _module_map() -> dict[str, str]:
    result = {"docsubstrate": "src/docsubstrate/__init__.py"}
    for path in FILE_ROLES:
        if path.startswith("src/docsubstrate/") and path.endswith(".py") and not path.endswith(
            "/__init__.py"
        ):
            result[f"docsubstrate.{PurePosixPath(path).stem}"] = path
    return result


def _validate_allowlist_paths() -> None:
    unknown_mappings = set(SOURCE_PATHS) - set(FILE_ROLES)
    if unknown_mappings:
        raise BundleBuildError(
            f"source mappings lack artifact roles: {sorted(unknown_mappings)}"
        )
    for path in set(FILE_ROLES) | set(SOURCE_PATHS.values()):
        pure = PurePosixPath(path)
        if not path or path.startswith("/") or "\\" in path or pure.as_posix() != path:
            raise BundleBuildError(f"non-canonical allowlist path: {path!r}")
        if any(part in {"", ".", ".."} for part in pure.parts):
            raise BundleBuildError(f"unsafe allowlist path: {path!r}")
        blocked = {part.lower() for part in pure.parts} & FORBIDDEN_SEGMENTS
        if blocked:
            raise BundleBuildError(f"forbidden allowlist path: {path!r}")
        if pure.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise BundleBuildError(f"forbidden allowlist suffix: {path!r}")


def _imports(payload: bytes, path: str) -> tuple[set[str], set[str]]:
    tree = ast.parse(payload.decode("utf-8"), filename=path)
    internal: set[str] = set()
    external: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise BundleBuildError(f"relative import requires explicit closure review: {path}")
            names = [node.module] if node.module else []
        else:
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name in {"__import__", "import_module"}:
                    raise BundleBuildError(f"dynamic import requires explicit closure review: {path}")
            continue
        for name in names:
            if not name:
                continue
            if name == "docsubstrate" or name.startswith("docsubstrate."):
                internal.add(name)
            else:
                external.add(name.split(".", 1)[0])
    return internal, external


def _validate_python_closure(files: Mapping[str, bytes]) -> None:
    module_paths = _module_map()
    expected_modules = set(module_paths)
    pending = list(SOURCE_SEEDS | {"docsubstrate"})
    reached: set[str] = set()
    while pending:
        module = pending.pop()
        if module in reached:
            continue
        path = module_paths.get(module)
        if path is None:
            raise BundleBuildError(f"unknown internal dependency: {module}")
        internal, _ = _imports(files[path], path)
        reached.add(module)
        pending.extend(internal - reached)
    if reached != expected_modules:
        raise BundleBuildError(
            f"source closure differs from allowlist: missing={sorted(expected_modules - reached)}, "
            f"unknown={sorted(reached - expected_modules)}"
        )

    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    for path, payload in files.items():
        if not path.endswith(".py"):
            continue
        internal, external = _imports(payload, path)
        unknown_internal = internal - expected_modules
        unknown_external = external - stdlib - ALLOWED_THIRD_PARTY_IMPORTS
        if unknown_internal:
            raise BundleBuildError(f"unknown internal import in {path}: {sorted(unknown_internal)}")
        if unknown_external:
            raise BundleBuildError(f"unknown external import in {path}: {sorted(unknown_external)}")


def _validate_document_links(files: Mapping[str, bytes]) -> None:
    link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
    backtick_path_pattern = re.compile(r"`([^`\n]+\.md(?:#[^`\n]+)?)`")
    for path, payload in files.items():
        if not path.endswith(".md"):
            continue
        text = payload.decode("utf-8")
        targets = link_pattern.findall(text) + backtick_path_pattern.findall(text)
        for raw_target in targets:
            target = raw_target.strip().strip("<>")
            if not target or target.startswith("#") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            target = target.split("#", 1)[0].split("?", 1)[0]
            resolved = posixpath.normpath(str(PurePosixPath(path).parent / target))
            if resolved.startswith("../") or resolved not in files:
                raise BundleBuildError(f"missing allowlisted documentation dependency: {path} -> {target}")


def _read_files(source_root: Path) -> dict[str, bytes]:
    _validate_allowlist_paths()
    files: dict[str, bytes] = {}
    for path in sorted(FILE_ROLES):
        source_path = SOURCE_PATHS.get(path, path)
        candidate = source_root / source_path
        if not candidate.exists() and source_path != path:
            # A verified extraction contains artifact paths, not repository-only
            # input paths, so it remains byte-rebuildable without the repository.
            candidate = source_root / path
        if candidate.is_symlink() or not candidate.is_file():
            raise BundleBuildError(
                f"missing or non-regular allowlisted file: {source_path}"
            )
        files[path] = candidate.read_bytes()
    _validate_python_closure(files)
    _validate_document_links(files)
    return files


def _manifest(source_commit: str, files: Mapping[str, bytes]) -> bytes:
    if len(source_commit) != 40 or any(char not in "0123456789abcdef" for char in source_commit):
        raise BundleBuildError("source commit must be a full lowercase Git SHA")
    value = {
        "artifact": {
            "classification": CLASSIFICATION,
            "copyright": COPYRIGHT_NOTICE,
            "format": FORMAT_ID,
            "format_version": FORMAT_VERSION,
            "intended_use": "external-technical-source-review",
            "license": LICENSE_ID,
            "not_a": ["frozen-api", "frozen-wire-profile", "release", "sdist", "wheel"],
        },
        "files": [
            {
                "path": path,
                "role": FILE_ROLES[path],
                "sha256": hashlib.sha256(files[path]).hexdigest(),
                "size": len(files[path]),
                "source_path": SOURCE_PATHS.get(path, path),
            }
            for path in sorted(files)
        ],
        "integrity": {
            "algorithm": "sha256",
            "manifest_self_digest": "excluded-by-design",
        },
        "source": {"commit": source_commit},
    }
    return _canonical_json(value)


def _archive_bytes(members: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(members):
            info = zipfile.ZipInfo(path, FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, members[path])
    return buffer.getvalue()


def build_review_bundle_from_directory(
    source_root: str | Path,
    source_commit: str,
    destination: str | Path,
) -> Path:
    root = Path(source_root).resolve()
    target = Path(destination).resolve()
    if target == root or root in target.parents:
        raise BundleBuildError("destination must be outside the source tree")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    if not target.parent.is_dir():
        raise BundleBuildError(f"destination parent does not exist: {target.parent}")
    files = _read_files(root)
    members = dict(files)
    members[MANIFEST_NAME] = _manifest(source_commit, files)
    payload = _archive_bytes(members)
    with target.open("xb") as stream:
        stream.write(payload)
    return target


def _git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", os.fspath(root), *args],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise BundleBuildError(
            "Git executable is unavailable; install Git or use --source-commit "
            "from a verified extraction"
        ) from exc
    if result.returncode:
        raise BundleBuildError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def build_review_bundle(source_root: str | Path, destination: str | Path) -> tuple[Path, str]:
    root = Path(source_root).resolve()
    if not (root / ".git").exists():
        raise BundleBuildError(
            "Git metadata is unavailable; pass --source-commit with the manifest commit"
        )
    git_root = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if git_root != root:
        raise BundleBuildError(f"source root is not the Git root: {root}")
    target = Path(destination).resolve()
    if target == root or root in target.parents:
        raise BundleBuildError("destination must be outside the source repository")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise BundleBuildError("source worktree must be clean")
    commit = _git(root, "rev-parse", "HEAD").decode().strip()
    files = _read_files(root)
    for path, payload in files.items():
        source_path = SOURCE_PATHS.get(path, path)
        if _git(root, "show", f"{commit}:{source_path}") != payload:
            raise BundleBuildError(
                f"allowlisted file does not match source commit: {source_path}"
            )
    return build_review_bundle_from_directory(root, commit, target), commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-commit",
        help=(
            "exact 40-hex manifest commit for a verified Git-less extraction; "
            "omit to require a clean Git HEAD"
        ),
    )
    parser.add_argument("destination", help="new .zip path outside the repository")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.source_commit is None:
            destination, commit = build_review_bundle(root, args.destination)
        else:
            commit = args.source_commit
            destination = build_review_bundle_from_directory(root, commit, args.destination)
    except (BundleBuildError, FileExistsError, OSError) as exc:
        print(f"A0 review bundle build failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "archive": str(destination),
                "classification": CLASSIFICATION,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "source_commit": commit,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
