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
    assert "--resume" in completed.stdout
    assert "--checkpoint-every" in completed.stdout
    assert "--progress-every" in completed.stdout


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


def test_run_xtb_real_dataset_distribution_rows_expose_property_statuses() -> None:
    from scripts.run_xtb_real_dataset_distribution import summarize

    rows = [
        {
            "dataset_name": "qm9",
            "record_id": "a",
            "tier": "medium",
            "status": "partial",
            "failure_type": "verifier_tool_error",
            "runtime_seconds": 1.0,
            "properties": {"global_electrophilicity": 0.4},
            "property_statuses": {
                "global_electrophilicity": {"status": "ok", "failure_type": None},
                "max_f_plus_on_carbon": {"status": "error", "failure_type": "verifier_tool_error"},
            },
        }
    ]

    summary = summarize(rows)

    assert summary["num_ok"] == 0
    assert summary["num_partial"] == 1
    assert summary["property_statuses"]["global_electrophilicity"]["ok"] == 1
    assert summary["property_statuses"]["max_f_plus_on_carbon"]["error"] == 1


def test_run_xtb_real_dataset_distribution_resume_skips_existing_rows(tmp_path) -> None:
    from scripts.run_xtb_real_dataset_distribution import load_existing_rows, pending_records

    output = tmp_path / "results.json"
    output.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "light",
                "rows": [
                    {
                        "dataset_name": "qmugs",
                        "record_id": "done",
                        "tier": "light",
                        "status": "ok",
                    }
                ],
            }
        )
    )
    records = [
        {"dataset_name": "qmugs", "record_id": "done"},
        {"dataset_name": "geom_drugs", "record_id": "todo"},
    ]

    existing = load_existing_rows(output, "light")
    pending = pending_records(records, existing, "light")

    assert [row["record_id"] for row in existing] == ["done"]
    assert [row["record_id"] for row in pending] == ["todo"]


def test_run_xtb_real_dataset_distribution_resume_does_not_skip_other_tiers(tmp_path) -> None:
    from scripts.run_xtb_real_dataset_distribution import load_existing_rows, pending_records

    output = tmp_path / "results.json"
    output.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "medium",
                "rows": [
                    {
                        "dataset_name": "qmugs",
                        "record_id": "same-record",
                        "tier": "medium",
                        "status": "ok",
                    }
                ],
            }
        )
    )
    records = [{"dataset_name": "qmugs", "record_id": "same-record"}]

    existing = load_existing_rows(output, "light")
    pending = pending_records(records, existing, "light")

    assert existing == []
    assert [row["record_id"] for row in pending] == ["same-record"]


def test_run_xtb_real_dataset_distribution_resume_keeps_dataset_names_distinct(tmp_path) -> None:
    from scripts.run_xtb_real_dataset_distribution import pending_records

    existing = [{"dataset_name": "qmugs", "record_id": "same-record", "tier": "light"}]
    records = [
        {"dataset_name": "qmugs", "record_id": "same-record"},
        {"dataset_name": "geom_drugs", "record_id": "same-record"},
    ]

    pending = pending_records(records, existing, "light")

    assert [(row["dataset_name"], row["record_id"]) for row in pending] == [("geom_drugs", "same-record")]


def test_run_xtb_real_dataset_distribution_writes_checkpoint_payload(tmp_path) -> None:
    from scripts.run_xtb_real_dataset_distribution import write_results

    output = tmp_path / "results.json"
    write_results(
        output,
        tier="light",
        sampled_records=tmp_path / "sampled.jsonl",
        executable="/usr/bin/xtb",
        rows=[
            {
                "dataset_name": "qmugs",
                "record_id": "a",
                "tier": "light",
                "status": "ok",
                "property_statuses": {"homo_lumo_gap": {"status": "ok"}},
            }
        ],
        complete=False,
    )

    payload = json.loads(output.read_text())
    assert payload["status"] == "running"
    assert payload["summary"]["num_ok"] == 1
    assert payload["rows"][0]["record_id"] == "a"


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


def test_analyze_xtb_real_dataset_distribution_counts_errors_per_property_tier(tmp_path) -> None:
    light_results = tmp_path / "light_results.json"
    medium_results = tmp_path / "medium_results.json"
    output_dir = tmp_path / "analysis"
    light_results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "light",
                "properties": ["homo_lumo_gap"],
                "rows": [
                    {
                        "dataset_name": "qm9",
                        "record_id": "a",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {"homo_lumo_gap": 5.0},
                        "property_statuses": {"homo_lumo_gap": {"status": "ok", "failure_type": None}},
                    },
                    {
                        "dataset_name": "qm9",
                        "record_id": "b",
                        "status": "error",
                        "failure_type": "verifier_tool_error",
                        "properties": {},
                        "property_statuses": {
                            "homo_lumo_gap": {"status": "error", "failure_type": "verifier_tool_error"}
                        },
                    },
                ],
            }
        )
    )
    medium_results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "medium",
                "properties": ["global_electrophilicity"],
                "rows": [
                    {
                        "dataset_name": "qm9",
                        "record_id": "c",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {"global_electrophilicity": 0.5},
                        "property_statuses": {
                            "global_electrophilicity": {"status": "ok", "failure_type": None}
                        },
                    }
                ],
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_xtb_real_dataset_distribution.py",
            "--inputs",
            str(light_results),
            str(medium_results),
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
    gap = summary["properties"]["homo_lumo_gap"]["all"]
    assert gap["count"] == 1
    assert gap["ok_count"] == 1
    assert gap["error_count"] == 1
    assert gap["error_rate"] == 0.5


