"""Shared local xTB backend for direct-XYZ verifier scripts."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from rdkit import Chem

from verifiers.backends.rdkit_descriptors import score_constraint


HARTREE_TO_EV = 27.211386245988
GAP_PATTERN = re.compile(r"HOMO-LUMO\s+GAP\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+eV", re.IGNORECASE)
ENERGY_PATTERN = re.compile(r"TOTAL\s+ENERGY\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Eh", re.IGNORECASE)
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


class XTBTimeoutError(XTBError):
    """Raised when an xTB run times out."""


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
            "2",
            "--chrg",
            str(backend.get("charge", 0)),
            "--uhf",
            str(backend.get("uhf", 0)),
        ]
        if mode == "optimize":
            command.append("--opt")
        elif mode != "singlepoint":
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
    result = base_result(task_id, spec)
    property_name = spec.get("property_name")
    if property_name != constraint.get("property"):
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
            "domain_error"
            if domain_error.startswith(
                (
                    "disallowed",
                    "atom_count",
                    "heavy_atom_count",
                    "carbon_count",
                    "hetero_atom_count",
                    "heavy_element_diversity",
                    "formula",
                    "max_absolute",
                    "unknown",
                )
            )
            else "validity_error"
        )
        return error_result(result, failure_type, domain_error, properties=xyz_properties)

    xtb_runner = runner or XTBRunner(str((spec.get("backend") or {}).get("executable", "xtb")))
    timeout = float(spec.get("timeout_seconds", 60.0))

    with tempfile.TemporaryDirectory(prefix="xtb-property-") as temp_dir:
        xyz_path = Path(temp_dir) / "candidate.xyz"
        xyz_path.write_text(xyz)
        try:
            properties = run_property_calculation(property_name, xtb_runner, xyz_path, timeout, spec)
        except XTBEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc), properties=xyz_properties)
        except XTBTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc), properties=xyz_properties)
        except XTBToolError as exc:
            return error_result(result, "verifier_tool_error", str(exc), properties=xyz_properties)

    merged_properties = {**xyz_properties, **properties}
    constraint_score = {
        "property": constraint["property"],
        "type": constraint["type"],
        "score": score_constraint(merged_properties, constraint),
    }
    if "role" in constraint:
        constraint_score["role"] = constraint["role"]
    score = float(constraint_score["score"])
    result.update(
        {
            "status": "ok",
            "properties": merged_properties,
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


def run_property_calculation(
    property_name: str,
    runner: XTBRunnerProtocol,
    xyz_path: Path,
    timeout_seconds: float,
    spec: dict[str, Any],
) -> dict[str, float | str]:
    if property_name == "relaxation_energy":
        singlepoint = parse_xtb_output(runner.run("singlepoint", xyz_path, timeout_seconds, spec=spec).stdout)
        optimized = parse_xtb_output(runner.run("optimize", xyz_path, timeout_seconds, spec=spec).stdout, require_converged=True)
        relaxation = max(0.0, (singlepoint["total_energy_hartree"] - optimized["total_energy_hartree"]) * HARTREE_TO_EV)
        return {"relaxation_energy": relaxation, "relaxation_energy_unit": "eV"}

    optimized = parse_xtb_output(runner.run("optimize", xyz_path, timeout_seconds, spec=spec).stdout, require_converged=True)
    if property_name == "homo_lumo_gap":
        if "homo_lumo_gap" not in optimized:
            raise XTBToolError("xTB output missing HOMO-LUMO gap")
        return {"homo_lumo_gap": optimized["homo_lumo_gap"], "homo_lumo_gap_unit": "eV"}
    if property_name == "dipole_moment":
        if "dipole_moment" not in optimized:
            raise XTBToolError("xTB output missing dipole moment")
        return {"dipole_moment": optimized["dipole_moment"], "dipole_moment_unit": "debye"}
    raise XTBToolError(f"unsupported xTB property: {property_name}")


def parse_xtb_output(stdout: str, *, require_converged: bool = False) -> dict[str, float]:
    if require_converged and CONVERGED_PATTERN.search(stdout) is None:
        raise XTBToolError("xTB optimization did not converge")
    properties: dict[str, float] = {}
    if match := last_match(ENERGY_PATTERN, stdout):
        properties["total_energy_hartree"] = float(match.group(1))
    if match := last_match(GAP_PATTERN, stdout):
        properties["homo_lumo_gap"] = float(match.group(1))
    if match := DIPOLE_FULL_PATTERN.search(stdout):
        properties["dipole_moment"] = float(match.group(1))
    elif match := DIPOLE_PATTERN.search(stdout):
        properties["dipole_moment"] = float(match.group(4))
    return properties


def last_match(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    match: re.Match[str] | None = None
    for match in pattern.finditer(text):
        pass
    return match


def base_result(task_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "verifier_id": spec.get("verifier_id"),
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
        "versions": {
            "verifier_image": spec.get("verifier_image"),
            "xtb_backend": "local_xtb_cli",
            "rdkit": metadata.version("rdkit"),
        },
    }


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
