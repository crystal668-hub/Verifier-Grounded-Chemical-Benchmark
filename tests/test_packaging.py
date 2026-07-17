from __future__ import annotations

import subprocess
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

import yaml

from scripts.release.build_release import verify_archive_payloads


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_XTB_CALIBRATION_FILES = {
    "verifier_grounded_benchmark/task/calibration/xtb/tasks.yaml",
    "verifier_grounded_benchmark/task/calibration/xtb/verifier_specs.yaml",
    "verifier_grounded_benchmark/task/calibration/xtb/answers.jsonl",
    "verifier_grounded_benchmark/task/calibration/xtb/manifest.yaml",
}
REMOVED_COMPATIBILITY_SCRIPTS = {
    "scripts/score_answers.py",
}
REMOVED_LEGACY_PACKAGES = {
    "benchmark/__init__.py",
    "verifiers/__init__.py",
}
FORMAL_V2_TASK_FILES = {
    "verifier_grounded_benchmark/task/packs/rdkit/tasks.yaml",
    "verifier_grounded_benchmark/task/packs/rdkit/verifier_specs.yaml",
    "verifier_grounded_benchmark/task/packs/rdkit/sample_answers.jsonl",
    "verifier_grounded_benchmark/task/packs/xtb/tasks.yaml",
    "verifier_grounded_benchmark/task/packs/xtb/verifier_specs.yaml",
    "verifier_grounded_benchmark/task/packs/xtb/sample_answers.jsonl",
    "verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml",
    "verifier_grounded_benchmark/task/packs/property_calculation/verifier_specs.yaml",
    "verifier_grounded_benchmark/task/packs/property_calculation/sample_answers.jsonl",
}
FORMAL_EXPERT_XTB_TASK_IDS = {
    "xtb_formula_dipole_min_014",
    "xtb_two_fluorine_gap_min_015",
    "xtb_c10_f2_gap_min_016",
    "xtb_roy_singlepoint_energy_min_017",
    "xtb_ritonavir_optimized_energy_min_018",
}


def test_distribution_artifacts_exclude_private_and_removed_files(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--sdist", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    wheel_path = next(tmp_path.glob("*.whl"))
    sdist_path = next(tmp_path.glob("*.tar.gz"))

    with zipfile.ZipFile(wheel_path) as wheel:
        wheel_members = set(wheel.namelist())
        wheel_tasks = yaml.safe_load(
            wheel.read("verifier_grounded_benchmark/task/packs/xtb/tasks.yaml")
        )
    with tarfile.open(sdist_path) as sdist:
        sdist_members = {"/".join(Path(member.name).parts[1:]) for member in sdist.getmembers()}
        tasks_member = next(
            member
            for member in sdist.getmembers()
            if member.name.endswith(
                "/src/verifier_grounded_benchmark/task/packs/xtb/tasks.yaml"
            )
        )
        extracted_tasks = sdist.extractfile(tasks_member)
        assert extracted_tasks is not None
        sdist_tasks = yaml.safe_load(extracted_tasks.read())

    assert PRIVATE_XTB_CALIBRATION_FILES.isdisjoint(wheel_members)
    assert PRIVATE_XTB_CALIBRATION_FILES.isdisjoint(sdist_members)
    assert REMOVED_COMPATIBILITY_SCRIPTS.isdisjoint(wheel_members)
    assert REMOVED_COMPATIBILITY_SCRIPTS.isdisjoint(sdist_members)
    assert REMOVED_LEGACY_PACKAGES.isdisjoint(wheel_members)
    assert {f"src/{path}" for path in REMOVED_LEGACY_PACKAGES}.isdisjoint(sdist_members)
    assert not any(path.startswith("tasks/") for path in wheel_members)
    assert not any(path.startswith("tasks/") for path in sdist_members)
    assert FORMAL_V2_TASK_FILES.issubset(wheel_members)
    assert {f"src/{path}" for path in FORMAL_V2_TASK_FILES}.issubset(sdist_members)
    assert not any("/task/calibration/" in path for path in wheel_members)
    assert not any("/task/calibration/" in path for path in sdist_members)
    assert not any("/task/packs/experimental/" in path for path in wheel_members)
    assert not any("/task/packs/experimental/" in path for path in sdist_members)
    assert FORMAL_EXPERT_XTB_TASK_IDS.issubset(
        {task["task_id"] for task in wheel_tasks["tasks"]}
    )
    assert FORMAL_EXPERT_XTB_TASK_IDS.issubset(
        {task["task_id"] for task in sdist_tasks["tasks"]}
    )
    payload = verify_archive_payloads(wheel_path, sdist_path)
    assert payload["file_count"] > 0
    assert len(payload["sha256"]) == 64


def test_wheel_metadata_publishes_materials_extra(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    wheel_path = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        metadata_name = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode())

    provides_extra = metadata.get_all("Provides-Extra", [])
    requires_dist = metadata.get_all("Requires-Dist", [])

    assert not any(requirement.startswith("m" + "cp") for requirement in requires_dist)
    assert "materials" in provides_extra
    assert "atomistic" + "skills" not in provides_extra
    assert any(
        requirement.startswith("matgl==4.0.2")
        and (
            "extra == 'materials'" in requirement
            or 'extra == "materials"' in requirement
        )
        for requirement in requires_dist
    )


def test_wheel_metadata_publishes_mlip_extras(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    wheel_path = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        metadata_name = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode())

    provides_extra = metadata.get_all("Provides-Extra", [])
    requires_dist = metadata.get_all("Requires-Dist", [])

    assert "torchani" in provides_extra
    assert "mace" in provides_extra
    for package, extra in [
        ("torchani==2.8.2", "torchani"),
        ("ase==3.28.0", "torchani"),
        ("mace-torch==0.3.16", "mace"),
        ("ase==3.28.0", "mace"),
        ("pymatgen==2026.5.4", "mace"),
    ]:
        assert any(
            requirement.startswith(package)
            and (
                f"extra == '{extra}'" in requirement
                or f'extra == "{extra}"' in requirement
            )
            for requirement in requires_dist
        )
    assert any(
        requirement.startswith("pymatgen==2026.5.4")
        and (
            "extra == 'materials'" in requirement
            or 'extra == "materials"' in requirement
        )
        for requirement in requires_dist
    )


def test_wheel_metadata_publishes_future_backends_extra(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    wheel_path = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel_path) as wheel:
        metadata_name = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode())

    provides_extra = metadata.get_all("Provides-Extra", [])
    requires_dist = metadata.get_all("Requires-Dist", [])

    assert "future-backends" in provides_extra
    for package in [
        "ase==3.28.0",
        "cclib==1.8.1",
        "chembl-webresource-client==0.10.9",
        "mp-api==0.46.1",
        "ord-schema==0.6.5",
    ]:
        assert any(
            requirement.startswith(package)
            and (
                "extra == 'future-backends'" in requirement
                or 'extra == "future-backends"' in requirement
            )
            for requirement in requires_dist
        )
