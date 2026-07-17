"""Native TorchANI ANI-2x property backend for direct-XYZ verifier scripts."""

from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache
from importlib import metadata
from io import StringIO
from typing import Any

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import base_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import error_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import verified_result


SUPPORTED_TORCHANI_PROPERTIES = {
    "torchani_total_energy_hartree",
    "torchani_energy_per_atom_hartree",
    "torchani_max_force_hartree_per_angstrom",
}
DEFAULT_TORCHANI_MODEL = "ANI2x"
DEFAULT_TORCHANI_DEVICE = "cpu"


def evaluate_torchani_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), torchani_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    constraint_property = constraint.get("property")
    if constraint_property not in allowed_properties:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint_property!r}",
        )
    if constraint_property not in SUPPORTED_TORCHANI_PROPERTIES:
        return error_result(result, "verifier_spec_error", f"unsupported TorchANI property: {constraint_property}")

    try:
        atoms = parse_xyz_atoms(candidate.get("xyz"))
    except ValueError as exc:
        return error_result(result, "parse_error", str(exc))
    except (ImportError, ModuleNotFoundError) as exc:
        return error_result(result, "verifier_environment_error", str(exc))

    input_properties = inspect_xyz_atoms(atoms)
    domain_error = check_domain(input_properties, spec.get("domain") or {})
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=input_properties)

    try:
        prediction = predict_torchani_properties(atoms, spec)
        properties = {**input_properties, **prediction}
    except (ImportError, ModuleNotFoundError) as exc:
        return error_result(result, "verifier_environment_error", str(exc), properties=input_properties)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", str(exc), properties=input_properties)

    return verified_result(result, properties, canonical_candidate={"xyz": candidate["xyz"]})


def parse_xyz_atoms(xyz: Any) -> Any:
    if not isinstance(xyz, str) or not xyz.strip():
        raise ValueError("candidate must include an XYZ string")

    try:
        from ase.io import read
    except (ImportError, ModuleNotFoundError):
        raise

    try:
        return read(StringIO(xyz), format="xyz")
    except Exception as exc:
        raise ValueError(f"XYZ parse failed: {exc}") from exc


def inspect_xyz_atoms(atoms: Any) -> dict[str, Any]:
    symbols = list(atoms.get_chemical_symbols())
    counts = Counter(symbols)
    pbc = [bool(value) for value in atoms.pbc]
    return {
        "atom_count": len(symbols),
        "heavy_atom_count": sum(1 for symbol in symbols if symbol != "H"),
        "elements": sorted(counts),
        "formula": hill_formula(dict(counts)),
        "pbc": pbc,
    }


def hill_formula(counts: dict[str, int]) -> str:
    ordered_elements: list[str] = []
    if "C" in counts:
        ordered_elements.append("C")
    if "H" in counts:
        ordered_elements.append("H")
    ordered_elements.extend(sorted(element for element in counts if element not in {"C", "H"}))
    return "".join(f"{element}{'' if counts[element] == 1 else counts[element]}" for element in ordered_elements)


def check_domain(properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    if any(properties.get("pbc") or []):
        return "periodic XYZ is not accepted"

    allowed_elements = domain.get("allowed_elements")
    if allowed_elements:
        disallowed = sorted(set(properties["elements"]) - set(allowed_elements))
        if disallowed:
            return f"disallowed elements: {', '.join(disallowed)}"

    if "atom_count" in domain:
        lower, upper = domain["atom_count"]
        if not int(lower) <= int(properties["atom_count"]) <= int(upper):
            return f"atom_count outside [{lower}, {upper}]"
    if "heavy_atom_count" in domain:
        lower, upper = domain["heavy_atom_count"]
        if not int(lower) <= int(properties["heavy_atom_count"]) <= int(upper):
            return f"heavy_atom_count outside [{lower}, {upper}]"
    return None


def predict_torchani_properties(atoms: Any, spec: dict[str, Any]) -> dict[str, float | str]:
    import torch

    torchani_config = spec.get("torchani") or {}
    model_name = str(torchani_config.get("model_name", DEFAULT_TORCHANI_MODEL))
    device = str(torchani_config.get("device", DEFAULT_TORCHANI_DEVICE))
    model = load_torchani_model(model_name, device)

    atomic_numbers = torch.tensor([atoms.get_atomic_numbers()], dtype=torch.long, device=device)
    coordinates = torch.tensor([atoms.get_positions()], dtype=torch.float32, device=device)
    coordinates.requires_grad_(True)

    output = model((atomic_numbers, coordinates))
    energy = output.energies
    forces = -torch.autograd.grad(energy.sum(), coordinates)[0]
    total_energy = float(energy.detach().cpu().reshape(-1)[0].item())
    energy_per_atom = total_energy / len(atoms)
    max_force = float(torch.linalg.norm(forces[0], dim=1).max().detach().cpu().item())

    values = {
        "torchani_total_energy_hartree": total_energy,
        "torchani_energy_per_atom_hartree": energy_per_atom,
        "torchani_max_force_hartree_per_angstrom": max_force,
    }
    non_finite = [name for name, value in values.items() if not math.isfinite(value)]
    if non_finite:
        raise ValueError(f"TorchANI prediction returned non-finite values: {', '.join(non_finite)}")
    return {
        **values,
        "torchani_total_energy_unit": "Hartree",
        "torchani_energy_per_atom_unit": "Hartree/atom",
        "torchani_max_force_unit": "Hartree/Angstrom",
    }


@lru_cache(maxsize=None)
def load_torchani_model(model_name: str, device: str) -> Any:
    if model_name != DEFAULT_TORCHANI_MODEL:
        raise ValueError(f"unsupported TorchANI model_name: {model_name}")

    import torchani

    return torchani.models.ANI2x(periodic_table_index=True).to(device)


def torchani_versions(spec: dict[str, Any]) -> dict[str, Any]:
    torchani_config = spec.get("torchani") or {}
    return {
        "verifier_image": spec.get("verifier_image"),
        "torchani_backend": "native_torchani",
        "torchani_model_name": torchani_config.get("model_name", DEFAULT_TORCHANI_MODEL),
        "torchani": package_version("torchani"),
        "torch": package_version("torch"),
        "ase": package_version("ase"),
    }


def package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None
