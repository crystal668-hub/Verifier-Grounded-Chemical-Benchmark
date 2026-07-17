from __future__ import annotations

import importlib.util
from pathlib import Path

from verifier_grounded_benchmark.evaluation.open_generation.verification.runner import (
    SubprocessPropertyVerifier,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.rdkit_descriptors.backend import (
    evaluate_descriptor_constraint,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.backend import (
    evaluate_xtb_property_constraint,
)
from verifier_grounded_benchmark.task.loader import load_task_pack
from verifier_grounded_benchmark.task.resources import package_resource


VERIFIER_ROOT = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "verifier_grounded_benchmark"
    / "evaluation"
    / "open_generation"
    / "verifiers"
)


def _pack(name: str):
    return load_task_pack(
        package_resource(name, "tasks.yaml"),
        package_resource(name, "verifier_specs.yaml"),
    )


def test_all_formal_verifier_specs_use_importable_modules() -> None:
    for pack_name in ("rdkit", "xtb"):
        pack = _pack(pack_name)
        for spec in pack.verifier_specs:
            executor = spec.raw["executor"]
            assert executor["type"] == "python_module"
            assert importlib.util.find_spec(executor["module"]) is not None
            assert "verification_script" not in spec.raw


def test_concrete_backends_do_not_import_or_emit_scoring() -> None:
    for backend in VERIFIER_ROOT.glob("*/backend.py"):
        source = backend.read_text(encoding="utf-8")
        assert "score_constraint" not in source
        assert "common.scoring" not in source
        assert '"scores"' not in source
        assert "constraint_scores" not in source
    for backend in (VERIFIER_ROOT / "openmm").glob("*_backend.py"):
        source = backend.read_text(encoding="utf-8")
        assert "score_constraint" not in source
        assert '"scores"' not in source


def test_rdkit_backend_returns_verified_evidence_without_score() -> None:
    pack = _pack("rdkit")
    task = pack.tasks_by_id["rdkit_qed_max_001"]
    constraint = task["constraints"][0]
    spec = pack.verifier_specs_by_id[constraint["verifier_id"]]

    result = evaluate_descriptor_constraint(
        {"smiles": "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"},
        task,
        constraint,
        spec,
    )

    assert result["outcome"] == "verified"
    assert result["properties"]["qed"] > 0.8
    assert result["canonical_candidate"]["smiles"]
    assert "scores" not in result


def test_candidate_parse_failure_is_candidate_rejected_evidence() -> None:
    pack = _pack("xtb")
    task = pack.tasks_by_id["xtb_gap_window_001"]
    constraint = task["constraints"][0]
    spec = pack.verifier_specs_by_id[constraint["verifier_id"]]

    result = evaluate_xtb_property_constraint({}, task, constraint, spec)

    assert result["outcome"] == "candidate_rejected"
    assert result["failure_scope"] == "candidate"
    assert result["failure_type"] == "parse_error"
    assert "scores" not in result


def test_module_runner_returns_score_free_evidence() -> None:
    pack = _pack("rdkit")
    task = pack.tasks_by_id["rdkit_qed_max_001"]
    constraint = task["constraints"][0]
    spec = pack.verifier_specs_by_id[constraint["verifier_id"]]

    evidence = SubprocessPropertyVerifier().verify(
        {"smiles": "COc1ccc2cc([C@@H](C)C(=O)O)ccc2c1"},
        task,
        constraint,
        spec,
    )

    assert evidence.outcome == "verified"
    assert evidence.properties["qed"] > 0.8
    assert "scores" not in evidence.to_dict()
