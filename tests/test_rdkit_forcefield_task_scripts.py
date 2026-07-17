from __future__ import annotations

from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import SubprocessPropertyVerifier
from verifier_grounded_benchmark.task import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource


def test_rdkit_forcefield_script_outputs_single_constraint_result_json() -> None:
    pack = load_task_pack(
        package_resource("experimental/rdkit_forcefield", "tasks.yaml"),
        package_resource("experimental/rdkit_forcefield", "verifier_specs.yaml"),
    )
    task = pack.tasks_by_id["rdkit_forcefield_energy_range_window_001"]
    constraint = task["constraints"][0]
    spec = pack.verifier_specs_by_id[constraint["verifier_id"]]

    result = SubprocessPropertyVerifier().verify(
        {"smiles": "CCOc1ccc(NC(=O)C)cc1"}, task, constraint, spec
    ).to_dict()

    assert result["outcome"] == "verified"
    assert result["task_id"] == "rdkit_forcefield_energy_range_window_001"
    assert result["verifier_id"] == "rdkit_forcefield_energy_range_v1"
    assert result["canonical_candidate"]["smiles"] == "CCOc1ccc(NC(C)=O)cc1"
    assert result["properties"]["forcefield_name"] in {"MMFF94s", "MMFF94"}
    assert result["properties"]["energy_range_kcal_mol"] >= 0.0
    assert "scores" not in result
