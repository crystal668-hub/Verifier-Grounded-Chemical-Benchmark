"""Shared RDKit descriptor backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
from typing import Any

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, QED, rdMolDescriptors

from verifiers.result_schema import base_result
from verifiers.result_schema import error_result
from verifiers.scoring import clamp
from verifiers.scoring import score_constraint

sascorer = importlib.import_module("rdkit.Contrib.SA_Score.sascorer")

DESCRIPTOR_FUNCTIONS = {
    "qed": QED.qed,
    "logp": Crippen.MolLogP,
    "tpsa": rdMolDescriptors.CalcTPSA,
    "mw": Descriptors.MolWt,
    "hbd": rdMolDescriptors.CalcNumHBD,
    "hba": rdMolDescriptors.CalcNumHBA,
    "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds,
    "sa_score": sascorer.calculateScore,
    "fraction_csp3": rdMolDescriptors.CalcFractionCSP3,
    "ring_count": rdMolDescriptors.CalcNumRings,
}


def evaluate_descriptor_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = task["task_id"]
    result = base_result(task_id, spec.get("verifier_id"), rdkit_versions(spec))
    descriptor = spec.get("descriptor")
    if descriptor != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier descriptor {descriptor!r} does not match constraint property {constraint.get('property')!r}",
        )

    smiles = candidate.get("smiles")
    if not smiles or not isinstance(smiles, str):
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")

    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
    except Exception as exc:  # RDKit can raise for malformed edge cases.
        return error_result(result, "parse_error", f"RDKit parse failed: {exc}")
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    allowed_elements = set(spec["domain"]["allowed_elements"])
    elements = {atom.GetSymbol() for atom in mol.GetAtoms()}
    disallowed = sorted(elements - allowed_elements)
    if disallowed:
        return error_result(result, "domain_error", f"disallowed elements: {', '.join(disallowed)}")

    properties = compute_domain_properties(mol)
    domain_error = check_domain(properties, spec["domain"])
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=properties)

    descriptor_properties = {descriptor: compute_descriptor(mol, descriptor)}
    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": score_constraint(descriptor_properties, constraint),
    }
    property_score = float(constraint_score["score"])

    result.update(
        {
            "status": "ok",
            "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
            "properties": descriptor_properties,
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


def compute_descriptor(mol: Chem.Mol, descriptor: str) -> float | int:
    try:
        function = DESCRIPTOR_FUNCTIONS[descriptor]
    except KeyError as exc:
        raise ValueError(f"unsupported descriptor: {descriptor}") from exc
    return function(mol)


def compute_domain_properties(mol: Chem.Mol) -> dict[str, float | int]:
    return {
        "mw": Descriptors.MolWt(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "formal_charge": Chem.GetFormalCharge(mol),
    }


def check_domain(properties: dict[str, float | int], domain: dict[str, Any]) -> str | None:
    heavy_min, heavy_max = domain["heavy_atom_count"]
    mw_min, mw_max = domain["mw"]
    charge_min, charge_max = domain["formal_charge"]
    if not heavy_min <= properties["heavy_atom_count"] <= heavy_max:
        return f"heavy_atom_count outside [{heavy_min}, {heavy_max}]"
    if not mw_min <= properties["mw"] <= mw_max:
        return f"mw outside [{mw_min}, {mw_max}]"
    if not charge_min <= properties["formal_charge"] <= charge_max:
        return f"formal_charge outside [{charge_min}, {charge_max}]"
    return None


def geometric_mean(values: Any) -> float:
    scores = [clamp(float(value)) for value in values]
    if not scores:
        return 0.0
    if any(score == 0.0 for score in scores):
        return 0.0
    return math.prod(scores) ** (1.0 / len(scores))


def rdkit_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "rdkit": metadata.version("rdkit"),
    }
