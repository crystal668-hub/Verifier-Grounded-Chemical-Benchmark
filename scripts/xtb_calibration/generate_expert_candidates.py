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
DEFAULT_OUTPUT_DIR = ROOT / "tasks" / "xtb_xyz" / "expert_calibration"
TASK_2_SMILES = "CCO[C](O)Nc1cc([N+](=O)[O-])cc([N+](=O)[O-])c1CC(O)CO"
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
            "xtb_formula_dipole_min_014",
            TASK_2_SMILES,
            [17, 29],
            "task2_radical",
            False,
            True,
        ),
        (
            "xtb_two_fluorine_gap_min_015",
            TASK_3_SMILES,
            [19, 31],
            "task3_difluorobenzoquinone",
            True,
            False,
        ),
        (
            "xtb_c10_f2_gap_min_016",
            TASK_4_SMILES,
            [23, 37],
            "task4_difluoronaphthoquinone",
            True,
            False,
        ),
        (
            "xtb_roy_singlepoint_energy_min_017",
            ROY_SMILES,
            [7, 11, 17],
            "roy",
            False,
            False,
        ),
        (
            "xtb_ritonavir_optimized_energy_min_018",
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
        ("xtb_formula_dipole_min_014", "O", "task2_negative_water", "negative formula"),
        ("xtb_two_fluorine_gap_min_015", "O", "task3_negative_water", "missing fluorine"),
        ("xtb_c10_f2_gap_min_016", "C", "task4_negative_methane", "wrong counts"),
        ("xtb_roy_singlepoint_energy_min_017", "CC#N", "roy_negative_acetonitrile", "wrong identity"),
        ("xtb_ritonavir_optimized_energy_min_018", ROY_SMILES, "ritonavir_negative_roy", "wrong identity"),
    ]
    for index, (task_id, smiles, candidate_id, source) in enumerate(
        negative_definitions,
        start=1,
    ):
        comment = (
            "charge=0"
            if task_id
            in {"xtb_two_fluorine_gap_min_015", "xtb_c10_f2_gap_min_016"}
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
