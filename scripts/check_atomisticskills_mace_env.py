#!/usr/bin/env python
"""Smoke-check AtomisticSkills MACE verifier backend."""

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


SI_FIXTURE = ROOT / "tasks" / "mace_materials" / "fixtures" / "Si.cif"


def main() -> None:
    atomisticskills_home = default_atomisticskills_home()
    config = resolve_mcp_server_config("mace")
    checks: dict[str, object] = {
        "atomisticskills_home": str(atomisticskills_home),
        "mace_python": str(config.command),
        "mace_python_exists": config.command.exists(),
        "si_fixture": str(SI_FIXTURE),
    }

    adapter = AtomisticSkillsMCPAdapter("mace")
    try:
        _, energy = adapter.call_tools(
            [
                ("load_model", {"model_name": "MACE-MP-small", "device": "cpu"}),
                ("predict_structure", {"structure_data": str(SI_FIXTURE)}),
            ],
            timeout_seconds=240,
        )
    except AtomisticSkillsToolError as exc:
        raise SystemExit(f"MACE energy smoke check failed: {exc}") from exc

    checks["energy"] = energy
    print(json.dumps({"status": "ok", "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
