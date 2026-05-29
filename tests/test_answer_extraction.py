from __future__ import annotations

from benchmark.answer_extraction import normalize_answer_record


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
