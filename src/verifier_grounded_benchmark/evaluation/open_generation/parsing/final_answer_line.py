"""FINAL ANSWER line parsing for scalar and JSON candidates."""

from __future__ import annotations

import json
from typing import Any, Mapping


def parse_final_answer_line(raw_answer: str, schema: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    prefix = schema.get("final_answer_prefix")
    if not isinstance(prefix, str) or not prefix:
        raise ValueError("answer_schema must include final_answer_prefix")
    final_lines = [line for line in raw_answer.splitlines() if line.startswith(prefix)]
    if not final_lines:
        raise ValueError(f"missing final answer line with prefix {prefix!r}")
    extracted = final_lines[-1][len(prefix) :].strip()
    if not extracted:
        raise ValueError("final answer line is empty")
    value_type = schema.get("value_type")
    if value_type == "smiles":
        return {"smiles": extracted}, extracted
    if value_type == "json":
        try:
            return {"json": json.loads(extracted)}, extracted
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON final answer: {exc.msg}") from exc
    if value_type == "number":
        try:
            return {"value": float(extracted), "raw_value": extracted}, extracted
        except ValueError as exc:
            raise ValueError(f"invalid numeric final answer: {extracted!r}") from exc
    raise ValueError(f"unsupported answer_schema value_type: {value_type!r}")
