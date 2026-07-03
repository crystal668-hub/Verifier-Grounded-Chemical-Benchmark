from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "envs" / "openmm-openff.yml"


def test_openmm_openff_conda_env_file_exists() -> None:
    assert ENV_FILE.exists()


def test_openmm_openff_conda_env_uses_conda_forge_only() -> None:
    payload = yaml.safe_load(ENV_FILE.read_text())

    assert payload["name"] == "vgb-openmm-openff"
    assert payload["channels"] == ["conda-forge"]


def test_openmm_openff_conda_env_contains_required_packages() -> None:
    payload = yaml.safe_load(ENV_FILE.read_text())
    dependencies = {str(item).split("=")[0] for item in payload["dependencies"]}

    assert dependencies >= {
        "python",
        "openmm",
        "openff-toolkit",
        "openff-interchange",
        "openmmforcefields",
        "ambertools",
        "rdkit",
        "numpy",
        "pyyaml",
        "pytest",
    }


def test_openmm_openff_not_added_to_pyproject_defaults() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert '"openmm' not in pyproject
    assert '"openff-toolkit' not in pyproject
    assert '"openff-interchange' not in pyproject
    assert '"openmmforcefields' not in pyproject
    assert '"ambertools' not in pyproject
