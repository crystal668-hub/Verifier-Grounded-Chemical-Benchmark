#!/usr/bin/env python
"""Smoke-check the Docker-backed MolGpKa verifier runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPOSITORY_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from verifiers.backends import docker_model_runtime as runtime
from verifiers.backends import molgpka_properties


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    spec = {
        "verifier_image": "verifier-grounded:dev",
        "molgpka": {
            "image": args.image,
            "platform": args.platform,
            "timeout_seconds": args.timeout_seconds,
        },
    }
    if args.docker_executable:
        spec["molgpka"]["docker_executable"] = args.docker_executable
    try:
        image = runtime.docker_image_inspect(args.image, docker_executable=args.docker_executable)
        prediction = molgpka_properties.predict_molgpka_properties(args.smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return {
            "status": "error",
            "failure_type": "verifier_environment_error",
            "message": str(exc),
            "runtime": {"image": args.image},
        }
    except runtime.DockerRuntimeTimeout as exc:
        return {
            "status": "error",
            "failure_type": "verifier_timeout",
            "message": str(exc),
            "runtime": {"image": args.image},
        }
    except Exception as exc:
        return {
            "status": "error",
            "failure_type": "verifier_tool_error",
            "message": str(exc),
            "runtime": {"image": args.image},
        }
    return {
        "status": "ok",
        "failure_type": None,
        "message": None,
        "runtime": {
            "image": args.image,
            "image_id": image.get("Id"),
            "platform": args.platform,
            "mode": "external_docker",
        },
        "prediction": {"smiles": args.smiles, **prediction},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smiles", default="CC(O)=O")
    parser.add_argument("--image", default=molgpka_properties.DEFAULT_MOLGPKA_IMAGE)
    parser.add_argument("--platform", default="linux/amd64")
    parser.add_argument("--docker-executable")
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args()
    print(json.dumps(build_payload(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
