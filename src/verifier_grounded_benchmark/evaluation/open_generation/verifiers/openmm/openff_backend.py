"""OpenMM + OpenFF/GAFF ligand minimization backend."""

from __future__ import annotations

from importlib import metadata
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.openmm.runtime import (
    DEFAULT_OPENFF_FORCEFIELD,
    ENV_FAILURE,
    TOOL_FAILURE,
    OpenMMEnvironmentError,
    OpenMMToolError,
    run_gaff_smoke,
    run_openff_smoke,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import base_result, error_result, verified_result


DEFAULT_BACKEND = {
    "forcefield_family": "openff",
    "forcefield_name": DEFAULT_OPENFF_FORCEFIELD,
    "platform": "Reference",
}


def evaluate_openmm_openff_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    result = base_result(task["task_id"], spec.get("verifier_id"), openmm_openff_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    if constraint.get("property") not in allowed_properties:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

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
        ligand_properties = compute_ligand_properties(canonical_smiles, spec.get("backend") or {})
    except OpenMMEnvironmentError as exc:
        return error_result(result, ENV_FAILURE, str(exc), properties=domain_properties)
    except OpenMMToolError as exc:
        return error_result(result, TOOL_FAILURE, str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(result, TOOL_FAILURE, f"OpenMM/OpenFF calculation failed: {exc}", properties=domain_properties)

    properties = {**domain_properties, **ligand_properties}
    return verified_result(
        result, properties, canonical_candidate={"smiles": canonical_smiles}
    )


def compute_ligand_properties(smiles: str, backend: dict[str, Any]) -> dict[str, float | int | str]:
    config = {**DEFAULT_BACKEND, **backend}
    family = str(config.get("forcefield_family", "openff")).lower()
    platform = str(config.get("platform", "Reference"))
    if family == "openff":
        smoke = run_openff_smoke(
            smiles=smiles,
            forcefield_name=str(config.get("forcefield_name", DEFAULT_OPENFF_FORCEFIELD)),
            preferred_platform=platform,
        )
    elif family == "gaff":
        smoke = run_gaff_smoke(preferred_platform=platform)
    else:
        raise OpenMMToolError(f"unsupported forcefield_family: {family}")

    result: dict[str, float | int | str] = {
        "forcefield_family": family,
        "forcefield_name": str(config.get("forcefield_name", DEFAULT_OPENFF_FORCEFIELD)),
        "parameterization_success": int(smoke.get("parameterization_success", 1)),
    }
    for key, value in smoke.items():
        if key == "status":
            continue
        if isinstance(value, (int, float, str)):
            result[key] = value
    return result


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


def openmm_openff_versions(spec: dict[str, Any]) -> dict[str, Any]:
    versions: dict[str, Any] = {
        "verifier_image": spec.get("verifier_image"),
        "openmm_openff_backend": "ligand_minimization_v1",
    }
    for distribution, key in [
        ("openmm", "openmm"),
        ("openff-toolkit", "openff_toolkit"),
        ("openff-interchange", "openff_interchange"),
        ("openmmforcefields", "openmmforcefields"),
    ]:
        try:
            versions[key] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[key] = None
    return versions
