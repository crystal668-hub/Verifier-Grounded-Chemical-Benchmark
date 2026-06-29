from __future__ import annotations

import json
import ast
from pathlib import Path

import pytest
import yaml

from benchmark.evaluate import evaluate_one
from verifiers.backends.rdkit_descriptors import score_constraint


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "rdkit_baseline"


def test_sa_score_import_avoids_static_contrib_import() -> None:
    for path in [
        ROOT / "verifiers" / "backends" / "rdkit_descriptors.py",
        ROOT / "scripts" / "check_core_env.py",
    ]:
        tree = ast.parse(path.read_text())
        static_contrib_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("rdkit.Contrib.SA_Score")
        ]

        assert not static_contrib_imports


def load_tasks() -> list[dict]:
    with (TASK_DIR / "tasks.yaml").open() as handle:
        payload = yaml.safe_load(handle)
    return payload["tasks"]


def load_specs() -> dict:
    with (TASK_DIR / "verifier_specs.yaml").open() as handle:
        payload = yaml.safe_load(handle)
    return {spec["verifier_id"]: spec for spec in payload["verifiers"]}


def load_samples() -> list[dict]:
    with (TASK_DIR / "sample_answers.jsonl").open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_task_constraints_bind_to_descriptor_verifier_specs() -> None:
    tasks = load_tasks()
    specs = load_specs()
    expected_by_property = {
        "qed": "rdkit_qed_v1",
        "sa_score": "rdkit_sa_score_v1",
        "logp": "rdkit_logp_v1",
        "tpsa": "rdkit_tpsa_v1",
        "hba": "rdkit_hba_v1",
        "hbd": "rdkit_hbd_v1",
        "fraction_csp3": "rdkit_fraction_csp3_v1",
    }

    assert len(tasks) == 10
    assert len({task["task_id"] for task in tasks}) == 10
    assert set(expected_by_property.values()).issubset(specs)
    assert all(task["task_id"] not in {"rdkit_mw_window_005", "rdkit_mw_qed_011"} for task in tasks)
    for task in tasks:
        assert "verifier_id" not in task
        assert task["object_type"] == "small_molecule"
        assert task["answer_schema"]["format"] == "final_answer_line"
        assert task["answer_schema"]["final_answer_prefix"] == "FINAL ANSWER:"
        assert task["answer_schema"]["value_type"] == "smiles"
        assert task["answer_schema"]["cardinality"] == "one"
        assert len(task["constraints"]) in {1, 2}
        for constraint in task["constraints"]:
            assert constraint["property"] != "mw"
            assert constraint["verifier_id"] == expected_by_property[constraint["property"]]
            spec = specs[constraint["verifier_id"]]
            assert spec["descriptor"] == constraint["property"]
            assert spec["verifier_image"] == "verifier-grounded:dev"
            assert spec["verification_script"] == f"verifiers/descriptors/{constraint['verifier_id'].removesuffix('_v1')}.py"
            assert (ROOT / spec["verification_script"]).exists()
            assert spec["backend"]["type"] == "rdkit_descriptors"
            assert "verifiers/tasks/rdkit_" not in spec["verification_script"]
            assert "rdkit_common" not in spec["verification_script"]


def test_rdkit_domain_gate_uses_only_mw_upper_bound() -> None:
    specs = load_specs()

    for spec in specs.values():
        if spec["backend"]["type"] == "rdkit_descriptors":
            assert spec["domain"]["mw"] == [0.0, 600.0]


def test_prompts_expose_requirements_without_verifier_internals() -> None:
    banned_fragments = [
        "verifier",
        "applicability domain",
        "benchmark validity",
        "benchmark",
        "domain constraints",
        "RDKit-calculated",
        "small-molecule",
        "sigma",
        "geometric mean",
    ]
    required_fragments = [
        "The molecule must satisfy these requirements:",
        "The SMILES must describe exactly one component; dot-separated multi-component SMILES are not accepted.",
        "Allowed elements: H, B, C, N, O, F, P, S, Cl, Br, I.",
        "Heavy atom count must be between 5 and 60 inclusive.",
        "Molecular weight must be at most 600.0 daltons.",
        "Formal charge must be between -1 and 1 inclusive.",
    ]

    for task in load_tasks():
        prompt = task["prompt"]
        prompt_lower = prompt.lower()
        assert prompt.startswith("Propose one valid single-component molecule and provide it as a SMILES string.")
        assert all(fragment in prompt for fragment in required_fragments)
        assert "Your final answer must appear on its own line exactly in this format:" in prompt
        assert prompt.rstrip().endswith("FINAL ANSWER: <SMILES>")
        assert not any(fragment in prompt_lower for fragment in banned_fragments)
        for constraint in task["constraints"]:
            if constraint["type"] == "window":
                assert str(float(constraint["min"])) in prompt
                assert str(float(constraint["max"])) in prompt
            if constraint["type"] in {"maximize_bounded", "minimize_bounded"}:
                assert str(float(constraint["lower"])) in prompt
                assert str(float(constraint["upper"])) in prompt


