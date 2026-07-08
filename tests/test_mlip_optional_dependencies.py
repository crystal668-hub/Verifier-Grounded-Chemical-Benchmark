from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_torchani_and_mace_are_optional_dependencies_only() -> None:
    payload = pyproject()
    default_dependencies = payload["project"]["dependencies"]
    optional = payload["project"]["optional-dependencies"]
    groups = payload["dependency-groups"]

    assert all("torchani" not in item.lower() for item in default_dependencies)
    assert all("mace" not in item.lower() for item in default_dependencies)
    assert "torchani" in optional
    assert "mace" in optional
    assert "torchani" in groups
    assert "mace" in groups


def test_torchani_optional_group_pins_model_runtime() -> None:
    optional = pyproject()["project"]["optional-dependencies"]

    assert "torchani==2.8.2" in optional["torchani"]
    assert "ase==3.28.0" in optional["torchani"]


def test_mace_optional_group_pins_model_runtime() -> None:
    optional = pyproject()["project"]["optional-dependencies"]

    assert "mace-torch==0.3.16" in optional["mace"]
    assert "ase==3.28.0" in optional["mace"]
    assert "pymatgen==2026.5.4" in optional["mace"]
