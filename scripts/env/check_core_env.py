"""Smoke-check the core verifier environment."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
from typing import Any


def package_version(distribution: str) -> str:
    return metadata.version(distribution)


def check_rdkit() -> dict[str, Any]:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, QED, rdMolDescriptors
    from rdkit.Chem import AllChem

    sascorer = importlib.import_module("rdkit.Contrib.SA_Score.sascorer")

    mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
    if mol is None:
        raise RuntimeError("RDKit failed to parse aspirin SMILES")

    reaction = AllChem.ReactionFromSmarts("CCO>>CC=O", useSmiles=True)
    if reaction is None or reaction.GetNumReactantTemplates() != 1:
        raise RuntimeError("RDKit failed to parse reaction SMILES")

    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "qed": round(QED.qed(mol), 4),
        "logp": round(Crippen.MolLogP(mol), 4),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 4),
        "mw": round(Descriptors.MolWt(mol), 4),
        "sa_score": round(sascorer.calculateScore(mol), 4),
        "reaction_templates": {
            "reactants": reaction.GetNumReactantTemplates(),
            "products": reaction.GetNumProductTemplates(),
        },
    }


def check_ord_schema() -> str:
    from ord_schema.proto import reaction_pb2

    reaction = reaction_pb2.Reaction()
    return reaction.DESCRIPTOR.full_name


def check_ase() -> dict[str, Any]:
    from ase.build import molecule

    water = molecule("H2O")
    return {"formula": water.get_chemical_formula(), "natoms": len(water)}


def check_pymatgen() -> dict[str, str]:
    from pymatgen.core import Composition

    composition = Composition("LiFePO4")
    return {
        "formula": composition.formula,
        "reduced_formula": composition.reduced_formula,
    }


def main() -> None:
    modules = {
        "admet_ai": "admet-ai",
        "ase": "ase",
        "cclib": "cclib",
        "chembl_webresource_client": "chembl-webresource-client",
        "mp_api": "mp-api",
        "ord_schema": "ord-schema",
        "pymatgen": "pymatgen",
        "rdkit": "rdkit",
    }

    versions: dict[str, str] = {}
    for module, distribution in modules.items():
        importlib.import_module(module)
        versions[distribution] = package_version(distribution)

    result = {
        "status": "ok",
        "versions": versions,
        "checks": {
            "rdkit": check_rdkit(),
            "ord_schema": check_ord_schema(),
            "ase": check_ase(),
            "pymatgen": check_pymatgen(),
            "cclib_import": True,
            "mp_api_import": True,
            "admet_ai_import": True,
            "chembl_client_import": True,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
