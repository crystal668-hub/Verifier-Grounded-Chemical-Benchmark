from __future__ import annotations

import math

import pytest

from benchmark.property_calculation import evaluate_property_calculation


TASK_7 = {
    "task_id": "property_calc_free_energy_001",
    "task_type": "property_calculation",
    "requested_properties": [
        {
            "name": "free_energy_difference",
            "value_type": "number",
            "unit": "kJ/mol",
            "comparison_group": "free_energy_difference",
        }
    ],
    "gold_answers": [
        {
            "property": "free_energy_difference",
            "value": 0.258031679,
            "unit": "kJ/mol",
            "absolute_tolerance": 0.001,
        }
    ],
    "scoring": {
        "aggregation": "arithmetic_mean",
        "comparison_groups": [{"id": "free_energy_difference", "mode": "all"}],
    },
}

TASK_8 = {
    "task_id": "property_calc_crystal_phase_002",
    "task_type": "property_calculation",
    "requested_properties": [
        {
            "name": "potential_energy_difference",
            "value_type": "number",
            "unit": "eV",
            "comparison_group": "potential_energy_difference",
        },
        {
            "name": "ambient_pressure_phase",
            "value_type": "string",
            "comparison_group": "pressure_phase_assignment",
        },
        {
            "name": "high_pressure_phase",
            "value_type": "string",
            "comparison_group": "pressure_phase_assignment",
        },
    ],
    "gold_answers": [
        {
            "property": "potential_energy_difference",
            "value": 0.079,
            "unit": "eV",
            "absolute_tolerance": 0.001,
        },
        {"property": "ambient_pressure_phase", "value": "alpha"},
        {"property": "high_pressure_phase", "value": "beta"},
    ],
    "scoring": {
        "aggregation": "arithmetic_mean",
        "comparison_groups": [
            {"id": "potential_energy_difference", "mode": "all"},
            {"id": "pressure_phase_assignment", "mode": "all"},
        ],
    },
}


def single_answer(value: object, unit: object = "kJ/mol") -> dict:
    return {"task_id": TASK_7["task_id"], "answer": value, "unit": unit}


def multi_answer(
    *,
    value: object = 0.079,
    unit: object = "eV",
    ambient: object = "alpha",
    high_pressure: object = "beta",
    include_numeric: bool = True,
    include_ambient: bool = True,
    include_high_pressure: bool = True,
) -> dict:
    answers: list[dict] = []
    if include_numeric:
        answers.append(
            {
                "property": "potential_energy_difference",
                "value": value,
                "unit": unit,
            }
        )
    if include_ambient:
        answers.append({"property": "ambient_pressure_phase", "value": ambient})
    if include_high_pressure:
        answers.append({"property": "high_pressure_phase", "value": high_pressure})
    return {"task_id": TASK_8["task_id"], "answers": answers}


@pytest.mark.parametrize(
    "value",
    [0.258031679, 0.257031679, 0.259031679],
)
def test_single_property_accepts_gold_and_tolerance_boundaries(value: float) -> None:
    result = evaluate_property_calculation(single_answer(value), TASK_7)

    assert result["status"] == "ok"
    assert result["scores"]["score"] == 1.0
    assert result["scores"]["constraint_scores"] == [
        {
            "property": "free_energy_difference",
            "type": "absolute_tolerance",
            "score": 1.0,
        }
    ]


@pytest.mark.parametrize("value", [0.257031678, 0.259031680])
def test_single_property_rejects_values_outside_tolerance(value: float) -> None:
    result = evaluate_property_calculation(single_answer(value), TASK_7)

    assert result["status"] == "ok"
    assert result["failure_type"] is None
    assert result["scores"]["validity_gate"] == 1.0
    assert result["scores"]["domain_gate"] == 1.0
    assert result["scores"]["score"] == 0.0


@pytest.mark.parametrize(
    ("value", "unit"),
    [
        (0.258031679, "meV"),
        (0.258031679, "kj/mol"),
        (0.258031679, None),
        (True, "kJ/mol"),
        ("0.258031679", "kJ/mol"),
        (math.nan, "kJ/mol"),
        (math.inf, "kJ/mol"),
    ],
)
def test_single_property_well_formed_wrong_values_score_zero(
    value: object,
    unit: object,
) -> None:
    result = evaluate_property_calculation(single_answer(value, unit), TASK_7)

    assert result["status"] == "ok"
    assert result["scores"]["score"] == 0.0


def test_single_property_missing_answer_scores_zero() -> None:
    result = evaluate_property_calculation(
        {"task_id": TASK_7["task_id"], "unit": "kJ/mol"},
        TASK_7,
    )

    assert result["status"] == "ok"
    assert result["scores"]["score"] == 0.0


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (multi_answer(), 1.0),
        (multi_answer(ambient="wrong", high_pressure="wrong"), 0.5),
        (multi_answer(value=0.2), 0.5),
        (multi_answer(value=0.2, ambient="wrong"), 0.0),
        (multi_answer(include_numeric=False), 0.5),
        (multi_answer(include_ambient=False), 0.5),
    ],
)
def test_multi_property_group_scores(answer: dict, expected: float) -> None:
    result = evaluate_property_calculation(answer, TASK_8)

    assert result["status"] == "ok"
    assert result["scores"]["score"] == expected
    assert [item["property"] for item in result["scores"]["constraint_scores"]] == [
        "potential_energy_difference",
        "pressure_phase_assignment",
    ]


@pytest.mark.parametrize("value", [0.078, 0.080])
def test_task_8_numeric_tolerance_is_inclusive(value: float) -> None:
    result = evaluate_property_calculation(multi_answer(value=value), TASK_8)

    assert result["scores"]["score"] == 1.0


@pytest.mark.parametrize(
    "update",
    [
        {"requested_properties": []},
        {"gold_answers": []},
        {
            "gold_answers": [
                {
                    "property": "other",
                    "value": 0.258031679,
                    "unit": "kJ/mol",
                    "absolute_tolerance": 0.001,
                }
            ]
        },
        {
            "gold_answers": [
                {
                    "property": "free_energy_difference",
                    "value": 0.258031679,
                    "unit": "kJ/mol",
                    "absolute_tolerance": 0.0,
                }
            ]
        },
        {
            "scoring": {
                "aggregation": "geometric_mean",
                "comparison_groups": [
                    {"id": "free_energy_difference", "mode": "all"}
                ],
            }
        },
        {
            "scoring": {
                "aggregation": "arithmetic_mean",
                "comparison_groups": [{"id": "unknown", "mode": "all"}],
            }
        },
    ],
)
def test_malformed_task_schema_returns_task_error(update: dict) -> None:
    task = {**TASK_7, **update}

    result = evaluate_property_calculation(single_answer(0.258031679), task)

    assert result["status"] == "error"
    assert result["failure_type"] == "task_error"
    assert result["scores"]["score"] == 0.0


def test_result_records_submitted_and_gold_values() -> None:
    result = evaluate_property_calculation(single_answer(0.258031679), TASK_7)

    assert result["canonical_smiles"] is None
    assert result["properties"] == {
        "submitted_answers": {
            "free_energy_difference": {"value": 0.258031679, "unit": "kJ/mol"}
        },
        "gold_answers": {
            "free_energy_difference": {"value": 0.258031679, "unit": "kJ/mol"}
        },
    }
    assert result["scores"]["property_score"] == 1.0
    assert result["versions"] == {"property_calculation_evaluator": 1}
