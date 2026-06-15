from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_xtb_real_dataset_distribution_help() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_xtb_real_dataset_distribution.py", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--sampled-records" in completed.stdout
    assert "--tier" in completed.stdout
    assert "--output" in completed.stdout


def test_run_xtb_real_dataset_distribution_reports_missing_xtb(tmp_path) -> None:
    sampled = tmp_path / "sampled_records.jsonl"
    sampled.write_text(
        json.dumps(
            {
                "dataset_name": "unit_fixture",
                "record_id": "water",
                "xyz": "3\nwater\nO 0 0 0\nH 0.758602 0 0.504284\nH -0.758602 0 0.504284\n",
            }
        )
        + "\n"
    )
    env = {**os.environ, "PATH": str(tmp_path)}

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xtb_real_dataset_distribution.py",
            "--sampled-records",
            str(sampled),
            "--tier",
            "light",
            "--output",
            str(tmp_path / "results.json"),
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


def test_analyze_xtb_real_dataset_distribution_outputs_quantiles(tmp_path) -> None:
    results = tmp_path / "light_results.json"
    output_dir = tmp_path / "analysis"
    results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "light",
                "rows": [
                    {
                        "dataset_name": "qm9",
                        "record_id": "a",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {"homo_lumo_gap": 5.0, "dipole_moment": 1.0},
                    },
                    {
                        "dataset_name": "qm9",
                        "record_id": "b",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {"homo_lumo_gap": 7.0, "dipole_moment": 3.0},
                    },
                    {
                        "dataset_name": "qmugs",
                        "record_id": "c",
                        "status": "error",
                        "failure_type": "verifier_timeout",
                        "properties": {},
                    },
                ],
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_xtb_real_dataset_distribution.py",
            "--inputs",
            str(results),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    summary = json.loads((output_dir / "property_distribution_summary.json").read_text())
    assert "homo_lumo_gap" in summary["properties"]
    assert summary["properties"]["homo_lumo_gap"]["all"]["count"] == 2
    assert summary["properties"]["homo_lumo_gap"]["all"]["p50"] == 6.0
    assert (output_dir / "property_distribution_summary.md").exists()
    assert (output_dir / "failure_summary.csv").exists()
