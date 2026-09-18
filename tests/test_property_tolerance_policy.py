"""Scientific scoring contracts for the answer-independent family policy."""

from __future__ import annotations

import csv
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from verifier_grounded_benchmark.evaluation.property_calculation.scoring.numeric_gold import (
    score_numeric_gold,
)
from verifier_grounded_benchmark.task.loader import load_task_pack

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/research/2026-09-17-property-tolerance-policy"
spec = importlib.util.spec_from_file_location(
    "family_projection", DIRECTORY / "project_scores.py"
)
projection = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = projection
spec.loader.exec_module(projection)
POLICY = yaml.safe_load((DIRECTORY / "family_policy.yaml").read_text(encoding="utf-8"))
POST_R2_TASK_SCORING_OVERRIDES = {
    "property_calculation_advanced_002_crystal_phase": {
        "aggregation": "arithmetic_mean",
        "comparison_groups": [
            {
                "id": "energy",
                "aggregation": "arithmetic_mean",
                "properties": ["potential_energy_difference"],
            },
            {
                "id": "phase",
                "aggregation": "all_correct",
                "properties": [
                    "ambient_pressure_phase",
                    "high_pressure_phase",
                ],
            },
        ],
        "version": "linear_goal_v2",
    }
}


@pytest.fixture(scope="module")
def sources():
    return {
        track: projection.baseline_scoring(track)
        for track in projection.original.SOURCES
    }


def numeric_fields(scoring):
    for task in scoring["tasks"]:
        for gold in task["gold_answers"]:
            profile = scoring["scoring_profiles"][gold["scoring_profile"]]
            if profile["type"] == "numeric_gold":
                yield gold, profile


def test_policy_covers_every_numeric_field_and_preserves_gold_and_semantics(sources):
    before = deepcopy(sources)
    numeric_count = 0
    for source in sources.values():
        candidate = projection.candidate_scoring(source, POLICY)
        assert candidate["tasks"] == source["tasks"]
        for profile_id, old in source["scoring_profiles"].items():
            new = candidate["scoring_profiles"][profile_id]
            if old["type"] != "numeric_gold":
                assert new == old
            else:
                assert new.get("value_transform") == old.get("value_transform")
                assert new.get("minimum_value") == old.get("minimum_value")
        for gold, profile in numeric_fields(candidate):
            numeric_count += 1
            assert score_numeric_gold(gold, gold, profile) == 1
    assert numeric_count == 71
    assert sources == before


def test_same_family_has_same_scoring_accuracy_across_both_tracks(sources):
    observed = {}
    for source in sources.values():
        for gold, profile in numeric_fields(
            projection.candidate_scoring(source, POLICY)
        ):
            family = profile["provenance"]["tolerance_family"]
            scale = abs(gold["value"]) if profile["error_mode"] == "relative" else 1
            accuracy = (
                profile["lower_tolerance"] / scale,
                profile["upper_tolerance"] / scale,
            )
            if family in observed:
                assert accuracy == pytest.approx(observed[family])
            observed[family] = accuracy
            center = (
                abs(gold["value"])
                if profile.get("value_transform") == "absolute"
                else gold["value"]
            )
            for fraction, expected in ((0.1, 0.9), (0.5, 0.5), (1, 0)):
                for side, sign in (("lower", -1), ("upper", 1)):
                    error = sign * fraction * profile[f"{side}_tolerance"]
                    value = (
                        center * 10**error
                        if profile.get("value_transform") == "log10"
                        else center + error
                    )
                    domain_expected = (
                        0
                        if value < profile.get("minimum_value", -float("inf"))
                        else expected
                    )
                    assert score_numeric_gold(
                        {"value": value, "unit": gold["unit"]}, gold, profile
                    ) == pytest.approx(domain_expected, abs=1e-12)
    assert observed["noncovalent_energy"] == (1, 1)
    assert observed["density"] == pytest.approx((0.1, 0.1))
    assert observed["vertical_excitation_energy"] == (0.5, 0.5)
    assert observed["wiberg_bond_order"] == (0.2, 0.2)
    assert observed["standard_entropy"] == pytest.approx((0.1, 0.1))
    assert observed["crystal_free_energy_difference"] == (8, 8)
    assert observed["crystal_potential_energy_difference"] == (0.8, 0.8)
    assert observed["geometric_distance"] == (0.2, 0.2)
    assert observed["excited_state_rate"] == (2, 2)


def test_task_identity_and_order_cannot_influence_tolerances(sources):
    for source in sources.values():
        renamed = deepcopy(source)
        renamed["tasks"].reverse()
        for i, task in enumerate(renamed["tasks"]):
            task["task_id"] = f"unseen_task_{i}"
        assert (
            projection.candidate_scoring(renamed, POLICY)["scoring_profiles"]
            == projection.candidate_scoring(source, POLICY)["scoring_profiles"]
        )


def test_policy_fails_closed_for_unknown_properties_and_overlapping_families(sources):
    unknown = deepcopy(sources["property_calculation_basic"])
    unknown["tasks"][0]["gold_answers"][0]["property"] = "new_property"
    with pytest.raises(ValueError, match="No family rule"):
        projection.candidate_scoring(unknown, POLICY)
    overlapping = deepcopy(POLICY)
    overlapping["families"]["duplicate"] = deepcopy(overlapping["families"]["density"])
    with pytest.raises(ValueError, match="Overlapping family selectors"):
        projection.index_rules(overlapping)


