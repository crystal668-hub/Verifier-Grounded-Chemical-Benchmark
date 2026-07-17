"""Dispatch Property Calculation answers by declared answer shape."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass
import json

from verifier_grounded_benchmark.evaluation.property_calculation.parsing.multi_property import (
    PropertyAnswerParseError,
    parse_multi_property,
)
from verifier_grounded_benchmark.evaluation.property_calculation.parsing.single_value import (
    parse_single_value,
)


def parse_answer(
    answer: dict[str, Any], requested_names: list[str]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if len(requested_names) == 1 and "answers" not in answer:
        return parse_single_value(answer, requested_names[0]), []
    return parse_multi_property(answer, set(requested_names))


@dataclass(frozen=True)
class ExtractionResult:
    answer: dict[str, Any] | None
    failure_type: str | None
    message: str | None

    @property
    def ok(self) -> bool:
        return self.answer is not None


def normalize_answer_record(
    record: dict[str, Any], task: dict[str, Any]
) -> ExtractionResult:
    if not isinstance(record.get("response", record.get("raw_answer")), str):
        return _normalize_payload(record, record)
    raw_answer = record.get("response", record.get("raw_answer"))
    schema = task.get("answer_schema") or {}
    prefix = schema.get("final_answer_prefix")
    if not isinstance(prefix, str) or not prefix:
        return ExtractionResult(None, "parse_error", "answer_schema must include final_answer_prefix")
    lines = [line for line in raw_answer.splitlines() if line.startswith(prefix)]
    if not lines:
        return ExtractionResult(None, "parse_error", f"missing final answer line with prefix {prefix!r}")
    extracted = lines[-1][len(prefix) :].strip()
    try:
        payload = json.loads(extracted)
    except json.JSONDecodeError as exc:
        return ExtractionResult(None, "parse_error", f"invalid JSON final answer: {exc.msg}")
    return _normalize_payload(
        record, payload, raw_answer=raw_answer, extracted_answer=extracted
    )


def _normalize_payload(
    record: dict[str, Any],
    payload: Any,
    *,
    raw_answer: str | None = None,
    extracted_answer: str | None = None,
) -> ExtractionResult:
    if not isinstance(payload, dict):
        return ExtractionResult(None, "parse_error", "property answer must be a JSON object")
    normalized: dict[str, Any] = {"task_id": record.get("task_id")}
    if "answers" in payload:
        items = payload.get("answers")
        requested_names = {
            item.get("property")
            for item in items
            if isinstance(items, list) and isinstance(item, dict)
            and isinstance(item.get("property"), str)
        } if isinstance(items, list) else set()
        try:
            submitted, _ = parse_multi_property(
                payload,
                requested_names,
            )
        except PropertyAnswerParseError as exc:
            return ExtractionResult(None, "parse_error", str(exc))
        normalized["answers"] = [
            {"property": name, **value} for name, value in submitted.items()
        ]
    elif "answer" in payload or "unit" in payload:
        normalized.update(
            {key: payload[key] for key in ("answer", "unit") if key in payload}
        )
    else:
        return ExtractionResult(None, "parse_error", "property answer must include answer or answers")
    if raw_answer is not None:
        normalized["raw_answer"] = raw_answer
        normalized["extracted_answer"] = extracted_answer
    return ExtractionResult(normalized, None, None)
