from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from scripts.release.build_release import task_inventory, verify_archive_payloads


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "releases" / "v0.1.1"


def test_release_manifest_binds_tag_artifacts_and_inventory() -> None:
    manifest = json.loads((RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8")
    )
    canonical_commit = manifest["canonical_source"]["commit"]

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == canonical_commit
    assert manifest["version"] == inventory["package_version"] == "0.1.1"
    assert inventory == task_inventory("0.1.1")
    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "dae8d47ae25df330ed7c44ddefaaf0a45f3c8677"
    assert {
        name: value["count"] for name, value in openclaw["datasets"].items()
    } == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 11,
        "verifier_grounded_xtb_xyz": 18,
    }

    artifacts = {item["filename"]: item for item in manifest["artifacts"]}
    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.1.1-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.1.1.tar.gz"
    for path in (wheel_path, sdist_path):
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifacts[path.name]["sha256"]
        assert len(content) == artifacts[path.name]["size"]

    assert verify_archive_payloads(wheel_path, sdist_path) == manifest["verified_payload"]


def test_release_source_payload_has_not_changed_after_canonical_commit() -> None:
    manifest = json.loads((RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            manifest["canonical_source"]["commit"],
            "--",
            "pyproject.toml",
            "uv.lock",
            "src",
            "tasks",
        ],
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 0
