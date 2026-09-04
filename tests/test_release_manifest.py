from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import yaml

from scripts.release.build_release import (
    normalized_release_payloads,
    payload_digest,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "releases" / "v0.1.1"
CURRENT_RELEASE_DIR = ROOT / "releases" / "v0.2.0"
V2_RELEASE_DIR = ROOT / "releases" / "v0.3.0"
V4_RELEASE_DIR = ROOT / "releases" / "v0.4.0"
V41_RELEASE_DIR = ROOT / "releases" / "v0.4.1"
V42_RELEASE_DIR = ROOT / "releases" / "v0.4.2"
V43_RELEASE_DIR = ROOT / "releases" / "v0.4.3"
V50_RELEASE_DIR = ROOT / "releases" / "v0.5.0"
V60_RELEASE_DIR = ROOT / "releases" / "v0.6.0"


def assert_release_artifacts_if_present(
    manifest: dict,
    wheel_path: Path,
    sdist_path: Path,
    *,
    archive_packages: tuple[str, ...] = ("verifier_grounded_benchmark", "vgb"),
) -> None:
    """Validate local release files without requiring them in a source checkout."""
    if not wheel_path.is_file() or not sdist_path.is_file():
        return

    artifacts = {item["filename"]: item for item in manifest["artifacts"]}
    for path in (wheel_path, sdist_path):
        content = path.read_bytes()
        assert path.name in artifacts
        assert hashlib.sha256(content).hexdigest() == artifacts[path.name]["sha256"]
        assert len(content) == artifacts[path.name]["size"]

    wheel_payloads, sdist_payloads = normalized_release_payloads(
        wheel_path,
        sdist_path,
        archive_packages=archive_packages,
    )
    assert wheel_payloads == sdist_payloads
    assert {
        "file_count": len(wheel_payloads),
        "sha256": payload_digest(wheel_payloads),
    } == manifest["verified_payload"]


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

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.1.1-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.1.1.tar.gz"
    assert_release_artifacts_if_present(
        manifest,
        wheel_path,
        sdist_path,
        archive_packages=("benchmark", "verifiers", "verifier_grounded_benchmark", "vgb"),
    )


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

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.2.0-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.2.0.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "75d6966e9a2ab39c184823abeefd28bddbfa56aa"
    assert {name: value["count"] for name, value in openclaw["datasets"].items()} == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 11,
        "verifier_grounded_xtb_xyz": 18,
    }
    assert len(openclaw["release_config_sha256"]) == 64


