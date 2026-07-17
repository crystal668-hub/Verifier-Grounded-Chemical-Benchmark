"""Molecular graph and stereochemistry checks for named xTB structures."""

from __future__ import annotations

from typing import Any

from rdkit import Chem
from rdkit.Chem import rdDetermineBonds, rdFMCS


class StructureIdentityError(ValueError):
    pass


def validate_structure_identity(
    molecule: Any,
    *,
    reference_smiles: str,
    charge: int,
    require_stereochemistry: bool,
) -> dict[str, Any]:
    reference = Chem.MolFromSmiles(reference_smiles)
    if reference is None:
        raise StructureIdentityError("reference SMILES is invalid")
    candidate = _candidate_heavy_molecule(molecule, charge=charge)

    mcs = rdFMCS.FindMCS(
        [reference, candidate],
        atomCompare=rdFMCS.AtomCompare.CompareElements,
        bondCompare=rdFMCS.BondCompare.CompareAny,
        ringMatchesRingOnly=True,
        completeRingsOnly=True,
        timeout=10,
    )
    graph_match = (
        not mcs.canceled
        and mcs.numAtoms == reference.GetNumAtoms() == candidate.GetNumAtoms()
        and mcs.numBonds == reference.GetNumBonds() == candidate.GetNumBonds()
    )
    if not graph_match:
        raise StructureIdentityError("candidate molecular graph does not match reference")

    reference_centers = dict(
        Chem.FindMolChiralCenters(reference, includeUnassigned=True, includeCIP=True)
    )
    stereochemistry_match: bool | None = None
    if require_stereochemistry:
        if not reference_centers or "?" in reference_centers.values():
            raise StructureIdentityError(
                "reference stereochemistry must specify every required center"
            )
        candidate_centers = dict(
            Chem.FindMolChiralCenters(
                candidate,
                includeUnassigned=True,
                includeCIP=True,
            )
        )
        stereochemistry_match = _stereochemistry_matches(
            reference,
            candidate,
            mcs.smartsString,
            reference_centers,
            candidate_centers,
        )
        if not stereochemistry_match:
            raise StructureIdentityError(
                "candidate stereochemistry does not match reference"
            )

    return {
        "graph_match": True,
        "stereochemistry_match": stereochemistry_match,
        "reference_heavy_atom_count": reference.GetNumAtoms(),
        "reference_stereocenter_count": len(reference_centers),
    }


def _candidate_heavy_molecule(molecule: Any, *, charge: int) -> Chem.Mol:
    xyz_lines = [str(len(molecule.atoms)), "identity reconstruction"]
    xyz_lines.extend(
        f"{atom.symbol} {atom.x:.12f} {atom.y:.12f} {atom.z:.12f}"
        for atom in molecule.atoms
    )
    candidate = Chem.MolFromXYZBlock("\n".join(xyz_lines) + "\n")
    if candidate is None:
        raise StructureIdentityError("could not construct molecule from XYZ")
    try:
        rdDetermineBonds.DetermineConnectivity(candidate)
        Chem.GetSymmSSSR(candidate)
        Chem.AssignAtomChiralTagsFromStructure(candidate, replaceExistingTags=True)
        candidate = Chem.RemoveHs(candidate, sanitize=False)
        Chem.GetSymmSSSR(candidate)
        Chem.AssignAtomChiralTagsFromStructure(candidate, replaceExistingTags=True)
        Chem.AssignStereochemistry(candidate, cleanIt=True, force=True)
    except Exception as exc:
        raise StructureIdentityError(
            f"could not reconstruct candidate molecular graph: {exc}"
        ) from exc
    return candidate


def _stereochemistry_matches(
    reference: Chem.Mol,
    candidate: Chem.Mol,
    mcs_smarts: str,
    reference_centers: dict[int, str],
    candidate_centers: dict[int, str],
) -> bool:
    query = Chem.MolFromSmarts(mcs_smarts)
    if query is None:
        return False
    reference_matches = reference.GetSubstructMatches(
        query,
        uniquify=False,
        maxMatches=1000,
    )
    candidate_matches = candidate.GetSubstructMatches(
        query,
        uniquify=False,
        maxMatches=1000,
    )
    for reference_match in reference_matches:
        for candidate_match in candidate_matches:
            mapping = {
                reference_match[index]: candidate_match[index]
                for index in range(len(reference_match))
            }
            if all(
                candidate_centers.get(mapping[atom_index]) == label
                for atom_index, label in reference_centers.items()
            ):
                return True
    return False
