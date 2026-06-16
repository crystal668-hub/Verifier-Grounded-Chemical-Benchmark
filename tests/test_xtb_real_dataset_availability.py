from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_inspect_xtb_real_dataset_availability_help() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/inspect_xtb_real_dataset_availability.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--source-manifest" in completed.stdout
    assert "--output-json" in completed.stdout
    assert "--check-remote" in completed.stdout


def test_inspect_xtb_real_dataset_availability_reports_missing_cache(tmp_path) -> None:
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": {
                    "qmugs": {
                        "status": "required",
                        "cache_path": str(tmp_path / "missing_qmugs"),
                        "access": {
                            "type": "nextcloud_public_webdav",
                            "files": {
                                "structures.tar.gz": "https://example.invalid/structures.tar.gz",
                            },
                            "conversion": "scripts/convert_xtb_real_dataset_sdf.py",
                        },
                    },
                    "tartarus_opv": {
                        "status": "optional_if_unavailable",
                        "cache_path": str(tmp_path / "opv"),
                        "access": {"status": "manual_or_generated_geometry_required"},
                    },
                },
            },
            sort_keys=True,
        )
    )
    output = tmp_path / "availability.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_xtb_real_dataset_availability.py",
            "--source-manifest",
            str(manifest),
            "--output-json",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(output.read_text())
    assert payload["status"] == "ok"
    assert payload["remote_checked"] is False
    assert payload["sources"]["qmugs"]["local_files"]["structures.tar.gz"]["exists"] is False
    assert payload["sources"]["qmugs"]["conversion"] == "scripts/convert_xtb_real_dataset_sdf.py"
    assert payload["sources"]["tartarus_opv"]["access_status"] == "manual_or_generated_geometry_required"


def test_inspect_xtb_real_dataset_availability_reports_existing_cache(tmp_path) -> None:
    cache = tmp_path / "qmugs"
    cache.mkdir()
    cached_file = cache / "structures.tar.gz"
    cached_file.write_bytes(b"unit")
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": {
                    "qmugs": {
                        "status": "required",
                        "cache_path": str(cache),
                        "access": {
                            "type": "nextcloud_public_webdav",
                            "files": {
                                "structures.tar.gz": "https://example.invalid/structures.tar.gz",
                            },
                        },
                    },
                },
            },
            sort_keys=True,
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_xtb_real_dataset_availability.py",
            "--source-manifest",
            str(manifest),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    cached = payload["sources"]["qmugs"]["local_files"]["structures.tar.gz"]
    assert cached["exists"] is True
    assert cached["size_bytes"] == 4


def test_inspect_xtb_real_dataset_availability_does_not_check_remote_by_default(tmp_path, monkeypatch) -> None:
    from scripts import inspect_xtb_real_dataset_availability as inspector

    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": {
                    "qmugs": {
                        "status": "required",
                        "cache_path": str(tmp_path / "qmugs"),
                        "access": {
                            "type": "nextcloud_public_webdav",
                            "files": {
                                "structures.tar.gz": "https://example.invalid/structures.tar.gz",
                            },
                        },
                    },
                },
            },
            sort_keys=True,
        )
    )

    def fail_remote_head(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("remote_head should not be called unless --check-remote is passed")

    monkeypatch.setattr(inspector, "remote_head", fail_remote_head)

    payload = inspector.inspect_manifest(manifest, check_remote=False, remote_timeout=0.01)

    assert payload["remote_checked"] is False
    assert "remote_files" not in payload["sources"]["qmugs"]
