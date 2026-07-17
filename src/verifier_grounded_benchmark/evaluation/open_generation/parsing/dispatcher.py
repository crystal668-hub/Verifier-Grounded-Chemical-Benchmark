"""Open-generation parser dispatch by answer schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from verifier_grounded_benchmark.evaluation.open_generation.parsing.final_answer_block import (
    parse_final_answer_block,
)
from verifier_grounded_benchmark.evaluation.open_generation.parsing.final_answer_line import (
    parse_final_answer_line,
)
from verifier_grounded_benchmark.evaluation.open_generation.parsing.structured_candidates import (
    parse_structured_candidates,
)


@dataclass(frozen=True)
class ParsedCandidates:
    candidates: list[dict[str, Any]]
    raw_answer: str | None = None
    extracted_answer: str | None = None


@dataclass(frozen=True)
class ExtractionResult:
    answer: dict[str, Any] | None
    failure_type: str | None
    message: str | None

    @property
    def ok(self) -> bool:
        return self.answer is not None


def parse_answer(record: dict[str, Any], task: Mapping[str, Any]) -> ParsedCandidates:
    if "candidates" in record:
        return ParsedCandidates(parse_structured_candidates(record))
    raw_answer = record.get("response", record.get("raw_answer"))
    if not isinstance(raw_answer, str):
        raise ValueError("answer record must include candidates or a raw response string")
    schema = task.get("answer_schema")
    if not isinstance(schema, Mapping):
        raise ValueError("task must include answer_schema")
    schema_format = schema.get("format")
    if schema_format == "final_answer_line":
        candidate, extracted = parse_final_answer_line(raw_answer, schema)
    elif schema_format == "final_answer_block":
        candidate, extracted = parse_final_answer_block(raw_answer, schema)
    else:
        raise ValueError("unsupported answer_schema format")
    return ParsedCandidates([candidate], raw_answer, extracted)


def normalize_answer_record(
    record: dict[str, Any], task: Mapping[str, Any]
) -> ExtractionResult:
    try:
        parsed = parse_answer(record, task)
    except ValueError as exc:
        return ExtractionResult(None, "parse_error", str(exc))
    if "candidates" in record:
        return ExtractionResult(record, None, None)
    normalized = {
        "task_id": record.get("task_id"),
        "candidates": parsed.candidates,
    }
    if parsed.raw_answer is not None:
        normalized["raw_answer"] = parsed.raw_answer
    if parsed.extracted_answer is not None:
        normalized["extracted_answer"] = parsed.extracted_answer
    return ExtractionResult(normalized, None, None)
