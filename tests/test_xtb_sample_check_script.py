from __future__ import annotations

import json
import os
import subprocess
import sys


def test_check_xtb_xyz_samples_reports_missing_executable(tmp_path) -> None:
    answers = tmp_path / "answers.jsonl"
    answers.write_text('{"task_id":"xtb_001_gap_window","candidates":[{}]}\n')
    env = {**os.environ, "PATH": str(tmp_path)}
    completed = subprocess.run(
        [sys.executable, "scripts/validation/check_xtb_xyz_samples.py", "--answers", str(answers)],
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


def test_xtb_validation_requires_an_explicit_answer_file() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validation/check_xtb_xyz_samples.py"],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 2
    assert "--answers" in completed.stderr


def test_xtb_validation_rejects_empty_answer_file(tmp_path) -> None:
    answers = tmp_path / "empty.jsonl"
    answers.write_text("")
    completed = subprocess.run(
        [sys.executable, "scripts/validation/check_xtb_xyz_samples.py", "--answers", str(answers)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 2
    assert "at least one answer" in completed.stderr
