from __future__ import annotations

import json
from pathlib import Path

import pytest

from verifiers.atomisticskills_backend import (
    AtomisticSkillsEnvironmentError,
    AtomisticSkillsScriptAdapter,
    resolve_mcp_server_config,
)


def write_fake_mcp_config(root: Path) -> None:
    (root / "mcp_config.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "base": {
                        "command": "/home/example/miniforge3/envs/base-agent/bin/python",
                        "args": ["-m", "src.mcp_server.base_server"],
                        "env": {"PYTHONPATH": "/home/example/AtomisticSkills"},
                    },
                    "drugdisc": {
                        "command": "/home/example/miniforge3/envs/drugdisc-agent/bin/python",
                        "args": ["-m", "src.mcp_server.drugdisc_server"],
                        "env": {"PYTHONPATH": "/home/example/AtomisticSkills"},
                    },
                }
            }
        )
    )


def test_resolve_mcp_server_config_patches_conda_and_pythonpath(tmp_path: Path) -> None:
    atomisticskills_home = tmp_path / "AtomisticSkills"
    atomisticskills_home.mkdir()
    write_fake_mcp_config(atomisticskills_home)
    conda_base = tmp_path / "miniforge3"

    config = resolve_mcp_server_config("base", atomisticskills_home=atomisticskills_home, conda_base=conda_base)

    assert config.command == conda_base / "envs" / "base-agent" / "bin" / "python"
    assert config.args == ["-m", "src.mcp_server.base_server"]
    assert config.env["PYTHONPATH"] == str(atomisticskills_home)


def test_resolve_mcp_server_config_rejects_unknown_server(tmp_path: Path) -> None:
    atomisticskills_home = tmp_path / "AtomisticSkills"
    atomisticskills_home.mkdir()
    write_fake_mcp_config(atomisticskills_home)

    with pytest.raises(AtomisticSkillsEnvironmentError, match="missing MCP server"):
        resolve_mcp_server_config("xrd", atomisticskills_home=atomisticskills_home, conda_base=tmp_path / "miniforge3")


def test_script_adapter_builds_xrd_command(tmp_path: Path) -> None:
    atomisticskills_home = tmp_path / "AtomisticSkills"
    script = atomisticskills_home / ".agents" / "skills" / "mat-xrd-calculator" / "scripts" / "calculate_xrd.py"
    script.parent.mkdir(parents=True)
    script.write_text("print('placeholder')\n")

    adapter = AtomisticSkillsScriptAdapter(atomisticskills_home=atomisticskills_home, conda_executable=Path("/opt/conda/bin/conda"))
    command = adapter.xrd_calculator_command(tmp_path / "Si.cif", tmp_path / "out", wavelength="CuKa")

    assert command == [
        "/opt/conda/bin/conda",
        "run",
        "-n",
        "xrd-agent",
        "python",
        str(script),
        str(tmp_path / "Si.cif"),
        "--output_dir",
        str(tmp_path / "out"),
        "--wavelength",
        "CuKa",
    ]
