from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from benchmark.evaluate import (
    evaluate_many as legacy_evaluate_many,
    evaluate_one as legacy_evaluate_one,
    summarize_row,
    summarize_rows,
)


@dataclass(frozen=True)
class EvaluationConfig:
    fail_fast: bool = False


@dataclass(frozen=True)
class EvaluationReport:
    summary: dict[str, Any]
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": deepcopy(self.summary),
            "rows": deepcopy(self.rows),
        }

    def to_json(self, *, indent: int | None = 2, sort_keys: bool = True) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys)

    def to_jsonl_rows(self, *, sort_keys: bool = True) -> str:
        return "\n".join(json.dumps(row, sort_keys=sort_keys) for row in self.rows)


class Evaluator:
    def __init__(
        self,
        tasks: dict[str, dict[str, Any]],
        verifier_specs: dict[str, dict[str, Any]],
        config: EvaluationConfig | None = None,
    ) -> None:
        self.tasks = deepcopy(tasks)
        self.verifier_specs = deepcopy(verifier_specs)
        self.config = config or EvaluationConfig()

    def evaluate_one(self, answer: dict[str, Any]) -> dict[str, Any]:
        return legacy_evaluate_one(answer, self.tasks, self.verifier_specs)

    def evaluate_many(
        self,
        answers: list[dict[str, Any]],
        *,
        as_report: bool = False,
    ) -> dict[str, Any] | EvaluationReport:
        if self.config.fail_fast:
            rows = []
            for answer in answers:
                result = self.evaluate_one(answer)
                if result.get("status") != "ok":
                    task_id = result.get("task_id")
                    failure_type = result.get("failure_type")
                    message = result.get("message")
                    raise RuntimeError(
                        f"evaluation failed for task_id={task_id!r}: "
                        f"{failure_type}: {message}"
                    )
                rows.append(summarize_row(result))
            report = {
                "summary": summarize_rows(rows, answers=answers, tasks=self.tasks),
                "rows": rows,
            }
        else:
            report = legacy_evaluate_many(answers, self.tasks, self.verifier_specs)

        if as_report:
            return EvaluationReport(
                summary=report["summary"],
                rows=report["rows"],
            )
        return report