def test_v2_release_manifest_binds_formal_profiles_and_openclaw_sync() -> None:
    manifest = json.loads((V2_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((V2_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8"))
    profiles = json.loads((V2_RELEASE_DIR / "scoring-profiles.json").read_text(encoding="utf-8"))

    assert manifest["version"] == inventory["package_version"] == "0.3.0"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert profiles["package_version"] == "0.3.0"
    assert profiles["scoring_version"] == "linear_goal_v2"

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.3.0-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.3.0.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "d3ed045c1e2ca38ed0d188ffb45116c4a712ecb1"
    assert {name: value["count"] for name, value in openclaw["datasets"].items()} == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 11,
        "verifier_grounded_xtb_xyz": 18,
    }
    assert len(openclaw["release_config_sha256"]) == 64


def test_v4_release_manifest_binds_expert_tasks_and_artifacts() -> None:
    manifest = json.loads((V4_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (V4_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8")
    )
    profiles = json.loads(
        (V4_RELEASE_DIR / "scoring-profiles.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == inventory["package_version"] == "0.4.0"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert profiles["package_version"] == "0.4.0"
    assert {name: value["count"] for name, value in inventory["tracks"].items()} == {
        "property_calculation": 2,
        "rdkit": 14,
        "xtb": 20,
    }
    assert {
        "rdkit_chain_end_to_end_maximize_6p36_6p49_v2",
        "rdkit_caffeine_morgan_tanimoto_maximize_0p0_1p0_v2",
        "xtb_odd_element_gap_maximize_3p6_11p9_v2",
        "xtb_pyrene_total_energy_minimize_neg_63p56975_neg_63p5669_v2",
    }.issubset(profiles["profiles"])

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.0-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.0.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "741903305f158a7b9e4ca3f5118afbc2546d21fe"
    assert {name: value["count"] for name, value in openclaw["datasets"].items()} == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 14,
        "verifier_grounded_xtb_xyz": 20,
    }
    assert len(openclaw["release_config_sha256"]) == 64


def test_v41_release_manifest_binds_clarified_prompt_and_artifacts() -> None:
    manifest = json.loads((V41_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (V41_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == inventory["package_version"] == "0.4.1"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert {name: value["count"] for name, value in inventory["tracks"].items()} == {
        "property_calculation": 2,
        "rdkit": 14,
        "xtb": 20,
    }

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.1-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.1.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "ae24a6079f50e2d4a0fd81dbada8fa64d20e78c3"
    assert {name: value["count"] for name, value in openclaw["datasets"].items()} == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 14,
        "verifier_grounded_xtb_xyz": 20,
    }
    assert len(openclaw["release_config_sha256"]) == 64


def test_v42_release_manifest_binds_dependency_preflight_artifacts() -> None:
    manifest = json.loads((V42_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (V42_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == inventory["package_version"] == "0.4.2"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert {name: value["count"] for name, value in inventory["tracks"].items()} == {
        "property_calculation": 2,
        "rdkit": 14,
        "xtb": 20,
    }

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.2-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.2.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    if wheel_path.is_file() and sdist_path.is_file():
        with zipfile.ZipFile(wheel_path) as wheel:
            assert (
                "verifier_grounded_benchmark/evaluation/external_dependencies.py"
                in wheel.namelist()
            )
            specs = yaml.safe_load(
                wheel.read(
                    "verifier_grounded_benchmark/task/packs/xtb/verifier_specs.yaml"
                )
            )["verifiers"]
        pyrene = next(
            spec for spec in specs if spec["verifier_id"] == "xtb_pyrene_crest_energy_v1"
        )
        assert {
            dependency["executable"]: dependency["version"]
            for dependency in pyrene["external_dependencies"]
        } == {"crest": "2.12", "xtb": "6.7.1"}

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "d65536873e4d83b904a03abf19374c3ea4c7a6d4"
    assert {name: value["count"] for name, value in openclaw["datasets"].items()} == {
        "verifier_grounded_property_calculation": 2,
        "verifier_grounded_rdkit": 14,
        "verifier_grounded_xtb_xyz": 20,
    }
    assert len(openclaw["release_config_sha256"]) == 64


def test_v43_release_manifest_binds_recalibrated_artifacts_and_openclaw_runtime() -> None:
    manifest = json.loads((V43_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (V43_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == inventory["package_version"] == "0.4.3"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert {name: value["count"] for name, value in inventory["tracks"].items()} == {
        "property_calculation": 2,
        "rdkit": 14,
        "xtb": 20,
    }

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.3-py3-none-any.whl"
    sdist_path = ROOT / "dist" / "verifier_grounded_benchmark-0.4.3.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "820b15ae97706cfb76710b02873a85335b9d8607"
    assert openclaw["release_config_sha256"] == (
        "a8e666e1cea057511d7d8779f3ed38e3a4bf0b344684c8355c6326f75ca66ad6"
    )
    assert openclaw["datasets"] == {
        "verifier_grounded_property_calculation": {
            "count": 2,
            "sha256": "254ab7e79c7bdbf69bac541a824308a8a3ea6a0c0094834137d4d2664802703a",
        },
        "verifier_grounded_rdkit": {
            "count": 14,
            "sha256": "ce93f52efd61a3997190dcc7471b28f2fb996084ded893d94a914e2ba9ad0dbb",
        },
        "verifier_grounded_xtb_xyz": {
            "count": 20,
            "sha256": "f0c6788049c0921fc4f332f41caae27655079562b12fa9c7ec9713b0b23723fa",
        },
    }


def test_v50_release_manifest_binds_property_calculation_expansion_and_openclaw_runtime() -> None:
    manifest = json.loads((V50_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((V50_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8"))

    assert manifest["version"] == inventory["package_version"] == "0.5.0"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert {name: value["count"] for name, value in inventory["tracks"].items()} == {
        "property_calculation": 14,
        "rdkit": 14,
        "xtb": 20,
    }

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "build" / "release-dist" / "verifier_grounded_benchmark-0.5.0-py3-none-any.whl"
    sdist_path = ROOT / "build" / "release-dist" / "verifier_grounded_benchmark-0.5.0.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "dca714c3ab5c89500b80854dac0a4a53b0c85b9a"
    assert openclaw["release_config_sha256"] == (
        "fe85d7fb1ae3b35221e70154cd40ccbdc3d45226e65a4f4d654105059b4e5178"
    )
    assert openclaw["datasets"] == {
        "verifier_grounded_property_calculation": {
            "count": 14,
            "sha256": "e42684f128fec0b8b795a55c1b4234f8df32f6eacde6aaece5d27f0717f2f41a",
        },
        "verifier_grounded_rdkit": {
            "count": 14,
            "sha256": "5bd66585afedf8fc5a7999c520f82dd4c4899d32639a23f656fd013649d6ce48",
        },
        "verifier_grounded_xtb_xyz": {
            "count": 20,
            "sha256": "de33af6561312538557951fe4e38eefecfbd4fb14ea223a956d00500acfaeffa",
        },
    }


def test_v60_release_manifest_binds_standardized_property_calculation_tasks() -> None:
    manifest = json.loads((V60_RELEASE_DIR / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads((V60_RELEASE_DIR / "task-inventory.json").read_text(encoding="utf-8"))

    assert manifest["version"] == inventory["package_version"] == "0.6.0"
    assert manifest["result_schema_version"] == inventory["result_schema_version"] == "2"
    assert manifest["scoring_version"] == inventory["scoring_version"] == "linear_goal_v2"
    assert {name: value["count"] for name, value in inventory["tracks"].items()} == {
        "property_calculation": 20,
        "rdkit": 14,
        "xtb": 20,
    }
    assert inventory["tracks"]["property_calculation"]["task_ids"][:2] == [
        "property_calc_001_free_energy",
        "property_calc_002_crystal_phase",
    ]

    tagged_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", manifest["tag"]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tagged_commit == manifest["canonical_source"]["commit"]

    wheel_path = ROOT / "build" / "release-dist" / "verifier_grounded_benchmark-0.6.0-py3-none-any.whl"
    sdist_path = ROOT / "build" / "release-dist" / "verifier_grounded_benchmark-0.6.0.tar.gz"
    assert_release_artifacts_if_present(manifest, wheel_path, sdist_path)

    openclaw = manifest["integrations"]["openclaw"]
    assert openclaw["commit"] == "390ba0ff077248083ab32a3111e2e99036c6ed83"
    assert openclaw["release_config_sha256"] == (
        "ad9a51149135e34ca49f2997183c1f42d2bfed94df9ec679670facaa413626c9"
    )
    assert openclaw["datasets"] == {
        "verifier_grounded_property_calculation": {
            "count": 20,
            "sha256": "99c4cbad87427f388b826c19f9f304743de6165d7cca0a9644a283f256be8e27",
        },
        "verifier_grounded_rdkit": {
            "count": 14,
            "sha256": "2fb1543f3d7ea3d88e26371ad2cae3e14712dc61b3863357d9605f4f6bb0069a",
        },
        "verifier_grounded_xtb_xyz": {
            "count": 20,
            "sha256": "c60dfe63e95025210c98b49f1adf0baa326c0a75adf1a7ab5db7e20617a2c8ea",
        },
    }
