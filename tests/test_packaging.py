from __future__ import annotations

import subprocess
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_XTB_CALIBRATION_FILES = {
    "tasks/xtb_xyz/calibration_answers.jsonl",
    "tasks/xtb_xyz/calibration_manifest.yaml",
}
REMOVED_PROTOTYPE_TASK_PACKS = {
    "tasks/" + "atomistic" + "skills_smoke/tasks.yaml",
    "tasks/mace_materials/tasks.yaml",
    "tasks/matgl_materials/tasks.yaml",
}


def test_distribution_artifacts_exclude_private_xtb_calibration_data(tmp_path: Path) -> None:
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
    with tarfile.open(sdist_path) as sdist:
        sdist_members = {"/".join(Path(member.name).parts[1:]) for member in sdist.getmembers()}

    assert PRIVATE_XTB_CALIBRATION_FILES.isdisjoint(wheel_members)
    assert PRIVATE_XTB_CALIBRATION_FILES.isdisjoint(sdist_members)
    assert REMOVED_PROTOTYPE_TASK_PACKS.isdisjoint(wheel_members)
    assert REMOVED_PROTOTYPE_TASK_PACKS.isdisjoint(sdist_members)


def test_wheel_metadata_publishes_matgl_materials_extra_only(tmp_path: Path) -> None:
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
    assert "mace" not in provides_extra
    assert "atomistic" + "skills" not in provides_extra
    assert any(
        requirement.startswith("matgl==4.0.2")
        and (
            "extra == 'materials'" in requirement
            or 'extra == "materials"' in requirement
        )
        for requirement in requires_dist
    )
