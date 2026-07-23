"""Shared RDKit descriptor backend for small-molecule verifier scripts."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
from typing import Any

from rdkit import Chem, DataStructs
from rdkit.Chem import Crippen, Descriptors, QED, rdFingerprintGenerator, rdMolDescriptors

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import base_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import error_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import verified_result


DESCRIPTOR_FUNCTIONS = {
    "qed": QED.qed,
    "logp": Crippen.MolLogP,
    "tpsa": rdMolDescriptors.CalcTPSA,
    "mw": Descriptors.MolWt,
    "hbd": rdMolDescriptors.CalcNumHBD,
    "hba": rdMolDescriptors.CalcNumHBA,
    "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds,
    "fraction_csp3": rdMolDescriptors.CalcFractionCSP3,
    "ring_count": rdMolDescriptors.CalcNumRings,
}


class SAScorerUnavailable(RuntimeError):
    """Raised when the optional RDKit Contrib SA_Score scorer is unavailable."""


class VerifierSpecMismatch(RuntimeError):
    """Raised when a frozen RDKit protocol does not match its audit values."""


def evaluate_descriptor_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = task["task_id"]
    result = base_result(task_id, spec.get("verifier_id"), rdkit_versions(spec))
    descriptors = spec.get("descriptors") or [spec.get("descriptor")]
    descriptor = constraint.get("property")
    if descriptor not in descriptors:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier descriptors {descriptors!r} do not include constraint property {descriptor!r}",
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

    domain = spec["domain"]
    if "allowed_elements" in domain:
        allowed_elements = set(domain["allowed_elements"])
        elements = {atom.GetSymbol() for atom in mol.GetAtoms()}
        disallowed = sorted(elements - allowed_elements)
        if disallowed:
            return error_result(result, "domain_error", f"disallowed elements: {', '.join(disallowed)}")

    properties = compute_domain_properties(mol)
    domain_error = check_domain(properties, domain)
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=properties)

    try:
        descriptor_properties = {
            name: compute_descriptor(mol, name, spec) for name in descriptors
        }
        descriptor_properties.update(reference_properties(spec))
        descriptor_properties.update(protocol_properties(spec))
    except SAScorerUnavailable as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=properties)
    except VerifierSpecMismatch as exc:
        return error_result(result, "verifier_spec_error", str(exc), properties=properties)

    reported_properties: dict[str, Any] = dict(descriptor_properties)
    if spec.get("report_domain_properties") or "atom_count" in domain or "element_fraction_min" in domain:
        reported_properties.update(
            {
                "atom_count": properties["atom_count"],
                "element_counts": properties["element_counts"],
                "element_fractions": properties["element_fractions"],
            }
        )

    return verified_result(
        result,
        reported_properties,
        canonical_candidate={"smiles": Chem.MolToSmiles(mol, canonical=True)},
    )


def compute_descriptor(
    mol: Chem.Mol, descriptor: str, spec: dict[str, Any] | None = None
) -> float | int:
    if descriptor == "sa_score":
        return compute_sa_score(mol)
    if descriptor == "caffeine_morgan_tanimoto":
        return compute_reference_similarity(mol, spec or {})
    try:
        function = DESCRIPTOR_FUNCTIONS[descriptor]
    except KeyError as exc:
        raise ValueError(f"unsupported descriptor: {descriptor}") from exc
    return function(mol)


def reference_properties(spec: dict[str, Any]) -> dict[str, float]:
    reference = spec.get("reference")
    if not isinstance(reference, dict) or "sa_score" not in reference:
        return {}
    mol = Chem.MolFromSmiles(str(reference.get("canonical_smiles")), sanitize=True)
    if mol is None:
        raise VerifierSpecMismatch("reference canonical_smiles is invalid")
    actual = float(compute_sa_score(mol))
    expected = float(reference["sa_score"])
    if abs(actual - expected) > float(reference.get("sa_tolerance", 1e-12)):
        raise VerifierSpecMismatch(
            f"reference SA score mismatch: expected {expected}, observed {actual}"
        )
    return {"reference_sa_score": actual}


def protocol_properties(spec: dict[str, Any]) -> dict[str, int]:
    fingerprint = spec.get("fingerprint")
    if not isinstance(fingerprint, dict):
        return {}
    return {
        "fingerprint_radius": int(fingerprint["radius"]),
        "fingerprint_size": int(fingerprint["fp_size"]),
    }


def compute_reference_similarity(mol: Chem.Mol, spec: dict[str, Any]) -> float:
    reference = spec.get("reference") or {}
    fingerprint = spec.get("fingerprint") or {}
    reference_mol = Chem.MolFromSmiles(
        str(reference.get("canonical_smiles")), sanitize=True
    )
    if reference_mol is None:
        raise VerifierSpecMismatch("reference canonical_smiles is invalid")
    required = {
        "generator": "Morgan",
        "radius": 2,
        "fp_size": 2048,
        "include_chirality": False,
        "use_bond_types": True,
        "fingerprint_type": "bit_vector",
        "similarity": "Tanimoto",
    }
    if fingerprint != required:
        raise VerifierSpecMismatch(
            "caffeine fingerprint configuration does not match frozen protocol"
        )
    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2,
        fpSize=2048,
        includeChirality=False,
        useBondTypes=True,
    )
    return float(
        DataStructs.TanimotoSimilarity(
            generator.GetFingerprint(mol), generator.GetFingerprint(reference_mol)
        )
    )


def compute_sa_score(mol: Chem.Mol) -> float:
    try:
        sascorer = importlib.import_module("rdkit.Contrib.SA_Score.sascorer")
    except ImportError as exc:
        raise SAScorerUnavailable("RDKit SA_Score scorer unavailable") from exc
    return sascorer.calculateScore(mol)


def compute_domain_properties(mol: Chem.Mol) -> dict[str, Any]:
    explicit_h_mol = Chem.AddHs(mol)
    element_counts: dict[str, int] = {}
    for atom in explicit_h_mol.GetAtoms():
        symbol = atom.GetSymbol()
        element_counts[symbol] = element_counts.get(symbol, 0) + 1
    atom_count = explicit_h_mol.GetNumAtoms()
    return {
        "mw": Descriptors.MolWt(mol),
        "heavy_atom_count": mol.GetNumHeavyAtoms(),
        "formal_charge": Chem.GetFormalCharge(mol),
        "atom_count": atom_count,
        "element_counts": element_counts,
        "element_fractions": {
            element: count / atom_count for element, count in element_counts.items()
        },
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    if "heavy_atom_count" in domain:
        heavy_min, heavy_max = domain["heavy_atom_count"]
        if not heavy_min <= properties["heavy_atom_count"] <= heavy_max:
            return f"heavy_atom_count outside [{heavy_min}, {heavy_max}]"
    if "mw" in domain:
        mw_min, mw_max = domain["mw"]
        if not mw_min <= properties["mw"] <= mw_max:
            return f"mw outside [{mw_min}, {mw_max}]"
    if "formal_charge" in domain:
        charge_min, charge_max = domain["formal_charge"]
        if not charge_min <= properties["formal_charge"] <= charge_max:
            return f"formal_charge outside [{charge_min}, {charge_max}]"
    if "atom_count" in domain:
        atom_min, atom_max = domain["atom_count"]
        if not atom_min <= properties["atom_count"] <= atom_max:
            return f"atom_count outside [{atom_min}, {atom_max}]"
    for element, minimum in domain.get("element_fraction_min", {}).items():
        fraction = properties["element_fractions"].get(element, 0.0)
        if fraction < float(minimum):
            return f"{element} atom fraction below minimum {minimum}"
    for element, minimum in domain.get("element_count_min", {}).items():
        if properties["element_counts"].get(element, 0) < int(minimum):
            return f"{element} count below minimum {minimum}"
    return None


def rdkit_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "rdkit": metadata.version("rdkit"),
    }
