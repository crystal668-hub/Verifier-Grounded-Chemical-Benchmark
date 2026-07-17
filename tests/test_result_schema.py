from __future__ import annotations

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import (
    base_result,
    error_result,
    verified_result,
)


def test_base_result_builds_score_free_evidence_skeleton() -> None:
    result = base_result(
        "task_1",
        "verifier_v1",
        {"verifier_image": "verifier-grounded:dev", "backend": "fake"},
    )

    assert result == {
        "outcome": "evaluation_failed",
        "task_id": "task_1",
        "verifier_id": "verifier_v1",
        "canonical_candidate": {},
        "properties": {},
        "diagnostics": {},
        "failure_scope": None,
        "failure_type": None,
        "message": None,
        "versions": {"verifier_image": "verifier-grounded:dev", "backend": "fake"},
    }
    assert "scores" not in result


def test_candidate_error_result_sets_candidate_rejected_outcome() -> None:
    result = base_result("task_1", "verifier_v1", {"backend": "fake"})

    updated = error_result(result, "parse_error", "candidate is missing")

    assert updated is result
    assert result["outcome"] == "candidate_rejected"
    assert result["failure_scope"] == "candidate"
    assert result["failure_type"] == "parse_error"
    assert result["message"] == "candidate is missing"


def test_infrastructure_error_preserves_diagnostic_properties() -> None:
    result = base_result("task_1", "verifier_v1")

    error_result(result, "verifier_tool_error", "tool failed", properties={"atom_count": 4})

    assert result["outcome"] == "evaluation_failed"
    assert result["failure_scope"] == "infrastructure"
    assert result["properties"] == {"atom_count": 4}


def test_verified_result_attaches_properties_and_canonical_candidate() -> None:
    result = base_result("task_1", "verifier_v1")

    verified_result(
        result,
        {"qed": 0.5},
        canonical_candidate={"smiles": "CCO"},
    )

    assert result["outcome"] == "verified"
    assert result["properties"] == {"qed": 0.5}
    assert result["canonical_candidate"] == {"smiles": "CCO"}
    assert "scores" not in result
