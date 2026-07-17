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
        if isinstance(tasks, TaskPack):
            self.task_pack = tasks
        else:
            self.task_pack = task_pack_from_mappings(tasks, verifier_specs or {})
        self.engine = EvaluationEngine(self.task_pack, self.config)

    @property
    def tasks(self) -> dict[str, dict[str, Any]]:
        return self.task_pack.tasks_by_id

    @property
    def verifier_specs(self) -> dict[str, dict[str, Any]]:
        return self.task_pack.verifier_specs_by_id

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return self.engine.evaluate_one(answer)

    def evaluate_many(
        self,
        answers: list[dict[str, Any]],
        *,
        as_report: bool = False,
    ) -> dict[str, Any] | EvaluationReport:
        report = self.engine.evaluate_many(answers)
        return report if as_report else report.to_dict()
