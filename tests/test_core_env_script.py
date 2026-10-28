from __future__ import annotations

import json

from scripts.env import check_core_env


def test_default_core_check_never_imports_optional_backends(monkeypatch, capsys):
    imported = []
    def import_core_only(name):
        assert name in {"rdkit", "yaml", "admet_ai"}
        imported.append(name)
    monkeypatch.setattr(check_core_env.importlib, "import_module", import_core_only)
    monkeypatch.setattr(check_core_env, "package_version", lambda _: "fixture")
    monkeypatch.setattr(check_core_env, "check_rdkit", lambda: {"qed": 0.5})
    assert check_core_env.main([]) == 0
    assert set(imported) == {"rdkit", "yaml", "admet_ai"}
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_requested_missing_optional_backend_reports_failure(monkeypatch, capsys):
    def import_without_ase(name):
        if name == "ase":
            raise ModuleNotFoundError("No module named 'ase'")
    monkeypatch.setattr(check_core_env.importlib, "import_module", import_without_ase)
    monkeypatch.setattr(check_core_env, "package_version", lambda _: "fixture")
    assert check_core_env.main(["--include-optional"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "error"
    assert "ase" in result["message"]
