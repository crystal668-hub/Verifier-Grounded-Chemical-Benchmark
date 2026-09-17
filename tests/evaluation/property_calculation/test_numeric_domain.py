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
        package_resource("property_calculation_advanced", "verifier_specs.yaml"),
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
        "oh_bond_distance",
        "h_o_contact_distance",
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


def test_domain_is_checked_before_absolute_transform(advanced):
    gold, profile = field(advanced, "oh_bond_distance")
    profile["value_transform"] = "absolute"
    assert score_numeric_gold({"value": -gold["value"], "unit": gold["unit"]}, gold, profile) == 0


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
    assert result["scores"]["score"] == pytest.approx(2 / 3)


@pytest.mark.parametrize("property_name", ["interaction_energy", "binding_energy", "halogen_bond_interaction_energy"])
def test_energy_sign_conventions_receive_identical_credit(advanced, property_name):
    gold, profile = field(advanced, property_name)
    for offset, expected in ((0, 1), (profile["upper_tolerance"] / 2, 0.5)):
        magnitude = abs(gold["value"]) + offset
        for sign in (-1, 1):
            assert score_numeric_gold(
                {"value": sign * magnitude, "unit": gold["unit"]}, gold, profile
            ) == pytest.approx(expected)


def test_energy_prompts_do_not_require_a_sign(advanced):
    for task in advanced.tasks:
        if task.task_id.split("_")[3] in {"008", "013"}:
            prompt = task.raw["prompt"].lower()
            assert "preserve its sign" not in prompt
            assert "preserving their signs" not in prompt


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
        package_resource("property_calculation_basic", "verifier_specs.yaml"),
    )
    gold, profile = field(basic, "spin_density")
    assert gold["value"] < 0
    assert score_numeric_gold(gold, gold, profile) == 1
