"""Public evaluator compatibility wrapper around EvaluationEngine."""

from __future__ import annotations

from typing import Any

from verifier_grounded_benchmark.evaluation import (
    EvaluationConfig,
    EvaluationEngine,
    EvaluationReport,
)
from verifier_grounded_benchmark.task.loader import task_pack_from_mappings
from verifier_grounded_benchmark.task.models import TaskPack


class Evaluator:
    def __init__(
        self,
        tasks: TaskPack | dict[str, dict[str, Any]],
        verifier_specs: dict[str, dict[str, Any]] | None = None,
        config: EvaluationConfig | None = None,
    ) -> None:
        self.config = config or EvaluationConfig()
        self._legacy: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]] | None = None
        if isinstance(tasks, TaskPack):
            self.task_pack = tasks
            self.engine = EvaluationEngine(tasks, self.config)
        else:
            from benchmark.evaluate import evaluate_many, evaluate_one

            specs = verifier_specs or {}
            self.task_pack = task_pack_from_mappings(tasks, specs)
            self.engine = None
            self._legacy = (tasks, specs)
            self._legacy_evaluate_one = evaluate_one
            self._legacy_evaluate_many = evaluate_many

    @property
    def tasks(self) -> dict[str, dict[str, Any]]:
        return self.task_pack.tasks_by_id

    @property
    def verifier_specs(self) -> dict[str, dict[str, Any]]:
        return self.task_pack.verifier_specs_by_id

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        if self.engine is not None:
            return self.engine.evaluate_one(answer)
        assert self._legacy is not None
        return self._legacy_evaluate_one(answer, *self._legacy)

    def evaluate_many(
        self,
        answers: list[dict[str, Any]],
        *,
        as_report: bool = False,
    ) -> dict[str, Any] | EvaluationReport:
        if self.engine is not None:
            report = self.engine.evaluate_many(answers)
            return report if as_report else report.to_dict()
        assert self._legacy is not None
        report_dict = self._legacy_evaluate_many(answers, *self._legacy)
        if as_report:
            return EvaluationReport(report_dict["summary"], report_dict["rows"])
        return report_dict
