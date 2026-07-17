"""MolGpKa pKa backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib.metadata as metadata
import json
import math
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common import docker_model_runtime as runtime
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import base_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import error_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import verified_result


DEFAULT_MOLGPKA_IMAGE = "ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d"
MOLGPKA_SCALAR_PROPERTIES = {"molgpka_min_pka", "molgpka_max_pka", "molgpka_pka_count"}


def evaluate_molgpka_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), molgpka_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )
    if property_name not in MOLGPKA_SCALAR_PROPERTIES:
        return error_result(result, "verifier_spec_error", f"unsupported MolGpKa property {property_name!r}")

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
        model_properties = predict_molgpka_properties(canonical_smiles, spec)
    except runtime.DockerRuntimeEnvironmentError as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=domain_properties)
    except runtime.DockerRuntimeTimeout as exc:
        return error_result(result, "verifier_timeout", str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(
            result,
            "verifier_tool_error",
            f"MolGpKa prediction failed: {exc}",
            properties=domain_properties,
        )

    properties = {**domain_properties, **model_properties}
    if property_name not in properties:
        return error_result(
            result,
            "domain_error",
            "MolGpKa predicted no ionizable pKa values for min/max pKa scoring",
            properties=properties,
        )

    return verified_result(
        result, properties, canonical_candidate={"smiles": canonical_smiles}
    )


def predict_molgpka_properties(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
    config = molgpka_config(spec)
    runtime_name = str(config.get("runtime", "external_docker"))
    if runtime_name != "external_docker":
        raise runtime.DockerRuntimeEnvironmentError(f"unsupported MolGpKa runtime: {runtime_name}")

    code = (
        "from cts_molgpka import CTSMolgpka; "
        "import json, sys; "
        "print(json.dumps(CTSMolgpka().main(sys.argv[1])))"
    )
    stdout = runtime.run_one_shot_container(
        image=str(config["image"]),
        platform=str(config["platform"]) if config.get("platform") else None,
        timeout_seconds=float(config["timeout_seconds"]),
        docker_executable=config.get("docker_executable"),
        workdir="/src",
        command=["micromamba", "run", "-n", "MolGpka", "python", "-c", code, smiles],
    )
    return parse_molgpka_stdout(stdout)


def parse_molgpka_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            return parse_molgpka_response(json.loads(line))
        except json.JSONDecodeError:
            continue
    raise runtime.DockerRuntimeToolError("MolGpKa stdout contained no JSON prediction")


def parse_molgpka_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or len(payload) != 3:
        raise runtime.DockerRuntimeToolError("MolGpKa response must be [smiles, site_count, pka_values]")
    site_count = payload[1]
    if isinstance(site_count, bool) or not isinstance(site_count, int):
        raise runtime.DockerRuntimeToolError("MolGpKa site count must be an integer")
    if site_count < 0:
        raise runtime.DockerRuntimeToolError("MolGpKa site count must be non-negative")
    values_raw = payload[2]
    if not isinstance(values_raw, list):
        raise runtime.DockerRuntimeToolError("MolGpKa pKa values must be a list")
    if any(isinstance(value, bool) for value in values_raw):
        raise runtime.DockerRuntimeToolError("MolGpKa pKa values must be numeric")
    try:
        values = [float(value) for value in values_raw]
    except (TypeError, ValueError) as exc:
        raise runtime.DockerRuntimeToolError("MolGpKa pKa values must be numeric") from exc
    if any(not math.isfinite(value) for value in values):
        raise runtime.DockerRuntimeToolError("MolGpKa pKa values must be finite")
    if site_count != len(values):
        raise runtime.DockerRuntimeToolError("MolGpKa site count does not match pKa value count")

    properties: dict[str, Any] = {
        "molgpka_pka_values": values,
        "molgpka_pka_count": site_count,
    }
    if values:
        properties["molgpka_min_pka"] = min(values)
        properties["molgpka_max_pka"] = max(values)
    return properties


def molgpka_config(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": "external_docker",
        "image": DEFAULT_MOLGPKA_IMAGE,
        "platform": "linux/amd64",
        "timeout_seconds": 120,
        **(spec.get("molgpka") or {}),
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


def molgpka_versions(spec: dict[str, Any]) -> dict[str, Any]:
    config = molgpka_config(spec)
    return {
        "verifier_image": spec.get("verifier_image"),
        "molgpka_backend": "gcn_container_v1",
        "molgpka_image": config["image"],
        "rdkit": metadata.version("rdkit"),
    }
