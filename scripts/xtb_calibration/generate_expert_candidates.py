#!/usr/bin/env python
"""Generate deterministic private calibration candidates for expert xTB tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from rdkit import Chem
from rdkit.Chem import AllChem, rdMolDescriptors

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "src"
    / "verifier_grounded_benchmark"
    / "task"
    / "calibration"
    / "xtb"
)
TASK_2_SMILES = (
    "[N](C(C)([N+](=O)[O-])C(=O)OCC=C)"
    "C(C)([N+](=O)[O-])C(=O)OCC=C"
)
TASK_3_SMILES = "O=C1C(F)=CC(=O)C(F)=C1"
TASK_4_SMILES = "O=C1C(F)=CC2=CC=CC(F)=C2C1=O"
ROY_SMILES = "Cc1cc(c(s1)Nc2ccccc2[N+](=O)[O-])C#N"
RITONAVIR_SMILES = (
    "CC(C)C1=NC(=CS1)CN(C)C(=O)N[C@@H](C(C)C)C(=O)N[C@@H]"
    "(CC2=CC=CC=C2)C[C@@H]([C@H](CC3=CC=CC=C3)NC(=O)OCC4=CN=CS4)O"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def embed_xyz(smiles: str, *, seed: int, comment: str, use_uff: bool = False) -> str:
    molecule = Chem.AddHs(Chem.MolFromSmiles(smiles))
    status = AllChem.EmbedMolecule(
        molecule,
        randomSeed=seed,
        useRandomCoords=True,
    )
    if status != 0:
        raise RuntimeError(f"embedding failed for seed {seed}: {smiles}")
    if use_uff:
        optimization_status = AllChem.UFFOptimizeMolecule(molecule, maxIters=1000)
    else:
        optimization_status = AllChem.MMFFOptimizeMolecule(molecule, maxIters=1000)
    if optimization_status < 0:
        raise RuntimeError(f"force-field optimization failed for seed {seed}: {smiles}")
    lines = Chem.MolToXYZBlock(molecule).splitlines()
    lines[1] = comment
    return "\n".join(lines) + "\n"


def candidate(
    task_id: str,
    candidate_id: str,
    role: str,
    xyz: str,
    *,
    source: str,
) -> tuple[dict, dict]:
    answer = {
        "task_id": task_id,
        "candidate_id": candidate_id,
        "role": role,
        "response": f"FINAL ANSWER:\n```xyz\n{xyz}```",
    }
    metadata = {
        "task_id": task_id,
        "role": role,
        "source": source,
    }
    return answer, metadata


def build_candidates() -> tuple[list[dict], dict]:
    answers: list[dict] = []
    manifest: dict[str, dict] = {}

    positive_definitions = [
        (
            "xtb_014_formula_dipole_min",
            TASK_2_SMILES,
            [41, 53],
            "task2_symmetric_aminyl",
            False,
            True,
        ),
        (
            "xtb_015_two_fluorine_gap_min",
            TASK_3_SMILES,
            [19, 31],
            "task3_difluorobenzoquinone",
            True,
            False,
        ),
        (
            "xtb_016_c10_f2_gap_min",
            TASK_4_SMILES,
            [23, 37],
            "task4_difluoronaphthoquinone",
            True,
            False,
        ),
        (
            "xtb_017_roy_singlepoint_energy_min",
            ROY_SMILES,
            [7, 11, 17],
            "roy",
            False,
            False,
        ),
        (
            "xtb_018_ritonavir_optimized_energy_min",
            RITONAVIR_SMILES,
            [7, 13, 19],
            "ritonavir",
            False,
            False,
        ),
    ]
    for task_id, smiles, seeds, prefix, charge_comment, use_uff in positive_definitions:
        formula = rdMolDescriptors.CalcMolFormula(Chem.MolFromSmiles(smiles))
        for seed in seeds:
            candidate_id = f"{prefix}_seed_{seed}"
            comment = "charge=0" if charge_comment else candidate_id
            xyz = embed_xyz(
                smiles,
                seed=seed,
                comment=comment,
                use_uff=use_uff,
            )
            answer, metadata = candidate(
                task_id,
                candidate_id,
                "positive_candidate",
                xyz,
                source=f"RDKit ETKDG conformer of {smiles}",
            )
            metadata.update({"seed": seed, "formula": formula})
            answers.append(answer)
            manifest[candidate_id] = metadata

    negative_definitions = [
        ("xtb_014_formula_dipole_min", "O", "task2_negative_water", "negative formula"),
        ("xtb_015_two_fluorine_gap_min", "O", "task3_negative_water", "missing fluorine"),
        ("xtb_016_c10_f2_gap_min", "C", "task4_negative_methane", "wrong counts"),
        ("xtb_017_roy_singlepoint_energy_min", "CC#N", "roy_negative_acetonitrile", "wrong identity"),
        ("xtb_018_ritonavir_optimized_energy_min", ROY_SMILES, "ritonavir_negative_roy", "wrong identity"),
    ]
    for index, (task_id, smiles, candidate_id, source) in enumerate(
        negative_definitions,
        start=1,
    ):
        comment = (
            "charge=0"
            if task_id
            in {"xtb_015_two_fluorine_gap_min", "xtb_016_c10_f2_gap_min"}
            else candidate_id
        )
        xyz = embed_xyz(smiles, seed=100 + index, comment=comment)
        answer, metadata = candidate(
            task_id,
            candidate_id,
            "negative_baseline",
            xyz,
            source=source,
        )
        answers.append(answer)
        manifest[candidate_id] = metadata
    return answers, {"version": 1, "candidates": manifest}


def main() -> int:
    args = parse_args()
    answers, manifest = build_candidates()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    answers_text = "\n".join(
        json.dumps(answer, separators=(",", ":"), sort_keys=True)
        for answer in answers
    )
    (args.output_dir / "answers.jsonl").write_text(answers_text + "\n")
    (args.output_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False)
    )
    print(
        json.dumps(
            {"output_dir": str(args.output_dir), "num_candidates": len(answers)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
