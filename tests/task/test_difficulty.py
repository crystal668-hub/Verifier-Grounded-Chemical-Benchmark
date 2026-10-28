from importlib.resources import files

import pytest
import yaml

from verifier_grounded_benchmark.task.loader import (
    load_task_pack,
    load_tasks_file,
    task_pack_from_mappings,
)
from verifier_grounded_benchmark.task.resources import package_resource


@pytest.mark.parametrize("pack,cutoff,total", [
    ("open_generation_rdkit", 6, 10),
    ("open_generation_xtb", 13, 20),
    ("property_calculation_basic", 51, 51),
    ("property_calculation_advanced", 0, 19),
])
def test_formal_tasks_use_declared_two_level_classification(pack, cutoff, total):
    tasks = load_tasks_file(package_resource(pack, "tasks.yaml"))
    assert len(tasks) == total
    for task_id, task in tasks.items():
        parts = task_id.split("_")
        number = int(parts[1] if pack.startswith("open_generation_") else parts[3])
        assert task["difficulty"] == ("basic" if number <= cutoff else "advanced")


def test_calibration_difficulty_matches_formal_tasks():
    formal = load_tasks_file(package_resource("open_generation_xtb", "tasks.yaml"))
    calibration = load_tasks_file(
        files("verifier_grounded_benchmark.task.calibration.xtb").joinpath("tasks.yaml")
    )
    for task_id, task in calibration.items():
        assert task["difficulty"] == formal[task_id]["difficulty"]


@pytest.mark.parametrize("difficulty", ["simple", "intermediate", "expert", "easy", "", None, []])
@pytest.mark.parametrize("entrypoint", ["file", "v2", "legacy", "mapping"])
def test_task_loaders_reject_nonstandard_difficulty(tmp_path, difficulty, entrypoint):
    data = yaml.safe_load(package_resource("open_generation_rdkit", "tasks.yaml").read_text())
    data["tasks"][0]["difficulty"] = difficulty
    if entrypoint == "legacy":
        data.pop("schema_version")
    path = tmp_path / "tasks.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError, match="difficulty"):
        if entrypoint == "file":
            load_tasks_file(path)
        elif entrypoint == "mapping":
            task = data["tasks"][0]
            task_pack_from_mappings({task["task_id"]: task}, {})
        else:
            load_task_pack(
                path,
                package_resource("open_generation_rdkit", "verifier_specs.yaml"),
                package_resource("open_generation_rdkit", "scoring.yaml"),
            )


def test_legacy_minimal_task_without_difficulty_remains_supported():
    pack = task_pack_from_mappings({"minimal": {"task_id": "minimal"}}, {})
    assert "difficulty" not in pack.tasks[0].raw
