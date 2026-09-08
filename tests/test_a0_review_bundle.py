from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


def _load(repo_root: Path, name: str):
    path = repo_root / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_allowlist(builder, source: Path, destination: Path, *, omit=()) -> None:
    omitted = set(omit)
    for relative in builder.FILE_ROLES:
        if relative in omitted:
            continue
        source_relative = builder.SOURCE_PATHS.get(relative, relative)
        source_path = source / source_relative
        if not source_path.exists() and source_relative != relative:
            source_relative = relative
            source_path = source / relative
        target = destination / source_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)


def test_bundle_is_deterministic_and_verifies_after_clean_extraction(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    verifier = _load(repo_root, "verify_review_bundle")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    commit = "1" * 40

    builder.build_review_bundle_from_directory(repo_root, commit, first)
    builder.build_review_bundle_from_directory(repo_root, commit, second)

    assert first.read_bytes() == second.read_bytes()
    assert verifier.verify_archive(first)["source_commit"] == commit
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(first) as archive:
        archive.extractall(extracted)
    result = verifier.verify_directory(extracted)
    assert result["ok"] is True
    assert result["classification"] == "A0-PUBLIC-CANDIDATE"
    manifest = json.loads((extracted / builder.MANIFEST_NAME).read_text())
    assert manifest["artifact"]["license"] == "Apache-2.0"
    assert manifest["artifact"]["copyright"] == "Copyright 2026 DocSubstrate contributors"
    assert "Apache License" in (extracted / "LICENSE").read_text()
    assert "Copyright 2026 DocSubstrate contributors" in (extracted / "NOTICE").read_text()
    assert "docsubstrate/docsubstrate" in (extracted / "pyproject.toml").read_text()
    initializer = (extracted / "src/docsubstrate/__init__.py").read_text()
    assert "__all__" in initializer
    assert "from docsubstrate" not in initializer
    rebuilt = tmp_path / "rebuilt-from-extraction.zip"
    completed = subprocess.run(
        [
            sys.executable,
            extracted / "tools/build_a0_review_bundle.py",
            "--source-commit",
            commit,
            rebuilt,
        ],
        cwd=extracted,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert rebuilt.read_bytes() == first.read_bytes()
    assert not {".git", ".github", "integrations", "benchmarks"} & {
        path.parts[0] for path in map(Path, builder.FILE_ROLES)
    }


def test_extraction_cli_rejects_missing_or_malformed_source_commit(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    archive = tmp_path / "bundle.zip"
    builder.build_review_bundle_from_directory(repo_root, "1" * 40, archive)
    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(extracted)
    cli = extracted / "tools/build_a0_review_bundle.py"

    missing = subprocess.run(
        [sys.executable, cli, tmp_path / "missing.zip"],
        cwd=extracted,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 1
    assert (
        "Git metadata is unavailable; pass --source-commit with the manifest commit"
        in missing.stderr
    )
    assert not (tmp_path / "missing.zip").exists()

    no_git = subprocess.run(
        [sys.executable, cli, tmp_path / "no-git.zip"],
        cwd=extracted,
        env={**os.environ, "PATH": os.fspath(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert no_git.returncode == 1
    assert (
        "Git metadata is unavailable; pass --source-commit with the manifest commit"
        in no_git.stderr
    )
    assert not (tmp_path / "no-git.zip").exists()

    malformed = subprocess.run(
        [
            sys.executable,
            cli,
            "--source-commit",
            "not-a-commit",
            tmp_path / "malformed.zip",
        ],
        cwd=extracted,
        capture_output=True,
        text=True,
        check=False,
    )
    assert malformed.returncode == 1
    assert "full lowercase Git SHA" in malformed.stderr
    assert not (tmp_path / "malformed.zip").exists()


def test_builder_fails_on_overwrite_or_missing_dependency(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    existing = tmp_path / "existing.zip"
    existing.write_bytes(b"occupied")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        builder.build_review_bundle_from_directory(repo_root, "2" * 40, existing)

    incomplete = tmp_path / "incomplete"
    _copy_allowlist(builder, repo_root, incomplete, omit={"src/docsubstrate/preflight.py"})
    with pytest.raises(builder.BundleBuildError, match="missing or non-regular"):
        builder.build_review_bundle_from_directory(incomplete, "2" * 40, tmp_path / "missing.zip")


def test_builder_fails_on_forbidden_allowlist_path(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    monkeypatch.setitem(builder.FILE_ROLES, "integrations/client/private.pem", "core-source")

    with pytest.raises(builder.BundleBuildError, match="forbidden allowlist path"):
        builder.build_review_bundle_from_directory(repo_root, "2" * 40, tmp_path / "blocked.zip")


def test_builder_fails_on_unknown_internal_dependency(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    source = tmp_path / "source"
    _copy_allowlist(builder, repo_root, source)
    package = source / "src/docsubstrate/package.py"
    package.write_text(
        package.read_text(encoding="utf-8") + "\nimport docsubstrate.unknown_private_module\n",
        encoding="utf-8",
    )

    with pytest.raises(builder.BundleBuildError, match="unknown internal dependency"):
        builder.build_review_bundle_from_directory(source, "3" * 40, tmp_path / "unknown.zip")


def test_builder_fails_on_backtick_document_dependency(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    source = tmp_path / "source"
    _copy_allowlist(builder, repo_root, source)
    architecture = source / "docs/architecture.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8") + "\nSee `missing-decision.md`.\n",
        encoding="utf-8",
    )

    with pytest.raises(builder.BundleBuildError, match="documentation dependency"):
        builder.build_review_bundle_from_directory(source, "3" * 40, tmp_path / "dangling.zip")


def test_builder_does_not_resolve_broken_document_link_from_bundle_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    source = tmp_path / "source"
    _copy_allowlist(builder, repo_root, source)
    guide = source / "docs/a0-review-guide.md"
    guide.write_text(
        guide.read_text(encoding="utf-8") + "\n[Broken relative link](README.md)\n",
        encoding="utf-8",
    )

    with pytest.raises(builder.BundleBuildError, match="documentation dependency"):
        builder.build_review_bundle_from_directory(
            source, "3" * 40, tmp_path / "wrong-root.zip"
        )


def test_verifier_fails_on_tamper_extra_member_and_forbidden_surface(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    builder = _load(repo_root, "build_a0_review_bundle")
    verifier = _load(repo_root, "verify_review_bundle")
    archive_path = tmp_path / "bundle.zip"
    builder.build_review_bundle_from_directory(repo_root, "4" * 40, archive_path)

    tampered = tmp_path / "tampered"
    tampered.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(tampered)
    (tampered / "README.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(verifier.BundleVerificationError, match="mismatch"):
        verifier.verify_directory(tampered)

    extra_directory = tmp_path / "extra-directory"
    extra_directory.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extra_directory)
    (extra_directory / "notes.txt").write_text("not allowlisted\n", encoding="utf-8")
    with pytest.raises(verifier.BundleVerificationError, match="member set differs"):
        verifier.verify_directory(extra_directory)

    extra_archive = tmp_path / "extra-archive.zip"
    with zipfile.ZipFile(archive_path) as archive:
        members = {info.filename: archive.read(info) for info in archive.infolist()}
    members["notes.txt"] = b"not allowlisted\n"
    extra_archive.write_bytes(builder._archive_bytes(members))
    with pytest.raises(verifier.BundleVerificationError, match="member set differs"):
        verifier.verify_archive(extra_archive)

    forbidden = tmp_path / "forbidden"
    forbidden.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(forbidden)
    extra_path = forbidden / "integrations/client/restricted.pdf"
    extra_path.parent.mkdir(parents=True)
    extra_path.write_bytes(b"synthetic forbidden member")
    with pytest.raises(verifier.BundleVerificationError, match="forbidden"):
        verifier.verify_directory(forbidden)
