"""Native MACE-MP material property backend for CIF verifier scripts."""

from __future__ import annotations

import math
from functools import lru_cache
from importlib import metadata
from typing import Any

from verifiers.common.scoring import score_constraint
from verifiers.common.result_schema import base_result
from verifiers.common.result_schema import error_result


SUPPORTED_MACE_MP_PROPERTIES = {
    "mace_mp_energy_ev",
    "mace_mp_energy_per_atom_ev",
    "mace_mp_max_force_ev_per_angstrom",
    "mace_mp_stress_norm_ev_per_angstrom3",
}
DEFAULT_MACE_MP_MODEL = "small"
DEFAULT_MACE_MP_DEVICE = "cpu"
DEFAULT_MACE_MP_DTYPE = "float32"


def evaluate_mace_mp_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), mace_mp_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    constraint_property = constraint.get("property")
    if constraint_property not in allowed_properties:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint_property!r}",
        )
    if constraint_property not in SUPPORTED_MACE_MP_PROPERTIES:
        return error_result(result, "verifier_spec_error", f"unsupported MACE-MP property: {constraint_property}")

    try:
        structure, atoms = parse_cif_atoms(candidate.get("cif"))
    except ValueError as exc:
        return error_result(result, "parse_error", str(exc))
    except (ImportError, ModuleNotFoundError) as exc:
        return error_result(result, "verifier_environment_error", str(exc))

    structure_properties = inspect_structure(structure, atoms)
    domain_error = check_domain(structure_properties, spec.get("domain") or {})
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=structure_properties)

    try:
        prediction = predict_mace_mp_properties(atoms, spec)
        properties = {**structure_properties, **prediction}
        constraint_score = {
            "property": constraint["property"],
            "type": constraint["type"],
            "score": score_constraint(properties, constraint),
        }
    except (ImportError, ModuleNotFoundError) as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=structure_properties)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", str(exc), properties=structure_properties)

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


def parse_cif_atoms(cif: Any) -> tuple[Any, Any]:
    if not isinstance(cif, str) or not cif.strip():
        raise ValueError("candidate must include a CIF string")

    try:
        from pymatgen.core import Structure
        from pymatgen.io.ase import AseAtomsAdaptor
    except (ImportError, ModuleNotFoundError):
        raise

    try:
        structure = Structure.from_str(cif, fmt="cif")
        atoms = AseAtomsAdaptor.get_atoms(structure)
    except Exception as exc:
        raise ValueError(f"CIF parse failed: {exc}") from exc
    return structure, atoms


def inspect_structure(structure: Any, atoms: Any) -> dict[str, Any]:
    return {
        "reduced_formula": structure.composition.reduced_formula,
        "atom_count": len(structure),
        "volume": float(structure.volume),
        "elements": sorted({str(element) for element in structure.composition.elements}),
        "pbc": [bool(value) for value in atoms.pbc],
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


def predict_mace_mp_properties(atoms: Any, spec: dict[str, Any]) -> dict[str, float | str]:
    mace_config = spec.get("mace_mp") or {}
    model = str(mace_config.get("model", DEFAULT_MACE_MP_MODEL))
    device = str(mace_config.get("device", DEFAULT_MACE_MP_DEVICE))
    default_dtype = str(mace_config.get("default_dtype", DEFAULT_MACE_MP_DTYPE))
    calculator = load_mace_mp_calculator(model, device, default_dtype)

    atoms.calc = calculator
    energy = float(atoms.get_potential_energy())
    forces = atoms.get_forces()
    stress = atoms.get_stress()
    max_force = max(math.sqrt(float(sum(component * component for component in force))) for force in forces)
    stress_norm = math.sqrt(float(sum(component * component for component in stress)))
    values = {
        "mace_mp_energy_ev": energy,
        "mace_mp_energy_per_atom_ev": energy / len(atoms),
        "mace_mp_max_force_ev_per_angstrom": max_force,
        "mace_mp_stress_norm_ev_per_angstrom3": stress_norm,
    }
    non_finite = [name for name, value in values.items() if not math.isfinite(value)]
    if non_finite:
        raise ValueError(f"MACE-MP prediction returned non-finite values: {', '.join(non_finite)}")
    return {
        **values,
        "mace_mp_energy_unit": "eV",
        "mace_mp_energy_per_atom_unit": "eV/atom",
        "mace_mp_max_force_unit": "eV/Angstrom",
        "mace_mp_stress_norm_unit": "eV/Angstrom^3",
    }


@lru_cache(maxsize=None)
def load_mace_mp_calculator(model: str, device: str, default_dtype: str) -> Any:
    from mace.calculators import mace_mp

    return mace_mp(model=model, device=device, default_dtype=default_dtype)


def mace_mp_versions(spec: dict[str, Any]) -> dict[str, Any]:
    mace_config = spec.get("mace_mp") or {}
    return {
        "verifier_image": spec.get("verifier_image"),
        "mace_mp_backend": "native_mace_mp",
        "mace_mp_model": mace_config.get("model", DEFAULT_MACE_MP_MODEL),
        "mace-torch": package_version("mace-torch"),
        "torch": package_version("torch"),
        "ase": package_version("ase"),
        "pymatgen": package_version("pymatgen"),
    }


def package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None
