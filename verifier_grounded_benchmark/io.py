from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_tasks_file(path: str | Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml_mapping(path)
    items = _require_list(data, "tasks", path)
    return _index_by_id(items, "task_id", path)


def load_verifier_specs_file(path: str | Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml_mapping(path)
    items = _require_list(data, "verifiers", path)
    return _index_by_id(items, "verifier_id", path)


def load_answers_jsonl_file(path: str | Path) -> list[dict[str, Any]]:
    answer_path = Path(path)
    answers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    try:
        lines = answer_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Could not read answers file {answer_path}: {exc}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in answers file {answer_path} on line {line_number}: "
                f"{exc.msg}"
            ) from exc
        if not isinstance(item, dict):
            raise ValueError(
                f"Expected JSON object in answers file {answer_path} on line "
                f"{line_number}"
            )
        task_id = item.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(
                f"Answer in {answer_path} on line {line_number} must have a "
                "non-empty string task_id"
            )
        if task_id in seen_ids:
            raise ValueError(f"Duplicate answer task_id {task_id!r} in {answer_path}")
        seen_ids.add(task_id)
        answers.append(item)

    return answers


def _load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    yaml_path = Path(path)
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML file {yaml_path}: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Could not read YAML file {yaml_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level mapping in {yaml_path}")
    return data


def _require_list(data: dict[str, Any], key: str, path: str | Path) -> list[Any]:
    items = data.get(key)
    if not isinstance(items, list):
        raise ValueError(f"Expected top-level {key!r} list in {path}")
    return items


def _index_by_id(
    items: list[Any],
    id_key: str,
    path: str | Path,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Expected mapping at {path} item {index}")
        item_id = item.get(id_key)
        if not isinstance(item_id, str) or not item_id:
            raise ValueError(
                f"Item {index} in {path} must have a non-empty string {id_key}"
            )
        if item_id in indexed:
            raise ValueError(f"Duplicate {id_key} {item_id!r} in {path}")
        indexed[item_id] = item
    return indexed
