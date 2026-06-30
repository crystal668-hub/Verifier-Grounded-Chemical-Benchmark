from __future__ import annotations

from pathlib import Path

from benchmark.verifier_scripts import run_verification_script


ROOT = Path(__file__).resolve().parents[1]


def test_rdkit_forcefield_script_outputs_single_constraint_result_json() -> None:
    spec = {
        "verifier_id": "rdkit_forcefield_energy_range_v1",
        "verifier_image": "verifier-grounded:dev",
        "verification_script": "verifiers/forcefield/rdkit_energy_range.py",
        "property_name": "energy_range_kcal_mol",
        "backend": {
            "type": "rdkit_forcefield",
            "embedder": "ETKDGv3",
            "random_seed": 61453,
            "num_conformers": 8,
            "prune_rms_thresh": 0.5,
            "forcefield_priority": ["MMFF94s", "MMFF94", "UFF"],
            "max_iters": 200,
        },
        "domain": {
            "allowed_elements": ["H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [5, 60],
            "mw": [0.0, 600.0],
            "formal_charge": [-1, 1],
        },
    }
    payload = {
        "task": {"task_id": "rdkit_forcefield_energy_range_window_001"},
        "constraint": {
            "type": "window",
            "property": "energy_range_kcal_mol",
            "min": 0.0,
            "max": 20.0,
            "sigma": 5.0,
        },
        "verifier_spec": spec,
        "candidate": {"smiles": "CCOc1ccc(NC(=O)C)cc1"},
    }

    result = run_verification_script(ROOT / spec["verification_script"], payload, timeout_seconds=60)

    assert result["status"] == "ok"
    assert result["task_id"] == "rdkit_forcefield_energy_range_window_001"
    assert result["verifier_id"] == "rdkit_forcefield_energy_range_v1"
    assert result["canonical_smiles"] == "CCOc1ccc(NC(C)=O)cc1"
    assert result["properties"]["forcefield_name"] in {"MMFF94s", "MMFF94"}
    assert result["properties"]["energy_range_kcal_mol"] >= 0.0
    assert result["scores"]["constraint_scores"] == [
        {"property": "energy_range_kcal_mol", "type": "window", "score": 1.0}
    ]
