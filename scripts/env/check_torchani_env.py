#!/usr/bin/env python
"""Smoke-check native TorchANI ANI-2x verifier environment."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from typing import Any

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.torchani import backend as torchani_properties


WATER_XYZ = """3
water
O 0.000000 0.000000 0.000000
H 0.758602 0.000000 0.504284
H -0.758602 0.000000 0.504284
"""


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    spec = {"torchani": {"model_name": args.model_name, "device": args.device}}
    try:
        atoms = torchani_properties.parse_xyz_atoms(WATER_XYZ)
        input_properties = torchani_properties.inspect_xyz_atoms(atoms)
        prediction = torchani_properties.predict_torchani_properties(atoms, spec)
    except (ImportError, ModuleNotFoundError) as exc:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": str(exc)}

    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "versions": {
            "torchani": package_version("torchani"),
            "torch": package_version("torch"),
            "ase": package_version("ase"),
        },
        "runtime": {"model_name": args.model_name, "device": args.device},
        "input": input_properties,
        "prediction": prediction,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="ANI2x")
    parser.add_argument("--device", default="cpu")
    print(json.dumps(build_payload(parser.parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
