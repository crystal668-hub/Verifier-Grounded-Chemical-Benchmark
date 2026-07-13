from __future__ import annotations

import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANSWERS_PATH = ROOT / "tasks" / "rdkit_baseline" / "sample_answers.jsonl"
PROPERTY_ANSWERS_PATH = ROOT / "tasks" / "property_calculation" / "sample_answers.jsonl"
PROJECT_SITE_PACKAGE_PREFIXES = (
    "_editable_impl_verifier_grounded_benchmark",
    "benchmark",
    "tasks",
    "verifier_grounded_benchmark",
    "verifier_grounded_benchmark-",
    "verifiers",
    "vgb",
)


def test_installed_wheel_vgb_score_rdkit_smoke(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    wheels = sorted(dist_dir.glob("*.whl"))
    assert len(wheels) == 1

    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
        check=True,
        text=True,
        capture_output=True,
    )
    pip = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "pip"
    subprocess.run(
        [str(pip), "install", "--no-deps", str(wheels[0])],
        check=True,
        text=True,
        capture_output=True,
    )
    dependency_site = tmp_path / "dependency_site"
    dependency_site.mkdir()
    current_site = Path(site.getsitepackages()[0])
    for item in current_site.iterdir():
        if item.name.endswith(".pth") or item.name.startswith(PROJECT_SITE_PACKAGE_PREFIXES):
            continue
        target = dependency_site / item.name
        if item.is_dir():
            try:
                target.symlink_to(item, target_is_directory=True)
            except OSError:
                shutil.copytree(item, target)
        else:
            try:
                target.symlink_to(item)
            except OSError:
                shutil.copy2(item, target)

    executable = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "vgb-score"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(dependency_site)
    if shutil.which("uv") is not None:
        env["UV_NO_SYNC"] = "1"
    completed = subprocess.run(
        [
            str(executable),
            "--track",
            "rdkit",
            "--answers",
            str(ANSWERS_PATH),
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )

    report = json.loads(completed.stdout)
    assert report["summary"]["coverage"]["complete"] is True
    assert report["summary"]["benchmark_score"] is not None

    property_completed = subprocess.run(
        [
            str(executable),
            "--track",
            "property_calculation",
            "--answers",
            str(PROPERTY_ANSWERS_PATH),
            "--require-complete",
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    property_report = json.loads(property_completed.stdout)
    assert property_report["summary"]["coverage"]["complete"] is True
    assert property_report["summary"]["benchmark_score"] == 1.0
    assert [row["score"] for row in property_report["rows"]] == [1.0, 1.0]
