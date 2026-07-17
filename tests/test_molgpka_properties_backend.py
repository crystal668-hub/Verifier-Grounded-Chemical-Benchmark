from __future__ import annotations

from typing import Any

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.common import docker_model_runtime
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.molgpka import backend as molgpka_properties


def payload(property_name: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = {"smiles": "CC(O)=O"}
    task = {"task_id": f"{property_name}_001", "version": 1, "object_type": "small_molecule"}
    constraint = {
        "type": "window",
        "property": property_name,
        "verifier_id": f"{property_name}_v1",
        "min": 7.0,
        "max": 9.0,
        "sigma": 1.0,
    }
    if property_name == "molgpka_pka_count":
        constraint.update({"min": 1, "max": 2})
    spec = {
        "verifier_id": f"{property_name}_v1",
        "property_name": property_name,
        "verifier_image": "verifier-grounded:dev",
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [1, 80],
            "mw": [1.0, 1000.0],
            "formal_charge": [-2, 2],
        },
    }
    return candidate, task, constraint, spec


def test_parse_molgpka_response_reads_values() -> None:
    properties = molgpka_properties.parse_molgpka_response(["CC(O)=O", 1, [8.34]])

    assert properties["molgpka_pka_count"] == 1
    assert properties["molgpka_pka_values"] == [8.34]
    assert properties["molgpka_min_pka"] == pytest.approx(8.34)
    assert properties["molgpka_max_pka"] == pytest.approx(8.34)


def test_parse_molgpka_response_rejects_bad_shape() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response({"bad": "shape"})


@pytest.mark.parametrize("bad_value", [float("nan"), "NaN"])
def test_parse_molgpka_response_rejects_nonfinite_pka_value(bad_value: float | str) -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", 1, [bad_value]])


def test_parse_molgpka_response_rejects_nonnumeric_pka_value() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", 1, ["not-a-number"]])


def test_parse_molgpka_response_rejects_boolean_pka_value() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", 1, [True]])


def test_parse_molgpka_response_rejects_boolean_count() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", True, [8.34]])


def test_parse_molgpka_response_rejects_float_count() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", 1.5, [8.34]])


def test_parse_molgpka_response_rejects_negative_count() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", -1, [8.34]])


def test_parse_molgpka_response_rejects_count_value_mismatch() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        molgpka_properties.parse_molgpka_response(["CC(O)=O", 2, [8.34]])


def test_parse_molgpka_stdout_reads_noisy_output() -> None:
    properties = molgpka_properties.parse_molgpka_stdout(
        "loading model\n"
        "warning: optional dependency not found\n"
        '["CC(O)=O", 1, [8.34]]\n'
    )

    assert properties["molgpka_pka_count"] == 1
    assert properties["molgpka_pka_values"] == [8.34]


def test_evaluate_molgpka_scores_min_max_and_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        molgpka_properties,
        "predict_molgpka_properties",
        lambda smiles, spec: {
            "molgpka_pka_values": [4.2, 8.34],
            "molgpka_pka_count": 2,
            "molgpka_min_pka": 4.2,
            "molgpka_max_pka": 8.34,
        },
    )

    for property_name, expected in [
        ("molgpka_min_pka", 4.2),
        ("molgpka_max_pka", 8.34),
        ("molgpka_pka_count", 2),
    ]:
        candidate, task, constraint, spec = payload(property_name)
        if property_name == "molgpka_min_pka":
            constraint.update({"min": 4.0, "max": 4.5})
        result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)
        assert result["outcome"] == "verified"
        assert result["canonical_candidate"]["smiles"] == "CC(=O)O"
        assert result["properties"][property_name] == pytest.approx(expected)


def test_evaluate_molgpka_allows_zero_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        molgpka_properties,
        "predict_molgpka_properties",
        lambda smiles, spec: {"molgpka_pka_values": [], "molgpka_pka_count": 0},
    )
    candidate, task, constraint, spec = payload("molgpka_pka_count")
    constraint.update({"min": 0, "max": 0})

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["outcome"] == "verified"
    assert result["properties"]["molgpka_pka_count"] == 0


def test_evaluate_molgpka_min_errors_when_no_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        molgpka_properties,
        "predict_molgpka_properties",
        lambda smiles, spec: {"molgpka_pka_values": [], "molgpka_pka_count": 0},
    )
    candidate, task, constraint, spec = payload("molgpka_min_pka")

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "domain_error"
    assert "no ionizable" in result["message"].lower()
    assert result["properties"]["molgpka_pka_count"] == 0


def test_evaluate_molgpka_maps_runtime_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise docker_model_runtime.DockerRuntimeEnvironmentError("Docker unavailable")

    monkeypatch.setattr(molgpka_properties, "predict_molgpka_properties", fail)
    candidate, task, constraint, spec = payload("molgpka_max_pka")

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["heavy_atom_count"] == 4


def test_evaluate_molgpka_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise docker_model_runtime.DockerRuntimeTimeout("slow")

    monkeypatch.setattr(molgpka_properties, "predict_molgpka_properties", fail)
    candidate, task, constraint, spec = payload("molgpka_max_pka")

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_timeout"
    assert result["properties"]["heavy_atom_count"] == 4


@pytest.mark.parametrize(
    "error",
    [
        docker_model_runtime.DockerRuntimeToolError("bad model output"),
        RuntimeError("unexpected model failure"),
    ],
)
def test_evaluate_molgpka_maps_tool_errors_with_domain_properties(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise error

    monkeypatch.setattr(molgpka_properties, "predict_molgpka_properties", fail)
    candidate, task, constraint, spec = payload("molgpka_max_pka")

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_tool_error"
    assert result["properties"]["heavy_atom_count"] == 4


def test_evaluate_molgpka_rejects_property_mismatch() -> None:
    candidate, task, constraint, spec = payload("molgpka_max_pka")
    spec["property_name"] = "molgpka_min_pka"

    result = molgpka_properties.evaluate_molgpka_constraint(candidate, task, constraint, spec)

    assert result["outcome"] != "verified"
    assert result["failure_type"] == "verifier_spec_error"


def test_predict_molgpka_dispatches_to_one_shot_container(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run_one_shot_container(**kwargs: Any) -> str:
        calls.append(kwargs)
        return '["CC(=O)O", 1, [8.34]]\n'

    monkeypatch.setattr(docker_model_runtime, "run_one_shot_container", fake_run_one_shot_container)
    _, _, _, spec = payload("molgpka_pka_count")
    spec["molgpka"] = {
        "image": "image:tag",
        "platform": "linux/test",
        "timeout_seconds": 12,
        "docker_executable": "docker-test",
    }

    properties = molgpka_properties.predict_molgpka_properties("CC(=O)O", spec)

    assert properties["molgpka_pka_count"] == 1
    assert calls[0]["image"] == "image:tag"
    assert calls[0]["platform"] == "linux/test"
    assert calls[0]["timeout_seconds"] == 12.0
    assert calls[0]["docker_executable"] == "docker-test"
    assert calls[0]["workdir"] == "/src"
    assert calls[0]["command"][:6] == ["micromamba", "run", "-n", "MolGpka", "python", "-c"]
    assert calls[0]["command"][-1] == "CC(=O)O"


def test_predict_molgpka_rejects_unsupported_runtime() -> None:
    _, _, _, spec = payload("molgpka_pka_count")
    spec["molgpka"] = {"runtime": "local"}

    with pytest.raises(docker_model_runtime.DockerRuntimeEnvironmentError) as exc:
        molgpka_properties.predict_molgpka_properties("CC(=O)O", spec)

    assert "unsupported MolGpKa runtime: local" in str(exc.value)
