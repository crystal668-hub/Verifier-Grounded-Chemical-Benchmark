"""AtomisticSkills-backed verifiers for first-batch smoke tasks."""

from __future__ import annotations

import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any

from pymatgen.core import Structure

from verifiers.atomisticskills_backend import (
    AtomisticSkillsEnvironmentError,
    AtomisticSkillsMCPAdapter,
    AtomisticSkillsScriptAdapter,
    AtomisticSkillsTimeoutError,
    AtomisticSkillsToolError,
)
from verifiers.small_molecule_rdkit import clamp, geometric_mean, score_constraint


def evaluate_base_supercell(answer: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    result = base_result(task["task_id"], spec["verifier_id"])
    payload = first_candidate(answer).get("json")
    if not isinstance(payload, dict):
        return error_result(result, "parse_error", "first candidate must include a JSON object")

    matrix = payload.get("scaling_matrix")
    if not valid_scaling_matrix(matrix):
        return error_result(result, "parse_error", "scaling_matrix must be a positive integer, 3 positive integers, or 3x3 integers")

    structure_path = Path(spec["fixture"]["structure_path"])
    with tempfile.TemporaryDirectory(prefix="atomisticskills-base-") as temp_dir:
        output_path = Path(temp_dir) / "supercell.cif"
        arguments = {
            "structure_path": str(structure_path),
            "scaling_matrix_json": json.dumps(matrix),
            "save_to_file": str(output_path),
        }
        try:
            tool_result = AtomisticSkillsMCPAdapter(spec["tool"]["server"]).call_tool(
                spec["tool"]["name"],
                arguments,
                timeout_seconds=float(spec.get("timeout_seconds", 60.0)),
            )
        except AtomisticSkillsEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc))
        except AtomisticSkillsTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc))
        except AtomisticSkillsToolError as exc:
            return error_result(result, "verifier_tool_error", str(exc))

        generated_path = output_path if output_path.exists() else extract_saved_path(str(tool_result))
        if generated_path is None or not generated_path.exists():
            return error_result(result, "verifier_tool_error", "base.supercell_expansion did not produce a readable CIF")

        properties = inspect_structure(generated_path)

    expected = spec["expected"]
    checks = [
        properties["atom_count"] == int(expected["atom_count"]),
        properties["reduced_formula"] == expected["reduced_formula"],
    ]
    score = 1.0 if all(checks) else 0.0
    return ok_result(
        result,
        properties=properties,
        constraint_scores=[
            {"property": "atom_count", "type": "exact", "score": 1.0 if checks[0] else 0.0},
            {"property": "reduced_formula", "type": "exact", "score": 1.0 if checks[1] else 0.0},
        ],
        score=score,
    )


def evaluate_drugdisc_descriptors(answer: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    result = base_result(task["task_id"], spec["verifier_id"])
    candidate = first_candidate(answer)
    smiles = candidate.get("smiles")
    if not isinstance(smiles, str) or not smiles:
        return error_result(result, "parse_error", "first candidate must include a SMILES string")
    if spec.get("domain", {}).get("single_component", True) and "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")

    try:
        adapter = AtomisticSkillsMCPAdapter(spec["tool"]["server"])
        standardized = adapter.call_tool(
            "standardize_molecule",
            {"smiles": smiles, "mode": spec.get("standardization_mode", "cleanup")},
            timeout_seconds=float(spec.get("timeout_seconds", 60.0)),
        )
        if not isinstance(standardized, dict) or not standardized.get("success"):
            return error_result(result, "verifier_tool_error", tool_error_message(standardized))

        canonical_smiles = str(standardized["standardized_smiles"])
        with tempfile.TemporaryDirectory(prefix="atomisticskills-drugdisc-") as temp_dir:
            output_file = Path(temp_dir) / "descriptors.json"
            descriptor_result = adapter.call_tool(
                "compute_molecular_descriptors",
                {"smiles": canonical_smiles, "output_file": str(output_file)},
                timeout_seconds=float(spec.get("timeout_seconds", 60.0)),
            )
            if not isinstance(descriptor_result, dict) or not descriptor_result.get("success"):
                return error_result(result, "verifier_tool_error", tool_error_message(descriptor_result))
            properties = read_drugdisc_properties(output_file)
    except AtomisticSkillsEnvironmentError as exc:
        return error_result(result, "verifier_environment_error", str(exc))
    except AtomisticSkillsTimeoutError as exc:
        return error_result(result, "verifier_timeout", str(exc))
    except AtomisticSkillsToolError as exc:
        return error_result(result, "verifier_tool_error", str(exc))

    disallowed = sorted(set(properties.get("elements", [])) - set(spec.get("domain", {}).get("allowed_elements", [])))
    if disallowed:
        return error_result(result, "domain_error", f"disallowed elements: {', '.join(disallowed)}", properties=properties)

    constraint_scores = [
        {"property": constraint["property"], "type": constraint["type"], "score": score_constraint(properties, constraint)}
        for constraint in task.get("constraints", [])
    ]
    score = geometric_mean(item["score"] for item in constraint_scores)
    result["canonical_smiles"] = canonical_smiles
    return ok_result(result, properties=properties, constraint_scores=constraint_scores, score=score)


