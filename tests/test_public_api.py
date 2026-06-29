from __future__ import annotations

import pytest

import verifier_grounded_benchmark as vgb


def test_list_tracks_returns_formal_builtin_names() -> None:
    assert [track.name for track in vgb.list_tracks()] == ["rdkit", "xtb"]


def test_load_track_exposes_tasks_prompts_and_sample_answers() -> None:
    track = vgb.load_track("rdkit")

    task_ids = [task["task_id"] for task in track.tasks()]
    assert "rdkit_qed_max_001" in task_ids

    prompt = track.prompts()[0]
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


def test_load_track_rejects_unknown_track() -> None:
    with pytest.raises(KeyError, match="Unknown benchmark track|unknown track"):
        vgb.load_track("missing")
