from __future__ import annotations

import json
import sys
from typing import Any

import pytest

from scripts import check_molgpka_env
from scripts import check_soltrannet_env


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
