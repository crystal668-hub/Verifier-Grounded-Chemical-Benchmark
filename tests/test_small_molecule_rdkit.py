from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from verifiers.small_molecule_rdkit import (
    evaluate_answer,
    score_constraint,
)


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "tasks" / "rdkit_baseline"


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


def test_task_cards_bind_to_verifier_spec() -> None:
    tasks = load_tasks()
    specs = load_specs()

    assert len(tasks) == 12
    assert len({task["task_id"] for task in tasks}) == 12
    for task in tasks:
        assert task["verifier_id"] in specs
        assert task["object_type"] == "small_molecule"
        assert task["answer_schema"]["format"] == "json"
        assert len(task["constraints"]) in {1, 2}


def test_prompts_expose_targets_without_verifier_internals() -> None:
    banned_fragments = [
        "rdkit",
        "verifier",
        "applicability domain",
        "sigma",
        "geometric mean",
    ]

    for task in load_tasks():
        prompt = task["prompt"]
        prompt_lower = prompt.lower()
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

    assert len(samples) == 12
    for sample in samples:
        task = tasks[sample["task_id"]]
        result = evaluate_answer(sample, task, specs[task["verifier_id"]])
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
    spec = load_specs()[task["verifier_id"]]
    result = evaluate_answer({"task_id": task["task_id"], "candidates": [{"smiles": "not a smiles"}]}, task, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "parse_error"


def test_multicomponent_smiles_returns_validity_error() -> None:
    task = load_tasks()[0]
    spec = load_specs()[task["verifier_id"]]
    result = evaluate_answer({"task_id": task["task_id"], "candidates": [{"smiles": "CCO.O"}]}, task, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "validity_error"


def test_disallowed_element_returns_domain_error() -> None:
    task = load_tasks()[0]
    spec = load_specs()[task["verifier_id"]]
    result = evaluate_answer({"task_id": task["task_id"], "candidates": [{"smiles": "C[Si](C)(C)C"}]}, task, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "domain_error"


def test_known_descriptor_values_are_stable() -> None:
    task = load_tasks()[0]
    spec = load_specs()[task["verifier_id"]]

    aspirin = evaluate_answer(
        {"task_id": task["task_id"], "candidates": [{"smiles": "CC(=O)Oc1ccccc1C(=O)O"}]},
        task,
        spec,
    )
    ibuprofen = evaluate_answer(
        {"task_id": task["task_id"], "candidates": [{"smiles": "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"}]},
        task,
        spec,
    )

    assert aspirin["properties"]["qed"] == pytest.approx(0.5501, abs=1e-4)
    assert aspirin["properties"]["logp"] == pytest.approx(1.3101, abs=1e-4)
    assert aspirin["properties"]["tpsa"] == pytest.approx(63.6, abs=1e-4)
    assert aspirin["properties"]["mw"] == pytest.approx(180.159, abs=1e-3)
    assert ibuprofen["properties"]["qed"] == pytest.approx(0.8216, abs=1e-4)
    assert ibuprofen["properties"]["sa_score"] == pytest.approx(2.1918, abs=1e-4)
