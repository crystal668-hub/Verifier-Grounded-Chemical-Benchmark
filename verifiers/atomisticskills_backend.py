"""Backend adapters for AtomisticSkills MCP tools and script-only environments."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ENV_PATTERN = re.compile(r".*/envs/([^/]+)/bin/python$")
ATOMISTICSKILLS_MCP_SHIM_DIR = Path(__file__).resolve().parent / "atomisticskills_mcp_shims"


class AtomisticSkillsError(RuntimeError):
    """Base error for AtomisticSkills adapter failures."""


class AtomisticSkillsEnvironmentError(AtomisticSkillsError):
    """Raised when AtomisticSkills paths or environments are not available."""


class AtomisticSkillsToolError(AtomisticSkillsError):
    """Raised when an MCP tool or script reports a failed execution."""


class AtomisticSkillsTimeoutError(AtomisticSkillsError):
    """Raised when an AtomisticSkills backend call exceeds its timeout."""


@dataclass(frozen=True)
class MCPServerConfig:
    command: Path
    args: list[str]
    env: dict[str, str]


def default_atomisticskills_home() -> Path:
    return Path(os.environ.get("ATOMISTICSKILLS_HOME", Path.home() / "projects" / "AtomisticSkills")).expanduser()


def detect_conda_base() -> Path:
    for command in ("conda", "mamba", "micromamba"):
        executable = shutil.which(command)
        if not executable:
            continue
        try:
            result = subprocess.run(
                [executable, "info", "--base"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except subprocess.SubprocessError:
            continue
        base = result.stdout.strip()
        if result.returncode == 0 and base:
            return Path(base).expanduser()

    for name in ("miniforge3", "mambaforge", "miniconda3", "anaconda3"):
        candidate = Path.home() / name
        if candidate.is_dir():
            return candidate

    raise AtomisticSkillsEnvironmentError("could not detect conda base; install Miniforge or set up conda first")


def detect_conda_executable() -> Path:
    for command in ("conda", "mamba", "micromamba"):
        executable = shutil.which(command)
        if executable:
            return Path(executable)
    raise AtomisticSkillsEnvironmentError("conda executable not found; install Miniforge before running xrd-agent")


def prepend_pythonpath(path: Path, current: str | None) -> str:
    if current:
        return os.pathsep.join([str(path), current])
    return str(path)


def xrd_subprocess_environment(atomisticskills_home: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env or os.environ)
    env["PYTHONPATH"] = prepend_pythonpath(atomisticskills_home, env.get("PYTHONPATH"))
    return env


def resolve_mcp_server_config(
    server_name: str,
    *,
    atomisticskills_home: Path | None = None,
    conda_base: Path | None = None,
) -> MCPServerConfig:
    root = (atomisticskills_home or default_atomisticskills_home()).expanduser()
    config_path = root / "mcp_config.json"
    if not config_path.exists():
        raise AtomisticSkillsEnvironmentError(f"AtomisticSkills mcp_config.json not found at {config_path}")

    payload = json.loads(config_path.read_text())
    servers = payload.get("mcpServers", {})
    server = servers.get(server_name)
    if server is None:
        raise AtomisticSkillsEnvironmentError(f"missing MCP server {server_name!r} in {config_path}")

    base = conda_base or detect_conda_base()
    command = str(server.get("command", ""))
    match = ENV_PATTERN.match(command)
    if match:
        command_path = base / "envs" / match.group(1) / "bin" / "python"
    else:
        command_path = Path(command).expanduser()

    env = {str(k): str(v) for k, v in (server.get("env") or {}).items()}
    env["PYTHONPATH"] = os.pathsep.join([str(ATOMISTICSKILLS_MCP_SHIM_DIR), str(root)])
    env["ATOMISTICSKILLS_MCP_DISABLE_JSON_PREPARSE"] = "1"
    return MCPServerConfig(command=command_path, args=list(server.get("args") or []), env=env)


def extract_text_content(tool_result: Any) -> Any:
    structured = getattr(tool_result, "structuredContent", None)
    if structured is not None:
        return unwrap_mcp_result_payload(structured)

    content = getattr(tool_result, "content", None)
    if content is None:
        return tool_result
    texts = [getattr(item, "text", None) for item in content if getattr(item, "text", None) is not None]
    if len(texts) == 1:
        text = texts[0]
        try:
            return unwrap_mcp_result_payload(json.loads(text))
        except json.JSONDecodeError:
            return text
    return "\n".join(texts)


def unwrap_mcp_result_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload


class AtomisticSkillsMCPAdapter:
    def __init__(
        self,
        server_name: str,
        *,
        atomisticskills_home: Path | None = None,
        conda_base: Path | None = None,
    ) -> None:
        self.server_name = server_name
        self.config = resolve_mcp_server_config(
            server_name,
            atomisticskills_home=atomisticskills_home,
            conda_base=conda_base,
        )

    def call_tool(self, tool_name: str, arguments: dict[str, Any], timeout_seconds: float = 60.0) -> Any:
        return self.call_tools([(tool_name, arguments)], timeout_seconds=timeout_seconds)[0]

    def call_tools(self, tool_calls: list[tuple[str, dict[str, Any]]], timeout_seconds: float = 60.0) -> list[Any]:
        try:
            return asyncio.run(self._call_tools(tool_calls, timeout_seconds))
        except TimeoutError as exc:
            raise AtomisticSkillsTimeoutError(f"{self.server_name} tool sequence timed out") from exc
        except AtomisticSkillsError:
            raise
        except Exception as exc:
            raise AtomisticSkillsToolError(f"{self.server_name} tool sequence failed: {exc}") from exc

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any], timeout_seconds: float) -> Any:
        return (await self._call_tools([(tool_name, arguments)], timeout_seconds))[0]

    async def _call_tools(self, tool_calls: list[tuple[str, dict[str, Any]]], timeout_seconds: float) -> list[Any]:
        env = os.environ.copy()
        env.update(self.config.env)
        params = StdioServerParameters(
            command=str(self.config.command),
            args=self.config.args,
            env=env,
        )
        async with stdio_client(params, errlog=sys.stderr) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                results = []
                for tool_name, arguments in tool_calls:
                    result = await session.call_tool(
                        tool_name,
                        arguments,
                        read_timeout_seconds=timedelta(seconds=timeout_seconds),
                    )
                    if getattr(result, "isError", False):
                        raise AtomisticSkillsToolError(str(extract_text_content(result)))
                    results.append(extract_text_content(result))
        return results


class AtomisticSkillsScriptAdapter:
    def __init__(
        self,
        *,
        atomisticskills_home: Path | None = None,
        conda_executable: Path | None = None,
    ) -> None:
        self.atomisticskills_home = (atomisticskills_home or default_atomisticskills_home()).expanduser()
        self.conda_executable = conda_executable or detect_conda_executable()

    def xrd_calculator_script(self) -> Path:
        return (
            self.atomisticskills_home
            / ".agents"
            / "skills"
            / "mat-xrd-calculator"
            / "scripts"
            / "calculate_xrd.py"
        )

    def xrd_calculator_command(self, structure_path: Path, output_dir: Path, *, wavelength: str) -> list[str]:
        script = self.xrd_calculator_script()
        if not script.exists():
            raise AtomisticSkillsEnvironmentError(f"XRD calculator script not found at {script}")
        return [
            str(self.conda_executable),
            "run",
            "-n",
            "xrd-agent",
            "python",
            str(script),
            str(structure_path),
            "--output_dir",
            str(output_dir),
            "--wavelength",
            wavelength,
        ]

    def run_xrd_calculator(
        self,
        structure_path: str,
        output_dir: str,
        wavelength: str = "CuKa",
        timeout_seconds: float = 120.0,
    ) -> Path:
        structure = Path(structure_path)
        output = Path(output_dir)
        command = self.xrd_calculator_command(structure, output, wavelength=wavelength)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=xrd_subprocess_environment(self.atomisticskills_home),
            )
        except subprocess.TimeoutExpired as exc:
            raise AtomisticSkillsTimeoutError("xrd-agent calculator timed out") from exc
        if completed.returncode != 0:
            raise AtomisticSkillsToolError(completed.stderr.strip() or completed.stdout.strip())

        result_path = output / f"{structure.stem}_xrd.json"
        if not result_path.exists():
            raise AtomisticSkillsToolError(f"XRD calculator did not produce {result_path}")
        return result_path
