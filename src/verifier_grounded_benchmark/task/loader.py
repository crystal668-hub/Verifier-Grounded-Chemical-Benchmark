"""Task-pack configuration loading and one-time schema validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from verifier_grounded_benchmark.task.models import (
    OpenGenerationTaskSpec,
    PropertyCalculationTaskSpec,
    TaskPack,
    TaskSpec,
    VerifierSpec,
    freeze_mapping,
)
from verifier_grounded_benchmark.task.schema.common import (
    SCORING_VERSION,
    index_unique,
    require_list,
    require_mapping,
    require_string,
    validate_profiles,
)
from verifier_grounded_benchmark.task.schema.open_generation import validate_open_generation_task
from verifier_grounded_benchmark.task.schema.property_calculation import (
    validate_property_calculation_task,
)
from verifier_grounded_benchmark.task.schema.verifier import validate_verifier_specs


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_task_pack(tasks_resource: Any, verifier_resource: Any) -> TaskPack:
    task_data = _load_yaml_mapping(tasks_resource)
    verifier_data = _load_yaml_mapping(verifier_resource)
    if task_data.get("schema_version") == 2:
        task_data = _load_yaml_mapping(tasks_resource, require_unique_keys=True)
        return _load_v2(task_data, verifier_data)
    return _load_legacy(task_data, verifier_data, source=str(tasks_resource))


def load_tasks_file(resource: Any) -> dict[str, dict[str, Any]]:
    data = _load_yaml_mapping(resource)
    return index_unique(require_list(data.get("tasks"), "tasks"), "task_id", "task")


def load_verifier_specs_file(resource: Any) -> dict[str, dict[str, Any]]:
    data = _load_yaml_mapping(resource)
    items = data.get("verifiers")
    if not isinstance(items, list):
        raise ValueError("verifiers must be a list")
    return validate_verifier_specs(items)


def load_answers_jsonl_file(resource: Any) -> list[dict[str, Any]]:
    text = _read_text(resource, "answers")
    answers: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON on line {line_number}: {exc.msg}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Expected JSON object on line {line_number}")
        require_string(item.get("task_id"), f"answer line {line_number} task_id")
        answers.append(item)
    return answers


def task_pack_from_mappings(
    tasks: dict[str, dict[str, Any]], verifier_specs: dict[str, dict[str, Any]]
) -> TaskPack:
    return _load_legacy(
        {"tasks": list(tasks.values())},
        {"verifiers": list(verifier_specs.values())},
        source="legacy mappings",
    )


def _load_v2(task_data: dict[str, Any], verifier_data: dict[str, Any]) -> TaskPack:
    metadata = require_mapping(task_data.get("task_pack"), "task_pack")
    pack_id = require_string(metadata.get("id"), "task_pack id")
    version = require_string(metadata.get("version"), "task_pack version")
    scoring_version = require_string(metadata.get("scoring_version"), "task_pack scoring_version")
    if scoring_version != SCORING_VERSION:
        raise ValueError(f"unsupported scoring version: {scoring_version}")
    profiles = validate_profiles(task_data.get("scoring_profiles"))
    verifier_items = verifier_data.get("verifiers")
    if not isinstance(verifier_items, list):
        raise ValueError("verifiers must be a list")
    verifiers_by_id = validate_verifier_specs(verifier_items)
    tasks_by_id = index_unique(
        require_list(task_data.get("tasks"), "tasks"), "task_id", "task"
    )
    tasks: list[TaskSpec] = []
    for task_id, raw in tasks_by_id.items():
        task_type = require_string(raw.get("task_type"), f"task {task_id} task_type")
        frozen = freeze_mapping(raw)
        if task_type == "open_generation":
            constraints = validate_open_generation_task(raw, profiles, set(verifiers_by_id))
            tasks.append(OpenGenerationTaskSpec(task_id, task_type, frozen, constraints))
        elif task_type == "property_calculation":
            validate_property_calculation_task(raw, profiles)
            tasks.append(PropertyCalculationTaskSpec(task_id, task_type, frozen))
        else:
            raise ValueError(f"unsupported task_type for {task_id}: {task_type}")
    verifier_specs = [
        VerifierSpec(verifier_id, freeze_mapping(raw))
        for verifier_id, raw in verifiers_by_id.items()
    ]
    return TaskPack.create(
        schema_version=2,
        pack_id=pack_id,
        version=version,
        scoring_version=scoring_version,
        tasks=tasks,
        verifier_specs=verifier_specs,
        scoring_profiles=profiles,
    )


def _load_legacy(
    task_data: dict[str, Any], verifier_data: dict[str, Any], *, source: str
) -> TaskPack:
    tasks_by_id = index_unique(
        require_list(task_data.get("tasks"), f"legacy tasks in {source}"), "task_id", "task"
    )
    verifier_items = verifier_data.get("verifiers")
    if not isinstance(verifier_items, list):
        raise ValueError("legacy verifiers must be a list")
    verifiers_by_id = validate_verifier_specs(verifier_items)
    tasks: list[TaskSpec] = []
    for task_id, raw in tasks_by_id.items():
        task_type = raw.get("task_type", "open_generation")
        frozen = freeze_mapping(raw)
        if task_type == "property_calculation":
            tasks.append(PropertyCalculationTaskSpec(task_id, task_type, frozen))
        else:
            tasks.append(OpenGenerationTaskSpec(task_id, "open_generation", frozen, ()))
    return TaskPack.create(
        schema_version=1,
        pack_id=Path(source).parent.name or "legacy",
        version="legacy",
        scoring_version="legacy_v1",
        tasks=tasks,
        verifier_specs=[
            VerifierSpec(verifier_id, freeze_mapping(raw))
            for verifier_id, raw in verifiers_by_id.items()
        ],
        scoring_profiles={},
    )


def _load_yaml_mapping(
    resource: Any, *, require_unique_keys: bool = False
) -> dict[str, Any]:
    try:
        loader = _UniqueKeyLoader if require_unique_keys else yaml.SafeLoader
        data = yaml.load(_read_text(resource, "YAML"), Loader=loader)
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML in {resource}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level mapping in {resource}")
    return data


def _read_text(resource: Any, label: str) -> str:
    try:
        return resource.read_text(encoding="utf-8")
    except TypeError:
        return resource.read_text()
    except AttributeError:
        try:
            return Path(resource).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Could not read {label} resource {resource}: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Could not read {label} resource {resource}: {exc}") from exc
