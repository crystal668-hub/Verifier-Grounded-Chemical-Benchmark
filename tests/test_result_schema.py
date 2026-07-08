from __future__ import annotations

from verifiers.common.result_schema import base_result, error_result


def test_base_result_builds_standard_error_skeleton_with_versions() -> None:
    result = base_result(
        "task_1",
        "verifier_v1",
        {"verifier_image": "verifier-grounded:dev", "backend": "fake"},
    )

    assert result == {
        "task_id": "task_1",
        "verifier_id": "verifier_v1",
        "status": "error",
        "canonical_smiles": None,
        "properties": {},
        "scores": {
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "constraint_scores": [],
            "property_score": 0.0,
            "score": 0.0,
        },
        "failure_type": None,
        "message": None,
        "versions": {"verifier_image": "verifier-grounded:dev", "backend": "fake"},
    }


def test_error_result_sets_failure_and_preserves_existing_scores() -> None:
    result = base_result("task_1", "verifier_v1", {"backend": "fake"})

    updated = error_result(result, "parse_error", "candidate is missing")

    assert updated is result
    assert result["failure_type"] == "parse_error"
    assert result["message"] == "candidate is missing"
    assert result["properties"] == {}
    assert result["scores"]["validity_gate"] == 0.0
    assert result["versions"] == {"backend": "fake"}


def test_error_result_marks_validity_gate_when_properties_are_available() -> None:
    result = base_result("task_1", "verifier_v1")

    error_result(result, "verifier_tool_error", "tool failed", properties={"atom_count": 4})

    assert result["properties"] == {"atom_count": 4}
    assert result["scores"]["validity_gate"] == 1.0


def test_error_result_marks_validity_gate_for_domain_errors_without_properties() -> None:
    result = base_result("task_1", "verifier_v1")

    error_result(result, "domain_error", "disallowed elements")

    assert result["properties"] == {}
    assert result["scores"]["validity_gate"] == 1.0
