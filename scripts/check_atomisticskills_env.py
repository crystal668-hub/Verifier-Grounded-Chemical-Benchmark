#!/usr/bin/env python
"""Smoke-check AtomisticSkills first-batch verifier backends."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from verifiers.atomisticskills_backend import (
    AtomisticSkillsMCPAdapter,
    AtomisticSkillsScriptAdapter,
    default_atomisticskills_home,
    resolve_mcp_server_config,
)


ROOT = Path(__file__).resolve().parents[1]
SI_FIXTURE = ROOT / "tasks" / "atomisticskills_smoke" / "fixtures" / "Si.cif"


def main() -> None:
    atomisticskills_home = default_atomisticskills_home()
    checks: dict[str, object] = {
        "atomisticskills_home": str(atomisticskills_home),
        "mcp": {},
        "xrd": {},
    }

    for server_name, tool_name, arguments in [
        ("base", "supercell_expansion", {"structure_path": str(SI_FIXTURE), "scaling_matrix_json": "[2, 1, 1]"}),
        ("drugdisc", "standardize_molecule", {"smiles": "CCO", "mode": "cleanup"}),
    ]:
        config = resolve_mcp_server_config(server_name)
        checks["mcp"][server_name] = {"python": str(config.command), "exists": config.command.exists()}
        result = AtomisticSkillsMCPAdapter(server_name).call_tool(tool_name, arguments)
        checks["mcp"][server_name]["result"] = str(result)[:500]

    with tempfile.TemporaryDirectory(prefix="atomisticskills-check-xrd-") as temp_dir:
        xrd_json = AtomisticSkillsScriptAdapter().run_xrd_calculator(str(SI_FIXTURE), temp_dir, wavelength="CuKa")
        payload = json.loads(xrd_json.read_text())
        checks["xrd"] = {
            "output": str(xrd_json),
            "num_points": len(payload.get("x", [])),
            "max_two_theta": payload["x"][max(range(len(payload["y"])), key=lambda index: payload["y"][index])],
        }

    print(json.dumps({"status": "ok", "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
