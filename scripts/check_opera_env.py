#!/usr/bin/env python
"""Smoke-check OPERA CLI discovery without requiring OPERA to be installed."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def head(text: str, limit: int = 2000) -> str:
    return text[:limit]


def find_opera() -> str | None:
    configured = os.environ.get("OPERA_EXECUTABLE")
    if configured:
        return configured
    return shutil.which("opera") or shutil.which("OPERA")


def find_mcr_directory() -> str | None:
    return os.environ.get("OPERA_MCR_DIRECTORY")


def check_opera() -> dict[str, Any]:
    executable = find_opera()
    if executable is None:
        return {
            "status": "missing",
            "failure_type": "verifier_environment_error",
            "message": "OPERA executable not found. Set OPERA_EXECUTABLE or add opera/OPERA to PATH.",
            "remediation": "Install OPERA separately and configure OPERA_EXECUTABLE; do not vendor OPERA binaries.",
        }

    if os.environ.get("OPERA_EXECUTABLE") and not Path(executable).exists():
        return {
            "status": "missing",
            "failure_type": "verifier_environment_error",
            "executable": executable,
            "message": f"Configured OPERA_EXECUTABLE does not exist: {executable}",
            "remediation": "Set OPERA_EXECUTABLE to the installed OPERA executable path.",
        }

    mcr_directory = find_mcr_directory()
    if not mcr_directory:
        return {
            "status": "missing",
            "failure_type": "verifier_environment_error",
            "executable": executable,
            "message": "OPERA MCR directory not configured. Set OPERA_MCR_DIRECTORY to the MATLAB runtime directory.",
            "remediation": "Set OPERA_MCR_DIRECTORY to the MCR runtime directory used by run_OPERA.sh.",
        }

    if not Path(mcr_directory).is_dir():
        return {
            "status": "missing",
            "failure_type": "verifier_environment_error",
            "executable": executable,
            "mcr_directory": mcr_directory,
            "message": f"Configured OPERA_MCR_DIRECTORY is not a directory: {mcr_directory}",
            "remediation": "Set OPERA_MCR_DIRECTORY to an existing MCR runtime directory.",
        }

    try:
        completed = subprocess.run(
            [executable, mcr_directory, "-h"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return {
            "status": "error",
            "failure_type": "verifier_environment_error",
            "executable": executable,
            "mcr_directory": mcr_directory,
            "message": f"Failed to run OPERA help command: {exc}",
        }

    return {
        "status": "ok" if completed.returncode == 0 else "error",
        "executable": executable,
        "mcr_directory": mcr_directory,
        "returncode": completed.returncode,
        "stdout_head": head(completed.stdout),
        "stderr_head": head(completed.stderr),
    }


def main() -> None:
    print(json.dumps(check_opera(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
