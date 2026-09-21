"""Validation shared by task-pack schema v2 topics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from numbers import Real
from typing import Any

from verifier_grounded_benchmark.task.models import LinearGoalSpec

SCORING_VERSION = "linear_goal_v1"
SUPPORTED_SCORING_VERSIONS = frozenset({"linear_goal_v1", "linear_goal_v2"})
SUPPORTED_SCORING_STATUSES = frozenset({"formal", "shadow_pending_research"})
PROFILE_TYPES = {
    "target",
    "window",
    "maximize",
    "minimize",
    "numeric_gold",
    "exact_string",
    "atom_identity",
}


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def index_unique(items: list[Any], key: str, label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        mapping = require_mapping(item, f"{label} entry")
        item_id = require_string(mapping.get(key), f"{label} {key}")
        if item_id in indexed:
            raise ValueError(f"duplicate {label}: {item_id}")
        indexed[item_id] = mapping
    return indexed


def validate_profiles(
    profiles: Any,
    *,
    scoring_version: str = SCORING_VERSION,
    scoring_status: str = "formal",
) -> dict[str, dict[str, Any]]:
    mappings = require_mapping(profiles, "scoring_profiles")
    if not mappings:
        raise ValueError("scoring_profiles must not be empty")
    for profile_id, raw in mappings.items():
        require_string(profile_id, "scoring profile id")
        profile = require_mapping(raw, f"scoring profile {profile_id}")
        profile_type = profile.get("type")
        if profile_type not in PROFILE_TYPES:
            raise ValueError(f"unsupported scoring profile type for {profile_id}: {profile_type}")
        require_string(profile.get("property"), f"scoring profile {profile_id} property")
        if "minimum_value" in profile:
            if profile_type != "numeric_gold":
                raise ValueError(f"minimum_value is only supported for numeric_gold: {profile_id}")
            _finite(profile["minimum_value"], f"scoring profile {profile_id} minimum_value")
        provenance = require_mapping(profile.get("provenance"), f"scoring profile {profile_id} provenance")
        require_string(provenance.get("target_source"), f"scoring profile {profile_id} target_source")
        require_string(provenance.get("decay_source"), f"scoring profile {profile_id} decay_source")
        if scoring_version == "linear_goal_v2" and scoring_status == "formal":
            if provenance.get("review_status") != "approved":
                raise ValueError(
                    f"formal v2 scoring profile {profile_id} must have approved review_status"
                )
            if (
                str(provenance["target_source"]).startswith("legacy_")
                or str(provenance["decay_source"]).startswith("legacy_")
                or "legacy_parameters" in provenance
            ):
                raise ValueError(
                    f"formal v2 scoring profile {profile_id} cannot use legacy provenance"
                )
            for field in ("decision_record", "review_date", "review_owner"):
                require_string(provenance.get(field), f"scoring profile {profile_id} {field}")
        if profile_type == "exact_string":
            if profile.get("normalization") != "exact":
                raise ValueError(f"exact string profile {profile_id} must use exact normalization")
            partial_scores = profile.get("partial_scores", {})
            if not isinstance(partial_scores, Mapping):
                raise ValueError(f"exact string profile {profile_id} partial_scores must be an object")
            for value, partial_score in partial_scores.items():
                if (
                    not isinstance(value, str)
                    or isinstance(partial_score, bool)
                    or not isinstance(partial_score, Real)
                ):
                    raise ValueError(f"exact string profile {profile_id} partial_scores must map strings to numbers")
                if not 0.0 <= float(partial_score) < 1.0:
                    raise ValueError(f"exact string profile {profile_id} partial scores must be in [0, 1)")
        elif profile_type == "atom_identity":
            if profile.get("normalization") != "atom_identity":
                raise ValueError(
                    f"atom identity profile {profile_id} must use atom_identity normalization"
                )
            partial_score = profile.get("element_partial_score", 0.0)
            if (
                isinstance(partial_score, bool)
                or not isinstance(partial_score, Real)
                or not 0.0 <= float(partial_score) < 1.0
            ):
                raise ValueError(
                    f"atom identity profile {profile_id} element_partial_score must be in [0, 1)"
                )
        else:
            require_string(profile.get("unit"), f"scoring profile {profile_id} unit")
            transform = profile.get("value_transform", "identity")
            if transform not in {"identity", "absolute", "log10"}:
                raise ValueError(f"unsupported value_transform for {profile_id}: {transform}")
            if profile_type != "numeric_gold" and transform != "identity":
                raise ValueError(f"value_transform is only supported for numeric_gold: {profile_id}")
    return dict(mappings)


def validate_family_policy(
    policy: Any,
    tasks: Mapping[str, Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
) -> None:
    families = require_mapping(policy, "family policy")
    family_items = require_mapping(families.get("families"), "family policy families")
    selectors: dict[tuple[str, str], tuple[str, Mapping[str, Any]]] = {}
    for family_name, raw_family in family_items.items():
        family = require_mapping(raw_family, f"family policy {family_name}")
        mode = family.get("mode")
        if mode not in {"absolute", "relative", "log10"}:
            raise ValueError(f"unsupported family policy mode for {family_name}: {mode}")
        _positive(family.get("parameter"), f"family policy {family_name} parameter")
        _positive(family.get("upper_parameter", family["parameter"]), f"family policy {family_name} upper_parameter")
        properties = require_list(family.get("properties"), f"family policy {family_name} properties")
        units = require_list(family.get("units"), f"family policy {family_name} units")
        for property_name in properties:
            require_string(property_name, f"family policy {family_name} property")
            for unit in units:
                require_string(unit, f"family policy {family_name} unit")
                selector = (property_name, unit)
                if selector in selectors:
                    raise ValueError(f"duplicate family policy selector: {selector}")
                selectors[selector] = (str(family_name), family)

    seen_profiles: set[str] = set()
    for task_id, task in tasks.items():
        if task.get("task_type") != "property_calculation":
            continue
        gold_by_property = index_unique(require_list(task.get("gold_answers"), f"task {task_id} gold_answers"), "property", f"task {task_id} gold")
        requested = index_unique(require_list(task.get("requested_properties"), f"task {task_id} requested_properties"), "name", f"task {task_id} requested")
        for property_name, definition in requested.items():
            if definition.get("value_type") != "number":
                continue
            gold = gold_by_property[property_name]
            profile_id = require_string(gold.get("scoring_profile"), "gold scoring_profile")
            profile = profiles[profile_id]
            unit = require_string(definition.get("unit"), f"numeric property {property_name} unit")
            try:
                family_name, family = selectors[(property_name, unit)]
            except KeyError as exc:
                raise ValueError(f"family policy has no selector for {(property_name, unit)}") from exc
            provenance = require_mapping(profile.get("provenance"), f"scoring profile {profile_id} provenance")
            if provenance.get("tolerance_family") != family_name:
                raise ValueError(f"scoring profile {profile_id} family does not match family policy")
            mode = family["mode"]
            expected_transform = "log10" if mode == "log10" else "identity"
            if profile.get("value_transform", "identity") != expected_transform:
                raise ValueError(f"scoring profile {profile_id} transform does not match family policy")
            scale = abs(float(gold["value"])) if mode == "relative" else 1.0
            expected_lower = float(family["parameter"]) * scale
            expected_upper = float(family.get("upper_parameter", family["parameter"])) * scale
            if not math.isclose(float(profile["lower_tolerance"]), expected_lower, rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"scoring profile {profile_id} lower_tolerance does not match family policy")
            if not math.isclose(float(profile["upper_tolerance"]), expected_upper, rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"scoring profile {profile_id} upper_tolerance does not match family policy")
            seen_profiles.add(profile_id)
    if not seen_profiles:
        raise ValueError("family policy did not validate any numeric property profile")


def linear_goal_from_profile(profile: Mapping[str, Any], *, gold: Any = None) -> LinearGoalSpec:
    profile_type = profile["type"]
    if profile_type == "window":
        full_score = require_mapping(profile.get("full_score"), "window full_score")
        decay = require_mapping(profile.get("decay"), "window decay")
        return LinearGoalSpec(
            lower=_finite(full_score.get("min"), "window min"),
            upper=_finite(full_score.get("max"), "window max"),
            lower_width=_optional_positive(decay.get("lower_width"), "lower_width"),
            upper_width=_optional_positive(decay.get("upper_width"), "upper_width"),
        )
    if profile_type == "target":
        target = _finite(profile.get("full_score_target"), "full_score_target")
        decay = require_mapping(profile.get("decay"), "target decay")
        return LinearGoalSpec(
            lower=target,
            upper=target,
            lower_width=_positive(decay.get("lower_width"), "lower_width"),
            upper_width=_positive(decay.get("upper_width"), "upper_width"),
        )
    if profile_type == "maximize":
        target = _finite(profile.get("full_score_target"), "full_score_target")
        anchor = _finite(profile.get("zero_score_anchor"), "zero_score_anchor")
        if anchor >= target:
            raise ValueError("maximize zero_score_anchor must be below target")
        return LinearGoalSpec(target, None, target - anchor, None)
    if profile_type == "minimize":
        target = _finite(profile.get("full_score_target"), "full_score_target")
        anchor = _finite(profile.get("zero_score_anchor"), "zero_score_anchor")
        if anchor <= target:
            raise ValueError("minimize zero_score_anchor must be above target")
        return LinearGoalSpec(None, target, None, anchor - target)
    if profile_type == "numeric_gold":
        numeric_gold = _finite(gold, "numeric gold")
        return LinearGoalSpec(
            numeric_gold,
            numeric_gold,
            _positive(profile.get("lower_tolerance"), "lower_tolerance"),
            _positive(profile.get("upper_tolerance"), "upper_tolerance"),
        )
    raise ValueError(f"profile type {profile_type} does not define a linear goal")


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _positive(value: Any, label: str) -> float:
    number = _finite(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _optional_positive(value: Any, label: str) -> float | None:
    if value is None:
        return None
    return _positive(value, label)
