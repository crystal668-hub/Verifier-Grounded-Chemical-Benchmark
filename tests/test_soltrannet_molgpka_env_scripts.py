from __future__ import annotations

import json
import sys
from argparse import Namespace
from typing import Any

import pytest

from scripts.env import check_molgpka_env
from scripts.env import check_soltrannet_env


def soltrannet_args(**overrides: Any) -> Namespace:
    values = {
        "smiles": "CCO",
        "image": "soltrannet:image",
        "container_name": "container",
        "host": "127.0.0.1",
        "port": 18081,
        "base_url": None,
        "docker_executable": None,
        "startup_timeout_seconds": 60.0,
        "prediction_timeout_seconds": 30.0,
    }
    values.update(overrides)
    return Namespace(**values)


def molgpka_args(**overrides: Any) -> Namespace:
    values = {
        "smiles": "CC(O)=O",
        "image": "molgpka:image",
        "platform": "linux/amd64",
        "docker_executable": None,
        "timeout_seconds": 120.0,
    }
    values.update(overrides)
    return Namespace(**values)


def test_check_soltrannet_env_reports_success_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"image": args.image, "mode": "external_docker"},
            "prediction": {"smiles": args.smiles, "soltrannet_log_s": 2.29},
        }

    monkeypatch.setattr(check_soltrannet_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_soltrannet_env.py", "--smiles", "CCO", "--image", "image:tag"])

    check_soltrannet_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["image"] == "image:tag"
    assert payload["prediction"]["soltrannet_log_s"] == 2.29


def test_check_soltrannet_env_reports_error_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {"status": "error", "failure_type": "verifier_environment_error", "message": "Docker unavailable"}

    monkeypatch.setattr(check_soltrannet_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_soltrannet_env.py"])

    check_soltrannet_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"


def test_check_soltrannet_env_reports_configured_base_url_only(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_spec: dict[str, Any] = {}

    def fake_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        assert image == "image:tag"
        return {"Id": "sha256:123"}

    def fake_predict(smiles: str, spec: dict[str, Any]) -> float:
        assert smiles == "CCO"
        seen_spec.update(spec)
        return 2.29

    monkeypatch.setattr(check_soltrannet_env.runtime, "docker_image_inspect", fake_inspect)
    monkeypatch.setattr(check_soltrannet_env.soltrannet_properties, "predict_soltrannet_log_s", fake_predict)
    args = soltrannet_args(image="image:tag")

    payload = check_soltrannet_env.build_payload(args)

    assert payload["status"] == "ok"
    assert payload["runtime"]["base_url"] is None
    assert seen_spec["soltrannet"]["base_url"] is None


def test_check_soltrannet_env_base_url_skips_image_inspect(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("docker_image_inspect should not run when base_url is configured")

    def fake_predict(smiles: str, spec: dict[str, Any]) -> float:
        assert smiles == "CCO"
        assert spec["soltrannet"]["base_url"] == "http://model.example"
        return 2.29

    monkeypatch.setattr(check_soltrannet_env.runtime, "docker_image_inspect", fail_inspect)
    monkeypatch.setattr(check_soltrannet_env.soltrannet_properties, "predict_soltrannet_log_s", fake_predict)

    payload = check_soltrannet_env.build_payload(soltrannet_args(base_url="http://model.example"))

    assert payload["status"] == "ok"
    assert payload["runtime"]["image"] == "soltrannet:image"
    assert payload["runtime"]["image_id"] is None
    assert payload["runtime"]["base_url"] == "http://model.example"
    assert payload["prediction"]["soltrannet_log_s"] == 2.29


def test_check_soltrannet_env_image_inspect_tool_error_is_environment_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        raise check_soltrannet_env.runtime.DockerRuntimeToolError("image missing")

    def fail_predict(smiles: str, spec: dict[str, Any]) -> float:
        raise AssertionError("prediction should not run after image inspect failure")

    monkeypatch.setattr(check_soltrannet_env.runtime, "docker_image_inspect", fail_inspect)
    monkeypatch.setattr(check_soltrannet_env.soltrannet_properties, "predict_soltrannet_log_s", fail_predict)

    payload = check_soltrannet_env.build_payload(soltrannet_args())

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"
    assert payload["message"] == "image missing"


def test_check_soltrannet_env_prediction_timeout_is_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        return {"Id": "sha256:123"}

    def fail_predict(smiles: str, spec: dict[str, Any]) -> float:
        raise check_soltrannet_env.runtime.DockerRuntimeTimeout("slow model")

    monkeypatch.setattr(check_soltrannet_env.runtime, "docker_image_inspect", fake_inspect)
    monkeypatch.setattr(check_soltrannet_env.soltrannet_properties, "predict_soltrannet_log_s", fail_predict)

    payload = check_soltrannet_env.build_payload(soltrannet_args())

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_timeout"
    assert payload["message"] == "slow model"


def test_check_soltrannet_env_prediction_tool_error_is_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        return {"Id": "sha256:123"}

    def fail_predict(smiles: str, spec: dict[str, Any]) -> float:
        raise check_soltrannet_env.runtime.DockerRuntimeToolError("bad model output")

    monkeypatch.setattr(check_soltrannet_env.runtime, "docker_image_inspect", fake_inspect)
    monkeypatch.setattr(check_soltrannet_env.soltrannet_properties, "predict_soltrannet_log_s", fail_predict)

    payload = check_soltrannet_env.build_payload(soltrannet_args())

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_tool_error"
    assert payload["message"] == "bad model output"


def test_check_molgpka_env_reports_success_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"image": args.image, "platform": args.platform},
            "prediction": {"smiles": args.smiles, "molgpka_pka_count": 1, "molgpka_pka_values": [8.34]},
        }

    monkeypatch.setattr(check_molgpka_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_molgpka_env.py", "--smiles", "CC(O)=O", "--image", "image:tag"])

    check_molgpka_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["image"] == "image:tag"
    assert payload["prediction"]["molgpka_pka_values"] == [8.34]


def test_check_molgpka_env_reports_error_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {"status": "error", "failure_type": "verifier_tool_error", "message": "bad output"}

    monkeypatch.setattr(check_molgpka_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_molgpka_env.py"])

    check_molgpka_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_tool_error"


def test_check_molgpka_env_image_inspect_tool_error_is_environment_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        raise check_molgpka_env.runtime.DockerRuntimeToolError("image missing")

    def fail_predict(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("prediction should not run after image inspect failure")

    monkeypatch.setattr(check_molgpka_env.runtime, "docker_image_inspect", fail_inspect)
    monkeypatch.setattr(check_molgpka_env.molgpka_properties, "predict_molgpka_properties", fail_predict)

    payload = check_molgpka_env.build_payload(molgpka_args())

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"
    assert payload["message"] == "image missing"


def test_check_molgpka_env_prediction_timeout_is_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        return {"Id": "sha256:123"}

    def fail_predict(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise check_molgpka_env.runtime.DockerRuntimeTimeout("slow model")

    monkeypatch.setattr(check_molgpka_env.runtime, "docker_image_inspect", fake_inspect)
    monkeypatch.setattr(check_molgpka_env.molgpka_properties, "predict_molgpka_properties", fail_predict)

    payload = check_molgpka_env.build_payload(molgpka_args())

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_timeout"
    assert payload["message"] == "slow model"


def test_check_molgpka_env_prediction_tool_error_is_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_inspect(image: str, **kwargs: Any) -> dict[str, Any]:
        return {"Id": "sha256:123"}

    def fail_predict(smiles: str, spec: dict[str, Any]) -> dict[str, Any]:
        raise check_molgpka_env.runtime.DockerRuntimeToolError("bad model output")

    monkeypatch.setattr(check_molgpka_env.runtime, "docker_image_inspect", fake_inspect)
    monkeypatch.setattr(check_molgpka_env.molgpka_properties, "predict_molgpka_properties", fail_predict)

    payload = check_molgpka_env.build_payload(molgpka_args())

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_tool_error"
    assert payload["message"] == "bad model output"
