"""Property Calculation topic evaluator."""

from __future__ import annotations

from typing import Any, Mapping

from verifier_grounded_benchmark.evaluation.common.failures import SUBMISSION_FAILURE
from verifier_grounded_benchmark.evaluation.common.results import scored_result
from verifier_grounded_benchmark.evaluation.property_calculation.parsing.dispatcher import parse_answer
from verifier_grounded_benchmark.evaluation.property_calculation.parsing.multi_property import (
    PropertyAnswerParseError,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.comparison_group import (
    score_comparison_group,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.exact_string import (
    score_exact_string,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.numeric_gold import (
    score_numeric_gold,
)
from verifier_grounded_benchmark.evaluation.property_calculation.scoring.task_score import score_task
from verifier_grounded_benchmark.task.models import PropertyCalculationTaskSpec


class PropertyCalculationEvaluator:
    def evaluate(
        self,
        answer: dict[str, Any],
        task: PropertyCalculationTaskSpec,
        scoring_profiles: Mapping[str, Mapping[str, Any]],
        *,
        versions: dict[str, Any],
    ) -> dict[str, Any]:
        raw = task.raw
        requested = {item["name"]: item for item in raw["requested_properties"]}
        gold = {item["property"]: item for item in raw["gold_answers"]}
        try:
            submitted, unknown = parse_answer(answer, list(requested))
        except PropertyAnswerParseError as exc:
            return _submission_failure(task.task_id, str(exc), versions)

        field_scores: dict[str, float] = {}
        constraint_scores: list[dict[str, Any]] = []
        for name, definition in requested.items():
            gold_definition = gold[name]
            profile_id = gold_definition["scoring_profile"]
            profile = scoring_profiles[profile_id]
            if definition["value_type"] == "number":
                field_score = score_numeric_gold(submitted.get(name), gold_definition, profile)
            else:
                field_score = score_exact_string(submitted.get(name), gold_definition, profile)
            field_scores[name] = field_score
            constraint_scores.append(
                {
                    "property": name,
                    "type": profile["type"],
                    "role": "main",
                    "value": None if submitted.get(name) is None else submitted[name].get("value"),
                    "score": field_score,
                    "scoring_profile": profile_id,
                    "scoring_version": versions["scoring"],
                }
            )

        group_scores: list[dict[str, Any]] = []
        for group in raw["scoring"]["comparison_groups"]:
            group_id = group["id"]
            members = [
                name for name, definition in requested.items()
                if definition["comparison_group"] == group_id
            ]
            group_scores.append(
                {
                    "group": group_id,
                    "mode": "all",
                    "members": members,
                    "score": score_comparison_group([field_scores[name] for name in members]),
                }
            )
        task_score = score_task([item["score"] for item in group_scores])
        return scored_result(
            task_id=task.task_id,
            properties={
                "submitted_answers": submitted,
                "gold_answers": {
                    name: {
                        "value": definition["value"],
                        **({"unit": definition["unit"]} if "unit" in definition else {}),
                    }
                    for name, definition in gold.items()
                },
                "diagnostics": {"unknown_properties": unknown},
            },
            scores={
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "identity_gate": 1.0,
                "constraint_scores": constraint_scores,
                "comparison_group_scores": group_scores,
                "property_score": task_score,
                "geometry_quality_score": 1.0,
                "stability_gate_score": 1.0,
                "score": task_score,
            },
            versions=versions,
        )


def _submission_failure(
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
            "stability_gate_score": 0.0,
            "score": 0.0,
        },
        versions=versions,
        failure_scope=SUBMISSION_FAILURE,
        failure_type="parse_error",
        message=message,
    )
