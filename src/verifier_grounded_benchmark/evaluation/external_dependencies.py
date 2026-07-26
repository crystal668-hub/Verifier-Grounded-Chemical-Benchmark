"""Task-scoped external executable discovery and preflight checks."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any


class ExternalDependencyError(RuntimeError):
    def __init__(self, checks: list[dict[str, Any]]) -> None:
        self.checks = checks
        failures = [str(check["message"]) for check in checks if check["status"] == "error"]
        super().__init__("; ".join(failures))


def verifier_specs_for_answers(
    tasks_by_id: Mapping[str, Mapping[str, Any]],
    verifier_specs_by_id: Mapping[str, Mapping[str, Any]],
    answers: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Return only verifier specs reachable from the submitted task IDs."""
    verifier_ids: set[str] = set()
    for answer in answers:
        task_id = answer.get("task_id")
        task = tasks_by_id.get(task_id) if isinstance(task_id, str) else None
        if task is None:
            continue
        for field in ("constraints", "hard_constraints"):
            constraints = task.get(field) or ()
            if not isinstance(constraints, (list, tuple)):
                continue
            for constraint in constraints:
                if isinstance(constraint, Mapping):
                    verifier_id = constraint.get("verifier_id")
                    if isinstance(verifier_id, str):
                        verifier_ids.add(verifier_id)
    return [
        verifier_specs_by_id[verifier_id]
        for verifier_id in sorted(verifier_ids)
        if verifier_id in verifier_specs_by_id
    ]


def preflight_external_dependencies(
    verifier_specs: Sequence[Mapping[str, Any]],
    *,
    environ: MutableMapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Resolve and version-check external executables required by verifier specs."""
    target_environ = os.environ if environ is None else environ
    dependencies = _unique_dependencies(verifier_specs)
    checks: list[dict[str, Any]] = []
    conda_prefixes: dict[str, Path | None] = {}
    for dependency in dependencies:
        executable = str(dependency["executable"])
        expected_version = str(dependency["version"])
        conda_environment = dependency.get("conda_environment")
        resolved = shutil.which(executable, path=target_environ.get("PATH"))
        version_output = _version_output(resolved, target_environ) if resolved else None

        if not resolved or not _matches_version(version_output, expected_version):
            if isinstance(conda_environment, str):
                if conda_environment not in conda_prefixes:
                    conda_prefixes[conda_environment] = _find_conda_environment(
                        conda_environment, target_environ
                    )
                prefix = conda_prefixes[conda_environment]
                if prefix is not None:
                    _prepend_environment_path(prefix, target_environ)
                    resolved = shutil.which(executable, path=target_environ.get("PATH"))
                    version_output = (
                        _version_output(resolved, target_environ) if resolved else None
                    )

        if not resolved:
            checks.append(
                {
                    "executable": executable,
                    "expected_version": expected_version,
                    "conda_environment": conda_environment,
                    "status": "error",
                    "message": _missing_message(executable, conda_environment),
                }
            )
            continue
        if not _matches_version(version_output, expected_version):
            checks.append(
                {
                    "executable": executable,
                    "expected_version": expected_version,
                    "resolved_path": resolved,
                    "version_output": version_output,
                    "conda_environment": conda_environment,
                    "status": "error",
                    "message": (
                        f"{executable} version does not match required "
                        f"{expected_version}: {version_output or 'no version output'}"
                    ),
                }
            )
            continue
        checks.append(
            {
                "executable": executable,
                "expected_version": expected_version,
                "resolved_path": resolved,
                "version_output": version_output,
                "conda_environment": conda_environment,
                "status": "ok",
            }
        )
    if any(check["status"] == "error" for check in checks):
        raise ExternalDependencyError(checks)
    return checks


def _unique_dependencies(
    verifier_specs: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    by_executable: dict[str, Mapping[str, Any]] = {}
    for spec in verifier_specs:
        dependencies = spec.get("external_dependencies") or ()
        if not isinstance(dependencies, (list, tuple)):
            continue
        for dependency in dependencies:
            if not isinstance(dependency, Mapping):
                continue
            executable = dependency.get("executable")
            version = dependency.get("version")
            if not isinstance(executable, str) or not isinstance(version, str):
                continue
            existing = by_executable.get(executable)
            if existing is not None and existing != dependency:
                checks = [
                    {
                        "executable": executable,
                        "status": "error",
                        "message": f"conflicting external dependency declarations for {executable}",
                    }
                ]
                raise ExternalDependencyError(checks)
            by_executable[executable] = dependency
    return [by_executable[name] for name in sorted(by_executable)]


def _find_conda_environment(
    name: str, environ: Mapping[str, str]
) -> Path | None:
    active_prefix = environ.get("CONDA_PREFIX")
    if active_prefix and Path(active_prefix).name == name:
        return Path(active_prefix)
    conda = environ.get("CONDA_EXE") or shutil.which(
        "conda", path=environ.get("PATH")
    )
    if not conda:
        return None
    try:
        completed = subprocess.run(
            [conda, "env", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            env=dict(environ),
        )
        payload = json.loads(completed.stdout) if completed.returncode == 0 else {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    prefixes = payload.get("envs") if isinstance(payload, dict) else None
    if not isinstance(prefixes, list):
        return None
    return next(
        (
            Path(prefix)
            for prefix in prefixes
            if isinstance(prefix, str) and Path(prefix).name == name
        ),
        None,
    )


def _prepend_environment_path(
    prefix: Path, environ: MutableMapping[str, str]
) -> None:
    candidates = [prefix / "bin", prefix / "Scripts", prefix / "Library" / "bin"]
    entries = [str(path) for path in candidates if path.is_dir()]
    if not entries:
        return
    current = environ.get("PATH", "")
    existing = current.split(os.pathsep) if current else []
    environ["PATH"] = os.pathsep.join(entries + [item for item in existing if item not in entries])


def _version_output(
    executable: str, environ: Mapping[str, str]
) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            env=dict(environ),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode != 0 or not output:
        return None
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return next(
        (line for line in lines if "version" in line.lower()),
        lines[0] if lines else None,
    )


def _matches_version(output: str | None, expected: str) -> bool:
    if output is None:
        return False
    pattern = rf"(?<![0-9.]){re.escape(expected)}(?![0-9.])"
    return re.search(pattern, output) is not None


def _missing_message(executable: str, conda_environment: object) -> str:
    if isinstance(conda_environment, str):
        return (
            f"required executable {executable} was not found on PATH or in "
            f"Conda environment {conda_environment}"
        )
    return f"required executable {executable} was not found on PATH"
