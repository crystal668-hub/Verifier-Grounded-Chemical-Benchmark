from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.property_calculation import (
    PropertyCalculationEvaluator,
)
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.models import PropertyCalculationTaskSpec
from verifier_grounded_benchmark.task.resources import package_resource


PACK = load_task_pack(
    package_resource("property_calculation", "tasks.yaml"),
    package_resource("property_calculation", "verifier_specs.yaml"),
)
VERSIONS = {
    "package": "0.2.0",
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
        (0.0, 0.0),
        (0.1290158395, 0.5),
        (0.258031679, 1.0),
        (0.3870475185, 0.5),
        (0.516063358, 0.0),
        (0.6, 0.0),
    ],
)
def test_numeric_gold_uses_continuous_linear_decay(answer: float, expected: float) -> None:
    result = _evaluate(
        "property_calc_free_energy_001",
        {"answer": answer, "unit": "kJ/mol"},
    )

    assert result["status"] == "scored"
    assert result["scores"]["score"] == pytest.approx(expected, abs=1e-12)


def test_comparison_group_uses_minimum_and_task_uses_arithmetic_mean() -> None:
    result = _evaluate(
        "property_calc_crystal_phase_002",
        {
            "answers": [
                {"property": "potential_energy_difference", "value": 0.1185, "unit": "eV"},
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
        "property_calc_crystal_phase_002",
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
    result = _evaluate("property_calc_crystal_phase_002", {"answers": []})

    assert result["status"] == "scored"
    assert result["failure_scope"] is None
    assert result["scores"]["score"] == 0.0


def test_wrong_numeric_unit_scores_zero() -> None:
    result = _evaluate(
        "property_calc_free_energy_001",
        {"answer": 0.258031679, "unit": "eV"},
    )

    assert result["scores"]["score"] == 0.0


def test_unknown_property_is_ignored_and_recorded() -> None:
    result = _evaluate(
        "property_calc_crystal_phase_002",
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
    result = _evaluate("property_calc_crystal_phase_002", answer)

    assert result["status"] == "scored"
    assert result["failure_scope"] == "submission"
    assert result["failure_type"] == "parse_error"
    assert message in result["message"]
    assert result["scores"]["score"] == 0.0


def test_result_has_v2_schema_and_constraint_provenance() -> None:
    result = _evaluate(
        "property_calc_free_energy_001",
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
            "scoring_profile": "property_calculation_free_energy_difference_numeric_gold_v2",
            "scoring_version": "linear_goal_v2",
        }
    ]
