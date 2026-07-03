from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

import pytest

from scripts import check_openmm_openff_env


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
        [sys.executable, "scripts/check_openmm_openff_env.py", "--mode", "invalid"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    assert "invalid choice" in completed.stderr
