from __future__ import annotations

from verifier_grounded_benchmark.evaluation.open_generation.parsing.dispatcher import normalize_answer_record


XYZ_TASK = {
    "task_id": "xtb_gap_window_001",
    "answer_schema": {
        "format": "final_answer_block",
        "final_answer_prefix": "FINAL ANSWER:",
        "value_type": "xyz",
        "fence_language": "xyz",
        "cardinality": "one",
    },
}


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""


def test_normalize_answer_record_extracts_xyz_block() -> None:
    response = f"Use a compact water geometry.\nFINAL ANSWER:\n```xyz\n{WATER_XYZ}```"

    result = normalize_answer_record({"task_id": "xtb_gap_window_001", "response": response}, XYZ_TASK)

    assert result.ok
    assert result.answer == {
        "task_id": "xtb_gap_window_001",
        "candidates": [{"xyz": WATER_XYZ.rstrip()}],
        "raw_answer": response,
        "extracted_answer": WATER_XYZ.rstrip(),
    }


def test_normalize_answer_record_uses_last_xyz_block() -> None:
    methane = """5
methane
C 0.000000 0.000000 0.000000
H 0.629118 0.629118 0.629118
H -0.629118 -0.629118 0.629118
H -0.629118 0.629118 -0.629118
H 0.629118 -0.629118 -0.629118
"""
    response = f"FINAL ANSWER:\n```xyz\n{WATER_XYZ}```\nRevision:\nFINAL ANSWER:\n```xyz\n{methane}```"

    result = normalize_answer_record({"task_id": "xtb_gap_window_001", "response": response}, XYZ_TASK)

    assert result.ok
    assert result.answer is not None
    assert result.answer["candidates"] == [{"xyz": methane.rstrip()}]


def test_normalize_answer_record_rejects_missing_xyz_fence() -> None:
    result = normalize_answer_record({"task_id": "xtb_gap_window_001", "response": f"FINAL ANSWER:\n{WATER_XYZ}"}, XYZ_TASK)

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert "missing fenced xyz block" in str(result.message)


def test_normalize_answer_record_rejects_empty_xyz_block() -> None:
    result = normalize_answer_record({"task_id": "xtb_gap_window_001", "response": "FINAL ANSWER:\n```xyz\n```"}, XYZ_TASK)

    assert not result.ok
    assert result.failure_type == "parse_error"
    assert result.message == "final answer xyz block is empty"


def test_normalize_answer_record_passes_structured_xyz_candidates_through() -> None:
    record = {"task_id": "xtb_gap_window_001", "candidates": [{"xyz": WATER_XYZ}]}

    result = normalize_answer_record(record, XYZ_TASK)

    assert result.ok
    assert result.answer is record
