from __future__ import annotations

import json
import sys
from argparse import Namespace
from typing import Any

import pytest

from scripts.env import check_mace_mp_env
from scripts.env import check_torchani_env


def test_check_torchani_env_reports_success_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"model_name": args.model_name, "device": args.device},
            "prediction": {"torchani_total_energy_hartree": -76.38121032714844},
        }

    monkeypatch.setattr(check_torchani_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_torchani_env.py", "--model-name", "ANI2x"])

    check_torchani_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["model_name"] == "ANI2x"


def test_check_mace_env_reports_success_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_payload(args: Any) -> dict[str, Any]:
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "runtime": {"model": args.model, "device": args.device},
            "prediction": {"mace_mp_energy_per_atom_ev": -5.369234085083008},
        }

    monkeypatch.setattr(check_mace_mp_env, "build_payload", fake_payload)
    monkeypatch.setattr(sys, "argv", ["check_mace_mp_env.py", "--model", "small"])

    check_mace_mp_env.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["runtime"]["model"] == "small"


def test_check_torchani_env_maps_environment_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_predict(atoms: object, spec: dict[str, Any]) -> dict[str, Any]:
        raise ModuleNotFoundError("No module named 'torchani'")

    monkeypatch.setattr(check_torchani_env.torchani_properties, "predict_torchani_properties", fail_predict)
    args = Namespace(model_name="ANI2x", device="cpu")

    payload = check_torchani_env.build_payload(args)

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_environment_error"


def test_check_mace_env_maps_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_predict(atoms: object, spec: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("checkpoint download failed")

    monkeypatch.setattr(check_mace_mp_env.mace_mp_properties, "predict_mace_mp_properties", fail_predict)
    args = Namespace(model="small", device="cpu", default_dtype="float32")

    payload = check_mace_mp_env.build_payload(args)

    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_tool_error"
    assert "checkpoint download failed" in payload["message"]
