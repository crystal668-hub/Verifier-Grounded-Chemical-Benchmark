from __future__ import annotations

from typing import Any

import pytest

from verifiers.backends import docker_model_runtime
from verifiers.backends import soltrannet_properties


def payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidate = {"smiles": "CCO"}
    task = {"task_id": "soltrannet_log_s_001", "version": 1, "object_type": "small_molecule"}
    constraint = {
        "type": "window",
        "property": "soltrannet_log_s",
        "verifier_id": "soltrannet_log_s_v1",
        "min": 2.0,
        "max": 2.5,
        "sigma": 1.0,
    }
    spec = {
        "verifier_id": "soltrannet_log_s_v1",
        "property_name": "soltrannet_log_s",
        "verifier_image": "verifier-grounded:dev",
        "domain": {
            "allowed_elements": ["C", "N", "O", "F", "P", "S", "Cl", "Br", "I"],
            "heavy_atom_count": [1, 80],
            "mw": [1.0, 1000.0],
            "formal_charge": [-2, 2],
        },
    }
    return candidate, task, constraint, spec


def test_parse_soltrannet_response_reads_solubility() -> None:
    value = soltrannet_properties.parse_soltrannet_response([{"solubility": 2.297180414199829}])

    assert value == pytest.approx(2.297180414199829)


def test_parse_soltrannet_response_rejects_missing_solubility() -> None:
    with pytest.raises(docker_model_runtime.DockerRuntimeToolError):
        soltrannet_properties.parse_soltrannet_response([{"other": 1.0}])


def test_evaluate_soltrannet_scores_mocked_prediction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", lambda smiles, spec: 2.297180414199829)
    candidate, task, constraint, spec = payload()

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "ok"
    assert result["canonical_smiles"] == "CCO"
    assert result["properties"]["soltrannet_log_s"] == pytest.approx(2.297180414199829)
    assert result["properties"]["heavy_atom_count"] == 3
    assert result["scores"]["score"] == 1.0


def test_evaluate_soltrannet_maps_runtime_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> float:
        raise docker_model_runtime.DockerRuntimeEnvironmentError("Docker daemon unavailable")

    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", fail)
    candidate, task, constraint, spec = payload()

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_environment_error"
    assert result["properties"]["heavy_atom_count"] == 3


def test_evaluate_soltrannet_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> float:
        raise docker_model_runtime.DockerRuntimeTimeout("slow")

    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", fail)
    candidate, task, constraint, spec = payload()

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_timeout"


def test_evaluate_soltrannet_rejects_property_mismatch() -> None:
    candidate, task, constraint, spec = payload()
    spec["property_name"] = "other"

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"


def test_evaluate_soltrannet_rejects_unsupported_property(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(smiles: str, spec: dict[str, Any]) -> float:
        raise AssertionError("prediction should not be called")

    monkeypatch.setattr(soltrannet_properties, "predict_soltrannet_log_s", fail)
    candidate, task, constraint, spec = payload()
    constraint["property"] = "other_soltrannet_property"
    spec["property_name"] = "other_soltrannet_property"

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "verifier_spec_error"
    assert "unsupported" in result["message"]


def test_evaluate_soltrannet_rejects_multicomponent_smiles() -> None:
    candidate, task, constraint, spec = payload()
    candidate["smiles"] = "CCO.O"

    result = soltrannet_properties.evaluate_soltrannet_constraint(candidate, task, constraint, spec)

    assert result["status"] == "error"
    assert result["failure_type"] == "validity_error"


def test_predict_soltrannet_uses_configured_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    ensure_calls: list[dict[str, Any]] = []
    http_calls: list[dict[str, Any]] = []

    def fake_ensure_http_container(**kwargs: Any) -> None:
        ensure_calls.append(kwargs)

    def fake_http_json(url: str, **kwargs: Any) -> list[dict[str, float]]:
        http_calls.append({"url": url, **kwargs})
        return [{"solubility": 2.1}]

    monkeypatch.setattr(docker_model_runtime, "ensure_http_container", fake_ensure_http_container)
    monkeypatch.setattr(docker_model_runtime, "http_json", fake_http_json)
    _, _, _, spec = payload()
    spec["soltrannet"] = {"base_url": "http://example.test/soltrannet/"}

    value = soltrannet_properties.predict_soltrannet_log_s("CCO", spec)

    assert value == pytest.approx(2.1)
    assert ensure_calls == []
    assert http_calls == [
        {
            "url": "http://example.test/soltrannet/run",
            "method": "POST",
            "payload": ["CCO"],
            "timeout_seconds": 30.0,
        }
    ]


def test_predict_soltrannet_rejects_unsupported_runtime() -> None:
    _, _, _, spec = payload()
    spec["soltrannet"] = {"runtime": "local"}

    with pytest.raises(docker_model_runtime.DockerRuntimeEnvironmentError) as exc:
        soltrannet_properties.predict_soltrannet_log_s("CCO", spec)

    assert "unsupported SolTranNet runtime: local" in str(exc.value)