def evaluate_xrd_peak(answer: dict[str, Any], task: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    result = base_result(task["task_id"], spec["verifier_id"])
    candidate = first_candidate(answer)
    proposed = candidate.get("value")
    if not isinstance(proposed, int | float):
        return error_result(result, "parse_error", "first candidate must include a numeric value")

    xrd_config = spec["xrd"]
    with tempfile.TemporaryDirectory(prefix="atomisticskills-xrd-") as temp_dir:
        try:
            xrd_json = AtomisticSkillsScriptAdapter().run_xrd_calculator(
                spec["fixture"]["structure_path"],
                temp_dir,
                wavelength=xrd_config.get("wavelength", "CuKa"),
                timeout_seconds=float(spec.get("timeout_seconds", 120.0)),
            )
        except AtomisticSkillsEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc))
        except AtomisticSkillsTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc))
        except AtomisticSkillsToolError as exc:
            return error_result(result, "verifier_tool_error", str(exc))
        properties = read_xrd_peak_properties(xrd_json)

    tolerance = float(xrd_config["tolerance_degrees"])
    delta = abs(float(proposed) - properties["target_two_theta"])
    score = clamp(1.0 - delta / tolerance) if delta <= tolerance else 0.0
    properties["proposed_two_theta"] = float(proposed)
    properties["absolute_error_degrees"] = delta
    return ok_result(
        result,
        properties=properties,
        constraint_scores=[{"property": "two_theta", "type": "absolute_tolerance", "score": score}],
        score=score,
    )


def first_candidate(answer: dict[str, Any]) -> dict[str, Any]:
    candidates = answer.get("candidates")
    if not candidates or not isinstance(candidates[0], dict):
        return {}
    return candidates[0]


def valid_scaling_matrix(matrix: Any) -> bool:
    if isinstance(matrix, int):
        return matrix > 0
    if isinstance(matrix, list) and len(matrix) == 3 and all(isinstance(item, int) and item > 0 for item in matrix):
        return True
    if isinstance(matrix, list) and len(matrix) == 3:
        return all(
            isinstance(row, list)
            and len(row) == 3
            and all(isinstance(value, int) for value in row)
            and any(value != 0 for value in row)
            for row in matrix
        )
    return False


def extract_saved_path(text: str) -> Path | None:
    match = re.search(r"Saved to ([^\n]+)", text)
    if not match:
        return None
    return Path(match.group(1).strip().rstrip("."))


def inspect_structure(path: Path) -> dict[str, Any]:
    structure = Structure.from_file(str(path))
    return {
        "atom_count": len(structure),
        "reduced_formula": structure.composition.reduced_formula,
    }


def read_drugdisc_properties(output_file: Path) -> dict[str, Any]:
    payload = json.loads(output_file.read_text())
    descriptors = payload.get("descriptors") or []
    if not descriptors or not descriptors[0].get("valid"):
        raise AtomisticSkillsToolError("drugdisc descriptor output contains no valid molecule")
    item = dict(descriptors[0])
    properties = {
        "qed": float(item["qed"]),
        "logp": float(item["logp"]),
        "tpsa": float(item["tpsa"]),
        "mw": float(item["molecular_weight"]),
        "hbd": int(item.get("hbd", 0)),
        "hba": int(item.get("hba", 0)),
        "rotatable_bonds": int(item.get("rotatable_bonds", 0)),
        "heavy_atom_count": int(item.get("num_heavy_atoms", 0)),
        "formal_charge": int(item.get("formal_charge", 0)),
    }
    return properties


def read_xrd_peak_properties(xrd_json: Path) -> dict[str, float]:
    payload = json.loads(xrd_json.read_text())
    x_values = payload.get("x") or []
    y_values = payload.get("y") or []
    if len(x_values) != len(y_values) or not x_values:
        raise AtomisticSkillsToolError("XRD JSON must contain non-empty x and y arrays with equal length")
    max_index = max(range(len(y_values)), key=lambda index: float(y_values[index]))
    return {
        "target_two_theta": float(x_values[max_index]),
        "target_intensity": float(y_values[max_index]),
    }


def tool_error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("error") or payload)
    return str(payload)


def base_result(task_id: str, verifier_id: str) -> dict[str, Any]:
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
        "versions": {"verifier": verifier_id},
    }


def ok_result(
    result: dict[str, Any],
    *,
    properties: dict[str, Any],
    constraint_scores: list[dict[str, Any]],
    score: float,
) -> dict[str, Any]:
    result.update(
        {
            "status": "ok",
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": constraint_scores,
                "property_score": score,
                "score": score,
            },
        }
    )
    return result


def error_result(
    result: dict[str, Any],
    failure_type: str,
    message: str,
    *,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result["failure_type"] = failure_type
    result["message"] = message
    if properties is not None:
        result["properties"] = properties
        result["scores"]["validity_gate"] = 1.0
    if failure_type == "domain_error":
        result["scores"]["validity_gate"] = 1.0
    return result
