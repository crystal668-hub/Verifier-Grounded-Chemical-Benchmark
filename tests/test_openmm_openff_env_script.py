from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

import pytest

from scripts.env import check_openmm_openff_env
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.openmm import runtime as openmm_runtime


def test_check_openmm_openff_env_reports_missing_dependency_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def missing_runtime(mode: str) -> dict[str, Any]:
        return {
            "status": "error",
            "failure_type": "verifier_env_error",
            "message": "missing optional dependency: openff.toolkit",
            "versions": {},
            "platforms": [],
            "checks": {
                "core": {"status": "skipped"},
                "openff": {"status": "error", "failure_type": "verifier_env_error"},
                "gaff": {"status": "skipped"},
            },
        }

    monkeypatch.setattr(check_openmm_openff_env, "build_payload", missing_runtime)
    monkeypatch.setattr(sys, "argv", ["check_openmm_openff_env.py", "--mode", "openff"])

    with pytest.raises(SystemExit) as exc:
        check_openmm_openff_env.main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "error"
    assert payload["failure_type"] == "verifier_env_error"
    assert "openff.toolkit" in payload["message"]
    assert captured.err == ""


def test_check_openmm_openff_env_reports_success_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def ok_runtime(mode: str) -> dict[str, Any]:
        assert mode == "core"
        return {
            "status": "ok",
            "failure_type": None,
            "message": None,
            "versions": {"openmm": "8.2.0"},
            "platforms": ["Reference", "CPU"],
            "checks": {"core": {"status": "ok"}},
        }

    monkeypatch.setattr(check_openmm_openff_env, "build_payload", ok_runtime)
    monkeypatch.setattr(sys, "argv", ["check_openmm_openff_env.py", "--mode", "core"])

    check_openmm_openff_env.main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "ok"
    assert payload["failure_type"] is None
    assert captured.err == ""


def test_check_openmm_openff_env_rejects_invalid_mode() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/env/check_openmm_openff_env.py", "--mode", "invalid"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    assert "invalid choice" in completed.stderr


def test_check_script_runs_from_checkout_without_pythonpath() -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    completed = subprocess.run(
        [sys.executable, "scripts/env/check_openmm_openff_env.py", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )

    assert completed.returncode == 0
    assert "--mode" in completed.stdout


def test_quantity_vector_norm_uses_vec3_components() -> None:
    class FakeUnit:
        pass

    class FakeQuantity:
        def __init__(self, value: object) -> None:
            self._value = value

        def value_in_unit(self, target_unit: FakeUnit) -> object:
            assert isinstance(target_unit, FakeUnit)
            return self._value

    class FakeVector:
        x = 3.0
        y = 4.0
        z = 12.0

    assert openmm_runtime.quantity_vector_norm(FakeQuantity(FakeVector()), FakeUnit()) == 13.0
