from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


def _load_generator(repo_root: Path):
    path = repo_root / "tools" / "generate_review_fixture.py"
    spec = importlib.util.spec_from_file_location("generate_review_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_independent(tool: Path, package: Path) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-I", str(tool), str(package)],
        cwd=package.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_generated_review_fixture_passes_both_independent_readers(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    package = tmp_path / "synthetic-review-package"
    generator = _load_generator(repo_root)

    manifest = generator.generate_review_fixture(package)
    manifest_text = manifest.read_text(encoding="utf-8")
    assert str(tmp_path) not in manifest_text
    assert "/home/" not in manifest_text

    reader = _run_independent(repo_root / "tools" / "independent_reader.py", package)
    assert reader["summary"]["package_id"] == "package:synthetic-a0-review"
    assert reader["summary"]["object_count"] == 1
    assert reader["summary"]["relation_count"] == 1
    assert reader["summary"]["occurrence_count"] == 1
    assert reader["physical_verification"]["ok"] is True

    closure = _run_independent(repo_root / "tools" / "closure_report.py", package)
    assert closure["package_id"] == "package:synthetic-a0-review"
    assert closure["source_environment_kill_ready"] is True
    assert closure["missing_dependencies"] == []


def test_review_fixture_generator_refuses_to_overwrite(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    generator = _load_generator(repo_root)
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        generator.generate_review_fixture(destination)
