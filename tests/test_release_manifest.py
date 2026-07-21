from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from scripts.release.build_release import (
    normalized_release_payloads,
    payload_digest,
    task_inventory,
    verify_archive_payloads,
)


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "releases" / "v0.1.1"
CURRENT_RELEASE_DIR = ROOT / "releases" / "v0.2.0"


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
    assert inventory["package_version"] == "0.1.1"
    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "cc5814a9c0c0d3486f22009cbf7361dc2b3cefe8"
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

    wheel_payloads, sdist_payloads = normalized_release_payloads(
        wheel_path,
        sdist_path,
        archive_packages=("benchmark", "verifiers", "verifier_grounded_benchmark", "vgb"),
    )
    assert wheel_payloads == sdist_payloads
    assert {
        "file_count": len(wheel_payloads),
        "sha256": payload_digest(wheel_payloads),
    } == manifest["verified_payload"]


def test_release_manifest_records_canonical_source_tree() -> None:
    manifest = json.loads((RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    tree = subprocess.run(
        ["git", "rev-parse", f"{manifest['canonical_source']['commit']}^{{tree}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert tree == manifest["canonical_source"]["tree"]


def test_current_release_manifest_binds_v2_artifacts_profiles_and_openclaw() -> None:
    manifest = json.loads(
        (CURRENT_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    inventory = json.loads(
        (CURRENT_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8")
    )
    profiles = json.loads(
        (CURRENT_RELEASE_DIR / "scoring-profiles.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == inventory["package_version"] == "0.2.0"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v1"
    # v0.2.0 remains an immutable linear_goal_v1 release. The checkout now
    # contains the unreleased v2 shadow profiles and must not be compared to
    # this historical inventory.
    assert profiles["scoring_version"] == "linear_goal_v1"

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    artifacts = {item["filename"]: item for item in manifest["artifacts"]}
    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.2.0-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.2.0.tar.gz"
    for path in (wheel_path, sdist_path):
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifacts[path.name]["sha256"]
        assert len(content) == artifacts[path.name]["size"]
    assert verify_archive_payloads(wheel_path, sdist_path) == manifest["verified_payload"]

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "75d6966e9a2ab39c184823abeefd28bddbfa56aa"
    assert {name: value["count"] for name, value in openclaw["datasets"].items()} == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 11,
        "verifier_grounded_xtb_xyz": 18,
    }
    assert len(openclaw["release_config_sha256"]) == 64
