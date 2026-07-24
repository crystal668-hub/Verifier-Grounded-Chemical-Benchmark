"""Open-generation topic evaluation from candidate through evidence to score."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Mapping

from verifier_grounded_benchmark.evaluation.common.results import error_result, scored_result
from verifier_grounded_benchmark.evaluation.open_generation.parsing.dispatcher import parse_answer
from verifier_grounded_benchmark.evaluation.open_generation.scoring.task_score import (
    score_constraint_value,
    score_open_generation_task,
)
from verifier_grounded_benchmark.evaluation.open_generation.verification.evidence import (
    VerificationEvidence,
)
from verifier_grounded_benchmark.evaluation.open_generation.verification.protocol import PropertyVerifier
from verifier_grounded_benchmark.evaluation.open_generation.verification.reuse import evidence_reuse_key
from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import (
    SubprocessPropertyVerifier,
)
from verifier_grounded_benchmark.task.models import OpenGenerationTaskSpec


class OpenGenerationEvaluator:
    def __init__(self, verifier: PropertyVerifier | None = None) -> None:
        self.verifier = verifier or SubprocessPropertyVerifier()

    def evaluate(
        self,
        answer: dict[str, Any],
        task: OpenGenerationTaskSpec,
        verifier_specs: Mapping[str, Mapping[str, Any]],
        scoring_profiles: Mapping[str, Mapping[str, Any]],
        *,
        versions: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            parsed = parse_answer(answer, task.raw)
        except ValueError as exc:
            return _candidate_zero(
                task.task_id,
                scope="submission",
                failure_type="parse_error",
                message=str(exc),
                versions=versions,
            )
        if len(parsed.candidates) != 1:
            return _candidate_zero(
                task.task_id,
                scope="submission",
                failure_type="parse_error",
                message="task requires exactly one candidate",
                versions=versions,
            )
        candidate = parsed.candidates[0]
        cache: dict[tuple[str, str, str, str], VerificationEvidence] = {}
        constraint_scores: list[dict[str, Any]] = []
        properties: dict[str, Any] = {}
        verifier_versions: dict[str, Any] = {}
        canonical_candidate: dict[str, Any] = candidate

        for hard, raw_hard in zip(
            task.hard_constraints, task.raw.get("hard_constraints", ()), strict=True
        ):
            spec = verifier_specs[hard.verifier_id]
            evidence = _get_evidence(
                self.verifier, cache, candidate, task.raw, raw_hard, spec, hard.property
            )
            failure = _handle_evidence_failure(
                evidence,
                task_id=task.task_id,
                parsed=parsed,
                versions=versions,
                verifier_versions=verifier_versions,
            )
            if failure is not None:
                return failure
            properties.update(evidence.properties)
            canonical_candidate = evidence.canonical_candidate or canonical_candidate
            verifier_versions[evidence.verifier_id] = evidence.versions
            value_or_error = _finite_property(evidence, hard.property)
            if isinstance(value_or_error, dict):
                return value_or_error
            value = value_or_error
            if not _hard_constraint_passes(
                value, hard.operator, hard.threshold, hard.lower, hard.upper
            ):
                properties["hard_constraint_passed"] = False
                result = _candidate_zero(
                    task.task_id,
                    scope="candidate",
                    failure_type="hard_constraint_failed",
                    message=_hard_constraint_message(
                        hard.property,
                        value,
                        hard.operator,
                        hard.threshold,
                        hard.lower,
                        hard.upper,
                    ),
                    versions=_versions(versions, verifier_versions),
                    properties=properties,
                )
                result["canonical_candidate"] = canonical_candidate
                result["canonical_smiles"] = canonical_candidate.get("smiles")
                result["hard_constraint"] = {
                    "property": hard.property,
                    "operator": hard.operator,
                    "threshold": hard.threshold,
                    "lower": hard.lower,
                    "upper": hard.upper,
                    "value": value,
                }
                _attach_parsed(result, parsed.raw_answer, parsed.extracted_answer)
                return result

        if task.hard_constraints:
            properties["hard_constraint_passed"] = True

        for constraint, raw_constraint in zip(task.constraints, task.raw["constraints"], strict=True):
            spec = verifier_specs[constraint.verifier_id]
            evidence = _get_evidence(
                self.verifier, cache, candidate, task.raw, raw_constraint, spec, constraint.property
            )
            failure = _handle_evidence_failure(
                evidence,
                task_id=task.task_id,
                parsed=parsed,
                versions=versions,
                verifier_versions=verifier_versions,
            )
            if failure is not None:
                return failure
            value_or_error = _finite_property(evidence, constraint.property)
            if isinstance(value_or_error, dict):
                return value_or_error
            value = value_or_error
            profile = scoring_profiles[constraint.scoring_profile]
            constraint_score = score_constraint_value(float(value), profile)
            constraint_scores.append(
                {
                    "property": constraint.property,
                    "type": constraint.type,
                    "role": constraint.role,
                    "value": value,
                    "score": constraint_score,
                    "scoring_profile": constraint.scoring_profile,
                    "scoring_version": versions["scoring"],
                }
            )
            properties.update(evidence.properties)
            canonical_candidate = evidence.canonical_candidate or canonical_candidate
            verifier_versions[evidence.verifier_id] = evidence.versions

        aggregate = score_open_generation_task(constraint_scores)
        result = scored_result(
            task_id=task.task_id,
            properties=properties,
            scores={
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "identity_gate": 1.0,
                "constraint_scores": constraint_scores,
                **aggregate,
            },
            versions=_versions(versions, verifier_versions),
        )
        result["canonical_candidate"] = canonical_candidate
        result["canonical_smiles"] = canonical_candidate.get("smiles")
        _attach_parsed(result, parsed.raw_answer, parsed.extracted_answer)
        return result


def _candidate_zero(
    task_id: str,
    *,
    scope: str,
    failure_type: str,
    message: str,
    versions: dict[str, Any],
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return scored_result(
        task_id=task_id,
        properties=properties or {},
        scores={
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "identity_gate": 0.0,
            "constraint_scores": [],
            "property_score": 0.0,
            "geometry_quality_score": 0.0,
            "score": 0.0,
        },
        versions=versions,
        failure_scope=scope,  # type: ignore[arg-type]
        failure_type=failure_type,
        message=message,
    )


def _versions(base: dict[str, Any], verifiers: dict[str, Any]) -> dict[str, Any]:
    return {**base, "verifiers": dict(verifiers)}


def _attach_parsed(
    result: dict[str, Any], raw_answer: str | None, extracted_answer: str | None
) -> None:
    if raw_answer is not None:
        result["raw_answer"] = raw_answer
    if extracted_answer is not None:
        result["extracted_answer"] = extracted_answer


def _get_evidence(verifier, cache, candidate, task, constraint, spec, property_name):
    key = evidence_reuse_key(candidate, spec)
    evidence = cache.get(key)
    if evidence is None or property_name not in evidence.properties:
        evidence = verifier.verify(candidate, task, constraint, spec)
        if evidence.outcome == "verified":
            cache[key] = evidence
    return evidence


def _handle_evidence_failure(
    evidence, *, task_id, parsed, versions, verifier_versions
) -> dict[str, Any] | None:
    if evidence.outcome == "candidate_rejected":
        result = _candidate_zero(
            task_id,
            scope="candidate",
            failure_type=evidence.failure_type or "candidate_rejected",
            message=evidence.message or "candidate rejected",
            versions=_versions(versions, verifier_versions),
            properties=evidence.properties,
        )
        _attach_parsed(result, parsed.raw_answer, parsed.extracted_answer)
        return result
    if evidence.outcome == "evaluation_failed":
        result = error_result(
            task_id=task_id,
            failure_scope="task" if evidence.failure_scope == "task" else "infrastructure",
            failure_type=evidence.failure_type or "verifier_tool_error",
            message=evidence.message or "verifier evaluation failed",
            versions=_versions(versions, verifier_versions),
        )
        _attach_parsed(result, parsed.raw_answer, parsed.extracted_answer)
        return result
    return None


def _finite_property(evidence, property_name: str) -> float | dict[str, Any]:
    try:
        value = evidence.properties[property_name]
    except KeyError:
        return error_result(
            task_id=evidence.task_id,
            failure_scope="infrastructure",
            failure_type="verifier_schema_error",
            message=f"verifier evidence is missing property {property_name}",
            versions={"verifiers": {evidence.verifier_id: evidence.versions}},
        )
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        return error_result(
            task_id=evidence.task_id,
            failure_scope="infrastructure",
            failure_type="verifier_schema_error",
            message=f"verifier property {property_name} must be finite",
            versions={"verifiers": {evidence.verifier_id: evidence.versions}},
        )
    return float(value)


def _hard_constraint_passes(
    value: float,
    operator: str,
    threshold: float | None,
    lower: float | None,
    upper: float | None,
) -> bool:
    if operator == "lt":
        assert threshold is not None
        return value < threshold
    if operator == "le":
        assert threshold is not None
        return value <= threshold
    assert lower is not None and upper is not None
    return lower <= value <= upper


def _hard_constraint_message(
    property_name: str,
    value: float,
    operator: str,
    threshold: float | None,
    lower: float | None,
    upper: float | None,
) -> str:
    condition = (
        f"{property_name} {operator} {threshold}"
        if operator != "closed_window"
        else f"{lower} <= {property_name} <= {upper}"
    )
    return f"hard constraint failed: {condition}; observed {value}"
