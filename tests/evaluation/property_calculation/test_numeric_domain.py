from __future__ import annotations

from copy import deepcopy

import pytest

from verifier_grounded_benchmark.evaluation.property_calculation import (
    PropertyCalculationEvaluator,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.numeric_gold import (
    score_numeric_gold,
)
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource
from verifier_grounded_benchmark.task.schema.common import validate_profiles
from verifier_grounded_benchmark.task.schema.property_calculation import (
    validate_property_calculation_task,
)


@pytest.fixture(scope="module")
def advanced():
    return load_task_pack(
        package_resource("property_calculation_advanced", "tasks.yaml"),
        None,
    )


def field(pack, property_name):
    for task in pack.tasks:
        for gold in task.raw["gold_answers"]:
            if gold["property"] == property_name:
                return gold, dict(pack.scoring_profiles[gold["scoring_profile"]])
    raise AssertionError(f"Missing test property: {property_name}")


@pytest.mark.parametrize(
    "property_name",
    [
        "free_energy_difference",
        "potential_energy_difference",
        "accessible_to_inaccessible_volume_ratio",
        "carboxyl_hydrogen_distance",
    ],
)
def test_nonnegative_domains_hold_even_when_tolerances_are_widened(advanced, property_name):
    gold, profile = field(advanced, property_name)
    for width in (profile["lower_tolerance"], 10000.0):
        profile.update(lower_tolerance=width, upper_tolerance=width)
        for value in (-float(gold["value"]), -0.1, -1e-12):
            assert score_numeric_gold({"value": value, "unit": gold["unit"]}, gold, profile) == 0
        assert score_numeric_gold({"value": 0.0, "unit": gold["unit"]}, gold, profile) == pytest.approx(
            max(0.0, 1 - gold["value"] / width)
        )
        assert score_numeric_gold(gold, gold, profile) == 1


def test_invalid_crystal_difference_does_not_erase_correct_phase_fields(advanced):
    task = advanced.tasks[1]
    answers = [{key: gold[key] for key in ("property", "value", "unit") if key in gold}
               for gold in task.raw["gold_answers"]]
    answers[0]["value"] = -0.1
    result = PropertyCalculationEvaluator().evaluate(
        {"answers": answers}, task, advanced.scoring_profiles,
        versions={"scoring": advanced.scoring_version},
    )
    assert [item["score"] for item in result["scores"]["constraint_scores"]] == [0, 1, 1]
    assert result["scores"]["score"] == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("property_name", "width"),
    [
        ("interaction_energy", 10.0),
        ("binding_energy", 10.0),
        ("oh_bond_distance", 0.1),
        ("h_o_contact_distance", 0.1),
        ("halogen_bond_interaction_energy", 5.0),
    ],
)
def test_selected_advanced_fields_score_magnitudes_at_new_boundaries(advanced, property_name, width):
    gold, profile = field(advanced, property_name)
    assert profile["value_transform"] == "absolute"
    assert "minimum_value" not in profile
    assert profile["lower_tolerance"] == profile["upper_tolerance"] == width
    assert profile["error_parameter"] == width
    for side in (-1, 1):
        for fraction, expected in ((0, 1), (0.5, 0.5), (1, 0), (1.01, 0)):
            magnitude = abs(gold["value"]) + side * fraction * width
            for sign in (-1, 1):
                answer = {"value": sign * magnitude, "unit": gold["unit"]}
                assert score_numeric_gold(answer, gold, profile) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("number", ["008", "010", "013"])
def test_selected_advanced_tasks_accept_opposite_sign_answers_end_to_end(advanced, number):
    task = next(task for task in advanced.tasks if task.task_id.split("_")[3] == number)
    answers = [
        {"property": gold["property"], "value": -gold["value"], "unit": gold["unit"]}
        for gold in task.raw["gold_answers"]
    ]
    result = PropertyCalculationEvaluator().evaluate(
        {"answers": answers}, task, advanced.scoring_profiles,
        versions={"scoring": advanced.scoring_version},
    )
    assert result["scores"]["score"] == 1


def test_energy_prompts_accept_either_sign_and_pore_prompt_specifies_probe(advanced):
    for task in advanced.tasks:
        number = task.task_id.split("_")[3]
        if number in {"008", "013"}:
            assert "preserve the sign of the energy" not in task.raw["prompt"].lower()
        if number == "011":
            assert "spherical probe radius of 1.2 angstrom" in task.raw["prompt"]


@pytest.mark.parametrize("bound", [True, None, "0", float("nan"), float("inf"), -float("inf")])
def test_minimum_value_requires_a_finite_numeric_bound(advanced, bound):
    _, profile = field(advanced, "potential_energy_difference")
    profile["minimum_value"] = bound
    with pytest.raises(ValueError, match="minimum_value must be a finite number"):
        validate_profiles({"test": profile})


def test_minimum_value_is_not_silently_accepted_for_categorical_profiles(advanced):
    _, profile = field(advanced, "ambient_pressure_phase")
    profile["minimum_value"] = 0
    with pytest.raises(ValueError, match="minimum_value is only supported for numeric_gold"):
        validate_profiles({"test": profile})


def test_gold_must_satisfy_its_original_value_domain(advanced):
    task = deepcopy(dict(advanced.tasks_by_id["property_calculation_advanced_001_free_energy"]))
    task["gold_answers"][0]["value"] = -0.1
    with pytest.raises(ValueError, match="numeric gold free_energy_difference is below minimum_value"):
        validate_property_calculation_task(task, advanced.scoring_profiles)


def test_signed_spin_density_keeps_its_negative_gold():
    basic = load_task_pack(
        package_resource("property_calculation_basic", "tasks.yaml"),
        None,
    )
    gold, profile = field(basic, "spin_density")
    assert gold["value"] < 0
    assert score_numeric_gold(gold, gold, profile) == 1
