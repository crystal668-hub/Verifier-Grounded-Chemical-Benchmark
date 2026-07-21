from __future__ import annotations

import json
import sys

import pytest

from verifier_grounded_benchmark.evaluation import EvaluationEngine
from verifier_grounded_benchmark.evaluation.open_generation.verification.evidence import (
    VerificationEvidence,
)
from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import (
    SubprocessPropertyVerifier,
)
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource


def _pack(name: str):
    return load_task_pack(
        package_resource(name, "tasks.yaml"),
        package_resource(name, "verifier_specs.yaml"),
    )


class FakeVerifier:
    def __init__(self, properties_by_verifier: dict[str, dict]) -> None:
        self.properties_by_verifier = properties_by_verifier
        self.calls: list[tuple[str, str]] = []
        self.evidence_override: VerificationEvidence | None = None

    def verify(self, candidate, task, constraint, spec):
        self.calls.append((spec["verifier_id"], constraint["property"]))
        if self.evidence_override is not None:
            return self.evidence_override
        return VerificationEvidence(
            "verified",
            task["task_id"],
            spec["verifier_id"],
            {"smiles": candidate.get("smiles", "canonical")},
            self.properties_by_verifier[spec["verifier_id"]],
            versions={"backend": "fake"},
        )


def test_open_generation_scores_evidence_with_configured_profile() -> None:
    fake = FakeVerifier({"rdkit_qed_v1": {"qed": 0.5}})
    engine = EvaluationEngine(_pack("rdkit"), verifier=fake)

    result = engine.evaluate_one(
        {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}
    )

    assert result["status"] == "scored"
    assert result["scores"]["score"] == 0.5
    assert result["scores"]["constraint_scores"] == [
        {
            "property": "qed",
            "type": "maximize",
            "role": "main",
            "value": 0.5,
            "score": 0.5,
            "scoring_profile": "rdkit_qed_maximize_0p0_1p0_v2",
            "scoring_version": "linear_goal_v2",
        }
    ]


def test_evidence_reuse_never_reuses_constraint_score() -> None:
    fake = FakeVerifier(
        {
            "xtb_hessian_thermo_gfn2_v1": {
                "imaginary_frequency_count": 1,
                "entropy_298_per_heavy_atom": 65.0,
            },
            "xtb_relaxation_energy_gfn2_v1": {"relaxation_energy": 0.175},
        }
    )
    engine = EvaluationEngine(_pack("xtb"), verifier=fake)

    result = engine.evaluate_one(
        {"task_id": "xtb_hessian_thermo_stability_013", "candidates": [{"xyz": "fake"}]}
    )

    assert len(fake.calls) == 2
    assert result["scores"]["property_score"] == pytest.approx(0.687443701)
    assert result["scores"]["geometry_quality_score"] == pytest.approx(7 / 12)
    assert result["scores"]["stability_gate_score"] == pytest.approx(0.5)
    assert result["scores"]["score"] == pytest.approx(0.200504413)
    assert [item["property"] for item in result["scores"]["constraint_scores"]] == [
        "imaginary_frequency_count",
        "entropy_298_per_heavy_atom",
        "relaxation_energy",
    ]


def test_candidate_rejection_is_scored_zero() -> None:
    fake = FakeVerifier({})
    fake.evidence_override = VerificationEvidence(
        "candidate_rejected",
        "rdkit_qed_max_001",
        "rdkit_qed_v1",
        {"smiles": "invalid"},
        {},
        failure_type="validity_error",
        message="invalid molecule",
        failure_scope="candidate",
    )
    engine = EvaluationEngine(_pack("rdkit"), verifier=fake)

    result = engine.evaluate_one(
        {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "invalid"}]}
    )

    assert result["status"] == "scored"
    assert result["failure_scope"] == "candidate"
    assert result["scores"]["score"] == 0.0


