#!/usr/bin/env python
"""Smoke-check AtomisticSkills MatGL verifier backend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from verifiers.atomisticskills_backend import (  # noqa: E402
    AtomisticSkillsMCPAdapter,
    AtomisticSkillsToolError,
    default_atomisticskills_home,
    resolve_mcp_server_config,
)


SI_FIXTURE = ROOT / "tasks" / "matgl_materials" / "fixtures" / "Si.cif"
DTYPE_HINTS = ("FloatTensor", "LongTensor", "embedding", "indices", "dtype")


def main() -> None:
    atomisticskills_home = default_atomisticskills_home()
    config = resolve_mcp_server_config("matgl")
    checks: dict[str, object] = {
        "atomisticskills_home": str(atomisticskills_home),
        "matgl_python": str(config.command),
        "matgl_python_exists": config.command.exists(),
        "si_fixture": str(SI_FIXTURE),
    }

    adapter = AtomisticSkillsMCPAdapter("matgl")
    try:
        bandgap = adapter.call_tool(
            "predict_bandgap",
            {"structure_data": str(SI_FIXTURE), "task_name": "PBE"},
            timeout_seconds=180,
        )
    except AtomisticSkillsToolError as exc:
        raise SystemExit(matgl_tool_failure_message("bandgap", exc)) from exc

    try:
        _, formation_energy = adapter.call_tools(
            [
                ("load_model", {"model_name": "MEGNet-Eform-MP-2018.6.1", "device": "cpu"}),
                ("predict_structure", {"structure_data": str(SI_FIXTURE)}),
            ],
            timeout_seconds=180,
        )
    except AtomisticSkillsToolError as exc:
        raise SystemExit(matgl_tool_failure_message("formation_energy", exc)) from exc

    checks["bandgap"] = bandgap
    checks["formation_energy"] = formation_energy
    print(json.dumps({"status": "ok", "checks": checks}, indent=2, sort_keys=True))


def matgl_tool_failure_message(property_name: str, exc: Exception) -> str:
    message = str(exc)
    if all(hint in message for hint in DTYPE_HINTS[:2]) or (
        "embedding" in message and ("indices" in message or "dtype" in message)
    ):
        return (
            f"MatGL {property_name} smoke check failed with a likely MatGL/AtomisticSkills dtype compatibility issue: "
            f"{message}\n"
            "Use an AtomisticSkills checkout that fixes src/utils/mlips/matgl/matgl_wrapper.py state_attr dtype "
            "for MatGL 4.x, or patch the external checkout before running integration tests."
        )
    return f"MatGL {property_name} smoke check failed: {message}"


if __name__ == "__main__":
    main()
