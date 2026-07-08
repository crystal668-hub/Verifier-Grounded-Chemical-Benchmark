"""RDKit ETKDG + MMFF/UFF force-field backend for small molecules."""

from __future__ import annotations

import math
from importlib import metadata
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors

from verifiers.common.scoring import score_constraint
from verifiers.common.result_schema import base_result, error_result


DEFAULT_BACKEND = {
    "embedder": "ETKDGv3",
    "random_seed": 61453,
    "num_conformers": 20,
    "prune_rms_thresh": 0.5,
    "forcefield_priority": ["MMFF94s", "MMFF94", "UFF"],
    "max_iters": 200,
}


class ForceFieldError(RuntimeError):
    """Raised when RDKit force-field setup or calculation fails."""


def evaluate_forcefield_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = task["task_id"]
    result = base_result(task_id, spec.get("verifier_id"), rdkit_forcefield_versions(spec))
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
        forcefield_properties = compute_forcefield_properties(mol, spec.get("backend") or {})
    except ForceFieldError as exc:
        return error_result(result, "verifier_tool_error", str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"RDKit force-field calculation failed: {exc}", properties=domain_properties)

    properties = {**domain_properties, **forcefield_properties}
    try:
        property_score = score_constraint(properties, constraint)
    except Exception as exc:
        return error_result(result, "verifier_spec_error", f"constraint scoring failed: {exc}", properties=properties)

    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": property_score,
    }
    result.update(
        {
            "status": "ok",
            "canonical_smiles": canonical_smiles,
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [constraint_score],
                "property_score": property_score,
                "score": property_score,
            },
        }
    )
    return result


def compute_forcefield_properties(mol: Chem.Mol, backend: dict[str, Any]) -> dict[str, float | int | str]:
    config = {**DEFAULT_BACKEND, **backend}
    molecule = Chem.AddHs(Chem.Mol(mol))
    params = embedding_parameters(str(config.get("embedder", "ETKDGv3")))
    params.randomSeed = int(config.get("random_seed", DEFAULT_BACKEND["random_seed"]))
    params.pruneRmsThresh = float(config.get("prune_rms_thresh", DEFAULT_BACKEND["prune_rms_thresh"]))

    requested_conformers = max(1, int(config.get("num_conformers", DEFAULT_BACKEND["num_conformers"])))
    conformer_ids = list(AllChem.EmbedMultipleConfs(molecule, numConfs=requested_conformers, params=params))
    if not conformer_ids:
        raise ForceFieldError("RDKit ETKDG embedding produced no conformers")

    forcefield_name = choose_forcefield(molecule, config.get("forcefield_priority") or DEFAULT_BACKEND["forcefield_priority"])
    max_iters = int(config.get("max_iters", DEFAULT_BACKEND["max_iters"]))
    energies: list[float] = []
    converged_count = 0
    for conformer_id in conformer_ids:
        status = optimize_conformer(molecule, forcefield_name, conformer_id, max_iters)
        if status == 0:
            converged_count += 1
        energies.append(forcefield_energy(molecule, forcefield_name, conformer_id))

    minimum_energy = min(energies)
    maximum_energy = max(energies)
    median_energy = median(energies)
    return {
        "forcefield_name": forcefield_name,
        "forcefield_parameterized": 1,
        "conformer_count": len(conformer_ids),
        "requested_conformer_count": requested_conformers,
        "embedding_success_rate": len(conformer_ids) / requested_conformers,
        "optimization_converged_fraction": converged_count / len(conformer_ids),
        "best_energy_kcal_mol": minimum_energy,
        "min_energy_kcal_mol": minimum_energy,
        "median_energy_kcal_mol": median_energy,
        "max_energy_kcal_mol": maximum_energy,
        "energy_range_kcal_mol": maximum_energy - minimum_energy,
        "min_nonbonded_distance_angstrom": min_nonbonded_distance(molecule, conformer_ids[0]),
    }


def embedding_parameters(embedder: str) -> Any:
    name = embedder.lower()
    if name == "etkdgv3":
        return AllChem.ETKDGv3()
    if name == "etkdgv2":
        return AllChem.ETKDGv2()
    if name == "etkdg":
        return AllChem.ETKDG()
    raise ForceFieldError(f"unsupported RDKit embedder: {embedder}")


def choose_forcefield(mol: Chem.Mol, priority: Any) -> str:
    for name in [str(item) for item in priority]:
        normalized = name.upper()
        if normalized in {"MMFF94", "MMFF94S"}:
            if AllChem.MMFFHasAllMoleculeParams(mol):
                return "MMFF94s" if normalized == "MMFF94S" else "MMFF94"
            continue
        if normalized == "UFF":
            if AllChem.UFFHasAllMoleculeParams(mol):
                return "UFF"
            continue
        raise ForceFieldError(f"unsupported RDKit force field: {name}")
    raise ForceFieldError("RDKit force-field parameters are not available for this molecule")


def optimize_conformer(mol: Chem.Mol, forcefield_name: str, conformer_id: int, max_iters: int) -> int:
    if forcefield_name in {"MMFF94", "MMFF94s"}:
        return int(AllChem.MMFFOptimizeMolecule(mol, mmffVariant=forcefield_name, confId=conformer_id, maxIters=max_iters))
    return int(AllChem.UFFOptimizeMolecule(mol, confId=conformer_id, maxIters=max_iters))


def forcefield_energy(mol: Chem.Mol, forcefield_name: str, conformer_id: int) -> float:
    if forcefield_name in {"MMFF94", "MMFF94s"}:
        properties = AllChem.MMFFGetMoleculeProperties(mol, mmffVariant=forcefield_name)
        forcefield = AllChem.MMFFGetMoleculeForceField(mol, properties, confId=conformer_id)
    else:
        forcefield = AllChem.UFFGetMoleculeForceField(mol, confId=conformer_id)
    if forcefield is None:
        raise ForceFieldError(f"could not build {forcefield_name} force field")
    energy = float(forcefield.CalcEnergy())
    if not math.isfinite(energy):
        raise ForceFieldError(f"{forcefield_name} energy was not finite")
    return energy


def min_nonbonded_distance(mol: Chem.Mol, conformer_id: int) -> float:
    conformer = mol.GetConformer(conformer_id)
    bonded_pairs = {
        tuple(sorted((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())))
        for bond in mol.GetBonds()
    }
    distances: list[float] = []
    for i in range(mol.GetNumAtoms()):
        first = conformer.GetAtomPosition(i)
        for j in range(i + 1, mol.GetNumAtoms()):
            if (i, j) in bonded_pairs:
                continue
            second = conformer.GetAtomPosition(j)
            distances.append(first.Distance(second))
    return min(distances, default=0.0)


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


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


def rdkit_forcefield_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "rdkit": metadata.version("rdkit"),
        "rdkit_forcefield_backend": "ETKDG_MMFF_UFF",
    }