def test_analyze_xtb_real_dataset_distribution_counts_partial_rows_per_property(tmp_path) -> None:
    results = tmp_path / "medium_results.json"
    output_dir = tmp_path / "analysis"
    results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "medium",
                "properties": ["global_electrophilicity", "max_f_plus_on_carbon"],
                "rows": [
                    {
                        "dataset_name": "qm9",
                        "record_id": "a",
                        "status": "partial",
                        "failure_type": "verifier_tool_error",
                        "properties": {"global_electrophilicity": 0.5},
                        "property_statuses": {
                            "global_electrophilicity": {"status": "ok", "failure_type": None},
                            "max_f_plus_on_carbon": {
                                "status": "error",
                                "failure_type": "verifier_tool_error",
                            },
                        },
                    }
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
    electrophilicity = summary["properties"]["global_electrophilicity"]["all"]
    fukui = summary["properties"]["max_f_plus_on_carbon"]["all"]
    assert electrophilicity["ok_count"] == 1
    assert electrophilicity["error_count"] == 0
    assert fukui["ok_count"] == 0
    assert fukui["error_count"] == 1
    assert fukui["error_rate"] == 1.0


def test_analyze_xtb_real_dataset_distribution_omits_helper_properties(tmp_path) -> None:
    results = tmp_path / "medium_results.json"
    output_dir = tmp_path / "analysis"
    results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "medium",
                "properties": ["alpb_water_hexane_selectivity"],
                "rows": [
                    {
                        "dataset_name": "qm9",
                        "record_id": "a",
                        "status": "ok",
                        "failure_type": None,
                        "properties": {
                            "alpb_water_hexane_selectivity": 0.2,
                            "gsolv_water_eV": -0.4,
                            "gsolv_hexane_eV": -0.2,
                        },
                    }
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
    assert set(summary["properties"]) == {"alpb_water_hexane_selectivity"}


def test_analyze_xtb_real_dataset_distribution_writes_expanded_readiness(tmp_path) -> None:
    results = tmp_path / "light_results.json"
    output_dir = tmp_path / "analysis"
    rows = [
        {
            "dataset_name": "qm9",
            "record_id": "qm9_a",
            "status": "ok",
            "failure_type": None,
            "properties": {"homo_lumo_gap": 5.0},
            "property_statuses": {"homo_lumo_gap": {"status": "ok", "failure_type": None}},
        }
    ]
    rows.extend(
        {
            "dataset_name": "qmugs",
            "record_id": f"qmugs_{index}",
            "status": "ok",
            "failure_type": None,
            "properties": {"homo_lumo_gap": 2.0 + index},
            "property_statuses": {"homo_lumo_gap": {"status": "ok", "failure_type": None}},
        }
        for index in range(120)
    )
    results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "light",
                "properties": ["homo_lumo_gap"],
                "rows": rows,
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
            "--expanded-readiness",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    readiness = json.loads((output_dir / "expanded_run_readiness.json").read_text())
    assert readiness["non_qm9_ok_records"] == 120
    assert readiness["ready_for_expanded_run"] is True
    assert readiness["property_error_rate"] == 0.0
    assert (output_dir / "expanded_run_readiness.md").read_text().startswith("# Expanded Run Readiness")


def test_analyze_xtb_real_dataset_distribution_readiness_uses_property_level_statuses(tmp_path) -> None:
    results = tmp_path / "expensive_results.json"
    output_dir = tmp_path / "analysis"
    rows = []
    for index in range(100):
        rows.append(
            {
                "dataset_name": "qmugs",
                "record_id": f"qmugs_{index}",
                "status": "partial",
                "failure_type": "domain_error",
                "properties": {"entropy_298_per_heavy_atom": 30.0},
                "property_statuses": {
                    "entropy_298_per_heavy_atom": {"status": "ok", "failure_type": None},
                    "imaginary_frequency_count": {"status": "skipped", "failure_type": "domain_skip"},
                    "homo_lumo_gap": {"status": "error", "failure_type": "domain_error"},
                },
            }
        )
    rows.append(
        {
            "dataset_name": "qmugs",
            "record_id": "runtime_failure",
            "status": "partial",
            "failure_type": "verifier_timeout",
            "properties": {},
            "property_statuses": {
                "imaginary_frequency_count": {"status": "error", "failure_type": "verifier_timeout"},
            },
        }
    )
    results.write_text(
        json.dumps(
            {
                "status": "ok",
                "tier": "expensive",
                "properties": ["entropy_298_per_heavy_atom", "imaginary_frequency_count", "homo_lumo_gap"],
                "rows": rows,
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
            "--expanded-readiness",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    readiness = json.loads((output_dir / "expanded_run_readiness.json").read_text())
    assert readiness["non_qm9_ok_records"] == 100
    assert readiness["attempted_property_count"] == 201
    assert readiness["error_property_count"] == 101
    assert readiness["hessian_runtime_failures"] == 1
    assert "hessian_runtime_or_parser_failures" in readiness["blockers"]
