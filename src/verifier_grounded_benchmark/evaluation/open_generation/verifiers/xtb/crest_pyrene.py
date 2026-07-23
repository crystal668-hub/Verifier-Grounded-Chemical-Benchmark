"""Frozen CREST/xTB protocol for pyrene trisubstitution isomers."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from rdkit import Chem
from rdkit.Chem import AllChem, rdDetermineBonds, rdFMCS, rdMolDescriptors

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common.result import (
    base_result,
    error_result,
    verified_result,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.backend import (
    XTBEnvironmentError,
    XTBRunner,
    XTBRunnerProtocol,
    XTBTimeoutError,
    XTBToolError,
    parse_xtb_output,
)


class PyreneIdentityError(ValueError):
    pass


class CrestEnvironmentError(RuntimeError):
    pass


class CrestTimeoutError(RuntimeError):
    pass


class CrestToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class CrestSearchResult:
    conformers: tuple[str, ...]
    relative_energies: tuple[float, ...]
    version: str


class CrestRunnerProtocol(Protocol):
    def search(
        self,
        initial_xyz: str,
        workdir: Path,
        timeout_seconds: float,
        *,
        spec: dict[str, Any],
    ) -> CrestSearchResult: ...


class CrestRunner:
    def __init__(self, executable: str = "crest") -> None:
        self.executable = executable

    def search(
        self,
        initial_xyz: str,
        workdir: Path,
        timeout_seconds: float,
        *,
        spec: dict[str, Any],
    ) -> CrestSearchResult:
        executable = shutil.which(self.executable)
        if executable is None:
            raise CrestEnvironmentError(f"CREST executable not found: {self.executable}")
        input_path = workdir / "initial.xyz"
        input_path.write_text(initial_xyz, encoding="utf-8")
        backend = spec.get("backend") or {}
        command = [
            executable,
            str(input_path),
            "-gfn2",
            "-chrg",
            str(backend.get("charge", 0)),
            "-uhf",
            str(backend.get("uhf", 0)),
            "-T",
            str(backend.get("threads", 1)),
            str(backend.get("search_level", "-quick")),
        ]
        if xtb_executable := backend.get("xtb_executable"):
            command.extend(["-xnam", str(xtb_executable)])
        try:
            completed = subprocess.run(
                command,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CrestTimeoutError(
                f"CREST search timed out after {timeout_seconds:g} seconds"
            ) from exc
        if completed.returncode != 0:
            message = "\n".join(
                part
                for part in (completed.stdout.strip(), completed.stderr.strip())
                if part
            )
            raise CrestToolError(message or f"CREST exited {completed.returncode}")
        ensemble_path = workdir / "crest_conformers.xyz"
        if not ensemble_path.exists():
            raise CrestToolError("CREST produced no conformer ensemble")
        conformers, energies = parse_xyz_ensemble(
            ensemble_path.read_text(encoding="utf-8")
        )
        if not conformers:
            raise CrestToolError("CREST conformer ensemble was empty")
        minimum_energy = min(energies)
        relative_energies = [energy - minimum_energy for energy in energies]
        return CrestSearchResult(
            tuple(conformers),
            tuple(relative_energies),
            executable_version(executable, "crest"),
        )


def evaluate_pyrene_energy_constraint(
    candidate: dict[str, Any],
    task: dict[str, Any],
    constraint: dict[str, Any],
    spec: dict[str, Any],
    *,
    crest_runner: CrestRunnerProtocol | None = None,
    xtb_runner: XTBRunnerProtocol | None = None,
) -> dict[str, Any]:
    result = base_result(
        str(task.get("task_id")), spec.get("verifier_id"), protocol_versions(spec)
    )
    if constraint.get("property") != spec.get("property_name"):
        return error_result(
            result,
            "verifier_spec_error",
            "pyrene CREST verifier property does not match constraint",
        )
    smiles = candidate.get("smiles")
    if not isinstance(smiles, str) or not smiles:
        return error_result(result, "parse_error", "candidate must include a SMILES string")
    if "." in smiles:
        return error_result(result, "validity_error", "multi-component SMILES are not accepted")
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        return error_result(result, "parse_error", "RDKit returned no molecule")

    identity = spec.get("identity") or {}
    try:
        identity_properties = validate_pyrene_identity(mol, identity)
    except PyreneIdentityError as exc:
        return error_result(result, "identity_error", str(exc))
    canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
    try:
        initial_xyz = embed_initial_xyz(mol, spec.get("backend") or {})
        validate_xyz_identity(initial_xyz, mol)
    except PyreneIdentityError as exc:
        return error_result(
            result,
            "identity_error",
            f"initial geometry identity mismatch: {exc}",
            properties=identity_properties,
        )
    except Exception as exc:
        return error_result(
            result,
            "verifier_tool_error",
            f"initial geometry generation failed: {exc}",
            properties=identity_properties,
        )

    backend = spec.get("backend") or {}
    crest = crest_runner or CrestRunner(str(backend.get("crest_executable", "crest")))
    xtb = xtb_runner or XTBRunner(str(backend.get("xtb_executable", "xtb")))
    with tempfile.TemporaryDirectory(prefix="crest-pyrene-") as temp_dir:
        workdir = Path(temp_dir)
        try:
            search = crest.search(
                initial_xyz,
                workdir,
                float(backend.get("crest_timeout_seconds", 1800)),
                spec=spec,
            )
        except CrestEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc))
        except CrestTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc))
        except CrestToolError as exc:
            return error_result(result, "verifier_tool_error", str(exc))

        selected_index = min(
            range(len(search.conformers)),
            key=lambda index: (search.relative_energies[index], index),
        )
        selected_xyz = search.conformers[selected_index]
        try:
            validate_xyz_identity(selected_xyz, mol)
        except PyreneIdentityError as exc:
            return error_result(
                result,
                "structure_identity_error",
                f"post-CREST identity mismatch: {exc}",
                properties={**identity_properties, "pre_search_identity_match": True},
            )

        selected_path = workdir / "selected.xyz"
        selected_path.write_text(selected_xyz, encoding="utf-8")
        try:
            run = xtb.run(
                "singlepoint",
                selected_path,
                float(backend.get("xtb_timeout_seconds", 300)),
                spec=spec,
            )
            parsed = parse_xtb_output(run.stdout)
            total_energy = parsed["total_energy_hartree"]
        except XTBEnvironmentError as exc:
            return error_result(result, "verifier_environment_error", str(exc))
        except XTBTimeoutError as exc:
            return error_result(result, "verifier_timeout", str(exc))
        except (XTBToolError, KeyError) as exc:
            return error_result(
                result, "verifier_tool_error", f"xTB single-point failed: {exc}"
            )

    properties = {
        **identity_properties,
        "crest_version": search.version,
        "xtb_version": str(backend.get("xtb_version", "6.7.1")),
        "crest_conformer_count": len(search.conformers),
        "crest_min_relative_energy": search.relative_energies[selected_index],
        "total_energy": total_energy,
        "pre_search_identity_match": True,
        "post_crest_identity_match": True,
    }
    return verified_result(
        result, properties, canonical_candidate={"smiles": canonical_smiles}
    )


def validate_pyrene_identity(
    mol: Chem.Mol, identity: dict[str, Any]
) -> dict[str, Any]:
    reference_smiles = str(identity.get("reference_smiles"))
    reference = Chem.MolFromSmiles(reference_smiles, sanitize=True)
    if reference is None:
        raise PyreneIdentityError("pyrene reference SMILES is invalid")
    expected_formula = str(identity.get("formula", "C17H10N2O4"))
    formula = rdMolDescriptors.CalcMolFormula(mol)
    if formula != expected_formula:
        raise PyreneIdentityError(f"formula must be {expected_formula}")
    if Chem.GetFormalCharge(mol) != 0:
        raise PyreneIdentityError("candidate must have formal charge 0")
    if {atom.GetSymbol() for atom in mol.GetAtoms()} - {"C", "H", "N", "O"}:
        raise PyreneIdentityError("candidate contains disallowed elements")

    valid: list[tuple[tuple[int, ...], list[int], dict[str, int]]] = []
    for mapping in mol.GetSubstructMatches(reference, uniquify=False, maxMatches=10000):
        if not scaffold_graph_matches(reference, mol, mapping):
            continue
        classified = classify_graph_delta(reference, mol, mapping)
        if classified is not None:
            sites, counts = classified
            valid.append((mapping, sites, counts))
    if not valid:
        raise PyreneIdentityError(
            "candidate is not exactly pyrene with one nitro, amino, and carboxyl substituent"
        )
    mapping, sites, counts = min(valid, key=lambda item: (item[1], item[0]))
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "formula": formula,
        "formal_charge": 0,
        "scaffold_match": True,
        "scaffold_atom_indices": list(mapping),
        "substitution_site_indices": sites,
        "substituent_counts": counts,
    }


def scaffold_graph_matches(
    reference: Chem.Mol, candidate: Chem.Mol, mapping: tuple[int, ...]
) -> bool:
    mapped = set(mapping)
    internal_bonds = [
        bond
        for bond in candidate.GetBonds()
        if bond.GetBeginAtomIdx() in mapped and bond.GetEndAtomIdx() in mapped
    ]
    if len(internal_bonds) != reference.GetNumBonds():
        return False
    for bond in reference.GetBonds():
        candidate_bond = candidate.GetBondBetweenAtoms(
            mapping[bond.GetBeginAtomIdx()], mapping[bond.GetEndAtomIdx()]
        )
        if candidate_bond is None or candidate_bond.GetBondType() != bond.GetBondType():
            return False
    return all(candidate.GetAtomWithIdx(index).GetSymbol() == "C" for index in mapping)


def classify_graph_delta(
    reference: Chem.Mol, candidate: Chem.Mol, mapping: tuple[int, ...]
) -> tuple[list[int], dict[str, int]] | None:
    scaffold = set(mapping)
    outside = set(range(candidate.GetNumAtoms())) - scaffold
    if len(outside) != 7:
        return None
    components = outside_components(candidate, outside)
    counts = {"nitro": 0, "amino": 0, "carboxyl": 0}
    sites: list[int] = []
    inverse = {candidate_index: reference_index for reference_index, candidate_index in enumerate(mapping)}
    for component in components:
        attachment_bonds = [
            bond
            for bond in candidate.GetBonds()
            if (bond.GetBeginAtomIdx() in component) != (bond.GetEndAtomIdx() in component)
            and ({bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()} & component)
            and ({bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()} & scaffold)
        ]
        if len(attachment_bonds) != 1:
            return None
        bond = attachment_bonds[0]
        root = (
            bond.GetBeginAtomIdx()
            if bond.GetBeginAtomIdx() in component
            else bond.GetEndAtomIdx()
        )
        scaffold_atom = (
            bond.GetEndAtomIdx()
            if root == bond.GetBeginAtomIdx()
            else bond.GetBeginAtomIdx()
        )
        reference_index = inverse[scaffold_atom]
        if reference.GetAtomWithIdx(reference_index).GetTotalNumHs() < 1:
            return None
        kind = classify_substituent(candidate, component, root)
        if kind is None:
            return None
        counts[kind] += 1
        sites.append(reference_index)
    if counts != {"nitro": 1, "amino": 1, "carboxyl": 1}:
        return None
    if len(set(sites)) != 3:
        return None
    return sorted(sites), counts


def classify_substituent(
    mol: Chem.Mol, component: set[int], root: int
) -> str | None:
    atoms = [mol.GetAtomWithIdx(index) for index in component]
    symbols = sorted(atom.GetSymbol() for atom in atoms)
    charge = sum(atom.GetFormalCharge() for atom in atoms)
    if len(component) == 1 and symbols == ["N"]:
        atom = mol.GetAtomWithIdx(root)
        return "amino" if charge == 0 and atom.GetTotalNumHs() == 2 else None
    if symbols == ["N", "O", "O"] and mol.GetAtomWithIdx(root).GetSymbol() == "N":
        return "nitro" if charge == 0 and mol.GetAtomWithIdx(root).GetTotalNumHs() == 0 else None
    if symbols == ["C", "O", "O"] and mol.GetAtomWithIdx(root).GetSymbol() == "C":
        oxygen_atoms = [atom for atom in atoms if atom.GetSymbol() == "O"]
        oxygen_hydrogens = sum(atom.GetTotalNumHs() for atom in oxygen_atoms)
        bond_types = {
            mol.GetBondBetweenAtoms(root, atom.GetIdx()).GetBondType()
            for atom in oxygen_atoms
        }
        if charge == 0 and oxygen_hydrogens == 1 and bond_types == {
            Chem.BondType.SINGLE,
            Chem.BondType.DOUBLE,
        }:
            return "carboxyl"
    return None


def outside_components(mol: Chem.Mol, outside: set[int]) -> list[set[int]]:
    components: list[set[int]] = []
    unseen = set(outside)
    while unseen:
        start = unseen.pop()
        component = {start}
        stack = [start]
        while stack:
            atom_index = stack.pop()
            for neighbor in mol.GetAtomWithIdx(atom_index).GetNeighbors():
                index = neighbor.GetIdx()
                if index in unseen:
                    unseen.remove(index)
                    component.add(index)
                    stack.append(index)
        components.append(component)
    return components


def embed_initial_xyz(mol: Chem.Mol, backend: dict[str, Any]) -> str:
    molecule = Chem.AddHs(Chem.Mol(mol))
    params = AllChem.ETKDGv3()
    params.randomSeed = int(backend.get("random_seed", 61453))
    if AllChem.EmbedMolecule(molecule, params) < 0:
        raise CrestToolError("ETKDGv3 embedding failed")
    return Chem.MolToXYZBlock(molecule)


def validate_xyz_identity(xyz: str, expected: Chem.Mol) -> None:
    mol = Chem.MolFromXYZBlock(xyz)
    if mol is None:
        raise PyreneIdentityError("could not parse XYZ geometry")
    try:
        rdDetermineBonds.DetermineConnectivity(mol)
    except Exception as exc:
        raise PyreneIdentityError(f"could not reconstruct molecular graph: {exc}") from exc
    expected_with_hydrogens = Chem.AddHs(expected)
    mcs = rdFMCS.FindMCS(
        [expected_with_hydrogens, mol],
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareAny,
        timeout=10,
    )
    if (
        mcs.canceled
        or mcs.numAtoms != expected_with_hydrogens.GetNumAtoms()
        or mcs.numAtoms != mol.GetNumAtoms()
        or mcs.numBonds != expected_with_hydrogens.GetNumBonds()
        or mcs.numBonds != mol.GetNumBonds()
    ):
        raise PyreneIdentityError("reconstructed graph does not match candidate SMILES")


def parse_xyz_ensemble(text: str) -> tuple[list[str], list[float]]:
    lines = text.splitlines()
    conformers: list[str] = []
    energies: list[float] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        try:
            atom_count = int(lines[index].strip())
        except ValueError as exc:
            raise CrestToolError("CREST ensemble has invalid atom count") from exc
        block = lines[index : index + atom_count + 2]
        if len(block) != atom_count + 2:
            raise CrestToolError("CREST ensemble contains a truncated conformer")
        match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", block[1])
        energy = float(match.group(0)) if match else float(len(conformers))
        if not math.isfinite(energy):
            raise CrestToolError("CREST conformer energy is not finite")
        conformers.append("\n".join(block) + "\n")
        energies.append(energy)
        index += atom_count + 2
    return conformers, energies


def executable_version(executable: str, name: str) -> str:
    completed = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=False, timeout=30
    )
    match = re.search(r"(?:Version|version)\s+([0-9][^,\s]*)", completed.stdout + completed.stderr)
    return match.group(1) if match else name


def protocol_versions(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "verifier_image": spec.get("verifier_image"),
        "rdkit": metadata.version("rdkit"),
        "crest_backend": "crest_pyrene_gfn2_v1",
    }
