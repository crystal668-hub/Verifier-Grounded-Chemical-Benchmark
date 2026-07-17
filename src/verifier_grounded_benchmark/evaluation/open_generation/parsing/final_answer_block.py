"""Fenced FINAL ANSWER block parsing for XYZ and CIF candidates."""

from __future__ import annotations

import re
from typing import Any, Mapping


def parse_final_answer_block(raw_answer: str, schema: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    prefix = schema.get("final_answer_prefix")
    if not isinstance(prefix, str) or not prefix:
        raise ValueError("answer_schema must include final_answer_prefix")
    value_type = schema.get("value_type")
    if value_type not in {"cif", "xyz"}:
        raise ValueError(f"unsupported answer_schema value_type: {value_type!r}")
    prefix_index = raw_answer.rfind(prefix)
    if prefix_index < 0:
        raise ValueError(f"missing final answer block with prefix {prefix!r}")
    fence_language = schema.get("fence_language", value_type)
    if not isinstance(fence_language, str) or not fence_language:
        raise ValueError("answer_schema must include fence_language")
    match = re.search(
        rf"^[ \t]*```{re.escape(fence_language)}[ \t]*\r?\n(?P<value>.*?)(?:\r?\n)?^[ \t]*```[ \t]*$",
        raw_answer[prefix_index + len(prefix) :],
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError(f"missing fenced {fence_language} block after final answer prefix")
    extracted = match.group("value").strip()
    if not extracted:
        raise ValueError(f"final answer {value_type} block is empty")
    return {value_type: extracted}, extracted
