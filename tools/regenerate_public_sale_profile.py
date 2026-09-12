#!/usr/bin/env python3
"""Generate the bounded sale profile from public inputs and a fixed spec.

The shipped profile is an output, never an input. The template is a
reviewable public skeleton; selector tables are regenerated from the pinned
CSS outputs and filtered by the independent transformation specification.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "public-alpha" / "sale-profile-transform.json"


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _assignments(source: str) -> dict[str, ast.Assign]:
    return {
        node.targets[0].id: node
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }


def _emitted_blocks(source: str) -> dict[str, str]:
    lines = source.splitlines()
    return {
        name: "\n".join(lines[node.lineno - 1 : node.end_lineno])
        for name, node in _assignments(source).items()
        if isinstance(node.value, ast.Tuple)
    }


def _filter_hand_compiled(name: str, node: ast.Assign, fragments: tuple[str, ...]) -> str:
    kept = []
    for row in node.value.elts:
        selector = ast.literal_eval(row.elts[0])
        if any(fragment in selector for fragment in fragments):
            continue
        rendered = ast.unparse(row)
        kept.append(textwrap.indent(rendered, "    ") + ",")
    return f"{name} = (\n" + "\n".join(kept) + "\n)"


def _review_map(spec: dict, profile_source: str) -> dict:
    constants = []
    for node in ast.parse(profile_source).body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.isupper()
        ):
            constants.append(
                {
                    "name": node.targets[0].id,
                    "basis": "public-synthetic-contract",
                    "contract": "tests/test_public_sale_runtime_contract.py",
                }
            )
    return {
        "schema": "docsubstrate.public-sale-profile-review-map/v1",
        "generated_from": {
            "spec": spec["input_contract"],
            "transformation": "public-alpha/sale-profile-transform.json",
            "stylesheet_source_map": spec["source_map"],
        },
        "profile_constants": constants,
        "theme_mappings": [
            {"name": "layout_table_style", "basis": "public Odoo 19 template contract"},
            {"name": "table_skins", "basis": "pinned public stylesheet inputs"},
            {"name": "company_overlay", "basis": "public Odoo 19 template contract"},
            {"name": "informations_box", "basis": "pinned public stylesheet inputs"},
            {"name": "layout_shapes", "basis": "public Odoo 19 template contract"},
        ],
        "runtime_imported": False,
        "claims": {"legal_clearance": None, "publication_readiness": None},
    }


def regenerate() -> None:
    spec = _spec()
    template = ROOT / spec["template"]
    profile = ROOT / spec["output"]
    review_map = ROOT / spec["review_map"]
    fragments = tuple(spec["selector_exclude_fragments"])
    emitted = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "derive_layout_rules.py"), "--emit"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    replacements = _emitted_blocks(emitted)
    source = template.read_text(encoding="utf-8")
    nodes = _assignments(source)
    lines = source.splitlines()
    edits: list[tuple[int, int, str]] = []
    for name, replacement in replacements.items():
        node = nodes.get(name)
        if node is not None:
            edits.append((node.lineno - 1, node.end_lineno, replacement))
    for name in spec["hand_compiled_assignments"]:
        node = nodes[name]
        edits.append((node.lineno - 1, node.end_lineno, _filter_hand_compiled(name, node, fragments)))
    for start, end, replacement in sorted(edits, reverse=True):
        lines[start:end] = replacement.splitlines()
    output = "\n".join(lines) + "\n"
    profile.write_text(output, encoding="utf-8")
    review_map.write_text(
        json.dumps(_review_map(spec, output), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    regenerate()
