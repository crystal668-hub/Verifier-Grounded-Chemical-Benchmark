"""ADMET-AI property backend for small-molecule verifier scripts."""

from __future__ import annotations

import contextlib
import importlib.metadata as metadata
import io
from functools import lru_cache
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


@lru_cache(maxsize=4)
def load_model_cached(include_physchem: bool, drugbank_percentiles: bool, num_workers: int):
    from admet_ai import ADMETModel

    return ADMETModel(
        include_physchem=include_physchem,
        drugbank_path=None if not drugbank_percentiles else None,
        num_workers=num_workers,
    )


def load_model(spec: dict[str, Any]):
    admet_spec = spec.get("admet_ai") or {}
    return load_model_cached(
        bool(admet_spec.get("include_physchem", False)),
        bool(admet_spec.get("drugbank_percentiles", False)),
        int(admet_spec.get("num_workers", 0)),
    )


def quiet_predict(model: Any, smiles: str) -> dict[str, float]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        predictions = model.predict(smiles=smiles)
    return {str(key): float(value) for key, value in dict(predictions).items()}


def evaluate_admet_ai_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = task["task_id"]
    result = base_result(task_id, spec.get("verifier_id"), admet_ai_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
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
        predictions = quiet_predict(load_model(spec), canonical_smiles)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"ADMET-AI prediction failed: {exc}")

    if property_name not in predictions:
        return error_result(result, "verifier_tool_error", f"ADMET-AI output missing property {property_name!r}")

    properties = {property_name: predictions[property_name]}
    try:
        property_score = score_constraint(properties, constraint)
    except Exception as exc:
        return error_result(result, "verifier_spec_error", f"constraint scoring failed: {exc}")

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


def admet_ai_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "admet-ai": metadata.version("admet-ai"),
        "chemprop": metadata.version("chemprop"),
        "rdkit": metadata.version("rdkit"),
    }
