from __future__ import annotations

from copy import deepcopy
from importlib.resources import files

import pytest

import verifier_grounded_benchmark as vgb
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource
from verifier_grounded_benchmark.task.schema.common import linear_goal_from_profile


def _load(pack: str):
    return load_task_pack(
        package_resource(pack, "tasks.yaml"),
        package_resource(pack, "verifier_specs.yaml"),
    )


def test_four_top_level_packs_cover_exactly_33_unique_tasks() -> None:
    packs = [
        _load("rdkit"),
        _load("xtb"),
        _load("property_calculation"),
        _load("experimental/rdkit_forcefield"),
    ]
    task_ids = [task.task_id for pack in packs for task in pack.tasks]

    assert len(task_ids) == 33
    assert len(set(task_ids)) == 33
    assert all(pack.schema_version == 2 for pack in packs)
    assert all(pack.scoring_version == "linear_goal_v1" for pack in packs)


def test_all_numeric_constraints_normalize_to_linear_goal() -> None:
    for pack_name in ("rdkit", "xtb", "experimental/rdkit_forcefield"):
        pack = _load(pack_name)
        for task in pack.tasks:
            for constraint in task.raw["constraints"]:
                profile = pack.scoring_profiles[constraint["scoring_profile"]]
                assert linear_goal_from_profile(profile)


def test_property_calculation_profiles_bind_numeric_and_exact_string_policies() -> None:
    pack = _load("property_calculation")
    for task in pack.tasks:
        requested = {item["name"]: item for item in task.raw["requested_properties"]}
        for gold in task.raw["gold_answers"]:
            profile = pack.scoring_profiles[gold["scoring_profile"]]
            if requested[gold["property"]]["value_type"] == "number":
                assert profile["type"] == "numeric_gold"
                assert linear_goal_from_profile(profile, gold=gold["value"])
            else:
                assert profile["type"] == "exact_string"
                assert profile["normalization"] == "exact"


def test_repeated_semantics_reuse_one_profile() -> None:
    rdkit = _load("rdkit")
    logp_profiles = {
        constraint["scoring_profile"]
        for task in rdkit.tasks
        for constraint in task.raw["constraints"]
        if constraint["property"] == "logp" and constraint["type"] == "window"
    }
    assert len(logp_profiles) == 1

    xtb = _load("xtb")
    relaxation_profiles = {
        constraint["scoring_profile"]
        for task in xtb.tasks
        for constraint in task.raw["constraints"]
        if constraint["role"] == "quality_gate"
    }
    assert len(relaxation_profiles) == 1


def test_calibration_duplicates_reuse_formal_profiles() -> None:
    formal = _load("xtb")
    calibration = load_task_pack(
        files("verifier_grounded_benchmark.task.calibration.xtb").joinpath("tasks.yaml"),
        files("verifier_grounded_benchmark.task.calibration.xtb").joinpath("verifier_specs.yaml"),
    )
    formal_tasks = formal.tasks_by_id
    for task_id, calibration_task in calibration.tasks_by_id.items():
        formal_task = formal_tasks[task_id]
        assert [item["scoring_profile"] for item in calibration_task["constraints"]] == [
            item["scoring_profile"] for item in formal_task["constraints"]
        ]
        for constraint in calibration_task["constraints"]:
            profile_id = constraint["scoring_profile"]
            assert calibration.scoring_profiles[profile_id] == formal.scoring_profiles[profile_id]


def test_public_tracks_use_validated_v2_package_resources() -> None:
    assert len(vgb.load_track("rdkit").tasks()) == 11
    assert vgb.load_track("rdkit")._task_pack.schema_version == 2


def test_task_pack_is_immutable_and_accessors_return_copies() -> None:
    pack = _load("rdkit")
    with pytest.raises(TypeError):
        pack.tasks[0].raw["prompt"] = "mutated"  # type: ignore[index]

    copied = pack.tasks_by_id
    copied[pack.tasks[0].task_id]["prompt"] = "mutated"
    assert pack.tasks[0].raw["prompt"] != "mutated"


def test_v2_loader_rejects_static_profile_errors(tmp_path) -> None:
    task_resource = package_resource("rdkit", "tasks.yaml")
    data = __import__("yaml").safe_load(task_resource.read_text(encoding="utf-8"))
    broken = deepcopy(data)
    profile = next(iter(broken["scoring_profiles"].values()))
    profile["zero_score_anchor"] = profile["full_score_target"]
    tasks_path = tmp_path / "tasks.yaml"
    tasks_path.write_text(__import__("yaml").safe_dump(broken), encoding="utf-8")

    with pytest.raises(ValueError, match="zero_score_anchor"):
        load_task_pack(tasks_path, package_resource("rdkit", "verifier_specs.yaml"))
