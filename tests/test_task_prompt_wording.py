from __future__ import annotations

import yaml

from verifier_grounded_benchmark.task.resources import package_resource

PACKS = ("rdkit", "xtb", "property_calculation", "experimental/rdkit_forcefield")

FORBIDDEN_PROMPT_FRAGMENTS = [
    "RDKit-calculated",
    "local xTB",
    "low-energy xTB",
    "GFN2-xTB",
    "MatGL",
    "MACE-MP-small",
    "MACE potential",
    "local verifier",
    "verifier_id",
    "verifiers/",
    "geometric_mean",
    "sigma",
    "benchmark",
]


def test_task_prompts_do_not_expose_tool_or_benchmark_internals() -> None:
    violations: list[str] = []

    for pack_name in PACKS:
        tasks_resource = package_resource(pack_name, "tasks.yaml")
        payload = yaml.safe_load(tasks_resource.read_text(encoding="utf-8"))
        for task in payload["tasks"]:
            prompt = task["prompt"]
            for fragment in FORBIDDEN_PROMPT_FRAGMENTS:
                if fragment.lower() in prompt.lower():
                    violations.append(
                        f"{pack_name}/tasks.yaml:{task['task_id']} contains {fragment!r}"
                    )

    assert violations == []
