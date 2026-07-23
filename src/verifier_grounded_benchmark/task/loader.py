"""Task-pack configuration loading and one-time schema validation."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from verifier_grounded_benchmark.task.models import (
    ConstraintSpec,
    OpenGenerationTaskSpec,
    PropertyCalculationTaskSpec,
    TaskPack,
    TaskSpec,
    VerifierSpec,
    freeze_mapping,
)
from verifier_grounded_benchmark.task.schema.common import (
    SCORING_VERSION,
    SUPPORTED_SCORING_STATUSES,
    SUPPORTED_SCORING_VERSIONS,
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
    profiles: dict[str, dict[str, Any]] = {}
    migrated_tasks: list[TaskSpec] = []
    for task_id, source in tasks.items():
        raw = deepcopy(source)
        task_type = raw.get("task_type", "open_generation")
        if task_type == "property_calculation":
            requested = {item["name"]: item for item in raw["requested_properties"]}
            for gold in raw["gold_answers"]:
                profile_id = f"legacy_{task_id}_{gold['property']}"
                if requested[gold["property"]]["value_type"] == "number":
                    tolerance = gold.pop("absolute_tolerance")
                    profiles[profile_id] = {
                        "property": gold["property"],
                        "type": "numeric_gold",
                        "unit": gold["unit"],
                        "lower_tolerance": tolerance,
                        "upper_tolerance": tolerance,
                    }
                else:
                    profiles[profile_id] = {
                        "property": gold["property"],
                        "type": "exact_string",
                        "normalization": "exact",
                    }
                gold["scoring_profile"] = profile_id
            raw["task_type"] = task_type
            migrated_tasks.append(
                PropertyCalculationTaskSpec(task_id, task_type, freeze_mapping(raw))
            )
            continue
        constraints: list[ConstraintSpec] = []
        for index, constraint in enumerate(raw.get("constraints") or []):
            old = dict(constraint)
            new_type, profile = _legacy_constraint_profile(old)
            profile_id = f"legacy_{task_id}_{index}"
            profiles[profile_id] = profile
            replacement = {
                "type": new_type,
                "property": old["property"],
                "verifier_id": old["verifier_id"],
                "role": old.get("role", "main"),
                "scoring_profile": profile_id,
            }
            constraint.clear()
            constraint.update(replacement)
            constraints.append(
                ConstraintSpec(
                    old["property"],
                    new_type,
                    replacement["role"],
                    old["verifier_id"],
                    profile_id,
                )
            )
        raw["task_type"] = "open_generation"
        migrated_tasks.append(
            OpenGenerationTaskSpec(
                task_id, "open_generation", freeze_mapping(raw), tuple(constraints)
            )
        )
    return TaskPack.create(
        schema_version=2,
        pack_id="legacy_mappings",
        version="legacy_migrated",
        scoring_version=SCORING_VERSION,
        tasks=migrated_tasks,
        verifier_specs=[
            VerifierSpec(verifier_id, freeze_mapping(raw))
            for verifier_id, raw in verifier_specs.items()
        ],
        scoring_profiles=profiles,
    )


def _legacy_constraint_profile(
    constraint: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    kind = constraint["type"]
    common = {"property": constraint["property"], "unit": "legacy_unit"}
    if kind == "window":
        return "window", {
            **common,
            "type": "window",
            "full_score": {"min": constraint["min"], "max": constraint["max"]},
            "decay": {
                "lower_width": 2 * constraint["sigma"],
                "upper_width": 2 * constraint["sigma"],
            },
        }
    if kind == "target_distance":
        return "target", {
            **common,
            "type": "target",
            "full_score_target": constraint["target"],
            "decay": {
                "lower_width": 2 * constraint["scale"],
                "upper_width": 2 * constraint["scale"],
            },
        }
    if kind == "maximize_bounded":
        return "maximize", {
            **common,
            "type": "maximize",
            "full_score_target": constraint["upper"],
            "zero_score_anchor": constraint["lower"],
        }
    if kind == "minimize_bounded":
        return "minimize", {
            **common,
            "type": "minimize",
            "full_score_target": constraint["lower"],
            "zero_score_anchor": constraint["upper"],
        }
    raise ValueError(f"unsupported legacy constraint type: {kind}")


def _load_v2(task_data: dict[str, Any], verifier_data: dict[str, Any]) -> TaskPack:
    metadata = require_mapping(task_data.get("task_pack"), "task_pack")
    pack_id = require_string(metadata.get("id"), "task_pack id")
    version = require_string(metadata.get("version"), "task_pack version")
    scoring_version = require_string(metadata.get("scoring_version"), "task_pack scoring_version")
    if scoring_version not in SUPPORTED_SCORING_VERSIONS:
        raise ValueError(f"unsupported scoring version: {scoring_version}")
    scoring_status = metadata.get("scoring_status", "formal")
    if scoring_status not in SUPPORTED_SCORING_STATUSES:
        raise ValueError(f"unsupported scoring status: {scoring_status}")
    profiles = validate_profiles(
        task_data.get("scoring_profiles"),
        scoring_version=scoring_version,
        scoring_status=scoring_status,
    )
    verifier_items = verifier_data.get("verifiers")
    if not isinstance(verifier_items, list):
        raise ValueError("verifiers must be a list")
    verifiers_by_id = validate_verifier_specs(
        verifier_items, require_module_executor=True
    )
    tasks_by_id = index_unique(
        require_list(task_data.get("tasks"), "tasks"), "task_id", "task"
    )
    tasks: list[TaskSpec] = []
    for task_id, raw in tasks_by_id.items():
        task_type = require_string(raw.get("task_type"), f"task {task_id} task_type")
        scoring = require_mapping(raw.get("scoring"), f"task {task_id} scoring")
        task_scoring_version = require_string(
            scoring.get("version"), f"task {task_id} scoring version"
        )
        if task_scoring_version != scoring_version:
            raise ValueError(
                f"task {task_id} scoring version {task_scoring_version} "
                f"does not match task_pack scoring_version {scoring_version}"
            )
        frozen = freeze_mapping(raw)
        if task_type == "open_generation":
            constraints, hard_constraints = validate_open_generation_task(
                raw, profiles, set(verifiers_by_id)
            )
            tasks.append(
                OpenGenerationTaskSpec(
                    task_id, task_type, frozen, constraints, hard_constraints
                )
            )
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
