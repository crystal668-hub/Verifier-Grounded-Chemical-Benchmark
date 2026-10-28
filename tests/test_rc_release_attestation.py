from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases/v1.0.0-rc"


def read_json(name):
    return json.loads((RELEASE / name).read_text())


def test_rc_tag_inventory_and_source_hashes_are_bound():
    manifest = read_json("manifest.json")
    inventory = read_json("task-inventory.json")
    acceptance = read_json("acceptance.json")
    assert manifest["version"] == inventory["package_version"] == acceptance["package_version"] == "1.0.0rc1"
    assert manifest["tag"] == acceptance["tag"] == "v1.0.0-rc"
    commit = subprocess.check_output(
        ["git", "rev-parse", "v1.0.0-rc^{commit}"], cwd=ROOT, text=True,
    ).strip()
    assert commit == manifest["canonical_source"]["commit"] == acceptance["source_commit"]
    tree = subprocess.check_output(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=ROOT, text=True).strip()
    assert tree == manifest["canonical_source"]["tree"] == acceptance["source_tree"]
    assert {name: info["count"] for name, info in inventory["tracks"].items()} == {
        "open_generation_rdkit": 10, "open_generation_xtb": 20,
        "property_calculation_basic": 51, "property_calculation_advanced": 19,
    }
    for name, info in inventory["tracks"].items():
        assert info["task_pack_version"] == "1.0.0rc1"
        for filename, field in (("tasks.yaml", "tasks_sha256"), ("scoring.yaml", "scoring_sha256"),
                                ("verifier_specs.yaml", "verifier_specs_sha256")):
            if field not in info:
                continue
            path = f"src/verifier_grounded_benchmark/task/packs/{name}/{filename}"
            content = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
            assert hashlib.sha256(content).hexdigest() == info[field]


def test_rc_materials_hashes_and_acceptance_scope():
    listed = set()
    for line in (RELEASE / "MATERIALS.SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((RELEASE / name).read_bytes()).hexdigest() == digest
        listed.add(name)
    actual = {path.relative_to(RELEASE).as_posix() for path in RELEASE.rglob("*")
              if path.is_file() and path.name != "MATERIALS.SHA256SUMS"}
    assert listed == actual
    acceptance = read_json("acceptance.json")
    assert acceptance["status"] == "accepted_for_local_artifact_delivery"
    assert acceptance["scope"]["public_sample_answers"] is False
    assert acceptance["scope"]["remote_publication"] is False
    assert acceptance["scope"]["review_system_changes"] is False
    assert acceptance["gates"]["core_tests"]["skipped"] == 15
    assert acceptance["unverified"]
    migration = read_json("task-id-migration.json")
    assert len(migration["retired_task_ids"]) == 5
    assert sum(old != new for old, new in migration["id_mapping"].items()) == 25


def test_rc_local_archives_match_and_contain_no_public_sample_files():
    manifest = read_json("manifest.json")
    assert (RELEASE / "SHA256SUMS").read_text() == "".join(
        f"{item['sha256']}  {item['filename']}\n" for item in manifest["artifacts"]
    )
    for item in manifest["artifacts"]:
        path = ROOT / "dist" / item["filename"]
        if not path.exists():
            continue  # Local artifacts are not committed; metadata remains independently verifiable.
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()
        assert not any(name.endswith("sample_answers.jsonl") or "_regression_answers.jsonl" in name for name in names)
        assert not any("/task/calibration/" in name or "review_system/" in name or "task_backups/" in name for name in names)
