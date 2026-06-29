"""OPERA property backend for small-molecule verifier scripts."""

from __future__ import annotations

import csv
import importlib.metadata as metadata
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import Descriptors

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result, error_result


class OPERAEnvironmentError(RuntimeError):
    """Raised when OPERA is not available."""


class OPERAToolError(RuntimeError):
    """Raised when OPERA execution or output parsing fails."""


def find_opera_executable(spec: dict[str, Any]) -> str | None:
    opera_spec = spec.get("opera") or {}
    configured = opera_spec.get("executable") or os.environ.get("OPERA_EXECUTABLE")
    if configured:
        return str(configured) if Path(str(configured)).exists() else None
    return shutil.which("opera") or shutil.which("OPERA")


def evaluate_opera_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = task["task_id"]
    result = base_result(task_id, spec.get("verifier_id"), opera_versions(spec))
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

    executable = find_opera_executable(spec)
    if executable is None:
        return error_result(
            result,
            "verifier_environment_error",
            "OPERA executable not found. Set spec['opera']['executable'], OPERA_EXECUTABLE, or PATH.",
            properties=domain_properties,
        )

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    try:
        opera_properties = run_opera(executable, canonical_smiles, property_name, spec)
    except subprocess.TimeoutExpired:
        return error_result(result, "verifier_timeout", "OPERA run timed out", properties=domain_properties)
    except OPERAEnvironmentError as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=domain_properties)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", f"OPERA prediction failed: {exc}", properties=domain_properties)

    properties = {**domain_properties, **opera_properties}
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


def run_opera(
    executable: str,
    smiles: str,
    property_name: str,
    spec: dict[str, Any],
) -> dict[str, float | int]:
    opera_spec = spec.get("opera") or {}
    model = str(opera_spec.get("model") or property_name)
    timeout_seconds = float(opera_spec.get("timeout_seconds", spec.get("timeout_seconds", 120)))
    with tempfile.TemporaryDirectory(prefix="opera-") as temp_dir:
        work_dir = Path(temp_dir)
        input_path = work_dir / "candidate.smi"
        output_path = work_dir / "predictions.csv"
        input_path.write_text(f"{smiles}\tcandidate\n")

        completed = subprocess.run(
            [executable, str(input_path), str(output_path), model],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"OPERA exited {completed.returncode}"
            raise OPERAToolError(message)
        if not output_path.exists():
            raise OPERAToolError(f"OPERA output file was not created: {output_path}")
        return parse_opera_output(output_path.read_text(), property_name)


def parse_opera_output(output: str, property_name: str) -> dict[str, float | int]:
    reader = csv.DictReader(output.splitlines())
    try:
        row = next(reader)
    except StopIteration as exc:
        raise OPERAToolError("OPERA output contained no prediction rows") from exc

    if property_name not in row or row[property_name] in {None, ""}:
        raise OPERAToolError(f"OPERA output missing property {property_name!r}")

    try:
        properties: dict[str, float | int] = {property_name: float(row[property_name])}
    except ValueError as exc:
        raise OPERAToolError(f"OPERA property {property_name!r} is not numeric") from exc

    ad_name = f"AD_{property_name}"
    ad_value = row.get(ad_name)
    if ad_value not in {None, ""}:
        try:
            properties[ad_name] = int(float(ad_value))
        except ValueError as exc:
            raise OPERAToolError(f"OPERA applicability-domain flag {ad_name!r} is not numeric") from exc
    return properties


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


def opera_versions(spec: dict[str, Any]) -> dict[str, Any]:
    opera_spec = spec.get("opera") or {}
    return {
        "verifier_image": spec.get("verifier_image"),
        "opera": opera_spec.get("version", "2.9"),
        "rdkit": metadata.version("rdkit"),
    }
