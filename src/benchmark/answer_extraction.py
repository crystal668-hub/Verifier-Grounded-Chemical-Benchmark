"""Normalize raw model responses into verifier-ready answer records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractionResult:
    answer: dict[str, Any] | None
    failure_type: str | None
    message: str | None

    @property
    def ok(self) -> bool:
        return self.answer is not None


def normalize_answer_record(record: dict[str, Any], task: dict[str, Any]) -> ExtractionResult:
    if "candidates" in record:
        return ExtractionResult(record, None, None)

    raw_answer = record.get("response", record.get("raw_answer"))
    if not isinstance(raw_answer, str):
        return ExtractionResult(None, "parse_error", "answer record must include candidates or a raw response string")

    schema = task.get("answer_schema") or {}
    schema_format = schema.get("format")
    if schema_format == "final_answer_block":
        return normalize_final_answer_block(record, raw_answer, schema)
    if schema_format != "final_answer_line":
        return ExtractionResult(None, "parse_error", "unsupported answer_schema format")

    prefix = schema.get("final_answer_prefix")
    if not isinstance(prefix, str) or not prefix:
        return ExtractionResult(None, "parse_error", "answer_schema must include final_answer_prefix")

    final_lines = [line for line in raw_answer.splitlines() if line.startswith(prefix)]
    if not final_lines:
        return ExtractionResult(None, "parse_error", f"missing final answer line with prefix {prefix!r}")

    extracted = final_lines[-1][len(prefix) :].strip()
    if not extracted:
        return ExtractionResult(None, "parse_error", "final answer line is empty")

    value_type = schema.get("value_type")
    candidate: dict[str, Any]
    if value_type == "smiles":
        candidate = {"smiles": extracted}
    elif value_type == "json":
        try:
            candidate = {"json": json.loads(extracted)}
        except json.JSONDecodeError as exc:
            return ExtractionResult(None, "parse_error", f"invalid JSON final answer: {exc.msg}")
    elif value_type == "number":
        try:
            candidate = {"value": float(extracted), "raw_value": extracted}
        except ValueError:
            return ExtractionResult(None, "parse_error", f"invalid numeric final answer: {extracted!r}")
    else:
        return ExtractionResult(None, "parse_error", f"unsupported answer_schema value_type: {value_type!r}")

    return ExtractionResult(
        {
            "task_id": record.get("task_id"),
            "candidates": [candidate],
            "raw_answer": raw_answer,
            "extracted_answer": extracted,
        },
        None,
        None,
    )


def normalize_final_answer_block(record: dict[str, Any], raw_answer: str, schema: dict[str, Any]) -> ExtractionResult:
    prefix = schema.get("final_answer_prefix")
    if not isinstance(prefix, str) or not prefix:
        return ExtractionResult(None, "parse_error", "answer_schema must include final_answer_prefix")
    value_type = schema.get("value_type")
    if value_type not in {"cif", "xyz"}:
        return ExtractionResult(None, "parse_error", f"unsupported answer_schema value_type: {value_type!r}")

    prefix_index = raw_answer.rfind(prefix)
    if prefix_index < 0:
        return ExtractionResult(None, "parse_error", f"missing final answer block with prefix {prefix!r}")
    block_text = raw_answer[prefix_index + len(prefix) :]
    fence_language = schema.get("fence_language", "cif")
    if not isinstance(fence_language, str) or not fence_language:
        return ExtractionResult(None, "parse_error", "answer_schema must include fence_language")

    match = re.search(
        rf"^[ \t]*```{re.escape(fence_language)}[ \t]*\r?\n(?P<value>.*?)(?:\r?\n)?^[ \t]*```[ \t]*$",
        block_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return ExtractionResult(None, "parse_error", f"missing fenced {fence_language} block after final answer prefix")

    extracted = match.group("value").strip()
    if not extracted:
        return ExtractionResult(None, "parse_error", f"final answer {value_type} block is empty")

    return ExtractionResult(
        {
            "task_id": record.get("task_id"),
            "candidates": [{value_type: extracted}],
            "raw_answer": raw_answer,
            "extracted_answer": extracted,
        },
        None,
        None,
    )