def test_sample_answers_score_successfully() -> None:
    tasks = {task["task_id"]: task for task in load_tasks()}
    specs = load_specs()
    samples = load_samples()

    assert len(samples) == 10
    assert all(sample["task_id"] in tasks for sample in samples)
    for sample in samples:
        task = tasks[sample["task_id"]]
        result = evaluate_one(sample, tasks, specs)
        assert result["status"] == "ok"
        assert result["failure_type"] is None
        assert 0.0 <= result["scores"]["property_score"] <= 1.0
        assert result["canonical_smiles"]


@pytest.mark.parametrize(
    ("constraint", "properties", "expected"),
    [
        ({"type": "window", "property": "logp", "min": 1.0, "max": 3.0, "sigma": 0.5}, {"logp": 2.0}, 1.0),
        ({"type": "window", "property": "logp", "min": 1.0, "max": 3.0, "sigma": 0.5}, {"logp": 3.5}, pytest.approx(0.367879, rel=1e-5)),
        ({"type": "maximize_bounded", "property": "qed", "lower": 0.0, "upper": 1.0}, {"qed": 0.72}, 0.72),
        ({"type": "minimize_bounded", "property": "sa_score", "lower": 1.0, "upper": 10.0}, {"sa_score": 2.8}, pytest.approx(0.8)),
    ],
)
def test_score_constraint_modes(constraint: dict, properties: dict, expected: float) -> None:
    assert score_constraint(properties, constraint) == expected


def test_bounded_scoring_does_not_accept_good_at_or_baseline() -> None:
    with pytest.raises(ValueError, match="good_at|baseline"):
        score_constraint(
            {"qed": 0.8},
            {
                "type": "maximize_bounded",
                "property": "qed",
                "lower": 0.0,
                "upper": 1.0,
                "good_at": 0.8,
            },
        )


def test_invalid_smiles_returns_parse_error() -> None:
    task = load_tasks()[0]
    result = evaluate_one({"task_id": task["task_id"], "candidates": [{"smiles": "not a smiles"}]}, {task["task_id"]: task}, load_specs())

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_multicomponent_smiles_returns_validity_error() -> None:
    task = load_tasks()[0]
    result = evaluate_one({"task_id": task["task_id"], "candidates": [{"smiles": "CCO.O"}]}, {task["task_id"]: task}, load_specs())

    assert result["status"] == "error"
    assert result["failure_type"] == "validity_error"


def test_disallowed_element_returns_domain_error() -> None:
    task = load_tasks()[0]
    result = evaluate_one({"task_id": task["task_id"], "candidates": [{"smiles": "C[Si](C)(C)C"}]}, {task["task_id"]: task}, load_specs())

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"


def test_light_single_component_molecule_is_not_rejected_by_mw_domain() -> None:
    task = next(task for task in load_tasks() if task["task_id"] == "rdkit_logp_window_003")
    result = evaluate_one({"task_id": task["task_id"], "candidates": [{"smiles": "c1ccccc1"}]}, {task["task_id"]: task}, load_specs())

    assert result["failure_type"] != "domain_error"


def test_known_descriptor_values_are_stable() -> None:
    task = load_tasks()[0]

    aspirin = evaluate_one(
        {"task_id": task["task_id"], "candidates": [{"smiles": "CC(=O)Oc1ccccc1C(=O)O"}]},
        {task["task_id"]: task},
        load_specs(),
    )
    ibuprofen = evaluate_one(
        {"task_id": task["task_id"], "candidates": [{"smiles": "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"}]},
        {task["task_id"]: task},
        load_specs(),
    )

    assert aspirin["properties"]["qed"] == pytest.approx(0.5501, abs=1e-4)
    assert ibuprofen["properties"]["qed"] == pytest.approx(0.8216, abs=1e-4)
