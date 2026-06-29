#!/usr/bin/env python
"""Smoke-check native MatGL+pymatgen verifier environment."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SI_FIXTURE = ROOT / "tasks" / "matgl_materials" / "fixtures" / "Si.cif"


def environment_error(message: str) -> dict[str, str]:
    return {
        "status": "missing",
        "failure_type": "verifier_environment_error",
        "message": message,
    }


def package_version(distribution: str) -> str:
    return metadata.version(distribution)


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import matgl
        from pymatgen.core import Structure
    except Exception as exc:
        return environment_error(str(exc))

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
        try:
            model = matgl.load_model(args.model)
        except Exception as exc:
            return {
                "status": "missing",
                "failure_type": "verifier_environment_error",
                "message": f"failed to load MatGL model {args.model}: {exc}",
            }
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
