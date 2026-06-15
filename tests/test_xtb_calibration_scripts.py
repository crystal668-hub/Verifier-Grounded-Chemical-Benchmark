from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_xtb_calibration.py"


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
