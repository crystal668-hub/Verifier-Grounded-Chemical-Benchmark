"""Validation shared by task-pack schema v2 topics."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Mapping

from verifier_grounded_benchmark.task.models import LinearGoalSpec


SCORING_VERSION = "linear_goal_v1"
PROFILE_TYPES = {"target", "window", "maximize", "minimize", "numeric_gold", "exact_string"}


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


def validate_profiles(profiles: Any) -> dict[str, dict[str, Any]]:
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
        provenance = require_mapping(profile.get("provenance"), f"scoring profile {profile_id} provenance")
        require_string(provenance.get("target_source"), f"scoring profile {profile_id} target_source")
        require_string(provenance.get("decay_source"), f"scoring profile {profile_id} decay_source")
        if profile_type == "exact_string":
            if profile.get("normalization") != "exact":
                raise ValueError(f"exact string profile {profile_id} must use exact normalization")
        else:
            require_string(profile.get("unit"), f"scoring profile {profile_id} unit")
    return dict(mappings)


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
