from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.property_calculation import (
    PropertyCalculationEvaluator,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.comparison_group import (
    score_unordered_numeric_group,
)
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.models import PropertyCalculationTaskSpec
from verifier_grounded_benchmark.task.resources import package_resource

PACK = load_task_pack(
    package_resource("property_calculation_advanced", "tasks.yaml"),
    package_resource("property_calculation_advanced", "verifier_specs.yaml"),
)
VERSIONS = {
    "package": "0.9.0",
    "task_pack": PACK.version,
    "scoring": PACK.scoring_version,
    "verifiers": {},
}


def _task(task_id: str) -> PropertyCalculationTaskSpec:
    task = next(task for task in PACK.tasks if task.task_id == task_id)
    assert isinstance(task, PropertyCalculationTaskSpec)
    return task


def _evaluate(task_id: str, answer: dict):
    return PropertyCalculationEvaluator().evaluate(
        answer,
        _task(task_id),
        PACK.scoring_profiles,
        versions=VERSIONS,
    )


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (-9.741968321, 0.0),
        (-4.741968321, 0.5),
        (0.258031679, 1.0),
        (5.258031679, 0.5),
        (10.258031679, 0.0),
        (11.0, 0.0),
    ],
)
def test_numeric_gold_uses_continuous_linear_decay(answer: float, expected: float) -> None:
    result = _evaluate(
        "property_calc_001_free_energy",
        {"answer": answer, "unit": "kJ/mol"},
    )

    assert result["status"] == "scored"
    assert result["scores"]["score"] == pytest.approx(expected, abs=1e-12)


def test_comparison_group_uses_minimum_and_task_uses_arithmetic_mean() -> None:
    result = _evaluate(
        "property_calc_002_crystal_phase",
        {
            "answers": [
                {"property": "potential_energy_difference", "value": 0.579, "unit": "eV"},
                {"property": "ambient_pressure_phase", "value": "wrong"},
                {"property": "high_pressure_phase", "value": "beta"},
            ]
        },
    )

    groups = result["scores"]["comparison_group_scores"]
    assert [group["score"] for group in groups] == pytest.approx([0.5, 0.0])
    assert result["scores"]["score"] == pytest.approx(0.25)


def test_exact_string_is_case_sensitive() -> None:
    result = _evaluate(
        "property_calc_002_crystal_phase",
        {
            "answers": [
                {"property": "potential_energy_difference", "value": 0.079, "unit": "eV"},
                {"property": "ambient_pressure_phase", "value": "Alpha"},
                {"property": "high_pressure_phase", "value": "beta"},
            ]
        },
    )

    ambient = next(
        item for item in result["scores"]["constraint_scores"]
        if item["property"] == "ambient_pressure_phase"
    )
    assert ambient["score"] == 0.0
    assert result["scores"]["score"] == 0.5


def test_missing_requested_field_scores_zero_without_infrastructure_error() -> None:
    result = _evaluate("property_calc_002_crystal_phase", {"answers": []})

    assert result["status"] == "scored"
    assert result["failure_scope"] is None
    assert result["scores"]["score"] == 0.0


def test_wrong_numeric_unit_scores_zero() -> None:
    result = _evaluate(
        "property_calc_001_free_energy",
        {"answer": 0.258031679, "unit": "eV"},
    )

    assert result["scores"]["score"] == 0.0


def test_unknown_property_is_ignored_and_recorded() -> None:
    result = _evaluate(
        "property_calc_002_crystal_phase",
        {
            "answers": [
                {"property": "potential_energy_difference", "value": 0.079, "unit": "eV"},
                {"property": "ambient_pressure_phase", "value": "alpha"},
                {"property": "high_pressure_phase", "value": "beta"},
                {"property": "not_requested", "value": 1},
            ]
        },
    )

    assert result["scores"]["score"] == 1.0
    assert result["properties"]["diagnostics"]["unknown_properties"] == ["not_requested"]


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        ({"answers": {}}, "answers must be a list"),
        (
            {
                "answers": [
                    {"property": "ambient_pressure_phase", "value": "alpha"},
                    {"property": "ambient_pressure_phase", "value": "alpha"},
                ]
            },
            "duplicate property",
        ),
    ],
)
def test_known_task_parse_failure_is_submission_zero(
    answer: dict, message: str
) -> None:
    result = _evaluate("property_calc_002_crystal_phase", answer)

    assert result["status"] == "scored"
    assert result["failure_scope"] == "submission"
    assert result["failure_type"] == "parse_error"
    assert message in result["message"]
    assert result["scores"]["score"] == 0.0


