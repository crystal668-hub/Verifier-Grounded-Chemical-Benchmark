#!/usr/bin/env python
"""Smoke-check native MatGL+pymatgen verifier environment."""

from __future__ import annotations

import argparse
import contextlib
import importlib.metadata as metadata
import io
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SI_FIXTURE = ROOT / "tasks" / "matgl_materials" / "fixtures" / "Si.cif"


def environment_error(message: str, **details: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "missing",
        "failure_type": "verifier_environment_error",
        "message": message,
    }
    payload.update({key: value for key, value in details.items() if value})
    return payload


def package_version(distribution: str) -> str:
    return metadata.version(distribution)


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import matgl
        from pymatgen.core import Structure
    except Exception as exc:
        return environment_error(
            f"failed to import MatGL/pymatgen: {exc}",
            install_hint="Run `uv sync --group materials` to install matgl==4.0.2 and its material-science dependencies.",
        )

    try:
        structure = Structure.from_file(SI_FIXTURE)
    except Exception as exc:
        return {
            "status": "missing",
            "failure_type": "verifier_environment_error",
            "message": f"failed to parse fixture {SI_FIXTURE}: {exc}",
        }

    payload: dict[str, Any] = {
        "status": "ok",
        "versions": {
            "matgl": package_version("matgl"),
            "pymatgen": package_version("pymatgen"),
            "torch": package_version("torch"),
        },
        "pymatgen": {
            "fixture": str(SI_FIXTURE),
            "fixture_formula": structure.composition.reduced_formula,
            "atom_count": len(structure),
        },
        "model": {
            "loaded": False,
            "name": args.model,
        },
    }

    if not args.no_model_load:
        model_stdout = io.StringIO()
        model_stderr = io.StringIO()
        try:
            with contextlib.redirect_stdout(model_stdout), contextlib.redirect_stderr(model_stderr):
                model = matgl.load_model(args.model)
        except Exception as exc:
            return environment_error(
                f"failed to load MatGL model {args.model}: {exc}",
                model_load_stdout=model_stdout.getvalue(),
                model_load_stderr=model_stderr.getvalue(),
            )
        payload["model"]["loaded"] = True
        payload["model"]["class"] = type(model).__name__

    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="MEGNet-Eform-MP-2018.6.1")
    parser.add_argument("--no-model-load", action="store_true")
    args = parser.parse_args()

    print(json.dumps(build_payload(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
