from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "xtb_calibration" / "run_xtb_calibration.py"


def test_run_xtb_calibration_reports_missing_executable(tmp_path) -> None:
    env = {**os.environ, "PATH": str(tmp_path)}
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--answers",
            "tasks/xtb_xyz/calibration_answers.jsonl",
            "--output",
            str(tmp_path / "calibration-results.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"
    assert payload["xtb_executable"] is None


def test_run_xtb_calibration_help() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--answers" in completed.stdout
    assert "--output" in completed.stdout
    assert "--max-candidates" in completed.stdout


def test_analyze_xtb_calibration_writes_summary_files(tmp_path) -> None:
    input_path = tmp_path / "results.json"
    output_dir = tmp_path / "analysis"
    input_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "rows": [
                    {
                        "candidate_id": "positive_1",
                        "role": "positive_candidate",
                        "task_id": "xtb_lumo_min_008",
                        "status": "ok",
                        "failure_type": None,
                        "score": 0.8,
                        "properties": {"lumo_energy": -3.0, "relaxation_energy": 0.05},
                    },
                    {
                        "candidate_id": "negative_1",
                        "role": "negative_baseline",
                        "task_id": "xtb_lumo_min_008",
                        "status": "ok",
                        "failure_type": None,
                        "score": 0.1,
                        "properties": {"lumo_energy": 0.5, "relaxation_energy": 0.02},
                    },
                    {
                        "candidate_id": "bad_1",
                        "role": "stress_case",
                        "task_id": "xtb_hessian_thermo_stability_013",
                        "status": "error",
                        "failure_type": "verifier_timeout",
                        "score": 0.0,
                        "properties": {},
                    },
                ],
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/xtb_calibration/analyze_xtb_calibration.py",
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    summary = json.loads((output_dir / "summary.json").read_text())
    assert summary["tasks"]["xtb_lumo_min_008"]["num_rows"] == 2
    assert summary["tasks"]["xtb_lumo_min_008"]["num_positive_candidates"] == 1
    assert summary["tasks"]["xtb_lumo_min_008"]["num_negative_baselines"] == 1
    assert summary["tasks"]["xtb_hessian_thermo_stability_013"]["failure_types"]["verifier_timeout"] == 1
    assert (output_dir / "summary.md").exists()
