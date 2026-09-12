#!/usr/bin/env python3
"""Run the public-alpha smoke in cached, disposable Odoo 19 containers."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_PREFIX = "DOCSUBSTRATE_PUBLIC_ALPHA_RESULT="


class HarnessError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _tree_sha256(root: Path) -> str:
    """Hash the exact relative paths and bytes staged as the addon input."""
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, **kwargs)


def _image_id(image: str) -> str:
    try:
        return subprocess.check_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", image],
            text=True,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise HarnessError(f"required cached image is absent; refusing to pull: {image}") from exc


def _wait_postgres(container: str) -> None:
    for _ in range(60):
        result = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", "odoo", "-d", "postgres"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(0.25)
    raise HarnessError("disposable PostgreSQL did not become ready")


def _validate_result(result: dict) -> None:
    """Fail closed unless the two in-process renderer observations agree."""
    if result.get("status") != "PASS":
        raise HarnessError(f"Odoo harness did not pass: {result!r}")
    if result.get("schema") != "docsubstrate.public-alpha-odoo19-harness-native-only/v1":
        raise HarnessError("Odoo harness emitted an unsupported result schema")
    case = result.get("case")
    expected = {
        "name": "record-native",
        "requested": "reportlab",
        "actual": "reportlab-native",
        "fallback": False,
        "render_host": "record-native",
        "qweb_evaluated": False,
        "producer_calls": {"reportlab_render_bytes": 1, "wkhtmltopdf": 0},
        "artifact_persisted": True,
    }
    if not isinstance(case, dict):
        raise HarnessError("native-only harness did not emit its path case")
    actual = {key: case.get(key) for key in expected}
    if actual != expected:
        raise HarnessError(f"record-native renderer contract mismatch: {actual!r}")


def run_harness(
    *,
    core_wheel: Path,
    reportlab_wheel: Path,
    addon: Path,
    payload: Path,
    output: Path,
    odoo_image: str,
    postgres_image: str,
) -> dict:
    if output.exists():
        raise HarnessError(f"refusing to overwrite output: {output}")
    for path in (core_wheel, reportlab_wheel, addon, payload):
        if not path.exists():
            raise HarnessError(f"required local input is absent: {path}")
    odoo_id = _image_id(odoo_image)
    postgres_id = _image_id(postgres_image)
    output.mkdir(parents=True)
    scratch = output / "scratch"
    addons = scratch / "addons"
    staged_addon = addons / "docsubstrate_report"
    shutil.copytree(
        addon,
        staged_addon,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    addon_sha256 = _tree_sha256(staged_addon)
    lib = staged_addon / "lib"
    lib.mkdir()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    _run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--offline",
            "--no-deps",
            "--target",
            str(lib),
            str(core_wheel),
            str(reportlab_wheel),
        ],
        env=env,
    )
    token = secrets.token_hex(5)
    network = f"ds-alpha-{token}"
    database = f"ds-alpha-pg-{token}"
    common = [
        "--network",
        network,
        "-e",
        "HOST=postgres",
        "-e",
        "USER=odoo",
        "-e",
        "PASSWORD=odoo",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "PYTHONPATH=/mnt/addons/docsubstrate_report/lib",
        "-v",
        f"{addons.resolve()}:/mnt/addons:ro",
        "-v",
        f"{payload.resolve()}:/mnt/sale_order_smoke.py:ro",
    ]
    try:
        _run(["docker", "network", "create", "--internal", network], capture_output=True)
        _run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                database,
                "--network",
                network,
                "--network-alias",
                "postgres",
                "-e",
                "POSTGRES_DB=postgres",
                "-e",
                "POSTGRES_USER=odoo",
                "-e",
                "POSTGRES_PASSWORD=odoo",
                postgres_image,
            ],
            capture_output=True,
        )
        _wait_postgres(database)
        container = [
            "docker",
            "run",
            "--rm",
            *common,
            odoo_image,
            "odoo",
        ]
        options = [
            "--db_host=postgres",
            "--db_user=odoo",
            "--db_password=odoo",
            "--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/addons",
            "--database=public_alpha",
            "--without-demo",
        ]
        install = _run(
            [
                *container,
                "server",
                *options,
                "--init=docsubstrate_report",
                "--stop-after-init",
                "--log-level=warn",
            ],
            capture_output=True,
        )
        shell_command = " ".join(
            [
                "exec odoo shell",
                *options,
                "--no-http",
                "--log-level=warn",
                "< /mnt/sale_order_smoke.py",
            ]
        )
        shell = _run(
            [
                "docker",
                "run",
                "--rm",
                *common,
                odoo_image,
                "/bin/sh",
                "-c",
                shell_command,
            ],
            capture_output=True,
        )
        result_lines = [
            line.removeprefix(RESULT_PREFIX)
            for line in (shell.stdout + "\n" + shell.stderr).splitlines()
            if line.startswith(RESULT_PREFIX)
        ]
        if len(result_lines) != 1:
            output.joinpath("FAILED.log").write_text(
                ("STDOUT\n" + shell.stdout + "\nSTDERR\n" + shell.stderr)[-20000:]
            )
            raise HarnessError("Odoo shell did not emit exactly one harness result")
        result = json.loads(result_lines[0])
        _validate_result(result)
        case = result.get("case")
        encoded_pdf = case.pop("pdf_base64", None) if isinstance(case, dict) else None
        if not isinstance(encoded_pdf, str):
            raise HarnessError("Odoo harness did not return the final PDF artifact")
        try:
            final_pdf = base64.b64decode(encoded_pdf, validate=True)
        except ValueError as exc:
            raise HarnessError("Odoo harness returned an invalid PDF encoding") from exc
        if not final_pdf.startswith(b"%PDF-1.4"):
            raise HarnessError("Odoo harness final artifact is not PDF 1.4")
        final_sha256 = _sha256_bytes(final_pdf)
        if final_sha256 != case.get("pdf_sha256"):
            raise HarnessError("Odoo harness final artifact digest is inconsistent")
        output.joinpath("final.pdf").write_bytes(final_pdf)
        case["pdf_file"] = "final.pdf"
        result["inputs"] = {
            "core_wheel_sha256": _sha256(core_wheel),
            "reportlab_wheel_sha256": _sha256(reportlab_wheel),
            "addon_tree": "docsubstrate_report",
            "addon_tree_sha256": addon_sha256,
            "payload_sha256": _sha256(payload),
            "odoo_image_id": odoo_id,
            "postgres_image_id": postgres_id,
        }
        result["network"] = "isolated-local-docker-only"
        result["install_log_sha256"] = hashlib.sha256(
            (install.stdout + install.stderr).encode()
        ).hexdigest()
        output.joinpath("odoo19-harness-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
        return result
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stdout or "") + (exc.stderr or "")
            output.joinpath("FAILED.log").write_text(detail[-20000:])
        raise HarnessError(f"disposable Odoo harness failed: {exc}") from exc
    finally:
        subprocess.run(
            ["docker", "rm", "-f", database],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["docker", "network", "rm", network],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-wheel", type=Path, required=True)
    parser.add_argument("--reportlab-wheel", type=Path, required=True)
    parser.add_argument(
        "--addon",
        type=Path,
        default=ROOT / "integrations/odoo/addons/docsubstrate_report",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=ROOT / "public-alpha/odoo-harness/sale_order_smoke.py",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--odoo-image", default="odoo:19.0")
    parser.add_argument("--postgres-image", default="postgres:16")
    args = parser.parse_args(argv)
    try:
        result = run_harness(
            core_wheel=args.core_wheel.resolve(),
            reportlab_wheel=args.reportlab_wheel.resolve(),
            addon=args.addon.resolve(),
            payload=args.payload.resolve(),
            output=args.output.resolve(),
            odoo_image=args.odoo_image,
            postgres_image=args.postgres_image,
        )
    except HarnessError as exc:
        print(f"public-alpha-odoo19-harness: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
