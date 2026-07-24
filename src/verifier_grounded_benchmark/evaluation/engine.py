"""Static topic dispatch for validated task packs."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.evaluation.common.results import error_result, scored_result
from verifier_grounded_benchmark.evaluation.config import EvaluationConfig
from verifier_grounded_benchmark.evaluation.open_generation import OpenGenerationEvaluator
from verifier_grounded_benchmark.evaluation.open_generation.parsing.final_answer_line import (
    parse_final_answer_line,
)
from verifier_grounded_benchmark.evaluation.open_generation.verification.protocol import PropertyVerifier
from verifier_grounded_benchmark.evaluation.property_calculation import PropertyCalculationEvaluator
from verifier_grounded_benchmark.evaluation.reporting.summary import EvaluationReport, build_report
from verifier_grounded_benchmark.task.models import (
    OpenGenerationTaskSpec,
    PropertyCalculationTaskSpec,
    TaskPack,
)


class EvaluationEngine:
    def __init__(
        self,
        task_pack: TaskPack,
        config: EvaluationConfig | None = None,
        *,
        verifier: PropertyVerifier | None = None,
    ) -> None:
        self.task_pack = task_pack
        self.config = config or EvaluationConfig()
        self._tasks = {task.task_id: task for task in task_pack.tasks}
        self._verifier_specs = {
            spec.verifier_id: spec.raw for spec in task_pack.verifier_specs
        }
        self._open_generation = OpenGenerationEvaluator(verifier)
        self._property_calculation = PropertyCalculationEvaluator()

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        task_id = answer.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            return error_result(
                task_id=None,
                failure_scope="submission",
                failure_type="task_error",
                message="answer must include a task_id string",
                versions=self._versions(),
            )
        task = self._tasks.get(task_id)
        if task is None:
            return error_result(
                task_id=task_id,
                failure_scope="submission",
                failure_type="task_error",
                message=f"unknown task_id: {task_id}",
                versions=self._versions(),
            )
        if isinstance(task, OpenGenerationTaskSpec):
            result = self._open_generation.evaluate(
                answer,
                task,
                self._verifier_specs,
                self.task_pack.scoring_profiles,
                versions=self._versions(),
            )
        elif isinstance(task, PropertyCalculationTaskSpec):
            try:
                normalized, raw_answer, extracted = _normalize_property_answer(answer, task.raw)
            except ValueError as exc:
                result = _property_parse_failure(task_id, str(exc), self._versions())
            else:
                result = self._property_calculation.evaluate(
                    normalized,
                    task,
                    self.task_pack.scoring_profiles,
                    versions=self._versions(),
                )
                if raw_answer is not None:
                    result["raw_answer"] = raw_answer
                    result["extracted_answer"] = extracted
        else:
            raise TypeError(f"unsupported task model: {type(task).__name__}")
        if self.config.fail_fast and result["status"] == "error":
            raise RuntimeError(
                f"evaluation failed for task_id={task_id!r}: "
                f"{result['failure_type']}: {result['message']}"
            )
        return result

    def evaluate_many(self, answers: list[dict[str, Any]]) -> EvaluationReport:
        results = [self.evaluate_one(answer) for answer in answers]
        return build_report(results, answers, list(self._tasks))

    def _versions(self) -> dict[str, Any]:
        return {
            "package": "0.3.0",
            "task_pack": self.task_pack.version,
            "scoring": self.task_pack.scoring_version,
            "verifiers": {},
        }


def _normalize_property_answer(
    answer: dict[str, Any], task: Any
) -> tuple[dict[str, Any], str | None, str | None]:
    if "response" not in answer and not isinstance(answer.get("raw_answer"), str):
        return answer, None, None
    raw_answer = answer.get("response", answer.get("raw_answer"))
    if not isinstance(raw_answer, str):
        raise ValueError("property answer must be structured or a raw response string")
    schema = task.get("answer_schema")
    if schema.get("format") != "final_answer_line" or schema.get("value_type") != "json":
        raise ValueError("property answer schema must use a JSON final answer line")
    candidate, extracted = parse_final_answer_line(raw_answer, schema)
    payload = candidate["json"]
    if not isinstance(payload, dict):
        raise ValueError("property answer must be a JSON object")
    return {"task_id": answer.get("task_id"), **payload}, raw_answer, extracted


def _property_parse_failure(
    task_id: str, message: str, versions: dict[str, Any]
) -> dict[str, Any]:
    return scored_result(
        task_id=task_id,
        properties={},
        scores={
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "identity_gate": 0.0,
            "constraint_scores": [],
            "comparison_group_scores": [],
            "property_score": 0.0,
            "geometry_quality_score": 0.0,
            "score": 0.0,
        },
        versions=versions,
        failure_scope="submission",
        failure_type="parse_error",
        message=message,
    )