def test_result_has_v2_schema_and_constraint_provenance() -> None:
    result = _evaluate(
        "property_calc_001_free_energy",
        {"answer": 0.258031679, "unit": "kJ/mol"},
    )

    assert result["schema_version"] == 2
    assert result["versions"] == {**VERSIONS, "result_schema": "2"}
    assert result["scores"]["constraint_scores"] == [
        {
            "property": "free_energy_difference",
            "type": "numeric_gold",
            "role": "main",
            "value": 0.258031679,
            "score": 1.0,
                "scoring_profile": "property_calculation_advanced_free_energy_difference_numeric_gold_v2",
            "scoring_version": "linear_goal_v2",
        }
    ]


def test_unordered_numeric_group_uses_best_assignment() -> None:
    members = ["frequency_1", "frequency_2", "frequency_3"]
    submitted = {
        "frequency_1": {"value": 1685.5562, "unit": "cm^-1"},
        "frequency_2": {"value": 1208.1036, "unit": "cm^-1"},
        "frequency_3": {"value": 1674.0688, "unit": "cm^-1"},
    }
    gold = {
        name: {"value": value, "unit": "cm^-1", "scoring_profile": name}
        for name, value in zip(
            members, [1208.1036, 1674.0688, 1685.5562], strict=True
        )
    }
    profiles = {
        name: {
            "property": name,
            "type": "numeric_gold",
            "unit": "cm^-1",
            "lower_tolerance": 1.0,
            "upper_tolerance": 1.0,
        }
        for name in members
    }

    assert score_unordered_numeric_group(submitted, members, gold, profiles) == pytest.approx(1.0)


def test_ir_top_two_frequencies_are_scored_as_an_unordered_pair() -> None:
    result = _evaluate(
        "property_calc_004_ir_top3_frequencies",
        {
            "answers": [
                {"property": "frequency_1", "value": 1685.56, "unit": "cm^-1"},
                {"property": "frequency_2", "value": 1208.10, "unit": "cm^-1"},
            ]
        },
    )

    assert result["scores"]["score"] == pytest.approx(1.0)
    assert result["scores"]["comparison_group_scores"][0]["members"] == [
        "frequency_1",
        "frequency_2",
    ]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("1:1", 1.0), ("1:2", 0.5), ("2:1", 0.5), ("1:3", 0.0)],
)
def test_cocrystal_ratio_has_explicit_partial_credit(answer: str, expected: float) -> None:
    result = _evaluate("property_calc_006_cocrystal_ratio", {"answer": answer})

    assert result["scores"]["score"] == pytest.approx(expected)


def test_absolute_value_scoring_compares_answer_and_gold_magnitudes() -> None:
    result = _evaluate(
        "property_calc_013_halogen_bond_energy",
        {"answer": 17.11, "unit": "kcal/mol"},
    )

    assert result["scores"]["score"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (117000000.0, 1.0),
        (117000.0, 0.0),
        (117000000000.0, 0.0),
        (11700000.0, 2.0 / 3.0),
        (0.0, 0.0),
        (-117000000.0, 0.0),
    ],
)
def test_log10_scoring_uses_order_of_magnitude_distance(
    answer: float, expected: float
) -> None:
    result = _evaluate(
        "property_calc_016_anthracene_isc_rate",
        {"answer": answer, "unit": "s^-1"},
    )

    assert result["scores"]["score"] == pytest.approx(expected)


@pytest.mark.parametrize(
    ("answer", "expected"),
    [(9.8, 0.5), (98.0, 1.0), (98.0 * 10**1.5, 0.5)],
)
def test_asymmetric_log10_scoring_uses_separate_side_widths(
    answer: float, expected: float
) -> None:
    result = _evaluate(
        "property_calc_017_biacetyl_phosphorescence_rate",
        {"answer": answer, "unit": "s^-1"},
    )

    assert result["scores"]["score"] == pytest.approx(expected)


@pytest.mark.parametrize(("answer", "expected"), [(95.0, 0.5), (100.0, 1.0), (100.5, 0.5)])
def test_asymmetric_linear_scoring_uses_separate_side_widths(
    answer: float, expected: float
) -> None:
    result = _evaluate(
        "property_calc_018_anthracene_ht_contribution",
        {"answer": answer, "unit": "percent"},
    )

    assert result["scores"]["score"] == pytest.approx(expected)
