"""Executable closure for the bounded public Odoo 19 stylesheet inputs."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "public-alpha" / "odoo19-stylesheet-inputs.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_lgpl_evidence(contract: dict) -> None:
    """Require inputs intentionally retained in the separate adapter repo.

    The source checkout used to be one tree. The public split keeps the raw
    Odoo stylesheet evidence at its LGPL boundary in
    ``docsubstrate/odoo-adapter`` while Core retains the compiled profile and
    its digest contract. A combined engineering checkout still executes these
    byte-for-byte checks; a standalone public Core checkout reports the
    external evidence boundary explicitly instead of failing on dangling
    paths.
    """
    required = [
        ROOT / contract["source_map"]["path"],
        *(ROOT / row["path"] for row in contract["outputs"]),
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
    if missing:
        pytest.skip(
            "raw Odoo stylesheet evidence is shipped in the matching "
            f"docsubstrate/odoo-adapter checkout: {', '.join(missing)}"
        )


def test_public_stylesheet_contract_pins_one_exact_upstream_revision():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    revision = contract["upstream"]["revision"]
    assert len(revision) == 40
    assert contract["upstream"]["repository"] == "https://github.com/odoo/odoo"
    assert contract["upstream"]["revision_url"].endswith(revision)
    assert contract["upstream"]["license_file_url"].endswith(f"/{revision}/LICENSE")
    assert contract["claims"] == {
        "legal_clearance": None,
        "publication_readiness": None,
    }


def test_public_source_map_is_current_and_complete_for_the_compiled_assets():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    _require_lgpl_evidence(contract)
    source_map_path = ROOT / contract["source_map"]["path"]
    assert _sha256(source_map_path) == contract["source_map"]["sha256"]
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    rows = source_map["public_sources"]
    assert source_map["public_source_count"] == len(rows) == 64
    assert sum(row["role"] == "static-contributor" for row in rows) == 61
    assert sum(row["role"] == "dynamic-generator" for row in rows) == 3
    revision = contract["upstream"]["revision"]
    assert all(f"/{revision}/" in row["upstream_url"] for row in rows)
    assert {row["upstream_path"] for row in rows if row["role"] == "dynamic-generator"} == {
        item["path"] for item in contract["dynamic_asset_sources"]
    }
    for row in rows:
        basis = row["license_basis"]
        assert basis["spdx"] in {"LGPL-3.0-only", "MIT"}
        assert basis["basis_kind"] in {
            "pinned-repository-license", "vendored-library-license"
        }
        assert basis["basis_url"].startswith("https://")
        assert len(basis["basis_sha256"]) == 64
    assert source_map["license_provenance"] == {
        "basis_count": 64,
        "basis_revision": contract["upstream"]["revision"],
        "classification_only": True,
        "legal_clearance": None,
    }


def test_generated_stylesheets_match_both_contracts_byte_for_byte():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    _require_lgpl_evidence(contract)
    source_map = json.loads((ROOT / contract["source_map"]["path"]).read_text(encoding="utf-8"))
    extracted = {row["path"]: row for row in source_map["outputs"]}
    for row in contract["outputs"]:
        path = ROOT / row["path"]
        assert path.stat().st_size == row["bytes"] == extracted[path.name]["bytes"]
        assert _sha256(path) == row["sha256"] == extracted[path.name]["sha256"]


def test_sale_profile_excludes_unrelated_product_label_selectors():
    profile = (ROOT / "src" / "docsubstrate" / "odoo_report_profile.py").read_text(encoding="utf-8")
    selectors = {
        node.value
        for node in ast.walk(ast.parse(profile))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    joined = "\n".join(selectors)
    assert "label_sheet" not in joined
    assert "o_report_reception" not in joined
    assert "o_report_stock_rule" not in joined


def test_sale_profile_regenerator_is_input_driven_and_not_seeded_by_output():
    script = ROOT / "tools" / "regenerate_public_sale_profile.py"
    spec = importlib.util.spec_from_file_location("sale_profile_regenerator", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = script.read_text(encoding="utf-8")
    spec = json.loads((ROOT / "public-alpha/sale-profile-transform.json").read_text())
    assert spec["template"] == "public-alpha/sale-profile-template.py"
    assert "SPEC_PATH" in source
    assert "PROFILE.read_text" not in source
    assert "src/docsubstrate/odoo_report_profile.py" not in source


def test_regenerator_bootstraps_from_archive_without_output_profile(tmp_path):
    """The generator must not import the file it is about to replace."""
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    _require_lgpl_evidence(contract)
    archive = tmp_path / "archive"
    shutil.copytree(ROOT / "src", archive / "src")
    shutil.copytree(ROOT / "tools", archive / "tools")
    shutil.copytree(ROOT / "public-alpha", archive / "public-alpha")
    shutil.copytree(ROOT / "tests" / "data", archive / "tests" / "data")
    expected_profile = (ROOT / "src/docsubstrate/odoo_report_profile.py").read_bytes()
    expected_review = (ROOT / "public-alpha/profile-review-map.json").read_bytes()
    (archive / "src/docsubstrate/odoo_report_profile.py").unlink()
    subprocess.run(
        [sys.executable, "tools/regenerate_public_sale_profile.py"],
        cwd=archive,
        check=True,
        env={**os.environ, "PYTHONPATH": str(archive / "src")},
    )
    assert (archive / "src/docsubstrate/odoo_report_profile.py").read_bytes() == expected_profile
    assert (archive / "public-alpha/profile-review-map.json").read_bytes() == expected_review
