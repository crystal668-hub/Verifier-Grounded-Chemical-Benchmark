#!/usr/bin/env python
"""Smoke-check the Docker-backed SolTranNet verifier runtime."""

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

from verifiers.common import docker_model_runtime as runtime
from verifiers.backends import soltrannet_properties


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    image_id = None
    spec = {
        "verifier_image": "verifier-grounded:dev",
        "soltrannet": {
            "image": args.image,
            "container_name": args.container_name,
            "host": args.host,
            "port": args.port,
            "base_url": args.base_url,
            "startup_timeout_seconds": args.startup_timeout_seconds,
            "prediction_timeout_seconds": args.prediction_timeout_seconds,
        },
    }
    if args.docker_executable:
        spec["soltrannet"]["docker_executable"] = args.docker_executable
    if not args.base_url:
        try:
            image = runtime.docker_image_inspect(args.image, docker_executable=args.docker_executable)
        except (runtime.DockerRuntimeEnvironmentError, runtime.DockerRuntimeToolError) as exc:
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
        image_id = image.get("Id")
    try:
        value = soltrannet_properties.predict_soltrannet_log_s(args.smiles, spec)
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
            "image_id": image_id,
            "mode": "external_docker",
            "base_url": args.base_url,
            "container_name": args.container_name,
            "host": args.host,
            "port": args.port,
        },
        "prediction": {"smiles": args.smiles, "soltrannet_log_s": value},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smiles", default="CCO")
    parser.add_argument("--image", default=soltrannet_properties.DEFAULT_SOLTRANNET_IMAGE)
    parser.add_argument("--container-name", default=soltrannet_properties.DEFAULT_CONTAINER_NAME)
    parser.add_argument("--host", default=soltrannet_properties.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=soltrannet_properties.DEFAULT_PORT)
    parser.add_argument("--base-url")
    parser.add_argument("--docker-executable")
    parser.add_argument("--startup-timeout-seconds", type=float, default=60)
    parser.add_argument("--prediction-timeout-seconds", type=float, default=30)
    args = parser.parse_args()
    print(json.dumps(build_payload(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
