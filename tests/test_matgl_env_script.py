from __future__ import annotations

import json
import subprocess
import sys
import types
from collections.abc import Callable
from typing import Any

from scripts import check_matgl_env


def test_check_matgl_env_reports_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_matgl_env.py", "--no-model-load"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert "matgl" in payload["versions"]
    assert payload["pymatgen"]["fixture_formula"] == "Si"


def install_fake_matgl_modules(
    monkeypatch: Any,
    load_model: Callable[[str], object],
) -> None:
    class FakeComposition:
        reduced_formula = "Si"

    class FakeStructure:
        composition = FakeComposition()

        def __len__(self) -> int:
            return 2

        @classmethod
        def from_file(cls, path: object) -> "FakeStructure":
            return cls()

    matgl = types.ModuleType("matgl")
    matgl.load_model = load_model  # type: ignore[attr-defined]

    pymatgen = types.ModuleType("pymatgen")
    pymatgen_core = types.ModuleType("pymatgen.core")
    pymatgen_core.Structure = FakeStructure

    monkeypatch.setitem(sys.modules, "matgl", matgl)
    monkeypatch.setitem(sys.modules, "pymatgen", pymatgen)
    monkeypatch.setitem(sys.modules, "pymatgen.core", pymatgen_core)
    monkeypatch.setattr(
        check_matgl_env,
        "package_version",
        lambda distribution: {
            "matgl": "4.0.2",
            "pymatgen": "2026.5.4",
            "torch": "2.12.0",
        }[distribution],
    )


def test_check_matgl_env_captures_noisy_model_load(monkeypatch: Any, capsys: Any) -> None:
    class FakeLoadedModel:
        pass

    def load_model(model_name: str) -> FakeLoadedModel:
        print(f"stdout noise while loading {model_name}")
        print("stderr noise while loading model", file=sys.stderr)
        return FakeLoadedModel()

    install_fake_matgl_modules(monkeypatch, load_model)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_matgl_env.py", "--model", "FakeModel"],
    )

    check_matgl_env.main()

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "ok"
    assert payload["model"] == {
        "class": "FakeLoadedModel",
        "loaded": True,
        "name": "FakeModel",
    }


def test_check_matgl_env_returns_json_for_noisy_model_load_failure(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    def load_model(model_name: str) -> object:
        print(f"stdout before failing {model_name}")
        print("stderr before failing model load", file=sys.stderr)
        raise RuntimeError("cache miss")

    install_fake_matgl_modules(monkeypatch, load_model)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_matgl_env.py", "--model", "MissingModel"],
    )

    check_matgl_env.main()

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "missing"
    assert payload["failure_type"] == "verifier_environment_error"
    assert "cache miss" in payload["message"]
    assert payload["model_load_stdout"] == "stdout before failing MissingModel\n"
    assert payload["model_load_stderr"] == "stderr before failing model load\n"