def test_infrastructure_failure_has_null_score_and_invalidates_benchmark() -> None:
    fake = FakeVerifier({})
    fake.evidence_override = VerificationEvidence(
        "evaluation_failed",
        "rdkit_qed_max_001",
        "rdkit_qed_v1",
        {"smiles": "CCO"},
        {},
        failure_type="verifier_timeout",
        message="timed out",
        failure_scope="infrastructure",
    )
    engine = EvaluationEngine(_pack("rdkit"), verifier=fake)
    answer = {"task_id": "rdkit_qed_max_001", "candidates": [{"smiles": "CCO"}]}

    result = engine.evaluate_one(answer)
    report = engine.evaluate_many([answer])

    assert result["status"] == "error"
    assert result["scores"]["score"] is None
    assert report.rows[0]["score"] is None
    assert report.summary["benchmark_score"] is None


def test_known_task_parse_failure_is_submission_zero() -> None:
    engine = EvaluationEngine(_pack("rdkit"), verifier=FakeVerifier({}))

    result = engine.evaluate_one(
        {"task_id": "rdkit_qed_max_001", "response": "no final answer"}
    )

    assert result["status"] == "scored"
    assert result["failure_scope"] == "submission"
    assert result["scores"]["score"] == 0.0


def test_engine_dispatches_property_calculation_and_raw_json() -> None:
    engine = EvaluationEngine(_pack("property_calculation"))
    structured = engine.evaluate_one(
        {
            "task_id": "property_calc_free_energy_001",
            "answer": 0.258531679,
            "unit": "kJ/mol",
        }
    )
    raw = engine.evaluate_one(
        {
            "task_id": "property_calc_free_energy_001",
            "response": 'FINAL ANSWER: {"answer":0.258531679,"unit":"kJ/mol"}',
        }
    )

    assert structured["scores"]["score"] == pytest.approx(1 - 0.0005 / 0.258031679)
    assert raw["scores"] == structured["scores"]
    assert raw["raw_answer"].startswith("FINAL ANSWER")


def test_complete_property_report_gets_official_benchmark_score() -> None:
    pack = _pack("property_calculation")
    answers = [json.loads(line) for line in package_resource("property_calculation", "sample_answers.jsonl").read_text().splitlines()]

    report = EvaluationEngine(pack).evaluate_many(answers)

    assert report.summary["coverage"]["complete"] is True
    assert report.summary["benchmark_score"] == 1.0
    assert [row["score"] for row in report.rows] == [1.0, 1.0]


def test_duplicate_unknown_and_missing_ids_invalidate_coverage() -> None:
    engine = EvaluationEngine(_pack("property_calculation"))
    answer = {
        "task_id": "property_calc_free_energy_001",
        "answer": 0.258031679,
        "unit": "kJ/mol",
    }
    report = engine.evaluate_many([answer, answer, {"task_id": "unknown"}])

    coverage = report.summary["coverage"]
    assert coverage["duplicate_task_ids"] == ["property_calc_free_energy_001"]
    assert coverage["unknown_task_ids"] == ["unknown"]
    assert coverage["missing_task_ids"] == ["property_calc_crystal_phase_002"]
    assert report.summary["benchmark_score"] is None


def test_subprocess_adapter_discards_legacy_scores(tmp_path) -> None:
    script = tmp_path / "legacy_verifier.py"
    script.write_text(
        "import json, sys\n"
        "payload=json.load(sys.stdin)\n"
        "json.dump({'status':'ok','task_id':payload['task']['task_id'],"
        "'canonical_smiles':'CCO','properties':{'qed':0.5},"
        "'scores':{'score':0.99,'constraint_scores':[{'score':0.99}]},"
        "'versions':{'backend':'legacy'}},sys.stdout)\n",
        encoding="utf-8",
    )
    evidence = SubprocessPropertyVerifier(python_executable=sys.executable).verify(
        {"smiles": "CCO"},
        {"task_id": "task"},
        {"property": "qed"},
        {"verifier_id": "legacy", "verification_script": str(script), "timeout_seconds": 5},
    )

    assert evidence.outcome == "verified"
    assert evidence.properties == {"qed": 0.5}
    assert "score" not in evidence.to_dict()
    assert "scores" not in evidence.to_dict()
