from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from verifiers.xtb import backend as xtb_backend
from verifiers.xtb.structure_identity import StructureIdentityError
from verifiers.xtb.structure_identity import validate_structure_identity


ROY_SMILES = "Cc1cc(c(s1)Nc2ccccc2[N+](=O)[O-])C#N"
RITONAVIR_SMILES = (
    "CC(C)C1=NC(=CS1)CN(C)C(=O)N[C@@H](C(C)C)C(=O)N[C@@H]"
    "(CC2=CC=CC=C2)C[C@@H]([C@H](CC3=CC=CC=C3)NC(=O)OCC4=CN=CS4)O"
)
LACTIC_ACID_SMILES = "C[C@H](O)C(=O)O"


@lru_cache(maxsize=None)
def xyz_for_smiles(smiles: str, seed: int = 7) -> str:
    molecule = Chem.AddHs(Chem.MolFromSmiles(smiles))
    assert AllChem.EmbedMolecule(molecule, randomSeed=seed, useRandomCoords=True) == 0
    AllChem.MMFFOptimizeMolecule(molecule, maxIters=300)
    return Chem.MolToXYZBlock(molecule)


def test_roy_identity_accepts_reference_connectivity() -> None:
    result = validate_structure_identity(
        xtb_backend.parse_xyz(xyz_for_smiles(ROY_SMILES)),
        reference_smiles=ROY_SMILES,
        charge=0,
        require_stereochemistry=False,
    )

    assert result["graph_match"] is True
    assert result["stereochemistry_match"] is None
    assert result["reference_heavy_atom_count"] == 18


def test_roy_identity_is_independent_of_xyz_atom_order() -> None:
    molecule = Chem.AddHs(Chem.MolFromSmiles(ROY_SMILES))
    assert AllChem.EmbedMolecule(molecule, randomSeed=11) == 0
    order = list(reversed(range(molecule.GetNumAtoms())))
    reordered = Chem.RenumberAtoms(molecule, order)

    result = validate_structure_identity(
        xtb_backend.parse_xyz(Chem.MolToXYZBlock(reordered)),
        reference_smiles=ROY_SMILES,
        charge=0,
        require_stereochemistry=False,
    )

    assert result["graph_match"] is True


def test_roy_identity_rejects_connectivity_change() -> None:
    positional_isomer = "Cc1c(C#N)cc(Nc2ccccc2[N+](=O)[O-])s1"

    with pytest.raises(StructureIdentityError, match="graph"):
        validate_structure_identity(
            xtb_backend.parse_xyz(xyz_for_smiles(positional_isomer)),
            reference_smiles=ROY_SMILES,
            charge=0,
            require_stereochemistry=False,
        )


def test_ritonavir_identity_recovers_all_reference_stereocenters() -> None:
    result = validate_structure_identity(
        xtb_backend.parse_xyz(xyz_for_smiles(RITONAVIR_SMILES)),
        reference_smiles=RITONAVIR_SMILES,
        charge=0,
        require_stereochemistry=True,
    )

    assert result["graph_match"] is True
    assert result["stereochemistry_match"] is True
    assert result["reference_heavy_atom_count"] == 50
    assert result["reference_stereocenter_count"] == 4


def test_ritonavir_identity_rejects_inverted_stereocenter() -> None:
    inverted = RITONAVIR_SMILES.replace("[C@@H]", "[C@H]", 1)

    with pytest.raises(StructureIdentityError, match="stereochemistry"):
        validate_structure_identity(
            xtb_backend.parse_xyz(xyz_for_smiles(inverted)),
            reference_smiles=RITONAVIR_SMILES,
            charge=0,
            require_stereochemistry=True,
        )


def test_backend_rechecks_identity_after_optimization() -> None:
    class InvertingRunner:
        def run(
            self,
            mode: str,
            xyz_path: Path,
            timeout_seconds: float,
            *,
            spec: dict,
        ) -> xtb_backend.XTBRunResult:
            assert mode == "optimize"
            inverted = LACTIC_ACID_SMILES.replace("[C@H]", "[C@@H]")
            (xyz_path.parent / "xtbopt.xyz").write_text(xyz_for_smiles(inverted))
            return xtb_backend.XTBRunResult(
                stdout=(
                    "TOTAL ENERGY -10.000000 Eh\n"
                    "GEOMETRY OPTIMIZATION CONVERGED\n"
                ),
                stderr="",
                returncode=0,
            )

    task = {
        "task_id": "identity_task",
        "structure_identity": {
            "reference_smiles": LACTIC_ACID_SMILES,
            "require_stereochemistry": True,
            "recheck_after_optimization": True,
        },
        "constraints": [
            {
                "type": "minimize_bounded",
                "property": "total_energy",
                "verifier_id": "xtb_total_energy_gfn2_v1",
                "lower": -12.0,
                "upper": -8.0,
            }
        ],
    }
    spec = {
        "verifier_id": "xtb_total_energy_gfn2_v1",
        "property_name": "total_energy",
        "timeout_seconds": 60,
        "backend": {
            "executable": "xtb",
            "charge": 0,
            "uhf": 0,
            "calculation_mode": "optimized",
        },
        "domain": {
            "allowed_elements": ["H", "C", "O"],
            "inferred_components": 1,
            "min_interatomic_distance": 0.45,
        },
    }

    result = xtb_backend.evaluate_xtb_property_constraint(
        {"xyz": xyz_for_smiles(LACTIC_ACID_SMILES)},
        task,
        task["constraints"][0],
        spec,
        runner=InvertingRunner(),
    )

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"
    assert "stereochemistry" in result["message"]
