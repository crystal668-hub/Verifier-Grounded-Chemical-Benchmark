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


def configured_opera_executable(spec: dict[str, Any]) -> str | None:
    opera_spec = spec.get("opera") or {}
    configured = opera_spec.get("executable") or os.environ.get("OPERA_EXECUTABLE")
    return str(configured) if configured else None


def find_opera_executable(spec: dict[str, Any]) -> str | None:
    configured = configured_opera_executable(spec)
    if configured:
        path = Path(configured)
        executable = str(path) if path.exists() else shutil.which(configured)
        if executable is None:
            return None
        return executable if os.access(executable, os.X_OK) else None
    for command in ("opera", "OPERA"):
        executable = shutil.which(command)
        if executable and os.access(executable, os.X_OK):
            return executable
    return None


def resolve_mcr_directory(spec: dict[str, Any]) -> str | None:
    opera_spec = spec.get("opera") or {}
    mcr_directory = opera_spec.get("mcr_directory") or os.environ.get("OPERA_MCR_DIRECTORY")
    return str(mcr_directory) if mcr_directory else None


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
        configured = configured_opera_executable(spec)
        if configured:
            message = f"Configured OPERA executable does not exist: {configured}"
        else:
            message = "OPERA executable not found. Set spec['opera']['executable'], OPERA_EXECUTABLE, or PATH."
        return error_result(
            result,
            "verifier_environment_error",
            message,
            properties=domain_properties,
        )

    mcr_directory = resolve_mcr_directory(spec)
    if not mcr_directory:
        return error_result(
            result,
            "verifier_environment_error",
            "OPERA MCR directory not configured. Set spec['opera']['mcr_directory'] or OPERA_MCR_DIRECTORY.",
            properties=domain_properties,
        )
    if not Path(mcr_directory).is_dir():
        return error_result(
            result,
            "verifier_environment_error",
            f"Configured OPERA MCR directory is not a directory: {mcr_directory}",
            properties=domain_properties,
        )

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    try:
        opera_properties = run_opera(executable, mcr_directory, canonical_smiles, property_name, spec)
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

    domain_gate = applicability_domain_gate(opera_properties, property_name)
    final_score = property_score * domain_gate
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
                "domain_gate": domain_gate,
                "constraint_scores": [constraint_score],
                "property_score": property_score,
                "score": final_score,
            },
        }
    )
    return result


def run_opera(
    executable: str,
    mcr_directory: str,
    smiles: str,
    property_name: str,
    spec: dict[str, Any],
) -> dict[str, float | int]:
    opera_spec = spec.get("opera") or {}
    endpoint = str(opera_spec.get("endpoint") or opera_spec.get("model") or property_name)
    timeout_seconds = float(opera_spec.get("timeout_seconds", spec.get("timeout_seconds", 120)))
    with tempfile.TemporaryDirectory(prefix="opera-") as temp_dir:
        work_dir = Path(temp_dir)
        input_path = work_dir / "candidate.smi"
        output_path = work_dir / "predictions.csv"
        input_path.write_text(f"{smiles}\tcandidate\n")

        completed = subprocess.run(
            [
                executable,
                mcr_directory,
                "--SMI",
                str(input_path),
                "--Output",
                str(output_path),
                "--Endpoint",
                endpoint,
            ],
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

    property_column = property_name if property_name in row else "pred" if "pred" in row else None
    if property_column is None or row[property_column] in {None, ""}:
        raise OPERAToolError(f"OPERA output missing property {property_name!r}")

    try:
        properties: dict[str, float | int] = {property_name: float(row[property_column])}
    except ValueError as exc:
        raise OPERAToolError(f"OPERA property {property_name!r} is not numeric") from exc

    ad_name = f"AD_{property_name}"
    ad_value = row.get(ad_name)
    if ad_value in {None, ""} and property_column == "pred":
        ad_value = row.get("AD")
    if ad_value not in {None, ""}:
        try:
            properties[ad_name] = int(float(ad_value))
        except ValueError as exc:
            raise OPERAToolError(f"OPERA applicability-domain flag {ad_name!r} is not numeric") from exc
    return properties


def applicability_domain_gate(properties: dict[str, Any], property_name: str) -> float:
    ad_value = properties.get(f"AD_{property_name}")
    if ad_value is None:
        return 1.0
    return 1.0 if int(ad_value) != 0 else 0.0


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
