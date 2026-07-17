from __future__ import annotations

from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import SubprocessPropertyVerifier
from verifier_grounded_benchmark.task import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource


def test_rdkit_descriptor_script_outputs_single_constraint_result_json() -> None:
    pack = load_task_pack(
        package_resource("rdkit", "tasks.yaml"),
        package_resource("rdkit", "verifier_specs.yaml"),
    )
    task = pack.tasks_by_id["rdkit_logp_window_003"]
    constraint = task["constraints"][0]
    spec = pack.verifier_specs_by_id[constraint["verifier_id"]]

    result = SubprocessPropertyVerifier().verify(
        {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}, task, constraint, spec
    ).to_dict()

    assert result["outcome"] == "verified"
    assert result["task_id"] == "rdkit_logp_window_003"
    assert result["verifier_id"] == "rdkit_logp_v1"
    assert result["canonical_candidate"]["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert set(result["properties"]) == {"logp"}
    assert "scores" not in result
