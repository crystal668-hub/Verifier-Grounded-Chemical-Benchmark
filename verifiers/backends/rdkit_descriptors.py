"""Shared RDKit descriptor backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import math
from typing import Any

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, QED, rdMolDescriptors

sascorer = importlib.import_module("rdkit.Contrib.SA_Score.sascorer")


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def score_constraint(properties: dict[str, float], constraint: dict[str, Any]) -> float:
    kind = constraint["type"]
    prop = constraint["property"]
    value = float(properties[prop])

    if kind == "window":
        minimum = float(constraint["min"])
        maximum = float(constraint["max"])
        sigma = float(constraint.get("sigma", 1.0))
        if sigma <= 0:
            raise ValueError("window sigma must be positive")
        if minimum <= value <= maximum:
            return 1.0
        distance = minimum - value if value < minimum else value - maximum
        return clamp(math.exp(-distance / sigma))

    if kind in {"maximize_bounded", "minimize_bounded"}:
        forbidden = {"good_at", "baseline"} & set(constraint)
        if forbidden:
            raise ValueError(f"bounded scoring does not accept {sorted(forbidden)}")
        lower = float(constraint["lower"])
        upper = float(constraint["upper"])
        if upper <= lower:
            raise ValueError("bounded scoring requires upper > lower")
        if kind == "maximize_bounded":
            return clamp((value - lower) / (upper - lower))
        return clamp((upper - value) / (upper - lower))

    raise ValueError(f"unsupported constraint type: {kind}")


def evaluate_candidate(candidate: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    task_id = task["task_id"]
    result = base_result(task_id, spec)

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

    properties = compute_properties(mol)
    domain_error = check_domain(properties, spec["domain"])
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=properties)

    constraint_scores = [
        {
            "property": constraint["property"],
            "type": constraint["type"],
            "score": score_constraint(properties, constraint),
        }
        for constraint in task["constraints"]
    ]
    property_score = geometric_mean(item["score"] for item in constraint_scores)

    result.update(
        {
            "status": "ok",
            "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": constraint_scores,
                "property_score": property_score,
                "score": property_score,
            },
        }
    )
    return result


def compute_properties(mol: Chem.Mol) -> dict[str, float | int]:
    return {
        "qed": QED.qed(mol),
        "logp": Crippen.MolLogP(mol),
        "tpsa": rdMolDescriptors.CalcTPSA(mol),
        "mw": Descriptors.MolWt(mol),
        "hbd": rdMolDescriptors.CalcNumHBD(mol),
        "hba": rdMolDescriptors.CalcNumHBA(mol),
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "sa_score": sascorer.calculateScore(mol),
        "fraction_csp3": rdMolDescriptors.CalcFractionCSP3(mol),
        "ring_count": rdMolDescriptors.CalcNumRings(mol),
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


def base_result(task_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "error",
        "canonical_smiles": None,
        "properties": {},
        "scores": {
            "validity_gate": 0.0,
            "domain_gate": 0.0,
            "constraint_scores": [],
            "property_score": 0.0,
            "score": 0.0,
        },
        "failure_type": None,
        "message": None,
        "versions": {
            "verifier_image": spec.get("verifier_image"),
            "rdkit": metadata.version("rdkit"),
        },
    }


def error_result(
    result: dict[str, Any],
    failure_type: str,
    message: str,
    *,
    properties: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    result["failure_type"] = failure_type
    result["message"] = message
    if properties is not None:
        result["properties"] = properties
        result["scores"]["validity_gate"] = 1.0
    if failure_type == "domain_error":
        result["scores"]["validity_gate"] = 1.0
    return result
