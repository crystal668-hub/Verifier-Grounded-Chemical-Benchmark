from __future__ import annotations

import pytest

from benchmark.answer_extraction import normalize_answer_record


TASK_7 = {
    "task_id": "property_calc_free_energy_001",
    "task_type": "property_calculation",
    "answer_schema": {
        "format": "final_answer_line",
        "final_answer_prefix": "FINAL ANSWER:",
        "value_type": "json",
        "cardinality": "one",
    },
}

TASK_8 = {
    **TASK_7,
    "task_id": "property_calc_crystal_phase_002",
}


def test_normalizes_raw_single_property_answer() -> None:
    response = 'Reasoning\nFINAL ANSWER: {"answer":0.258031679,"unit":"kJ/mol"}'

    result = normalize_answer_record(
        {"task_id": TASK_7["task_id"], "response": response},
        TASK_7,
    )

    assert result.ok
    assert result.answer == {
        "task_id": TASK_7["task_id"],
        "answer": 0.258031679,
        "unit": "kJ/mol",
        "raw_answer": response,
        "extracted_answer": '{"answer":0.258031679,"unit":"kJ/mol"}',
    }


def test_normalizes_structured_single_property_answer() -> None:
    record = {
        "task_id": TASK_7["task_id"],
        "answer": 0.258031679,
        "unit": "kJ/mol",
    }

    result = normalize_answer_record(record, TASK_7)

    assert result.ok
    assert result.answer == record


def test_nested_task_id_cannot_override_submission_task_id() -> None:
    result = normalize_answer_record(
        {
            "task_id": TASK_7["task_id"],
            "response": 'FINAL ANSWER: {"task_id":"other","answer":1,"unit":"kJ/mol"}',
        },
        TASK_7,
    )

    assert result.ok
    assert result.answer["task_id"] == TASK_7["task_id"]


def test_normalizes_raw_multi_property_answer() -> None:
    response = (
        'FINAL ANSWER: {"answers":['
        '{"property":"potential_energy_difference","value":0.079,"unit":"eV"},'
        '{"property":"ambient_pressure_phase","value":"alpha"},'
        '{"property":"high_pressure_phase","value":"beta"}]}'
    )

    result = normalize_answer_record(
        {"task_id": TASK_8["task_id"], "response": response},
        TASK_8,
    )

    assert result.ok
    assert result.answer["answers"] == [
        {"property": "potential_energy_difference", "value": 0.079, "unit": "eV"},
        {"property": "ambient_pressure_phase", "value": "alpha"},
        {"property": "high_pressure_phase", "value": "beta"},
    ]


def test_multi_property_answer_may_omit_requested_fields_for_partial_scoring() -> None:
    record = {
        "task_id": TASK_8["task_id"],
        "answers": [
            {"property": "potential_energy_difference", "value": 0.079, "unit": "eV"}
        ],
    }

    result = normalize_answer_record(record, TASK_8)

    assert result.ok
    assert result.answer == record


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("[]", "JSON object"),
        ('{"answers":{}}', "answers must be a list"),
        ('{"answers":[1]}', "entries must be objects"),
        ('{"answers":[{"property":"a"},{"property":"a"}]}', "duplicate property"),
        ('{"other":1}', "answer or answers"),
    ],
)
def test_rejects_malformed_property_answer_shapes(payload: str, message: str) -> None:
    result = normalize_answer_record(
        {"task_id": TASK_8["task_id"], "response": f"FINAL ANSWER: {payload}"},
        TASK_8,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert message in str(result.message)


def test_rejects_invalid_json() -> None:
    result = normalize_answer_record(
        {"task_id": TASK_7["task_id"], "response": "FINAL ANSWER: {bad}"},
        TASK_7,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "invalid JSON" in str(result.message)


def test_rejects_missing_final_answer_marker() -> None:
    result = normalize_answer_record(
        {"task_id": TASK_7["task_id"], "response": '{"answer":1}'},
        TASK_7,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "missing final answer line" in str(result.message)
