#!/usr/bin/env python
"""Smoke-check optional OpenMM + OpenFF/GAFF local environment."""

from __future__ import annotations

import argparse
import json
from typing import Any

from verifiers.backends import openmm_runtime


def error_payload(message: str, *, check: str | None = None) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {
        "core": {"status": "skipped"},
        "openff": {"status": "skipped"},
        "gaff": {"status": "skipped"},
    }
    if check is not None:
        checks[check] = {"status": "error", "failure_type": openmm_runtime.ENV_FAILURE}
    return {
        "status": "error",
        "failure_type": openmm_runtime.ENV_FAILURE,
        "message": message,
        "versions": {},
        "platforms": [],
        "checks": checks,
    }


def build_payload(mode: str) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    versions = {
        "openmm": openmm_runtime.package_version("openmm"),
        "openff_toolkit": openmm_runtime.package_version("openff-toolkit"),
        "openff_interchange": openmm_runtime.package_version("openff-interchange"),
        "openmmforcefields": openmm_runtime.package_version("openmmforcefields"),
        "rdkit": openmm_runtime.package_version("rdkit"),
    }
    platforms: list[str] = []

    try:
        if mode in {"core", "all"}:
            core = openmm_runtime.run_core_smoke()
            checks["core"] = core
            platforms = openmm_runtime.openmm_platforms(openmm_runtime.load_core_modules().openmm)
        if mode in {"openff", "all"}:
            checks["openff"] = openmm_runtime.run_openff_smoke()
        if mode in {"gaff", "all"}:
            checks["gaff"] = openmm_runtime.run_gaff_smoke()
    except openmm_runtime.OpenMMEnvironmentError as exc:
        check = mode if mode in {"core", "openff", "gaff"} else None
        return error_payload(str(exc), check=check)
    except openmm_runtime.OpenMMToolError as exc:
        return {
            "status": "error",
            "failure_type": openmm_runtime.TOOL_FAILURE,
            "message": str(exc),
            "versions": versions,
            "platforms": platforms,
            "checks": checks,
        }

    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "versions": versions,
        "platforms": platforms,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "core", "openff", "gaff"], default="all")
    args = parser.parse_args()

    payload = build_payload(args.mode)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
