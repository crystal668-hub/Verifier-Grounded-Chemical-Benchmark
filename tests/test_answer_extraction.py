from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.parsing.dispatcher import normalize_answer_record


TASK = {
    "task_id": "rdkit_qed_max_001",
    "answer_schema": {
        "format": "final_answer_line",
        "final_answer_prefix": "FINAL ANSWER:",
        "value_type": "smiles",
        "cardinality": "one",
    },
}


def test_normalize_answer_record_extracts_final_answer_line() -> None:
    result = normalize_answer_record(
        {
            "task_id": "rdkit_qed_max_001",
            "response": "I will use ethanol.\nFINAL ANSWER: CCO",
        },
        TASK,
    )

    assert result.ok
    assert result.answer == {
        "task_id": "rdkit_qed_max_001",
        "candidates": [{"smiles": "CCO"}],
        "raw_answer": "I will use ethanol.\nFINAL ANSWER: CCO",
        "extracted_answer": "CCO",
    }


def test_normalize_answer_record_uses_last_final_answer_line() -> None:
    result = normalize_answer_record(
        {
            "task_id": "rdkit_qed_max_001",
            "response": "FINAL ANSWER: C\nRevision follows.\nFINAL ANSWER: CCO",
        },
        TASK,
    )

    assert result.ok
    assert result.answer is not None
    assert result.answer["candidates"] == [{"smiles": "CCO"}]


def test_normalize_answer_record_reports_missing_final_answer_line() -> None:
    result = normalize_answer_record({"task_id": "rdkit_qed_max_001", "response": "CCO"}, TASK)

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "missing final answer line" in str(result.message)


def test_normalize_answer_record_reports_empty_final_answer_line() -> None:
    result = normalize_answer_record({"task_id": "rdkit_qed_max_001", "response": "FINAL ANSWER:   "}, TASK)

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert result.message == "final answer line is empty"


def test_normalize_answer_record_reports_unsupported_schema_format() -> None:
    task = {"task_id": "task_1", "answer_schema": {"format": "json"}}

    result = normalize_answer_record({"task_id": "task_1", "response": "FINAL ANSWER: CCO"}, task)

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert result.message == "unsupported answer_schema format"


def test_normalize_answer_record_passes_structured_candidates_through() -> None:
    record = {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}

    result = normalize_answer_record(record, TASK)

    assert result.ok
    assert result.answer is record


def test_normalize_answer_record_extracts_json_value() -> None:
    task = {
        "task_id": "json_final_answer_example_001",
        "answer_schema": {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "json",
            "cardinality": "one",
        },
    }

    result = normalize_answer_record(
        {
            "task_id": "json_final_answer_example_001",
            "response": 'Reasoning...\nFINAL ANSWER: {"scaling_matrix": [2, 1, 1]}',
        },
        task,
    )

    assert result.ok
    assert result.answer is not None
    assert result.answer["candidates"] == [{"json": {"scaling_matrix": [2, 1, 1]}}]
    assert result.answer["extracted_answer"] == '{"scaling_matrix": [2, 1, 1]}'


def test_normalize_answer_record_rejects_invalid_json_value() -> None:
    task = {
        "task_id": "json_final_answer_example_001",
        "answer_schema": {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "json",
            "cardinality": "one",
        },
    }

    result = normalize_answer_record(
        {
            "task_id": "json_final_answer_example_001",
            "response": "FINAL ANSWER: {not-json}",
        },
        task,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "invalid JSON final answer" in str(result.message)


@pytest.mark.parametrize(("raw", "expected"), [("28.44", 28.44), ("2.844e1", 28.44)])
def test_normalize_answer_record_extracts_number_value(raw: str, expected: float) -> None:
    task = {
        "task_id": "number_final_answer_example_001",
        "answer_schema": {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "number",
            "cardinality": "one",
        },
    }

    result = normalize_answer_record(
        {
            "task_id": "number_final_answer_example_001",
            "response": f"The strongest Si peak is near this angle.\nFINAL ANSWER: {raw}",
        },
        task,
    )

    assert result.ok
    assert result.answer is not None
    assert result.answer["candidates"] == [{"value": expected, "raw_value": raw}]


def test_normalize_answer_record_rejects_invalid_number_value() -> None:
    task = {
        "task_id": "number_final_answer_example_001",
        "answer_schema": {
            "format": "final_answer_line",
            "final_answer_prefix": "FINAL ANSWER:",
            "value_type": "number",
            "cardinality": "one",
        },
    }

    result = normalize_answer_record(
        {
            "task_id": "number_final_answer_example_001",
            "response": "FINAL ANSWER: twenty eight",
        },
        task,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "invalid numeric final answer" in str(result.message)


CIF_TASK = {
    "task_id": "matgl_bandgap_window_si_001",
    "answer_schema": {
        "format": "final_answer_block",
        "final_answer_prefix": "FINAL ANSWER:",
        "value_type": "cif",
        "fence_language": "cif",
        "cardinality": "one",
    },
}


SI_CIF = """data_Si
_symmetry_space_group_name_H-M   'P 1'
_cell_length_a   3.8669746
_cell_length_b   3.8669746
_cell_length_c   3.8669746
_cell_angle_alpha   60.0000000
_cell_angle_beta   60.0000000
_cell_angle_gamma   60.0000000
loop_
 _atom_site_label
 _atom_site_type_symbol
 _atom_site_fract_x
 _atom_site_fract_y
 _atom_site_fract_z
 Si0 Si 0.000000 0.000000 0.000000
 Si1 Si 0.250000 0.250000 0.250000
"""


def test_normalize_answer_record_extracts_cif_block() -> None:
    response = f"Use a crystalline silicon cell.\nFINAL ANSWER:\n```cif\n{SI_CIF}```"

    result = normalize_answer_record({"task_id": "matgl_bandgap_window_si_001", "response": response}, CIF_TASK)

    assert result.ok
    assert result.answer is not None
    assert result.answer["candidates"] == [{"cif": SI_CIF.rstrip()}]
    assert result.answer["raw_answer"] == response
    assert result.answer["extracted_answer"] == SI_CIF.rstrip()


def test_normalize_answer_record_rejects_missing_final_answer_block_prefix() -> None:
    result = normalize_answer_record(
        {"task_id": "matgl_bandgap_window_si_001", "response": f"```cif\n{SI_CIF}```"},
        CIF_TASK,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "missing final answer block" in str(result.message)


def test_normalize_answer_record_rejects_missing_cif_fence() -> None:
    result = normalize_answer_record(
        {"task_id": "matgl_bandgap_window_si_001", "response": f"FINAL ANSWER:\n{SI_CIF}"},
        CIF_TASK,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "missing fenced cif block" in str(result.message)


def test_normalize_answer_record_rejects_wrong_fence_language() -> None:
    result = normalize_answer_record(
        {"task_id": "matgl_bandgap_window_si_001", "response": f"FINAL ANSWER:\n```text\n{SI_CIF}```"},
        CIF_TASK,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "missing fenced cif block" in str(result.message)


def test_normalize_answer_record_rejects_empty_cif_block() -> None:
    result = normalize_answer_record(
        {"task_id": "matgl_bandgap_window_si_001", "response": "FINAL ANSWER:\n```cif\n   \n```"},
        CIF_TASK,
    )

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert result.message == "final answer cif block is empty"
