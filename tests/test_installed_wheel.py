from __future__ import annotations

import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
    python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / "python"
    resources_completed = subprocess.run(
        [
            str(python),
            "-c",
            (
                "from importlib.resources import files; import json; "
                "print(json.dumps(["
                "str(files('verifier_grounded_benchmark.task.packs.rdkit').joinpath('sample_answers.jsonl')),"
                "str(files('verifier_grounded_benchmark.task.packs.property_calculation').joinpath('sample_answers.jsonl'))]))"
            ),
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    answers_path, property_answers_path = json.loads(resources_completed.stdout)
    completed = subprocess.run(
        [
            str(executable),
            "--track",
            "rdkit",
            "--answers",
            answers_path,
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
            property_answers_path,
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

    xtb_completed = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import json, verifier_grounded_benchmark as v; "
                "t=v.load_track('xtb'); "
                "print(json.dumps({'task_ids':[x['task_id'] for x in t.tasks()],"
                "'num_specs':len(t.verifier_specs_by_id)}))"
            ),
        ],
        cwd=tmp_path,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    xtb_payload = json.loads(xtb_completed.stdout)
    assert len(xtb_payload["task_ids"]) == 18
    assert xtb_payload["num_specs"] == 13
    assert {
        "xtb_formula_dipole_min_014",
        "xtb_two_fluorine_gap_min_015",
        "xtb_c10_f2_gap_min_016",
        "xtb_roy_singlepoint_energy_min_017",
        "xtb_ritonavir_optimized_energy_min_018",
    }.issubset(xtb_payload["task_ids"])
