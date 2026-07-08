"""SolTranNet aqueous solubility backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib.metadata as metadata
import math
import os
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.common import docker_model_runtime as runtime
from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.common.result_schema import base_result
from verifiers.common.result_schema import error_result


DEFAULT_SOLTRANNET_IMAGE = "ersiliaos/eos6oli:v1.0.0"
DEFAULT_CONTAINER_NAME = "vgb-soltrannet-eos6oli"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18081
DEFAULT_CONTAINER_PORT = 80
SUPPORTED_SOLTRANNET_PROPERTIES = {"soltrannet_log_s"}


def evaluate_soltrannet_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), soltrannet_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )
    if property_name not in SUPPORTED_SOLTRANNET_PROPERTIES:
        return error_result(result, "verifier_spec_error", f"unsupported SolTranNet property {property_name!r}")

    smiles = candidate.get("smiles")
    if not smiles or not isinstance(smiles, str):
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")

    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
    except Exception as exc:
        return error_result(result, "parse_error", f"RDKit parse failed: {exc}")
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    domain_properties = compute_domain_properties(mol)
    domain_error = check_domain(domain_properties, spec.get("domain") or {})
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=domain_properties)

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    try:
        prediction = predict_soltrannet_log_s(canonical_smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=domain_properties)
    except runtime.DockerRuntimeTimeout as exc:
        return error_result(result, "verifier_timeout", str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(
            result,
            "verifier_tool_error",
            f"SolTranNet prediction failed: {exc}",
            properties=domain_properties,
        )

    properties = {**domain_properties, "soltrannet_log_s": prediction}
    try:
        property_score = score_constraint(properties, constraint)
    except Exception as exc:
        return error_result(result, "verifier_spec_error", f"constraint scoring failed: {exc}", properties=properties)

    result.update(
        {
            "status": "ok",
            "canonical_smiles": canonical_smiles,
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [
                    {
                        "property": constraint["property"],
                        "type": constraint["type"],
                        "score": property_score,
                    }
                ],
                "property_score": property_score,
                "score": property_score,
            },
        }
    )
    return result


def predict_soltrannet_log_s(smiles: str, spec: dict[str, Any]) -> float:
    config = soltrannet_config(spec)
    runtime_name = str(config.get("runtime", "external_docker"))
    if runtime_name != "external_docker":
        raise runtime.DockerRuntimeEnvironmentError(f"unsupported SolTranNet runtime: {runtime_name}")

    base_url = str(config.get("base_url") or os.environ.get("SOLTRANNET_BASE_URL") or "").rstrip("/")
    if not base_url:
        host = str(config["host"])
        port = int(config["port"])
        base_url = f"http://{host}:{port}"
        runtime.ensure_http_container(
            image=str(config["image"]),
            container_name=str(config["container_name"]),
            host=host,
            port=port,
            container_port=int(config["container_port"]),
            readiness_url=f"{base_url}/run/columns/output",
            docker_executable=config.get("docker_executable"),
            startup_timeout_seconds=float(config["startup_timeout_seconds"]),
        )
    payload = runtime.http_json(
        f"{base_url}/run",
        method="POST",
        payload=[smiles],
        timeout_seconds=float(config["prediction_timeout_seconds"]),
    )
    return parse_soltrannet_response(payload)


def parse_soltrannet_response(payload: Any) -> float:
    if not isinstance(payload, list) or not payload:
        raise runtime.DockerRuntimeToolError("SolTranNet response must be a non-empty list")
    row = payload[0]
    if not isinstance(row, dict) or "solubility" not in row:
        raise runtime.DockerRuntimeToolError("SolTranNet response missing 'solubility'")
    try:
        value = float(row["solubility"])
    except (TypeError, ValueError) as exc:
        raise runtime.DockerRuntimeToolError("SolTranNet solubility was not numeric") from exc
    if not math.isfinite(value):
        raise runtime.DockerRuntimeToolError("SolTranNet solubility was not finite")
    return value


def soltrannet_config(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": "external_docker",
        "image": DEFAULT_SOLTRANNET_IMAGE,
        "container_name": DEFAULT_CONTAINER_NAME,
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "container_port": DEFAULT_CONTAINER_PORT,
        "base_url": None,
        "startup_timeout_seconds": 60,
        "prediction_timeout_seconds": 30,
        **(spec.get("soltrannet") or {}),
    }


def compute_domain_properties(mol: Chem.Mol) -> dict[str, Any]:
    return {
        "mw": Descriptors.MolWt(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "formal_charge": Chem.GetFormalCharge(mol),
        "elements": sorted({atom.GetSymbol() for atom in mol.GetAtoms()}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements is not None:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"

    for key in ("heavy_atom_count", "mw", "formal_charge"):
        if key not in domain:
            continue
        lower, upper = domain[key]
        if not lower <= properties[key] <= upper:
            return f"{key} outside [{lower}, {upper}]"
    return None


def soltrannet_versions(spec: dict[str, Any]) -> dict[str, Any]:
    config = soltrannet_config(spec)
    return {
        "verifier_image": spec.get("verifier_image"),
        "soltrannet_backend": "eos6oli_v1",
        "soltrannet_image": config["image"],
        "rdkit": metadata.version("rdkit"),
    }
