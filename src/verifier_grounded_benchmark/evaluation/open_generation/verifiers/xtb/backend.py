"""Shared local xTB backend for direct-XYZ verifier scripts."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from rdkit import Chem

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import base_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import error_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import verified_result
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.structure_identity import StructureIdentityError
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.structure_identity import validate_structure_identity


HARTREE_TO_EV = 27.211386245988
GAP_PATTERN = re.compile(r"HOMO-LUMO\s+GAP\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+eV", re.IGNORECASE)
ENERGY_PATTERN = re.compile(r"TOTAL\s+ENERGY\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Eh", re.IGNORECASE)
LUMO_PATTERN = re.compile(
    r"^\s*\d+\s+(?:\d+\.\d+\s+)?[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+\(LUMO\)",
    re.IGNORECASE | re.MULTILINE,
)
POLARIZABILITY_PATTERN = re.compile(
    r"Mol\.\s+(?:alpha|α)\(0\)\s*/au\s*:\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    re.IGNORECASE,
)
GSOLV_PATTERN = re.compile(r"->\s*Gsolv\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Eh", re.IGNORECASE)
ELECTROPHILICITY_PATTERN = re.compile(
    r"Global\s+electrophilicity\s+index\s+\(eV\):\s*([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    re.IGNORECASE,
)
IMAGINARY_FREQUENCY_PATTERN = re.compile(r"#\s*imaginary\s+freq\.\s+(\d+)", re.IGNORECASE)
ENTROPY_298_PATTERN = re.compile(
    r"^\s*TOT\s+[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
DIPOLE_PATTERN = re.compile(
    r"molecular\s+dipole:.*?tot\s+\(Debye\)\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    re.IGNORECASE | re.DOTALL,
)
DIPOLE_FULL_PATTERN = re.compile(
    r"molecular\s+dipole:.*?^\s*full:\s+"
    r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+"
    r"([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)
CONVERGED_PATTERN = re.compile(r"(GEOMETRY\s+OPTIMIZATION\s+CONVERGED|normal\s+termination\s+of\s+xtb)", re.IGNORECASE)


class XTBError(RuntimeError):
    """Base error for xTB backend failures."""


class XTBParseError(XTBError):
    """Raised when XYZ input cannot be parsed."""


class XTBEnvironmentError(XTBError):
    """Raised when the xTB executable is not available."""


class XTBToolError(XTBError):
    """Raised when xTB execution or output parsing fails."""


class XTBSpecError(XTBError):
    """Raised when an xTB verifier spec is internally inconsistent."""


class XTBTimeoutError(XTBError):
    """Raised when an xTB run times out."""


class XTBElectronicStateError(XTBError):
    """Raised when charge, spin, and electron count are incompatible."""


@dataclass(frozen=True)
class XYZAtom:
    symbol: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class XYZMolecule:
    comment: str
    atoms: list[XYZAtom]


@dataclass(frozen=True)
class XTBRunResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class ElectronicState:
    charge: int
    uhf: int
    electron_count: int


class XTBRunnerProtocol(Protocol):
    def run(self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict[str, Any]) -> XTBRunResult:
        ...


def parse_xyz(xyz: str) -> XYZMolecule:
    if not isinstance(xyz, str) or not xyz.strip():
        raise XTBParseError("candidate must include an XYZ string")
    lines = xyz.splitlines()
    if len(lines) < 3:
        raise XTBParseError("XYZ must include atom count, comment line, and atom lines")
    try:
        atom_count = int(lines[0].strip())
    except ValueError as exc:
        raise XTBParseError("XYZ first line must be an integer atom count") from exc
    atom_lines = lines[2:]
    if atom_count != len(atom_lines):
        raise XTBParseError(f"XYZ atom count {atom_count} does not match {len(atom_lines)} atom lines")

    atoms: list[XYZAtom] = []
    for index, line in enumerate(atom_lines, start=3):
        parts = line.split()
        if len(parts) != 4:
            raise XTBParseError(f"XYZ atom line {index} must contain element and three coordinates")
        symbol = parts[0]
        try:
            x, y, z = (float(value) for value in parts[1:])
        except ValueError as exc:
            raise XTBParseError(f"XYZ atom line {index} contains non-numeric coordinates") from exc
        if not all(math.isfinite(value) for value in (x, y, z)):
            raise XTBParseError(f"XYZ atom line {index} contains non-finite coordinates")
        atoms.append(XYZAtom(symbol=symbol, x=x, y=y, z=z))
    return XYZMolecule(comment=lines[1], atoms=atoms)


def inspect_xyz(molecule: XYZMolecule) -> dict[str, Any]:
    elements = sorted({atom.symbol for atom in molecule.atoms})
    heavy_atom_count = sum(1 for atom in molecule.atoms if atom.symbol != "H")
    counts = Counter(atom.symbol for atom in molecule.atoms)
    return {
        "atom_count": len(molecule.atoms),
        "heavy_atom_count": heavy_atom_count,
        "elements": elements,
        "formula": hill_formula(dict(counts)),
        "element_counts": dict(counts),
        "carbon_count": counts.get("C", 0),
        "hetero_atom_count": sum(count for element, count in counts.items() if element not in {"H", "C"}),
        "heavy_element_diversity": len({element for element in counts if element != "H"}),
        "max_absolute_coordinate": max(abs(value) for atom in molecule.atoms for value in (atom.x, atom.y, atom.z)),
    }


def hill_formula(counts: dict[str, int]) -> str:
    ordered_elements: list[str] = []
    if "C" in counts:
        ordered_elements.append("C")
    if "H" in counts:
        ordered_elements.append("H")
    ordered_elements.extend(sorted(element for element in counts if element not in {"C", "H"}))
    return "".join(f"{element}{'' if counts[element] == 1 else counts[element]}" for element in ordered_elements)


def check_domain(molecule: XYZMolecule, properties: dict[str, Any], domain: dict[str, Any]) -> str | None:
    table = Chem.GetPeriodicTable()
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
    if "formula" in domain and properties["formula"] != domain["formula"]:
        return f"formula must be {domain['formula']}"
    for element, expected in domain.get("element_count_exact", {}).items():
        if properties["element_counts"].get(element, 0) != int(expected):
            return f"{element} count must be {expected}"
    for element, maximum in domain.get("element_count_max", {}).items():
        if properties["element_counts"].get(element, 0) > int(maximum):
            return f"{element} count exceeds maximum {maximum}"
    if "carbon_count_min" in domain and properties["carbon_count"] < int(domain["carbon_count_min"]):
        return f"carbon_count below minimum {domain['carbon_count_min']}"
    if "hetero_atom_count_min" in domain and properties["hetero_atom_count"] < int(domain["hetero_atom_count_min"]):
        return f"hetero_atom_count below minimum {domain['hetero_atom_count_min']}"
    if "heavy_element_diversity_min" in domain and properties["heavy_element_diversity"] < int(domain["heavy_element_diversity_min"]):
        return f"heavy_element_diversity below minimum {domain['heavy_element_diversity_min']}"
    if properties["formula"] in set(domain.get("formula_denylist", [])):
        return f"formula is denied: {properties['formula']}"
    max_coordinate = domain.get("max_absolute_coordinate")
    if max_coordinate is not None and properties["max_absolute_coordinate"] > float(max_coordinate):
        return f"max_absolute_coordinate exceeds {max_coordinate}"

    distances = pairwise_distances(molecule)
    minimum_distance = float(domain.get("min_interatomic_distance", 0.0))
    for _, _, distance in distances:
        if distance < minimum_distance:
            return f"interatomic distance {distance:.3f} below minimum {minimum_distance}"

    for atom in molecule.atoms:
        try:
            table.GetAtomicNumber(atom.symbol)
        except RuntimeError:
            return f"unknown element: {atom.symbol}"

    if int(domain.get("inferred_components", 1)) == 1 and component_count(molecule) != 1:
        return "disconnected geometry is not accepted"
    return None


def parse_xyz_charge(comment: str) -> int:
    match = re.fullmatch(r"charge=([+-]?\d+)", comment)
    if match is None:
        raise XTBParseError("XYZ comment must have exact form charge=<integer>")
    return int(match.group(1))


def resolve_electronic_state(
    molecule: XYZMolecule,
    spec: dict[str, Any],
) -> ElectronicState:
    backend = spec.get("backend") or {}
    charge_source = backend.get("charge_source", "fixed")
    if charge_source == "xyz_comment":
        charge = parse_xyz_charge(molecule.comment)
    elif charge_source == "fixed":
        charge = int(backend.get("charge", 0))
    else:
        raise XTBElectronicStateError(f"unsupported charge source: {charge_source}")
    uhf = int(backend.get("uhf", 0))
    if uhf < 0:
        raise XTBElectronicStateError("UHF must be non-negative")

    table = Chem.GetPeriodicTable()
    electron_count = sum(table.GetAtomicNumber(atom.symbol) for atom in molecule.atoms) - charge
    if electron_count <= 0:
        raise XTBElectronicStateError("electron count must be positive")
    if backend.get("validate_electron_parity") and (electron_count - uhf) % 2 != 0:
        raise XTBElectronicStateError(
            f"electron count {electron_count} is incompatible with UHF {uhf}"
        )
    return ElectronicState(charge=charge, uhf=uhf, electron_count=electron_count)


def pairwise_distances(molecule: XYZMolecule) -> list[tuple[int, int, float]]:
    distances: list[tuple[int, int, float]] = []
    atoms = molecule.atoms
    for i, first in enumerate(atoms):
        for j in range(i + 1, len(atoms)):
            second = atoms[j]
            distance = math.dist((first.x, first.y, first.z), (second.x, second.y, second.z))
            distances.append((i, j, distance))
    return distances


def component_count(molecule: XYZMolecule) -> int:
    if not molecule.atoms:
        return 0
    table = Chem.GetPeriodicTable()
    graph: list[set[int]] = [set() for _ in molecule.atoms]
    for i, j, distance in pairwise_distances(molecule):
        first = molecule.atoms[i]
        second = molecule.atoms[j]
        radius_sum = table.GetRcovalent(first.symbol) + table.GetRcovalent(second.symbol)
        if radius_sum > 0 and distance <= radius_sum * 1.25:
            graph[i].add(j)
            graph[j].add(i)

    seen: set[int] = set()
    components = 0
    for start in range(len(molecule.atoms)):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            node = stack.pop()
            for neighbor in graph[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
    return components


class XTBRunner:
    def __init__(self, executable: str = "xtb") -> None:
        self.executable = executable

    def run(self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict[str, Any]) -> XTBRunResult:
        executable = shutil.which(self.executable)
        if executable is None:
            raise XTBEnvironmentError(f"xTB executable not found: {self.executable}")
        command = self.command(mode, xyz_path, spec=spec, executable=executable)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                cwd=str(xyz_path.parent),
            )
        except subprocess.TimeoutExpired as exc:
            raise XTBTimeoutError(f"xTB {mode} run timed out after {timeout_seconds} seconds") from exc
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or f"xTB {mode} exited {completed.returncode}"
            raise XTBToolError(message)
        return XTBRunResult(stdout=completed.stdout, stderr=completed.stderr, returncode=completed.returncode)

    def command(self, mode: str, xyz_path: Path, *, spec: dict[str, Any], executable: str) -> list[str]:
        backend = spec.get("backend") or {}
        command = [
            executable,
            str(xyz_path),
            "--gfn",
            str(gfn_number(backend.get("method"))),
            "--chrg",
            str(backend.get("charge", 0)),
            "--uhf",
            str(backend.get("uhf", 0)),
        ]
        if solvent := backend.get("solvent"):
            solvent_model = str(backend.get("solvent_model") or backend.get("model") or "alpb").lower()
            if solvent_model not in {"alpb", "gbsa"}:
                raise XTBToolError(f"unsupported xTB solvent model: {solvent_model}")
            command.extend([f"--{solvent_model}", str(solvent)])

        if mode == "optimize":
            command.append("--opt")
        elif mode == "singlepoint":
            pass
        elif mode in {"property", "hessian"}:
            property_command = backend.get("property_command")
            if not isinstance(property_command, str) or not property_command:
                raise XTBToolError(f"xTB {mode} run requires property_command")
            command.append(property_command)
        else:
            raise XTBToolError(f"unsupported xTB run mode: {mode}")
        return command


def evaluate_xtb_property_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
    *,
    runner: XTBRunnerProtocol | None = None,
) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    result = base_result(task_id, spec.get("verifier_id"), xtb_versions(spec))
    property_name = spec.get("property_name")
    allowed_properties = {property_name, *(spec.get("additional_property_names") or [])}
    if constraint.get("property") not in allowed_properties:
        return error_result(
            result,
            "verifier_spec_error",
            f"verifier property {property_name!r} does not match constraint property {constraint.get('property')!r}",
        )

    xyz = candidate.get("xyz")
    if not isinstance(xyz, str) or not xyz.strip():
        return error_result(result, "parse_error", "candidate must include an XYZ string")

    try:
        molecule = parse_xyz(xyz)
    except XTBParseError as exc:
        return error_result(result, "parse_error", str(exc))

    xyz_properties = inspect_xyz(molecule)
    domain = {**(spec.get("domain") or {}), **(task.get("structural_domain") or {})}
    domain_error = check_domain(molecule, xyz_properties, domain)
    if domain_error:
        failure_type = (
            "validity_error"
            if domain_error.startswith(("interatomic distance", "disconnected"))
            else "domain_error"
        )
        return error_result(result, failure_type, domain_error, properties=xyz_properties)

    try:
        electronic_state = resolve_electronic_state(molecule, spec)
    except XTBParseError as exc:
        return error_result(result, "parse_error", str(exc), properties=xyz_properties)
    except XTBElectronicStateError as exc:
        return error_result(result, "domain_error", str(exc), properties=xyz_properties)

    xyz_properties.update(
        {
            "charge": electronic_state.charge,
            "uhf": electronic_state.uhf,
            "electron_count": electronic_state.electron_count,
        }
    )
    resolved_spec = deepcopy(spec)
    resolved_spec["backend"] = {
        **(resolved_spec.get("backend") or {}),
        "charge": electronic_state.charge,
        "uhf": electronic_state.uhf,
    }

    identity_config = task.get("structure_identity") or {}
    identity_properties: dict[str, Any] = {}
    if identity_config:
        try:
            identity_properties = validate_structure_identity(
                molecule,
                reference_smiles=str(identity_config["reference_smiles"]),
                charge=electronic_state.charge,
                require_stereochemistry=bool(
                    identity_config.get("require_stereochemistry", False)
                ),
            )
        except (KeyError, StructureIdentityError) as exc:
            return error_result(
                result,
                "domain_error",
                str(exc),
                properties=xyz_properties,
            )

    xtb_runner = runner or XTBRunner(str((spec.get("backend") or {}).get("executable", "xtb")))
    timeout = float(spec.get("timeout_seconds", 60.0))

    with tempfile.TemporaryDirectory(prefix="xtb-property-") as temp_dir:
        xyz_path = Path(temp_dir) / "candidate.xyz"
        xyz_path.write_text(xyz)
        try:
            properties = run_property_calculation(
                property_name,
                xtb_runner,
                xyz_path,
                timeout,
                resolved_spec,
            )
        except XTBEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc), properties=xyz_properties)
        except XTBSpecError as exc:
            return error_result(result, "verifier_spec_error", str(exc), properties=xyz_properties)
        except XTBTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc), properties=xyz_properties)
        except XTBToolError as exc:
            return error_result(result, "verifier_tool_error", str(exc), properties=xyz_properties)

        if identity_config.get("recheck_after_optimization"):
            optimized_path = optimized_geometry_path(xyz_path)
            try:
                optimized_molecule = parse_xyz(optimized_path.read_text())
                post_identity = validate_structure_identity(
                    optimized_molecule,
                    reference_smiles=str(identity_config["reference_smiles"]),
                    charge=electronic_state.charge,
                    require_stereochemistry=bool(
                        identity_config.get("require_stereochemistry", False)
                    ),
                )
            except (OSError, XTBParseError) as exc:
                return error_result(
                    result,
                    "verifier_tool_error",
                    f"could not read optimized geometry: {exc}",
                    properties={**xyz_properties, **properties},
                )
            except StructureIdentityError as exc:
                return error_result(
                    result,
                    "domain_error",
                    f"optimized structure {exc}",
                    properties={**xyz_properties, **properties},
                )
            identity_properties.update(
                {
                    "post_optimization_graph_match": post_identity["graph_match"],
                    "post_optimization_stereochemistry_match": post_identity[
                        "stereochemistry_match"
                    ],
                }
            )

    merged_properties = {**xyz_properties, **identity_properties, **properties}
    return verified_result(result, merged_properties, canonical_candidate={"xyz": xyz})


def run_property_calculation(
    property_name: str,
    runner: XTBRunnerProtocol,
    xyz_path: Path,
    timeout_seconds: float,
    spec: dict[str, Any],
) -> dict[str, float | str]:
    if property_name == "total_energy":
        calculation_mode = (spec.get("backend") or {}).get("calculation_mode")
        if calculation_mode == "submitted_singlepoint":
            parsed = parse_xtb_output(
                runner.run("singlepoint", xyz_path, timeout_seconds, spec=spec).stdout
            )
        elif calculation_mode == "optimized":
            parsed = parse_xtb_output(
                runner.run("optimize", xyz_path, timeout_seconds, spec=spec).stdout,
                require_converged=True,
            )
        else:
            raise XTBSpecError(
                f"unsupported total_energy calculation_mode: {calculation_mode}"
            )
        if "total_energy_hartree" not in parsed:
            raise XTBToolError("xTB output missing total energy")
        return {
            "total_energy": parsed["total_energy_hartree"],
            "total_energy_unit": "hartree",
        }
    if property_name == "relaxation_energy":
        singlepoint = parse_xtb_output(runner.run("singlepoint", xyz_path, timeout_seconds, spec=spec).stdout)
        optimized = parse_xtb_output(runner.run("optimize", xyz_path, timeout_seconds, spec=spec).stdout, require_converged=True)
        relaxation = max(0.0, (singlepoint["total_energy_hartree"] - optimized["total_energy_hartree"]) * HARTREE_TO_EV)
        return {"relaxation_energy": relaxation, "relaxation_energy_unit": "eV"}
    if property_name == "entropy_298_per_heavy_atom":
        hessian_spec = ensure_property_command(spec, "--ohess")
        parsed = parse_xtb_output(runner.run("hessian", xyz_path, timeout_seconds, spec=hessian_spec).stdout, require_converged=True)
        required = {"imaginary_frequency_count", "entropy_298"}
        if missing := sorted(required - set(parsed)):
            raise XTBToolError(f"xTB output missing hessian properties: {', '.join(missing)}")
        heavy_atom_count = count_heavy_atoms_from_xyz(xyz_path)
        entropy_298 = parsed["entropy_298"]
        return {
            "imaginary_frequency_count": parsed["imaginary_frequency_count"],
            "entropy_298": entropy_298,
            "entropy_298_unit": "J mol-1 K-1",
            "entropy_298_per_heavy_atom": entropy_298 / heavy_atom_count,
            "entropy_298_per_heavy_atom_unit": "J mol-1 K-1 per heavy atom",
        }

    optimized = parse_xtb_output(runner.run("optimize", xyz_path, timeout_seconds, spec=spec).stdout, require_converged=True)
    if property_name == "homo_lumo_gap":
        if "homo_lumo_gap" not in optimized:
            raise XTBToolError("xTB output missing HOMO-LUMO gap")
        return {"homo_lumo_gap": optimized["homo_lumo_gap"], "homo_lumo_gap_unit": "eV"}
    if property_name == "dipole_moment":
        if "dipole_moment" not in optimized:
            raise XTBToolError("xTB output missing dipole moment")
        return {"dipole_moment": optimized["dipole_moment"], "dipole_moment_unit": "debye"}
    if property_name == "lumo_energy":
        if "lumo_energy" not in optimized:
            raise XTBToolError("xTB output missing LUMO energy")
        return {"lumo_energy": optimized["lumo_energy"], "lumo_energy_unit": "eV"}
    if property_name == "polarizability_per_heavy_atom":
        if "molecular_polarizability" not in optimized:
            raise XTBToolError("xTB output missing molecular polarizability")
        heavy_atom_count = count_heavy_atoms_from_xyz(xyz_path)
        polarizability = optimized["molecular_polarizability"]
        return {
            "molecular_polarizability": polarizability,
            "molecular_polarizability_unit": "atomic_units",
            "polarizability_per_heavy_atom": polarizability / heavy_atom_count,
            "polarizability_per_heavy_atom_unit": "atomic_units_per_heavy_atom",
        }
    if property_name == "alpb_water_hexane_selectivity":
        optimized_path = optimized_geometry_path(xyz_path)
        solvent_runs = (spec.get("backend") or {}).get("solvent_runs") or [
            {"model": "alpb", "solvent": "water"},
            {"model": "alpb", "solvent": "hexane"},
        ]
        gsolv_by_solvent: dict[str, float] = {}
        for solvent_run in solvent_runs:
            solvent = str(solvent_run["solvent"])
            solvent_spec = merge_backend(
                spec,
                {
                    "solvent_model": solvent_run.get("model", "alpb"),
                    "solvent": solvent,
                },
            )
            parsed = parse_xtb_output(runner.run("singlepoint", optimized_path, timeout_seconds, spec=solvent_spec).stdout)
            if "gsolv_hartree" not in parsed:
                raise XTBToolError(f"xTB output missing Gsolv for solvent {solvent}")
            gsolv_by_solvent[solvent] = parsed["gsolv_hartree"] * HARTREE_TO_EV
        if "water" not in gsolv_by_solvent or "hexane" not in gsolv_by_solvent:
            raise XTBToolError("ALPB selectivity requires water and hexane solvent runs")
        return {
            "gsolv_water_eV": gsolv_by_solvent["water"],
            "gsolv_hexane_eV": gsolv_by_solvent["hexane"],
            "alpb_water_hexane_selectivity": gsolv_by_solvent["hexane"] - gsolv_by_solvent["water"],
            "alpb_water_hexane_selectivity_unit": "eV",
        }
    if property_name == "global_electrophilicity":
        property_spec = ensure_property_command(spec, "--vomega")
        parsed = parse_xtb_output(runner.run("property", optimized_geometry_path(xyz_path), timeout_seconds, spec=property_spec).stdout)
        if "global_electrophilicity" not in parsed:
            raise XTBToolError("xTB output missing global electrophilicity")
        return {
            "global_electrophilicity": parsed["global_electrophilicity"],
            "global_electrophilicity_unit": "eV",
        }
    if property_name == "max_f_plus_on_carbon":
        property_spec = ensure_property_command(spec, "--vfukui")
        parsed = parse_xtb_output(runner.run("property", optimized_geometry_path(xyz_path), timeout_seconds, spec=property_spec).stdout)
        required = {"max_f_plus_on_carbon", "f_plus_contrast"}
        if missing := sorted(required - set(parsed)):
            raise XTBToolError(f"xTB output missing Fukui properties: {', '.join(missing)}")
        return {
            "max_f_plus_on_carbon": parsed["max_f_plus_on_carbon"],
            "f_plus_contrast": parsed["f_plus_contrast"],
            "max_f_plus_atom_index": parsed["max_f_plus_atom_index"],
            "max_f_plus_atom_symbol": parsed["max_f_plus_atom_symbol"],
        }
    raise XTBToolError(f"unsupported xTB property: {property_name}")


def parse_xtb_output(stdout: str, *, require_converged: bool = False) -> dict[str, float]:
    if require_converged and CONVERGED_PATTERN.search(stdout) is None:
        raise XTBToolError("xTB optimization did not converge")
    properties: dict[str, float] = {}
    if match := last_match(ENERGY_PATTERN, stdout):
        properties["total_energy_hartree"] = float(match.group(1))
    if match := last_match(GAP_PATTERN, stdout):
        properties["homo_lumo_gap"] = float(match.group(1))
    if match := last_match(LUMO_PATTERN, stdout):
        properties["lumo_energy"] = float(match.group(1))
    if match := last_match(POLARIZABILITY_PATTERN, stdout):
        properties["molecular_polarizability"] = float(match.group(1))
    if match := last_match(GSOLV_PATTERN, stdout):
        properties["gsolv_hartree"] = float(match.group(1))
    if match := last_match(ELECTROPHILICITY_PATTERN, stdout):
        properties["global_electrophilicity"] = float(match.group(1))
    if match := DIPOLE_FULL_PATTERN.search(stdout):
        properties["dipole_moment"] = float(match.group(1))
    elif match := DIPOLE_PATTERN.search(stdout):
        properties["dipole_moment"] = float(match.group(4))
    properties.update(parse_fukui_properties(stdout))
    if match := last_match(IMAGINARY_FREQUENCY_PATTERN, stdout):
        properties["imaginary_frequency_count"] = int(match.group(1))
    if match := last_match(ENTROPY_298_PATTERN, stdout):
        properties["entropy_298"] = float(match.group(1))
    return properties


def parse_fukui_properties(stdout: str) -> dict[str, float | int | str]:
    table_match = re.search(r"Fukui functions:\s*\n\s*#\s+f\(\+\)\s+f\(-\)\s+f\(0\)\s*\n(?P<body>.*?)(?:\n\s*-{5,}|\n\s*\|)", stdout, re.IGNORECASE | re.DOTALL)
    if table_match is None:
        return {}
    values: list[tuple[int, str, float]] = []
    for line in table_match.group("body").splitlines():
        match = re.match(r"\s*(\d+)([A-Z][a-z]?)\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+", line)
        if match:
            values.append((int(match.group(1)), match.group(2), float(match.group(3))))
    if not values:
        return {}
    carbon_values = [(index, symbol, value) for index, symbol, value in values if symbol == "C"]
    if not carbon_values:
        return {}
    carbon_index, carbon_symbol, max_carbon = max(carbon_values, key=lambda item: item[2])
    non_carbon_competitors = [value for _, symbol, value in values if symbol != "C"]
    second_largest = max(non_carbon_competitors, default=max_carbon)
    return {
        "max_f_plus_on_carbon": max_carbon,
        "f_plus_contrast": max_carbon - second_largest,
        "max_f_plus_atom_index": carbon_index,
        "max_f_plus_atom_symbol": carbon_symbol,
    }


def gfn_number(method: Any) -> int:
    method_text = str(method or "GFN2-xTB").lower()
    if "gfn1" in method_text:
        return 1
    if "gfn0" in method_text:
        return 0
    return 2


def merge_backend(spec: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(spec)
    merged["backend"] = {**(spec.get("backend") or {}), **updates}
    return merged


def ensure_property_command(spec: dict[str, Any], fallback: str) -> dict[str, Any]:
    backend = spec.get("backend") or {}
    if backend.get("property_command"):
        return spec
    return merge_backend(spec, {"property_command": fallback})


def optimized_geometry_path(xyz_path: Path) -> Path:
    optimized = xyz_path.parent / "xtbopt.xyz"
    return optimized if optimized.exists() else xyz_path


def count_heavy_atoms_from_xyz(xyz_path: Path) -> int:
    molecule = parse_xyz(xyz_path.read_text())
    heavy_atom_count = sum(1 for atom in molecule.atoms if atom.symbol != "H")
    if heavy_atom_count <= 0:
        raise XTBToolError("heavy_atom_count must be positive")
    return heavy_atom_count


def last_match(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    match: re.Match[str] | None = None
    for match in pattern.finditer(text):
        pass
    return match


def xtb_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "xtb_backend": "local_xtb_cli",
        "rdkit": metadata.version("rdkit"),
    }
