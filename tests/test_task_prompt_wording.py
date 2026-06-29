from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "tasks"

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

    for tasks_path in sorted(TASKS_DIR.glob("*/tasks.yaml")):
        with tasks_path.open() as handle:
            payload = yaml.safe_load(handle)
        for task in payload["tasks"]:
            prompt = task["prompt"]
            for fragment in FORBIDDEN_PROMPT_FRAGMENTS:
                if fragment.lower() in prompt.lower():
                    relative_path = tasks_path.relative_to(ROOT)
                    violations.append(f"{relative_path}:{task['task_id']} contains {fragment!r}")

    assert violations == []
