from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.evaluate import (
    evaluate_many,
    load_answers_jsonl,
    load_tasks,
    load_verifier_specs,
)
import verifier_grounded_benchmark as vgb


def test_list_tracks_returns_formal_builtin_names() -> None:
    assert [track.name for track in vgb.list_tracks()] == ["rdkit", "xtb"]


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
    assert len(track.sample_answers()) == 10


def test_load_suite_defaults_to_formal_tracks_only() -> None:
    suite = vgb.load_suite()
    task_ids = [task["task_id"] for task in suite.tasks()]

    assert "rdkit_qed_max_001" in task_ids
    assert "xtb_gap_window_001" in task_ids
    assert not any(task_id.startswith("matgl_") for task_id in task_ids)
    assert not any(task_id.startswith("mace_") for task_id in task_ids)


def test_builtin_track_materialized_verifier_scripts_exist() -> None:
    for track_name in ("rdkit", "xtb"):
        specs = vgb.load_track(track_name).verifier_specs_by_id
        scripts = [
            spec["verification_script"]
            for spec in specs.values()
            if spec.get("verification_script")
        ]

        assert scripts
        assert all(Path(script).exists() for script in scripts)


def test_load_track_rejects_unknown_track() -> None:
    with pytest.raises(KeyError, match="Unknown benchmark track|unknown track"):
        vgb.load_track("missing")


def test_track_evaluate_answers_matches_existing_rdkit_summary() -> None:
    track = vgb.load_track("rdkit")
    definition = track.definition
    legacy_tasks = load_tasks(definition.resolve_path(definition.task_pack_path))
    legacy_specs = load_verifier_specs(
        definition.resolve_path(definition.verifier_specs_path)
    )
    legacy_answers = load_answers_jsonl(
        definition.resolve_path(definition.sample_answers_path)
    )

    assert track.sample_answers() == legacy_answers
    assert track.evaluate_answers(track.sample_answers()) == evaluate_many(
        legacy_answers,
        legacy_tasks,
        legacy_specs,
    )


def test_track_evaluate_one_returns_structured_xtb_parse_error() -> None:
    result = vgb.load_track("xtb").evaluate_one(
        {"task_id": "xtb_gap_window_001", "candidates": [{}]}
    )

    assert result["status"] == "error"
    assert result["task_id"] == "xtb_gap_window_001"
    assert result["failure_type"] == "parse_error"
    assert result["message"] == "candidate must include an XYZ string"


def test_suite_evaluate_one_routes_by_task_id() -> None:
    result = vgb.load_suite(["rdkit", "xtb"]).evaluate_one(
        {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}
    )

    assert result["task_id"] == "rdkit_qed_max_001"
    assert result["status"] in {"ok", "error"}
    if result["status"] == "error":
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