@pytest.mark.parametrize(
    ("property_name", "width"),
    [("free_energy_difference", 8.0), ("potential_energy_difference", 0.8)],
)
def test_absolute_differences_score_zero_normally_but_reject_negatives(
    sources, property_name, width
):
    candidate = projection.candidate_scoring(
        sources["property_calculation_advanced"], POLICY
    )
    gold, profile = next(
        (gold, profile)
        for gold, profile in numeric_fields(candidate)
        if gold["property"] == property_name
    )
    assert profile["error_mode"] == "absolute"
    assert profile["lower_tolerance"] == profile["upper_tolerance"] == width
    assert profile["minimum_value"] == 0
    for value in (-1e-12, -gold["value"], -width):
        assert (
            score_numeric_gold({"value": value, "unit": gold["unit"]}, gold, profile)
            == 0
        )
    for value in (0, 0.5 * gold["value"], 1.5 * gold["value"]):
        assert score_numeric_gold(
            {"value": value, "unit": gold["unit"]}, gold, profile
        ) == pytest.approx(1 - abs(value - gold["value"]) / width)


def test_absolute_difference_widths_are_independent_of_gold_magnitude(sources):
    source = deepcopy(sources["property_calculation_advanced"])
    original = projection.candidate_scoring(source, POLICY)
    for gold, _ in numeric_fields(source):
        if gold["property"] in {
            "free_energy_difference",
            "potential_energy_difference",
        }:
            gold["value"] *= 10
    changed = projection.candidate_scoring(source, POLICY)
    assert changed["scoring_profiles"] == original["scoring_profiles"]


def test_export_needs_no_answer_workbooks_and_loads_as_shadow_scoring(tmp_path):
    summary = projection.run(None, tmp_path)
    assert summary["parameters_fit_to_answers"] is False
    assert summary["tracks"] == {}
    for track in projection.original.SOURCES:
        directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
        scoring_path = tmp_path / f"{track}.scoring.yaml"
        pack = load_task_pack(
            directory / "tasks.yaml", directory / "verifier_specs.yaml", scoring_path
        )
        config = yaml.safe_load(scoring_path.read_text())
        assert config["scoring_config"]["scoring_status"] == "shadow_pending_research"
        assert len(pack.tasks) == (51 if track.endswith("basic") else 20)


def test_committed_candidate_configs_match_the_frozen_family_policy(sources):
    for track, source in sources.items():
        stored = yaml.safe_load((DIRECTORY / f"{track}.scoring.yaml").read_text())
        assert stored == projection.candidate_scoring(source, POLICY)


@pytest.mark.parametrize("track", projection.original.SOURCES)
def test_formal_release_preserves_every_approved_r2_scoring_field(track):
    directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
    formal = yaml.safe_load((directory / "scoring.yaml").read_text())
    frozen = yaml.safe_load((DIRECTORY / f"{track}.scoring.yaml").read_text())
    assert formal["scoring_config"]["scoring_status"] == "formal"
    assert formal["scoring_config"]["task_pack_version"] == "0.9.3"
    released_tasks = deepcopy(formal["tasks"])
    frozen_tasks = {task["task_id"]: task for task in frozen["tasks"]}
    for task in released_tasks:
        override = POST_R2_TASK_SCORING_OVERRIDES.get(task["task_id"])
        if override is not None:
            assert task["scoring"] == override
            task["scoring"] = frozen_tasks[task["task_id"]]["scoring"]
    assert released_tasks == frozen["tasks"]
    assert formal["scoring_profiles"].keys() == frozen["scoring_profiles"].keys()
    for profile_id, approved in frozen["scoring_profiles"].items():
        released = formal["scoring_profiles"][profile_id]
        assert {k: v for k, v in released.items() if k != "provenance"} == {
            k: v for k, v in approved.items() if k != "provenance"
        }
        assert released["provenance"]["review_status"] == "approved"
        if released["type"] == "numeric_gold":
            assert released["provenance"]["tolerance_policy"] == POLICY["policy_id"]
            assert (
                released["provenance"]["calibration_status"]
                == approved["provenance"]["review_status"]
            )


@pytest.mark.parametrize("track", projection.original.SOURCES)
def test_formal_release_reproduces_approved_r2_answer_scores(track):
    workbook = (
        ROOT / "review_system/data/shared-files" / projection.original.SOURCES[track]
    )
    if not workbook.exists():
        pytest.skip("Private source workbook is not part of the repository")
    directory = ROOT / "src/verifier_grounded_benchmark/task/packs" / track
    pack = load_task_pack(
        directory / "tasks.yaml",
        directory / "verifier_specs.yaml",
        DIRECTORY / f"{track}.scoring.yaml",
    )
    with (DIRECTORY / "task_scores.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        expected = {row["task_id"]: row for row in csv.DictReader(handle)}
    for observation in projection.original.read_observations(workbook, pack):
        scores, _ = projection.original.evaluate(pack, observation)
        assert (scores * 100).tolist() == pytest.approx(
            [
                float(expected[observation.task.task_id][f"family_{group}"])
                for group in projection.original.GROUPS
            ],
            abs=1e-10,
        )
