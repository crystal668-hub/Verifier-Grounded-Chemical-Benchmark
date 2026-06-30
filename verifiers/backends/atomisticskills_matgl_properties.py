"""Shared AtomisticSkills MatGL MCP backend for verifier scripts."""

from __future__ import annotations

import tempfile
from importlib import metadata
from pathlib import Path
from typing import Any

from pymatgen.core import Structure

from verifiers.atomisticskills_backend import (
    AtomisticSkillsEnvironmentError,
    AtomisticSkillsMCPAdapter,
    AtomisticSkillsTimeoutError,
    AtomisticSkillsToolError,
)
from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result
from verifiers.result_schema import error_result


def evaluate_atomisticskills_matgl_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), atomisticskills_matgl_versions(spec))
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

    cif = candidate.get("cif")
    if not isinstance(cif, str) or not cif.strip():
        return error_result(result, "parse_error", "candidate must include a CIF string")

    with tempfile.TemporaryDirectory(prefix="matgl-property-") as temp_dir:
        structure_path = Path(temp_dir) / "candidate.cif"
        structure_path.write_text(cif)
        try:
            structure = Structure.from_file(str(structure_path))
        except Exception as exc:
            return error_result(result, "parse_error", f"CIF parse failed: {exc}")

        structure_properties = inspect_structure(structure)
        domain_error = check_domain(structure_properties, spec.get("domain", {}))
        if domain_error:
            return error_result(result, "domain_error", domain_error, properties=structure_properties)

        try:
            adapter = AtomisticSkillsMCPAdapter(str(spec.get("backend", {}).get("server", "matgl")))
            property_payload = compute_property(adapter, property_name, structure_path, spec)
        except AtomisticSkillsEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc), properties=structure_properties)
        except AtomisticSkillsTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc), properties=structure_properties)
        except AtomisticSkillsToolError as exc:
            return error_result(result, "verifier_tool_error", str(exc), properties=structure_properties)

    property_error = parse_property_payload(property_name, property_payload)
    if isinstance(property_error, str):
        return error_result(result, "verifier_tool_error", property_error, properties=structure_properties)

    properties = {**structure_properties, **property_error}
    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": score_constraint(properties, constraint),
    }
    score = float(constraint_score["score"])
    result.update(
        {
            "status": "ok",
            "properties": properties,
            "scores": {
                "validity_gate": 1.0,
                "domain_gate": 1.0,
                "constraint_scores": [constraint_score],
                "property_score": score,
                "score": score,
            },
        }
    )
    return result


def compute_property(
    adapter: AtomisticSkillsMCPAdapter,
    property_name: str,
    structure_path: Path,
    spec: dict[str, Any],
) -> Any:
    timeout = float(spec.get("timeout_seconds", 120.0))
    matgl_config = spec.get("matgl") or {}
    if property_name == "bandgap":
        return adapter.call_tool(
            "predict_bandgap",
            {
                "structure_data": str(structure_path),
                "task_name": matgl_config.get("task_name", "PBE"),
            },
            timeout_seconds=timeout,
        )
    if property_name == "formation_energy":
        results = adapter.call_tools(
            [
                (
                    "load_model",
                    {
                        "model_name": matgl_config.get("model_name", "MEGNet-Eform-MP-2018.6.1"),
                        "device": matgl_config.get("device", "cpu"),
                    },
                ),
                ("predict_structure", {"structure_data": str(structure_path)}),
            ],
            timeout_seconds=timeout,
        )
        return results[-1]
    raise AtomisticSkillsToolError(f"unsupported MatGL property: {property_name}")


def parse_property_payload(property_name: str, payload: Any) -> dict[str, float | str] | str:
    if not isinstance(payload, dict):
        return f"MatGL {property_name} returned non-object payload"
    if payload.get("error"):
        return str(payload["error"])
    unit = str(payload.get("unit", "eV"))
    if property_name == "bandgap":
        if "bandgap" not in payload:
            return "MatGL bandgap payload missing bandgap"
        return {"bandgap": float(payload["bandgap"]), "bandgap_unit": unit}
    if property_name == "formation_energy":
        if "formation_energy" in payload:
            return {"formation_energy": float(payload["formation_energy"]), "formation_energy_unit": unit}
        if "energy" in payload:
            return {"formation_energy": float(payload["energy"]), "formation_energy_unit": unit}
        return "MatGL formation energy payload missing formation_energy"
    return f"unsupported MatGL property: {property_name}"


def inspect_structure(structure: Structure) -> dict[str, Any]:
    return {
        "reduced_formula": structure.composition.reduced_formula,
        "atom_count": len(structure),
        "volume": float(structure.volume),
        "elements": sorted({str(element) for element in structure.composition.elements}),
    }


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    allowed_elements = domain.get("allowed_elements")
    if allowed_elements:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"
    if "atom_count" in domain:
        lower, upper = domain["atom_count"]
        if not int(lower) <= int(properties["atom_count"]) <= int(upper):
            return f"atom_count outside [{lower}, {upper}]"
    if "volume" in domain:
        lower, upper = domain["volume"]
        if not float(lower) <= float(properties["volume"]) <= float(upper):
            return f"volume outside [{lower}, {upper}]"
    return None


def atomisticskills_matgl_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "matgl_backend": "atomisticskills_matgl_mcp",
        "pymatgen": metadata.version("pymatgen"),
    }
