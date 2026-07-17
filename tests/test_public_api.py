from __future__ import annotations

from pathlib import Path

import pytest

import verifier_grounded_benchmark as vgb


def test_list_tracks_returns_formal_builtin_names() -> None:
    assert [track.name for track in vgb.list_tracks()] == [
        "rdkit",
        "xtb",
        "property_calculation",
    ]


def test_vgb_alias_exposes_same_public_api() -> None:
    import vgb as short_vgb

    assert [definition.name for definition in short_vgb.list_tracks()] == [
        "rdkit",
        "xtb",
        "property_calculation",
    ]
    assert short_vgb.load_track("rdkit").name == "rdkit"


def test_load_track_exposes_tasks_prompts_and_sample_answers() -> None:
    track = vgb.load_track("rdkit")

    task_ids = [task["task_id"] for task in track.tasks()]
    assert "rdkit_qed_max_001" in task_ids

    prompt = next(
        prompt
        for prompt in track.prompts()
        if prompt["task_id"] == "rdkit_qed_max_001"
    )
    assert prompt["track"] == "rdkit"
    assert prompt["task_id"] == "rdkit_qed_max_001"
    assert prompt["prompt"].startswith(
        "Propose one valid single-component molecule"
    )
    assert prompt["answer_schema"] == track.task("rdkit_qed_max_001")["answer_schema"]
    assert set(prompt) == {"track", "task_id", "prompt", "answer_schema"}
    assert len(track.sample_answers()) == 11


def test_load_suite_defaults_to_formal_tracks_only() -> None:
    suite = vgb.load_suite()
    task_ids = [task["task_id"] for task in suite.tasks()]

    assert "rdkit_qed_max_001" in task_ids
    assert "xtb_gap_window_001" in task_ids
    assert "property_calc_free_energy_001" in task_ids
    assert "property_calc_crystal_phase_002" in task_ids
    assert not any(task_id.startswith("matgl_") for task_id in task_ids)
    assert not any(task_id.startswith("mace_") for task_id in task_ids)
    assert not any(task_id.startswith("atomistic" + "skills_") for task_id in task_ids)


def test_builtin_track_uses_importable_module_executors() -> None:
    import importlib.util

    for track_name in ("rdkit", "xtb"):
        specs = vgb.load_track(track_name).verifier_specs_by_id
        modules = [
            spec["executor"]["module"]
            for spec in specs.values()
        ]

        assert modules
        assert all(importlib.util.find_spec(module) is not None for module in modules)

    assert vgb.load_track("property_calculation").verifier_specs_by_id == {}


def test_property_calculation_track_scores_public_samples() -> None:
    track = vgb.load_track("property_calculation")

    report = track.evaluate_answers(track.sample_answers())

    assert len(track.tasks()) == 2
    assert len(track.sample_answers()) == 2
    assert report["summary"]["coverage"]["complete"] is True
    assert report["summary"]["benchmark_score"] == 1.0
    assert [row["score"] for row in report["rows"]] == [1.0, 1.0]


def test_load_track_rejects_unknown_track() -> None:
    with pytest.raises(KeyError, match="Unknown benchmark track|unknown track"):
        vgb.load_track("missing")


def test_track_evaluate_answers_uses_v2_result_and_scoring_contract() -> None:
    track = vgb.load_track("rdkit")
    report = track.evaluate_answers(track.sample_answers())

    assert report["summary"]["coverage"]["complete"] is True
    assert all(row["schema_version"] == 2 for row in report["rows"])
    assert all(row["status"] == "scored" for row in report["rows"])
    assert all(
        item["scoring_version"] == "linear_goal_v1"
        for row in report["rows"]
        for item in row["constraint_scores"]
    )


def test_track_evaluate_answers_reports_partial_coverage() -> None:
    track = vgb.load_track("rdkit")
    answers = track.sample_answers()[:2]

    report = track.evaluate_answers(answers)

    coverage = report["summary"]["coverage"]
    assert coverage["num_tasks_total"] == 11
    assert coverage["num_rows_submitted"] == 2
    assert coverage["num_task_ids_submitted"] == 2
    assert coverage["num_tasks_answered"] == 2
    assert coverage["duplicate_task_ids"] == []
    assert coverage["unknown_task_ids"] == []
    assert coverage["complete"] is False
    assert len(coverage["missing_task_ids"]) == 9
    assert report["summary"]["evaluated_mean_score"] == report["summary"]["mean_score"]
    assert report["summary"]["benchmark_score"] is None


def test_track_evaluate_answers_reports_complete_benchmark_score() -> None:
    track = vgb.load_track("rdkit")

    report = track.evaluate_answers(track.sample_answers())

    coverage = report["summary"]["coverage"]
    assert coverage["complete"] is True
    assert coverage["missing_task_ids"] == []
    assert coverage["duplicate_task_ids"] == []
    assert coverage["unknown_task_ids"] == []
    assert report["summary"]["benchmark_score"] == report["summary"]["evaluated_mean_score"]


def test_track_evaluate_answers_coverage_detects_duplicate_and_unknown_task_ids() -> None:
    track = vgb.load_track("rdkit")
    answers = [
        track.sample_answers()[0],
        track.sample_answers()[0],
        {"task_id": "missing_from_track", "candidates": [{"smiles": "CCO"}]},
    ]

    report = track.evaluate_answers(answers)

    coverage = report["summary"]["coverage"]
    assert coverage["num_rows_submitted"] == 3
    assert coverage["num_task_ids_submitted"] == 2
    assert coverage["num_tasks_answered"] == 1
    assert coverage["duplicate_task_ids"] == ["rdkit_qed_max_001"]
    assert coverage["unknown_task_ids"] == ["missing_from_track"]
    assert coverage["complete"] is False
    assert report["summary"]["benchmark_score"] is None


def test_track_evaluate_one_returns_structured_xtb_parse_error() -> None:
    result = vgb.load_track("xtb").evaluate_one(
        {"task_id": "xtb_gap_window_001", "candidates": [{}]}
    )

    assert result["status"] == "scored"
    assert result["task_id"] == "xtb_gap_window_001"
    assert result["failure_type"] == "parse_error"
    assert result["failure_scope"] == "candidate"
    assert result["message"] == "candidate must include an XYZ string"


def test_suite_evaluate_one_routes_by_task_id() -> None:
    result = vgb.load_suite(["rdkit", "xtb"]).evaluate_one(
        {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}
    )

    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["status"] == "scored"
    assert result["failure_type"] == "domain_error"
    assert result["scores"]["score"] == 0.0


def test_evaluation_report_wrapper_serializes_rows() -> None:
    report = vgb.EvaluationReport(
        summary={"num_answers": 1},
        rows=[{"task_id": "task_1", "score": 0.5}],
    )

    assert report.to_dict() == {
        "summary": {"num_answers": 1},
        "rows": [{"task_id": "task_1", "score": 0.5}],
    }
    assert report.to_json() == (
        '{\n'
        '  "rows": [\n'
        "    {\n"
        '      "score": 0.5,\n'
        '      "task_id": "task_1"\n'
        "    }\n"
        "  ],\n"
        '  "summary": {\n'
        '    "num_answers": 1\n'
        "  }\n"
        "}"
    )
    assert report.to_jsonl_rows() == '{"score": 0.5, "task_id": "task_1"}'


def test_track_evaluate_answers_can_return_report() -> None:
    report = vgb.load_track("rdkit").evaluate_answers([], as_report=True)

    assert isinstance(report, vgb.EvaluationReport)
    assert report.summary["num_answers"] == 0
    assert report.rows == []
