"""Native MatGL material property backend for verifier scripts."""

from __future__ import annotations

import contextlib
import io
from functools import lru_cache
from importlib import metadata
from numbers import Number
from typing import Any

from pymatgen.core import Structure

from verifiers.backends.rdkit_descriptors import score_constraint
from verifiers.result_schema import base_result
from verifiers.result_schema import error_result

DEFAULT_MATGL_MODEL = "MEGNet-Eform-MP-2018.6.1"


def evaluate_matgl_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), matgl_versions(spec))
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

    try:
        structure = Structure.from_str(cif, fmt="cif")
    except Exception as exc:
        return error_result(result, "parse_error", f"CIF parse failed: {exc}")

    structure_properties = inspect_structure(structure)
    domain_error = check_domain(structure_properties, spec.get("domain", {}))
    if domain_error:
        return error_result(result, "domain_error", domain_error, properties=structure_properties)

    try:
        with _suppress_output():
            model = load_matgl_model(spec)
            prediction = model.predict_structure(structure)
    except (ImportError, ModuleNotFoundError) as exc:
        return error_result(result, "verifier_environment_error", str(exc))
    except Exception as exc:
        return error_result(result, "verifier_tool_error", str(exc), properties=structure_properties)

    try:
        property_values = parse_prediction(property_name, prediction)
    except Exception as exc:
        return error_result(result, "verifier_tool_error", str(exc), properties=structure_properties)

    properties = {**structure_properties, **property_values}
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


def load_matgl_model(spec: dict[str, Any]) -> Any:
    matgl_config = spec.get("matgl") or {}
    model_name = matgl_config.get("model_name", DEFAULT_MATGL_MODEL)
    return _load_matgl_model_by_name(str(model_name))


@lru_cache(maxsize=None)
def _load_matgl_model_by_name(model_name: str) -> Any:
    import matgl

    return matgl.load_model(model_name)


def parse_prediction(property_name: str, prediction: Any) -> dict[str, float | str]:
    if property_name == "formation_energy":
        return {"formation_energy": float_value(prediction), "formation_energy_unit": "eV/atom"}
    if property_name == "bandgap":
        return {"bandgap": float_value(prediction), "bandgap_unit": "eV"}
    raise ValueError(f"unsupported MatGL property: {property_name}")


def float_value(value: Any) -> float:
    if isinstance(value, Number):
        return float(value)

    converted = value
    for method_name in ("detach", "cpu", "numpy"):
        method = getattr(converted, method_name, None)
        if callable(method):
            converted = method()

    if isinstance(converted, Number):
        return float(converted)

    size = getattr(converted, "size", None)
    if size is not None:
        size_value = int(size() if callable(size) else size)
        if size_value != 1:
            raise ValueError(f"MatGL prediction must contain exactly one element; got {size_value}")

    item = getattr(converted, "item", None)
    if callable(item):
        try:
            return float(item())
        except ValueError as exc:
            raise ValueError("MatGL prediction must contain exactly one element") from exc

    if isinstance(converted, (list, tuple)):
        if len(converted) != 1:
            raise ValueError(f"MatGL prediction must contain exactly one element; got {len(converted)}")
        return float_value(converted[0])

    raise ValueError(f"MatGL prediction is not a scalar: {type(value).__name__}")


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


def matgl_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "pymatgen": _package_version("pymatgen"),
        "matgl": _package_version("matgl"),
    }


def _package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


@contextlib.contextmanager
def _suppress_output() -> Any:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield
