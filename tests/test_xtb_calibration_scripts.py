from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.xtb_calibration.run_xtb_calibration import build_calibration_row


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


def test_build_calibration_row_records_expert_diagnostics() -> None:
    row = build_calibration_row(
        answer={
            "candidate_id": "ritonavir_1",
            "role": "positive_candidate",
        },
        result={
            "task_id": "xtb_ritonavir_optimized_energy_min_018",
            "status": "ok",
            "failure_type": None,
            "properties": {
                "charge": 0,
                "uhf": 0,
                "total_energy": -148.19,
                "graph_match": True,
                "stereochemistry_match": True,
                "post_optimization_graph_match": True,
                "post_optimization_stereochemistry_match": True,
            },
            "scores": {
                "score": 0.75,
                "property_score": 0.75,
                "constraint_scores": [],
            },
        },
        task={
            "constraints": [{"property": "total_energy"}],
            "structure_identity": {"recheck_after_optimization": True},
        },
        spec={"backend": {"calculation_mode": "optimized"}},
        wall_time_seconds=12.5,
    )

    assert row["property_name"] == "total_energy"
    assert row["calculation_mode"] == "optimized"
    assert row["resolved_charge"] == 0
    assert row["resolved_uhf"] == 0
    assert row["wall_time_seconds"] == 12.5
    assert row["converged"] is True
    assert row["identity"] == {
        "graph_match": True,
        "stereochemistry_match": True,
        "post_optimization_graph_match": True,
        "post_optimization_stereochemistry_match": True,
    }
    assert row["peak_memory_mb"] is None
    assert row["peak_memory_status"] == "unavailable"


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
                        "property_name": "lumo_energy",
                        "wall_time_seconds": 8.0,
                        "converged": True,
                        "identity": {
                            "graph_match": True,
                            "stereochemistry_match": None,
                            "post_optimization_graph_match": None,
                            "post_optimization_stereochemistry_match": None,
                        },
                        "properties": {"lumo_energy": -3.0, "relaxation_energy": 0.05},
                    },
                    {
                        "candidate_id": "negative_1",
                        "role": "negative_baseline",
                        "task_id": "xtb_lumo_min_008",
                        "status": "ok",
                        "failure_type": None,
                        "score": 0.1,
                        "property_name": "lumo_energy",
                        "wall_time_seconds": 4.0,
                        "converged": True,
                        "identity": {
                            "graph_match": False,
                            "stereochemistry_match": None,
                            "post_optimization_graph_match": None,
                            "post_optimization_stereochemistry_match": None,
                        },
                        "properties": {"lumo_energy": 0.5, "relaxation_energy": 0.02},
                    },
                    {
                        "candidate_id": "bad_1",
                        "role": "stress_case",
                        "task_id": "xtb_hessian_thermo_stability_013",
                        "status": "error",
                        "failure_type": "verifier_timeout",
                        "score": 0.0,
                        "property_name": "entropy_298_per_heavy_atom",
                        "wall_time_seconds": 20.0,
                        "converged": False,
                        "identity": {},
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
    assert summary["tasks"]["xtb_lumo_min_008"]["success_rate"] == 1.0
    assert summary["tasks"]["xtb_lumo_min_008"]["timeout_count"] == 0
    assert summary["tasks"]["xtb_lumo_min_008"]["runtime_seconds"]["median"] == 6.0
    assert summary["tasks"]["xtb_lumo_min_008"]["property_stats"] == {
        "count": 2,
        "min": -3.0,
        "median": -1.25,
        "mean": -1.25,
        "max": 0.5,
    }
    assert summary["tasks"]["xtb_lumo_min_008"]["structure_retention_failures"] == 1
    assert summary["tasks"]["xtb_hessian_thermo_stability_013"]["failure_types"]["verifier_timeout"] == 1
    assert summary["tasks"]["xtb_hessian_thermo_stability_013"]["timeout_count"] == 1
    assert (output_dir / "summary.md").exists()
