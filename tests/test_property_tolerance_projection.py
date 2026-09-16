"""Regression checks for the offline experiment's scoring and data contracts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from verifier_grounded_benchmark.task.loader import load_task_pack

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "docs/research/2026-09-16-property-tolerance-projection/project_scores.py"
)
spec = importlib.util.spec_from_file_location("property_tolerance_projection", SCRIPT)
projection = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = projection
spec.loader.exec_module(projection)


@pytest.fixture(scope="module")
def advanced():
    directory = (
        ROOT
        / "src/verifier_grounded_benchmark/task/packs/property_calculation_advanced"
    )
    return load_task_pack(directory / "tasks.yaml", directory / "verifier_specs.yaml")


def observation(pack, prefix, answers):
    task = next(task for task in pack.tasks if task.task_id.startswith(prefix))
    return projection.Observation(task, answers, np.zeros(4), 1)


def test_projection_changes_only_numeric_widths_and_preserves_frozen_profiles(advanced):
    before = {key: dict(value) for key, value in advanced.scoring_profiles.items()}
    task = advanced.tasks[1]  # mixed numeric/string crystal phase task
    candidate = projection.profiles_at_scale(advanced, task, 3.0)
    changed = []
    for key, old in before.items():
        fields = {field for field in old if old[field] != candidate[key][field]}
        if fields:
            changed.append(key)
            assert fields == {"lower_tolerance", "upper_tolerance"}
            assert candidate[key]["lower_tolerance"] == old["lower_tolerance"] * 3
            assert candidate[key]["upper_tolerance"] == old["upper_tolerance"] * 3
    assert len(changed) == 1
    assert before == {
        key: dict(value) for key, value in advanced.scoring_profiles.items()
    }


def test_missing_wrong_unit_and_nonpositive_log_answers_stay_zero(advanced):
    item = observation(
        advanced,
        "property_calculation_advanced_020",
        [
            {},
            {"answer": 0, "unit": "s^-1"},
            {"answer": 382000000, "unit": "wrong"},
            {"answer": 382000000, "unit": "s^-1"},
        ],
    )
    for scale in (0.1, 1, 10):
        scores, _ = projection.evaluate(advanced, item, scale)
        assert scores.tolist() == [0.0, 0.0, 0.0, 1.0]


def test_floor_is_widened_and_selection_is_invariant_to_model_order(advanced):
    item = observation(
        advanced,
        "property_calculation_advanced_009",
        [{"answer": value, "unit": "eV"} for value in (3.5588, 3.5592, 3.5845, 3.584)],
    )
    category, options = projection.candidate_options(advanced, item)
    assert category == "numeric_floor"
    scale, score = projection.select_option(options, 0.003)
    assert scale > 1
    assert np.min(score) > 0
    assert np.mean(score) >= 0.2
    reversed_options = [(factor, values[::-1]) for factor, values in options]
    assert projection.select_option(reversed_options, 0.003)[0] == scale


def test_holdout_answers_do_not_change_fitted_tolerance(advanced):
    def make(values):
        return observation(
            advanced,
            "property_calculation_advanced_001",
            [{"answer": value, "unit": "kJ/mol"} for value in values],
        )

    first = make([0.08, 0.258, 0.1, 0.258])
    second = make([0.08, 1000, 0.1, -1000])
    training = (0, 2)
    selected = [
        projection.select_option(
            projection.candidate_options(advanced, item, training)[1], 0.03, training
        )[0]
        for item in (first, second)
    ]
    assert selected[0] == selected[1]


@pytest.mark.parametrize("track", projection.SOURCES)
def test_supplied_workbooks_reproduce_all_published_scores(track):
    source = ROOT / "review_system/data/shared-files" / projection.SOURCES[track]
    if not source.exists():
        pytest.skip("Private source workbook is not part of the repository")
    directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
    pack = load_task_pack(directory / "tasks.yaml", directory / "verifier_specs.yaml")
    before = projection.sha256(directory / "scoring.yaml")
    items = projection.read_observations(source, pack)
    assert len(items) == (51 if track.endswith("basic") else 20)
    for item in items:
        actual, _ = projection.evaluate(pack, item)
        assert actual == pytest.approx(item.recorded, abs=5.1e-7)
    assert projection.sha256(directory / "scoring.yaml") == before
