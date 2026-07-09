from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchmark.evaluate import (
    aggregate_constraint_results,
    evaluate_many,
    evaluate_one,
    load_answers_jsonl,
    load_tasks,
    load_verifier_specs,
    summarize_row,
)


ROOT = Path(__file__).resolve().parents[1]
TASKS_PATH = ROOT / "tasks" / "rdkit_baseline" / "tasks.yaml"
SPECS_PATH = ROOT / "tasks" / "rdkit_baseline" / "verifier_specs.yaml"
ANSWERS_PATH = ROOT / "tasks" / "rdkit_baseline" / "sample_answers.jsonl"

FINAL_ANSWER_SCHEMA = {
    "format": "final_answer_line",
    "final_answer_prefix": "FINAL ANSWER:",
    "value_type": "smiles",
    "cardinality": "one",
}


def test_python_verifier_registry_has_been_removed() -> None:
    assert not (ROOT / "verifiers" / "registry.py").exists()


def test_legacy_atomistic_skills_verifier_module_has_been_removed() -> None:
    assert not (ROOT / "verifiers" / ("atomistic" + "skills.py")).exists()


def test_score_answers_compatibility_wrapper_has_been_removed() -> None:
    assert not (ROOT / "scripts" / "score_answers.py").exists()


def test_evaluate_one_routes_by_constraint_descriptor_verifier() -> None:
    tasks = load_tasks(TASKS_PATH)
    specs = load_verifier_specs(SPECS_PATH)
    answer = {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"}]}

    result = evaluate_one(answer, tasks, specs)

    constraint = tasks["rdkit_qed_max_001"]["constraints"][0]
    assert constraint["verifier_id"] == "rdkit_qed_v1"
    assert specs[constraint["verifier_id"]]["verification_script"].endswith("rdkit_qed.py")
    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["canonical_smiles"] == "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"
    assert result["scores"]["score"] == pytest.approx(0.8810778082204156)


def test_evaluate_one_aggregates_multi_descriptor_constraints() -> None:
    tasks = load_tasks(TASKS_PATH)
    specs = load_verifier_specs(SPECS_PATH)
    answer = {"task_id": "rdkit_qed_sa_009", "candidates": [{"smiles": "CCN(CC)CC(=O)Nc1c(C)cccc1C"}]}

    result = evaluate_one(answer, tasks, specs)

    assert result["status"] == "ok"
    assert [item["property"] for item in result["scores"]["constraint_scores"]] == ["qed", "sa_score"]
    assert set(result["properties"]) == {"qed", "sa_score"}
    assert result["scores"]["score"] == pytest.approx(0.8788835428179828)


def test_aggregate_constraint_results_applies_quality_gate_multiplier() -> None:
    task = {"task_id": "quality_task", "scoring": {"aggregation": "geometric_mean"}}
    results = [
        {
            "verifier_id": "xtb_gap_gfn2_v1",
            "canonical_smiles": None,
            "properties": {"homo_lumo_gap": 2.0},
            "scores": {
                "constraint_scores": [{"property": "homo_lumo_gap", "type": "minimize_bounded", "score": 0.8}]
            },
            "versions": {"xtb_backend": "fake"},
        },
        {
            "verifier_id": "xtb_dipole_gfn2_v1",
            "canonical_smiles": None,
            "properties": {"dipole_moment": 5.0},
            "scores": {
                "constraint_scores": [{"property": "dipole_moment", "type": "maximize_bounded", "score": 0.5}]
            },
            "versions": {"xtb_backend": "fake"},
        },
        {
            "verifier_id": "xtb_relaxation_energy_gfn2_v1",
            "canonical_smiles": None,
            "properties": {"relaxation_energy": 0.175},
            "scores": {
                "constraint_scores": [
                    {
                        "property": "relaxation_energy",
                        "type": "minimize_bounded",
                        "role": "quality_gate",
                        "score": 0.5,
                    }
                ]
            },
            "versions": {"xtb_backend": "fake"},
        },
    ]

    result = aggregate_constraint_results(task, results)

    assert result["scores"]["property_score"] == pytest.approx((0.8 * 0.5) ** 0.5)
    assert result["scores"]["geometry_quality_score"] == pytest.approx(0.5)
    assert result["scores"]["score"] == pytest.approx(((0.8 * 0.5) ** 0.5) * 0.5)


def test_aggregate_constraint_results_applies_stability_gate_multiplier() -> None:
    task = {"task_id": "hessian_task", "scoring": {"aggregation": "geometric_mean"}}
    results = [
        {
            "verifier_id": "xtb_hessian_thermo_gfn2_v1",
            "canonical_smiles": None,
            "properties": {"imaginary_frequency_count": 1},
            "scores": {
                "constraint_scores": [
                    {
                        "property": "imaginary_frequency_count",
                        "type": "window",
                        "role": "stability_gate",
                        "score": 0.25,
                    }
                ]
            },
            "versions": {"xtb_backend": "fake"},
        },
        {
            "verifier_id": "xtb_hessian_thermo_gfn2_v1",
            "canonical_smiles": None,
            "properties": {"entropy_298_per_heavy_atom": 12.0},
            "scores": {
                "constraint_scores": [
                    {
                        "property": "entropy_298_per_heavy_atom",
                        "type": "maximize_bounded",
                        "score": 0.8,
                    }
                ]
            },
            "versions": {"xtb_backend": "fake"},
        },
    ]

    result = aggregate_constraint_results(task, results)

    assert result["scores"]["property_score"] == pytest.approx(0.8)
    assert result["scores"]["stability_gate_score"] == pytest.approx(0.25)
    assert result["scores"]["score"] == pytest.approx(0.2)


def test_evaluate_one_extracts_raw_response_before_routing() -> None:
    tasks = load_tasks(TASKS_PATH)
    tasks["rdkit_qed_max_001"]["answer_schema"] = FINAL_ANSWER_SCHEMA
    specs = load_verifier_specs(SPECS_PATH)
    answer = {
        "task_id": "rdkit_qed_max_001",
        "response": "QED should be high for this candidate.\nFINAL ANSWER: COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1",
    }

    result = evaluate_one(answer, tasks, specs)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["canonical_smiles"] == "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"
    assert result["raw_answer"] == answer["response"]
    assert result["extracted_answer"] == "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"
    assert result["scores"]["score"] == pytest.approx(0.8810778082204156)


def test_evaluate_one_returns_parse_error_for_missing_final_answer_line() -> None:
    tasks = load_tasks(TASKS_PATH)
    tasks["rdkit_qed_max_001"]["answer_schema"] = FINAL_ANSWER_SCHEMA
    specs = load_verifier_specs(SPECS_PATH)
    answer = {"task_id": "rdkit_qed_max_001", "response": "I choose CCO."}

    result = evaluate_one(answer, tasks, specs)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"
    assert result["scores"]["score"] == 0.0
    assert "missing final answer line" in result["message"]


def test_summarize_row_preserves_extraction_fields_when_present() -> None:
    row = summarize_row(
        {
            "task_id": "task_1",
            "status": "ok",
            "failure_type": None,
            "canonical_smiles": "CCO",
            "raw_answer": "Reasoning\nFINAL ANSWER: CCO",
            "extracted_answer": "CCO",
            "properties": {},
            "scores": {"score": 1.0, "constraint_scores": []},
        }
    )

    assert row["raw_answer"] == "Reasoning\nFINAL ANSWER: CCO"
    assert row["extracted_answer"] == "CCO"


def test_evaluate_many_scores_sample_answers_with_summary() -> None:
    tasks = load_tasks(TASKS_PATH)
    specs = load_verifier_specs(SPECS_PATH)
    answers = load_answers_jsonl(ANSWERS_PATH)

    report = evaluate_many(answers, tasks, specs)

    assert report["summary"]["num_answers"] == 10
    assert report["summary"]["num_ok"] == 10
    assert report["summary"]["num_error"] == 0
    assert report["summary"]["min_score"] == pytest.approx(0.863812109226767)
    assert report["summary"]["max_score"] == 1.0
    assert report["summary"]["mean_score"] == pytest.approx(0.9547086473382975)
    assert len(report["rows"]) == 10


def test_unknown_task_id_returns_structured_error() -> None:
    result = evaluate_one({"task_id": "missing_task", "candidates": [{"smiles": "CCO"}]}, {}, {})

    assert result["status"] == "error"
    assert result["failure_type"] == "task_error"
    assert result["scores"]["score"] == 0.0


def test_missing_verifier_spec_returns_structured_error() -> None:
    tasks = {
        "task_1": {
            "task_id": "task_1",
            "constraints": [{"type": "window", "property": "logp", "verifier_id": "missing_logp_v1"}],
        }
    }

    result = evaluate_one({"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}, tasks, {})

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_missing_constraint_verifier_id_returns_structured_error() -> None:
    tasks = {
        "task_1": {
            "task_id": "task_1",
            "constraints": [{"type": "window", "property": "logp", "min": 1.0, "max": 3.0}],
        }
    }

    result = evaluate_one({"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}, tasks, {})

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_spec_without_verification_script_returns_structured_error() -> None:
    tasks = {
        "task_1": {
            "task_id": "task_1",
            "constraints": [{"type": "window", "property": "logp", "verifier_id": "rdkit_logp_v1"}],
        }
    }
    specs = {"rdkit_logp_v1": {"verifier_id": "rdkit_logp_v1", "descriptor": "logp"}}

    result = evaluate_one({"task_id": "task_1", "candidates": [{"smiles": "CCO"}]}, tasks, specs)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_package_score_answers_cli_default_development_paths_remain_repo_relative() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "verifier_grounded_benchmark.cli.score_answers",
            "--answers",
            str(ANSWERS_PATH),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    report = json.loads(completed.stdout)
    assert report["summary"]["num_ok"] == 10
    assert report["summary"]["num_error"] == 0


def test_package_score_answers_cli_module_accepts_track_name() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "verifier_grounded_benchmark.cli.score_answers",
            "--track",
            "rdkit",
            "--answers",
            str(ANSWERS_PATH),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    report = json.loads(completed.stdout)
    assert report["summary"]["num_answers"] == 10
    assert report["summary"]["coverage"]["complete"] is True
    assert report["summary"]["benchmark_score"] == report["summary"]["evaluated_mean_score"]


def test_package_score_answers_cli_development_overrides_resolve_scripts_from_specs_dir(
    tmp_path: Path,
) -> None:
    tasks_path = tmp_path / "tasks.yaml"
    specs_path = tmp_path / "verifier_specs.yaml"
    answers_path = tmp_path / "answers.jsonl"
    verifier_path = tmp_path / "local_verifier.py"
    tasks_path.write_text(
        """
tasks:
  - task_id: local_task_1
    constraints:
      - type: maximize
        property: local_sentinel
        verifier_id: local_verifier_v1
    scoring:
      aggregation: geometric_mean
""".lstrip()
    )
    specs_path.write_text(
        """
verifiers:
  - verifier_id: local_verifier_v1
    descriptor: local_sentinel
    verification_script: local_verifier.py
""".lstrip()
    )
    answers_path.write_text(
        json.dumps({"task_id": "local_task_1", "candidates": [{"smiles": "CCO"}]})
        + "\n"
    )
    verifier_path.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "json.dump({\n"
        "  'task_id': payload['task']['task_id'],\n"
        "  'verifier_id': payload['verifier_spec']['verifier_id'],\n"
        "  'status': 'ok',\n"
        "  'canonical_smiles': None,\n"
        "  'properties': {'local_verifier_sentinel': 'from_specs_dir'},\n"
        "  'scores': {'constraint_scores': [{'property': 'local_sentinel', 'score': 1.0}], 'score': 1.0},\n"
        "  'failure_type': None,\n"
        "  'message': None,\n"
        "  'versions': {'local_verifier': 'sentinel'}\n"
        "}, sys.stdout)\n"
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "verifier_grounded_benchmark.cli.score_answers",
            "--tasks",
            str(tasks_path),
            "--specs",
            str(specs_path),
            "--answers",
            str(answers_path),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    report = json.loads(completed.stdout)
    assert report["rows"][0]["status"] == "ok"
    assert report["rows"][0]["properties"]["local_verifier_sentinel"] == "from_specs_dir"


def test_score_answers_cli_require_complete_rejects_partial_track_answers(tmp_path: Path) -> None:
    partial_answers = tmp_path / "partial_answers.jsonl"
    partial_answers.write_text(ANSWERS_PATH.read_text().splitlines()[0] + "\n")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "verifier_grounded_benchmark.cli.score_answers",
            "--track",
            "rdkit",
            "--answers",
            str(partial_answers),
            "--require-complete",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 2
    error = json.loads(completed.stderr)
    assert error["error"] == "incomplete_submission"
    assert error["coverage"]["complete"] is False
    assert len(error["coverage"]["missing_task_ids"]) == 9


def test_evaluate_many_routes_matgl_material_tasks_with_script_specs(tmp_path: Path) -> None:
    fake_script = tmp_path / "fake_matgl_verifier.py"
    fake_script.write_text(
        "import json, sys\n"
        "payload = json.load(sys.stdin)\n"
        "prop = payload['constraint']['property']\n"
        "value = 0.987 if prop == 'bandgap' else 0.005\n"
        "json.dump({\n"
        "  'task_id': payload['task']['task_id'],\n"
        "  'verifier_id': payload['verifier_spec']['verifier_id'],\n"
        "  'status': 'ok',\n"
        "  'canonical_smiles': None,\n"
        "  'properties': {prop: value},\n"
        "  'scores': {'validity_gate': 1.0, 'domain_gate': 1.0, 'constraint_scores': [{'property': prop, 'type': 'window', 'score': 1.0}], 'property_score': 1.0, 'score': 1.0},\n"
        "  'failure_type': None,\n"
        "  'message': None,\n"
        "  'versions': {'matgl_backend': 'fake'}\n"
        "}, sys.stdout)\n"
    )
    tasks = {
        "matgl_bandgap_window_si_001": {
            "task_id": "matgl_bandgap_window_si_001",
            "version": 1,
            "object_type": "crystal_structure",
            "answer_schema": {
                "format": "final_answer_block",
                "final_answer_prefix": "FINAL ANSWER:",
                "value_type": "cif",
                "fence_language": "cif",
                "cardinality": "one",
            },
            "constraints": [{"type": "window", "property": "bandgap", "verifier_id": "matgl_bandgap_fake_v1"}],
            "scoring": {"aggregation": "geometric_mean"},
        },
        "matgl_bandgap_eform_si_003": {
            "task_id": "matgl_bandgap_eform_si_003",
            "version": 1,
            "object_type": "crystal_structure",
            "answer_schema": {
                "format": "final_answer_block",
                "final_answer_prefix": "FINAL ANSWER:",
                "value_type": "cif",
                "fence_language": "cif",
                "cardinality": "one",
            },
            "constraints": [
                {"type": "window", "property": "bandgap", "verifier_id": "matgl_bandgap_fake_v1"},
                {"type": "window", "property": "formation_energy", "verifier_id": "matgl_formation_energy_fake_v1"},
            ],
            "scoring": {"aggregation": "geometric_mean"},
        },
    }
    specs = {
        "matgl_bandgap_fake_v1": {
            "verifier_id": "matgl_bandgap_fake_v1",
            "verification_script": str(fake_script),
            "property_name": "bandgap",
        },
        "matgl_formation_energy_fake_v1": {
            "verifier_id": "matgl_formation_energy_fake_v1",
            "verification_script": str(fake_script),
            "property_name": "formation_energy",
        },
    }
    response = "FINAL ANSWER:\n```cif\ndata_Si\n```\n"
    answers = [
        {"task_id": "matgl_bandgap_window_si_001", "response": response},
        {"task_id": "matgl_bandgap_eform_si_003", "response": response},
    ]

    report = evaluate_many(answers, tasks, specs)

    assert report["summary"]["num_answers"] == 2
    assert report["summary"]["num_ok"] == 2
    assert report["summary"]["num_error"] == 0
    assert report["summary"]["mean_score"] == 1.0
    assert report["rows"][0]["constraint_scores"] == [{"property": "bandgap", "type": "window", "score": 1.0}]
    assert [item["property"] for item in report["rows"][1]["constraint_scores"]] == ["bandgap", "formation_energy"]


def test_evaluate_one_reuses_same_verifier_measurement_for_multiple_constraints(tmp_path: Path) -> None:
    counter_path = tmp_path / "counter.txt"
    fake_script = tmp_path / "fake_multi_property_verifier.py"
    fake_script.write_text(
        "import json, pathlib, sys\n"
        f"counter = pathlib.Path({str(counter_path)!r})\n"
        "count = int(counter.read_text()) if counter.exists() else 0\n"
        "counter.write_text(str(count + 1))\n"
        "payload = json.load(sys.stdin)\n"
        "prop = payload['constraint']['property']\n"
        "json.dump({\n"
        "  'task_id': payload['task']['task_id'],\n"
        "  'verifier_id': payload['verifier_spec']['verifier_id'],\n"
        "  'status': 'ok',\n"
        "  'canonical_smiles': 'CCO',\n"
        "  'properties': {'a': 6.0, 'b': 4.0},\n"
        "  'scores': {'validity_gate': 1.0, 'domain_gate': 1.0, 'constraint_scores': [{'property': prop, 'type': payload['constraint']['type'], 'score': 1.0}], 'property_score': 1.0, 'score': 1.0},\n"
        "  'failure_type': None,\n"
        "  'message': None,\n"
        "  'versions': {'fake_backend': 'v1'}\n"
        "}, sys.stdout)\n"
    )
    tasks = {
        "multi_constraint_task": {
            "task_id": "multi_constraint_task",
            "version": 1,
            "object_type": "small_molecule",
            "constraints": [
                {"type": "maximize_bounded", "property": "a", "verifier_id": "fake_multi_v1", "lower": 0.0, "upper": 10.0},
                {"type": "minimize_bounded", "property": "b", "verifier_id": "fake_multi_v1", "lower": 0.0, "upper": 10.0},
            ],
            "scoring": {"aggregation": "geometric_mean"},
        }
    }
    specs = {
        "fake_multi_v1": {
            "verifier_id": "fake_multi_v1",
            "verification_script": str(fake_script),
        }
    }

    result = evaluate_one(
        {"task_id": "multi_constraint_task", "candidates": [{"smiles": "CCO"}]},
        tasks,
        specs,
    )

    assert result["status"] == "ok"
    assert result["properties"] == {"a": 6.0, "b": 4.0}
    assert result["scores"]["constraint_scores"] == [
        {"property": "a", "type": "maximize_bounded", "score": 1.0},
        {"property": "b", "type": "minimize_bounded", "score": 0.6},
    ]
    assert counter_path.read_text() == "1"


def test_evaluate_one_runs_again_when_cached_measurement_lacks_property(tmp_path: Path) -> None:
    counter_path = tmp_path / "counter.txt"
    fake_script = tmp_path / "fake_single_property_verifier.py"
    fake_script.write_text(
        "import json, pathlib, sys\n"
        f"counter = pathlib.Path({str(counter_path)!r})\n"
        "count = int(counter.read_text()) if counter.exists() else 0\n"
        "counter.write_text(str(count + 1))\n"
        "payload = json.load(sys.stdin)\n"
        "prop = payload['constraint']['property']\n"
        "value = 6.0 if prop == 'a' else 4.0\n"
        "json.dump({\n"
        "  'task_id': payload['task']['task_id'],\n"
        "  'verifier_id': payload['verifier_spec']['verifier_id'],\n"
        "  'status': 'ok',\n"
        "  'canonical_smiles': 'CCO',\n"
        "  'properties': {prop: value},\n"
        "  'scores': {'validity_gate': 1.0, 'domain_gate': 1.0, 'constraint_scores': [{'property': prop, 'type': payload['constraint']['type'], 'score': 1.0}], 'property_score': 1.0, 'score': 1.0},\n"
        "  'failure_type': None,\n"
        "  'message': None,\n"
        "  'versions': {'fake_backend': 'v1'}\n"
        "}, sys.stdout)\n"
    )
    tasks = {
        "multi_constraint_task": {
            "task_id": "multi_constraint_task",
            "version": 1,
            "object_type": "small_molecule",
            "constraints": [
                {"type": "maximize_bounded", "property": "a", "verifier_id": "fake_multi_v1", "lower": 0.0, "upper": 10.0},
                {"type": "minimize_bounded", "property": "b", "verifier_id": "fake_multi_v1", "lower": 0.0, "upper": 10.0},
            ],
            "scoring": {"aggregation": "geometric_mean"},
        }
    }
    specs = {
        "fake_multi_v1": {
            "verifier_id": "fake_multi_v1",
            "verification_script": str(fake_script),
        }
    }

    result = evaluate_one(
        {"task_id": "multi_constraint_task", "candidates": [{"smiles": "CCO"}]},
        tasks,
        specs,
    )

    assert result["status"] == "ok"
    assert result["properties"] == {"a": 6.0, "b": 4.0}
    assert [item["property"] for item in result["scores"]["constraint_scores"]] == ["a", "b"]
    assert counter_path.read_text() == "2"
