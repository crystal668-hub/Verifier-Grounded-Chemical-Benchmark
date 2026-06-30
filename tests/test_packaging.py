from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_XTB_CALIBRATION_FILES = {
    "tasks/xtb_xyz/calibration_answers.jsonl",
    "tasks/xtb_xyz/calibration_manifest.yaml",
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
